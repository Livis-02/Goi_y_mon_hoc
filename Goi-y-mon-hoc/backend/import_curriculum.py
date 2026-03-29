from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.db import SessionLocal
from backend.curriculum_importer import import_curriculum_from_excel


def main() -> int:
    parser = argparse.ArgumentParser(description="Import curriculum courses from docx/xlsx/csv into DB")
    parser.add_argument("--file", default="data/7480201.docx", help="Path to curriculum file")
    parser.add_argument("--program-code", default="7480201", help="Default program code")
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Delete non-imported courses that are not referenced by user_grades",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        stats = import_curriculum_from_excel(
            db,
            file_path=args.file,
            replace_existing=args.replace_existing,
            default_program_code=args.program_code,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("file:", stats.file_path)
    print("program_code:", stats.program_code)
    print("parsed_courses:", stats.parsed_courses)
    print("inserted_courses:", stats.inserted_courses)
    print("updated_courses:", stats.updated_courses)
    print("deleted_courses:", stats.deleted_courses)
    print("protected_courses:", stats.protected_courses)
    print("inserted_rules:", stats.inserted_rules)
    print("updated_rules:", stats.updated_rules)
    print("assumptions:")
    for item in stats.assumptions:
        print("-", item)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
