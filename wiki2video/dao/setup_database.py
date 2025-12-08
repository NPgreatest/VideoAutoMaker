#!/usr/bin/env python3
"""
Initialize SQLite database from fixed schema SQL file.
"""

import sqlite3
from pathlib import Path


SCHEMA_FILE = Path("db/schema/working_blocks.sql")
DB_PATH = Path("db/working_blocks.db")


def setup_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not SCHEMA_FILE.exists():
        raise FileNotFoundError(f"Schema file not found: {SCHEMA_FILE}")

    schema_sql = SCHEMA_FILE.read_text()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(schema_sql)
    conn.commit()
    conn.close()

    print(f"🎉 Database initialized at: {DB_PATH.absolute()}")


if __name__ == "__main__":
    setup_database()
