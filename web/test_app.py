"""웹 API 통합 테스트: python -m unittest test_app"""
import os
import tempfile
import unittest
import uuid

_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["PLUGIN_API_KEY"] = "test-key"
os.environ.setdefault("SECRET_KEY", "test-secret")

from app import app  # noqa: E402

PLUGIN = {"Authorization": "Bearer test-key"}


class FlowTest(unittest.TestCase):
    def setUp(self):
        self.c = app.test_client()

    def register(self, name):
        r = self.c.post("/api/auth/register", json={"username": name, "password": "password123"})
        self.assertEqual(r.status_code, 201, r.json)
        return r.json

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
        self.assertEqual(self.c.get("/api/auth/me").json["minecraft"]["name"], "Steve")

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
        self.assertIsNone(self.c.get("/api/auth/me").json["minecraft"])

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
        r = self.c.post("/api/auth/register", json={"username": "builder3", "password": "password123"})
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

    def test_form_post_rejected(self):
        r = self.c.post("/api/auth/login", data={"username": "a", "password": "b"})
        self.assertEqual(r.status_code, 415)


if __name__ == "__main__":
    unittest.main()
