import json
import os
import sqlite3
from pathlib import Path

from flask import g

DB_PATH = Path(os.environ.get("DB_PATH") or Path(__file__).parent / "instance" / "app.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    mc_uuid       TEXT UNIQUE,
    mc_name       TEXT,
    created_at    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS templates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    category    TEXT NOT NULL DEFAULT '기타',
    author_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    size_x      INTEGER NOT NULL,
    size_y      INTEGER NOT NULL,
    size_z      INTEGER NOT NULL,
    block_count INTEGER NOT NULL,
    data        TEXT NOT NULL,
    created_at  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS library (
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    template_id INTEGER NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
    added_at    INTEGER NOT NULL,
    PRIMARY KEY (user_id, template_id)
);
CREATE TABLE IF NOT EXISTS link_codes (
    code       TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    expires_at INTEGER NOT NULL
);
"""


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = connect()
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = connect()
    conn.executescript(SCHEMA)
    # 기본 템플릿 중 아직 없는 것(이름 기준)만 추가 → 기존 DB에도 새 기본 템플릿이 들어간다
    from seed import seed_templates
    import time

    existing = {r[0] for r in conn.execute("SELECT name FROM templates WHERE author_id IS NULL")}
    now = int(time.time())
    for t in seed_templates():
        if t["name"] in existing:
            continue
        sx, sy, sz = t["data"]["size"]
        conn.execute(
            "INSERT INTO templates (name, description, category, size_x, size_y, size_z,"
            " block_count, data, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (t["name"], t["description"], t["category"], sx, sy, sz,
             len(t["data"]["blocks"]), json.dumps(t["data"], separators=(",", ":")), now),
        )
    conn.commit()
    conn.close()
