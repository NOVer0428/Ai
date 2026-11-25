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
USERNAME_RE = re.compile(r"^[A-Za-z0-9_가-힣]{6,15}$")
PASSWORD_SPECIALS = r"!?/\|@#$%^&*"
PASSWORD_RE = re.compile(r"^[A-Za-z0-9!?/\\|@#$%^&*]{8,15}$")  # \\ = 역슬래시 자체
PASSWORD_RULE = "비밀번호는 8~15자이고 숫자, 영어 소문자, 영어 대문자, 특수문자(! ? / \\ | @ # $ % ^ & *)를 모두 넣어야 해요."


def password_problem(password, username):
    """새 비밀번호 규칙 검사. 문제가 없으면 None, 있으면 안내 문구."""
    if not PASSWORD_RE.match(password):
        return PASSWORD_RULE
    if not (re.search(r"\d", password) and re.search(r"[a-z]", password) and re.search(r"[A-Z]", password)
            and any(c in PASSWORD_SPECIALS for c in password)):
        return PASSWORD_RULE
    # 아이디와 같거나 비슷하면 거절: 기호·숫자를 뺀 글자로 포함 관계와 유사도를 본다
    from difflib import SequenceMatcher
    core = lambda x: re.sub(r"[^a-z가-힣]", "", x.lower())
    pw, uid = core(password), core(username)
    pw_l, uid_l = password.lower(), username.lower()
    if uid_l and (uid_l in pw_l or pw_l in uid_l or uid_l[::-1] in pw_l):
        return "비밀번호에 아이디를 넣을 수 없어요."
    if uid and pw and (uid in pw or pw in uid or SequenceMatcher(None, pw, uid).ratio() >= 0.6
                       or SequenceMatcher(None, pw_l, uid_l).ratio() >= 0.6):
        return "아이디와 비슷한 비밀번호는 쓸 수 없어요."
    return None


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
    PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30,  # "로그인 상태 유지" 기간 (요청마다 연장)
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
    # 쿠키 기반 API에 대한 CSRF 방어: 쓰기 요청은 JSON만 허용 (폼 전송으로는 보낼 수 없음)
    if request.method in ("POST", "PUT", "DELETE") and request.path.startswith("/api/"):
        if request.content_length and not request.is_json:
            return err("Content-Type은 application/json이어야 합니다.", 415)
        # 본문 없는 POST 도 막도록: 브라우저가 붙이는 Origin 이 이 사이트가 아니면 거절 (플러그인은 Origin 없음)
        # 프록시 뒤에서는 내부 주소가 http 라서 스킴은 빼고 호스트만 비교한다
        from urllib.parse import urlsplit
        origin = request.headers.get("Origin")
        if origin and urlsplit(origin).netloc.lower() != request.host.lower():
            return err("다른 사이트에서 보낸 요청은 받을 수 없습니다.", 403)


CSP = ("default-src 'self'; script-src 'self'; "  # 인라인 스크립트 금지: 페이지 스크립트는 static/page-*.js
       "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; "
       "img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; base-uri 'self'; "
       "form-action 'self'; frame-ancestors 'none'")


@app.after_request
def security_headers(resp):
    resp.headers.setdefault("Content-Security-Policy", CSP)
    resp.headers.setdefault("X-Frame-Options", "DENY")            # 클릭재킹 방지
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if app.config["SESSION_COOKIE_SECURE"]:
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return resp


# 관리자 아이디 목록 (쉼표로 구분, 대소문자 무시). 예: ADMIN_USERS=noha04
ADMINS = {n.strip().lower() for n in os.environ.get("ADMIN_USERS", "").split(",") if n.strip()}


SUB_ADMIN = "sub_admin"


def is_staff(user):
    """메인 관리자 또는 부 관리자: 관리자 페이지를 볼 수 있다."""
    return is_admin(user) or bool(user and user["role"] == SUB_ADMIN)


def role_of(user):
    return "admin" if is_admin(user) else "sub_admin" if user["role"] == SUB_ADMIN else None


def is_admin(user):
    return bool(user) and user["username"].lower() in ADMINS


def current_user():
    uid = session.get("uid")
    if uid is None:
        return None
    # 비활성화된 계정, 비밀번호를 바꾸거나 "모든 기기에서 로그아웃" 한 뒤의 옛 쿠키는 바로 끊긴다
    return db.get_db().execute("SELECT * FROM users WHERE id = ? AND active = 1 AND session_ver = ?",
                               (uid, session.get("sv", 0))).fetchone()


def can_see_template(row, user):
    """비활성 템플릿은 관리자와 작성자 본인만 본다."""
    return bool(row["active"]) or is_staff(user) or bool(user and row["author_id"] == user["id"])


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return err("로그인이 필요합니다.", 401)
        return fn(user, *args, **kwargs)
    return wrapper


def admin_required(fn):
    """메인 관리자(ADMIN_USERS)만: 삭제, 부 관리자 지정."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return err("로그인이 필요합니다.", 401)
        if not is_admin(user):
            return err("메인 관리자만 할 수 있습니다.", 403)
        return fn(user, *args, **kwargs)
    return wrapper


def staff_required(fn):
    """메인 관리자 또는 부 관리자: 관리자 페이지 보기, 템플릿 비/활성화, 회원 정지."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return err("로그인이 필요합니다.", 401)
        if not is_staff(user):
            return err("관리자만 할 수 있습니다.", 403)
        return fn(user, *args, **kwargs)
    return wrapper


def hash_key(token):
    return hashlib.sha256(token.encode()).hexdigest()


SERVER_NAME_MAX = 32


def clean_server_name(value):
    """플러그인 config 의 server-name. 앞뒤 공백 제거, 제어문자 제거, 32자. 비면 None."""
    name = "".join(ch for ch in str(value or "") if ch.isprintable()).strip()[:SERVER_NAME_MAX]
    return name or None


def plugin_auth(fn):
    """플러그인 인증. 키가 가리키는 서버 한 줄을 g.server_id 로 둔다(운영자 키도 서버 한 줄).
    플러그인이 X-Server-Name 헤더(UTF-8 퍼센트 인코딩)를 보내면 그 값으로 서버 이름을 바로 바꾼다."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        from urllib.parse import unquote
        header = request.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        conn = db.get_db()
        if token and hmac.compare_digest(token.encode(), PLUGIN_API_KEY.encode()):
            g.server_id = db.operator_server_id(conn)
        else:
            row = token and conn.execute(
                "SELECT s.id FROM servers s JOIN users u ON u.id = s.owner_id"
                " WHERE s.key_hash = ? AND u.active = 1", (hash_key(token),)).fetchone()
            if not row:
                return err("플러그인 API 키가 올바르지 않습니다.", 401)
            g.server_id = row["id"]
        sets, params = ["last_seen_at = ?"], [int(time.time())]
        if "X-Server-Name" in request.headers:
            sets.append("name = ?")
            params.append(clean_server_name(unquote(request.headers["X-Server-Name"])))
        conn.execute(f"UPDATE servers SET {', '.join(sets)} WHERE id = ?", (*params, g.server_id))
        conn.commit()
        return fn(*args, **kwargs)
    return wrapper


def number_unnamed(rows):
    """이름 없는 서버에 목록 순서대로 Minecraft Server (1), (2) ... 를 붙인다."""
    n, out = 0, []
    for r in rows:
        if r["name"]:
            label = r["name"]
        else:
            n += 1
            label = f"Minecraft Server ({n})"
        out.append((r, label))
    return out


def user_links(user_id):
    rows = db.get_db().execute(
        "SELECT l.*, s.name, s.is_operator, s.last_seen_at FROM server_links l JOIN servers s ON s.id = l.server_id"
        " WHERE l.user_id = ? ORDER BY l.linked_at, l.server_id", (user_id,)).fetchall()
    return [{"serverId": r["server_id"], "serverName": label, "named": bool(r["name"]),
             "minecraft": {"uuid": r["mc_uuid"], "name": r["mc_name"]},
             "linkedAt": r["linked_at"], "lastSeenAt": r["last_seen_at"]} for r, label in number_unnamed(rows)]


def user_json(u):
    links = db.get_db().execute("SELECT COUNT(*) FROM server_links WHERE user_id = ?", (u["id"],)).fetchone()[0]
    return {
        "id": u["id"],
        "username": u["username"],
        "email": u["email"],
        "isAdmin": is_admin(u),
        "isStaff": is_staff(u),
        "role": role_of(u),
        "avatar": f"/api/users/{u['id']}/avatar.png?v={u['avatar_ver']}" if u["avatar_ver"] else None,
        "linkedServers": links,
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


TEMPLATE_COLS = ("t.id, t.name, t.description, t.category, t.author_id, t.size_x, t.size_y, t.size_z,"
                 " t.block_count, t.created_at, t.active")
TEMPLATE_SELECT = """
SELECT """ + TEMPLATE_COLS + """, u.username AS author,
       (SELECT COUNT(*) FROM library l WHERE l.template_id = t.id) AS saves
FROM templates t LEFT JOIN users u ON u.id = t.author_id
"""


# ---------------------------------------------------------------- auth

TERMS_VERSION = "2026-11-23"  # static/terms.html 의 버전과 같게
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]+$")
VERIFY_TTL = 24 * 60 * 60
RESEND_GAP = 3 * 60  # 남의 이메일로 가입해 로그인을 반복하는 메일 폭탄 완화 (24시간 뒤 미인증 가입은 삭제)
CODE_TTL = 30 * 60
CODE_MAX_TRIES = 5   # 코드 하나당 틀릴 수 있는 횟수. 넘으면 새 코드를 받아야 한다
verify_tokens = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt="email-verify")


def send_mail(to, subject, text, html=None):
    """MAIL_USER/MAIL_PASSWORD(Gmail 앱 비밀번호)가 있으면 SMTP로 보내고, 없으면 로그에 찍는다(개발용)."""
    user, password = os.environ.get("MAIL_USER"), os.environ.get("MAIL_PASSWORD")
    if not limiter.hit(("mail",), MAIL_PER_DAY, 24 * 3600):
        raise RuntimeError("오늘 보낼 수 있는 메일 수를 넘었습니다.")
    if not (user and password):
        if app.config["SESSION_COOKIE_SECURE"]:  # 운영(HTTPS)에서는 인증 코드를 로그에 남기지 않는다
            raise RuntimeError("MAIL_USER/MAIL_PASSWORD 가 설정되지 않았습니다.")
        print(f"[메일 미설정] 받는 사람 {to} / {subject}\n{text}", flush=True)
        return
    import smtplib
    from email.message import EmailMessage
    from email.utils import formatdate, make_msgid
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = f"블루프린트 <{user}>", to, subject
    # Date·Message-ID 가 없으면 스팸 점수가 올라간다
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=user.split("@")[-1])
    msg.set_content(text)                 # 일반 글자 본문 (HTML 을 못 보는 메일 앱용)
    if html:
        msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(os.environ.get("MAIL_HOST", "smtp.gmail.com"),
                      int(os.environ.get("MAIL_PORT", 587)), timeout=20) as s:
        s.starttls()
        s.login(user, password)
        s.send_message(msg)


def code_hash(user_id, code):
    # DB 가 새어도 6자리 코드를 바로 대입해 볼 수 없게 서버 비밀키로 HMAC
    return hmac.new(app.config["SECRET_KEY"].encode(), f"{user_id}:{code}".encode(), hashlib.sha256).hexdigest()


VERIFY_MAIL_HTML = """<!doctype html>
<html lang="ko"><body style="margin:0;padding:24px;font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;font-size:15px;line-height:1.6;color:#1d2a3a">
<p style="margin:0 0 12px;font-size:15px">블루프린트 가입 인증 코드예요.</p>
<p style="margin:0 0 12px;font-size:15px">인증 코드: <b style="font-size:18px;font-weight:900;letter-spacing:2px">{code}</b></p>
<p style="margin:0 0 12px;font-size:15px">가입 화면에 위 6자리 코드를 입력하세요. 코드는 30분 동안 유효합니다.</p>
<p style="margin:0;font-size:15px;color:#5b6676">직접 가입하지 않았다면 이 메일을 무시하세요.</p>
</body></html>"""


RESET_MAIL_HTML = """<!doctype html>
<html lang="ko"><body style="margin:0;padding:24px;font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;font-size:15px;line-height:1.6;color:#1d2a3a">
<p style="margin:0 0 12px;font-size:15px">블루프린트 비밀번호 재설정 코드예요.</p>
<p style="margin:0 0 12px;font-size:15px">재설정 코드: <b style="font-size:18px;font-weight:900;letter-spacing:2px">{code}</b></p>
<p style="margin:0 0 12px;font-size:15px">아이디: <b>{username}</b></p>
<p style="margin:0 0 12px;font-size:15px">비밀번호 재설정 화면에 위 6자리 코드와 새 비밀번호를 입력하세요. 코드는 30분 동안 유효합니다.</p>
<p style="margin:0;font-size:15px;color:#5b6676">직접 요청하지 않았다면 이 메일을 무시하세요. 비밀번호는 바뀌지 않아요.</p>
</body></html>"""


def send_verify_mail(user_id, email):
    """6자리 코드만 보낸다(링크 없음). 코드는 본문(15px)보다 3px 큰 18px 굵은 글씨. 새로 보내면 이전 코드는 무효."""
    code = f"{secrets.randbelow(10**6):06d}"
    send_mail(email, f"[블루프린트] 인증 코드 {code}",
              f"블루프린트 가입 인증 코드예요.\n\n인증 코드: {code}\n\n"
              "가입 화면에 위 6자리 코드를 입력하세요. 코드는 30분 동안 유효합니다.\n\n"
              "직접 가입하지 않았다면 이 메일을 무시하세요.",
              html=VERIFY_MAIL_HTML.format(code=code))
    db.get_db().execute(
        "UPDATE users SET verify_sent_at = ?, verify_code_hash = ?, verify_attempts = 0 WHERE id = ?",
        (int(time.time()), code_hash(user_id, code), user_id))
    db.get_db().commit()


def log_in(user, remember=False):
    """remember=True(로그인 상태 유지)면 30일 쿠키, 아니면 브라우저를 닫을 때까지만."""
    session.clear()
    session.permanent = remember
    session["uid"] = user["id"]
    session["sv"] = user["session_ver"]


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
        return err("아이디는 6~15자의 영문, 숫자, 한글, _ 만 사용할 수 있습니다.")
    if len(email) > 254 or not EMAIL_RE.match(email):
        return err("올바른 이메일 주소를 입력해 주세요.")
    problem = password_problem(password, username)
    if problem:
        return err(problem)
    if data.get("agreeTerms") is not True or data.get("agreePrivacy") is not True:
        return err("이용약관과 개인정보 수집·이용에 모두 동의해야 가입할 수 있어요.")
    if data.get("agreeAge") is not True:  # 만 14세 미만은 법정대리인 동의가 필요해 가입을 받지 않는다
        return err("만 14세 이상만 가입할 수 있어요.")
    if username.lower() in ADMINS:  # 관리자 아이디는 미리 만든 계정만 쓴다(선점 방지)
        return err("이미 사용 중인 아이디입니다.", 409)
    if not limiter.hit(("register-ip", request.remote_addr), REGISTER_PER_HOUR, 3600):
        return err("가입 신청이 너무 많습니다. 1시간 뒤에 다시 시도해 주세요.", 429)
    conn = db.get_db()
    # 링크 유효시간이 지나도록 인증하지 않은 가입은 지워서 아이디·이메일을 다시 쓸 수 있게 한다
    conn.execute("DELETE FROM users WHERE email IS NOT NULL AND verified_at IS NULL AND created_at < ?",
                 (int(time.time()) - VERIFY_TTL,))
    conn.commit()  # 아래에서 메일을 보내는 동안 DB 쓰기 잠금을 붙잡지 않게 바로 끝낸다
    taken = conn.execute("SELECT username = ? COLLATE NOCASE FROM users"
                         " WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE",
                         (username, username, email)).fetchone()
    if taken and taken[0]:
        return err("이미 사용 중인 아이디입니다.", 409)
    conn.execute("DELETE FROM withdrawn_emails WHERE until <= ?", (int(time.time()),))
    conn.commit()
    held = conn.execute("SELECT until FROM withdrawn_emails WHERE email_hash = ?", (email_hash(email),)).fetchone()
    if held:
        days = max(1, -(-(held["until"] - int(time.time())) // 86400))
        return err(f"탈퇴한 이메일은 탈퇴 7일 뒤부터 다시 가입할 수 있어요. ({days}일 남음)", 409)
    if taken:
        # 이메일이 이미 가입돼 있어도 성공과 같은 응답을 준다(가입 여부 노출 방지). 그 주소로는 안내 메일만 보낸다
        try:
            send_mail(email, "[블루프린트] 이미 가입된 이메일이에요",
                      "이 이메일로 이미 가입된 계정이 있어서 새 가입은 진행되지 않았어요.\n"
                      "비밀번호가 기억나지 않으면 관리자에게 문의해 주세요.\n\n"
                      "직접 가입하지 않았다면 이 메일을 무시하세요.")
        except Exception as e:
            app.logger.error("중복 가입 안내 메일 실패: %s", e)
        return jsonify({"verify": True, "email": mask_email(email)}), 201
    try:
        cur = conn.execute(
            "INSERT INTO users (username, email, password_hash, created_at, terms_version, terms_agreed_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (username, email, generate_password_hash(password), int(time.time()), TERMS_VERSION, int(time.time())),
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
        conn.execute("UPDATE users SET verified_at = ?, verify_code_hash = NULL WHERE id = ?",
                     (int(time.time()), user["id"]))
        conn.commit()
    log_in(user)
    return redirect("/")


@app.post("/api/auth/verify-code")
def verify_code():
    data = body()
    code = str(data.get("code", "")).strip()
    conn = db.get_db()
    user = conn.execute("SELECT * FROM users WHERE username = ? COLLATE NOCASE AND email IS NOT NULL"
                        " AND verified_at IS NULL AND active = 1",
                        (str(data.get("username", "")).strip(),)).fetchone()
    if user is None or not user["verify_code_hash"]:
        return err("인증할 가입 정보가 없어요. 이미 인증했다면 로그인해 주세요.", 404)
    if user["verify_attempts"] >= CODE_MAX_TRIES:
        return err("코드를 너무 많이 틀렸어요. 새 코드를 받아 주세요.", 429)
    if time.time() - (user["verify_sent_at"] or 0) > CODE_TTL:
        return err("코드가 만료됐어요. 새 코드를 받아 주세요.", 410)
    if not (re.fullmatch(r"\d{6}", code)
            and hmac.compare_digest(code_hash(user["id"], code), user["verify_code_hash"])):
        conn.execute("UPDATE users SET verify_attempts = verify_attempts + 1 WHERE id = ?", (user["id"],))
        conn.commit()
        left = CODE_MAX_TRIES - user["verify_attempts"] - 1
        return err(f"코드가 맞지 않아요. {left}번 더 시도할 수 있어요." if left
                   else "코드를 너무 많이 틀렸어요. 새 코드를 받아 주세요.", 400)
    conn.execute("UPDATE users SET verified_at = ?, verify_code_hash = NULL WHERE id = ?",
                 (int(time.time()), user["id"]))
    conn.commit()
    log_in(user)
    return jsonify(user_json(current_user()))


class Limiter:
    """키별로 최근 시각을 세는 간단한 횟수 제한.
    shortcut: 프로세스 메모리에 둔다(재시작하면 초기화, 워커 1개 기준). 워커를 늘리면 DB로 옮긴다.
    키 수가 MAX_KEYS 를 넘으면 기한이 지난 키를 지우고, 그래도 많으면 가장 오래된 절반을 버려 메모리가 무한히 늘지 않는다."""
    MAX_KEYS = 20000

    def __init__(self):
        self.hits = {}

    def count(self, key, window, now=None):
        now = now or time.time()
        times = [t for t in self.hits.get(key, ()) if now - t < window]
        if times:
            self.hits[key] = times
        else:
            self.hits.pop(key, None)
        return len(times)

    def add(self, key, now=None):
        if len(self.hits) >= self.MAX_KEYS:
            self._prune()
        self.hits.setdefault(key, []).append(now or time.time())

    def hit(self, key, limit, window):
        """한도 안이면 기록하고 True, 넘었으면 False."""
        if self.count(key, window) >= limit:
            return False
        self.add(key)
        return True

    def clear(self, key):
        self.hits.pop(key, None)

    def _prune(self):
        now = time.time()
        for k in [k for k, v in self.hits.items() if not v or now - v[-1] > 24 * 3600]:
            del self.hits[k]
        if len(self.hits) >= self.MAX_KEYS:
            for k in sorted(self.hits, key=lambda k: self.hits[k][-1])[: len(self.hits) // 2]:
                del self.hits[k]


limiter = Limiter()
LOGIN_WINDOW = 10 * 60
LOGIN_MAX_FAILS = {"ip": 20, "user": 5}
REGISTER_PER_HOUR = int(os.environ.get("REGISTER_PER_HOUR", 5))    # IP 하나당 1시간에 가입 신청 수
MAIL_PER_DAY = int(os.environ.get("MAIL_PER_DAY", 300))           # 사이트 전체 하루 발송 한도 (Gmail 한도 500 아래)
LINK_FAILS_PER_10MIN = 10                                         # 서버 키 하나당 틀린 연동 코드 허용 수
UPLOADS_PER_HOUR = int(os.environ.get("UPLOADS_PER_HOUR", 20))
UPLOADS_MAX = int(os.environ.get("UPLOADS_MAX", 200))             # 회원 한 명이 올릴 수 있는 템플릿 수




@app.post("/api/auth/login")
def login():
    data = body()
    username = str(data.get("username", "")).strip()
    now = time.time()
    # 아이디 키는 20자로 자른다(긴 아이디로 메모리를 채우는 것 방지)
    keys = {"ip": ("login-ip", request.remote_addr), "user": ("login-user", username.lower()[:20])}
    if any(limiter.count(k, LOGIN_WINDOW, now) >= LOGIN_MAX_FAILS[kind] for kind, k in keys.items()):
        return err("로그인 시도가 너무 많습니다. 10분 뒤에 다시 시도해 주세요.", 429)
    user = len(username) <= 20 and db.get_db().execute(
        "SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if not user or not check_password_hash(user["password_hash"], str(data.get("password", ""))):
        for k in keys.values():
            limiter.add(k, now)
        return err("아이디 또는 비밀번호가 올바르지 않습니다.", 401)
    limiter.clear(keys["user"])
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
            wait = RESEND_GAP - (now - (user["verify_sent_at"] or 0))
            msg += f" {mask_email(user['email'])} 메일함을 확인해 주세요. 새 코드는 {int(wait // 60) + 1}분 뒤에 받을 수 있어요."
        # 화면이 바로 코드 입력 칸을 띄울 수 있게 알려 준다
        return jsonify({"error": msg, "needsVerify": True, "username": user["username"],
                        "email": mask_email(user["email"])}), 403
    log_in(user, remember=data.get("remember") is True)
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
    sql += " LIMIT 500"  # 한 번에 보내는 목록 상한
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
    row = db.get_db().execute(TEMPLATE_SELECT.replace(TEMPLATE_COLS, TEMPLATE_COLS + ", t.data", 1)
                              + " WHERE t.id = ?", (tid,)).fetchone()
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
    out["canEdit"] = row["author_id"] is not None and (out["mine"] or is_admin(user))
    return jsonify(out)


@app.get("/api/templates/<int:tid>/thumbnail.png")
def template_thumbnail(tid):
    """실제 블록 텍스처로 그린 썸네일. ?rot=0~3 (보는 방향), ?maxY= (그 높이까지만)"""
    if not thumbnail.available():
        return err("썸네일용 블록 에셋이 없습니다. tools/fetch_assets.py 를 실행하세요.", 404)
    row = db.get_db().execute("SELECT data, active, author_id, size_y FROM templates WHERE id = ?",
                              (tid,)).fetchone()
    if row is None or not can_see_template(row, current_user()):
        return err("템플릿을 찾을 수 없습니다.", 404)
    rot = request.args.get("rot", 0, type=int) % 4
    max_y = request.args.get("maxY", type=int)
    if max_y is not None and not 0 <= max_y < row["size_y"]:  # 0 = 첫 층만
        max_y = None
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


RENDER_SLOTS = __import__("threading").BoundedSemaphore(2)


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
    total, recent = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(created_at > ?), 0) FROM templates WHERE author_id = ?",
        (int(time.time()) - 3600, user["id"])).fetchone()
    if total >= UPLOADS_MAX:
        return err(f"템플릿은 한 사람당 {UPLOADS_MAX}개까지 올릴 수 있어요. 안 쓰는 템플릿을 지워 주세요.", 400)
    if recent >= UPLOADS_PER_HOUR:
        return err("업로드가 너무 많습니다. 1시간 뒤에 다시 시도해 주세요.", 429)
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
        def render(tid=cur.lastrowid, data_json=json.dumps(tpl, separators=(",", ":"))):
            with RENDER_SLOTS:  # 업로드가 몰려도 미리 그리기는 동시에 2개까지
                thumbnail.thumbnail_path(tid, data_json)
        threading.Thread(target=render, daemon=True).start()
    return jsonify({"id": cur.lastrowid}), 201


@app.put("/api/templates/<int:tid>")
@login_required
def update_template(user, tid):
    """내가 올린 템플릿(메인 관리자는 회원 템플릿 전부)의 이름·분류·설명과 파일(data)을 고친다.
    기본 템플릿은 서버를 켤 때 코드로 다시 맞춰지므로 고칠 수 없다. data 를 빼면 내용은 그대로 둔다."""
    conn = db.get_db()
    row = conn.execute("SELECT author_id FROM templates WHERE id = ?", (tid,)).fetchone()
    if row is None:
        return err("템플릿을 찾을 수 없습니다.", 404)
    if row["author_id"] is None:
        return err("기본 템플릿은 수정할 수 없어요.", 403)
    if row["author_id"] != user["id"] and not is_admin(user):
        return err("내가 올린 템플릿만 수정할 수 있습니다.", 403)
    data = body()
    name = str(data.get("name", "")).strip()
    if not 1 <= len(name) <= 40:
        return err("이름은 1~40자여야 합니다.")
    description = str(data.get("description", "")).strip()[:500]
    category = str(data.get("category", "기타")).strip()[:20] or "기타"
    sets = ["name = ?", "description = ?", "category = ?"]
    params = [name, description, category]
    if data.get("data") is not None:
        try:
            tpl = validate(data.get("data"))
        except TemplateError as e:
            return err(str(e))
        data_json = json.dumps(tpl, separators=(",", ":"))
        sets += ["size_x = ?", "size_y = ?", "size_z = ?", "block_count = ?", "data = ?"]
        params += [*tpl["size"], len(tpl["blocks"]), data_json]
        if thumbnail.available():  # 새 내용의 썸네일을 미리 그린다(캐시 키가 내용 해시라 옛 그림은 안 쓰임)
            import threading

            def render():
                with RENDER_SLOTS:
                    thumbnail.thumbnail_path(tid, data_json)
            threading.Thread(target=render, daemon=True).start()
    conn.execute(f"UPDATE templates SET {', '.join(sets)} WHERE id = ?", (*params, tid))
    conn.commit()
    return jsonify({"ok": True, "id": tid})


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


@app.get("/api/links")
@login_required
def my_links(user):
    """내가 인게임 연동한 서버 목록 (새 서버에서 연동할 때마다 늘어난다)."""
    return jsonify(user_links(user["id"]))


@app.delete("/api/links/<int:server_id>")
@login_required
def unlink_server(user, server_id):
    conn = db.get_db()
    cur = conn.execute("DELETE FROM server_links WHERE user_id = ? AND server_id = ?", (user["id"], server_id))
    conn.commit()
    if cur.rowcount == 0:
        return err("연동되지 않은 서버입니다.", 404)
    return jsonify({"ok": True})


# ---------------------------------------------------------------- 내 마인크래프트 서버 (서버마다 키가 따로)

def owned_servers(user_id):
    rows = db.get_db().execute(
        "SELECT s.*, (SELECT COUNT(*) FROM server_links l WHERE l.server_id = s.id) AS players"
        " FROM servers s WHERE s.owner_id = ? ORDER BY s.created_at, s.id", (user_id,)).fetchall()
    return [{"id": r["id"], "name": label, "named": bool(r["name"]), "prefix": r["prefix"],
             "players": r["players"], "createdAt": r["created_at"], "lastSeenAt": r["last_seen_at"]}
            for r, label in number_unnamed(rows)]


def new_key():
    token = "bp_" + secrets.token_urlsafe(32)
    return token, hash_key(token), token[:8]


SERVERS_MAX = 20


@app.get("/api/servers")
@login_required
def list_servers(user):
    return jsonify(owned_servers(user["id"]))


@app.post("/api/servers")
@login_required
def add_server(user):
    """서버를 하나 더 등록하고 그 서버 전용 키를 만든다. 키 원문은 이번 응답에서만 보여 준다."""
    conn = db.get_db()
    if conn.execute("SELECT COUNT(*) FROM servers WHERE owner_id = ?", (user["id"],)).fetchone()[0] >= SERVERS_MAX:
        return err(f"서버는 {SERVERS_MAX}개까지 등록할 수 있어요.", 400)
    token, digest, prefix = new_key()
    sid = conn.execute("INSERT INTO servers (owner_id, key_hash, prefix, created_at) VALUES (?, ?, ?, ?)",
                       (user["id"], digest, prefix, int(time.time()))).lastrowid
    conn.commit()
    server = next(s for s in owned_servers(user["id"]) if s["id"] == sid)
    return jsonify({**server, "key": token}), 201


@app.post("/api/servers/<int:server_id>/key")
@login_required
def reissue_server_key(user, server_id):
    """그 서버의 키만 바꾼다. 옛 키는 바로 막히고 연동된 플레이어는 그대로."""
    token, digest, prefix = new_key()
    conn = db.get_db()
    cur = conn.execute("UPDATE servers SET key_hash = ?, prefix = ? WHERE id = ? AND owner_id = ?",
                       (digest, prefix, server_id, user["id"]))
    conn.commit()
    if cur.rowcount == 0:
        return err("내 서버가 아닙니다.", 404)
    server = next(s for s in owned_servers(user["id"]) if s["id"] == server_id)
    return jsonify({**server, "key": token})


@app.delete("/api/servers/<int:server_id>")
@login_required
def delete_server(user, server_id):
    conn = db.get_db()
    cur = conn.execute("DELETE FROM servers WHERE id = ? AND owner_id = ?", (server_id, user["id"]))
    conn.commit()
    if cur.rowcount == 0:
        return err("내 서버가 아닙니다.", 404)
    return jsonify({"ok": True})


# ---------------------------------------------------------------- 내 프로필

@app.get("/api/profile")
@login_required
def profile(user):
    conn = db.get_db()
    uploads = conn.execute(TEMPLATE_SELECT + " WHERE t.author_id = ? ORDER BY t.id DESC",
                           (user["id"],)).fetchall()
    library = conn.execute("SELECT COUNT(*) FROM library l JOIN templates t ON t.id = l.template_id"
                           " WHERE l.user_id = ? AND t.active = 1", (user["id"],)).fetchone()[0]
    return jsonify({
        **user_json(user),
        "createdAt": user["created_at"],
        "emailVerified": user["email"] is not None and user["verified_at"] is not None,
        "stats": {"library": library, "uploads": len(uploads),
                  "savesReceived": sum(r["saves"] for r in uploads)},
        "uploads": [template_summary(r) for r in uploads],
        "links": user_links(user["id"]),
        "servers": owned_servers(user["id"]),
    })


@app.post("/api/auth/password")
@login_required
def change_password(user):
    data = body()
    if not check_password_hash(user["password_hash"], str(data.get("current", ""))):
        return err("지금 비밀번호가 올바르지 않습니다.", 403)
    new = str(data.get("new", ""))
    problem = password_problem(new, user["username"])
    if problem:
        return err(problem)
    conn = db.get_db()
    # 비밀번호를 바꾸면 다른 기기의 로그인은 모두 끊고, 지금 기기는 새 버전으로 유지한다
    conn.execute("UPDATE users SET password_hash = ?, session_ver = session_ver + 1 WHERE id = ?",
                 (generate_password_hash(new), user["id"]))
    conn.commit()
    session["sv"] = user["session_ver"] + 1
    return jsonify({"ok": True})


REJOIN_WAIT = 7 * 24 * 3600  # 탈퇴한 이메일은 7일 뒤부터 다시 가입할 수 있다


def email_hash(email):
    return hmac.new(app.config["SECRET_KEY"].encode(), email.strip().lower().encode(), hashlib.sha256).hexdigest()


def delete_account(conn, uid):
    """계정과 그 회원의 템플릿·보관함·서버·연동·사진을 지운다. 템플릿을 남기면 작성자가 비어 기본 템플릿으로 오인된다."""
    conn.execute("DELETE FROM templates WHERE author_id = ?", (uid,))
    conn.execute("DELETE FROM users WHERE id = ?", (uid,))
    conn.commit()
    avatar_file(uid).unlink(missing_ok=True)


@app.post("/api/account/delete")
@login_required
def withdraw(user):
    """회원 탈퇴. 비밀번호를 다시 확인한다. 이메일은 7일 동안 재가입에 쓸 수 없다."""
    if is_admin(user):
        return err("메인 관리자 계정은 탈퇴할 수 없어요. ADMIN_USERS 설정에서 먼저 빼 주세요.", 400)
    if not check_password_hash(user["password_hash"], str(body().get("password", ""))):
        return err("비밀번호가 올바르지 않습니다.", 403)
    conn = db.get_db()
    if user["email"]:
        conn.execute("INSERT OR REPLACE INTO withdrawn_emails (email_hash, until) VALUES (?, ?)",
                     (email_hash(user["email"]), int(time.time()) + REJOIN_WAIT))
    delete_account(conn, user["id"])
    session.clear()
    return jsonify({"ok": True, "rejoinAfterDays": REJOIN_WAIT // 86400})


RESET_PER_HOUR = int(os.environ.get("RESET_PER_HOUR", 5))  # IP 하나당 1시간 재설정 요청 수


def reset_hash(user_id, code):
    return hmac.new(app.config["SECRET_KEY"].encode(), f"reset:{user_id}:{code}".encode(),
                    hashlib.sha256).hexdigest()


@app.post("/api/auth/reset/request")
def reset_request():
    """비밀번호 재설정 코드 메일. 가입 여부가 드러나지 않도록 응답은 항상 같다."""
    email = str(body().get("email", "")).strip()
    if len(email) > 254 or not EMAIL_RE.match(email):
        return err("올바른 이메일 주소를 입력해 주세요.")
    if not limiter.hit(("reset-ip", request.remote_addr), RESET_PER_HOUR, 3600):
        return err("요청이 너무 많습니다. 1시간 뒤에 다시 시도해 주세요.", 429)
    conn = db.get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE AND active = 1", (email,)).fetchone()
    now = int(time.time())
    if user and now - (user["reset_sent_at"] or 0) >= RESEND_GAP:
        code = f"{secrets.randbelow(10**6):06d}"
        try:
            send_mail(user["email"], f"[블루프린트] 비밀번호 재설정 코드 {code}",
                      f"비밀번호 재설정 코드예요.\n\n재설정 코드: {code}\n\n"
                      f"아이디: {user['username']}\n"
                      "비밀번호 재설정 화면에 위 6자리 코드와 새 비밀번호를 입력하세요. 코드는 30분 동안 유효합니다.\n\n"
                      "직접 요청하지 않았다면 이 메일을 무시하세요. 비밀번호는 바뀌지 않아요.",
                      html=RESET_MAIL_HTML.format(code=code, username=user["username"]))
            conn.execute("UPDATE users SET reset_code_hash = ?, reset_sent_at = ?, reset_attempts = 0 WHERE id = ?",
                         (reset_hash(user["id"], code), now, user["id"]))
            conn.commit()
        except Exception as e:
            app.logger.error("재설정 메일 실패: %s", e)
    return jsonify({"ok": True, "email": mask_email(email)})


@app.post("/api/auth/reset/confirm")
def reset_confirm():
    data = body()
    email = str(data.get("email", "")).strip()
    code = str(data.get("code", "")).strip()
    password = str(data.get("password", ""))
    conn = db.get_db()
    user = conn.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE AND active = 1", (email,)).fetchone()
    if user is None or not user["reset_code_hash"]:
        return err("코드가 올바르지 않거나 만료됐어요. 새 코드를 받아 주세요.", 400)
    if user["reset_attempts"] >= CODE_MAX_TRIES:
        return err("코드를 너무 많이 틀렸어요. 새 코드를 받아 주세요.", 429)
    if time.time() - (user["reset_sent_at"] or 0) > CODE_TTL:
        return err("코드가 만료됐어요. 새 코드를 받아 주세요.", 410)
    if not (re.fullmatch(r"\d{6}", code) and hmac.compare_digest(reset_hash(user["id"], code), user["reset_code_hash"])):
        conn.execute("UPDATE users SET reset_attempts = reset_attempts + 1 WHERE id = ?", (user["id"],))
        conn.commit()
        left = CODE_MAX_TRIES - user["reset_attempts"] - 1
        return err(f"코드가 맞지 않아요. {left}번 더 시도할 수 있어요." if left
                   else "코드를 너무 많이 틀렸어요. 새 코드를 받아 주세요.", 400)
    problem = password_problem(password, user["username"])
    if problem:
        return err(problem)
    # 새 비밀번호로 바꾸고, 모든 기기의 옛 로그인을 끊는다. 메일을 받은 것이니 이메일 인증도 끝난 것으로 본다
    conn.execute("UPDATE users SET password_hash = ?, session_ver = session_ver + 1, reset_code_hash = NULL,"
                 " reset_attempts = 0, verified_at = COALESCE(verified_at, ?) WHERE id = ?",
                 (generate_password_hash(password), int(time.time()), user["id"]))
    conn.commit()
    limiter.clear(("login-user", user["username"].lower()[:20]))
    return jsonify({"ok": True, "username": user["username"]})


@app.post("/api/auth/logout-all")
@login_required
def logout_all(user):
    """모든 기기(이 기기 포함)에서 로그아웃. 훔친 쿠키도 이 순간부터 못 쓴다."""
    conn = db.get_db()
    conn.execute("UPDATE users SET session_ver = session_ver + 1 WHERE id = ?", (user["id"],))
    conn.commit()
    session.clear()
    return jsonify({"ok": True})


# ---------------------------------------------------------------- 프로필 이미지

AVATARS = INSTANCE / "avatars"
AVATAR_SIZE = 256
AVATAR_MAX_BYTES = 5 * 1024 * 1024


def avatar_file(uid):
    return AVATARS / f"{int(uid)}.png"


@app.post("/api/profile/avatar")
@login_required
def upload_avatar(user):
    """{"image": "data:image/...;base64,..."} — JSON 으로 받아 CSRF 방어(require_json_for_writes)를 유지한다.
    Pillow 로 열어 정사각형으로 자르고 256px PNG 로 다시 저장하므로 원본 파일(메타데이터 포함)은 남지 않는다."""
    import base64
    import binascii
    import io
    from PIL import Image, UnidentifiedImageError

    raw = str(body().get("image", ""))
    _, _, b64 = raw.partition("base64,")
    try:
        data = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        return err("이미지 파일을 읽지 못했어요.")
    if not data or len(data) > AVATAR_MAX_BYTES:
        return err("5MB 이하의 이미지를 올려 주세요.")
    try:
        img = Image.open(io.BytesIO(data))
        if img.format not in ("PNG", "JPEG", "GIF", "WEBP") or img.width * img.height > 40_000_000:
            return err("PNG, JPG, GIF, WEBP 이미지만 올릴 수 있어요.")
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return err("이미지 파일을 읽지 못했어요.")
    side = min(img.size)
    left, top = (img.width - side) // 2, (img.height - side) // 2
    img = img.convert("RGBA").crop((left, top, left + side, top + side)).resize(
        (AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
    AVATARS.mkdir(parents=True, exist_ok=True)
    tmp = avatar_file(user["id"]).with_suffix(".tmp")
    img.save(tmp, "PNG", optimize=True)
    tmp.replace(avatar_file(user["id"]))
    conn = db.get_db()
    conn.execute("UPDATE users SET avatar_ver = ? WHERE id = ?", (int(time.time() * 1000), user["id"]))
    conn.commit()
    return jsonify(user_json(current_user()))


@app.delete("/api/profile/avatar")
@login_required
def delete_avatar(user):
    avatar_file(user["id"]).unlink(missing_ok=True)
    conn = db.get_db()
    conn.execute("UPDATE users SET avatar_ver = NULL WHERE id = ?", (user["id"],))
    conn.commit()
    return jsonify(user_json(current_user()))


@app.get("/api/users/<int:uid>/avatar.png")
def get_avatar(uid):
    path = avatar_file(uid)
    if not path.exists():
        return err("프로필 이미지가 없어요.", 404)
    # 주소에 ?v=버전이 붙어 있어서 바뀌면 주소도 바뀐다 → 오래 캐시해도 된다
    return send_file(path, mimetype="image/png", max_age=60 * 60 * 24 * 30)


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
@staff_required
def admin_users(_admin):
    rows = db.get_db().execute("""
        SELECT u.*,
               (SELECT COUNT(*) FROM servers s WHERE s.owner_id = u.id) AS server_count,
               (SELECT GROUP_CONCAT(DISTINCT l.mc_name) FROM server_links l WHERE l.user_id = u.id) AS mc_names,
               (SELECT COUNT(*) FROM library l WHERE l.user_id = u.id) AS library_count,
               (SELECT COUNT(*) FROM templates t WHERE t.author_id = u.id) AS upload_count
        FROM users u ORDER BY u.id DESC""").fetchall()
    return jsonify([{
        **user_json(u),
        "active": bool(u["active"]),
        "status": "inactive" if not u["active"] else "unverified" if u["email"] and u["verified_at"] is None
                  else "verified" if u["email"] else "legacy",
        "createdAt": u["created_at"],
        "serverCount": u["server_count"],
        "mcNames": u["mc_names"].split(",") if u["mc_names"] else [],
        "libraryCount": u["library_count"],
        "uploadCount": u["upload_count"],
    } for u in rows])


@app.post("/api/admin/users/<int:uid>/active")
@staff_required
def admin_user_active(actor, uid):
    """회원 정지/해제. 메인 관리자는 아무도 정지할 수 없고, 부 관리자는 다른 부 관리자를 정지할 수 없다."""
    target = db.get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    if target is not None and is_admin(target):
        return err("메인 관리자 계정은 정지할 수 없습니다.", 400)
    if target is not None and target["role"] == SUB_ADMIN and not is_admin(actor):
        return err("부 관리자 계정은 메인 관리자만 정지할 수 있습니다.", 403)
    return set_active("users", uid, body())


@app.post("/api/admin/users/<int:uid>/role")
@admin_required
def admin_user_role(_admin, uid):
    """부 관리자 지정/해제 ({"role": "sub_admin"} 또는 {"role": null}). 메인 관리자만."""
    role = body().get("role")
    if role not in (SUB_ADMIN, None):
        return err("role 은 sub_admin 또는 null 이어야 합니다.")
    conn = db.get_db()
    target = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    if target is None:
        return err("찾을 수 없습니다.", 404)
    if is_admin(target):
        return err("메인 관리자는 ADMIN_USERS 설정으로 정해져서 여기서 바꿀 수 없습니다.", 400)
    conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, uid))
    conn.commit()
    return jsonify({"ok": True, "role": role})


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
    delete_account(conn, uid)
    return jsonify({"ok": True})


@app.get("/api/admin/templates")
@staff_required
def admin_templates(_admin):
    rows = db.get_db().execute(TEMPLATE_SELECT + " ORDER BY t.id DESC").fetchall()
    return jsonify([template_summary(r) for r in rows])


@app.post("/api/admin/templates/<int:tid>/active")
@staff_required
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


def linked_user(mc_uuid):
    """이 서버(g.server_id)에서 연동한 플레이어의 웹 계정. 다른 서버에서 한 연동은 보이지 않는다."""
    return db.get_db().execute(
        "SELECT u.* FROM users u JOIN server_links l ON l.user_id = u.id"
        " WHERE l.server_id = ? AND l.mc_uuid = ? AND u.active = 1", (g.server_id, mc_uuid)).fetchone()


def server_label(server_id):
    row = db.get_db().execute("SELECT name FROM servers WHERE id = ?", (server_id,)).fetchone()
    return row["name"] if row and row["name"] else None


@app.post("/api/plugin/server")
@plugin_auth
def plugin_server():
    """플러그인이 켜질 때·config 를 다시 읽을 때 서버 이름을 알린다 ({"name": ""} 면 이름 없음)."""
    conn = db.get_db()
    conn.execute("UPDATE servers SET name = ? WHERE id = ?", (clean_server_name(body().get("name")), g.server_id))
    conn.commit()
    return jsonify({"id": g.server_id, "name": server_label(g.server_id)})


@app.post("/api/plugin/link")
@plugin_auth
def plugin_link():
    """인게임 /tb link 코드: 이 서버에 대한 연동을 하나 추가한다(서버마다 따로)."""
    data = body()
    code = str(data.get("code", "")).strip().upper()
    mc_uuid = parse_uuid(data.get("uuid"))
    mc_name = str(data.get("name", ""))[:16]
    if limiter.count(("link-fail", g.server_id), 600) >= LINK_FAILS_PER_10MIN:
        return err("연동 코드를 너무 많이 틀렸습니다. 10분 뒤에 다시 시도해 주세요.", 429)
    conn = db.get_db()
    # 조회와 소비를 한 문장으로: 같은 코드로 동시에 두 번 요청해도 한 번만 성공한다
    row = conn.execute("DELETE FROM link_codes WHERE code = ? AND expires_at >= ? RETURNING user_id",
                       (code, int(time.time()))).fetchone()
    if row is None:
        conn.commit()
        limiter.add(("link-fail", g.server_id))
        return err("연동 코드가 없거나 만료되었습니다. 웹사이트에서 새 코드를 발급받으세요.", 404)
    # 이 서버에서 같은 마인크래프트 계정이 다른 웹 계정에 연결돼 있었다면 그 연동을 넘겨받는다
    conn.execute("DELETE FROM server_links WHERE server_id = ? AND mc_uuid = ?", (g.server_id, mc_uuid))
    conn.execute(
        "INSERT INTO server_links (user_id, server_id, mc_uuid, mc_name, linked_at) VALUES (?, ?, ?, ?, ?)"
        " ON CONFLICT(user_id, server_id) DO UPDATE SET mc_uuid = excluded.mc_uuid, mc_name = excluded.mc_name,"
        " linked_at = excluded.linked_at",
        (row["user_id"], g.server_id, mc_uuid, mc_name, int(time.time())))
    conn.commit()
    user = conn.execute("SELECT username FROM users WHERE id = ?", (row["user_id"],)).fetchone()
    label = next(l["serverName"] for l in user_links(row["user_id"]) if l["serverId"] == g.server_id)
    return jsonify({"username": user["username"], "serverName": label})


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
    cur = conn.execute("DELETE FROM server_links WHERE server_id = ? AND mc_uuid = ?",
                       (g.server_id, parse_uuid(mc_uuid)))
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
         "profile": "profile.html", "admin": "admin.html", "terms": "terms.html",
         "privacy": "privacy.html", "copyright": "copyright.html", "forgot": "forgot.html"}


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
