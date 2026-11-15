"""웹 API 통합 테스트: python -m unittest test_app"""
import os
import tempfile
import unittest
import uuid

_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["PLUGIN_API_KEY"] = "test-key"
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ["ADMIN_USERS"] = "boss1"

import re  # noqa: E402

import app as appmod  # noqa: E402
from app import app  # noqa: E402

PLUGIN = {"Authorization": "Bearer test-key"}
appmod.AVATARS = __import__("pathlib").Path(_tmp) / "avatars"  # 테스트 사진은 임시 폴더에
MAILS = []  # (받는 사람, 제목, 본문)
appmod.send_mail = lambda to, subject, text: MAILS.append((to, subject, text))


def verify_path(email):
    text = next(t for to, _, t in reversed(MAILS) if to == email)
    return re.search(r"https?://[^/]+(/verify\?token=\S+)", text).group(1)


class FlowTest(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()

    def register(self, name):
        email = f"{name}@example.com"
        r = self.c.post("/api/auth/register", json={"username": name, "email": email, "password": "password123"})
        self.assertEqual(r.status_code, 201, r.json)
        r = self.c.get(verify_path(email))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/library?verified=1", r.headers["Location"])
        return self.c.get("/api/auth/me").json

    def test_email_verification(self):
        body = {"username": "mailuser1", "email": "mailuser1@example.com", "password": "password123"}
        r = self.c.post("/api/auth/register", json=body)
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(self.c.get("/api/auth/me").json)  # 인증 전에는 로그인 안 됨
        login = {"username": "mailuser1", "password": "password123"}
        self.assertEqual(self.c.post("/api/auth/login", json=login).status_code, 403)
        # 잘못된 토큰
        self.assertIn("verify=invalid", self.c.get("/verify?token=bad").headers["Location"])
        # 같은 이메일로 또 가입 불가
        dup = {"username": "mailuser2", "email": "MailUser1@example.com", "password": "password123"}
        self.assertEqual(self.c.post("/api/auth/register", json=dup).status_code, 409)
        bad = {"username": "mailuser3", "email": "not-an-email", "password": "password123"}
        self.assertEqual(self.c.post("/api/auth/register", json=bad).status_code, 400)
        # 인증 후 로그인
        self.c.get(verify_path("mailuser1@example.com"))
        self.c.post("/api/auth/logout")
        self.assertEqual(self.c.post("/api/auth/login", json=login).status_code, 200)

    def test_remember_me(self):
        self.register("remember1")
        self.c.post("/api/auth/logout")
        creds = {"username": "remember1", "password": "password123"}
        r = self.c.post("/api/auth/login", json=creds)
        self.assertNotIn("Expires", r.headers["Set-Cookie"])  # 브라우저를 닫으면 끝나는 쿠키
        r = self.c.post("/api/auth/login", json={**creds, "remember": True})
        self.assertIn("Expires", r.headers["Set-Cookie"])     # 30일 유지

    def test_avatar(self):
        import base64
        import io
        from PIL import Image
        me = self.register("avatar1")
        self.assertIsNone(me["avatar"])

        def data_url(img, fmt):
            buf = io.BytesIO()
            img.save(buf, fmt)
            return f"data:image/{fmt.lower()};base64," + base64.b64encode(buf.getvalue()).decode()

        r = self.c.post("/api/profile/avatar", json={"image": data_url(Image.new("RGB", (400, 300), "red"), "JPEG")})
        self.assertEqual(r.status_code, 200, r.json)
        url = r.json["avatar"]
        png = self.c.get(url)
        self.assertEqual(png.status_code, 200)
        self.assertEqual(Image.open(io.BytesIO(png.data)).size, (256, 256))  # 가운데 정사각형으로 잘림
        png.close()
        self.assertEqual(self.c.get("/api/auth/me").json["avatar"], url)
        # 이미지가 아닌 것은 거절
        bad = "data:image/png;base64," + base64.b64encode(b"<script>alert(1)</script>").decode()
        self.assertEqual(self.c.post("/api/profile/avatar", json={"image": bad}).status_code, 400)
        self.assertEqual(self.c.post("/api/profile/avatar", json={"image": "not base64!"}).status_code, 400)
        # 로그인 없이 불가
        self.assertEqual(app.test_client().post("/api/profile/avatar", json={"image": bad}).status_code, 401)
        # 삭제
        self.assertIsNone(self.c.delete("/api/profile/avatar").json["avatar"])
        self.assertEqual(self.c.get(url).status_code, 404)

    def test_email_code(self):
        body = {"username": "codeuser1", "email": "codeuser1@example.com", "password": "password123"}
        self.assertEqual(self.c.post("/api/auth/register", json=body).status_code, 201)
        code = re.search(r"인증 코드: (\d{6})", next(t for to, _, t in reversed(MAILS)
                                                     if to == "codeuser1@example.com")).group(1)
        wrong = "000000" if code != "000000" else "111111"
        r = self.c.post("/api/auth/verify-code", json={"username": "CodeUser1", "code": wrong})
        self.assertEqual(r.status_code, 400)
        self.assertIn("4번", r.json["error"])
        # 인증 전 로그인 → 코드 입력 화면용 정보
        r = self.c.post("/api/auth/login", json={"username": "codeuser1", "password": "password123"})
        self.assertEqual(r.status_code, 403)
        self.assertTrue(r.json["needsVerify"])
        r = self.c.post("/api/auth/verify-code", json={"username": "codeuser1", "code": code})
        self.assertEqual(r.status_code, 200, r.json)
        self.assertEqual(self.c.get("/api/auth/me").json["username"], "codeuser1")
        # 이미 인증됨 → 다시 쓸 수 없음
        self.assertEqual(self.c.post("/api/auth/verify-code", json={"username": "codeuser1", "code": code}).status_code, 404)

        # 5번 틀리면 맞는 코드도 거절
        body = {"username": "codeuser2", "email": "codeuser2@example.com", "password": "password123"}
        self.c.post("/api/auth/register", json=body)
        code = re.search(r"인증 코드: (\d{6})", MAILS[-1][2]).group(1)
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(5):
            self.c.post("/api/auth/verify-code", json={"username": "codeuser2", "code": wrong})
        self.assertEqual(self.c.post("/api/auth/verify-code", json={"username": "codeuser2", "code": code}).status_code, 429)

    def test_admin_and_profile(self):
        boss, user, other = app.test_client(), app.test_client(), app.test_client()
        for client, name in ((boss, "boss1"), (user, "writer1"), (other, "viewer1")):
            self.c = client
            self.register(name)
        self.assertTrue(boss.get("/api/auth/me").json["isAdmin"])
        self.assertFalse(user.get("/api/auth/me").json["isAdmin"])
        self.assertEqual(user.get("/api/admin/users").status_code, 403)

        data = {"size": [1, 1, 1], "palette": ["minecraft:stone"], "blocks": [[0, 0, 0, 0]]}
        tid = user.post("/api/templates", json={"name": "숨길 집", "data": data}).json["id"]
        self.assertEqual(other.post(f"/api/library/{tid}").status_code, 200)
        prof = user.get("/api/profile").json
        # 올린 템플릿은 작성자 보관함에도 자동으로 담기므로 담기 수는 2
        self.assertEqual((prof["stats"]["uploads"], prof["stats"]["savesReceived"]), (1, 2))

        # 템플릿 비활성화: 일반 사용자 목록·상세·보관함에서 사라지고, 작성자·관리자는 본다
        self.assertEqual(boss.post(f"/api/admin/templates/{tid}/active", json={"active": False}).status_code, 200)
        ids = lambda c: [t["id"] for t in c.get("/api/templates").json["templates"]]
        self.assertNotIn(tid, ids(other))
        self.assertEqual(other.get(f"/api/templates/{tid}").status_code, 404)
        self.assertEqual(other.get("/api/library").json, [])
        self.assertEqual(other.post(f"/api/library/{tid}").status_code, 404)
        self.assertEqual(user.get(f"/api/templates/{tid}").status_code, 200)
        self.assertFalse(user.get("/api/profile").json["uploads"][0]["active"])
        self.assertIn(tid, [t["id"] for t in boss.get("/api/admin/templates").json])
        # 다시 활성화하면 보관함에도 돌아온다
        boss.post(f"/api/admin/templates/{tid}/active", json={"active": True})
        self.assertEqual([t["id"] for t in other.get("/api/library").json], [tid])
        # 기본 템플릿은 삭제 불가
        builtin = next(t for t in boss.get("/api/admin/templates").json if t["builtin"])
        self.assertEqual(boss.delete(f"/api/admin/templates/{builtin['id']}").status_code, 400)

        # 회원 비활성화: 세션이 끊기고 로그인 불가
        wid = user.get("/api/auth/me").json["id"]
        row = next(u for u in boss.get("/api/admin/users").json if u["id"] == wid)
        self.assertEqual((row["uploadCount"], row["status"]), (1, "verified"))
        boss.post(f"/api/admin/users/{wid}/active", json={"active": False})
        self.assertIsNone(user.get("/api/auth/me").json)
        r = user.post("/api/auth/login", json={"username": "writer1", "password": "password123"})
        self.assertEqual(r.status_code, 403)
        # 관리자 자신은 비활성화·삭제 불가
        bid = boss.get("/api/auth/me").json["id"]
        self.assertEqual(boss.post(f"/api/admin/users/{bid}/active", json={"active": False}).status_code, 400)
        self.assertEqual(boss.delete(f"/api/admin/users/{bid}").status_code, 400)
        # 회원 삭제: 올린 템플릿도 함께 삭제
        self.assertEqual(boss.delete(f"/api/admin/users/{wid}").status_code, 200)
        self.assertNotIn(tid, [t["id"] for t in boss.get("/api/admin/templates").json])

        # 비밀번호 변경
        self.assertEqual(other.post("/api/auth/password", json={"current": "nope", "new": "newpass123"}).status_code, 403)
        self.assertEqual(other.post("/api/auth/password", json={"current": "password123", "new": "newpass123"}).status_code, 200)
        other.post("/api/auth/logout")
        self.assertEqual(other.post("/api/auth/login", json={"username": "viewer1", "password": "newpass123"}).status_code, 200)

    def test_servers_and_links(self):
        # 서버 주인 A 는 서버 2개, B 는 1개. 서버마다 키가 따로
        a, b = app.test_client(), app.test_client()
        for client, name in ((a, "owner_a"), (b, "owner_b")):
            self.c = client
            self.register(name)
        self.assertEqual(a.get("/api/servers").json, [])
        a1 = a.post("/api/servers").json
        a2 = a.post("/api/servers").json
        b1 = b.post("/api/servers").json
        self.assertTrue(a1["key"].startswith("bp_"))
        self.assertEqual([s["name"] for s in a.get("/api/servers").json], ["Minecraft Server (1)", "Minecraft Server (2)"])
        h = lambda srv, name=None: {"Authorization": f"Bearer {srv['key']}",
                                    **({"X-Server-Name": __import__("urllib.parse").parse.quote(name)} if name is not None else {})}

        # 플레이어가 A1 에서 연동 → 목록 1개, A2 에서 또 연동 → 목록 2개
        self.c = app.test_client()
        self.register("player_a")
        mc = str(uuid.uuid4())
        for srv in (a1, a2):
            code = self.c.post("/api/link/code").json["code"]
            r = self.c.post("/api/plugin/link", json={"code": code, "uuid": mc, "name": "P"}, headers=h(srv))
            self.assertEqual(r.status_code, 200, r.json)
        names = lambda: [l["serverName"] for l in self.c.get("/api/links").json]
        self.assertEqual(names(), ["Minecraft Server (1)", "Minecraft Server (2)"])

        # 서버 이름: 헤더로 보내면 바로 바뀌고, 비우면 다시 번호 이름
        self.c.get(f"/api/plugin/players/{mc}/library", headers=h(a1, "모닥불 서버"))
        self.assertEqual(names(), ["모닥불 서버", "Minecraft Server (1)"])
        self.assertEqual(self.c.post("/api/plugin/server", json={"name": "  "}, headers=h(a1)).json["name"], None)
        self.assertEqual(names(), ["Minecraft Server (1)", "Minecraft Server (2)"])
        self.c.post("/api/plugin/server", json={"name": "야생 서버"}, headers=h(a2))
        self.assertEqual(names(), ["Minecraft Server (1)", "야생 서버"])

        # 연동하지 않은 서버(B1)에서는 이 플레이어가 안 보인다 / 해제·업로드 불가
        self.assertEqual(self.c.get(f"/api/plugin/players/{mc}/library", headers=h(b1)).status_code, 404)
        self.assertEqual(self.c.post(f"/api/plugin/players/{mc}/unlink", headers=h(b1)).status_code, 404)
        data = {"size": [1, 1, 1], "palette": ["minecraft:stone"], "blocks": [[0, 0, 0, 0]]}
        self.assertEqual(self.c.post(f"/api/plugin/players/{mc}/templates", json={"name": "x", "data": data},
                                     headers=h(b1)).status_code, 404)
        self.assertEqual(self.c.get(f"/api/plugin/players/{mc}/library", headers=h(a2)).status_code, 200)

        # 웹에서 서버 하나만 연동 해제
        self.c.delete(f"/api/links/{a1['id']}")
        self.assertEqual(names(), ["야생 서버"])
        self.assertEqual(self.c.get(f"/api/plugin/players/{mc}/library", headers=h(a1)).status_code, 404)
        self.assertEqual(a.get("/api/servers").json[1]["players"], 1)

        # 키 재발급: 옛 키는 막히고 연동은 유지
        new_a2 = a.post(f"/api/servers/{a2['id']}/key").json
        self.assertEqual(self.c.get(f"/api/plugin/players/{mc}/library", headers=h(a2)).status_code, 401)
        self.assertEqual(self.c.get(f"/api/plugin/players/{mc}/library", headers=h(new_a2)).status_code, 200)
        # 남의 서버는 못 건드림 / 서버 삭제하면 연동도 사라짐
        self.assertEqual(b.delete(f"/api/servers/{a2['id']}").status_code, 404)
        self.assertEqual(a.delete(f"/api/servers/{a2['id']}").status_code, 200)
        self.assertEqual(names(), [])
        self.assertEqual(app.test_client().post("/api/servers").status_code, 401)

    def test_full_flow(self):
        templates = self.c.get("/api/templates").json["templates"]
        self.assertGreaterEqual(len(templates), 5)
        tid = templates[0]["id"]

        # 비로그인 보관함 접근 불가
        self.assertEqual(self.c.post(f"/api/library/{tid}").status_code, 401)

        self.register("builder1")
        self.assertEqual(self.c.post(f"/api/library/{tid}").status_code, 200)
        self.assertEqual([t["id"] for t in self.c.get("/api/library").json], [tid])

        # 연동 전 플러그인 조회 → 404
        mc = str(uuid.uuid4())
        self.assertEqual(self.c.get(f"/api/plugin/players/{mc}/library", headers=PLUGIN).status_code, 404)

        # 잘못된 API 키
        self.assertEqual(self.c.get(f"/api/plugin/players/{mc}/library").status_code, 401)

        code = self.c.post("/api/link/code").json["code"]
        r = self.c.post("/api/plugin/link", json={"code": code, "uuid": mc, "name": "Steve"}, headers=PLUGIN)
        self.assertEqual(r.status_code, 200, r.json)
        self.assertEqual(r.json["username"], "builder1")
        links = self.c.get("/api/links").json
        self.assertEqual([(l["serverName"], l["minecraft"]["name"]) for l in links], [("Minecraft Server (1)", "Steve")])

        # 코드는 1회용
        r = self.c.post("/api/plugin/link", json={"code": code, "uuid": mc, "name": "Steve"}, headers=PLUGIN)
        self.assertEqual(r.status_code, 404)

        lib = self.c.get(f"/api/plugin/players/{mc}/library", headers=PLUGIN).json
        self.assertEqual([t["id"] for t in lib["templates"]], [tid])
        full = self.c.get(f"/api/plugin/players/{mc}/templates/{tid}", headers=PLUGIN).json
        self.assertIn("blocks", full["data"])

        # 보관함에 없는 템플릿은 못 받음
        other = templates[1]["id"]
        self.assertEqual(self.c.get(f"/api/plugin/players/{mc}/templates/{other}", headers=PLUGIN).status_code, 404)

        # 인게임 업로드 → 자동으로 보관함에 추가
        data = {"size": [2, 1, 1], "palette": ["minecraft:stone", "minecraft:air"], "blocks": [[0, 0, 0, 0], [1, 0, 0, 1]]}
        r = self.c.post(f"/api/plugin/players/{mc}/templates", json={"name": "돌", "data": data}, headers=PLUGIN)
        self.assertEqual(r.status_code, 201, r.json)
        lib = self.c.get(f"/api/plugin/players/{mc}/library", headers=PLUGIN).json
        self.assertEqual(len(lib["templates"]), 2)
        self.assertEqual(lib["templates"][1]["blockCount"], 1)  # air 제거됨

        # 인게임 연동 해제
        self.assertEqual(self.c.post(f"/api/plugin/players/{mc}/unlink", headers=PLUGIN).status_code, 200)
        self.assertEqual(self.c.get("/api/links").json, [])

    def test_validation(self):
        self.register("builder2")
        bad = [
            {"size": [1, 1, 1], "palette": ["stone"], "blocks": [[0, 0, 0, 0]]},
            {"size": [1, 1, 1], "palette": ["minecraft:stone"], "blocks": [[1, 0, 0, 0]]},
            {"size": [1, 1, 1], "palette": ["minecraft:stone"], "blocks": [[0, 0, 0, 3]]},
            {"size": [999, 1, 1], "palette": ["minecraft:stone"], "blocks": [[0, 0, 0, 0]]},
            {"size": [True, 1, 1], "palette": ["minecraft:stone"], "blocks": [[False, 0, 0, False]]},
            # 26.3 블록 레지스트리 검사: 없는 블록 / 없는 속성 / 허용되지 않은 값
            {"size": [1, 1, 1], "palette": ["minecraft:not_a_block"], "blocks": [[0, 0, 0, 0]]},
            {"size": [1, 1, 1], "palette": ["minecraft:stone[facing=north]"], "blocks": [[0, 0, 0, 0]]},
            {"size": [1, 1, 1], "palette": ["minecraft:oak_stairs[facing=up]"], "blocks": [[0, 0, 0, 0]]},
        ]
        ok = {"size": [1, 1, 1], "palette": ["minecraft:oak_stairs[facing=east,half=top]"], "blocks": [[0, 0, 0, 0]]}
        self.assertEqual(self.c.post("/api/templates", json={"name": "ok", "data": ok}).status_code, 201)
        for d in bad:
            r = self.c.post("/api/templates", json={"name": "x", "data": d})
            self.assertEqual(r.status_code, 400, d)

    def test_auth_errors(self):
        self.register("builder3")
        self.c.post("/api/auth/logout")
        r = self.c.post("/api/auth/register",
                        json={"username": "builder3", "email": "other3@example.com", "password": "password123"})
        self.assertEqual(r.status_code, 409)
        r = self.c.post("/api/auth/login", json={"username": "builder3", "password": "wrongpass"})
        self.assertEqual(r.status_code, 401)
        r = self.c.post("/api/auth/login", json={"username": "BUILDER3", "password": "password123"})
        self.assertEqual(r.status_code, 200)

    @unittest.skipUnless(__import__("thumbnail").available(), "블록 에셋 없음 (tools/fetch_assets.py)")
    def test_thumbnail(self):
        tid = self.c.get("/api/templates").json["templates"][0]["id"]
        for q in ("", "?rot=1", "?maxY=2"):
            r = self.c.get(f"/api/templates/{tid}/thumbnail.png{q}")
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.data.startswith(b"\x89PNG"))
        r = self.c.get("/api/blocks/icon.png?state=minecraft:oak_stairs")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.c.get("/api/blocks/icon.png?state=../../app").status_code, 404)

    def test_builtin_templates(self):
        from seed import seed_templates
        seeds = seed_templates()
        self.assertEqual(len(seeds), 17)  # 갈림길 모퉁이 주택 + 15종 + 현실형 1종
        self.assertEqual(len({t["name"] for t in seeds}), 17)
        names = {t["name"] for t in self.c.get("/api/templates").json["templates"]}
        self.assertTrue({t["name"] for t in seeds} <= names)
        self.assertNotIn("아늑한 오두막", names)  # 지운 옛 기본 템플릿

    def test_builtin_templates_structure(self):
        """기본 템플릿마다 지지 없는 블록·짝 없는 문/침대·샐 유체·막힌 방이 없어야 한다 (qa.py)."""
        from qa import check
        from seed import seed_templates
        from template_format import validate
        for t in seed_templates():
            issues = check(validate(t["data"]))
            self.assertEqual(issues, [], f"{t['name']}: {issues[:5]}")

    def test_real_templates_strict(self):
        """현실형 템플릿은 외피 구멍·걸어서 못 가는 가구·떠 있는 블록도 없어야 한다 (qa.strict_check)."""
        from qa import check, strict_check
        from template_format import validate
        from village_real import real_templates
        for t in real_templates():
            data = validate(t["data"])
            issues = check(data) + strict_check(data)
            self.assertEqual(issues, [], f"{t['name']}: {issues[:5]}")

    def test_login_rate_limit(self):
        self.register("ratelimit1")
        bad = {"username": "ratelimit1", "password": "wrong-password"}
        for _ in range(5):
            self.assertEqual(self.c.post("/api/auth/login", json=bad).status_code, 401)
        self.assertEqual(self.c.post("/api/auth/login", json=bad).status_code, 429)
        # 막힌 동안에는 맞는 비밀번호도 거절
        good = {"username": "ratelimit1", "password": "password123"}
        self.assertEqual(self.c.post("/api/auth/login", json=good).status_code, 429)

    def test_form_post_rejected(self):
        r = self.c.post("/api/auth/login", data={"username": "a", "password": "b"})
        self.assertEqual(r.status_code, 415)


if __name__ == "__main__":
    unittest.main()
