# Taste Profile — 블루프린트 템플릿 프로젝트

근거: 참고 이미지 1장(중세 마을 주택 모음, Pinterest — 남의 작품이므로 **복제 금지, 문법만 추출**).
단일 레퍼런스라 모든 항목은 `low` 신뢰도. 피드백이 쌓이면 갱신한다.

## 원본 관찰 (Raw observations)

- 한 이미지에 10채 가까운 집. 공통점이 강해서 "하나의 마을 언어"로 읽힌다.
- 1층은 회청색·회색 돌(조약돌/돌벽돌 섞임), 위층은 주황빛 나무 골조 + 흰 회벽.
- 지붕: 가파르고 회청색 슬레이트 계열. 박공이 정면을 향한 집이 많고, 교차 박공·지붕창(도머)·높이가 다른 지붕이 겹친다.
- 굴뚝: 붉은 벽돌/테라코타, 지붕보다 높이 솟아 강조점 역할.
- 매스: 본채 + 낮은 날개/덧붙인 처마 + 돌출창. 거의 모두 비대칭.
- 위층이 앞으로 튀어나오고(jetty) 까치발로 받친다. 외부 계단·발코니가 붙은 집도 있다.
- 꽃 화단, 덩굴, 이끼, 랜턴, 차양 같은 생활감 디테일이 촘촘하다.

## 추론한 취향 (Inferred preferences)

```yaml
taste_profile:
  massing:
    complexity: medium-high            # low — 본채 + 1~2 보조 매스 + 돌출부
    dominant_mass: clear               # low — 본채가 항상 가장 크고 높다
    secondary_mass_frequency: high     # low
  silhouette:
    roofline_variation: high           # low — 지붕 높이·방향이 서로 다름
    verticality: moderate              # low — 가파른 지붕 + 굴뚝이 세로 강조
  symmetry:
    preference: asymmetric-but-ordered # low — 각 매스 안은 정돈, 전체 배치는 비대칭
  facade:
    depth: high                        # low — jetty, 돌출창, 덧창, 화단으로 깊이
    flatness_tolerance: low            # low
  roof_language:
    pitch: steep (1:1 이상)            # low
    layering: high                     # low
    overhang: 1 block                  # low
    preferred_forms: [front-facing gable, cross gable, dormer, lean-to]
  structural_expression:
    beams: exposed timber frame        # low — 기둥·들보·가새가 보임
    foundations: stone plinth          # low
  palette:
    material_count: 5~6 core           # low — 돌 / 회벽 / 주황 나무 / 회청 지붕 / 벽돌 + 초록
    contrast: high (warm wood vs cool roof)
    accent_usage: chimney, flowers, lanterns
  atmosphere:
    fantasy: low-medium (storybook)    # low
    weathering: light (moss, mixed stone)
    warmth: warm
```

## 맥락 메모

- "중세"는 이 레퍼런스 맥락의 스타일이지 프로젝트 기본값이 아니다.
- 생활감 디테일은 주거/상업 건물에 한정한 Contextual 취향으로 본다.
