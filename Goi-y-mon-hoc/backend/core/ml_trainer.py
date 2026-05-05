"""
ML Recommendation Model — Gradient Boosted Trees trên features từ CurriculumGraph.

Pipeline:
1. Sinh training data từ DB thực (synthetic_data.generate_training_data)
2. Train GradientBoostingClassifier với 14 features
3. Cross-validate, lưu model + metadata
4. Inference: ml_score_courses(student_ctx, candidates, db) → {code: float 0..1}

Sử dụng:
    # Train (chạy 1 lần sau khi có DB đủ courses):
    python -m backend.core.ml_trainer

    # Inference (academic_engine gọi tự động):
    from backend.core.ml_trainer import ml_score_courses
    scores = ml_score_courses(student_ctx, candidates, db)
"""
from __future__ import annotations

import pathlib
import sys
import time
import warnings
from typing import Any

import numpy as np

from backend.core.curriculum_graph import (
    CurriculumGraph,
    FEATURE_NAMES,
    get_graph,
)

# ── Paths ────────────────────────────────────────────────────────────────────────
_ROOT = pathlib.Path(__file__).resolve().parents[2]
_MODEL_PATH = _ROOT / "data" / "rec_model.joblib"

# ── Model cache ──────────────────────────────────────────────────────────────────
_cached_artifact: dict | None = None
_artifact_mtime: float = 0.0


def _load_artifact() -> dict | None:
    global _cached_artifact, _artifact_mtime
    if not _MODEL_PATH.exists():
        return None
    mtime = _MODEL_PATH.stat().st_mtime
    if _cached_artifact is not None and mtime == _artifact_mtime:
        return _cached_artifact
    try:
        import joblib
        _cached_artifact = joblib.load(_MODEL_PATH)
        _artifact_mtime = mtime
        return _cached_artifact
    except Exception:
        return None


def _save_artifact(artifact: dict) -> None:
    import joblib
    _MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, _MODEL_PATH)
    global _cached_artifact, _artifact_mtime
    _cached_artifact = artifact
    _artifact_mtime = _MODEL_PATH.stat().st_mtime


# ── Training ─────────────────────────────────────────────────────────────────────
def train(
    db=None,
    specialization: str = "Khoa học dữ liệu",
    n_students: int = 600,
    seed: int = 42,
    save: bool = True,
) -> dict | None:
    """
    Train GradientBoostingClassifier trên synthetic data từ DB.

    Args:
        db: SQLAlchemy Session. Nếu None, thử import từ main app.
        specialization: Chuyên ngành để build CurriculumGraph.
        n_students: Số sinh viên synthetic (500-1000 là tốt).
        seed: Random seed.
        save: Lưu model vào disk.

    Returns:
        dict artifact hoặc None nếu thất bại.
    """
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    from sklearn.utils.class_weight import compute_sample_weight
    import joblib

    if db is None:
        print("[ml_trainer] ERROR: db session required")
        return None

    print(f"[ml_trainer] Generating training data ({n_students} synthetic students)...")
    t0 = time.time()

    from backend.scripts.synthetic_data import generate_training_data
    X_list, y_list = generate_training_data(
        db=db,
        specialization=specialization,
        n_students=n_students,
        seed=seed,
    )

    X = np.array(X_list, dtype=np.float32)
    y = np.array(y_list, dtype=np.int32)
    print(f"[ml_trainer] Data ready in {time.time()-t0:.1f}s — "
          f"{len(y)} examples, {X.shape[1]} features, "
          f"pos={y.sum()} ({100*y.mean():.1f}%)")

    if len(y) < 100 or y.sum() < 20:
        print("[ml_trainer] ERROR: Không đủ training examples")
        return None

    # ── Model: GradientBoostingClassifier ──────────────────────────────────────
    # Mạnh hơn LogisticRegression, hoạt động tốt với 14 features phi tuyến,
    # không cần scaling nhưng vẫn thêm để tương thích inference pipeline.
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.85,
            min_samples_leaf=20,
            random_state=seed,
        )),
    ])

    # ── Cross-validation ────────────────────────────────────────────────────────
    n_splits = min(5, max(2, int(y.sum() / 30)))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        cv_scores = cross_val_score(model, X, y, cv=cv, scoring="roc_auc")
    print(f"[ml_trainer] CV ROC-AUC: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")

    # ── Fit trên toàn bộ data ───────────────────────────────────────────────────
    sample_weights = compute_sample_weight("balanced", y)
    model.fit(X, y, clf__sample_weight=sample_weights)
    print("[ml_trainer] Model trained.")

    # ── Feature importance (chỉ in ra, không lưu) ──────────────────────────────
    clf = model.named_steps["clf"]
    importances = clf.feature_importances_
    top = sorted(zip(FEATURE_NAMES, importances), key=lambda x: -x[1])[:5]
    print("[ml_trainer] Top 5 features:", [(n, f"{v:.3f}") for n, v in top])

    artifact = {
        "model": model,
        "feature_names": FEATURE_NAMES,
        "specialization": specialization,
        "n_synthetic": n_students,
        "cv_roc_auc": float(cv_scores.mean()),
        "trained_at": time.time(),
        "n_examples": len(y),
        "pos_rate": float(y.mean()),
    }

    if save:
        _save_artifact(artifact)
        print(f"[ml_trainer] Saved to {_MODEL_PATH}")

    return artifact


# ── Inference ────────────────────────────────────────────────────────────────────
def ml_score_courses(
    student_ctx: dict,
    candidates: list[dict],
    db=None,
) -> dict[str, float]:
    """
    Tính xác suất P(success | student, course) cho từng candidate.

    student_ctx keys:
        avg_score10 (float): GPA thang 10
        gpa_trend (float): -1/0/1
        earned_credits (float): tín chỉ tích lũy
        sem_count (int): số kỳ đã học
        career_goal (str): định hướng
        completed_codes (list[str]): các môn đã qua
        specialization (str): chuyên ngành

    candidates: list of dicts với key "course_code"

    Returns:
        {course_code: probability 0..1}
        Empty dict nếu model chưa được train.
    """
    artifact = _load_artifact()
    if artifact is None:
        return {}

    model = artifact["model"]

    if db is None:
        return {}

    # Build graph để lấy features
    specialization = student_ctx.get("specialization")
    completed_codes = set(student_ctx.get("completed_codes") or [])
    try:
        graph = get_graph(db, specialization, completed_codes)
    except Exception:
        return {}

    # Compute unlock scores một lần cho tất cả candidates
    remaining_codes = {c["course_code"] for c in candidates}
    try:
        unlock_scores = graph.compute_unlock_scores(remaining_codes)
        max_unlock = max(unlock_scores.values()) if unlock_scores else 1
    except Exception:
        unlock_scores = {}
        max_unlock = 1

    # Difficulty stats từ candidates (đã được tính ở academic_engine)
    rows: list[list[float]] = []
    codes: list[str] = []

    gpa = float(student_ctx.get("avg_score10") or 6.0)
    gpa_trend = float(student_ctx.get("gpa_trend") or 0.0)
    credits_earned = float(student_ctx.get("earned_credits") or 0.0)
    sem_count = int(student_ctx.get("sem_count") or 0)
    career = student_ctx.get("career_goal") or "general"

    # Lấy difficulty stats từ academic_engine
    try:
        from backend.core.academic_engine import _get_difficulty_stats
        dstats = _get_difficulty_stats(db)
    except Exception:
        dstats = {}

    for c in candidates:
        code = c.get("course_code", "")
        if not code or code not in graph.courses:
            continue

        dstat = dstats.get(code, {})

        # Prereq avg score từ candidate metadata nếu có
        prereq_avg = c.get("prereq_avg_score")

        try:
            features = graph.extract_features(
                course_code=code,
                student_gpa10=gpa,
                student_gpa_trend=gpa_trend,
                student_credits_earned=credits_earned,
                student_sem_count=sem_count,
                course_pass_rate=dstat.get("pass_rate"),
                course_avg_score10=dstat.get("avg_score10"),
                unlock_count=unlock_scores.get(code, 0),
                max_unlock_count=max_unlock,
                prereq_avg_score=prereq_avg,
                career_track=career,
            )
            rows.append(features)
            codes.append(code)
        except Exception:
            continue

    if not rows:
        return {}

    try:
        X = np.array(rows, dtype=np.float32)
        probs = model.predict_proba(X)[:, 1]
        return {code: float(prob) for code, prob in zip(codes, probs)}
    except Exception:
        return {}


def get_model_info() -> dict:
    """Trả về metadata của model hiện tại."""
    artifact = _load_artifact()
    if artifact is None:
        return {"status": "not_trained"}
    import time as _time
    trained_at = artifact.get("trained_at", 0)
    return {
        "status": "ready",
        "specialization": artifact.get("specialization"),
        "n_examples": artifact.get("n_examples"),
        "cv_roc_auc": artifact.get("cv_roc_auc"),
        "pos_rate": artifact.get("pos_rate"),
        "trained_ago_hours": round((_time.time() - trained_at) / 3600, 1),
        "feature_names": artifact.get("feature_names", FEATURE_NAMES),
    }


# ── CLI entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train ML recommendation model")
    parser.add_argument("--specialization", default="Khoa học dữ liệu",
                        help="Specialization to train for")
    parser.add_argument("--n-students", type=int, default=600,
                        help="Number of synthetic students")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # Import DB session từ app
    import os, sys
    sys.path.insert(0, str(_ROOT))
    from backend.db import SessionLocal
    db = SessionLocal()
    try:
        result = train(
            db=db,
            specialization=args.specialization,
            n_students=args.n_students,
            seed=args.seed,
        )
        if result:
            print(f"\n[ml_trainer] Done. ROC-AUC={result['cv_roc_auc']:.3f}")
        else:
            print("[ml_trainer] Training failed.")
            sys.exit(1)
    finally:
        db.close()
