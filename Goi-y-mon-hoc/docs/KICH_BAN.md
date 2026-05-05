# Kịch bản sử dụng — đi qua MỌI chức năng EduGuide

Dùng bộ dữ liệu trong `data/demo/` (10 SV / 10 GV / 10 phân công + 10 file điểm).

**Setup 1 lần** (idempotent, ~30s):
```bash
python -m backend.scripts.generate_demo_data --reset
uvicorn backend.main:app --reload --port 8000
python -m http.server 5500 --directory frontend/pages   # tab khác
```
Login chung: mật khẩu `Test1234!` cho mọi user. Admin: `demo_admin / Demo@2025`.

---

## 🎬 Phần 1 — ADMIN (10-12 phút)

> **Thứ tự BẮT BUỘC**: GV (1.3) → SV (1.4) → Phân công (1.5) → Điểm (1.6).
> Nếu đảo ngược → bulk phân công sẽ báo "GV chưa tồn tại" vì hệ thống FK check.

### 1.1. Login + Tab Tổng quan
- Mở `http://127.0.0.1:5500/index.html` → login `demo_admin / Demo@2026`
- **EXPECT**: redirect `admin.html`, sidebar trái có "Quản trị viên", topbar breadcrumb "Quản trị › Tổng quan"
- Show 5 KPI cards (Tổng SV / Cố vấn / Môn / SV chưa CV / SV chưa login) — clickable
- 2 charts: cohort bar + spec doughnut
- **Defense moment**: *"Dashboard cho overview tức thời, KPI clickable → quick-jump."*

### 1.2. ⭐ B2 — Báo cáo tốt nghiệp
- Cuộn xuống cuối Tab Tổng quan → section "🎓 Báo cáo tốt nghiệp"
- Filter: **Khoá K22 · CN KHMT · TC tối thiểu 100**
- Click **"Xem trước"** → preview hiện sv22001 (49 grades, đủ TC) với "Đủ TN: ✓"
- Click **"📥 Tải CSV (Excel)"** → file `graduation_report_*.csv` download (BOM UTF-8)
- Mở Excel → 13 cột tiếng Việt OK
- **Defense**: *"Phòng đào tạo cần báo cáo SV đủ ĐK TN. App auto-export, BOM UTF-8 cho Excel chuẩn TV."*

### 1.3. ⚠️ Tạo 10 GV TRƯỚC TIÊN
- Sidebar **Cố vấn học tập** → toolbar có nút xanh lá **"Thêm cố vấn"** (icon person_add)
- Click → modal mở, có 2 tab:
  - Tab **Tạo 1 cố vấn**: nhập từng GV thủ công (mã GV + tên + bộ môn)
  - Tab **Import hàng loạt**: upload file `data/demo/co_van/bulk_import.xlsx`
- Pick tab **Import hàng loạt** → kéo thả/chọn file → "Import"
- **EXPECT**: Toast "Đã tạo 10 GV", grouped sections theo BM (KHMT/CNPM/MMT/HTTT/THKT/CNTTDH + chung)
- **Verify**: KHMT001 có badge "Trưởng BM" vàng, KHMT002 không có
- **Defense**: *"Bulk import idempotent — duplicate code thì skip. Auto-detect head BM nếu chưa có head cho spec đó."*

> Nếu skip step này → step 1.5 (phân công) sẽ báo lỗi "Mã GV chưa có trong hệ thống".

### 1.4. Tạo 10 SV
- Sidebar **Sinh viên** → toolbar có nút tím **"Thêm SV"** (icon person_add)
- Click → modal mở 2 tab giống GV
- Tab **Import hàng loạt** → file `data/demo/sinh_vien/bulk_import.xlsx`
- **EXPECT**: Toast "Đã tạo 10 SV"
- Filter cohort `K22` → 4 SV (sv22001/22003/22004/22005)
- Filter cohort `K23` → 3 SV
- Filter cohort `K24` → 3 SV
- **Verify**: SV có CN đã auto-assign GV (sv22001 → KHMT001 head)

### 1.5. Bulk phân công (override default)
- Sidebar **Cố vấn** → "Import phân công" → chọn `data/demo/co_van/phan_cong.xlsx`
- **EXPECT**: Preview 10 dòng, "Phân công mới: 10" hoặc "Cập nhật: 10"
  - Nếu hiện "Phát hiện Mã GV chưa có" → quay lại 1.3 tạo GV trước
- Click **Xử lý** → 10 mapping apply, có case "phân SV cho GV không phải head" (sv23001 → KHMT002)
- **Verify**: vào tab SV, cột "Cố vấn" của sv23001 = "Trần Thị KHMT-Phụ"

### 1.6. Upload điểm cho 1 SV cụ thể
- Tab **Sinh viên** → click sv22001 → side panel
- Click **"Upload điểm"** → chọn `data/demo/sinh_vien/bang_diem/sv22001.xlsx`
- **EXPECT**: Toast "Đã import 49 môn", icon MK đổi 👁 → 🔒 (locked)
- Click "Xem bảng điểm" → 49 môn, tích luỹ 152 TC
- **Defense**: *"Source = 'admin' → SV không upload đè được. Fallback flow: SV upload → source='self' tới khi admin override."*

### 1.7. ⭐ Bulk action SV
- Tab **Sinh viên** → tích checkbox 3 SV (sv22001, sv23001, sv24001)
- **EXPECT**: Bulk bar floating "3 SV đã chọn" với 4 actions [Reset MK / Gửi TB / Xuất CSV / Xoá]
- Click **Xuất CSV** → file download chứa 3 SV
- Search "xxx_không_có" → empty state với 2 CTA "Xoá filter" + "Thêm SV mới"

### 1.8. ⭐ B7 — Sửa mô tả môn
- Sidebar **Môn học** → filter spec=KHMT → click row "Cấu trúc dữ liệu và giải thuật" (7080206)
- Side panel → tab **Nội dung** → edit textarea → click **Lưu**
- **EXPECT**: Toast "Đã lưu", hard reload → mô tả được persist
- **Defense**: *"Mô tả 150 môn em viết baseline, admin có thể curate qua tab Nội dung."*

---

## 🎬 Phần 2 — SINH VIÊN (15 phút — main story)

Dùng 3 SV cover 3 trạng thái khác nhau:

### 2.1. **sv22001** (top student) — happy path
- Logout → login `sv22001 / Test1234!`
- **EXPECT** home.html: greeting + 3 KPI (TC=152 / GPA-4=3.85 / Career Fit), 5 môn gợi ý kỳ tới
- Sidebar widget **"CỐ VẤN: Nguyễn Văn KHMT-Trưởng · KHMT001"** (A3) + nút "Nhắn tin nhanh"
- Click 1 môn trong gợi ý → auto-navigate `integrated-roadmap.html?focus=<code>` + mở modal course detail
- **B1 — Hỏi AI (RAG)**: trong modal click "Hỏi AI" → FAB panel mở tab AI, prefill câu hỏi → Send → AI trả lời ~3-5s
- Tab **Bảng điểm** → banner xanh "✓ Đã xác thực", nút "Upload điểm" KHÔNG hiển thị (locked)
- Tab **Lộ trình** → drag-drop môn giữa kỳ, valid prereq cho phép, invalid block + tooltip
- Tab **Mục tiêu nghề** → đã có goal, hiện career fit %

### 2.2. **sv22003** (at-risk) — A6 risk analysis
- Logout → login `sv22003 / Test1234!` (CNPM, GPA 1.95, 3 fail + 2 retake pass)
- Tab **Bảng điểm** → 41 môn, có rows với term "(học lại pass)" — frontend detect retake, hiện badge
- Sidebar widget hiện cố vấn `CNPM001`
- Floating chat → tab Cố vấn → gửi tin nhắn (sẽ test ở Phần 3)

### 2.3. **sv24001** (chưa chọn CN) — career-goal flow
- Logout → login `sv24001 / Test1234!`
- Tab **Mục tiêu nghề** → chọn 6 nghề (vd Backend, Data Engineer, AI/ML...) → "Tính phù hợp"
- **EXPECT**: % match cho 6 CN, gợi ý chọn CN → click "Xem chi tiết" → so sánh CTĐT
- Tab **Lộ trình** → banner "Chuyên ngành chưa chốt" + CTA "Chọn ngay"

### 2.4. **sv24003** (empty state) — UI states
- Logout → login `sv24003 / Test1234!` (chưa upload điểm)
- Tab **Bảng điểm** → empty state với CTA "Upload bảng điểm"
- Click → upload `data/demo/sinh_vien/bang_diem/sv24001.xlsx` (test student có thể upload nhầm SV, system reject vì MSSV không khớp)
- Verify error rõ ràng

### 2.5. ⭐ Soft skills career resources
- Login bất kỳ SV nào, vào Mục tiêu nghề → click 1 skill → resources panel
- **VERIFY**: Link YouTube không phải Rick Roll (đã anti-rickroll)

---

## 🎬 Phần 3 — CỐ VẤN (5-7 phút)

### 3.1. Login head BM
- Logout → login `KHMT001 / Test1234!` (head KHMT)
- **EXPECT** advisor.html: dashboard với stats SV của mình (sv22001, sv24002), badges
- Filter cohort K22 → chỉ sv22001 (head KHMT only manage SV cùng spec)

### 3.2. ⭐ A6 — AI Risk Analysis
- Click `sv22001` → student modal mở
- Tab **Tiến độ** → click **"Phân tích AI"**
- **EXPECT**: 5-15s loading → kết quả `risk_level=low` + summary tích cực + factors + recommendations
- Logout → login `CNPM001` → click `sv22003` → Phân tích AI → `risk_level=high`, factors về fail/GPA
- Logout → login `THKT001` → click `sv23004` → `risk_level=high` (critical, GPA 1.50)

### 3.3. Per-term trao đổi
- Trong modal SV → tab **Bảng điểm** → click "Trao đổi" cạnh 1 kỳ (vd HK5)
- **EXPECT**: FAB panel mở tab Cố vấn (chiều ngược) + prefill "Em muốn trao đổi về kỳ HK5..."

### 3.4. Stats dashboard (sidebar)
- Sidebar **Tổng quan** → stats 5 SV thuộc KHMT, charts GPA distribution

---

## 🎬 Phần 4 — CROSS-ROLE (3-5 phút)

### 4.1. Real-time messaging
- **Window 1** (Chrome profile A): SV `sv22001` login → floating chat → tab Cố vấn → gửi "Em chào thầy"
- **Window 2** (Chrome profile B): GV `KHMT001` login → tab Tin nhắn → SV "Lê Hoàng Xuất Sắc" có badge unread
- Click vào SV → reply "Chào em" → quan sát Window 1 nhận tin nhắn ≤ 60s
- **Defense**: *"Real-time qua polling 60s — đơn giản, không cần WebSocket."*

### 4.2. Notification broadcast
- Logout Window 1 → login admin `demo_admin`
- Tab **Thông báo** → "+ Tạo TB" → title "Hạn đăng ký kỳ tới" · severity `urgent` · target "Khoá K22"
- Click **"Estimate reach"** → "4 SV sẽ nhận"
- Send → switch sang Window 1 (login lại sv22001) → bell icon badge `1`
- Click bell → dropdown hiện TB urgent với border đỏ
- Click → modal "Đã hiểu" để mark read

---

## 📋 Mapping nhanh: chức năng → SV nào dùng

| Chức năng | Dùng SV | Tại sao |
|---|---|---|
| B2 báo cáo TN (eligible) | sv22001 | GPA 3.85, đủ 152 TC, đã TT+ĐATN |
| A6 risk = LOW | sv22001 (login KHMT001) | Top student |
| A6 risk = HIGH | sv22003 (login CNPM001) | GPA 1.95, fail 3 môn |
| A6 risk = CRITICAL | sv23004 (login THKT001) | GPA 1.50, cảnh cáo học vụ |
| Retake handling | sv23002 (login CNPM001) | 2 môn "(học lại pass)" |
| Advisor không phải head | sv23001 | Phân cho KHMT002 (chỉ là phụ) |
| Empty state điểm | sv24003 | Chưa upload bảng điểm |
| Career-goal flow | sv24001 | Năm 2 chưa chốt CN |
| Internship done | sv22004 | Có thực tập, chưa ĐATN |
| Overdue (thiếu TC) | sv22005 | Năm 4 nhưng GPA + TC thấp |

## 🔄 Reset state nhanh

Khi demo gặp lỗi state (test xoá nhầm, dirty data...):
```bash
python -m backend.scripts.generate_demo_data --reset
```
Hoàn thành trong ~30s, idempotent.
