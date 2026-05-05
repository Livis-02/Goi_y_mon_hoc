# Bộ dữ liệu demo EduGuide

Tất cả file Excel để upload qua admin UI. Sinh tự động bởi `backend/scripts/generate_demo_data.py`.

**Mật khẩu chung mọi user**: `Test1234!`

## Cấu trúc thư mục

```
data/demo/
├── README.md                 (file này)
├── sinh_vien/
│   ├── bulk_import.xlsx       ─ 10 SV để bulk-import qua /admin/users/import
│   └── bang_diem/
│       ├── sv22001.xlsx ... sv24003.xlsx (10 file điểm, 1 file/SV)
│       │                     để upload qua /admin/grades/import
└── co_van/
    ├── bulk_import.xlsx       ─ 10 GV để bulk-import qua /admin/advisors/import
    └── phan_cong.xlsx         ─ 10 mapping SV↔GV qua /admin/assignments/bulk-import
```

## Bộ 10 sinh viên (3 khoá)

| MSSV | Họ tên | Khoá | CN | Profile |
|---|---|---|---|---|
| `sv22001` | Lê Hoàng Xuất Sắc | K22 | KHMT | Top student, đủ TC tốt nghiệp (GPA 3.85) |
| `sv22003` | Trần Văn Yếu | K22 | CNPM | At-risk: GPA thấp + trượt nhiều môn |
| `sv22004` | Phạm Thị Internship | K22 | MMT | Đã thực tập, đang chọn ĐATN |
| `sv22005` | Vũ Minh Overdue | K22 | HTTT | Năm cuối thiếu TC — cảnh báo overdue |
| `sv23001` | Hoàng Văn Giỏi | K23 | KHMT | Năm 3 typical, vừa vào CN |
| `sv23002` | Bùi Thị Học Lại | K23 | CNPM | Có 2 môn học lại đã pass |
| `sv23004` | Tô Anh Cảnh Cáo | K23 | THKT | Critical: GPA 1.50, cảnh cáo học vụ |
| `sv24001` | Đinh Thị Chuẩn Bị Chọn | K24 | (chưa) | Năm 2, đang chọn CN |
| `sv24002` | Mai Đức Cao Điểm | K24 | KHMT | High performer GPA 3.70 |
| `sv24003` | Nguyễn Hoa Chưa Upload | K24 | (chưa) | Empty state — chưa có điểm |

## Bộ 10 cố vấn

| Mã GV | Họ tên | Bộ môn | Chức vụ |
|---|---|---|---|
| `KHMT001` | Nguyễn Văn KHMT-Trưởng | KHMT | Trưởng BM |
| `KHMT002` | Trần Thị KHMT-Phụ | KHMT | Cố vấn |
| `CNPM001` | Lê Văn CNPM-Trưởng | CNPM | Trưởng BM |
| `MMT001` | Hoàng Văn MMT-Trưởng | MMT | Trưởng BM |
| `HTTT001` | Vũ Thị HTTT-Trưởng | HTTT | Trưởng BM |
| `THKT001` | Bùi Văn THKT-Trưởng | THKT | Trưởng BM |
| `CNTTDH001` | Đỗ Thị CNTTDH-Trưởng | CNTTDH | Trưởng BM |
| `GV001` | Đinh Văn Đại Cương 1 | (chung) | Cố vấn |
| `GV002` | Mai Thị Đại Cương 2 | (chung) | Cố vấn |
| `GV003` | Phạm Anh Đại Cương 3 | (chung) | Cố vấn |

## Bộ 10 phân công SV ↔ GV

10 mapping cover các case: SV trong CN → trưởng BM, SV trong CN → GV phụ (KHMT002), SV chưa CN → GV chung.

## Cách dùng (admin demo)

### 1. Bulk-import GV trước (vì SV cần advisor)

Login admin → tab **Quản lý cố vấn** → "Import từ file" → chọn `data/demo/co_van/bulk_import.xlsx`.
Kết quả: 10 GV được tạo, mật khẩu auto-gen 6 số (admin xem qua icon 👁).

### 2. Bulk-import SV

Tab **Quản lý sinh viên** → "Import từ file" → chọn `data/demo/sinh_vien/bulk_import.xlsx`.
Kết quả: 10 SV được tạo. Auto-assign GV theo CN (head BM của CN tương ứng).

### 3. Import điểm cho từng SV (lặp 10 lần)

Tab **Quản lý sinh viên** → click 1 SV → side panel → "Upload điểm" → chọn file tương ứng trong `data/demo/sinh_vien/bang_diem/`.
Kết quả: Bảng điểm SV được lưu, dashboard SV hiện đầy đủ data.

### 4. Bulk-assign cố vấn (override default assignment)

Tab **Quản lý cố vấn** → "Phân công bulk" → chọn `data/demo/co_van/phan_cong.xlsx`.
Kết quả: 10 mapping được apply, demo case "phân SV cho GV không phải trưởng BM" (sv23001 → KHMT002).

## Re-generate

Chạy lại generator nếu data trong DB bị lỗi:
```bash
python -m backend.scripts.generate_demo_data --reset      # xoá DB cũ + tạo lại
python -m backend.scripts.generate_demo_data --dry-run    # preview, không động DB
python -m backend.scripts.generate_demo_data --no-db      # chỉ ghi XLSX, không động DB
```

Generator vừa **seed DB trực tiếp** vừa **ghi file Excel** — dùng cách nào cũng được tuỳ scenario:
- **Test admin upload UI** → Bỏ qua DB seed, dùng Excel để upload qua giao diện
- **Demo nhanh** → Dùng `--reset` để DB sẵn sàng, không cần upload thủ công
