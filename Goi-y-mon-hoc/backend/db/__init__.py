# Re-export DB essentials so `from backend.db import get_db, engine, Base` still works
from .db import get_db, engine, Base, SessionLocal  # noqa: F401
