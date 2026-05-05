# CTDT_CHUAN — Chương trình Kỹ sư Công nghệ Thông tin
## Mã ngành: 7480201 | Phiên bản: 2026-04-23 (CHUẨN — cập nhật từ 7480201ver2.pdf)
## File này thay thế ctdt_reference.md và CTDT_FINAL.md

> **Nguồn ưu tiên khi mâu thuẫn:**
> 1. Bảng điểm thực tế SV (Diem_2.csv, Diem_Hoai_Nam.csv)
> 2. CTDT_ExportFromDaotao.pdf
> 3. 7480201ver2.pdf
> 4. 7480201.pdf (chỉ dùng cho quy chế chung, không dùng cho mã môn)

---

## PHẦN 1 — THÔNG TIN CHUNG

### 1.1 Thông tin ngành

| Mục | Giá trị |
|-----|---------|
| Tên ngành | Kỹ thuật Công nghệ Thông tin |
| Mã ngành | 7480201 |
| Trình độ | Đại học (Kỹ sư) |
| Thời gian đào tạo chuẩn | 4.5 năm (9 học kỳ chính + học kỳ hè) |
| Ngưỡng tốt nghiệp | **153 TC** |

### 1.2 Cấu trúc tổng thể CTĐT

| Khối kiến thức | TC danh nghĩa |
|----------------|---------------|
| Giáo dục đại cương | 65 |
| Cơ sở ngành (chung mọi chuyên ngành) | 52 |
| Chuyên ngành | 40 |
| **Tổng danh nghĩa** | **157** |

Phần chuyên ngành gồm:
- 12 TC định hướng bắt buộc
- ≥ 9 TC Tự chọn B
- ≥ 9 TC Tự chọn C
- **10 TC Thực tập doanh nghiệp**
- **10 TC Đồ án tốt nghiệp**

→ Tổng tối đa **167 TC**; ngưỡng tốt nghiệp **153 TC**.

### 1.3 Danh sách 6 chuyên ngành

| Mã CN | Tên đầy đủ | Viết tắt |
|-------|-----------|---------|
| 7480201_07 | Khoa học máy tính (ứng dụng) | KHMT |
| 7480201_06 | Mạng máy tính | MMT |
| 7480201_05 | Công nghệ phần mềm | CNPM |
| 7480201_09 | Hệ thống thông tin | HTTT |
| 7480201_04 | Tin học kinh tế | THKT |
| 7480201_08 | Công nghệ thông tin Địa học | CNTTDH |

---

## PHẦN 2 — QUY CHẾ TÍNH TÍN CHỈ TÍCH LŨY

### 2.1 Được tính vào TC tích lũy

- Môn đạt điểm **D trở lên** (≥ 4.0/10, điểm 4 ≥ 1.0)
- Môn Tự chọn A/B/C học vượt mức tối thiểu vẫn được tính toàn bộ

### 2.2 KHÔNG tính vào TC tích lũy

| Trường hợp | Ghi chú |
|-----------|--------|
| Môn trượt F (< 4.0/10) | Phải học lại |
| Môn học lại / cải thiện điểm | Chỉ tính TC **1 lần** |
| Học kỳ hè (HK3 mỗi năm) | TC không cộng sau HK hè |
| GDTC (7010701/702/703) | Phải hoàn thành nhưng không tính TC |
| QPAN (mã bắt đầu 73) | Phải hoàn thành nhưng không tính TC |
| Tiếng Anh tăng cường 7010610 | Không tính TC (xác nhận từ bảng điểm 2 SV) |

### 2.3 Quy tắc đặc biệt

- Môn xuất hiện trong cả pool B và pool C: chỉ tính **1 lần**
- Nhận biết QPAN: **không có dấu `x`** ở cột "Môn bắt buộc" trong file export
- Dùng cột **"Số tín chỉ tích lũy"** (MAX value) từ file điểm — không tự tính lại

---

## PHẦN 3 — CÔNG THỨC TÍNH ĐIỂM

### 3.1 GPA học kỳ (thang 4)

```
GPA_kỳ = Σ(điểm_4 × TC) / Σ(TC)
```

Chỉ tính các môn có `count_toward_credits = TRUE` trong kỳ đó. Loại GDTC, QPAN, TA tăng cường.

### 3.2 GPA tích lũy (thang 4)

```
GPA_TL = Σ(điểm_4_max × TC) / Σ(TC_đã_pass)
```

**Quy tắc môn học lại:** Lấy điểm **cao nhất** qua các lần học. TC chỉ tính 1 lần.

### 3.3 GPA hệ 10

Tính tương tự công thức 3.1–3.2 nhưng dùng điểm 10 thay vì điểm 4.

### 3.4 Thang quy đổi điểm

| Điểm 10 | Điểm chữ | Điểm 4 | Kết quả |
|---------|---------|--------|--------|
| 9.0 – 10.0 | A+ | 4.0 | Đạt |
| 8.5 – 8.9 | A | 3.7 | Đạt |
| 8.0 – 8.4 | B+ | 3.5 | Đạt |
| 7.0 – 7.9 | B | 3.0 | Đạt |
| 6.5 – 6.9 | C+ | 2.5 | Đạt |
| 5.5 – 6.4 | C | 2.0 | Đạt |
| 5.0 – 5.4 | D+ | 1.5 | Đạt |
| 4.0 – 4.9 | D | 1.0 | Đạt |
| 0.0 – 3.9 | F | 0.0 | **Trượt** |

### 3.5 Điểm học phần

Điểm học phần = điểm bộ phận (kiểm tra, bài tập, thí nghiệm) + điểm thi cuối kỳ.
Tỉ lệ cụ thể do giảng viên quy định trong đề cương môn học (thường 30%–50% bộ phận + 50%–70% thi).

---

## PHẦN 4 — XẾP LOẠI HỌC LỰC

Dựa trên GPA tích lũy thang 4:

| GPA tích lũy | Xếp loại |
|--------------|----------|
| ≥ 3.6 | Xuất sắc |
| 3.2 – 3.59 | Giỏi |
| 2.5 – 3.19 | Khá |
| 2.0 – 2.49 | Trung bình |
| < 2.0 | Yếu (cảnh báo học vụ) |

**Xếp loại tốt nghiệp:** dựa trên GPA tích lũy cuối cùng (cùng thang này).

---

## PHẦN 5 — CẢNH BÁO HỌC VỤ

### 5.1 Trạng thái SV tự động (cho advisor theo dõi)

| Trạng thái | Điều kiện |
|-----------|-----------|
| 🔴 Nguy cơ cao | GPA < 2.0 **HOẶC** trễ TN > 2 HK |
| 🟡 Cần chú ý | 2.0 ≤ GPA < 2.5 **HOẶC** trễ 1–2 HK |
| 🟢 Bình thường | Còn lại |

### 5.2 Công thức late_hk

```
late_hk = max(0, terms_studied + estimated_terms_remaining - 9)
```

Trong đó 9 = số HK chuẩn của CTĐT 4.5 năm.

### 5.3 Các mức cảnh báo chi tiết

- **GPA < 2.0:** Nguy cơ buộc thôi học nếu kéo dài nhiều kỳ liên tiếp
- **GPA 2.0–2.5:** Cần cải thiện, nên giảm TC đăng ký
- **Trễ tốt nghiệp > 2 HK:** Cần lập lại kế hoạch với advisor

---

## PHẦN 6 — GIỚI HẠN TC ĐĂNG KÝ MỖI KỲ

| GPA tích lũy (thang 4) | Giới hạn TC/kỳ |
|------------------------|----------------|
| ≥ 3.6 | 25 TC |
| ≥ 2.5 | 22 TC |
| < 2.5 | 18 TC |

---

## PHẦN 7 — ĐIỀU KIỆN TỐT NGHIỆP

### 7.1 Điều kiện bắt buộc

| Điều kiện | Ngưỡng |
|-----------|--------|
| TC tích lũy tối thiểu | **153 TC** (gồm thực tập 10 + đồ án 10) |
| GPA tích lũy (thang 4) | **≥ 2.0** |
| Hoàn thành GDTC 1+2+3 | Bắt buộc (không tính TC) |
| Hoàn thành toàn bộ QPAN (4 môn) | Bắt buộc (không tính TC) |
| Không còn nợ môn bắt buộc | Bắt buộc |
| Tự chọn B: pass ≥ 9 TC | Bắt buộc |
| Tự chọn C: pass ≥ 9 TC | Bắt buộc |
| Tự chọn A: pass ≥ 6 TC | Bắt buộc |
| Thực tập doanh nghiệp: pass | Bắt buộc |
| Đồ án tốt nghiệp: pass | Bắt buộc (sau khi pass thực tập) |

### 7.2 Điều kiện đăng ký thực tập

Còn ≤ **6 TC** chưa hoàn thành (không tính thực tập + đồ án TN).

### 7.3 Điều kiện đăng ký đồ án tốt nghiệp

Đã pass thực tập doanh nghiệp. **Không được** đăng ký cùng kỳ với thực tập.

---

## PHẦN 8 — CHƯƠNG TRÌNH HỌC THEO HỌC KỲ (CƠ SỞ NGÀNH CHUNG)

### 8.1 HK1 — Năm 1 HK1 (chung mọi chuyên ngành)

| Mã MH | Tên môn học | TC | Tính TC | Tiên quyết |
|-------|------------|-----|---------|-----------|
| 7010102 | Đại số tuyến tính | 4 | ✓ | — |
| 7010103 | Giải tích 1 | 4 | ✓ | — |
| 7010120 | Xác suất thống kê | 3 | ✓ | — |
| 7010601 | Tiếng Anh 1 | 3 | ✓ | — |
| 7010701 | Giáo dục thể chất 1 | 1 | ✗ | — |
| 7020105 | Triết học Mác - Lênin | 3 | ✓ | — |
| 7080514 | Nhập môn ngành CNTT | 3 | ✓ | — |

> **QPAN theo khóa:**
> - **Khóa 2021 (bảng điểm thực tế):** 4 môn trong HK1 — 7300103 (2TC), 7300104 (2TC), 7300202 (3TC), 7300203 (4TC)
> - **ver2.pdf (khóa mới hơn):** 3 môn rải HK4/5/6 — 7300101 (3TC, HK4), 7300102 (3TC, HK5), 7300201 (5TC, HK6)
> - Nhận biết QPAN: mã bắt đầu bằng **73**. Tất cả đều không tính TC tích lũy.

### 8.2 HK2

| Mã MH | Tên môn học | TC | Tính TC | Tiên quyết |
|-------|------------|-----|---------|-----------|
| 7010104 | Giải tích 2 | 4 | ✓ | 7010103 |
| 7010111 | Phương pháp tính | 3 | ✓ | — |
| 7010202 | Thí nghiệm vật lý 1 | 1 | ✓ | — |
| 7010204 | Vật lý đại cương 1 | 4 | ✓ | — |
| 7010602 | Tiếng Anh 2 | 3 | ✓ | 7010601 |
| 7010702 | Giáo dục thể chất 2 | 1 | ✗ | 7010701 |
| 7020302 | Kinh tế chính trị Mác - Lênin | 2 | ✓ | 7020105 |
| 7080208 | Cơ sở lập trình | 3 | ✓ | — |

### 8.3 HK3

| Mã MH | Tên môn học | TC | Tính TC | Tiên quyết |
|-------|------------|-----|---------|-----------|
| 7010304 | Hóa học đại cương phần 1 + TN | 3 | ✓ | — |
| 7010703 | Giáo dục thể chất 3 | 1 | ✗ | 7010702 |
| 7020202 | Chủ nghĩa xã hội khoa học | 2 | ✓ | 7020302 |
| 7080112 | Nguyên lý Hệ điều hành | 2 | ✓ | — |
| 7080207 | Cơ sở dữ liệu | 3 | ✓ | — |
| 7080216 | Kỹ thuật LT hướng đối tượng C++ + BTL | 2 | ✓ | 7080208 |
| 7080712 | Kiến trúc máy tính | 2 | ✓ | — |

### 8.4 HK4

| Mã MH | Tên môn học | TC | Tính TC | Tiên quyết |
|-------|------------|-----|---------|-----------|
| 7020201 | Tư tưởng Hồ Chí Minh | 2 | ✓ | 7020202 |
| 7080206 | Cấu trúc dữ liệu và giải thuật | 3 | ✓ | — |
| 7080211 | Hệ quản trị cơ sở dữ liệu | 2 | ✓ | 7080207 |
| 7080512 | Lập trình hướng đối tượng Java | 3 | ✓ | 7080208 |
| 7080717 | Mạng máy tính + BTL | 3 | ✓ | — |
| 7300101 | Công tác quốc phòng - an ninh | 3 | ✗ | — |

> QPAN 7300101: áp dụng theo ver2.pdf (khóa mới). Khóa 2021 thì 4 môn QPAN nằm ở HK1.

### 8.5 HK5

| Mã MH | Tên môn học | TC | Tính TC | Tiên quyết |
|-------|------------|-----|---------|-----------|
| 7020303 | Lịch sử Đảng Cộng sản Việt Nam | 2 | ✓ | — |
| 7080111 | Mã nguồn mở | 2 | ✓ | 7080226 |
| 7080116 | Phát triển ứng dụng Web + BTL | 4 | ✓ | 7080207 |
| 7080509 | Khoa học dữ liệu | 2 | ✓ | 7080514 |
| 7080703 | Cơ sở an ninh mạng | 3 | ✓ | 7080717 |
| 7080713 | Kiến trúc và hạ tầng mạng IoT | 2 | ✓ | — |
| 7300102 | Đường lối quân sự của Đảng | 3 | ✗ | — |

### 8.6 HK6

| Mã MH | Tên môn học | TC | Tính TC | Tiên quyết |
|-------|------------|-----|---------|-----------|
| 7020104 | Pháp luật đại cương | 2 | ✓ | — |
| 7080113 | Phân tích & thiết kế hệ thống + BTL | 3 | ✓ | — |
| 7080122 | Trí tuệ nhân tạo + BTL | 3 | ✓ | 7080717 |
| 7080517 | Phát triển ứng dụng IoT | 2 | ✓ | — |
| 7080626 | Thương mại điện tử | 3 | ✓ | — |
| 7300201 | Quân sự chung và chiến thuật | 5 | ✗ | — |

### 8.7 HK7 — Cơ sở ngành chung

| Mã MH | Tên môn học | TC | Tính TC |
|-------|------------|-----|---------|
| 7080504 | Điện toán đám mây và ứng dụng | 2 | ✓ |

> HK7 trở đi: kết hợp 7080504 + các môn chuyên ngành (xem Phần 10).

---

## PHẦN 9 — ĐIỀU KIỆN TIÊN QUYẾT

> Nguồn: 7480201.pdf. Điều kiện pass tiên quyết: **điểm ≥ 4.0/10** (xếp loại D trở lên).

| Môn cần học | Tiên quyết phải pass trước |
|-------------|---------------------------|
| 7010104 Giải tích 2 | 7010103 Giải tích 1 |
| 7010602 Tiếng Anh 2 | 7010601 Tiếng Anh 1 |
| 7010702 GDTC 2 | 7010701 GDTC 1 |
| 7010703 GDTC 3 | 7010702 GDTC 2 |
| 7020302 Kinh tế chính trị | 7020105 Triết học Mác-Lênin |
| 7020202 CNXH khoa học | 7020302 Kinh tế chính trị |
| 7020201 Tư tưởng Hồ Chí Minh | 7020202 CNXH khoa học |
| 7080216 KTLT C++ | 7080208 Cơ sở lập trình |
| 7080211 HQ CSDL | 7080207 Cơ sở dữ liệu |
| 7080717 Mạng máy tính | 7080216 KTLT C++ |
| 7080512 LT Java | 7080206 Cấu trúc DL & giải thuật |
| 7080116 Phát triển Web | 7080211 HQ CSDL |
| 7080703 Cơ sở an ninh mạng | 7080512 LT Java |
| 7080517 Phát triển IoT | 7080116 Phát triển Web |
| 7080122 Trí tuệ nhân tạo | 7080717 Mạng máy tính |

**Phân biệt:**
- **Tiên quyết:** phải pass (D trở lên) TRƯỚC khi học môn mới
- **Song hành:** học cùng kỳ được (không áp dụng trong CTĐT này)
- **Trước:** học trước là đủ (pass hay không cũng được)

---

## PHẦN 10 — NHÓM TỰ CHỌN A (chung mọi CN)

- **Yêu cầu tốt nghiệp:** pass ≥ 6 TC
- **Học rải:** HK3–HK5
- Học vượt 6 TC vẫn tính toàn bộ vào TC tích lũy

| Mã MH | Tên môn học | TC | Ghi chú |
|-------|------------|-----|--------|
| 7010108 | Logic đại cương | 3 | Tất cả CN |
| 7010607 | Tiếng Trung 1 | 3 | Tất cả CN |
| 7010608 | Tiếng Trung 2 | 3 | Tất cả CN |
| 7080121 | Toán rời rạc cho CNTT | 4 | Tất cả CN |
| 7080219 | Lý thuyết đồ thị cho tin học | 2 | Tất cả CN |
| 7080226 | Tin học đại cương + TH | 3 | Tất cả CN |
| 7080622 | Tối ưu hóa thuật toán | 2 | Tất cả CN |
| 7080636 | Tin học văn phòng nâng cao | 3 | Tất cả CN |
| 7080222 | Phương pháp tính ứng dụng | 3 | **Chỉ HTTT** |

Mã DB: `A_2020_7480201_07` (KHMT), `A_2020_7480201_09` (HTTT có thêm 7080222), v.v.

---

## PHẦN 11 — CHUYÊN NGÀNH CHI TIẾT

### 11A. KHMT — Khoa học máy tính (7480201_07)

#### Định hướng bắt buộc (12 TC)
| Mã MH | Tên môn học | TC | HK |
|-------|------------|-----|----|
| 7080508 | Khai phá dữ liệu | 3 | 7 |
| 7080515 | Phân tích và thiết kế hướng đối tượng | 3 | 7 |
| 7080510 | Kỹ nghệ tri thức và học máy | 3 | 8 |
| 7080506 | Đồ án Khoa học máy tính | 3 | 8 |

#### Tốt nghiệp (HK9)
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7080519 | Thực tập doanh nghiệp | 10 |
| 7080513 | Đồ án tốt nghiệp | 10 |

#### Tự chọn B KHMT (≥9 TC) — `B_2020_7480201_07`
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7080107 | Kiểm thử và đảm bảo chất lượng PM + BTL | 3 |
| 7080124 | Xử lý ngôn ngữ tự nhiên | 3 |
| 7080516 | Phân tích và thiết kế thuật toán | 3 |
| 7080518 | Thị giác máy tính | 3 |
| 7080520 | Web ngữ nghĩa | 3 |

#### Tự chọn C KHMT (≥9 TC) — `C_2020_7480201_07`
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7080316 | Lập trình Python 2 | 3 |
| 7080319 | Trực quan hóa dữ liệu | 3 |
| 7080505 | Điện toán di động | 3 |
| 7080507 | Dữ liệu lớn và ứng dụng | 3 |
| 7080511 | Lập trình game trên di động | 3 |
| 7080634 | Quản trị dự án CNTT | 3 |

---

### 11B. MMT — Mạng máy tính (7480201_06)

#### Định hướng bắt buộc (12 TC)
| Mã MH | Tên môn học | TC | HK |
|-------|------------|-----|----|
| 7080721 | Quản trị mạng + BTL | 3 | 7 |
| 7080728 | An ninh mạng + BTL | 3 | 8 |
| 7080720 | Quản trị hệ thống + BTL | 3 | 8 |
| 7080729 | Đồ án Mạng máy tính | 3 | 8 |

#### Tốt nghiệp (HK9)
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7080723 | Thực tập doanh nghiệp | 10 |
| 7080715 | Đồ án tốt nghiệp | 10 |

#### Tự chọn B MMT (≥9 TC) — `B_2020_7480201_06`
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7080108 | Lập trình .NET 1 + BTL | 3 |
| 7080511 | Lập trình game trên di động | 3 |
| 7080716 | Mã nguồn mở chuyên ngành mạng + BTL | 3 |
| 7080724 | Tiếng Anh chuyên ngành mạng | 2 |
| 7080730 | Lập trình mạng + BTL | 3 |
| 7080731 | Thiết kế mạng + BTL | 3 |
| 7080732 | Truyền dữ liệu và mạng máy tính nâng cao + BTL | 3 |

#### Tự chọn C MMT (≥9 TC) — `C_2020_7480201_06`
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7000002 | Kỹ năng giao tiếp và làm việc nhóm | 2 |
| 7000004 | Kỹ năng tư duy phản biện | 2 |
| 7080118 | Thiết kế Website | 2 |
| 7080234 | Chuẩn kỹ năng sử dụng Công nghệ Thông tin | 3 |
| 7080308 | Hệ quản trị nội dung mã nguồn mở | 2 |
| 7080507 | Dữ liệu lớn và ứng dụng | 3 |
| 7080516 | Phân tích và thiết kế thuật toán | 3 |
| 7080518 | Thị giác máy tính | 3 |
| 7080634 | Quản trị dự án CNTT | 3 |

---

### 11C. CNPM — Công nghệ phần mềm (7480201_05)

#### Định hướng bắt buộc (9 TC) — theo ver2.pdf
| Mã MH | Tên môn học | TC | HK |
|-------|------------|-----|----|
| 7080104 | Công nghệ phần mềm | 2 | 7 |
| 7080108 | Lập trình .NET 1 + BTL | 3 | 7 |
| 7080114 | Phân tích, thiết kế hướng đối tượng với UML | 2 | 7 |
| 7080102 | Chuyên đề (định hướng doanh nghiệp phần mềm) | 2 | 8 |
| 7080106 | Đồ án CNPM | 3 | 8 |

#### Tốt nghiệp (HK9)
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7080119 | Thực tập doanh nghiệp | 10 |
| 7080110 | Đồ án tốt nghiệp | 10 |

#### Tự chọn B CNPM (≥9 TC) — `B_2020_7480201_05`
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7080107 | Kiểm thử và đảm bảo chất lượng phần mềm + BTL | 3 |
| 7080109 | Lập trình .NET 2 + BTL | 3 |
| 7080115 | Phát triển ứng dụng cho thiết bị di động + BTL | 3 |
| 7080123 | Tương tác người máy | 3 |
| 7080234 | Chuẩn kỹ năng sử dụng Công nghệ Thông tin | 3 |
| 7080508 | Khai phá dữ liệu | 3 |
| 7080510 | Kỹ nghệ tri thức và học máy | 3 |
| 7080516 | Phân tích và thiết kế thuật toán | 3 |

#### Tự chọn C CNPM (≥9 TC) — `C_2020_7480201_05`
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7000002 | Kỹ năng giao tiếp và làm việc theo nhóm | 2 |
| 7000004 | Kỹ năng tư duy phản biện | 2 |
| 7080103 | Cơ sở dữ liệu nâng cao | 2 |
| 7080105 | Đạo đức máy tính | 2 |
| 7080117 | Quản trị dự án CNTT (2TC) | 2 |
| 7080118 | Thiết kế Website | 2 |
| 7080120 | Tiếng Anh cho ngành CNTT | 2 |
| 7080502 | An ninh và Bảo mật Internet | 3 |
| 7080505 | Điện toán di động | 3 |
| 7080507 | Dữ liệu lớn và ứng dụng | 3 |
| 7080516 | Phân tích và thiết kế thuật toán | 3 |
| 7080518 | Thị giác máy tính | 3 |
| 7080610 | Marketing điện tử cơ bản | 2 |
| 7080618 | Thương mại điện tử | 2 |
| 7080634 | Quản trị dự án CNTT (3TC) | 3 |

---

### 11D. HTTT — Hệ thống thông tin (7480201_09)

#### Định hướng bắt buộc (12 TC) — theo ver2.pdf
| Mã MH | Tên môn học | TC | HK |
|-------|------------|-----|----|
| 7080212 | Hệ thống phân tán | 3 | 7 |
| 7080213 | Học máy thống kê | 3 | 7 |
| 7080204 | Các hệ cơ sở tri thức | 3 | 8 |
| 7080210 | Đồ án Hệ thống thông tin | 3 | 8 |

#### Tốt nghiệp (HK9)
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7080224 | Thực tập doanh nghiệp | 10 |
| 7080218 | Đồ án tốt nghiệp | 10 |

#### Tự chọn B HTTT (≥9 TC) — `B_2020_7480201_09`
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7080202 | An toàn và bảo mật hệ thống thông tin | 3 |
| 7080205 | Các hệ thống thông tin thông minh | 3 |
| 7080209 | Công nghệ đa phương tiện | 3 |
| 7080214 | Kho dữ liệu | 3 |
| 7080217 | Lập trình nâng cao | 3 |
| 7080634 | Quản trị dự án CNTT | 3 |

#### Tự chọn C HTTT (≥9 TC) — `C_2020_7480201_09`
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7000002 | Kỹ năng giao tiếp và làm việc theo nhóm | 2 |
| 7000004 | Kỹ năng tư duy phản biện | 2 |
| 7080107 | Kiểm thử và đảm bảo chất lượng phần mềm + BTL | 3 |
| 7080120 | Tiếng Anh cho ngành CNTT | 2 |
| 7080215 | Kỹ thuật Hadoop/Mapreduce | 3 |
| 7080220 | Ngôn ngữ lập trình Python | 3 |
| 7080230 | Chuẩn kỹ năng sử dụng công nghệ thông tin | 3 |
| 7080232 | Ngôn ngữ lập trình R cho phân tích dữ liệu | 3 |
| 7080234 | Chuẩn kỹ năng sử dụng Công nghệ Thông tin | 3 |
| 7080310 | Hệ thông tin địa lý | 3 |
| 7080505 | Điện toán di động | 3 |
| 7080518 | Thị giác máy tính | 3 |
| 7080609 | Marketing điện tử nâng cao | 2 |

---

### 11E. THKT — Tin học kinh tế (7480201_04)

#### Định hướng bắt buộc (12 TC)
| Mã MH | Tên môn học | TC | HK |
|-------|------------|-----|----|
| 7080633 | Kế toán máy | 3 | 7 |
| 7080616 | Thuật toán hóa các bài toán kinh tế | 3 | 7 |
| 7080638 | Phát triển phần mềm quản lý | 3 | 8 |
| 7080603 | Đồ án Tin học kinh tế | 3 | 8 |

#### Tốt nghiệp (HK9)
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7080617 | Thực tập doanh nghiệp | 10 |
| 7080604 | Đồ án tốt nghiệp | 10 |

#### Tự chọn B THKT (≥9 TC) — `B_2020_7480201_04`
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7080605 | Hệ thống Thông tin quản lý | 3 |
| 7080615 | Thống kê & ứng dụng tin học + TH | 3 |
| 7080627 | Kinh tế thông tin | 3 |
| 7080628 | Kinh tế lượng ứng dụng | 3 |
| 7080635 | Marketing điện tử | 3 |

#### Tự chọn C THKT (≥9 TC) — `C_2020_7480201_04`
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7080107 | Kiểm thử và đảm bảo chất lượng PM + BTL | 3 |
| 7080631 | Trí tuệ nhân tạo trong marketing | 3 |
| 7080634 | Quản trị dự án CNTT | 3 |
| 7080636 | Tin học văn phòng nâng cao | 3 |
| 7080637 | Quản trị các nguồn lực thông tin | 3 |

---

### 11F. CNTTDH — CNTT Địa học (7480201_08)

#### Định hướng bắt buộc (12 TC)
| Mã MH | Tên môn học | TC | HK |
|-------|------------|-----|----|
| 7080313 | Thông tin địa học đại cương | 3 | 7 |
| 7050303 | Cơ sở Hệ thông tin địa lý (GIS) | 3 | 7 |
| 7080309 | Hệ thống CSDL không gian | 3 | 8 |
| 7080403 | Đồ án Thông tin địa học | 3 | 8 |

#### Tốt nghiệp (HK9)
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7080314 | Thực tập doanh nghiệp | 10 |
| 7080311 | Đồ án tốt nghiệp | 10 |

#### Tự chọn B CNTTDH (≥9 TC) — `B_2020_7480201_08`
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7050362 | Cơ sở viễn thám và ứng dụng | 3 |
| 7080302 | Cơ sở xử lý ảnh số | 3 |
| 7080321 | Phân tích thông tin địa lý | 3 |
| 7080323 | Dịch vụ dựa trên địa điểm | 3 |
| 7080324 | Phát triển ứng dụng web GIS với Python/JS | 3 |
| 7080402 | Địa thống kê + BTL | 3 |
| 7080405 | Thông tin địa học trong đánh giá cảnh quan | 3 |

#### Tự chọn C CNTTDH (≥9 TC) — `C_2020_7480201_08`
| Mã MH | Tên môn học | TC |
|-------|------------|-----|
| 7080301 | Cơ sở dữ liệu phân tán | 3 |
| 7080307 | GIS cho phát triển ứng dụng | 3 |
| 7080325 | Phát triển ứng dụng di động đa nền tảng 1 | 3 |
| 7080406 | Thông tin địa học trong đánh giá tài nguyên | 3 |
| 7080407 | Thông tin địa học trong đánh giá thiên tai | 3 |
| 7080408 | Ứng dụng Matlab trong khoa học Trái đất | 3 |
| 7080507 | Dữ liệu lớn và ứng dụng | 3 |
| 7080541 | Khai phá dữ liệu | 3 |

---

## PHẦN 12 — QUY TẮC MATCHING KHI UPLOAD BẢNG ĐIỂM

1. Match theo `course_code` trước (mã môn chính xác)
2. Không khớp → fallback match theo `course_name` (normalize lowercase + trim khoảng trắng)
3. Không khớp cả 2 → đánh dấu **"Môn ngoài CTĐT"** (không tính tiến độ)
4. Nhận biết QPAN: **không có dấu `x`** cột "Môn bắt buộc"

### 12.1 Cấu trúc file điểm từ cổng SV

Các cột: `Stt | Mã MH | Tên môn học | Chuyên ngành | Môn cốt lõi | Số tín chỉ | Số TC học phí | Môn bắt buộc | Đã học | Nhóm | Nhánh | Số TC tối thiểu | Số TC tối đa | Môn đã học và đạt | Tổng tiết | Lý thuyết | Thực hành`

Header nhóm: `"Học kỳ N - Năm học YYYY - YYYY"`

### 12.2 Dòng định danh (yêu cầu của hệ thống EduGuide)

File điểm upload vào hệ thống phải có dòng đầu tiên:
```
Mã sinh viên: XXXXXXXXXX
```
Để hệ thống tự định danh và tạo/cập nhật tài khoản SV.

---

## PHẦN 13 — ĐỊNH HƯỚNG NGHỀ NGHIỆP THEO CHUYÊN NGÀNH

| CN | Tag | Track nghề nghiệp | Môn học liên quan |
|----|-----|-------------------|------------------|
| KHMT | ai_ml | AI / Học máy | 7080122, 7080508, 7080510, 7080509, 7080518, 7080124 |
| KHMT | data_engineer | Kỹ thuật dữ liệu | 7080207, 7080211, 7080509, 7080507, 7080319, 7080504 |
| KHMT | software_dev | Phát triển phần mềm | 7080208, 7080512, 7080116, 7080515, 7080111, 7080520 |
| MMT | network_engineer | Kỹ sư mạng | 7080717, 7080721, 7080720, 7080731, 7080732 |
| MMT | security_analyst | An ninh mạng | 7080703, 7080728, 7080202 |
| MMT | iot_cloud | IoT / Điện toán đám mây | 7080713, 7080517, 7080504, 7080505 |
| CNPM | backend_dev | Backend Developer | 7080108, 7080109, 7080512, 7080116 |
| CNPM | frontend_mobile | Frontend / Mobile | 7080116, 7080118, 7080115, 7080505 |
| CNPM | devops_architect | DevOps / Kiến trúc | 7080114, 7080107, 7080104, 7080123 |
| HTTT | system_analyst | Phân tích hệ thống | 7080113, 7080212, 7080204, 7080205 |
| HTTT | data_bi | Dữ liệu / BI | 7080214, 7080213, 7080215, 7080232 |
| HTTT | enterprise_dev | Phát triển HT doanh nghiệp | 7080116, 7080217, 7080202 |
| THKT | fintech | Tài chính số | 7080633, 7080626, 7080627, 7080628 |
| THKT | business_software | Phần mềm quản lý | 7080638, 7080605, 7080637 |
| THKT | data_analytics | Phân tích dữ liệu kinh tế | 7080615, 7080628, 7080631 |
| CNTTDH | gis_dev | Phát triển GIS | 7080313, 7050303, 7080309, 7080324 |
| CNTTDH | spatial_analysis | Phân tích không gian | 7050362, 7080321, 7080402, 7080408 |
| CNTTDH | geospatial_software | Phần mềm địa không gian | 7080116, 7080325, 7080307 |

---

## PHẦN 14 — MÂU THUẪN ĐÃ GIẢI QUYẾT (Changelog)

| STT | Vấn đề | Sai (tài liệu cũ) | Đúng (CTDT_CHUAN) | Nguồn xác nhận |
|-----|--------|--------------------|---------------------|----------------|
| 1 | Mã Lịch sử Đảng | 7020301 | **7020303** | Bảng điểm + xlsx cổng SV |
| 2 | Mã Pháp luật đại cương | 7020103 | **7020104** | Bảng điểm + xlsx |
| 3 | TC thực tập TN | 2 TC | **10 TC** | Bảng điểm + xlsx |
| 4 | TC đồ án TN | 8 TC | **10 TC** | Bảng điểm + xlsx |
| 5 | Ngưỡng tốt nghiệp | 143 TC | **153 TC** | Code hệ thống + yêu cầu nghiệp vụ |
| 6 | 7010610 TA tăng cường | Tính TC | **Không tính TC** | Bảng điểm 2 SV (TC HK1=17 thay vì 20) |
| 7 | CNPM chuyên đề | 7080101 | **7080102** | 7480201ver2.pdf |
| 8 | CNPM thực tập TN | 7080113_cn | **7080119** | 7480201ver2.pdf |
| 9 | CNPM đồ án TN | 7080117 | **7080110** | 7480201ver2.pdf |
| 10 | CNTTDH HK8 | chỉ 7080403 | **7080309 + 7080403** | 7480201ver2.pdf |
| 11 | 7080504 phân loại | Chuyên ngành KHMT | **Cơ sở ngành chung HK7** | 7480201ver2.pdf |
| 12 | Pool A thiếu TA Trung | Không có 7010607/608 | **Thêm 7010607, 7010608** | CTDT_ExportFromDaotao |
| 13 | Pool A HTTT | Không có 7080222 | **Thêm 7080222 (chỉ HTTT)** | ver2 + ExportFromDaotao |
| 14 | Pool B KHMT thừa môn | 7080316 trong pool B | **7080316 chỉ pool C** | CTDT_ExportFromDaotao |
| 15 | Pool C CNPM thiếu | Thiếu 7000004, 7080117, 7080120, 7080502 | **Thêm 4 môn** | 7480201ver2.pdf |
| 16 | Pool C CNPM thừa | 7080107 trong pool C | **7080107 chỉ pool B** | 7480201ver2.pdf |
| 17 | 7080230 HTTT — tên sai | "Công nghệ dữ liệu lớn" | **"Chuẩn kỹ năng sử dụng CNTT"** | CTDT_ExportFromDaotao |
| 18 | QPAN HK1 khóa 2021 | Không có 7300202 | **Thêm 7300202 Quân sự chung (3TC)** | CTDT_ExportFromDaotao |
| 19 | QPAN ver2.pdf | Khóa 2021: 4 mã HK1 | **ver2.pdf: 3 mã HK4/5/6 (7300101/7300102/7300201)** | 7480201ver2.pdf |
| 20 | CNPM compulsory sai hoàn toàn | 7080114/115/102/109 | **7080104/108/114 (HK7), 7080102/106 (HK8)** | 7480201ver2.pdf |
| 21 | CNPM pool B sai hoàn toàn | 7080104/107/108/123/505 | **8 môn: 7080107/109/115/123/234/508/510/516** | 7480201ver2.pdf |
| 22 | CNPM pool C thiếu 11 môn | 4 môn cũ sai tên | **15 môn đúng theo ver2.pdf** | 7480201ver2.pdf |
| 23 | HTTT 7080212 tên sai | Phân tích và xử lý dữ liệu | **Hệ thống phân tán** | 7480201ver2.pdf |
| 24 | HTTT 7080213 tên sai | Hệ hỗ trợ quyết định | **Học máy thống kê** | 7480201ver2.pdf |
| 25 | HTTT 7080204 tên sai | Quản lý hệ thống thông tin | **Các hệ cơ sở tri thức** | 7480201ver2.pdf |
| 26 | HTTT HK8 đồ án sai mã | 7080218 | **7080210 Đồ án HTTT** | 7480201ver2.pdf |
| 27 | HTTT HK9 sai mã | 7080203 TT, 7080201 ĐATN | **7080224 TT, 7080218 ĐATN** | 7480201ver2.pdf |
| 28 | HTTT pool B thiếu | Không có 7080202 | **Thêm 7080202 An toàn và bảo mật HTTT** | 7480201ver2.pdf |
| 29 | HTTT pool C thiếu | Không có 7080234 | **Thêm 7080234** | 7480201ver2.pdf |
| 30 | MMT pool C thiếu | 7 môn | **Thêm 7080518, 7080634 → 9 môn** | 7480201ver2.pdf |

---

## PHẦN 15 — ĐỘ TIN CẬY TỪNG PHẦN

| Phần | Độ tin cậy | Lý do |
|------|-----------|-------|
| Quy chế, thang điểm, công thức GPA | ✅ Rất cao | Xác nhận từ bảng điểm 2 SV + PDF + quy định Bộ GD |
| HK1–HK6 cơ sở ngành chung | ✅ Rất cao | Khớp cả 3 nguồn: bảng điểm + ExportFromDaotao + ver2 |
| QPAN 4 môn khóa 2021 | ✅ Cao | Xác nhận từ bảng điểm + ExportFromDaotao |
| QPAN khóa mới hơn 2022+ | ⚠️ Chưa rõ | ver2 có bộ mã khác — cần bảng điểm SV khóa 2022+ |
| KHMT chi tiết (định hướng, pool B/C) | ✅ Cao | Xác nhận từ ExportFromDaotao của SV KHMT thực tế |
| CNPM — pool B/C, compulsory HK7/8 | ✅ Cao | Đã cập nhật đầy đủ theo 7480201ver2.pdf (2026-04-23) |
| HTTT — compulsory HK7/8/9, pool B/C | ✅ Cao | Đã cập nhật đầy đủ theo 7480201ver2.pdf (2026-04-23) |
| MMT — pool C | ✅ Cao | Đã bổ sung 7080518, 7080634 theo ver2.pdf (2026-04-23) |
| THKT / CNTTDH — pool B/C | 🟡 Trung bình | Chỉ dựa PDF, chưa có bảng điểm thực tế các CN này |
| Ngưỡng 153 TC, điều kiện TN | ✅ Cao | Xác nhận từ code + yêu cầu nghiệp vụ |
| Thang xếp loại học lực | ✅ Rất cao | Quy định Bộ GD chuẩn cho mọi trường |
| Career tags | 🟡 Trung bình | Suy luận từ nội dung môn học, cần xác nhận từ doanh nghiệp |

---

## PHẦN 16 — DỮ LIỆU KIỂM CHỨNG (REGRESSION TEST)

Bảng TC tích lũy từng HK của 2 SV KHMT khóa 2021 — dùng để kiểm tra khi thay đổi logic tính TC.

### 16.1 SV Hoàng Anh — KHMT khóa 2021 (DCCTCT66_07C)

| Học kỳ | TC tích lũy | +/- | Ghi chú |
|--------|-------------|-----|--------|
| HK1 2021-2022 | 17 | — | GDTC1 + 4 QPAN không tính |
| HK2 2021-2022 | 39 | +22 | |
| HK Hè 2022 | 39 | 0 | HK hè không cộng TC |
| HK1 2022-2023 | 57 | +18 | GDTC3 không tính |
| HK2 2022-2023 | 70 | +13 | |
| HK1 2023-2024 | 81 | +11 | 7080111 điểm D vẫn tính |
| HK2 2023-2024 | 97 | +16 | 7080316 F không tính |
| HK1 2024-2025 | 119 | +22 | |
| HK2 2024-2025 | 128 | +9 | |
| HK1 2025-2026 | 144 | +16 | 7080111 học lại không cộng thêm |

### 16.2 SV Hoài Nam — KHMT khóa 2021

| Học kỳ | TC tích lũy | +/- | Ghi chú |
|--------|-------------|-----|--------|
| HK1 2021-2022 | 17 | — | |
| HK2 2021-2022 | 34 | +17 | 7010602 F không tính |
| HK1 2022-2023 | 57 | +23 | |
| HK2 2022-2023 | 72 | +15 | |
| HK1 2023-2024 | 85 | +13 | |
| HK2 2023-2024 | 107 | +22 | |
| HK1 2024-2025 | 121 | +14 | 7080507 F không tính |
| HK Hè 2025 | 121 | 0 | HK hè không cộng TC |
| HK2 2024-2025 | 133 | +12 | 7080216 học lại không cộng |
| HK1 2025-2026 | 143 | +10 | 7080512 học lại không cộng |

---

## TÓM TẮT NGUYÊN TẮC VẬN HÀNH HỆ THỐNG

1. **Tính TC:** Dùng cột "Số tín chỉ tích lũy" MAX từ file điểm, không tự tính lại
2. **Tính GPA:** Tính lại theo công thức ở Phần 3, loại GDTC/QPAN/TA tăng cường
3. **Môn học lại:** Lấy điểm cao nhất, TC chỉ tính 1 lần
4. **Tiên quyết:** Phải pass (D trở lên) — Phần 9
5. **Xếp loại học vụ:** Theo GPA tích lũy — Phần 4 & 5
6. **Giới hạn TC đăng ký:** Theo GPA — Phần 6
7. **Điều kiện TN:** 153 TC + GDTC + QPAN + tự chọn A/B/C + thực tập + đồ án — Phần 7
