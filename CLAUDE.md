# 프로젝트 규칙

- 마인크래프트 플러그인(`plugin/`)은 **항상 Paper 26.3** 기준으로 개발한다.
  - `paper-api:26.3.build.<N>-stable`, Java 25 (`options.release = 25`), `plugin.yml`의 `api-version: '26.3'`
  - 다른 버전은 사용자가 그 버전을 직접 지정해서 요청할 때만 사용한다.
