# 플러그인 작업 지시: 서버 이름과 서버별 연동

웹사이트는 이미 바뀌었어요(커밋은 `docs/sessions/2-website.md` 참고). 이 문서대로 **플러그인(`plugin/`)만** 고쳐 주세요.

## 세션 시작할 때 붙여 넣을 정보

```
이 세션은 Paper 플러그인(plugin/)만 다룬다. 웹사이트(web/)는 고치지 않는다.
작업 지시: docs/sessions/1-plugin-server-links.md (기존 작업 목록: docs/sessions/1-plugin.md)

규칙
- 사용자에게 보이는 글은 모두 한국어로 쓴다.
- Paper 26.3 기준: paper-api 26.3.build.<N>-stable, Java 25(options.release=25), plugin.yml api-version '26.3'.
- 플러그인을 다시 빌드하면 plugin/build.gradle.kts 의 version 을 올린다(지금 1.0.0 → 1.1.0).
- 커밋·푸시는 사용자가 요청할 때만 한다.
```

## 무엇이 바뀌었나 (웹사이트 쪽, 이미 끝남)

- 서버 주인은 웹사이트(내 보관함 → 내 마인크래프트 서버)에서 **서버를 여러 개 등록**할 수 있고, **서버마다 키가 따로** 나와요(`bp_...`).
- 플레이어의 인게임 연동은 **서버마다 따로**예요. 새 서버에서 `/tb link 코드`를 할 때마다 웹사이트의 "연동된 서버" 목록에 한 줄씩 추가돼요.
- 키로 조회·업로드·해제할 수 있는 플레이어는 **그 서버에서 연동한 플레이어뿐**이에요.
- 서버 이름은 플러그인이 알려 줘요. 비어 있으면 웹사이트가 목록 순서대로 `Minecraft Server (1)`, `(2)` … 로 보여 줘요.
- 운영자 키(`web/instance/plugin_api_key.txt`)도 계속 쓸 수 있어요. 그 키는 "운영자 서버" 한 곳으로 취급돼요.
- 요청 모양(`/api/plugin/link`, `/players/...`)은 그대로라서 **지금 플러그인도 계속 동작**해요. 아래는 서버 이름 기능을 붙이는 작업이에요.

## 할 일

### 1. config.yml 에 서버 이름 칸 추가

```yaml
# 웹사이트에서 이 서버에 보여 줄 이름. 비워 두면 "Minecraft Server (번호)"로 보여요. (32자까지)
server-name: ""
```

- `api-key` 설명도 바꿔요: "웹사이트 → 내 보관함 → 내 마인크래프트 서버 → 서버 추가에서 받은 키(bp_로 시작)".
- 기존 서버의 config 에 `server-name` 이 없으면 빈 값으로 취급해요(`getConfig().getString("server-name", "")`). `saveDefaultConfig()` 는 기존 파일을 덮어쓰지 않으니, 필요하면 `getConfig().options().copyDefaults(true); saveConfig();` 로 새 칸을 채워 주세요.

### 2. 모든 API 요청에 서버 이름 헤더 붙이기

- `ApiClient` 가 보내는 **모든 요청**에 헤더를 붙여요:
  `X-Server-Name: <server-name 을 UTF-8 퍼센트 인코딩한 값>`
  - 한글이 들어가므로 반드시 인코딩: `URLEncoder.encode(name, StandardCharsets.UTF_8).replace("+", "%20")`
  - 비어 있어도 **빈 헤더를 보내요**(`X-Server-Name: `). 그래야 이름을 지웠을 때 웹사이트도 번호 이름으로 돌아가요.
- 웹사이트는 이 헤더를 받는 즉시 이름을 바꿔요. 그래서 이름을 바꾸고 `/tb reload` 하면 다음 요청부터 바로 반영돼요.

### 3. 켜질 때·`/tb reload` 때 이름 알리기

- 새 엔드포인트: `POST /api/plugin/server` 본문 `{"name": "<server-name>"}` (Bearer 키 필요)
  - 응답: `{"id": 3, "name": "모닥불 서버"}` (이름이 비면 `"name": null`)
- `onEnable()` 끝과 `/tb reload` 처리 끝에서 비동기로 한 번 호출해요. 플레이어가 아무 명령도 안 쳐도 웹사이트에 이름이 바로 보이게 하려는 거예요.
- 실패하면(401 등) 콘솔에 한국어로 이유만 남기고 플러그인은 계속 켜져 있어요.

### 4. `/tb link` 결과 문구

- `POST /api/plugin/link` 응답에 `serverName` 이 추가됐어요: `{"username": "Modagi12", "serverName": "모닥불 서버"}`
- 성공 문구 예: `웹 계정 Modagi12 과(와) 연동했어요. (이 서버: 모닥불 서버)`
- `/tb status` 도 서버 이름을 함께 보여 주면 좋아요(`/api/plugin/server` 응답의 name, 없으면 "이름 없음").

### 5. `/tb unlink` 문구

- 이제 연동 해제는 **이 서버에서만** 풀려요. 문구: `이 서버와의 연동을 해제했어요. 다른 서버의 연동은 그대로예요.`

### 6. 문서

- `plugin/README.md`(없으면 새로)에 서버 주인용 설정 순서를 적어요:
  1. 웹사이트 로그인 → 내 보관함 → 내 마인크래프트 서버 → **서버 추가**
  2. 화면에 나온 `api-url`, `api-key`, `server-name` 을 `plugins/BlueprintBuilder/config.yml` 에 붙여 넣기
  3. `/tb reload`
- `docs/sessions/1-plugin.md` 의 "웹사이트 쪽 API" 목록에 `POST /api/plugin/server`, `X-Server-Name` 헤더, link 응답의 `serverName` 을 추가해요.

## 확인할 것

- [ ] `server-name: "모닥불 서버"` 로 켜면 웹사이트 "내 마인크래프트 서버" 목록에 바로 그 이름이 보여요.
- [ ] 이름을 지우고 `/tb reload` → `Minecraft Server (번호)` 로 돌아가요.
- [ ] 키가 다른 서버 두 곳에서 각각 `/tb link` → 웹사이트 "연동된 서버" 목록이 2줄이 돼요.
- [ ] A 서버에서만 연동한 플레이어는 B 서버에서 `/tb list` 하면 "연동되지 않은 플레이어" 안내가 나와요.
- [ ] 한글·공백·이모지가 든 서버 이름도 깨지지 않아요(32자 넘으면 웹사이트가 잘라요).
