# EduGuide — Tài liệu

```
docs/
├── README.md          ─ (file này) index
└── DEFENSE_DEMO.md    ─ Script demo 15-20' cho hội đồng bảo vệ
```

## Khi nào đọc cái gì

| Cần | Đọc |
|---|---|
| Demo trước hội đồng | [`DEFENSE_DEMO.md`](DEFENSE_DEMO.md) |
| Bộ dữ liệu Excel để upload qua admin UI | [`../data/demo/README.md`](../data/demo/README.md) |
| Architecture / code map | [`../CLAUDE.md`](../CLAUDE.md) |

## Quick reset toàn bộ demo state

```bash
# Tạo lại 10 SV + 10 GV + 10 phân công + 10 file điểm XLSX (idempotent, ~30s)
python -m backend.scripts.generate_demo_data --reset

# Restart backend
uvicorn backend.main:app --reload --port 8000
```

Mật khẩu chung: `Test1234!` (mọi user trong bộ demo).
