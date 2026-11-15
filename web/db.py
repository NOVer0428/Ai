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
-- 회원마다 하나씩 발급하는 마인크래프트 서버 키. 원문은 저장하지 않고 sha256 해시만 둔다
CREATE TABLE IF NOT EXISTS server_keys (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    key_hash   TEXT NOT NULL UNIQUE,
    prefix     TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
-- 마인크래프트 서버. 회원은 여러 서버를 등록할 수 있고 서버마다 키가 다르다.
-- is_operator=1 은 사이트 운영자 키(plugin_api_key.txt)용 서버 한 줄 (owner·key_hash 없음)
CREATE TABLE IF NOT EXISTS servers (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id     INTEGER REFERENCES users(id) ON DELETE CASCADE,
    key_hash     TEXT UNIQUE,
    prefix       TEXT,
    name         TEXT,              -- 플러그인 config 의 server-name. 비어 있으면 화면에 "Minecraft Server (N)"
    is_operator  INTEGER NOT NULL DEFAULT 0,
    created_at   INTEGER NOT NULL,
    last_seen_at INTEGER
);
-- 플레이어가 서버마다 따로 하는 인게임 연동. 새 서버에서 연동할 때마다 한 줄씩 는다
CREATE TABLE IF NOT EXISTS server_links (
    user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    server_id INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    mc_uuid   TEXT NOT NULL,
    mc_name   TEXT,
    linked_at INTEGER NOT NULL,
    PRIMARY KEY (user_id, server_id),
    UNIQUE (server_id, mc_uuid)
);
"""


def operator_server_id(conn):
    row = conn.execute("SELECT id FROM servers WHERE is_operator = 1").fetchone()
    if row:
        return row[0]
    import time
    return conn.execute("INSERT INTO servers (is_operator, created_at) VALUES (1, ?)", (int(time.time()),)).lastrowid


def migrate_links(conn):
    """옛 구조(회원당 서버 키 1개, users.mc_uuid 에 연동 1개)를 servers / server_links 로 옮긴다. 한 번만 실행."""
    conn.execute("INSERT OR IGNORE INTO servers (id, owner_id, key_hash, prefix, created_at)"
                 " SELECT id, user_id, key_hash, prefix, created_at FROM server_keys")
    op = operator_server_id(conn)
    for uid, uuid, name, key_id, now in conn.execute(
            "SELECT id, mc_uuid, mc_name, link_key_id, created_at FROM users WHERE mc_uuid IS NOT NULL").fetchall():
        conn.execute("INSERT OR IGNORE INTO server_links (user_id, server_id, mc_uuid, mc_name, linked_at)"
                     " VALUES (?, ?, ?, ?, ?)", (uid, key_id or op, uuid, name, now))
    conn.execute("UPDATE users SET mc_uuid = NULL, mc_name = NULL, link_key_id = NULL")

# 기존 DB에 나중에 추가된 열 (없으면 ALTER TABLE 로 붙인다)
TEMPLATE_COLUMNS = {
    "active": "INTEGER NOT NULL DEFAULT 1",  # 0 = 관리자가 비활성화: 일반 사용자에게 숨김
}
USER_COLUMNS = {
    "active": "INTEGER NOT NULL DEFAULT 1",  # 0 = 관리자가 비활성화: 로그인·플러그인 차단
    "email": "TEXT",
    "verified_at": "INTEGER",       # NULL 이고 email 이 있으면 인증 전. 이메일 없는 옛 계정은 인증 면제
    "verify_sent_at": "INTEGER",
    "verify_code_hash": "TEXT",          # 메일로 보낸 6자리 코드의 해시 (verify_sent_at 기준으로 만료)
    "verify_attempts": "INTEGER NOT NULL DEFAULT 0",
    "avatar_ver": "INTEGER",
    "role": "TEXT",                    # 'sub_admin' = 부 관리자. 메인 관리자는 ADMIN_USERS 환경변수로 정한다             # 프로필 이미지 버전(올린 시각). NULL 이면 이미지 없음
    "link_key_id": "INTEGER REFERENCES server_keys(id) ON DELETE SET NULL",  # 어느 서버 키로 연동했는지
}


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
    had_links = conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'server_links'").fetchone()
    conn.executescript(SCHEMA)
    for table, columns in (("users", USER_COLUMNS), ("templates", TEMPLATE_COLUMNS)):
        have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}
        for name, decl in columns.items():
            if name not in have:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_email ON users(email COLLATE NOCASE)")
    if not had_links:
        migrate_links(conn)
    # 기본 템플릿(작성자 없음)을 코드와 맞춘다: 없으면 추가, 내용이 바뀌었으면 갱신 (이름 기준)
    from seed import seed_templates
    import time

    existing = {r[0]: r[1] for r in conn.execute(
        "SELECT name, data FROM templates WHERE author_id IS NULL")}
    now = int(time.time())
    seeds = seed_templates()
    # 코드에서 빠진 기본 템플릿은 DB 에서도 지운다 (사용자가 올린 템플릿은 건드리지 않음)
    names = {t["name"] for t in seeds}
    for old in set(existing) - names:
        conn.execute("DELETE FROM templates WHERE name = ? AND author_id IS NULL", (old,))
    for t in seeds:
        sx, sy, sz = t["data"]["size"]
        data = json.dumps(t["data"], separators=(",", ":"))
        values = (t["description"], t["category"], sx, sy, sz, len(t["data"]["blocks"]), data)
        if t["name"] not in existing:
            conn.execute(
                "INSERT INTO templates (description, category, size_x, size_y, size_z,"
                " block_count, data, name, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (*values, t["name"], now),
            )
        elif existing[t["name"]] != data:
            conn.execute(
                "UPDATE templates SET description=?, category=?, size_x=?, size_y=?, size_z=?,"
                " block_count=?, data=? WHERE name=? AND author_id IS NULL",
                (*values, t["name"]),
            )
    conn.commit()
    conn.close()
