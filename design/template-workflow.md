# 템플릿 추가 작업 체크리스트

새 건물 템플릿을 추가하거나 고칠 때 이 순서대로 진행한다.
이 파일과 아래 "핵심 파일"만 읽고 시작하면 된다. 전체 코드를 다시 훑지 않는다.

## 0. 지켜야 할 규칙 (먼저 확인)

- [ ] 사용자에게 보이는 글은 모두 **한국어**로 쓴다.
- [ ] 플러그인은 **Paper 26.3** / Java 25 기준이다.
- [ ] 블록은 `data/blocks-26.3.json`(26.3 레지스트리)에 있는 것만 쓴다. 대체 블록을 쓰기 전에 먼저 조회한다.
  - 26.x 변형: 콘크리트·양털 반블록/계단(16색), 색 사암, cinnabar·sulfur 계열, poplar·petrified_oak 목재, `*_shelf`, copper_chest, `iron_chain`(`chain` 없음)
- [ ] 건물만 만들고 주변 연출(조경)은 넣지 않는다. 실내는 반드시 넣는다.
- [ ] 레퍼런스는 핀터레스트 **이미지**와 유튜브 **강좌 영상(자막)** 으로 참고한다. 건축 파일은 받지 않는다.
- [ ] 파일을 받기 전에 파일명·출처·크기를 알리고 허락을 받는다.
- [ ] Codex는 읽기 전용으로 쓴다. 코드는 Claude가 고친다. 리뷰→수정 왕복은 최대 3회.

## 1. 레퍼런스 수집

- [ ] 사용자 크롬(로그인됨)에서 **새 탭**을 열어 핀터레스트에서 스타일별 외관과 실내를 검색한다. 끝나면 탭을 닫는다.
- [ ] 관찰한 특징만 `design/references-2026.md`에 짧게 추가한다(덩어리, 지붕, 재료 역할, 실내 구성).
  - 이미 정리된 스타일은 다시 찾지 않는다.
- [ ] 건축 기법(벽 깊이, 지붕, 매스, 실내 순서, 가구 문법)은 `design/build-techniques.md`를 따른다. 강좌 영상 자막에서 정리한 내용이다.

## 2. 설계 (Codex)

- [ ] 건물별 덩어리 배치, 재료 역할, 층별 실내를 Codex에 요청한다.
  ```bash
  codex exec -s read-only -o 결과.md "프롬프트"
  ```
- [ ] 제안은 그대로 따르지 않는다. 레퍼런스 특징과 합쳐 결정한다.

## 3. 구현

- [ ] 함수를 `web/village_*.py` 중 맞는 파일에 추가한다. 반환값은 `{"name", "description", "data"}`이다.
- [ ] `web/seed_village.py` 목록에 등록한다.
- [ ] 도구는 `seed_detail.Arch`(`seed_kit.Kit` 상속)를 쓴다. 새로 만들기 전에 아래 목록을 먼저 확인한다.
  - 벽면 깊이: `recessed_window`, `pilaster`, `cornice`, `arch_window`, `round_window`
  - 지붕: `curved_gable(pitch="concave"|"low")`, `flared_hip`, `eave_ring`, `dome`, `spire`, `gable`, `hip`, `cone`
  - 재료: `Arch.grad`(높이별 그라데이션), `mix`, `full_of(mat)`
  - 가구: `table`, `chair`, `bed`, `rug`, `counter`, `shelf_wall`, `ladder`, `hang`, `stair_run`, `door`, `double_door`
- [ ] 문, 덧창, 침대, 계단의 `facing`은 직접 지정한다. `door` 기본값은 north다.
- [ ] 템플릿 정면은 z=0이고 북쪽을 향한다.

## 4. 점검 (`web/`에서 실행)

- [ ] 구조 점검을 0건으로 만든다. 콘솔은 cp949라 결과를 UTF-8 파일로 저장한 뒤 Read로 읽는다.
  ```bash
  .venv/Scripts/python tools/runqa.py 결과.txt village_east:modern_villa village_world:windmill
  ```
  - 점검 항목: 위·아래·뒤 지지, 문·침대 짝, 유체 누출, 들어갈 수 없는 방
  - 점검 못 하는 것(눈으로 확인): 높이 차이로 못 걷는 계단, 문 방향, 다른 블록에 덮여 사라진 가구
- [ ] 외관을 모아서 확인한다. `@1`~`@3`은 회전.
  ```bash
  .venv/Scripts/python tools/sheet.py 외관.png village_east:modern_villa village_world:windmill@1
  ```
- [ ] 실내 단면을 확인한다. `=y`는 이 높이 위를 잘라낸다.
  ```bash
  .venv/Scripts/python tools/cutaway.py 단면.png village_east:modern_villa=4
  ```
- [ ] 단면 이미지와 레퍼런스를 Codex 리뷰에 넘긴다(`codex exec -s read-only -i 외관.png -i 단면.png ...`). 타당한 지적만 반영한다.

## 5. 마무리

- [ ] `web/test_app.py`의 템플릿 개수(`test_builtin_templates`)를 갱신한다.
- [ ] 테스트를 실행한다.
  ```bash
  .venv/Scripts/python -m unittest test_app
  ```
- [ ] 사이트를 띄워 썸네일 200 응답과 한국어 재료 목록을 확인한다. 기본 템플릿은 시작할 때 코드와 동기화된다.
- [ ] 사용자가 요청했을 때만 커밋·푸시한다.

## 핵심 파일

| 파일 | 역할 |
|---|---|
| `web/seed_detail.py` | `Arch` 건축 도구(지붕·창·그라데이션) |
| `web/seed_kit.py` | `Kit` 기본 도구(벽·가구), `mix`, `full_of` |
| `web/village_east.py` / `village_craft.py` / `village_world.py` | 템플릿 함수 |
| `web/seed_village.py`, `web/seed.py` | 템플릿 목록 등록 |
| `web/qa.py` | 구조 점검기 |
| `web/template_format.py` | `state()`, `normalize()`, 레지스트리 검사 |
| `web/tools/sheet.py`, `cutaway.py`, `runqa.py` | 외관 모음, 실내 단면, 점검 결과 저장 |
| `design/references-2026.md` | 스타일별 레퍼런스 특징 |
| `design/build-techniques.md` | 강좌 영상에서 뽑은 건축 기법과 적용 우선순위 |

## 토큰 절약 요령

- 큰 템플릿 파일은 통째로 읽지 않는다. `grep -n "def "`로 함수 위치를 찾은 뒤 그 범위만 읽는다.
- 여러 군데를 고칠 때는 `(찾을 문자열, 바꿀 문자열)` 목록을 패치 스크립트 하나로 적용한다.
- 이미지는 템플릿마다 따로 보지 않는다. `sheet.py`로 한 장에 모아서 본다.
- Codex에는 긴 설명 대신 파일 경로와 좌표를 넘긴다.
