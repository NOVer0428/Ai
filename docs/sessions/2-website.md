# 세션 2: 웹사이트

## 세션 시작할 때 붙여 넣을 정보

```
이 세션은 웹사이트(web/ 의 app.py, db.py, static/, thumbnail.py, materials.py, 배포 설정)만 다룬다.
템플릿 건물 코드(village_*.py, seed_*.py, qa.py)와 플러그인(plugin/)은 다른 세션 담당이라 고치지 않는다.
작업 목록: docs/sessions/2-website.md

규칙
- 사용자에게 보이는 글은 모두 한국어로 쓴다(진행 문구, 요약, 버튼 포함).
- 마인크래프트 에셋(client.jar 텍스처 등)은 저장소에 커밋하지 않는다(web/instance/ 는 .gitignore).
- 파일을 받기 전에 파일명·출처·크기를 알리고 허락을 받는다.
- 사용자 이메일 등 개인정보를 외부 요청에 넣지 않는다.
- 커밋·푸시는 사용자가 요청할 때만 한다.

구조
- Flask 3.1.3 + SQLite, 가상환경 web/.venv, 의존성 web/requirements.txt (Flask, Pillow 13)
- 실행: cd web; .venv/Scripts/python app.py  (HOST/PORT/DB_PATH/SECRET_KEY/PLUGIN_API_KEY 환경변수)
- 비밀값: web/instance/secret_key.txt, plugin_api_key.txt (없으면 자동 생성)
- 인증: 세션 쿠키(HttpOnly, SameSite=Lax), 쓰기 요청은 JSON만(CSRF 대비), 플러그인은 Bearer API 키
- db.init_db: 기본 템플릿을 코드(seed.seed_templates)와 동기화. 코드에서 빠진 기본 템플릿은 DB에서 삭제
- 템플릿 검사: template_format.validate() 가 26.3 레지스트리(data/blocks-26.3.json)로 블록·속성 검사
- 썸네일: thumbnail.py 가 client.jar 블록 모델로 등각 PNG 렌더, 시작할 때 미리 렌더
  에셋 받기: .venv/Scripts/python tools/fetch_assets.py (SHA1 검증, ~/.blueprint/assets 에 한 번만, 약 12MB, ASSETS_DIR 로 변경)
- 재료 목록: materials.py (블록 상태 → 아이템 개수, ko_kr 한국어 이름, 아이콘)
- 화면: static/index.html(목록) template.html(상세·재료·회전/높이 뷰어) library.html login/register upload

API
- /api/auth/register(이메일 필수, 코드+링크 메일)|verify-code(POST 6자리 코드)|login(인증 전 403 + needsVerify)|logout|me, GET /verify?token= (메일 링크)
- /api/templates (GET 목록, POST 업로드), /api/templates/<id> (GET, DELETE), .../thumbnail.png?rot&maxY
- /api/library, /api/library/<id> (POST 담기, DELETE 빼기)
- /api/link/code (POST 6자리 연동 코드), /api/link (DELETE)
- /api/profile (내 프로필·통계·올린 템플릿), /api/auth/password (POST 비밀번호 변경)
- /api/admin/users, /api/admin/templates (GET 목록), .../<id>/active (POST {active}), .../<id> (DELETE). ADMIN_USERS 환경변수의 아이디만. 비활성 템플릿은 작성자·관리자만 보고, 비활성 회원은 로그인·플러그인 차단. 회원 삭제 시 올린 템플릿도 삭제, 기본 템플릿은 삭제 불가(비활성화만)
- /api/server-key (GET 정보, POST 발급·재발급): 회원 서버 키. 플러그인 API는 운영자 키(전체) 또는 회원 키(그 키로 연동한 플레이어만)
- /api/items/<item>/icon.png, /api/blocks/icon.png?state=
- /api/plugin/* : 플러그인 전용 (세션 1 문서 참고) — 바꾸면 플러그인 세션에 알린다

테스트: cd web; .venv/Scripts/python -m unittest test_app  (13개)
운영 실행: deploy/README.md (PRODUCTION / COOKIE_SECURE / TRUST_PROXY 환경변수)
```

## 현재 상태

- 로컬에서 동작해요. 템플릿 17종, 썸네일, 한국어 재료 목록, 로그인, 보관함, 연동 코드까지 확인했어요.
- 운영 배포는 아직 안 했어요. `gh` CLI가 없어서 PR도 만들지 못했고, 브랜치만 푸시해 둔 상태예요.

## 할 일 (배포 준비)

- [ ] 배포 장소를 사용자에게 정해 달라고 해요.
  - VPS: 이 구조에 가장 잘 맞아요.
  - Render나 Fly.io: 볼륨을 따로 붙여야 해요.
  - 집 PC + Cloudflare Tunnel
- [x] 운영용 서버로 바꿔요. `PRODUCTION=1`이면 waitress로 실행해요.
- [x] HTTPS 설정을 넣어요. `COOKIE_SECURE=1`, `TRUST_PROXY=1`(ProxyFix)
- [x] 로그인을 여러 번 실패하면 막아요(아이디 5회, IP 20회 / 10분, 메모리 저장).
- [x] 데이터 보관·백업 방법을 `deploy/README.md`에 적었어요. 실제 위치는 배포 장소가 정해지면 정해요.
- [ ] 썸네일 텍스처 정책을 정해요.
  - Mojang 이용 지침은 사용자가 직접 확인하게 안내해요.
  - 대안: 썸네일 PNG만 미리 만들어 배포해요.
- [x] 배포 설정 파일과 한국어 설명서를 만들어요. `deploy/README.md`
- [ ] 플러그인 `api-url`을 배포 주소로 바꾸는 방법을 플러그인 세션에 알려요.

## 할 일 (기능)

- [ ] 템플릿 목록에 카테고리 필터와 검색을 넣어요.
- [ ] 상세 페이지에 층별 단면 보기를 넣어요. `maxY` 뷰어는 이미 있어요.
- [ ] 내 업로드 템플릿을 수정하고 삭제하는 화면을 만들어요.
- [ ] 모바일 화면을 점검해요.
