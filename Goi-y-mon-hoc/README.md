# EduGuide HUMG

Hệ thống gợi ý môn học và theo dõi tiến độ học tập cho sinh viên ngành CNTT (7480201) — Đại học Mỏ - Địa chất.

## Cách chạy

```bash
# 1. Cài dependencies
cd backend
pip install -r requirements.txt

# 2. Tạo file .env (copy từ .env.example)
cp .env.example .env  # điền DATABASE_URL, API keys

# 3. Chạy migration
python -m backend.db.migrate

# 4. Khởi động server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Hoặc chạy `start.bat` (Windows).

## Cấu trúc thư mục

```
Goi-y-mon-hoc/
├── backend/
│   ├── core/           Logic nghiệp vụ chính (engine, AI, ML, parser)
│   ├── db/             Models, schemas, migrations, kết nối DB
│   ├── scripts/        Import dữ liệu, seed, công cụ CLI
│   ├── main.py         FastAPI app — 100+ routes
│   └── requirements.txt
├── frontend/
│   └── pages/          index.html, home.html, advisor.html, admin.html
├── data/
│   ├── ctdt/           Chương trình đào tạo (markdown + PDF gốc)
│   ├── grades/         File điểm mẫu
│   ├── reference/      Tài liệu tham khảo, ảnh CTDT
│   └── test_scenarios/ Kịch bản kiểm thử 8 SV mẫu
├── tests/              Pytest — integration tests
├── docs/               MASTER_SPEC, UI specs, CLAUDE.md
└── .env                Cấu hình môi trường (không commit)
```

## Tech stack

- **Backend:** FastAPI + SQLAlchemy + PostgreSQL
- **ML:** GradientBoostingClassifier (scikit-learn)
- **AI:** Gemini 2.0 Flash → Groq llama-3.3-70b → OpenAI gpt-4o-mini → Claude
- **Frontend:** HTML/CSS/JS thuần + Tailwind CDN
