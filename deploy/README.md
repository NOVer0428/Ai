# 웹사이트 운영 배포

`web/app.py` 하나를 waitress로 띄우고, 앞에 HTTPS를 맡는 프록시를 둡니다.
VPS(nginx/Caddy), 집 PC + Cloudflare Tunnel, Render/Fly.io 어디든 같은 방식이에요.

## 1. 설치

```bash
cd web
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # 리눅스: .venv/bin/python
```

## 2. 환경변수

| 이름 | 운영 값 | 설명 |
|---|---|---|
| `PRODUCTION` | `1` | Flask 개발 서버 대신 waitress로 실행 |
| `HOST` | `127.0.0.1` | 프록시가 같은 컴퓨터에 있으면 그대로 둡니다. 컨테이너(Render/Fly.io)는 `0.0.0.0` |
| `PORT` | `5000` | 프록시가 넘겨줄 포트 |
| `COOKIE_SECURE` | `1` | 로그인 쿠키를 HTTPS에서만 보냅니다. **HTTP로 접속하면 로그인이 안 되니** HTTPS 뒤에서만 켜세요 |
| `TRUST_PROXY` | `1` | 프록시 뒤일 때만 켭니다. 실제 접속 IP를 읽어 로그인 시도 제한에 씁니다. 프록시 없이 인터넷에 직접 열면 끄세요(IP 위조 가능) |
| `DB_PATH` | (선택) | SQLite 파일 위치. 기본 `web/instance/app.db` |
| `MAIL_USER`, `MAIL_PASSWORD` | Gmail 주소, 앱 비밀번호 | 가입 인증 메일 발송. 없으면 메일 대신 서버 로그에 링크를 찍습니다(개발용) |
| `MAIL_HOST`, `MAIL_PORT` | (선택) | 기본 `smtp.gmail.com`, `587` |
| `ADMIN_USERS` | 관리자 아이디 | 쉼표로 여러 명. 이 아이디로 로그인하면 머리글에 "관리자" 메뉴가 생기고 /admin 에서 회원·템플릿을 비활성화/삭제합니다. 관리자 계정은 비활성화·삭제할 수 없습니다. 부 관리자는 관리자 페이지에서 메인 관리자가 지정합니다(템플릿 비/활성화, 회원 정지만 가능) |
| `ASSETS_DIR` | (선택) | 블록 에셋 위치. 기본 `~/.blueprint/assets` |
| `SECRET_KEY`, `PLUGIN_API_KEY` | (선택) | 없으면 `web/instance/`에 자동 생성됩니다 |

실행 예 (PowerShell):

```powershell
$env:PRODUCTION="1"; $env:COOKIE_SECURE="1"; $env:TRUST_PROXY="1"
.venv/Scripts/python app.py
```

리눅스:

```bash
PRODUCTION=1 COOKIE_SECURE=1 TRUST_PROXY=1 .venv/bin/python app.py
```

## 3. HTTPS 프록시

- **VPS + Caddy** (인증서 자동): `Caddyfile`에 `example.com { reverse_proxy 127.0.0.1:5000 }`
- **집 PC + Cloudflare Tunnel**: `cloudflared tunnel --url http://127.0.0.1:5000` (이름 있는 터널을 만들어 도메인에 연결)
- **Render / Fly.io**: 플랫폼이 HTTPS를 처리합니다. `HOST=0.0.0.0`, `PORT`는 플랫폼 값

프록시는 한 단계만 있다고 가정합니다(`ProxyFix x_for=1`).

## 4. 데이터 보관과 백업

지워지면 안 되는 것은 `web/instance/` 폴더 하나입니다(프로필 사진 `avatars/` 포함).

- `app.db` — 회원, 업로드 템플릿, 보관함
- `secret_key.txt` — 바뀌면 모두 로그아웃됩니다
- `plugin_api_key.txt` — 바뀌면 플러그인 `config.yml`도 바꿔야 합니다
- `thumbs/` — 다시 만들 수 있어서 백업하지 않아도 됩니다

블록 에셋은 `~/.blueprint/assets`(또는 `ASSETS_DIR`)에 따로 있어요. 다시 받을 수 있어서 백업하지 않아도 됩니다.

Render/Fly.io는 디스크가 재배포 때 지워지므로 **볼륨을 `web/instance`에 붙이세요.**

백업은 서버를 켠 채로 SQLite 백업 명령을 쓰세요(파일 복사보다 안전):

```bash
.venv/bin/python -c "import sqlite3; s=sqlite3.connect('instance/app.db'); d=sqlite3.connect('backup.db'); s.backup(d)"
```

## 5. 플러그인 연결

키는 두 종류입니다.

- **서버 키** (보통 이것): 로그인 → 내 보관함 → "내 마인크래프트 서버" → **서버 추가**. 서버마다 키가 따로 나옵니다. `bp_`로 시작하고,
  **그 키로 연동한 플레이어만** 조회·업로드·해제할 수 있습니다. 원문은 발급 직후 한 번만 보여 주고 서버에는 해시만 저장합니다.
  새로 발급하면 옛 키는 바로 막히고, 연동된 플레이어는 새 키로 그대로 이어집니다.
- **운영자 키**: `web/instance/plugin_api_key.txt` (또는 `PLUGIN_API_KEY`). 모든 플레이어에 접근하므로 사이트 운영자 서버에서만 씁니다.

플러그인 `config.yml`의 `api-url`을 배포 주소(`https://example.com`)로, `api-key`를 위 키로 바꿉니다.

## 6. 가입 인증 메일 (Gmail)

1. 보낼 Gmail 계정에서 2단계 인증을 켭니다.
2. Google 계정 → 보안 → **앱 비밀번호**에서 16자리 비밀번호를 만듭니다.
3. 서버 환경변수 `MAIL_USER`(Gmail 주소), `MAIL_PASSWORD`(앱 비밀번호)를 넣습니다.
   PythonAnywhere는 WSGI 파일 맨 위에 `os.environ["MAIL_USER"] = "..."` 형태로 넣고 Reload 합니다.

인증 메일에는 6자리 코드(30분 유효, 5번 틀리면 새 코드 필요)와 링크(24시간 유효)가 함께 들어갑니다. 가입 직후 화면에서 코드를 입력하면 바로 로그인됩니다. 인증 전에 로그인하면 코드 입력 화면이 다시 뜨고, "코드 다시 받기"는 3분에 한 번 새 코드를 보냅니다.
24시간 안에 인증하지 않은 가입은 다음 가입 때 지워져서 아이디·이메일을 다시 쓸 수 있습니다.
이메일 기능 전에 가입한 계정(이메일 없음)은 인증 없이 그대로 로그인됩니다.

## 7. 썸네일 텍스처

`tools/fetch_assets.py`는 Mojang `client.jar`에서 텍스처를 꺼냅니다. 공개 사이트에 이 텍스처로 만든 이미지를
보여 줘도 되는지는 [Minecraft 이용 지침](https://www.minecraft.net/usage-guidelines)을 직접 확인하세요.
에셋이 없으면 단순 색상 미리보기로 표시됩니다.

## PythonAnywhere 무료 (카드 없이)

지금 운영 중: https://noha04.pythonanywhere.com

- 코드: `~/Ai` (GitHub 클론). 갱신은 Bash 콘솔에서 `cd ~/Ai && git pull` 후 Web 탭에서 **Reload**
- 가상환경: `~/Ai/web/.venv` (Web 탭 Virtualenv에 연결)
- WSGI: `/var/www/noha04_pythonanywhere_com_wsgi.py` — `COOKIE_SECURE=1`, `TRUST_PROXY=1`을 넣고 `app`을 불러옵니다
- 에셋: 무료 계정은 Mojang 서버에 접속할 수 없어서(403) `fetch_assets.py`가 실패합니다. 내 PC의 에셋을 zip으로 묶어 Files 화면에서 올리고 콘솔에서 풀었습니다
- **한 달에 한 번** Web 탭에서 "Run until 1 month from today"를 눌러야 사이트가 계속 켜집니다(일주일 전에 메일이 옵니다)
- 플러그인 키: Files 화면에서 `~/Ai/web/instance/plugin_api_key.txt`

## 제한 사항

- 로그인 시도 제한(아이디당 10분에 5회, IP당 20회)은 메모리에 저장됩니다. 재시작하면 초기화되고,
  프로세스를 여러 개 띄우면 각자 따로 셉니다. 지금 구성(프로세스 1개, 스레드 8개)에서는 문제없습니다.
