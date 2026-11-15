# 세션 1: 마인크래프트 플러그인

## 세션 시작할 때 붙여 넣을 정보

```
이 세션은 Paper 플러그인(plugin/)만 다룬다. 웹사이트(web/)·템플릿은 다른 세션 담당이라 고치지 않는다.
작업 목록: docs/sessions/1-plugin.md

규칙
- 사용자에게 보이는 글은 모두 한국어로 쓴다(진행 문구, 요약, 버튼 포함).
- 항상 Paper 26.3 기준: paper-api 26.3.build.249-stable, Java 25(options.release=25), plugin.yml api-version '26.3'.
  다른 버전은 사용자가 직접 지정할 때만 쓴다.
- 블록은 data/blocks-26.3.json(26.3 레지스트리)에 있는 것만 다룬다.
- 파일(서버 jar 등)을 받기 전에 파일명·출처·크기를 알리고 허락을 받는다.
- 커밋·푸시는 사용자가 요청할 때만 한다.

구조 (plugin/src/main/java/dev/blueprint/builder/)
- BlueprintPlugin: 설정 로드(api-url, api-key, 환경변수 BLUEPRINT_API_KEY), 명령어 등록
- BlueprintCommand: /tb link|unlink|status|list|build|cancel|undo|pos1|pos2|save|reload|help
  onCommand → handle(), 예외는 채팅·콘솔에 한국어로 표시
- ApiClient: 웹사이트 /api/plugin/* 비동기 호출, Bearer API 키, configProblem()으로 설정 검사
- BuildManager: 틱당 blocks-per-tick 개씩 설치, max-blocks, undo
- Orientation: 템플릿 정면 z=0이 북쪽, 플레이어가 남쪽을 보면 회전 없음
- Capture: /tb pos1·pos2 영역을 템플릿 JSON으로 만들어 업로드
- config.yml: api-url, api-key, build.blocks-per-tick/max-blocks/distance/effects, save.max-size

웹사이트 쪽 API (웹 세션이 바꾸면 여기도 맞춘다)
- POST /api/plugin/link {code, uuid, name}
- GET  /api/plugin/players/<uuid>, POST .../unlink
- GET  /api/plugin/players/<uuid>/library, GET .../templates/<id>
- POST /api/plugin/players/<uuid>/templates {name, category, description, data}
- 템플릿 data: {"size":[x,y,z], "palette":["minecraft:블록[속성=값]"...], "blocks":[[x,y,z,팔레트번호]...]}

빌드: cd plugin; .\gradlew.bat build → plugin/build/libs/BlueprintBuilder-1.0.0.jar
```

## 현재 상태

- 빌드됨. 실제 Paper 26.3 서버에서는 연동 한 번만 시도했어요. 그때 config.yml의 api-key가 기본 한국어 문구 그대로라 "예상치 못한 오류"가 났어요.
- 이 오류는 고쳤어요. 설정이 틀리면 이제 한국어로 이유를 알려 줘요. 하지만 아직 커밋하지 않았어요.

## 할 일

- [ ] 지난 수정(ApiClient, BlueprintCommand, BlueprintPlugin)을 커밋해요. 사용자 확인을 받은 뒤에 해요.
- [ ] 로컬에서 Paper 26.3 테스트 서버를 띄워요. 서버 jar는 받기 전에 허락을 받아요.
- [ ] 게임 안에서 전체 흐름을 확인해요.
  - [ ] `/tb link <코드>`: 웹에서 받은 코드로 연동돼요.
  - [ ] `/tb status`, `/tb list`: 보관함 목록이 나와요.
  - [ ] `/tb build`: 네 방향(플레이어가 보는 방향)으로 회전이 맞아요.
  - [ ] 문·침대·계단·트랩도어·덧창의 방향이 회전 후에도 맞아요.
  - [ ] 매달린 등, 벽걸이 같은 붙는 블록이 떨어지지 않아요. 설치 순서와 물리 업데이트를 확인해요.
  - [ ] `/tb cancel`, `/tb undo`가 동작해요.
  - [ ] `/tb pos1`, `/tb pos2`, `/tb save`: 업로드한 뒤 웹 보관함에 보여요.
- [ ] 설치할 때 블록 물리를 끄고(`setBlockData(data, false)`), 붙는 블록은 마지막에 놓아요.
- [ ] 큰 건물에서 서버 렉을 측정하고 blocks-per-tick 기본값을 정해요.
- [ ] `api-url`이 https 주소일 때도 동작하는지 확인해요. 웹 세션의 배포 결과에 맞춰요.
- [ ] 서버 관리자용 설치 설명서를 써요. 위치: `plugin/README.md`, 한국어. 내용: config 설정과 API 키 넣는 방법.
