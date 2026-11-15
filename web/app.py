import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import uuid as uuidlib
from functools import wraps
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

import db
import materials
import thumbnail
from template_format import TemplateError, normalize, validate

BASE = Path(__file__).parent
INSTANCE = BASE / "instance"
STATIC = BASE / "static"
LINK_CODE_TTL = 10 * 60
USERNAME_RE = re.compile(r"^[A-Za-z0-9_가-힣]{3,20}$")


def load_secret(name, env):
    """환경변수 우선, 없으면 instance/<name> 파일에서 읽고 없으면 새로 만든다."""
    if os.environ.get(env):
        return os.environ[env]
    INSTANCE.mkdir(exist_ok=True)
    path = INSTANCE / name
    if not path.exists():
        path.write_text(secrets.token_urlsafe(32), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


app = Flask(__name__, static_folder=None)
app.config.update(
    SECRET_KEY=load_secret("secret_key.txt", "SECRET_KEY"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=8 * 1024 * 1024,
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 14,
    # HTTPS로 운영할 때만 켠다(HTTP 로컬 개발에서 켜면 로그인 쿠키가 안 붙는다)
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "1",
)
if os.environ.get("TRUST_PROXY") == "1":
    # 리버스 프록시(nginx, Cloudflare Tunnel 등) 한 단계 뒤: 실제 IP·https 여부를 X-Forwarded-* 에서 읽는다
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
PLUGIN_API_KEY = load_secret("plugin_api_key.txt", "PLUGIN_API_KEY")
app.teardown_appcontext(db.close_db)


# ---------------------------------------------------------------- helpers

def err(message, status=400):
    return jsonify({"error": message}), status


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


@app.before_request
def require_json_for_writes():
    # 쿠키 기반 API에 대한 간단한 CSRF 방어: 쓰기 요청은 JSON만 허용 (폼 전송으로는 보낼 수 없음)
    if request.method in ("POST", "PUT", "DELETE") and request.path.startswith("/api/"):
        if request.content_length and not request.is_json:
            return err("Content-Type은 application/json이어야 합니다.", 415)


def current_user():
    uid = session.get("uid")
    if uid is None:
        return None
    return db.get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return err("로그인이 필요합니다.", 401)
        return fn(user, *args, **kwargs)
    return wrapper


def plugin_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        if not hmac.compare_digest(token.encode(), PLUGIN_API_KEY.encode()):
            return err("플러그인 API 키가 올바르지 않습니다.", 401)
        return fn(*args, **kwargs)
    return wrapper


def user_json(u):
    return {
        "id": u["id"],
        "username": u["username"],
        "minecraft": {"uuid": u["mc_uuid"], "name": u["mc_name"]} if u["mc_uuid"] else None,
    }


def template_summary(row, saved=None):
    out = {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "category": row["category"],
        "size": [row["size_x"], row["size_y"], row["size_z"]],
        "blockCount": row["block_count"],
        "author": row["author"] if "author" in row.keys() else None,
        "saves": row["saves"] if "saves" in row.keys() else 0,
        "createdAt": row["created_at"],
        "thumbnail": f"/api/templates/{row['id']}/thumbnail.png" if thumbnail.available() else None,
    }
    if saved is not None:
        out["saved"] = saved
    return out


TEMPLATE_SELECT = """
SELECT t.*, u.username AS author,
       (SELECT COUNT(*) FROM library l WHERE l.template_id = t.id) AS saves
FROM templates t LEFT JOIN users u ON u.id = t.author_id
"""


# ---------------------------------------------------------------- auth

@app.post("/api/auth/register")
def register():
    data = body()
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    if not USERNAME_RE.match(username):
        return err("아이디는 3~20자의 영문, 숫자, 한글, _ 만 사용할 수 있습니다.")
    if not 8 <= len(password) <= 128:
        return err("비밀번호는 8자 이상이어야 합니다.")
    conn = db.get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), int(time.time())),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return err("이미 사용 중인 아이디입니다.", 409)
    session.clear()
    session.permanent = True
    session["uid"] = cur.lastrowid
    return jsonify(user_json(current_user())), 201


# shortcut: 실패 기록을 프로세스 메모리에 둔다(재시작하면 초기화, 워커 1개 기준). 워커를 늘리면 DB로 옮긴다.
LOGIN_WINDOW = 10 * 60
LOGIN_MAX_FAILS = {"ip": 20, "user": 5}
_login_fails = {}


def _recent_fails(key, now):
    times = [t for t in _login_fails.get(key, []) if now - t < LOGIN_WINDOW]
    _login_fails[key] = times
    return times


@app.post("/api/auth/login")
def login():
    data = body()
    username = str(data.get("username", "")).strip()
    now = time.time()
    keys = {"ip": ("ip", request.remote_addr), "user": ("user", username.lower())}
    if any(len(_recent_fails(k, now)) >= LOGIN_MAX_FAILS[kind] for kind, k in keys.items()):
        return err("로그인 시도가 너무 많습니다. 10분 뒤에 다시 시도해 주세요.", 429)
    user = db.get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], str(data.get("password", ""))):
        for k in keys.values():
            _login_fails[k].append(now)
        return err("아이디 또는 비밀번호가 올바르지 않습니다.", 401)
    _login_fails.pop(keys["user"], None)
    session.clear()
    session.permanent = True
    session["uid"] = user["id"]
    return jsonify(user_json(user))


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/auth/me")
def me():
    user = current_user()
    return jsonify(user_json(user) if user else None)


# ---------------------------------------------------------------- templates

@app.get("/api/templates")
def list_templates():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    sql, params = TEMPLATE_SELECT + " WHERE 1=1", []
    if q:
        sql += " AND (t.name LIKE ? OR t.description LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if category:
        sql += " AND t.category = ?"
        params.append(category)
    sort = request.args.get("sort", "new")
    sql += " ORDER BY saves DESC, t.id DESC" if sort == "popular" else " ORDER BY t.id DESC"
    conn = db.get_db()
    rows = conn.execute(sql, params).fetchall()
    user = current_user()
    saved = set()
    if user:
        saved = {r[0] for r in conn.execute(
            "SELECT template_id FROM library WHERE user_id = ?", (user["id"],))}
    cats = [r[0] for r in conn.execute("SELECT DISTINCT category FROM templates ORDER BY category")]
    return jsonify({
        "templates": [template_summary(r, r["id"] in saved if user else None) for r in rows],
        "categories": cats,
    })


@app.get("/api/templates/<int:tid>")
def get_template(tid):
    row = db.get_db().execute(TEMPLATE_SELECT + " WHERE t.id = ?", (tid,)).fetchone()
    if row is None:
        return err("템플릿을 찾을 수 없습니다.", 404)
    user = current_user()
    saved = None
    if user:
        saved = db.get_db().execute(
            "SELECT 1 FROM library WHERE user_id = ? AND template_id = ?", (user["id"], tid)
        ).fetchone() is not None
    out = template_summary(row, saved)
    out["data"] = json.loads(row["data"])
    out["materials"] = materials.materials(out["data"])
    out["mine"] = bool(user and row["author_id"] == user["id"])
    return jsonify(out)


@app.get("/api/templates/<int:tid>/thumbnail.png")
def template_thumbnail(tid):
    """실제 블록 텍스처로 그린 썸네일. ?rot=0~3 (보는 방향), ?maxY= (그 높이까지만)"""
    if not thumbnail.available():
        return err("썸네일용 블록 에셋이 없습니다. tools/fetch_assets.py 를 실행하세요.", 404)
    row = db.get_db().execute("SELECT data FROM templates WHERE id = ?", (tid,)).fetchone()
    if row is None:
        return err("템플릿을 찾을 수 없습니다.", 404)
    rot = request.args.get("rot", 0, type=int) % 4
    max_y = request.args.get("maxY", type=int)
    path = thumbnail.thumbnail_path(tid, row["data"], rot, max_y)
    resp = send_file(path, mimetype="image/png", conditional=True, max_age=0)
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.get("/api/items/<item>/icon.png")
def item_icon(item):
    """재료 목록용 아이템 아이콘: 아이템 그림이 있으면 그것, 블록 아이템은 입체 블록."""
    if not thumbnail.available():
        return err("아이콘이 없습니다.", 404)
    path = materials.icon_path(item)
    if path is None:
        return err("아이콘이 없습니다.", 404)
    return send_file(path, mimetype="image/png", max_age=86400)


@app.get("/api/blocks/icon.png")
def block_icon():
    """?state=minecraft:oak_stairs[...] → 그 블록의 실제 텍스처 (첫 프레임)."""
    if not thumbnail.available():
        return err("아이콘이 없습니다.", 404)
    try:
        state = normalize(request.args.get("state", ""))  # 26.3 에 있는 블록만, 전체 상태로
    except TemplateError:
        return err("아이콘이 없습니다.", 404)
    path = thumbnail.icon_texture(state)
    if path is None or not path.resolve().is_relative_to(thumbnail.ASSETS.resolve()):
        return err("아이콘이 없습니다.", 404)
    img = thumbnail.texture(path.relative_to(thumbnail.ASSETS / "textures").with_suffix("").as_posix())
    if img is None:
        return err("아이콘이 없습니다.", 404)
    import io
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    resp = send_file(buf, mimetype="image/png", max_age=86400)
    return resp


def prerender_thumbnails():
    """서버 시작 시 모든 템플릿의 기본 썸네일을 미리 그려둔다 (백그라운드)."""
    if not thumbnail.available():
        return
    conn = db.connect()
    rows = conn.execute("SELECT id, data FROM templates").fetchall()
    conn.close()
    for r in rows:
        try:
            thumbnail.thumbnail_path(r["id"], r["data"])
        except Exception as e:  # 한 템플릿 실패가 서버를 멈추지 않도록
            app.logger.warning("썸네일 생성 실패 (#%s): %s", r["id"], e)


@app.post("/api/templates")
@login_required
def create_template(user):
    return insert_template(user, body())


def insert_template(user, data):
    name = str(data.get("name", "")).strip()
    if not 1 <= len(name) <= 40:
        return err("이름은 1~40자여야 합니다.")
    description = str(data.get("description", "")).strip()[:500]
    category = str(data.get("category", "기타")).strip()[:20] or "기타"
    try:
        tpl = validate(data.get("data"))
    except TemplateError as e:
        return err(str(e))
    conn = db.get_db()
    cur = conn.execute(
        "INSERT INTO templates (name, description, category, author_id, size_x, size_y, size_z,"
        " block_count, data, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (name, description, category, user["id"], *tpl["size"], len(tpl["blocks"]),
         json.dumps(tpl, separators=(",", ":")), int(time.time())),
    )
    # 업로드한 템플릿은 자동으로 내 보관함에 추가
    conn.execute("INSERT INTO library (user_id, template_id, added_at) VALUES (?,?,?)",
                 (user["id"], cur.lastrowid, int(time.time())))
    conn.commit()
    if thumbnail.available():
        import threading
        threading.Thread(target=thumbnail.thumbnail_path,
                         args=(cur.lastrowid, json.dumps(tpl, separators=(",", ":"))), daemon=True).start()
    return jsonify({"id": cur.lastrowid}), 201


@app.delete("/api/templates/<int:tid>")
@login_required
def delete_template(user, tid):
    conn = db.get_db()
    cur = conn.execute("DELETE FROM templates WHERE id = ? AND author_id = ?", (tid, user["id"]))
    conn.commit()
    if cur.rowcount == 0:
        return err("내가 올린 템플릿만 삭제할 수 있습니다.", 403)
    return jsonify({"ok": True})


# ---------------------------------------------------------------- library (보관함)

@app.get("/api/library")
@login_required
def get_library(user):
    rows = db.get_db().execute(
        TEMPLATE_SELECT + " JOIN library lib ON lib.template_id = t.id AND lib.user_id = ?"
        " ORDER BY lib.added_at, t.id", (user["id"],)
    ).fetchall()
    return jsonify([template_summary(r, True) for r in rows])


@app.post("/api/library/<int:tid>")
@login_required
def add_to_library(user, tid):
    conn = db.get_db()
    if conn.execute("SELECT 1 FROM templates WHERE id = ?", (tid,)).fetchone() is None:
        return err("템플릿을 찾을 수 없습니다.", 404)
    conn.execute("INSERT OR IGNORE INTO library (user_id, template_id, added_at) VALUES (?,?,?)",
                 (user["id"], tid, int(time.time())))
    conn.commit()
    return jsonify({"ok": True})


@app.delete("/api/library/<int:tid>")
@login_required
def remove_from_library(user, tid):
    conn = db.get_db()
    conn.execute("DELETE FROM library WHERE user_id = ? AND template_id = ?", (user["id"], tid))
    conn.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------- 마인크래프트 계정 연동 (웹 쪽)

@app.post("/api/link/code")
@login_required
def create_link_code(user):
    conn = db.get_db()
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 헷갈리는 0/O, 1/I 제외
    conn.execute("DELETE FROM link_codes WHERE user_id = ? OR expires_at < ?",
                 (user["id"], int(time.time())))
    for _ in range(10):
        code = "".join(secrets.choice(alphabet) for _ in range(6))
        try:
            conn.execute("INSERT INTO link_codes (code, user_id, expires_at) VALUES (?,?,?)",
                         (code, user["id"], int(time.time()) + LINK_CODE_TTL))
            break
        except sqlite3.IntegrityError:
            continue
    else:
        return err("코드 생성에 실패했습니다. 다시 시도해주세요.", 500)
    conn.commit()
    return jsonify({"code": code, "expiresIn": LINK_CODE_TTL})


@app.delete("/api/link")
@login_required
def unlink_web(user):
    conn = db.get_db()
    conn.execute("UPDATE users SET mc_uuid = NULL, mc_name = NULL WHERE id = ?", (user["id"],))
    conn.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------- 플러그인 전용 API

def parse_uuid(value):
    try:
        return str(uuidlib.UUID(value))
    except (ValueError, TypeError, AttributeError):
        resp = jsonify({"error": "잘못된 UUID 입니다."})
        resp.status_code = 400
        abort(resp)


def linked_user(mc_uuid):
    return db.get_db().execute("SELECT * FROM users WHERE mc_uuid = ?", (mc_uuid,)).fetchone()


@app.post("/api/plugin/link")
@plugin_auth
def plugin_link():
    data = body()
    code = str(data.get("code", "")).strip().upper()
    mc_uuid = parse_uuid(data.get("uuid"))
    mc_name = str(data.get("name", ""))[:16]
    conn = db.get_db()
    # 조회와 소비를 한 문장으로: 같은 코드로 동시에 두 번 요청해도 한 번만 성공한다
    row = conn.execute("DELETE FROM link_codes WHERE code = ? AND expires_at >= ? RETURNING user_id",
                       (code, int(time.time()))).fetchone()
    if row is None:
        conn.commit()
        return err("연동 코드가 없거나 만료되었습니다. 웹사이트에서 새 코드를 발급받으세요.", 404)
    # 이 마인크래프트 계정이 다른 웹 계정에 연결돼 있었다면 해제하고 새로 연결
    conn.execute("UPDATE users SET mc_uuid = NULL, mc_name = NULL WHERE mc_uuid = ?", (mc_uuid,))
    conn.execute("UPDATE users SET mc_uuid = ?, mc_name = ? WHERE id = ?",
                 (mc_uuid, mc_name, row["user_id"]))
    conn.commit()
    user = conn.execute("SELECT username FROM users WHERE id = ?", (row["user_id"],)).fetchone()
    return jsonify({"username": user["username"]})


@app.get("/api/plugin/players/<mc_uuid>")
@plugin_auth
def plugin_player(mc_uuid):
    user = linked_user(parse_uuid(mc_uuid))
    if user is None:
        return err("연동되지 않은 플레이어입니다.", 404)
    return jsonify({"username": user["username"]})


@app.post("/api/plugin/players/<mc_uuid>/unlink")
@plugin_auth
def plugin_unlink(mc_uuid):
    conn = db.get_db()
    cur = conn.execute("UPDATE users SET mc_uuid = NULL, mc_name = NULL WHERE mc_uuid = ?",
                       (parse_uuid(mc_uuid),))
    conn.commit()
    if cur.rowcount == 0:
        return err("연동되지 않은 플레이어입니다.", 404)
    return jsonify({"ok": True})


@app.get("/api/plugin/players/<mc_uuid>/library")
@plugin_auth
def plugin_library(mc_uuid):
    user = linked_user(parse_uuid(mc_uuid))
    if user is None:
        return err("연동되지 않은 플레이어입니다.", 404)
    rows = db.get_db().execute(
        TEMPLATE_SELECT + " JOIN library lib ON lib.template_id = t.id AND lib.user_id = ?"
        " ORDER BY lib.added_at, t.id", (user["id"],)
    ).fetchall()
    return jsonify({"username": user["username"],
                    "templates": [template_summary(r) for r in rows]})


@app.get("/api/plugin/players/<mc_uuid>/templates/<int:tid>")
@plugin_auth
def plugin_template(mc_uuid, tid):
    user = linked_user(parse_uuid(mc_uuid))
    if user is None:
        return err("연동되지 않은 플레이어입니다.", 404)
    row = db.get_db().execute(
        "SELECT t.* FROM templates t JOIN library l ON l.template_id = t.id"
        " WHERE l.user_id = ? AND t.id = ?", (user["id"], tid)
    ).fetchone()
    if row is None:
        return err("보관함에 없는 템플릿입니다.", 404)
    return jsonify({"id": row["id"], "name": row["name"], "data": json.loads(row["data"])})


@app.post("/api/plugin/players/<mc_uuid>/templates")
@plugin_auth
def plugin_upload(mc_uuid):
    """인게임에서 잡은 영역을 템플릿으로 업로드 (/tb save)."""
    user = linked_user(parse_uuid(mc_uuid))
    if user is None:
        return err("연동되지 않은 플레이어입니다.", 404)
    return insert_template(user, body())


# ---------------------------------------------------------------- 정적 페이지

PAGES = {"": "index.html", "login": "login.html", "register": "register.html",
         "library": "library.html", "upload": "upload.html", "template": "template.html"}


@app.get("/")
@app.get("/<page>")
def page(page=""):
    if page in PAGES:
        return send_from_directory(STATIC, PAGES[page])
    return send_from_directory(STATIC, page)


@app.errorhandler(404)
def not_found(_e):
    if request.path.startswith("/api/"):
        return err("찾을 수 없습니다.", 404)
    return send_from_directory(STATIC, "index.html"), 404


db.init_db()

if __name__ == "__main__":
    import threading
    threading.Thread(target=prerender_thumbnails, daemon=True).start()
    if not thumbnail.available():
        print("※ 블록 에셋이 없어 단순 미리보기로 표시됩니다. 실제 텍스처 썸네일: python tools/fetch_assets.py")
    print(f"플러그인 API 키: {PLUGIN_API_KEY}  (instance/plugin_api_key.txt)")
    host, port = os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", 5000))
    if os.environ.get("PRODUCTION") == "1":
        from waitress import serve
        print(f"운영 서버(waitress) 시작: http://{host}:{port}")
        serve(app, host=host, port=port, threads=8)
    else:
        app.run(host=host, port=port)
