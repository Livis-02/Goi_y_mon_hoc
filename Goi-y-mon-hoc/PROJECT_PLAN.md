# PROJECT_PLAN

## 1) Project Snapshot
- Project: Web app goi y mon hoc va ho tro theo doi tien do hoc tap cho sinh vien nganh CNTT.
- Program scope: CNTT (ma nganh 7480201), co nhieu chuyen nganh ben trong (KHMT, ATTT, HTTT, Mang, CNPM, ...).
- Working repo: e:\Do_an\Goi-y-mon-hoc
- Main objective: lam dung nghiep vu truoc, code sau; uu tien hieu ro va bam sat khung do an.

## 2) Confirmed Decisions
1. Co tai khoan dang ky/dang nhap cho sinh vien.
2. Luu bang diem theo tai khoan.
3. Mon trong bang diem phai co trong CTDT (doi chieu theo ma mon/ten mon theo rule da thong nhat).
4. Co actor Admin de quan ly CTDT khi co thay doi.
5. GPA trong file diem neu da co san thi uu tien doc tu file; tinh lai GPA la tuy chon khi can.
6. Tien do hoan thanh khac voi uoc tinh thoi gian ra truong:
   - Tien do: trang thai hien tai (da dat/thi?u bao nhieu).
   - Uoc tinh ra truong: du bao tuong lai theo toc do hoc.

## 3) Upload Matching Rule (Critical)
Khi sinh vien upload bang diem:
1. Match theo `course_code` truoc.
2. Neu khong co/khong khop ma mon, fallback match theo `course_name` (normalize lowercase + trim).
3. Neu khong khop ca hai: danh dau `Mon khong co trong CTDT` (mau do tren UI).
4. Mon khong hop le khong duoc tinh vao tien do CTDT; xu ly GPA theo rule tung man hinh.

## 4) Thesis Outline (Approved Structure)
1. Phan mo dau
2. Chuong 1: Tong quan de tai
3. Chuong 2: Co so ly thuyet va cong nghe
4. Chuong 3: Phan tich yeu cau he thong
5. Chuong 4: Thiet ke he thong
6. Chuong 5: Cai dat va trien khai
7. Chuong 6: Kiem thu va danh gia
8. Ket luan va huong phat trien
9. Tai lieu tham khao
10. Phu luc

## 5) Target Database Design
### 5.1 users
- id BIGSERIAL PK
- email TEXT UNIQUE NOT NULL
- password_hash TEXT NOT NULL
- full_name TEXT
- created_at TIMESTAMP DEFAULT NOW()

### 5.2 courses (CTDT)
- id BIGSERIAL PK
- program_code TEXT NOT NULL
- specialization TEXT
- group_type TEXT  -- required/elective_A/elective_B/elective_C
- course_code TEXT NOT NULL UNIQUE
- course_name TEXT NOT NULL
- credits NUMERIC(4,1)
- term TEXT

### 5.3 user_grades
- id BIGSERIAL PK
- user_id BIGINT NOT NULL FK -> users(id)
- course_code TEXT NOT NULL FK -> courses(course_code)
- score10 NUMERIC(4,2)
- score4 NUMERIC(3,2)
- letter TEXT
- passed BOOLEAN DEFAULT FALSE
- term TEXT
- uploaded_at TIMESTAMP DEFAULT NOW()
- UNIQUE(user_id, course_code, term)

### 5.4 study_plans
- id BIGSERIAL PK
- user_id BIGINT NOT NULL FK -> users(id)
- plan_name TEXT NOT NULL
- target_gpa NUMERIC(3,2)
- max_credits_per_term NUMERIC(4,1)
- created_at TIMESTAMP DEFAULT NOW()

### 5.5 study_plan_items
- id BIGSERIAL PK
- plan_id BIGINT NOT NULL FK -> study_plans(id)
- course_code TEXT NOT NULL FK -> courses(course_code)
- term_label TEXT

## 6) Entity Relationships
1. users (1) -> (N) user_grades
2. users (1) -> (N) study_plans
3. study_plans (1) -> (N) study_plan_items
4. courses (1) -> (N) user_grades
5. courses (1) -> (N) study_plan_items

## 7) Use Case Direction (Current)
- Actor: Sinh vien, Admin
- Sinh vien: dang ky/dang nhap, chon chuyen nganh, upload bang diem, xem tien do, nhap muc tieu GPA, nhan goi y diem can dat, uoc tinh ra truong.
- Admin: quan ly CTDT (them/sua/xoa mon).
- Upload bang diem include kiem tra khop mon voi CTDT.

## 8) Delivery Strategy
- Lam theo thu tu: phan tich -> thiet ke -> diagram -> implementation -> test -> viet bao cao.
- Khong mo rong scope truoc khi chot xong chuong dang lam.
- Moi thay doi nghiep vu phai cap nhat file nay truoc.

## 9) How To Continue In A New Chat
Dung cau nay de tiep tuc nhanh:
"Hay doc file PROJECT_PLAN.md trong repo e:\Do_an\Goi-y-mon-hoc va tiep tuc tu muc [ghi muc can lam]."

## 10) Next Suggested Step
- Ve tiep bo diagram quan trong theo dung khung:
  1) Use case tong quan (chot)
  2) Use case chi tiet Upload bang diem
  3) Sequence upload + validate CTDT
  4) ERD chuan PK/FK
  5) Activity tien do + goi y
