# EduGuide — Demo Flow cho Bảo vệ Đồ án

**Tổng thời gian**: 15-20 phút demo + 5 phút Q&A
**Mục tiêu**: Map qua MỌI chức năng chính của hệ thống theo flow tự nhiên (không nhảy ngẫu nhiên)
**Ngày cập nhật**: 2026-05-04

---

## 📋 Pre-demo checklist (5 phút trước thuyết trình)

```
[ ] Backend chạy:    uvicorn backend.main:app --reload --port 8000
[ ] Frontend chạy:   python -m http.server 5500 --directory frontend/pages
[ ] DB seeded:       SV K14 + advisor + admin (mặc định đã có)
[ ] Hard-refresh:    Ctrl+Shift+R trên tab demo
[ ] DevTools:        ĐÓNG (đừng cho thấy console errors)
[ ] Network tab:     Throttling = "No throttling"
[ ] Browser zoom:    100% (Ctrl+0)
[ ] Window size:     Maximized 1440x900+
[ ] Mic check:       OK
[ ] Slide intro:     Sẵn sàng (architecture diagram)
```

### Test accounts

| Role | Username | Password | Note |
|---|---|---|---|
| **Admin** | `demo_admin` | `Demo@2026` | Toàn quyền |
| **Advisor (Trưởng BM KHMT)** | `KHMT001` | `Test1234!` | Quản lý sv22001, sv24002 — head BM KHMT |
| **Sinh viên** | `sv22001` | `Test1234!` | Lê Hoàng Xuất Sắc — top student K22, đủ TC TN |

> Tất cả seed bởi `python -m backend.scripts.generate_demo_data --reset` — xem `data/demo/README.md`.

### Backup nếu lỗi

- Nếu LLM rate limit → demo phần khác trước, quay lại sau (quota reset 60-90s)
- Nếu prefetch không kịp → đợi 1-2 giây giữa các nav
- Nếu modal không mở → F5, click lại

---

## 🎬 Phase 0 — Mở đầu (2 phút)

### Slide intro:
> *"EduGuide là hệ thống quản lý lộ trình học tập + tư vấn nghề cho sinh viên CNTT,*
> *gồm 3 vai trò: Sinh viên / Cố vấn / Quản trị viên.*
>
> *Tech stack: FastAPI + PostgreSQL + AI integration (Gemini, Groq) + vanilla HTML/JS frontend.*
>
> *Em chọn architecture multi-page với View Transitions API cho phía SV*
> *(zero race condition), single-page tabs cho Admin/Cố vấn (CRUD-heavy).*
>
> *Em sẽ demo một flow thực tế: SV năm 3 chuyên ngành KHMT lập kế hoạch kỳ tới."*

---

## 🎬 Phase 1 — Demo as ADMIN (5 phút)

### 1.1. Login
- Mở `http://127.0.0.1:5500/frontend/pages/index.html`
- Username: `demo_admin` · Password: `Demo@2026` · Click "Đăng nhập"

**EXPECT**: redirect tới `admin.html`, sidebar trái có "Admin Demo · QUẢN TRỊ VIÊN"

---

### 1.2. Tab Tổng quan (Dashboard)

**Show**:
- 5 stat cards (SV chưa đăng nhập / Tổng SV / Cố vấn / Môn / SV chưa có CV) — clickable
- 2 charts: Cohort bar (K14, K15...) + Spec doughnut (KHMT, MMT, CNPM...)
- System warnings (nếu có)
- Recent activity log

**Defense moment**: 
> *"Dashboard cho admin overview tức thời. 5 KPI clickable → quick-jump. Charts dùng Chart.js."*

---

### 1.3. ⭐ B2: Báo cáo tốt nghiệp (highlight)

- Cuộn xuống cuối Dashboard tab → section **"🎓 Báo cáo tốt nghiệp"**
- Filter: Khoá `K14` · CN `KHMT` · TC tối thiểu `100`
- Click **"Xem trước"** → preview table 100 dòng đầu
- Click **"📥 Tải CSV (Excel)"** → file `graduation_report_*.csv` download
- Mở Excel → 13 cột tiếng Việt rõ ràng

**Defense moment**:
> *"Phòng đào tạo cần báo cáo SV đủ điều kiện tốt nghiệp. EduGuide tự động export với BOM UTF-8 → Excel mở chuẩn tiếng Việt. Tích hợp với quy trình thực tế."*

---

### 1.4. Tab Môn học — B7: Sửa mô tả môn

- Click sidebar **"Môn học"**
- Filter spec = `KHMT` → bảng courses của KHMT
- Click row môn **"Cấu trúc dữ liệu và giải thuật"** (7080206)
- (HOẶC click button **"✏️ Sửa"** ở cuối row — visible button mới sau UX cleanup)

**EXPECT**: Side panel slide từ phải, header "7080206 · Cấu trúc dữ liệu và giải thuật"

- Click tab **"Nội dung"** trong panel
- **EXPECT**: textarea với mô tả hiện tại + button "Quản lý kỹ năng môn này dạy"
- Edit thêm 1 câu vào mô tả → Click **"Lưu"** ở dirty bar
- **EXPECT**: Toast "Đã lưu thay đổi"

**Defense moment**:
> *"Mô tả môn em generate baseline bằng kiến thức CNTT chuẩn (150 môn). Admin có thể curate qua tab Nội dung. Trước đây feature này bị giấu sâu — em đã thêm button 'Sửa' visible cho mỗi row sau audit UX."*

---

### 1.5. Tab Sinh viên — Bulk action + Empty state

- Sidebar **"Sinh viên"**
- Filter: Cohort `K14` → bảng update real-time
- Tích checkbox 2 SV
- **EXPECT**: Bulk bar floating ở dưới: 
  ```
  ┌─ Tác vụ hàng loạt ──┐  [🔒 Reset MK] [📢 Gửi TB] [📥 Xuất CSV] [🗑 Xoá]
  │  2 SV đã chọn       │
  └─────────────────────┘
  ```
- Click **"📥 Xuất CSV"** → file download, tích chọn được giữ
- (Demo empty state) Search "xxx_không_có" → bảng empty
- **EXPECT**: 2 CTA buttons "Xoá filter" + "Thêm SV mới"

**Defense moment**:
> *"Bulk action với 7 filters + scope label rõ ràng. Empty state có CTA cụ thể, không bao giờ để user stuck."*

---

### 1.6. Tab Cố vấn — Surface bulk menu

- Sidebar **"Cố vấn học tập"**
- **EXPECT**: 3 buttons inline (sau UX cleanup):
  - 🤖 **Phân loại tự động** (theo bảng điểm)
  - ✨ **Auto-assign theo lớp**
  - 📤 **Import phân công** (CSV/Excel)
- Hover từng button → tooltip giải thích
- Show grouped sections theo bộ môn (KHMT/MMT/CNPM...)
- Show advisor "Trưởng BM" badge có

**Defense moment**:
> *"Trước đây 3 actions này bị giấu trong dropdown 1 button. Audit UX phát hiện → surface ra ngoài cho discoverable."*

---

### 1.7. Tab Thông báo (skip nếu thiếu thời gian — 30s)

- Click **"+ Tạo thông báo"** topbar
- Show form: Title + Severity (info/warn/urgent) + 8 target options
- "Estimate reach" trước khi gửi
- Đóng modal (không gửi)

**Defense moment**:
> *"Target audience filter 8 loại — broadcast cả khoá hoặc 1 SV cụ thể."*

---

## 🎬 Phase 2 — Demo as STUDENT (8 phút — main story)

### 2.1. Logout + Login SV
- Logout (avatar dropdown → Đăng xuất)
- Login `sv22001` / `Test1234!`

**EXPECT**: home.html với:
- Greeting "Chào, Bình!" + emoji
- 3 KPI cards (TC, GPA, Career Fit)
- **Card "Gợi ý đăng ký kỳ tới"** với 5 môn + match score
- Mục tiêu nghề (đã chọn)
- Sidebar trái với widget **"CỐ VẤN CỦA BẠN: Lê Thành Long"** (A3) + nút "Nhắn tin nhanh"
- Bell icon góc trên-phải có badge unread
- **FAB tròn góc dưới-phải** (floating chat)

---

### 2.2. ⭐ Demo navigation smoothness

- Click sidebar **"Lộ trình"** → page chuyển fade smooth
- Click sidebar **"Bảng điểm"** → tương tự
- Click sidebar **"Mục tiêu nghề"** → tương tự
- Quay về sidebar **"Tổng quan"**

**Quan sát**:
- Sidebar **đứng yên hoàn toàn** (view-transition-name `app-sidebar`)
- Main content fade nhẹ 0.18s
- Các lần click sau → instant (đã prefetch)

**Defense moment**:
> *"View Transitions API + persistent layout shell — sidebar đứng yên, chỉ main fade. Browser-native, không cần SPA framework."*

---

### 2.3. ⭐ Click suggestion → auto-open course modal

- Trên home, click **1 môn** trong "Gợi ý đăng ký kỳ tới" (vd "Trí tuệ nhân tạo + BTL")
- **EXPECT**: 
  - Auto-navigate đến `integrated-roadmap.html?focus=7080122`
  - Sau init, modal course detail tự mở
  - Header: "Trí tuệ nhân tạo + BTL · 7080122 · 3 TC · BB · HK6"
  - **Mô tả môn** (1 đoạn ngắn hard-coded)
  - Hint box: *"Bấm Hỏi AI để biết kỹ năng đạt được"*
  - 3 buttons: 🟢 Hỏi cố vấn / 🟣 Hỏi AI / Đóng

**Defense moment**:
> *"Deep-link `?focus=` từ home → roadmap. Description hard-coded cho 150 môn (em viết dựa kiến thức CTĐT chuẩn) — tiết kiệm AI token. Skills lazy-load qua nút 'Hỏi AI'."*

---

### 2.4. ⭐ B1: Hỏi AI (RAG course_info)

- Click **"Hỏi AI"** trong modal
- **EXPECT**: 
  - Modal đóng
  - FAB panel mở sang **tab AI**
  - Câu hỏi prefilled: *"Cho em biết thêm về môn 'Trí tuệ nhân tạo + BTL' (mã 7080122)..."*
- Click Send (button paper plane)
- **EXPECT**:
  - Typing indicator
  - AI trả lời CỤ THỂ về môn này (không generic) vì backend dùng RAG context từ DB

**Defense moment**:
> *"Khi user hỏi về môn cụ thể, backend `chat_assistant.py` extract course_code → query DB lấy description + skills (joined với category) → pass vào LLM context. AI trả lời dựa trên CTĐT thật của trường, không phải kiến thức GPT generic. Đây là pattern Retrieval-Augmented Generation."*

---

### 2.5. ⭐ A3: Sidebar widget Cố vấn

- Cuộn xuống cuối sidebar → widget **"CỐ VẤN CỦA BẠN"**
- Show: Avatar "LT" + "Lê Thành Long" + "Trưởng bộ môn · KHMT001"
- Click **"💬 Nhắn tin nhanh"**
- **EXPECT**: FAB panel mở sang **tab Cố vấn** + thread DM với advisor

**Defense moment**:
> *"Widget sidebar hiện cố vấn của SV mọi page. localStorage cache để tránh layout shift khi nav."*

---

### 2.6. ⭐ A6: AI risk + bảng điểm với rating

- Sidebar **"Bảng điểm"**
- **EXPECT**: 
  - 4 KPI cards (TC tích lũy / GPA / Đã pass / Đang học)
  - Tab "Đã học" active với 18 môn (badge "Đã xác thực" xanh)
  - Banner xanh **"✓ Bảng điểm chính thức (đã xác thực) · 18 môn"**
- Hover 1 row → cursor pointer + tooltip "Click để đánh giá môn này"
- **Click row môn "Cấu trúc dữ liệu và giải thuật"**
- **EXPECT**: Modal rating mở
  - 5-star selector
  - Textarea nhận xét công khai
  - Toggle ẩn danh
  - Toggle góp ý cho admin
- Chọn 4 sao + nhập "Môn dễ hiểu, GV nhiệt tình" + Save
- **EXPECT**: Toast "Đã đánh giá thành công"

---

### 2.7. ⭐ A5: Per-term "Trao đổi"

- Trong tab "Đã học", mỗi học kỳ có header:
  ```
  HK1 - Năm học 2022-2023  6 môn · 12 TC · GPA 3.45  [💬 Trao đổi] [Học kỳ chính]
  ```
- Click **"💬 Trao đổi"** ở 1 kỳ
- **EXPECT**: FAB advisor tab mở + prefill *"Em muốn trao đổi với cô về HK1 - Năm học 2022-2023 (GPA 3.45)..."*

---

### 2.8. ⭐ A1 + Group view: Tab "Chưa học"

- Click tab **"Chưa học"**
- **EXPECT**: Group sections rõ ràng (sau A1 fix):
  ```
  📘 BẮT BUỘC ĐẠI CƯƠNG · 5 môn · 12 TC          5/5 đủ điều kiện
     7080112  Nguyên lý Hệ điều hành     2 TC  HK3  ✓ Đủ điều kiện
     ...
  
  🎓 CƠ SỞ NGÀNH KHMT · 8 môn · 24 TC             6/8 đủ điều kiện
     ...
  
  🎚 TỰ CHỌN A · 3 môn · 9 TC                     3/3 đủ điều kiện
     ...
  ```

**Defense moment**:
> *"Trước flat list 50 môn — khó scan. Em group theo block CTĐT (BB / CN / TC-A/B/C / GDTC) với count + sort theo HK chuẩn."*

---

### 2.9. ⭐ Workflow upload điểm + merge logic

- Click **"Upload bảng điểm"** (button trong banner hoặc empty state)
- Modal mở
- Drop file Excel test (có sẵn trong `data/demo/`)
- Click "Xác nhận lưu"
- **EXPECT**: Toast: 
  > *"Cập nhật điểm thành công · 6 môn được lưu · 18 môn giữ bản xác thực"*
- Banner cập nhật: **"✓ Đã xác thực 18 môn · ⚠ 6 môn tự khai"** (màu xanh dương)

**Defense moment** (long form — đây là feature kỹ thuật lớn):
> *"Đây là workflow merge thông minh.*
> *Trước đây: admin import → SV bị khoá vĩnh viễn. Vấn đề: kỳ sau SV không upload được.*
> *Em fix: SV luôn upload được, hệ thống merge — môn đã admin verify thì giữ nguyên (skip silent), môn mới insert as 'self'. Kỳ sau admin import → 'self' tự bị thay bằng 'admin'.*
> *Gọi là pattern Optimistic UI + Source-of-truth reconciliation. Cố vấn chỉ tin source 'admin'."*

---

### 2.10. Mục tiêu nghề (career-goal)

- Sidebar **"Mục tiêu nghề"**
- **EXPECT**: 
  - Hero strip với spec KHMT
  - 6 career path cards (AI Engineer / Data Scientist / Backend / ...)
  - Career đang chọn highlight với border + badge fit %
- Click 1 career card (vd "AI/ML Engineer")
- **EXPECT**: Modal detail với tabs:
  - Mô tả tổng quan
  - Hard skills + Soft skills (todo list checkbox)
  - Lộ trình recommended
  - Cảnh báo (skill gap)
- Soft skills section có **link YouTube hợp lệ** (sau fix Rick Roll)
- Footer: 🟢 **"Trao đổi với cố vấn"** (A4) + "Đóng" + "Chọn nghề này"

**Defense moment**:
> *"6 nghề CNTT phổ biến với skill mapping. Career fit % tính bằng cosine similarity giữa skill SV đã học và skill nghề yêu cầu."*

---

### 2.11. Trợ lý AI (full-screen mode)

- Sidebar **"Trợ lý AI"**
- **EXPECT**: 
  - Hero "Chào, [tên]! Tôi có thể tư vấn..."
  - 4 chips: "Gợi ý môn kỳ sau" / "Tiến độ" / "TC còn lại" / "Định hướng"
  - Sidebar list threads (nếu có)
- Click chip "Gợi ý môn kỳ sau"
- Send → AI response thực tế dùng `/chat/me`

---

### 2.12. Hỏi cố vấn (messaging)

- Sidebar **"Hỏi cố vấn"**
- **EXPECT**: 
  - List conversations bên trái
  - Click advisor → thread DM mở
- Send tin "Em muốn đăng ký môn AI kỳ sau"
- **EXPECT**: Tin xuất hiện ngay trong thread

---

### 2.13. Thông báo

- Sidebar **"Thông báo"**
- **EXPECT**: 
  - Filter pills: severity / target / status
  - List notifications từ admin (broadcast)
  - Badge "1" trên sidebar nav giảm sau khi mark read

---

## 🎬 Phase 3 — Demo as ADVISOR (3 phút)

### 3.1. Logout + Login advisor
- Logout
- Login `KHMT001` / `Test1234!`

**EXPECT**: `advisor.html` với section "Tổng quan" mặc định

---

### 3.2. Cần chú ý

- **EXPECT**:
  - 4 stat cards (Tổng SV / Cao rủi ro / Cần lưu ý / Bình thường)
  - Group avg GPA + completion %
  - Alert strip với SV high-risk
- Click 1 SV trong alert

---

### 3.3. ⭐⭐ A6: AI Risk Analysis (signature feature)

- Trong modal SV detail, tab "Tiến độ" mặc định
- Cuộn xuống thấy card gradient indigo:
  ```
  ┌─────────────────────────────────────────────┐
  │ 🧠 Phân tích AI rủi ro học tập  [Phân tích AI]│
  │                                              │
  │ Bấm "Phân tích AI" để AI đánh giá chi tiết...│
  └─────────────────────────────────────────────┘
  ```
- Click **"Phân tích AI"**
- **EXPECT**: 
  - "AI đang phân tích dữ liệu học tập của SV..."
  - Sau ~5-10s:
    ```
    [Rủi ro CAO] [Độ tin cậy: cao]
    
    [Summary]: SV này đang giảm GPA mạnh, thiếu 30 TC...
    
    YẾU TỐ RỦI RO:
    ⚠ GPA giảm từ 3.2 (HK3) xuống 2.4 (HK5)
    ⚠ Đã trượt môn cốt lõi "Cấu trúc DL" 2 lần
    ⚠ Còn 30 TC, đang HK5 → khó đảm bảo tốt nghiệp đúng hạn
    
    HÀNH ĐỘNG KHUYẾN NGHỊ:
    ✓ Hẹn SV gặp tuần sau, đánh giá lại lộ trình
    ✓ Khuyến cáo đăng ký lại Cấu trúc DL kỳ tới
    ✓ Giảm tải xuống 12 TC/kỳ thay vì 18 TC
    ```

**Defense moment** (signature):
> *"Hệ thống không chỉ rule-based threshold GPA. Backend `/advisor/students/{id}/risk-analysis`*
> *build context từ 5 nguồn: GPA trend chia 2 nửa kỳ, fail/retake count, thông tin tốt nghiệp, ghi chú cố vấn 5 gần nhất, current term performance.*
> *LLM (Gemini → Groq fallback) trả JSON structured: risk_level + summary + factors + recommendations + confidence.*
> *Em prompt LLM yêu cầu output strict JSON, parse + validate.*
> *Token economy: chỉ gọi khi advisor click button → tiết kiệm budget."*

---

### 3.4. Sinh viên của tôi
- Sidebar **"Sinh viên của tôi"**
- Filter cohort `K14` + status chip "high_risk"
- Click row SV → modal detail (như trên)

### 3.5. Ghi chú tư vấn
- Sidebar **"Ghi chú tư vấn"**
- Show form tạo note + filter theo SV

### 3.6. Sơ đồ CTĐT (skip nếu thiếu thời gian)
- Sidebar **"Sơ đồ chuẩn"** — read-only DAG view

---

## 🎬 Phase 4 — Cross-role messaging real-time-ish (2 phút)

### Setup: 2 browser windows
- **Window 1**: sv22001 đang login, sidebar "Tổng quan", FAB visible
- **Window 2**: KHMT001 đang login, mở `messaging.html?with=<sv22001_id>`

### Flow
1. **Cố vấn** (W2) gõ tin: *"Em nên đăng ký 'Trí tuệ nhân tạo' kỳ tới"* + Send
2. **Sinh viên** (W1) — trong vòng 60s:
   - FAB tròn có badge đỏ "1"
   - Sidebar "Hỏi cố vấn" có badge "1"
3. SV click FAB → tab Cố vấn → tin hiện
4. SV reply: *"Em nghe theo cô, cảm ơn cô"*
5. Cố vấn (W2) thấy tin reply trong vòng 60s

**Defense moment**:
> *"Polling 60s — gần real-time mà không cần WebSocket overhead. Production có thể nâng SSE (Server-Sent Events). FAB có dual-tab AI + Cố vấn → SV không bao giờ cần rời page hiện tại để nhắn tin."*

---

## 🎬 Phase 5 — Q&A Defense Story (5 phút)

### Q1: *"Tại sao chọn FastAPI thay vì Django?"*
> FastAPI native async (handle nhiều concurrent request hiệu quả), OpenAPI docs tự sinh, validation Pydantic mạnh, perf cao hơn Django. Đường cong học tập dốc nhưng vừa với scope đồ án.

### Q2: *"Tại sao SV multi-page mà admin/advisor single-page?"*
> Architecture **fit-for-purpose**: SV pages có view phức tạp khác hẳn (DAG drag-drop, GPA simulator, full-screen AI chat) → MPA + View Transitions cho zero race condition + state leak. Admin/advisor là CRUD lists tương tự nhau → SPA tabs phù hợp. Ngay cả Facebook, GitHub, Linear cũng dùng hybrid như vậy.

### Q3: *"AI có thể trả lời sai không?"*
> Có. Em mitigate bằng:
> 1. **RAG cho course_info**: query DB lấy mô tả thực + skills → pass vào LLM context → giảm hallucination
> 2. **Fallback rule-based KB**: ~40 môn phổ biến hard-code, dùng khi LLM fail
> 3. **Token economy**: chỉ gọi LLM khi user explicit click (Hỏi AI / Phân tích AI), không auto-trigger
> 4. **Production**: cần human-in-loop review cho output cố vấn

### Q4: *"Workflow upload điểm SV vs admin?"*
> **Hai source coexist** với priority:
> - SV upload tạm cho kỳ chưa có điểm chính thức → `source='self'`
> - Admin import xác thực sau → `source='admin'`
> - **Merge logic**: môn đã có 'admin' thì self upload SKIP (không override), môn mới insert as 'self'
> - Cố vấn + báo cáo chính thức chỉ tin 'admin' source
> 
> Đây là pattern **Optimistic UI + Source-of-truth reconciliation** dùng trong Notion, Linear.

### Q5: *"Bảo mật?"*
> 1. **Authentication**: bcrypt hash password, JWT bearer token expire 24h
> 2. **Authorization**: mọi endpoint check role (student/advisor/admin) qua decorator
> 3. **Rate limiting**: failed login attempt counter (5 lần/30 phút)
> 4. **Audit log**: mọi admin action (UPDATE_COURSE, IMPORT_GRADES...) log vào DB
> 5. **CORS**: production refuse khởi động nếu thiếu CORS_ORIGINS env
> 6. **Input validation**: Pydantic schema cho mọi request body
> 7. **SQL injection**: SQLAlchemy ORM (parameterized queries)

### Q6: *"Scale từ 50 SV demo lên cả khoa 2000+ SV?"*
> Architecture stateless → scale horizontal dễ:
> - **DB**: Postgres index sẵn (cohort, role, course_code)
> - **API**: FastAPI workers (uvicorn --workers 4)
> - **Cache**: thêm Redis cho `/auth/me`, `/courses/catalog`, `/advisor/stats`
> - **AI**: đã có exponential backoff retry, có thể batch request

### Q7: *"Tại sao tự viết description thay vì để LLM generate?"*
> Em đã thử: 150 môn × LLM call = hết quota Gemini + Groq daily ngay buổi đầu. Generate AI tốn cost, chất lượng cũng không kiểm soát được. Em **viết tay 146 mô tả** dựa kiến thức CTĐT chuẩn → consistent style + có thể defend chính xác. Admin có thể curate sau qua UI.

### Q8: *"Tích hợp với hệ thống thật của trường?"*
> Tách interface qua:
> - **Postgres replicate** từ Oracle/MSSQL của trường (CDC tools)
> - **Roster import** qua CSV/Excel (chuẩn của VN, em đã code)
> - **CTĐT import** qua Word docx parser (em đã viết)
> - SSO: có thể tích hợp qua endpoint `/auth/sso` (không trong scope đồ án)

### Q9: *"Em làm trong bao lâu? Tỉ lệ AI-coded vs em viết tay?"*
> ~3 tháng full-time (12 tuần × 40h = 480h). 
> **AI-assist** (Claude Code): ~70% code (architecture decision, boilerplate, refactor).
> **Em viết tay**: 30% (business logic specific, prompt engineering, debug, UX decision).
> Em chịu trách nhiệm cho mọi dòng code — review từng PR, test E2E (55 tests).

### Q10: *"Nếu phải làm lại từ đầu, em sẽ thay đổi gì?"*
> 1. **Single-page hơn cho SV**: hiện 8 file, có thể merge 4 file chính (home/grades/roadmap/career) thành 1 SPA → smoother nav
> 2. **Real-time qua SSE/WebSocket** thay polling 60s
> 3. **Test coverage**: hiện 55 E2E mostly SV; cần thêm advisor + admin flows
> 4. **TypeScript** thay vanilla JS — type safety
> 5. **Component library** (shadcn-style) thay duplicate Tailwind classes

---

## 🛟 Backup plan nếu có lỗi giữa demo

### LLM rate limit (most common)
- **Symptom**: "Hỏi AI" hoặc "Phân tích AI" return error
- **Fix**: Skip phần đó, demo tiếp phần khác. Đợi 60s rồi retry.
- **Defense narrative**: *"Em dùng free tier — production sẽ paid để stable."*

### Backend cold start (lần đầu)
- **Symptom**: page load lâu, overlay loading hiển thị
- **Fix**: Đã có retry exponential backoff. Đợi 5-10s.

### View transitions không hoạt động
- **Symptom**: Sidebar nháy khi nav
- **Cause**: Browser quá cũ (Safari < 18 hoặc Firefox không enable)
- **Fix**: Demo trên Chrome/Edge mới nhất

### Database migration mới
- **Symptom**: Backend log có schema error
- **Fix**: `EDU_RUN_MIGRATIONS=1 uvicorn backend.main:app --reload` (1 lần đầu)

---

## 📊 Quick reference card (in ra giấy mang theo)

```
┌─────────────────────────────────────────┐
│ ADMIN: demo_admin / Demo@2026           │
│ ADVISOR: KHMT001 / 714526               │
│ STUDENT: sv22001 / Test1234!     │
├─────────────────────────────────────────┤
│ STORY: SV K14 KHMT lập kế hoạch kỳ tới   │
├─────────────────────────────────────────┤
│ HIGHLIGHTS (signature features):         │
│  ⭐ B7: Admin sửa mô tả môn              │
│  ⭐ B2: Báo cáo tốt nghiệp CSV          │
│  ⭐ A6: AI Risk Analysis (advisor)       │
│  ⭐ B1: RAG course_info (AI chat)        │
│  ⭐ A1+A3+A6: Messaging FAB dual-tab     │
│  ⭐ Workflow merge upload điểm           │
├─────────────────────────────────────────┤
│ TIMING: 2+5+8+3+2 = 20 phút              │
├─────────────────────────────────────────┤
│ IF FAIL → skip + continue, đừng dừng     │
└─────────────────────────────────────────┘
```

---

## 📝 Post-demo checklist

- [ ] Tắt backend (Ctrl+C)
- [ ] Tắt frontend
- [ ] Backup DB dump (nếu giảng viên cần xem code/data)
- [ ] Github repo public (nếu có)
- [ ] Slide.pdf có trong USB

---

**Chúc bạn bảo vệ thành công! 🎓**
