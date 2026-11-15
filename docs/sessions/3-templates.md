# 세션 3: 건물 템플릿 제작

## 세션 시작할 때 붙여 넣을 정보

```
이 세션은 건물 템플릿(web/ 의 village_*.py, seed*.py, qa.py, tools/, design/)만 다룬다.
웹사이트 화면·API(app.py, static/)와 플러그인(plugin/)은 다른 세션 담당이라 고치지 않는다.
작업 목록: docs/sessions/3-templates.md
작업 순서·도구 사용법: design/template-workflow.md (먼저 읽기)

규칙
- 사용자에게 보이는 글은 모두 한국어로 쓴다(진행 문구, 요약, 버튼, 이미지 설명 포함).
- 블록은 data/blocks-26.3.json(26.3 레지스트리)에 있는 것만. 대체 블록을 쓰기 전에 먼저 조회한다.
  26.x 변형: 콘크리트·양털 반블록/계단(16색), 색 사암, cinnabar·sulfur, poplar·petrified_oak, *_shelf,
  copper_chest, iron_chain(chain 없음)
- 목표 품질 = "현실에 있는 건물을 마크 블록으로 지은 것" (1블록=1m).
  층고 실내 4칸, 벽 두께 1, 위아래 층 창 정렬, 모든 방은 문·계단으로 연결, 가구는 실제 쓰임대로.
- 건물만. 주변 조경은 넣지 않는다. 실내는 반드시 넣는다.
- 레퍼런스는 핀터레스트 이미지로만(사용자 크롬 로그인됨, 새 탭에서 작업 후 닫기). 건축 파일은 받지 않는다.
- Codex 는 읽기 전용 리뷰어: codex exec -s read-only -i 외관.png -i 단면.png -o 결과.md "프롬프트" < /dev/null
  (< /dev/null 없으면 입력 대기로 멈춘다). 지적은 검토해 타당한 것만 반영, 반영/기각 이유를 사용자에게 요약. 왕복 최대 3회.
- 커밋·푸시는 사용자가 요청할 때만 한다.

점검 (cd web)
- .venv/Scripts/python tools/runqa.py 결과.txt village_real:family_house   → check + strict_check
  strict_check: 외피 구멍(문 닫고 바깥 공기가 실내 가구에 닿음), 걸어서 못 감(계단 1칸·머리 위 2칸 규칙),
  떠 있는 블록. 콘솔은 cp949라 결과는 파일로 저장 후 Read 로 읽는다.
- 외관: tools/sheet.py 외관.png 모듈:함수[@회전] ...
- 단면: tools/cutaway.py 단면.png 모듈:함수=잘라낼y ...
- 테스트: .venv/Scripts/python -m unittest test_app
  test_real_templates_strict 는 village_real.real_templates() 전부 strict 0건을 요구한다.

기준 예시: web/village_real.py family_house() "모던 2층 단독주택" (strict 0건)
```

## 현재 상태 (`strict_check` 건수, 0이 목표)

| 템플릿 | 파일 | 건수 |
|---|---|---|
| 모던 2층 단독주택 | village_real | **0** (기준 예시) |
| ㄱ자 한옥 | village_real | **0** |
| 중세 여관 | village_real | **0** |
| 모던 화이트 빌라 | village_east | 0 |
| 지중해 빌라 | village_world | 0 |
| 해안 등대 | village_world | 0 |
| 창백한 정원 예배당 | village_craft | 1 |
| 갈림길 모퉁이 주택 | seed_townhouse | 4 |
| 오층 목탑 | village_east | 4 |
| 구리 시계탑 | village_craft | 5 |
| 구리 증기 공방 | village_craft | 6 |
| 마녀의 늪 오두막 | village_craft | 8 |
| 사막 교역소 | village_world | 9 |
| 네덜란드식 풍차 | village_world | 10 |
| 바이킹 롱하우스 | village_world | 12 |
| 벚꽃 찻집 | village_east | 14 |
| 모퉁이 카페 | village_east | 17 |
| 드워프 대장간 | village_craft | 26 |
| 엘프 나무 집 | village_world | 27 |

- "모던 2층 단독주택"과 `strict_check`, 테스트는 아직 커밋하지 않았어요.
- 게임에서 실제로 지어 본 템플릿은 아직 없어요.

## 할 일

- [ ] 사용자가 게임에서 "모던 2층 단독주택"을 지어 보고 준 피드백을 반영해요.
- [ ] 기존 16종을 현실형 기준으로 다시 만들어요. 건수가 많은 순서로 하거나, 사용자가 고른 것부터 해요.
  - [ ] 다시 만든 템플릿은 `real_templates()`로 옮겨서 strict 테스트 대상에 넣어요.
  - [ ] 모던 화이트 빌라의 `smooth_quartz_slab`은 콘크리트 반블록으로 바꿔요(레지스트리 조회 후).
- [ ] 새 현실형 템플릿을 추가해요. 템플릿마다 핀터레스트 레퍼런스를 보고 `design/references-2026.md`에 특징을 기록해요.
  - 후보: 한옥, 상가주택, 카페 겸 주택, 2층 오피스, 전원주택, 북유럽 주택, 소형 아파트 동
- [ ] 점검기가 놓치는 부분은 눈으로 확인해요.
  - 문 열림 공간, 가구 앞 여유, 욕실·부엌 기능, 지붕 처마
  - 이런 지적이 반복되면 `qa.py`에 규칙으로 추가해요.
- [ ] 템플릿 개수가 바뀌면 `test_app.py`의 `test_builtin_templates` 숫자를 갱신해요.
