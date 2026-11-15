import hashlib
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

from flask import Flask, abort, g, jsonify, redirect, request, send_file, send_from_directory, session
from itsdangerous import BadSignature, URLSafeTimedSerializer
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


# 관리자 아이디 목록 (쉼표로 구분, 대소문자 무시). 예: ADMIN_USERS=noha04
ADMINS = {n.strip().lower() for n in os.environ.get("ADMIN_USERS", "").split(",") if n.strip()}


def is_admin(user):
    return bool(user) and user["username"].lower() in ADMINS


def current_user():
    uid = session.get("uid")
    if uid is None:
        return None
    # 비활성화된 계정은 이미 로그인한 세션도 바로 끊긴다
    return db.get_db().execute("SELECT * FROM users WHERE id = ? AND active = 1", (uid,)).fetchone()


def can_see_template(row, user):
    """비활성 템플릿은 관리자와 작성자 본인만 본다."""
    return bool(row["active"]) or is_admin(user) or bool(user and row["author_id"] == user["id"])


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return err("로그인이 필요합니다.", 401)
        return fn(user, *args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return err("로그인이 필요합니다.", 401)
        if not is_admin(user):
            return err("관리자만 할 수 있습니다.", 403)
        return fn(user, *args, **kwargs)
    return wrapper


def hash_key(token):
    return hashlib.sha256(token.encode()).hexdigest()


def plugin_auth(fn):
    """플러그인 인증. g.key_id: 회원 서버 키면 그 키의 id(자기 서버에서 연동한 플레이어만),
    사이트 운영자 키(PLUGIN_API_KEY)면 None(전체)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        if token and hmac.compare_digest(token.encode(), PLUGIN_API_KEY.encode()):
            g.key_id = None
        else:
            row = token and db.get_db().execute(
                "SELECT k.id FROM server_keys k JOIN users u ON u.id = k.user_id"
                " WHERE k.key_hash = ? AND u.active = 1", (hash_key(token),)).fetchone()
            if not row:
                return err("플러그인 API 키가 올바르지 않습니다.", 401)
            g.key_id = row["id"]
        return fn(*args, **kwargs)
    return wrapper


def user_json(u):
    return {
        "id": u["id"],
        "username": u["username"],
        "email": u["email"],
        "isAdmin": is_admin(u),
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
        "active": bool(row["active"]),
        "builtin": row["author_id"] is None,
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

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]+$")
VERIFY_TTL = 24 * 60 * 60
RESEND_GAP = 10 * 60  # 남의 이메일로 가입해 로그인을 반복하는 메일 폭탄 완화
verify_tokens = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="email-verify")


def send_mail(to, subject, text):
    """MAIL_USER/MAIL_PASSWORD(Gmail 앱 비밀번호)가 있으면 SMTP로 보내고, 없으면 로그에 찍는다(개발용)."""
    user, password = os.environ.get("MAIL_USER"), os.environ.get("MAIL_PASSWORD")
    if not (user and password):
        print(f"[메일 미설정] 받는 사람 {to} / {subject}\n{text}", flush=True)
        return
    import smtplib
    from email.message import EmailMessage
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = f"블루프린트 <{user}>", to, subject
    msg.set_content(text)
    with smtplib.SMTP(os.environ.get("MAIL_HOST", "smtp.gmail.com"),
                      int(os.environ.get("MAIL_PORT", 587)), timeout=20) as s:
        s.starttls()
        s.login(user, password)
        s.send_message(msg)


def send_verify_mail(user_id, email):
    token = verify_tokens.dumps({"uid": user_id, "email": email})
    link = request.host_url.rstrip("/") + "/verify?token=" + token
    send_mail(email, "[블루프린트] 이메일 인증",
              f"아래 링크를 누르면 가입이 완료됩니다. 링크는 24시간 동안 유효합니다.\n\n{link}\n\n"
              "직접 가입하지 않았다면 이 메일을 무시하세요.")
    db.get_db().execute("UPDATE users SET verify_sent_at = ? WHERE id = ?", (int(time.time()), user_id))
    db.get_db().commit()


def mask_email(email):
    name, _, domain = email.partition("@")
    return name[:2] + "*" * max(1, len(name) - 2) + "@" + domain


@app.post("/api/auth/register")
def register():
    data = body()
    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip()
    password = str(data.get("password", ""))
    if not USERNAME_RE.match(username):
        return err("아이디는 3~20자의 영문, 숫자, 한글, _ 만 사용할 수 있습니다.")
    if len(email) > 254 or not EMAIL_RE.match(email):
        return err("올바른 이메일 주소를 입력해 주세요.")
    if not 8 <= len(password) <= 128:
        return err("비밀번호는 8자 이상이어야 합니다.")
    conn = db.get_db()
    # 링크 유효시간이 지나도록 인증하지 않은 가입은 지워서 아이디·이메일을 다시 쓸 수 있게 한다
    conn.execute("DELETE FROM users WHERE email IS NOT NULL AND verified_at IS NULL AND created_at < ?",
                 (int(time.time()) - VERIFY_TTL,))
    taken = conn.execute("SELECT username = ? COLLATE NOCASE FROM users"
                         " WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE",
                         (username, username, email)).fetchone()
    if taken:
        return err("이미 사용 중인 아이디입니다." if taken[0] else "이미 가입된 이메일입니다.", 409)
    try:
        cur = conn.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (username, email, generate_password_hash(password), int(time.time())),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return err("이미 사용 중인 아이디 또는 이메일입니다.", 409)
    try:
        send_verify_mail(cur.lastrowid, email)
    except Exception as e:  # 메일을 못 보내면 인증할 방법이 없으니 가입을 되돌린다
        app.logger.error("인증 메일 전송 실패: %s", e)
        conn.execute("DELETE FROM users WHERE id = ?", (cur.lastrowid,))
        conn.commit()
        return err("인증 메일을 보내지 못했습니다. 잠시 뒤 다시 시도해 주세요.", 502)
    return jsonify({"verify": True, "email": mask_email(email)}), 201


@app.get("/verify")
def verify_email():
    try:
        data = verify_tokens.loads(request.args.get("token", ""), max_age=VERIFY_TTL)
    except BadSignature:  # 만료(SignatureExpired)도 여기 포함
        return redirect("/login?verify=invalid")
    conn = db.get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ? AND email = ?",
                        (data.get("uid"), data.get("email"))).fetchone()
    if user is None:
        return redirect("/login?verify=invalid")
    if user["verified_at"] is None:
        conn.execute("UPDATE users SET verified_at = ? WHERE id = ?", (int(time.time()), user["id"]))
        conn.commit()
    session.clear()
    session.permanent = True
    session["uid"] = user["id"]
    return redirect("/library?verified=1")


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
    if not user["active"]:
        return err("관리자가 비활성화한 계정입니다.", 403)
    if user["email"] and user["verified_at"] is None:
        msg = "이메일 인증을 마쳐야 로그인할 수 있습니다."
        if now - (user["verify_sent_at"] or 0) >= RESEND_GAP:
            try:
                send_verify_mail(user["id"], user["email"])
                msg += f" 인증 메일을 다시 보냈어요({mask_email(user['email'])})."
            except Exception as e:
                app.logger.error("인증 메일 재전송 실패: %s", e)
        else:
            msg += f" {mask_email(user['email'])} 메일함을 확인해 주세요."
        return err(msg, 403)
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
    sql, params = TEMPLATE_SELECT + " WHERE t.active = 1", []
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
    cats = [r[0] for r in conn.execute(
        "SELECT DISTINCT category FROM templates WHERE active = 1 ORDER BY category")]
    return jsonify({
        "templates": [template_summary(r, r["id"] in saved if user else None) for r in rows],
        "categories": cats,
    })


@app.get("/api/templates/<int:tid>")
def get_template(tid):
    row = db.get_db().execute(TEMPLATE_SELECT + " WHERE t.id = ?", (tid,)).fetchone()
    user = current_user()
    if row is None or not can_see_template(row, user):
        return err("템플릿을 찾을 수 없습니다.", 404)
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
    row = db.get_db().execute("SELECT data, active, author_id FROM templates WHERE id = ?", (tid,)).fetchone()
    if row is None or not can_see_template(row, current_user()):
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
        " WHERE t.active = 1 ORDER BY lib.added_at, t.id", (user["id"],)
    ).fetchall()
    return jsonify([template_summary(r, True) for r in rows])


@app.post("/api/library/<int:tid>")
@login_required
def add_to_library(user, tid):
    conn = db.get_db()
    if conn.execute("SELECT 1 FROM templates WHERE id = ? AND active = 1", (tid,)).fetchone() is None:
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
    conn.execute("UPDATE users SET mc_uuid = NULL, mc_name = NULL, link_key_id = NULL WHERE id = ?",
                 (user["id"],))
    conn.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------- 내 마인크래프트 서버 키

def server_key_json(row, players):
    return {"prefix": row["prefix"], "createdAt": row["created_at"], "players": players}


@app.get("/api/server-key")
@login_required
def get_server_key(user):
    conn = db.get_db()
    row = conn.execute("SELECT * FROM server_keys WHERE user_id = ?", (user["id"],)).fetchone()
    if row is None:
        return jsonify(None)
    players = conn.execute("SELECT COUNT(*) FROM users WHERE link_key_id = ?", (row["id"],)).fetchone()[0]
    return jsonify(server_key_json(row, players))


@app.post("/api/server-key")
@login_required
def issue_server_key(user):
    """새 키 발급. 이미 있으면 키만 바꾼다(같은 id 유지 → 연동된 플레이어는 그대로). 원문은 이번 응답에서만 보여 준다."""
    token = "bp_" + secrets.token_urlsafe(32)
    now = int(time.time())
    conn = db.get_db()
    conn.execute(
        "INSERT INTO server_keys (user_id, key_hash, prefix, created_at) VALUES (?, ?, ?, ?)"
        " ON CONFLICT(user_id) DO UPDATE SET key_hash = excluded.key_hash, prefix = excluded.prefix,"
        " created_at = excluded.created_at",
        (user["id"], hash_key(token), token[:8], now))
    conn.commit()
    row = conn.execute("SELECT * FROM server_keys WHERE user_id = ?", (user["id"],)).fetchone()
    players = conn.execute("SELECT COUNT(*) FROM users WHERE link_key_id = ?", (row["id"],)).fetchone()[0]
    return jsonify({**server_key_json(row, players), "key": token}), 201


# ---------------------------------------------------------------- 내 프로필

@app.get("/api/profile")
@login_required
def profile(user):
    conn = db.get_db()
    uploads = conn.execute(TEMPLATE_SELECT + " WHERE t.author_id = ? ORDER BY t.id DESC",
                           (user["id"],)).fetchall()
    key = conn.execute("SELECT * FROM server_keys WHERE user_id = ?", (user["id"],)).fetchone()
    players = key and conn.execute("SELECT COUNT(*) FROM users WHERE link_key_id = ?", (key["id"],)).fetchone()[0]
    library = conn.execute("SELECT COUNT(*) FROM library l JOIN templates t ON t.id = l.template_id"
                           " WHERE l.user_id = ? AND t.active = 1", (user["id"],)).fetchone()[0]
    return jsonify({
        **user_json(user),
        "createdAt": user["created_at"],
        "emailVerified": user["email"] is not None and user["verified_at"] is not None,
        "stats": {"library": library, "uploads": len(uploads),
                  "savesReceived": sum(r["saves"] for r in uploads)},
        "uploads": [template_summary(r) for r in uploads],
        "serverKey": server_key_json(key, players) if key else None,
    })


@app.post("/api/auth/password")
@login_required
def change_password(user):
    data = body()
    if not check_password_hash(user["password_hash"], str(data.get("current", ""))):
        return err("지금 비밀번호가 올바르지 않습니다.", 403)
    new = str(data.get("new", ""))
    if not 8 <= len(new) <= 128:
        return err("새 비밀번호는 8자 이상이어야 합니다.")
    conn = db.get_db()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new), user["id"]))
    conn.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------- 관리자

def set_active(table, row_id, data):
    if not isinstance(data.get("active"), bool):
        return err("active 는 true/false 여야 합니다.")
    conn = db.get_db()
    cur = conn.execute(f"UPDATE {table} SET active = ? WHERE id = ?", (int(data["active"]), row_id))
    conn.commit()
    if cur.rowcount == 0:
        return err("찾을 수 없습니다.", 404)
    return jsonify({"ok": True, "active": data["active"]})


@app.get("/api/admin/users")
@admin_required
def admin_users(_admin):
    rows = db.get_db().execute("""
        SELECT u.*, k.prefix AS key_prefix,
               (SELECT COUNT(*) FROM users p WHERE p.link_key_id = k.id) AS key_players,
               (SELECT COUNT(*) FROM library l WHERE l.user_id = u.id) AS library_count,
               (SELECT COUNT(*) FROM templates t WHERE t.author_id = u.id) AS upload_count
        FROM users u LEFT JOIN server_keys k ON k.user_id = u.id
        ORDER BY u.id DESC""").fetchall()
    return jsonify([{
        **user_json(u),
        "active": bool(u["active"]),
        "status": "inactive" if not u["active"] else "unverified" if u["email"] and u["verified_at"] is None
                  else "verified" if u["email"] else "legacy",
        "createdAt": u["created_at"],
        "serverKey": {"prefix": u["key_prefix"], "players": u["key_players"]} if u["key_prefix"] else None,
        "libraryCount": u["library_count"],
        "uploadCount": u["upload_count"],
    } for u in rows])


@app.post("/api/admin/users/<int:uid>/active")
@admin_required
def admin_user_active(admin, uid):
    target = db.get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    if target is not None and is_admin(target):
        return err("관리자 계정은 비활성화할 수 없습니다.", 400)
    return set_active("users", uid, body())


@app.delete("/api/admin/users/<int:uid>")
@admin_required
def admin_user_delete(admin, uid):
    conn = db.get_db()
    target = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    if target is None:
        return err("찾을 수 없습니다.", 404)
    if is_admin(target):
        return err("관리자 계정은 삭제할 수 없습니다.", 400)
    # 작성자가 비면 기본 템플릿(author_id NULL)으로 오인되어 서버 재시작 때 지워지므로 함께 삭제한다
    conn.execute("DELETE FROM templates WHERE author_id = ?", (uid,))
    conn.execute("DELETE FROM users WHERE id = ?", (uid,))
    conn.commit()
    return jsonify({"ok": True})


@app.get("/api/admin/templates")
@admin_required
def admin_templates(_admin):
    rows = db.get_db().execute(TEMPLATE_SELECT + " ORDER BY t.id DESC").fetchall()
    return jsonify([template_summary(r) for r in rows])


@app.post("/api/admin/templates/<int:tid>/active")
@admin_required
def admin_template_active(_admin, tid):
    return set_active("templates", tid, body())


@app.delete("/api/admin/templates/<int:tid>")
@admin_required
def admin_template_delete(_admin, tid):
    conn = db.get_db()
    row = conn.execute("SELECT author_id FROM templates WHERE id = ?", (tid,)).fetchone()
    if row is None:
        return err("찾을 수 없습니다.", 404)
    if row["author_id"] is None:  # 기본 템플릿은 서버를 켤 때마다 코드에서 다시 만들어진다
        return err("기본 템플릿은 삭제할 수 없어요. 비활성화를 써 주세요.", 400)
    conn.execute("DELETE FROM templates WHERE id = ?", (tid,))
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


# 회원 서버 키는 자기 키로 연동된 플레이어만 볼 수 있다 (운영자 키 g.key_id=None 은 전체)
KEY_SCOPE = " AND (:key IS NULL OR link_key_id = :key)"


def linked_user(mc_uuid):
    return db.get_db().execute("SELECT * FROM users WHERE mc_uuid = :uuid AND active = 1" + KEY_SCOPE,
                               {"uuid": mc_uuid, "key": g.key_id}).fetchone()


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
    conn.execute("UPDATE users SET mc_uuid = NULL, mc_name = NULL, link_key_id = NULL WHERE mc_uuid = ?",
                 (mc_uuid,))
    conn.execute("UPDATE users SET mc_uuid = ?, mc_name = ?, link_key_id = ? WHERE id = ?",
                 (mc_uuid, mc_name, g.key_id, row["user_id"]))
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
    cur = conn.execute("UPDATE users SET mc_uuid = NULL, mc_name = NULL, link_key_id = NULL"
                       " WHERE mc_uuid = :uuid" + KEY_SCOPE, {"uuid": parse_uuid(mc_uuid), "key": g.key_id})
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
        " WHERE t.active = 1 ORDER BY lib.added_at, t.id", (user["id"],)
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
        " WHERE l.user_id = ? AND t.id = ? AND t.active = 1", (user["id"], tid)
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
         "library": "library.html", "upload": "upload.html", "template": "template.html",
         "profile": "profile.html", "admin": "admin.html"}


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
