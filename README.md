# 블루프린트 — 건물 템플릿 웹사이트 + 마인크래프트 자동 건축 플러그인

웹사이트에서 건물 템플릿을 둘러보고 **내 보관함**에 담아두면, 마인크래프트 서버에서 `/tb build 1` 한 줄로 자동 건축됩니다.

```
[웹사이트 (Flask + SQLite)]  ←── HTTP + API 키 ──→  [Paper 플러그인 (BlueprintBuilder)]
  템플릿 목록 · 회원가입/로그인                         /tb link · list · build · undo · save
  보관함 · 계정 연동 코드 발급
```

## 구성

| 폴더 | 내용 |
|------|------|
| `web/` | 웹사이트. Python 3.12 + Flask, DB는 `web/instance/app.db` (SQLite) |
| `plugin/` | **Paper 26.3** 플러그인 (Java 25, Gradle) |

## 1. 웹사이트 실행

```bash
cd web
py -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python app.py
```

- http://127.0.0.1:5000 접속. 처음 실행하면 기본 템플릿 5개가 들어갑니다.
- 실행 시 콘솔에 **플러그인 API 키**가 출력되고 `web/instance/plugin_api_key.txt` 에 저장됩니다.
- 외부에서 접속하게 하려면 `HOST=0.0.0.0` 환경변수를 주고, 실제 운영 시에는 HTTPS 리버스 프록시(nginx 등) 뒤에 두세요.
- 환경변수: `HOST`, `PORT`, `SECRET_KEY`, `PLUGIN_API_KEY`, `DB_PATH`
- 테스트: `cd web && .venv/Scripts/python -m unittest test_app`

## 2. 플러그인 빌드 & 설치

```bash
cd plugin
./gradlew build
```

1. `plugin/build/libs/BlueprintBuilder-1.0.0.jar` 를 서버 `plugins/` 폴더에 넣고 서버를 한 번 켭니다.
2. `plugins/BlueprintBuilder/config.yml` 에서
   - `api-url`: 웹사이트 주소 (예: `http://127.0.0.1:5000`)
   - `api-key`: 웹사이트의 `instance/plugin_api_key.txt` 값
3. `/tb reload` (OP) 또는 서버 재시작.

## 3. 사용 흐름

1. 웹사이트 회원가입 → 템플릿 상세에서 **보관함에 담기**
2. **내 보관함 → 연동 코드 발급** → 인게임에서 `/tb link ABC123` (코드는 10분 유효, 1회용)
   - 웹 페이지가 자동으로 "연동됨"으로 바뀝니다.
3. 인게임 `/tb list` → 번호 확인 (목록을 클릭하면 명령어가 입력됨)
4. 원하는 방향을 바라보고 `/tb build 1` → 플레이어 앞 2칸부터 정면이 플레이어를 향하게 자동 건축
5. 마음에 안 들면 `/tb undo` (최근 5번까지), 짓는 도중 중단은 `/tb cancel`

### 인게임 명령어

| 명령어 | 설명 |
|--------|------|
| `/tb link <코드>` | 웹 계정과 연동 |
| `/tb status` / `/tb unlink` | 연동 확인 / 해제 |
| `/tb list` | 내 보관함 목록 |
| `/tb build <번호>` | 바라보는 방향으로 건축 |
| `/tb cancel` / `/tb undo` | 건축 중단 / 되돌리기 |
| `/tb pos1` / `/tb pos2` | 바라보는 블록(없으면 발 위치)을 영역 꼭짓점으로 지정 |
| `/tb save <이름>` | 영역을 템플릿으로 업로드 → 자동으로 내 보관함에 추가. 저장할 때 **바라보는 쪽을 향한 면이 정면**이 됨 |
| `/tb reload` | 설정 리로드 (OP) |

권한: `blueprint.use`, `blueprint.save` (기본 모두), `blueprint.admin` (OP)

## 템플릿 형식

```json
{
  "size": [9, 8, 7],
  "palette": ["minecraft:oak_planks", "minecraft:oak_door[facing=north,half=lower,hinge=left,open=false]"],
  "blocks": [[0, 0, 0, 0], [4, 1, 0, 1]]
}
```

- `blocks` 의 각 항목은 `[x, y, z, 팔레트번호]`, 공기는 생략
- 블록 문자열은 `Bukkit.createBlockData` 형식 (블록 상태 포함)
- **정면(입구)은 z = 0 쪽, 북쪽(-z)을 향하도록** 만듭니다. 플러그인이 플레이어 방향에 맞게 회전합니다.
- 상자 내용물·표지판 글씨 같은 블록 엔티티 데이터는 저장하지 않습니다.

## 플러그인 API (웹사이트 쪽)

모든 요청에 `Authorization: Bearer <플러그인 API 키>` 필요.

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/plugin/link` | `{code, uuid, name}` → 계정 연동 |
| GET | `/api/plugin/players/{uuid}` | 연동된 웹 계정 확인 |
| POST | `/api/plugin/players/{uuid}/unlink` | 연동 해제 |
| GET | `/api/plugin/players/{uuid}/library` | 보관함 목록 |
| GET | `/api/plugin/players/{uuid}/templates/{id}` | 템플릿 데이터 (보관함에 있는 것만) |
| POST | `/api/plugin/players/{uuid}/templates` | 인게임 영역 업로드 |
