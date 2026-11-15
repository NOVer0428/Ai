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

지워지면 안 되는 것은 `web/instance/` 폴더 하나입니다.

- `app.db` — 회원, 업로드 템플릿, 보관함
- `secret_key.txt` — 바뀌면 모두 로그아웃됩니다
- `plugin_api_key.txt` — 바뀌면 플러그인 `config.yml`도 바꿔야 합니다
- `assets/`, `thumbs/` — 다시 만들 수 있어서 백업하지 않아도 됩니다

Render/Fly.io는 디스크가 재배포 때 지워지므로 **볼륨을 `web/instance`에 붙이세요.**

백업은 서버를 켠 채로 SQLite 백업 명령을 쓰세요(파일 복사보다 안전):

```bash
.venv/bin/python -c "import sqlite3; s=sqlite3.connect('instance/app.db'); d=sqlite3.connect('backup.db'); s.backup(d)"
```

## 5. 플러그인 연결

마인크래프트 서버의 플러그인 `config.yml`에서 `api-url`을 배포 주소(`https://example.com`)로,
`api-key`를 `web/instance/plugin_api_key.txt` 내용으로 바꿉니다.

## 6. 썸네일 텍스처

`tools/fetch_assets.py`는 Mojang `client.jar`에서 텍스처를 꺼냅니다. 공개 사이트에 이 텍스처로 만든 이미지를
보여 줘도 되는지는 [Minecraft 이용 지침](https://www.minecraft.net/usage-guidelines)을 직접 확인하세요.
에셋이 없으면 단순 색상 미리보기로 표시됩니다.

## 제한 사항

- 로그인 시도 제한(아이디당 10분에 5회, IP당 20회)은 메모리에 저장됩니다. 재시작하면 초기화되고,
  프로세스를 여러 개 띄우면 각자 따로 셉니다. 지금 구성(프로세스 1개, 스레드 8개)에서는 문제없습니다.
