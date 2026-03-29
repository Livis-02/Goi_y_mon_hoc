from __future__ import annotations

import hashlib
from pathlib import Path
import unicodedata

from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.db import get_db, engine
from backend import models, schemas
from backend.curriculum_importer import import_curriculum_from_excel
from backend.academic_engine import build_progress_snapshot, build_recommendations
from backend.chat_assistant import chat_reply, get_chat_history
from backend.parser import read_rows_from_upload, extract_grades, extract_tich_luy

STUDY_GOALS: dict[int, float] = {}  # user_id -> target_gpa (in-memory, mirrors StudyPlan)

app = FastAPI(title="CNTT GPA API")


@app.on_event("startup")
def on_startup():
    models.Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TOKENS: dict[str, int] = {}

PASSWORD_POLICY = {
    "min_length": 8,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_digit": True,
}

DEFAULT_CURRICULUM_FILE = Path("data/7480201.docx")


def _hash_password(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _issue_token(user: models.User) -> str:
    token = hashlib.sha256(f"{user.username}:{user.id}".encode("utf-8")).hexdigest()
    TOKENS[token] = user.id
    return token


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.replace("\u0111", "d").replace("\u0110", "d"))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _normalize_text(text: str) -> str:
    return _strip_accents(str(text or "")).lower().strip()


def _resolve_user_role(_user: models.User) -> str:
    return "student"


def _to_user_out(user: models.User) -> schemas.UserOut:
    return schemas.UserOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=_resolve_user_role(user),
        specialization=user.specialization,
    )


def _authenticate(username: str, password: str, db: Session) -> models.User:
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or user.password_hash != _hash_password(password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return user


def _get_user_by_token(authorization: str | None, db: Session) -> models.User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.replace("Bearer ", "", 1).strip()
    user_id = TOKENS.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user



@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/auth/password-policy")
def password_policy():
    return PASSWORD_POLICY


@app.post("/auth/register", response_model=schemas.UserOut)
def register(payload: schemas.RegisterIn, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = models.User(
        username=payload.username,
        password_hash=_hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _to_user_out(user)


@app.post("/auth/login")
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    user = _authenticate(payload.username, payload.password, db)
    token = _issue_token(user)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/admin/login")
def admin_login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    user = _authenticate(payload.username, payload.password, db)
    token = _issue_token(user)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me", response_model=schemas.UserOut)
def me(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    user = _get_user_by_token(authorization, db)
    return _to_user_out(user)


@app.post("/curriculum/import", response_model=schemas.CurriculumImportOut)
def import_curriculum(
    file_path: str = str(DEFAULT_CURRICULUM_FILE),
    replace_existing: bool = True,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _get_user_by_token(authorization, db)

    try:
        stats = import_curriculum_from_excel(
            db,
            file_path=file_path,
            replace_existing=replace_existing,
        )
        db.commit()
        return schemas.CurriculumImportOut(**stats.__dict__)
    except FileNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Failed to import curriculum: {exc}")


@app.get("/courses", response_model=list[schemas.CourseOut])
def list_courses(db: Session = Depends(get_db)):
    return db.query(models.Course).order_by(models.Course.course_code.asc()).all()


@app.get("/admin/courses", response_model=list[schemas.CourseOut])
def admin_list_courses(
    q: str | None = None,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _get_user_by_token(authorization, db)
    query = db.query(models.Course)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            models.Course.course_code.ilike(like) | models.Course.course_name.ilike(like)
        )
    return query.order_by(models.Course.course_code.asc()).all()


@app.post("/admin/courses", response_model=schemas.CourseOut)
def admin_create_course(
    payload: schemas.CourseAdminIn,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _get_user_by_token(authorization, db)
    existing = db.query(models.Course).filter(models.Course.course_code == payload.course_code).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Mã môn '{payload.course_code}' đã tồn tại")
    course = models.Course(
        course_code=payload.course_code,
        course_name=payload.course_name,
        credits=payload.credits,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@app.put("/admin/courses/{course_id}", response_model=schemas.CourseOut)
def admin_update_course(
    course_id: int,
    payload: schemas.CourseAdminIn,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _get_user_by_token(authorization, db)
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy môn học")
    conflict = db.query(models.Course).filter(
        models.Course.course_code == payload.course_code,
        models.Course.id != course_id,
    ).first()
    if conflict:
        raise HTTPException(status_code=409, detail=f"Mã môn '{payload.course_code}' đã tồn tại")
    course.course_code = payload.course_code
    course.course_name = payload.course_name
    course.credits = payload.credits
    db.commit()
    db.refresh(course)
    return course


@app.patch("/admin/courses/{course_id}/count-toward-credits", response_model=schemas.CourseOut)
def admin_toggle_count_toward_credits(
    course_id: int,
    count_toward_credits: bool,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _get_user_by_token(authorization, db)
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy môn học")
    course.count_toward_credits = count_toward_credits
    db.commit()
    db.refresh(course)
    return course


@app.delete("/admin/courses/{course_id}", response_model=schemas.MessageOut)
def admin_delete_course(
    course_id: int,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _get_user_by_token(authorization, db)
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Không tìm thấy môn học")
    db.delete(course)
    db.commit()
    return schemas.MessageOut(message=f"Đã xóa môn '{course.course_name}'")


@app.post("/admin/courses/bootstrap-default", response_model=schemas.CourseBootstrapOut)
def admin_bootstrap_default_courses(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _get_user_by_token(authorization, db)
    try:
        stats = import_curriculum_from_excel(db, file_path=str(DEFAULT_CURRICULUM_FILE), replace_existing=True)
        db.commit()
        return schemas.CourseBootstrapOut(
            inserted=stats.inserted_courses,
            skipped=stats.protected_courses,
            total_rows=stats.total_rows,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Lỗi import: {exc}")


@app.get("/admin/prerequisites", response_model=list[schemas.CoursePrerequisiteOut])
def list_prerequisites(
    course_code: str | None = None,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _get_user_by_token(authorization, db)
    q = db.query(models.CoursePrerequisite)
    if course_code:
        q = q.filter(models.CoursePrerequisite.course_code == course_code.strip())
    return q.order_by(models.CoursePrerequisite.course_code.asc()).all()


@app.post("/admin/prerequisites", response_model=schemas.CoursePrerequisiteOut)
def add_prerequisite(
    payload: schemas.CoursePrerequisiteIn,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _get_user_by_token(authorization, db)
    if payload.course_code == payload.prerequisite_code:
        raise HTTPException(status_code=400, detail="Môn học không thể là tiên quyết của chính nó")
    for code in (payload.course_code, payload.prerequisite_code):
        if not db.query(models.Course).filter(models.Course.course_code == code).first():
            raise HTTPException(status_code=404, detail=f"Không tìm thấy môn '{code}'")
    existing = db.query(models.CoursePrerequisite).filter(
        models.CoursePrerequisite.course_code == payload.course_code,
        models.CoursePrerequisite.prerequisite_code == payload.prerequisite_code,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Quan hệ tiên quyết này đã tồn tại")
    p = models.CoursePrerequisite(
        course_code=payload.course_code,
        prerequisite_code=payload.prerequisite_code,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@app.delete("/admin/prerequisites/{prereq_id}", response_model=schemas.MessageOut)
def delete_prerequisite(
    prereq_id: int,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _get_user_by_token(authorization, db)
    p = db.query(models.CoursePrerequisite).filter(models.CoursePrerequisite.id == prereq_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Không tìm thấy quan hệ tiên quyết")
    db.delete(p)
    db.commit()
    return schemas.MessageOut(message=f"Đã xóa tiên quyết {p.prerequisite_code} → {p.course_code}")


@app.get("/elective-rules", response_model=list[schemas.ElectiveRuleOut])
def list_elective_rules(
    specialization: str | None = None,
    program_code: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.ElectiveRule)
    if specialization:
        q = q.filter(models.ElectiveRule.specialization == specialization)
    if program_code:
        q = q.filter(models.ElectiveRule.program_code == program_code)
    return q.order_by(models.ElectiveRule.specialization.asc(), models.ElectiveRule.group_type.asc()).all()


@app.post("/grades/upload", response_model=schemas.GradeUploadOut)
def upload_grades(
    file: UploadFile,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _get_user_by_token(authorization, db)

    data = file.file.read()
    filename = file.filename or "upload.xlsx"

    try:
        rows = read_rows_from_upload(filename, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=400, detail="Khong the doc file. Kiem tra lai dinh dang (xlsx/csv).")

    grade_records = extract_grades(rows)
    if not grade_records:
        raise HTTPException(status_code=400, detail="Khong tim thay du lieu diem trong file.")

    tich_luy = extract_tich_luy(rows)
    if tich_luy is not None:
        user.official_earned_credits = tich_luy

    all_courses = {c.course_code: c for c in db.query(models.Course).all()}

    try:
        db.query(models.UserGrade).filter(models.UserGrade.user_id == user.id).delete()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Loi xoa du lieu cu.")

    inserted = 0
    skipped_unknown = 0
    issues: list[schemas.GradeUploadIssue] = []

    for rec in grade_records:
        code = rec["course_code"]
        if code not in all_courses:
            issues.append(schemas.GradeUploadIssue(
                course_code_in_file=code,
                course_name_in_file=rec.get("course_name"),
                reason="Ma mon khong co trong CTDT",
            ))
            skipped_unknown += 1
            continue

        db.add(models.UserGrade(
            user_id=user.id,
            course_code=code,
            score10=rec.get("score10"),
            score4=rec.get("score4"),
            letter=rec.get("letter"),
            passed=rec.get("passed", False),
            term=rec.get("term"),
        ))
        inserted += 1

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Loi luu du lieu: {exc}")

    return schemas.GradeUploadOut(inserted=inserted, skipped_unknown=skipped_unknown, issues=issues)


@app.get("/grades/me", response_model=list[schemas.UserGradeOut])
def list_my_grades(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _get_user_by_token(authorization, db)
    return (
        db.query(models.UserGrade)
        .filter(models.UserGrade.user_id == user.id)
        .order_by(models.UserGrade.uploaded_at.desc())
        .all()
    )


@app.patch("/auth/me/specialization", response_model=schemas.UserOut)
def update_specialization(
    payload: schemas.SpecializationIn,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _get_user_by_token(authorization, db)
    user.specialization = payload.specialization
    db.commit()
    db.refresh(user)
    return _to_user_out(user)


@app.get("/study-goal/me", response_model=schemas.StudyGoalOut)
def get_study_goal(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _get_user_by_token(authorization, db)
    plan = db.query(models.StudyPlan).filter(models.StudyPlan.user_id == user.id).order_by(models.StudyPlan.id.desc()).first()
    target_gpa = float(plan.target_gpa) if plan and plan.target_gpa is not None else None
    return schemas.StudyGoalOut(target_gpa=target_gpa)


@app.put("/study-goal/me", response_model=schemas.StudyGoalOut)
def set_study_goal(
    payload: schemas.StudyGoalIn,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _get_user_by_token(authorization, db)
    plan = db.query(models.StudyPlan).filter(models.StudyPlan.user_id == user.id).order_by(models.StudyPlan.id.desc()).first()
    if plan:
        plan.target_gpa = payload.target_gpa
    else:
        plan = models.StudyPlan(user_id=user.id, plan_name="default", target_gpa=payload.target_gpa)
        db.add(plan)
    db.commit()
    db.refresh(plan)
    return schemas.StudyGoalOut(target_gpa=float(plan.target_gpa) if plan.target_gpa is not None else None)


@app.get("/progress/me", response_model=schemas.ProgressOut)
def progress_me(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _get_user_by_token(authorization, db)
    plan = db.query(models.StudyPlan).filter(models.StudyPlan.user_id == user.id).order_by(models.StudyPlan.id.desc()).first()
    target_gpa = float(plan.target_gpa) if plan and plan.target_gpa is not None else None
    return schemas.ProgressOut(**build_progress_snapshot(db, user.id, target_gpa=target_gpa))


@app.get("/recommendations/me", response_model=schemas.RecommendationOut)
def recommendations_me(
    limit: int = 5,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _get_user_by_token(authorization, db)
    payload = build_recommendations(db, user.id, limit=limit)
    return schemas.RecommendationOut(**payload)

@app.post("/chat/me", response_model=schemas.ChatOut)
def chat_me(
    payload: schemas.ChatIn,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _get_user_by_token(authorization, db)
    result = chat_reply(
        message=payload.message,
        db=db,
        user_id=user.id,
        limit=payload.limit,
        prefer_llm=payload.prefer_llm,
    )
    return schemas.ChatOut(intent=result.intent, answer=result.answer, suggestions=result.suggestions)


@app.get("/chat/history/me", response_model=list[schemas.ChatHistoryItemOut])
def chat_history_me(
    limit: int = 30,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    user = _get_user_by_token(authorization, db)
    return get_chat_history(db, user.id, limit=limit)
