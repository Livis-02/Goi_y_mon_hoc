import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load env files — .env trước (defaults), AIKEY.env sau (override API keys)
# backend/db/db.py → .parent×3 = project root
_root = Path(__file__).resolve().parent.parent.parent
for _env_name in (".env", "AIKEY.env"):
    _env_file = _root / _env_name
    if _env_file.exists():
        for _line in _env_file.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                _k, _v = _k.strip(), _v.strip()
                # AIKEY.env luôn override; .env chỉ set nếu chưa có
                if _env_name == "AIKEY.env":
                    os.environ[_k] = _v
                else:
                    os.environ.setdefault(_k, _v)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://app_user:0212@localhost:5432/goi_y_mon_hoc")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,        # kiểm tra kết nối còn sống trước khi dùng
    pool_recycle=1800,         # recycle connection sau 30 phút
    connect_args={"connect_timeout": 10},  # timeout kết nối DB 10s
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
