# EduGuide — Demo guide

Hướng dẫn demo end-to-end cho hội đồng (~10 phút).

## Setup 1 lần (chỉ cần chạy 1 lần)

```bash
# 1. Chạy backend
uvicorn backend.main:app --reload

# 2. Mở terminal khác, seed dataset
python -m backend.scripts.seed_demo_full
```

→ Tạo:
- 6 cố vấn (1 head/CN + 1 GV chung)
- 18 SV K14 phân bổ qua 6 CN + đại cương
- 6 file XLSX bảng điểm tại `data/demo/svXXX_diem.xlsx`
- File mật khẩu mặc định: `data/demo/seed_passwords.txt`

## Architecture pitch (1 slide)

> **EduGuide** = lớp **bổ trợ** trên hệ thống chính của trường, KHÔNG thay thế.
>
> Trường vẫn quyết: ai học, học gì, điểm bao nhiêu, CN nào.
> EduGuide thêm giá trị: lộ trình kéo-thả, AI advisor gợi ý môn, cố vấn theo dõi tập trung.
>
> Source of truth = trường → admin **mirror** vào app qua CSV import.

## Demo flow (chia 3 vai trò)

### Phần 1: Admin (3 phút)

**Mục tiêu:** giới thiệu trách nhiệm admin = **đồng bộ data từ trường**, không quyết định học vụ.

1. Đăng nhập `admin / admin` → tab "Quản lý SV"
2. **Cohort filter K14** → 18 SV xuất hiện, group theo khóa
3. Click "..." trên 1 SV → highlight 5 actions:
   - 📝 **Chỉnh sửa thông tin** (sửa CN, tên, khoá — không sửa email vì là cá nhân)
   - 📊 **Xem bảng điểm** (xem điểm SV)
   - 📤 **Upload điểm** (đồng bộ từ trường)
   - 🔑 **Reset mật khẩu** (cấp tạm)
   - 🔓 **Khôi phục tài khoản** (case mất Gmail + quên mật khẩu, sau xác minh offline)
4. Click **"Upload điểm"** trên `sv14001` → chọn `data/demo/sv14001_diem.xlsx` → import
   → Toast "Đã import X môn", icon MK đổi từ 👁 → 🔒 (locked)

**Điểm nhấn:**
- Mọi action có audit log (admin_logs table)
- Admin KHÔNG thể sửa email cá nhân của SV (403 từ backend)
- 1 chuẩn MSSV: `sv14001` (sv + 2 số khoá + 3 số STT)

### Phần 2: Sinh viên (3 phút)

**Mục tiêu:** giới thiệu giá trị app cho SV.

1. Đăng xuất → đăng nhập `sv14002` (xem mật khẩu trong `seed_passwords.txt`)
2. **Modal "Thiết lập tài khoản"** chặn vào app:
   - Bắt nhập email Gmail (bắt buộc — dùng cho quên mật khẩu)
   - Đặt mật khẩu mới (8 ký tự, hoa+thường+số)
3. Vào app → tab **"Bảng điểm"**
   - Banner xanh "✓ Bảng điểm chính thức (đã xác minh)" (vì admin đã upload)
   - Nút "Upload điểm" **biến mất** (locked)
4. Tab **"Lộ trình tích hợp"**
   - Drag-drop môn giữa các HK → validate prereq, Quy chế CTDT
   - Click "+ HK" cuối row → thêm HK10+ (case học chậm)
   - Click "Reset CTDT" → restore default
5. Tab **"Định hướng nghề nghiệp"** → AI advisor gợi ý môn TC theo career goal
6. Floating chat icon → AI assistant trả lời câu hỏi học tập

**Điểm nhấn:**
- Nguồn dữ liệu rõ ràng (badge Đã xác minh / Tự khai)
- Quy chế CTDT enforced (max 25 TC/HK, max 16 HK, prereq, TT/ĐATN)

### Phần 3: Cố vấn (3 phút)

**Mục tiêu:** giới thiệu công cụ theo dõi cho advisor.

1. Đăng nhập advisor `KHMT001`
2. Tab **"Sinh viên"** → 5 SV KHMT (sv14001-5) hiện ra
   - Card có badges: 🟢 Đã xác minh / 🟡 Tự khai
   - Filter dropdown "Tất cả khoá" → chọn K14
3. Click vào `sv14001` → modal SV chi tiết, có 4 tabs:
   - **Tiến độ & Gợi ý**: progress KPI, ghi chú tư vấn
   - **Bảng điểm**: bảng điểm group theo HK, badge nguồn từng dòng. Toggle "Bao gồm điểm SV tự khai" để xem mix.
   - **Lộ trình học tập**: xem read-only lộ trình SV
   - **Định hướng**: career goal SV chọn
4. Tab **"Sơ đồ CTĐT"** (sidebar) → hiển thị CTDT chuẩn KHMT (auto-load theo `managed_specialization`)
5. Tab **"Tin nhắn"** / **"Ghi chú tư vấn"** → liên lạc + lưu trữ note

**Điểm nhấn:**
- Default chỉ thấy điểm xác minh (không bị nhiễu data SV tự khai)
- Có toggle để xem cả 2 nguồn khi cần
- CTDT auto theo CN phụ trách

## Edge cases để hỏi/chứng minh

**Q: SV mất Gmail + quên mật khẩu thì sao?**
A: Admin → "..." trên SV → "Khôi phục tài khoản" → reset password + clear email + force first-login lại. SV setup lại với Gmail mới. (Đã có audit log).

**Q: SV upload điểm sai/giả?**
A: Bản tự khai source='self' chỉ cho SV xem. Cố vấn mặc định không thấy. Khi admin upload bản chính thức (source='admin'), bản tự khai bị thay thế và `grades_locked=true` chặn SV upload sau đó.

**Q: SV chuyển CN giữa kỳ?**
A: Trường update bên hệ thống chính → admin re-upload roster CSV với spec mới → app tự reassign cố vấn sang CN mới.

**Q: Nếu trường cho SV tự nhập điểm trên web trường?**
A: Đó là chuyện của trường. App này nhận data qua CSV admin export. Không có conflict.

**Q: Scale 1M SV?**
A: Per-advisor query là ~30-100 SV (chỉ SV được assign), không phải full 1M. Backend có cohort index. Frontend pagination chưa làm — sẽ thêm khi cần thực tế.

## Mật khẩu test (nhớ trong đầu)

- **admin / admin** — tài khoản admin
- **KHMT001** + password trong `data/demo/seed_passwords.txt`
- **sv14001** + password trong `data/demo/seed_passwords.txt`

## Reset demo state

```bash
# Wipe + re-seed (nếu demo bị lỗi state)
python -m backend.scripts.seed_demo_full
```

(Idempotent — chạy lại không tạo trùng.)
