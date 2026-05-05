# Phân tích thiết kế CSDL — refactor Lớp + Email + Reviews moderation

> Tài liệu phân tích thiết kế DB cho phần báo cáo defense.
> Phản ánh refactor schema 2026-05-05 v2: chuyển từ "GV ↔ chuyên ngành" sang
> "GV chủ nhiệm Lớp ↔ Lớp ↔ SV" (mô hình GVCN truyền thống VN).

## Tổng quan

Hệ thống có **42 bảng** (thêm `class_groups`). Mọi bảng đều được sử dụng bởi
ít nhất một luồng nghiệp vụ. Refactor lần này giải quyết 3 vấn đề thiết kế:

1. **Phân công SV ↔ GV không thực tế**: trước đây mọi SV cùng chuyên ngành
   được gán cho 1 GV "Trưởng bộ môn" → 1 GV gánh tất cả SV của bộ môn.
2. **Workflow upload điểm phức tạp**: file điểm yêu cầu metadata `Mã sinh viên`
   ở đầu file → không khớp với file SV xuất từ portal trường.
3. **Không có cơ chế quên mật khẩu self-service**: admin phải reset thủ công.

## 1. Mô hình Lớp sinh hoạt (ClassGroup)

### Schema mới

```python
class ClassGroup(Base):
    """Lớp sinh hoạt — đơn vị tổ chức học vụ truyền thống của đại học VN.

    Mỗi lớp có 1 GVCN (NOT NULL). 1 GV có thể chủ nhiệm nhiều lớp.
    """
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    cohort = Column(String(10), nullable=False)
    specialization = Column(String(20), nullable=False)
    advisor_id = Column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"),
                        nullable=False)
```

**Format mã lớp**: `DCCTCT{cohort}_{spec_2digit}{letter}`, vd `DCCTCT66_07A`
- `66` = khoá tuyển
- `07` = mã chuyên ngành 2 chữ (suffix của `7480201_07`)
- `A` = thứ tự lớp (A, B, C, ...) trong cùng cohort+spec

### Quan hệ

| Bảng | Field | Quan hệ | ON DELETE |
|---|---|---|---|
| `class_groups.advisor_id` | FK → `users.id` | 1 lớp ↔ 1 GVCN | RESTRICT |
| `users.class_group_id` | FK → `class_groups.id` | 1 SV ↔ 1 lớp | SET NULL |

**ON DELETE RESTRICT** trên `advisor_id`: không cho xoá GV nếu còn lớp chủ nhiệm
→ admin buộc phải PATCH lớp đó (đổi GVCN khác) trước khi xoá GV.

**ON DELETE SET NULL** trên `class_group_id`: xoá lớp → SV về NULL tạm thời,
admin phải re-assign SV vào lớp khác.

### Workflow upload (thứ tự bắt buộc)

| # | File | Cột | Validation |
|---|---|---|---|
| 1 | GV (`advisors`) | Mã GV \| Họ tên \| Email \| Chuyên ngành | Mã GV match regex `^(KHMT\|MMT\|CNPM\|HTTT\|THKT\|CNTTDH\|GV)\d{3}$` |
| 2 | Lớp (`class_groups`) | Mã lớp \| Tên lớp \| Khoá \| Chuyên ngành \| **Mã GVCN** | Mã lớp match format DCCTCT, GVCN phải tồn tại + role=advisor |
| 3 | SV (`users`) | MSSV \| Họ tên \| Email \| **Mã lớp** | MSSV match `sv\d{5}`, lớp phải tồn tại |

**Logic tự động khi import SV**:
- Match `Mã lớp` → `class_groups.code` → derive `specialization` + `cohort`
- Tự động tạo `AdvisorAssignment` với `advisor_id = class_group.advisor_id`
- Reject row nếu lớp chưa tồn tại (chống typo + sai thứ tự)

## 2. Đã dọn — schema khớp code thực thi

### `users` — bỏ `is_head_of_department`

**Lý do**: concept "Trưởng bộ môn" được thay bằng GVCN của Lớp. 1 GV chủ nhiệm
nhiều lớp = "trưởng" theo nghĩa rộng. Không cần flag boolean nữa.

### `users.email_edu` — thêm

Email .edu.vn để forgot password (mock SMTP). Endpoint `POST /auth/forgot-password-edu`
nhận `{username, email_edu}` → match thì gen password mới và trả về response.

### `course_ratings` — thêm soft delete (3 cột)

| Cột | Kiểu | Mục đích |
|---|---|---|
| `hidden` | BOOLEAN, default false | True = admin đã ẩn review |
| `hidden_by` | BIGINT FK → users.id | Admin nào đã ẩn |
| `hidden_at` | TIMESTAMP | Khi nào ẩn |

**Endpoint admin moderation**:
- `GET /admin/reviews` — list + filter theo course/student/rating/hidden
- `DELETE /admin/reviews/{id}` — soft delete (set hidden=True)
- `POST /admin/reviews/{id}/restore` — undo soft delete

**Public filter**: `GET /courses/{code}/reviews` luôn filter `hidden=False`,
review bị ẩn không còn lộ ra UI public.

### `risk_cases` — đơn giản hoá từ 11 cột → 5 cột (đã làm trước đó)

Giữ nguyên simplification cũ — không thay đổi ở refactor này.

## 3. Tính toàn vẹn dữ liệu (defense-in-depth)

Schema được bảo vệ qua **6 lớp**:

### Lớp 1: DB constraints
- `class_groups.code UNIQUE`, `class_groups.advisor_id NOT NULL`
- `class_groups.advisor_id REFERENCES users(id) ON DELETE RESTRICT`
- `users.class_group_id REFERENCES class_groups(id) ON DELETE SET NULL`
- `course_ratings.uq_course_rating UNIQUE(user_id, course_code)` — 1 SV chỉ
  review 1 lần/môn

### Lớp 2: App-level validation
- `parse_class_code()` validate format mã lớp trước khi insert
- Mã GVCN phải tồn tại + `role='advisor'`
- Email format đúng RFC
- MSSV format `sv\d{5}`

### Lớp 3: Atomic transactions
- Mọi thao tác đa-bước nằm trong 1 transaction (commit/rollback together)
- Import lớp: cả batch hoặc rollback toàn bộ
- PATCH `class_group.advisor_id`: update + sync AdvisorAssignment trong 1 commit

### Lớp 4: Cascade sync
1 function duy nhất `sync_advisor_for_class(db, class_group)` được gọi ở MỌI
nơi cần đồng bộ assignment:
- Import lớp (sau khi tạo lớp mới)
- PATCH lớp (đổi GVCN)
- Import SV (sau khi gán SV vào lớp)
- Create SV qua POST /admin/users (qua `assign_advisor_for_student`)

### Lớp 5: Idempotent re-upload
- Re-upload roster nhiều lần KHÔNG sinh duplicate
- UPSERT: `class_groups.code` trùng → update fields, không insert mới
- `users.username` trùng → update class_group_id + spec, re-trigger sync

### Lớp 6: Audit logging
Mọi thao tác admin → ghi `AdminLog`:
- `CREATE_CLASS`, `UPDATE_CLASS`, `DELETE_CLASS`
- `BULK_IMPORT_CLASSES`, `BULK_IMPORT_USERS`, `BULK_IMPORT_ADVISORS`
- `HIDE_REVIEW`, `RESTORE_REVIEW`
- `FORGOT_PASSWORD_RESET_EDU`

## 4. Nghiệp vụ — Endpoint mới

| Endpoint | Mục đích |
|---|---|
| `GET /admin/classes` | List lớp với filter (cohort, spec, advisor) |
| `POST /admin/classes` | Tạo 1 lớp (GVCN bắt buộc) |
| `PATCH /admin/classes/{id}` | Đổi GVCN → tự sync AdvisorAssignment |
| `DELETE /admin/classes/{id}` | Block 409 nếu còn SV |
| `POST /admin/classes/import` | Bulk UPSERT từ Excel |
| `POST /auth/forgot-password-edu` | Reset password qua email_edu (mock) |
| `GET /admin/reviews` | List reviews với filter cho moderation |
| `DELETE /admin/reviews/{id}` | Soft delete review (hidden=True) |
| `POST /admin/reviews/{id}/restore` | Undo soft delete |

## 5. Demo data (sau cleanup)

| Loại | Trước | Sau |
|---|---|---|
| Lớp | 0 (không có concept) | 6 lớp K66 (1/spec) |
| SV | 10 (3 khoá) | 30 SV K66 (5/lớp) |
| GV | 10 (8 head + 2 phụ) | 10 GV (6 GVCN + 4 trợ giảng) |
| File Excel template | 3 file (SV, GV, Phân công) | 3 file (SV, GV, **Lớp**) |

## 6. Migration applied

```sql
-- migration_2026_05_05_class_groups.sql

-- Tạo bảng mới
CREATE TABLE class_groups (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    cohort VARCHAR(10) NOT NULL,
    specialization VARCHAR(20) NOT NULL,
    advisor_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Bổ sung users
ALTER TABLE users ADD COLUMN email_edu VARCHAR(255);
ALTER TABLE users ADD COLUMN class_group_id BIGINT
    REFERENCES class_groups(id) ON DELETE SET NULL;
ALTER TABLE users DROP COLUMN is_head_of_department;

-- Soft delete reviews
ALTER TABLE course_ratings ADD COLUMN hidden BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE course_ratings ADD COLUMN hidden_by BIGINT
    REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE course_ratings ADD COLUMN hidden_at TIMESTAMP;
```

## 7. Defense Q&A talking points

### Q: Tại sao chọn mô hình Lớp thay vì round-robin?

> "Em áp dụng mô hình GVCN truyền thống — mỗi GV chủ nhiệm 1-2 lớp, mỗi SV
> thuộc 1 lớp với GVCN cố định. Đây là cách quản lý đào tạo của các trường
> đại học VN, phản ánh thực tế: GV nắm sát lớp, SV biết rõ thầy/cô của mình.
> Round-robin tự động không có context — SV không biết tại sao lại được phân
> cho GV này, GV cũng không có nhóm SV thuộc về mình."

### Q: Tại sao class_groups.advisor_id NOT NULL?

> "Một lớp phải có GVCN — không có thì SV trong lớp không biết liên hệ với ai.
> Em enforce qua DB constraint NOT NULL + ON DELETE RESTRICT trên FK. Khi GV
> nghỉ, admin buộc phải đổi GVCN cho các lớp đó trước khi xoá GV — không có
> kẽ hở 'lớp mồ côi'."

### Q: Forgot password tại sao không gửi email thật?

> "Demo environment không có SMTP server, em mock bằng cách trả password mới
> trực tiếp tại response. Production sẽ thay bằng SMTP gửi reset link — kiến
> trúc endpoint đã tách rõ (POST /auth/forgot-password-edu nhận username +
> email_edu, validate match → gen password). Chỉ cần thay phần `gen + return`
> bằng `gen + queue email send` là production-ready."

### Q: Tính toàn vẹn data đảm bảo thế nào?

> "Em có 6 lớp bảo vệ: DB constraint (FK + UNIQUE + NOT NULL), app validation
> (regex format, role check), atomic transaction, cascade sync function dùng
> chung, UPSERT idempotent cho re-upload, và AdminLog audit cho mọi thao tác.
> Schema-level NOT NULL + RESTRICT đảm bảo không có data corruption nếu admin
> thao tác sai."

### Q: Soft delete review để làm gì?

> "Để admin moderation reviews (xoá spam/sai) mà vẫn giữ data cho audit. Trường
> hợp lỡ ẩn nhầm có thể restore bằng POST /admin/reviews/{id}/restore. Hard
> delete sẽ mất audit trail — không khôi phục được."

## 8. Số liệu schema sau refactor

| Metric | Trước | Sau |
|---|---|---|
| Tables | 41 | 42 (+ class_groups) |
| Total columns | ~271 | ~280 (+8 mới, -1 drop is_head) |
| Concepts removed | — | Trưởng bộ môn (is_head_of_department) |
| Concepts added | — | Lớp sinh hoạt, Email recovery, Soft-delete review |
| Self-service flows | 0 | 1 (forgot password) |
| Moderation flows | 0 | 1 (review hide/restore) |
