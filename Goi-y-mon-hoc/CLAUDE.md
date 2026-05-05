# CLAUDE.md — Hướng dẫn làm việc với project này

> Đọc file này TRƯỚC KHI làm bất cứ việc gì.
> Cập nhật: 2026-05-05 (Lớp sinh hoạt refactor + bỏ first-login setup + DB cleanup)

---

## 1. Project là gì

**EduGuide** — Web app gợi ý môn học và theo dõi tiến độ học tập cho sinh viên ngành CNTT (mã 7480201).

**Repo:** `E:\Do_an\Goi-y-mon-hoc`

**Stack:** FastAPI (Python 3.11+) + PostgreSQL + HTML/CSS/JS thuần + Tailwind CDN + ML (GradientBoosting) + LLM chain (Gemini → Groq → OpenAI → Claude)

**Không đề cập:** HUMG, Mỏ-Địa chất (đã bỏ khỏi branding).

---

## 2. Tài liệu cần đọc (theo thứ tự)

| File | Nội dung | Độ ưu tiên |
|------|---------|-----------|
| `docs/PHAN_TICH_THIET_KE.md` | Phân tích thiết kế CSDL sau refactor 2026-05-05 — ClassGroup, soft-delete reviews, cleanup. Defense Q&A talking points | **Đọc trước tiên** |
| `docs/KICH_BAN.md` | Kịch bản đi qua MỌI chức năng theo flow Admin → SV → GV (cập nhật cho 6 lớp + 30 SV K66) | Demo + bảo vệ |
| `docs/DEFENSE_DEMO.md` | Script demo 15-20' cho hội đồng bảo vệ | Bảo vệ trước hội đồng |
| `data/ctdt/CTDT_CHUAN.md` | CTĐT thực tế 6 chuyên ngành, quy tắc tính TC, tiên quyết | Đọc khi cần logic học vụ |
| `data/demo/README.md` | Bộ dữ liệu Excel demo: 10 GV + 6 Lớp + 30 SV (K66) + bảng điểm cá nhân | Setup data |

---

## 3. Trạng thái hiện tại (đọc kỹ trước khi code)

### 3.1 Đã hoàn thiện và đang chạy tốt

**Backend (`backend/main.py` — ~12.600 dòng, ~150 routes sau cleanup):**

**Auth & Users (3 endpoints sau Phase 6):**
- `POST /auth/login` (case-insensitive), `POST /auth/me/change-password`, `GET /auth/me`
- ❌ Đã DROP: `/auth/forgot-password`, `/auth/forgot-password-edu`, `/auth/reset-password`, `/auth/me/setup-account`, `/auth/google` (xem Phase 6 + Phase 4)
- Forgot password: SV liên hệ admin → admin reset qua `POST /admin/users/{id}/reset-password` (admin nhận pw mới + giao SV)
- Mã SV: format `sv\d{5}` (vd `sv66001`). Mã GV: prefix bộ môn (KHMT001, MMT001, CNPM001, HTTT001, THKT001, CNTTDH001, GV001)
- Default password 6 số (admin xem qua icon 👁 khi `default_password` còn). User đổi pw → `default_password=NULL` tự động

**Admin (4 chức năng chính sau Phase 3):**
1. **Quản lý tài khoản**:
   - CRUD users (SV/GV/Lớp), `POST /admin/users`, `POST /admin/users/import` (CSV/Excel)
   - **ClassGroup**: `GET/POST/PATCH/DELETE /admin/classes`, `POST /admin/classes/import` (Lớp sinh hoạt + GVCN bắt buộc)
   - Reset password: `POST /admin/users/{id}/reset-password`
   - Workflow upload BẮT BUỘC tuần tự: GV → Lớp → SV (FK constraint enforces)
2. **Thông báo hệ thống**:
   - `POST /admin/notifications` với 8 target types: all / all_students / all_advisors / cohort / specialization / students / advisors / department
   - Severity: info / warning / urgent
   - `GET /admin/notifications/estimate-reach` đếm số user
3. **CTĐT**:
   - `GET /admin/courses/grouped` (4 nhóm BB/TC-A/B/C/spec), `/admin/courses/all-ctdt`
   - `POST/DELETE /admin/prerequisites` (cycle check)
   - CRUD courses với `count_toward_credits`, `required_specialization`, M2M `course_specializations`
4. **Đánh giá môn học (moderation)**:
   - `GET /admin/reviews` (filter course/student/rating/hidden)
   - `DELETE /admin/reviews/{id}` (soft delete: `hidden=True`), `POST /admin/reviews/{id}/restore`
   - Public `GET /courses/{code}/reviews` luôn filter `hidden=False`
5. **Nhật ký**: `GET /admin/logs` audit trail mọi thao tác CRUD/import

❌ Đã DROP (không dùng nữa):
- `POST /admin/grades/import` (Phase 2 — EduGuide là tool cá nhân, SV tự upload)
- `GET /admin/users/{id}/grades`, `GET /admin/reports/graduation` (Phase 3 — admin không xem điểm/GPA SV nữa)
- `PATCH /admin/users/{id}/grades-lock` (Phase 2 — không lock SV)
- `POST /admin/advisors/{id}/transfer-head` (Phase 1 — concept "Trưởng bộ môn" bỏ)

Dashboard `GET /admin/dashboard/stats`: chỉ còn `total_students`, `total_advisors`, `total_courses`, `students_without_advisor`, `students_never_logged_in`, cohort/spec distribution. Không còn `at_risk_students`, `thesis_eligible`, GPA stats.

**Courses & Curriculum (cho SV/GV):**
- `GET /courses/standard-plan?spec=...`: sơ đồ kế hoạch chuẩn theo CN
- `GET /courses/{code}/reviews`, `POST /ratings/{course_code}` (SV rate môn đã pass), `GET /ratings/{course_code}/summary`

**Student:**
- Grades: `POST /grades/upload` (full replace, không merge), `GET /grades/me`, `GET /grades/me/status` (luôn `can_upload=True`)
- Progress: `/progress/me` — TC tích lũy live từ `user_grades.passed`, GPA hệ 4/10, điều kiện TN ước tính
- Recommendations: ML (GradientBoosting) + LLM rerank cho TC-A/B/C; BB list theo HK chuẩn không rerank
- Roadmap: `/v2/integrated-roadmap/me`, what-if, drag-drop môn TC vào slot
- Career: `/careers/*`, skill tree, evidence
- Chat AI: `/chat/*`, RAG over CTĐT + bảng điểm cá nhân

**Advisor (sau refactor — bỏ concept "Trưởng BM"):**
- `/advisor/students`: DS SV thuộc lớp chủ nhiệm (qua AdvisorAssignment, sync từ ClassGroup)
- `/advisor/my-department-students`, `/advisor/my-department-advisors`: mọi GV cùng spec đều xem được
- `/advisor/students/{id}/roadmap`: lộ trình SV phụ trách
- `/advisor/notes`: CRUD ghi chú (có `course_code` để gắn vào môn cụ thể)
- Messaging direct `/messages/direct/{user_id}` SV↔GV (admin KHÔNG có messaging)

### 3.2 Frontend đã có

Tất cả ở `frontend/pages/`. Cập nhật 2026-05-05 sau Phase 5 (UX consistency với app-core.js) + Phase 6 (xoá reset-password.html).

**12 page HTML** (mỗi page đều load `app-core.js` ở đầu, KHÔNG còn local `function toast/showToast/callApi`):

| File | Mô tả |
|------|-------|
| `index.html` | Login + role-based redirect (đã bỏ modal setup + forgot password, chỉ còn text "Liên hệ admin") |
| `home.html` | Dashboard SV — layout v3 (1280px, 8/12 main + 4/12 aside) |
| `integrated-roadmap.html` | Lộ trình tích hợp (CTĐT + drag-drop môn TC) |
| `grades.html` | Bảng điểm + charts (rebrand "tool cá nhân", luôn cho upload) |
| `messaging.html` | Chat direct SV ↔ cố vấn |
| `ai-chat.html` | AI chat threads (RAG) |
| `career-goal.html` | Mục tiêu nghề + skill tree + evidence |
| `notifications.html` | Trung tâm thông báo |
| `settings.html` | Cài đặt + Change password |
| `advisor.html` | Cổng cố vấn (sau bỏ concept Trưởng BM — không còn badge GVCN) |
| `admin.html` | Admin (4 chức năng: Tài khoản / Lớp / Đánh giá / Thông báo + Nhật ký + CTĐT) |
| `landing.html` | Trang giới thiệu (root `/` redirect tới đây) |

**Shared modules** (load thứ tự trong `<head>`):

| File | Mô tả |
|------|-------|
| `app-core.js` (Phase 5) | **Module shared 18KB** — `App.api/toast/modal/loading/showEmpty/showError`, debounce/throttle. Backward-compat shims: `window.callApi`, `window.toast`, `window.showToast`, `window.escHtml` |
| `theme.css` (v7) | Shared design system — CSS vars (light + dark), Stripe-style components, anti-FOUC sidebar strip |
| `theme.js` (v3) | Tailwind config — token trỏ vào CSS vars để markup cũ flip màu auto khi đổi mode |
| `theme-switcher.js` (v2) | Light/Dark/Auto toggle — persist `localStorage.eduguide_theme`, sessionStorage flag chống animation replay |
| `sidebar-init.js` (v10) | Sidebar render sync, scoped dark navy CSS vars trên `#sidebarDrawer` / `#adminSidebar` |
| `ajax-nav.js` (v6) | ⚠️ DISABLED (line 17 `return`) — multi-page nav truyền thống cho stability |
| `_curriculum_chart.js` | Component sơ đồ CTĐT dùng chung 3 role |
| `auth.js`, `floating-chat.js`, `accessibility.js`, `scroll-helpers.js`, `nav-prefetch.js`, `utils.js` | Shared utilities |

**Design system convention v3** (chốt 2026-05-02):

Order load trong `<head>` (BẮT BUỘC theo thứ tự):
```html
<link rel="stylesheet" href="theme.css?v=7"/>
<script src="theme.js?v=3"></script>            <!-- Tailwind config — TRƯỚC CDN -->
<script src="theme-switcher.js?v=2"></script>   <!-- Đặt .dark sync, chống FOUC -->
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
```

**3 màu chủ đạo** (không thêm màu trang trí):
- Slate (neutral) — UI chrome, surfaces, text, borders
- Indigo `#635bff` (primary) — CTA, accent, KPI primary, hero blob
- Emerald `#00ba88` (secondary) — success, growth, positive states
- Status (red/amber) chỉ khi có data thực sự cảnh báo, không decorative.

**Layout pattern v3** (đã apply ở `home.html`, các page khác giữ markup cũ + đổi topbar):
- Container `class="container-app"` → max-width 1280px, padding responsive.
- Topbar `class="topbar"` → fixed 60px, blur backdrop, breadcrumb + theme toggle + bell + avatar.
- Main grid `lg:grid-cols-12` → main `lg:col-span-8` + aside `lg:col-span-4`.
- Body `class="bg-canvas text-text-primary antialiased min-h-screen"`.

**Component primitives có sẵn** (gọi qua className, đừng tự build lại):
- `.card`, `.card-hover`, `.card-flat`, `.card-elevated`, `.card-feature`, `.card-highlight`
- `.btn` + variants: `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.btn-danger`, `.btn-sm`, `.btn-lg`
- `.input` (form input với focus ring)
- `.pill` + variants: `.pill-success`, `.pill-warn`, `.pill-danger`, `.pill-info`, `.pill-neutral`, `.pill-accent`
- `.eyebrow` (small uppercase label trên heading)
- `.stat-num`, `.stat-num-lg` (KPI numbers với tabular-nums)
- `.kpi-tile` + variants: `.kpi-tile-primary`, `.kpi-tile-secondary`, `.kpi-tile-neutral` (tinted backgrounds)
- `.aside-card` (panel bên phải)
- `.cta-dashed` (upload-style CTA box)
- `.hero-card`, `.hero-strip` (greeting block)
- `.chip-primary`, `.chip-secondary`, `.chip-neutral` (icon background chips)
- `.theme-toggle` (button đổi sáng/tối, auto-wired qua theme-switcher.js)
- `.skeleton` (loading shimmer)
- `.stat-strip`, `.stat-strip-item`, `.stat-strip-divider` (dòng số liệu inline)
- Animations: `.fade-up`, `.fade-up-delay-1..4` — **chỉ chạy lần đầu/session** (sessionStorage flag), không replay khi full reload.

**Cấm**:
- KHÔNG inline `tailwind.config = ...` ở từng page (đã consolidate vào theme.js).
- KHÔNG duplicate `@view-transition`, `.msym`, `.pri-grad`, autofill kill, scrollbar (đã trong theme.css).
- KHÔNG thêm chip màu mới (amber/rose/sky) — strict 3-color discipline.
- KHÔNG bật lại view-transitions khi `ajax-nav` còn DISABLED — gây jitter ở full reload.

### 3.3 Quyết định thiết kế đã chốt

| Quyết định | Chi tiết |
|-----------|----------|
| Tên app | EduGuide (không nhắc HUMG / Mỏ-Địa chất) |
| Mã SV | Format `sv\d{5}` (vd `sv66001` = K66 #001). 2 chữ số đầu sau `sv` = cohort |
| Mã GV | Prefix bộ môn + 3 số (KHMT001, MMT001, CNPM001, HTTT001, THKT001, CNTTDH001, GV001 đại cương) |
| Họ tên | Auto title case qua `normalize_vietnamese_name()` |
| File điểm format | Dòng 1: `Mã sinh viên: ...`, dòng 2: `Họ và tên: ...` |
| QPAN | Mã bắt đầu `73` — không tính TC, không vào GPA |
| **Lớp sinh hoạt** (Phase 1) | Mỗi SV thuộc 1 lớp, mỗi lớp có 1 GVCN (NOT NULL, ON DELETE RESTRICT). Mã lớp format `DCCTCT{cohort}_{spec_2digit}{letter}` vd `DCCTCT66_07A` |
| Auto-assign SV ↔ GVCN | Qua `class_group.advisor_id` (function `sync_advisor_for_class`). KHÔNG còn round-robin, KHÔNG còn concept "Trưởng bộ môn" |
| Workflow upload | BẮT BUỘC tuần tự: GV → Lớp → SV (FK constraint enforce) |
| Mật khẩu | Default 6 số. Admin xem qua icon 👁 khi `default_password` còn. User đổi pw → `default_password=NULL` tự động |
| Username login | Case-insensitive |
| **Quên mật khẩu** (Phase 6) | KHÔNG self-service. SV liên hệ admin → admin reset qua `POST /admin/users/{id}/reset-password` → giao SV. Không SMTP, không token reset, không email cá nhân |
| **First-login** (Phase 6) | KHÔNG có setup modal. SV login → vào thẳng app theo role. Đổi pw qua Settings (`POST /auth/me/change-password`) |
| **Admin KHÔNG quản lý điểm** (Phase 2-3) | Không có grades/import, không xem điểm/GPA SV. EduGuide là **tool cá nhân**, đã có SIS chính thức của trường |
| Admin KHÔNG có Tab tin nhắn | Dùng Notifications broadcast. Advisor VẪN có messaging direct với SV |
| Admin Dashboard | READ-ONLY — stats cơ bản (Tổng SV / SV đã upload / SV chưa CV / cohort/spec distribution). KHÔNG còn báo cáo TN, GPA avg, at_risk_students, thesis_eligible |
| SV không đổi CN | Trong app (quyết định CN là việc của trường — admin import qua Lớp) |
| Eligibility check (TT/ĐATN/TN) | Chỉ là **ước tính** cho SV xây lộ trình, không phải chính thức (đã có SIS) |

### 3.4 Pattern UI đã chốt

- **Tab Sinh viên admin:** Master-Detail + Filter header (table grouped khoá + side panel slide-in). KHÔNG có cột GPA / TC, KHÔNG có button "Xem bảng điểm", KHÔNG còn filter "Quá hạn"
- **Tab Cố vấn admin:** Grid Cards grouped theo chuyên ngành. KHÔNG còn distinguish GVCN (ai cũng là GVCN nếu chủ nhiệm ≥1 lớp). 3 stats: Tổng / Chưa có SV / SV chưa có CV
- **Tab Lớp sinh hoạt admin** (Phase 1): Table + side panel, CRUD lớp + Import Excel, hiển thị `code | name | cohort | specialization | GVCN | student_count`. PATCH advisor_id auto-sync AdvisorAssignment
- **Tab Đánh giá môn học admin** (Phase 1): Table reviews + filter (course/student/rating/hidden). Hide/Restore actions. Soft delete `hidden=True`
- **Tab Môn học admin:** Table + Side Panel, 4 accordion BB/TC-A/B/C, 7 tab (Đại cương + 6 CN) + 2 sub-tab (Danh sách / Kế hoạch chuẩn)
- **Sơ đồ kế hoạch:** Lưới HK × STT, SVG arrows, click môn → highlight upstream/downstream. Admin có toggle edit mode → +/- tiên quyết
- **SV xem sơ đồ:** Highlight môn đã học (xanh) / đang học (vàng) / chưa (bình thường)

### 3.4b Layout backend đã tái cấu trúc (quan trọng — không break)

```
backend/
├── main.py              ── ~12.000 dòng, 232 routes, 59 helpers
├── core/                ── logic nghiệp vụ tách module
│   ├── academic_engine.py     (2675 dòng — progress, recommendations, roadmap, analytics)
│   ├── chat_assistant.py      (1282 — LLM chain + chat history)
│   ├── ai_advisor.py          (281  — Gemini/Groq/Claude/OpenAI rerank — gọi qua `backend.core.ai_advisor`)
│   ├── risk_engine.py         (523  — risk score + cases)
│   ├── curriculum_graph.py    (415  — đồ thị tiên quyết)
│   ├── ml_trainer.py          (328  — train GradientBoosting → rec_model.joblib)
│   ├── grade_predictor.py, parser.py, career_data.py, career_journey_resources.py
│   └── __init__.py
├── db/                  ── tách rõ persistence
│   ├── db.py            (engine + SessionLocal + get_db)
│   ├── models.py        (50 SQLAlchemy classes)
│   ├── schemas.py       (~120 Pydantic classes)
│   ├── migrate.py       (idempotent runner — chạy lúc startup)
│   └── migrations/      (9 file SQL versioning)
└── scripts/             ── CLI tools, seeders, importers (6 file)
    ├── curriculum_importer.py        (parse docx/xlsx/csv → DB)
    ├── import_curriculum.py          (driver gọi curriculum_importer)
    ├── generate_demo_data.py         (⭐ tạo 10 SV/GV/phân công + 10 file điểm XLSX)
    ├── generate_assignment_templates.py (template phân công cho admin download)
    ├── seed_careers.py               (seed danh sách nghề + skills mapping)
    └── synthetic_data.py             (generate training data cho ML từ DB thực)
```

**Cảnh báo import:** module `backend.ai_advisor` đã chuyển sang `backend.core.ai_advisor` — không còn alias. Mọi `from backend.<old_name>` import (academic_engine, chat_assistant, parser, models, schemas, db, curriculum_importer, ai_advisor) đều phải dùng path mới.

### 3.4c Code dead/legacy còn sót (sau Phase 4 cleanup)

Phase 4 (2026-05-05) đã DROP hầu hết dead code:
- ✅ Hệ Notification v1 (`/system-notifications*`) — XOÁ HẲN
- ✅ Hệ admin↔SV messaging cũ (`/admin/messages/*`, `UserMessage`) — XOÁ
- ✅ Models `LearningContract`, `ContractCheckin`, `SkillResource`, `RiskCase` — XOÁ + 10 bảng orphan DB
- ✅ Cột users dead: `career_skills`, `career_goal`, `max_credits_per_term`, `difficulty_preference`, `google_sub`, `email_edu`, `email`, `is_head_of_department`, `grades_locked`, `official_earned_credits` — XOÁ
- ✅ Endpoints: `/auth/google`, `/me/career-skills` GET/PUT, `/admin/grades/import`, `/admin/users/{id}/grades`, `/admin/reports/graduation`, `/admin/users/{id}/grades-lock`, `/admin/advisors/{id}/transfer-head`, `/auth/forgot-password*`, `/auth/reset-password`, `/auth/me/setup-account` — XOÁ

Còn sót (low priority):
- 5 Pydantic schema orphan trong `schemas.py`: `CourseWithGroupOut`, `BulkOfferingIn`, `ActiveSemesterIn`, `NotificationListItem`, `GradesImportError`. Khai báo nhưng 0 caller. Có thể xoá khi rảnh.

→ Khi sửa code, **không thêm caller mới cho các orphan này**.

### 3.5 Trạng thái sau refactor 2026-05-05 (6 phases)

Cùng 1 ngày 2026-05-05 đã đẩy 6 đợt refactor lớn. Memory file
`memory/project_eduguide_state.md` ghi đầy đủ commit-by-commit.

#### Phase 1 — ClassGroup model + Email recovery + Reviews moderation (DONE)
- [x] Thêm bảng `class_groups` (Lớp sinh hoạt, GVCN bắt buộc)
- [x] DROP `users.is_head_of_department` — concept "Trưởng bộ môn" bỏ
- [x] Thêm `users.class_group_id` (SV thuộc 1 lớp, ON DELETE SET NULL)
- [x] Thêm `course_ratings.hidden/hidden_by/hidden_at` cho admin moderation
- [x] 9 endpoint mới: `/admin/classes/*` (CRUD + import) + `/admin/reviews/*` (list/hide/restore)
- [x] Frontend: tab "Lớp sinh hoạt" + tab "Đánh giá môn học" trong admin.html

#### Phase 2 — Bỏ admin grades import (DONE)
- [x] DROP `POST /admin/grades/import`, `PATCH /admin/users/{id}/grades-lock`
- [x] DROP cột `user_grades.source`, `users.grades_locked`, `users.official_earned_credits`
- [x] Đơn giản hoá `POST /grades/upload`: full replace mỗi lần, không merge admin/self
- [x] `/grades/me/status`: luôn `can_upload=True`

#### Phase 3 — Admin = quản lý tài khoản + thông báo (DONE)
- [x] DROP `GET /admin/reports/graduation`, `GET /admin/users/{id}/grades`
- [x] Dashboard stats: bỏ `at_risk_students`, `thesis_eligible`, `overdue warning`, `avg_gpa`
- [x] admin.html: bỏ cột GPA + TC trong table SV, bỏ filter "Quá hạn", bỏ button "Xem bảng điểm"
- [x] Disclaimer banner "EduGuide là tool cá nhân, không thay thế SIS"

#### Phase 4 — DB cleanup (DONE)
- [x] DROP 11 bảng orphan: `user_quiz_results`, `career_journeys`, `journey_milestones`, `case_actions`, `case_comments`, `risk_history`, `learning_contracts`, `contract_checkins`, `skill_resources`, `user_messages`, `risk_cases`
- [x] DROP 7 cột users dead: `career_skills`, `career_goal`, `max_credits_per_term`, `difficulty_preference`, `google_sub`, `email_edu`, `email`
- [x] DROP endpoint `POST /auth/google`, `/me/career-skills` GET/PUT
- [x] Đơn giản hoá `UserProfileIn/Out`: chỉ còn `target_gpa`

#### Phase 5 — UX consistency với app-core.js (DONE)
- [x] Tạo `frontend/pages/app-core.js` (18KB) — `App.api/toast/modal/loading/showEmpty/showError`, debounce/throttle
- [x] Backward-compat shims: `window.callApi`, `window.toast`, `window.showToast`, `window.escHtml`
- [x] 12/12 page load `app-core.js`, KHÔNG còn local `function toast/showToast/callApi`

#### Phase 6 — Bỏ first-login setup + email cá nhân (DONE)
- [x] DROP 4 endpoint: `/auth/me/setup-account`, `/auth/forgot-password`, `/auth/forgot-password-edu`, `/auth/reset-password`
- [x] DROP cột `users.email`, bảng `password_reset_tokens`, model `PasswordResetToken`
- [x] DROP 5 Pydantic schema: `SetupAccountIn`, `ForgotPasswordIn`, `ResetPasswordIn`, `ForgotPasswordEduIn`, `ForgotPasswordEduOut`
- [x] DROP frontend `reset-password.html` + modal `setupModal` + `forgotModal` + JS handlers
- [x] Login response: `require_setup` luôn `False` (kept for backward compat)
- [x] Workflow đổi pw mới: SV vào Settings → Change Password; SV quên pw → liên hệ admin → admin reset thủ công

### 3.6 Pending khi resume

**A. Cần test thực tế trên Chrome** (priority cao):
1. Admin login → tab "Lớp sinh hoạt" → CRUD + import file Excel `data/demo/lop/bulk_import.xlsx`
2. Admin tab "Đánh giá môn học" → filter + hide/restore
3. Login page → bỏ button "Quên mật khẩu" → text "Liên hệ admin" hiển thị đúng
4. SV login → vào thẳng app (không bị redirect setup modal)
5. Verify `advisor.html` không lỗi sau text rename "Bộ môn" → "Chuyên ngành" + "Trưởng BM" → "GVCN"
6. Demo data đã có 6 lớp K66 + 30 SV — sẵn sàng test ngay (nếu cần reset: `python -m backend.scripts.generate_demo_data --reset`)

**B. Optional polish**:
- Pagination cho admin reviews nếu nhiều review
- Filter "GVCN dropdown" cho tab Lớp (filter theo GVCN cụ thể)
- Bulk-action UI cho reviews (ẩn nhiều cùng lúc)
- Xoá 5 Pydantic schema orphan còn sót (low priority)

**C. Known issues**:
- `migrate.py` block "2026-05-05" có Unicode encoding error trên Windows console nhưng migration vẫn apply qua `python -c`
- `CLAUDE.md` (file này) đã updated 2026-05-05 sau Phase 6 — nếu thấy phần nào còn nhắc Trưởng BM / setup-account / email recovery → là chưa đồng bộ, báo ngay

---

## 4. Quy tắc làm việc

### 4.1 Cách Claude Code được giao việc

**Từ 2026-04-23:** User gửi **SPEC (đặc tả)**, không phải code chi tiết.

Spec mô tả:
- Mục tiêu (1 câu)
- Bối cảnh (tình trạng hiện tại)
- Yêu cầu (behavior mong đợi)
- Ràng buộc (không đụng gì)
- Cách test

**Claude Code TỰ QUYẾT:**
- Tên function, biến
- Cách tổ chức code
- CSS class, thuật toán
- Cấu trúc file

**Claude Code KHÔNG tự ý:**
- Đổi tên file/bảng đã có
- Refactor code đang chạy tốt
- Thêm dependency mới
- Bỏ tính năng đang dùng

### 4.2 Khi được yêu cầu làm tính năng mới:
1. Đọc `docs/PHAN_TICH_THIET_KE.md` để hiểu schema + nghiệp vụ
2. Kiểm tra route đã tồn tại chưa (xem section 3.1)
3. Nếu đã có → chỉ sửa/bổ sung, không viết lại
4. Nếu chưa có → thêm mới, không xóa route cũ
5. Đọc memory `memory/project_eduguide_state.md` để biết phase nào đã clean những gì

### 4.3 Khi sửa `academic_engine.py`:
- Ngưỡng TN: `_DEFAULT_GRADUATION_THRESHOLD = 153.0` — **KHÔNG đổi**
- Quy tắc TC: xem `CTDT_CHUAN.md`
- Không xóa function đang được import trong `main.py` hoặc `chat_assistant.py`

### 4.4 Khi thêm route mới vào `main.py`:
- Đặt theo nhóm (advisor routes gần nhau)
- Luôn thêm authentication dependency (`_require_admin`, etc.)

### 4.5 Khi sửa database:
- Thêm migration vào `migrate.py`
- Cập nhật `models.py` và `schemas.py` đồng thời
- Không đổi tên cột/bảng đang có (breaking change)

### 4.6 Sau khi sửa code:
- Chạy `pytest -v`
- Báo kết quả cụ thể: "X/X tests pass" hoặc liệt kê test FAIL

### 4.7 Không làm:
- Không xóa hoặc rename file đang có
- Không refactor khi không được yêu cầu
- Không đổi tech stack
- Không tự thêm dependency
- Không dùng localStorage/sessionStorage trong component

---

## 5. Thông tin kỹ thuật quan trọng

### 5.1 Hằng số:
```python
_DEFAULT_GRADUATION_THRESHOLD = 153.0
INTERNSHIP_REMAINING_BUFFER = 6.0
```

### 5.2 Giới hạn TC/kỳ theo GPA:
```
GPA >= 3.6  → max 25 TC/kỳ
GPA >= 2.5  → max 22 TC/kỳ
GPA < 2.5   → max 18 TC/kỳ
```

### 5.3 Upload matching rule:
```
1. Match course_code trước
2. Fallback: match course_name (lowercase + trim)
3. Không khớp → "Môn lạ" (amber color)
4. Môn không hợp lệ không tính vào tiến độ CTĐT
```

### 5.3a Phân lớp can thiệp CTĐT cho admin (chốt 2026-04-25):

Admin có **3 lớp** thao tác trên CTĐT, phân theo mức rủi ro:

**Lớp 1 — Vận hành (sửa inline thoải mái, không cần Import):**
- HK chuẩn của môn (1-9) — popup HK ở list view + input ở side panel
- Tiên quyết — `+/×` ngay tại row list
- Mô tả môn — modal Sửa
- Flag `count_toward_credits` (Tính TC tích lũy / Không tính)

**Lớp 2 — Cấu trúc CTĐT (CHỈ qua Import CTĐT chuẩn, UI khoá read-only):**
- Mã môn, Tên môn, Số TC
- Chuyên ngành áp dụng (`required_specialization` + bảng M2M `course_specializations`)
- Nhóm tự chọn (BB / TC-A / TC-B / TC-C) + TC tối thiểu mỗi nhóm
- → Modal "Sửa môn" disable các field này khi mode Edit + banner nhắc Import. Side panel hiện CN dạng badges read-only.
- Khi mode "Thêm môn mới" thì vẫn cho gõ tay (cần thiết khi DB rỗng).

**Lớp 3 — Cấu hình hệ thống (sửa có audit log + xác nhận, ở tab Nhật ký):**
- `graduation_credit_threshold` — ngưỡng TC tốt nghiệp (mặc định 153.0)
- `internship_min_credits` — ngưỡng TC đi thực tập DN (mặc định 90.0)
- `thesis_min_credits` — ngưỡng TC làm ĐATN (mặc định 130.0)
- `thesis_min_gpa4` — ngưỡng GPA hệ 4 làm ĐATN (mặc định 2.0)
- `active_semester` — kỳ học hiện hành
- Endpoints: `GET/PUT /admin/config/graduation-threshold`, `GET/PUT /admin/config/academic-thresholds`

**KHÔNG cho admin sửa:** thang quy đổi 10→4, công thức GPA, quy tắc học lại = max — đây là quy chuẩn Bộ GD, fix-code only.

### 5.4 Quy tắc tính điểm & GPA (xác nhận 2026-04-25 từ 2 bảng điểm thực tế K21):

**Thang quy đổi 10 → 4 → letter (chuẩn Bộ GD):**
```
≥ 9.0  → A+ (4.0)
8.5–8.9 → A  (3.7)
8.0–8.4 → B+ (3.5)
7.0–7.9 → B  (3.0)
6.5–6.9 → C+ (2.5)
5.5–6.4 → C  (2.0)
5.0–5.4 → D+ (1.5)
4.0–4.9 → D  (1.0)
< 4.0   → F  (0)   — KHÔNG pass
```
Pass khi `score4 ≥ 1.0` (D, D+ vẫn đạt nhưng kéo GPA xuống).

**Công thức GPA (HK + tích lũy):**
```
GPA = Σ(score4 × credits) / Σ(credits)    # chỉ trên môn count_toward_credits
GPA10 = Σ(score10 × credits) / Σ(credits) # cùng nguyên tắc
```
Làm tròn 2 chữ số thập phân (round half up).

**Môn KHÔNG vào TC tích lũy + KHÔNG vào GPA:**
- **GDTC** 1/2/3: `7010701`, `7010702`, `7010703`
- **QPAN** — nhận biết bằng **mã bắt đầu `73`**:
  - Khóa 2021 (bảng điểm thực tế): `7300103`, `7300104`, `7300202`, `7300203` (4 môn, đặt HK1)
  - ver2.pdf (khóa mới): `7300101` (HK4), `7300102` (HK5), `7300201` (HK6) (3 môn)
- **Môn trượt** (F, score4 < 1.0)
- **Chuẩn đầu ra Đ/K** (`CDRTH`, `CDRNN`, `7010610` Tiếng Anh tăng cường):
  0 TC, kết quả "Đ"/"K", chỉ là điều kiện ra trường, không tham gia GPA.

**Học kỳ hè (HK3) — VẪN tính bình thường:**
- TC HK3 **VẪN** vào TC tích lũy, GPA **VẪN** tính như HK1/HK2 (đúng quy chế tín chỉ Bộ GD).
- Chỉ KHÔNG dùng HK3 để **ước lượng tốc độ học / dự đoán kỳ TN** (vì kỳ hè ngắn ~6 tuần, không phản ánh nhịp học chính). Xem `_graduation_estimate()` line 706 + streak tracker line 1531.

**Học lại = lấy điểm CAO NHẤT (KHÔNG phải mới nhất):**
- Verify từ bảng điểm thực tế:
  - File 1: `7080111 Mã nguồn mở` HK1/2023 D (1.0) → HK1/2025 B+ (3.5) → cuối dùng **B+ (3.5)**.
  - File 2: `7080512 LTHĐT Java` HK2/2023 D (1.0) → HK1/2025 B (3.0) → cuối dùng **B**.
  - File 2: `7010602 TA2` F → C → dùng **C**.
- Chỉ tính 1 lần trong tổng TC tích lũy.

**Lưu ý "TC đạt HK"**: Bảng điểm có thể hiển thị 2 cách (1 cộng cả GDTC/QPAN, 1 trừ ra) tuỳ đời bản in. KHÔNG ảnh hưởng tới TC tích lũy tốt nghiệp — code chỉ cần đảm bảo TC tích lũy + GPA không bao gồm các môn loại trừ ở trên.

### 5.5 LLM chain:
```
Gemini 2.0 Flash → Groq llama-3.3-70b → Claude Haiku
```

### 5.6 Spec codes (6 CN CNTT):
```
7480201_07 — KHMT
7480201_06 — MMT
7480201_05 — CNPM
7480201_09 — HTTT
7480201_04 — THKT
7480201_08 — CNTTDH
```

### 5.7 Notifications target types:
```
all              — Toàn hệ thống
all_students     — Tất cả SV
all_advisors     — Tất cả GV
cohort           — SV theo khóa (K21,K22...)
specialization   — SV theo CN (7480201_07...)
students         — SV cụ thể (mã SV,mã SV...)
advisors         — GV cụ thể (KHMT001,MMT001...)
department       — GV theo bộ môn
```

### 5.8 Tài khoản demo (sau `python -m backend.scripts.generate_demo_data --reset`):

```
demo_admin           / Demo@2026   — admin
KHMT001              / Test1234!   — advisor (GVCN DCCTCT66_07A)
MMT001/CNPM001/HTTT001/THKT001/CNTTDH001 / Test1234!  — advisor (GVCN các lớp khác)
KHMT002/CNPM002/MMT002/GV001        / Test1234!  — advisor trợ giảng (không chủ nhiệm)
sv66001 ... sv66030  / Test1234!   — 30 SV (5/lớp × 6 lớp K66)
```

**Forgot password test** (nếu chưa restart sau Phase 6):
- KHÔNG còn endpoint self-service. SV liên hệ admin → admin reset qua `POST /admin/users/{id}/reset-password` → admin nhận pw mới + giao SV.

### 5.9 Phạm vi áp dụng cá nhân hóa & gợi ý (chốt 2026-04-30):

**Nguyên tắc gốc:** CTĐT của trường là **cố định, bắt buộc** — SV phải học hết các môn BB để đủ điều kiện tốt nghiệp, bất kể sở thích/định hướng nghề. **Hệ thống không "đề xuất" hay "không đề xuất" môn bắt buộc** — đó là quyết định của trường.

**Cá nhân hóa CHỈ áp dụng cho môn tự chọn** (TC-A / TC-B / TC-C) — nơi SV thực sự có quyền chọn. Đây là phạm vi duy nhất gợi ý/recommendation/career-fit có ý nghĩa.

**Implication cho từng feature:**

| Feature | Môn bắt buộc (BB) | Môn tự chọn (TC-A/B/C) |
|---------|-------------------|------------------------|
| `/recommendations/me` (gợi ý đăng ký kỳ tới) | List theo HK chuẩn + tiên quyết — **KHÔNG rerank theo skill/career** | **Rerank theo skill match với nghề + ML score** |
| `/recommendations/why-not/{code}` | "Đây là môn bắt buộc trong CTĐT — bạn phải học để đủ TC tốt nghiệp" | "Không phù hợp vì: thiếu skill X, sai CN, ..." |
| Skill tree (SV) | Skill từ BB pass đóng góp (vì có học thật) | Skill từ TC pass đóng góp |
| Career fit score | Tính trên skill từ TẤT CẢ môn pass (BB + TC) | Tính trên skill từ TẤT CẢ môn pass (BB + TC) |
| Skills mapping (admin) | Cần map (để tính skill tree) | Cần map (để tính skill tree + rerank gợi ý) |
| Roadmap kế hoạch chuẩn | Hiển thị toàn bộ BB + slot TC theo nhóm | SV chọn TC nào lấp slot — đây là chỗ admin/advisor có thể nói chuyện |
| What-if simulator | Cho thử cả BB lẫn TC để xem dự kiến TC/GPA | (như BB) |

**Tóm tắt:** Skills mapping ở admin **vẫn cần thiết cho cả BB và TC** (vì skill tree tính trên cả 2). Nhưng **logic recommendation cá nhân hóa chỉ filter/rerank các môn TC**, không đụng vào BB.

**Khi audit code recommendation:** nếu thấy BB bị filter ra theo skill/career match → đó là bug. BB phải luôn xuất hiện đầy đủ theo HK chuẩn + tiên quyết.

---

## 6. Pattern lỗi đã fix (GHI NHỚ)

- **innerHTML không chạy script:** fragment chỉ HTML+CSS, JS ở host page
- **Redirect loop:** backend `/auth/login` trả role, frontend decode JWT
- **Floating point 9.1000001:** `round(,2)` backend + `fmtScore()` frontend
- **Port 8000 CLOSE_WAIT:** kill + restart + `pool_pre_ping=True`
- **Advisor UNIQUE assignments:** check exists trước insert
- **PostgreSQL path:** fix `db.py` path `.parent.parent` → `.parent.parent.parent`
- **Upload điểm race condition:** throttle max 5 request
- **Mật khẩu mất:** checkbox ép xác nhận + Copy all + CSV export
- **Sidebar flash trắng khi reload (2026-05-02):** `html::before` pseudo-element reserve 240px dark navy strip — render-blocking CSS giữ vùng sidebar đậm trước khi JS mount
- **Animation replay gây jitter khi full reload (2026-05-02):** `.fade-up*` mặc định instant; chỉ animate khi `html[data-first-visit="true"]` (set 1 lần/session qua `sessionStorage.eduguide_visited`)
- **`tailwind.config = ...` inline duplicate 14× page (2026-05-02):** consolidate vào `theme.js`, mọi token map sang CSS vars để dark mode auto-flip cho cả markup cũ
- **`Mã CN '7480201_07' không hợp lệ` ở edit modal (2026-05-02):** `_IMPORT_VALID_SPECIALIZATIONS` chứa legacy Vietnamese names thay vì canonical codes
- **Workflow upload thứ tự (Phase 1):** GV → Lớp → SV bắt buộc tuần tự (FK constraint enforce). Đảo ngược → import SV reject "Lớp chưa tồn tại"
- **`migrate.py` Unicode error trên Windows console (Phase 4):** Migration block 2026-05-05 in console crash do encoding cp1252; vẫn apply được qua `python -c "open('migration.sql').read()"`
- **`is_head_of_department` còn sót ở frontend banner (Phase 1 follow-up):** Sau khi DROP cột → frontend còn check field này → banner đỏ "Chuyên ngành X chưa có GVCN" no-op. Replace `a.is_head_of_department` → `((a.class_count||0) > 0)`

---

## 7. Cách hỏi khi không chắc

Hỏi trước khi code:
- "Tôi định làm X — có ổn không?"
- "Route Y đã có chưa hay cần thêm mới?"
- "Logic này đúng với CTDT_CHUAN.md không?"

Tốt hơn hỏi 1 phút còn hơn code sai rồi phải sửa lại.

---

## 8. Thời gian còn lại (deadline bảo vệ ~3 tuần)

### Ưu tiên:
1. Test thủ công 3 role + các luồng chính (section 3.6)
2. Verify ClassGroup workflow + Reviews moderation (Phase 1 features mới)
3. Viết báo cáo 6 chương (~2 tuần)
4. PowerPoint + luyện demo (~3 ngày)

### Không làm:
- Không thêm tính năng mới ngoài danh sách
- Không refactor lớn nữa (đã 6 phase 2026-05-05 rồi)
- Không đổi database engine
- Không re-design UI khi đã có
- Không khôi phục concept "Trưởng bộ môn" / "Setup-account" / "Forgot password self-service" (đã quyết bỏ)
