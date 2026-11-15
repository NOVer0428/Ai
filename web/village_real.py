"""현실형 템플릿: 실제 건물을 1블록=1m 비율로 옮긴 집.

규칙
  층고: 1층 바닥 y0, 실내 y1~4, 2층 바닥 y5, 실내 y6~9, 천장 y10 (실내 높이 4칸)
  벽 두께 1칸, 창은 위아래 층 같은 열에 맞춘다.
  모든 방은 문으로 이어지고, 계단은 한 칸씩 오르며 머리 위 2칸을 비운다.
  qa.check + qa.strict_check 0건 (외피 구멍·걸어서 못 감·떠 있는 블록 없음).
"""
from seed_detail import Arch
from seed_kit import S

W = S("white_concrete")
PLINTH = S("polished_deepslate")
OAK = S("oak_planks")
CLAD = S("stripped_spruce_log", axis="y")
ROOF = "deepslate_tile"
SILL = S("polished_deepslate_slab", type="top")


def _pane(k, x, y, z, along, glass="glass_pane"):
    k.pane(x, y, z, along, glass)


def _win(k, x0, x1, y0, y1, z=None, x=None, glass="glass_pane", sill=False, out=None):
    """벽면 창. z 를 주면 남북 벽(x0..x1), x 를 주면 동서 벽(x0..x1 을 z 범위로)."""
    for a in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            if z is not None:
                _pane(k, a, y, z, "x", glass)
            else:
                _pane(k, x, y, a, "z", glass)
        if sill:
            if z is not None:
                k.set(a, y0 - 1, z + (-1 if out == "north" else 1), SILL)
            else:
                k.set(x + (-1 if out == "west" else 1), y0 - 1, a, SILL)


def family_house():
    k = Arch()

    # ---------------------------------------------------------------- 바닥·벽
    k.floor(0, 0, 27, 10, 0, PLINTH)                     # 기초 (둘레가 보이는 띠)
    k.walls(0, 0, 20, 10, 1, 10, W)                      # 본채 2층
    k.walls(20, 0, 27, 10, 1, 5, W)                      # 차고 1층
    k.floor(1, 1, 19, 9, 0, OAK)                         # 1층 마루
    k.floor(14, 5, 19, 9, 0, S("smooth_stone"))          # 부엌 바닥 타일
    k.floor(21, 1, 26, 9, 0, S("smooth_stone"))          # 차고 바닥
    k.floor(1, 1, 19, 9, 5, OAK)                         # 2층 바닥 = 1층 천장
    k.floor(1, 1, 19, 9, 10, W)                          # 2층 천장
    k.floor(21, 1, 26, 9, 5, S("spruce_planks"))         # 차고 지붕 = 테라스 데크

    # 현관 칸: 나무 세로 마감 (x9..12, 정면 전체 높이)
    k.fill(9, 1, 0, 12, 10, 0, CLAD)

    # 1층 칸막이 (거실 | 홀 | 부엌), 넓은 개구부
    k.fill(8, 1, 1, 8, 4, 9, W)
    k.fill(13, 1, 1, 13, 4, 9, W)
    k.clear(8, 1, 2, 8, 3, 4)
    k.clear(13, 1, 2, 13, 3, 4)
    # 2층 칸막이 (안방·욕실 | 홀 | 아이방·서재)
    k.fill(8, 6, 1, 8, 9, 9, W)
    k.fill(13, 6, 1, 13, 9, 9, W)
    k.fill(1, 6, 6, 7, 9, 6, W)
    k.fill(14, 6, 6, 19, 9, 6, W)

    # ---------------------------------------------------------------- 계단 (홀 동쪽, 남쪽으로 오름)
    for i in range(4):  # 디딤 y1..4, z5..8
        z = 5 + i
        k.set(12, 1 + i, z, S("spruce_stairs", facing="south"))
        for y in range(1, 1 + i):
            k.set(12, y, z, S("spruce_planks"))          # 계단 밑 수납
        k.fill(11, 1, z, 11, i, z, S("spruce_planks")) if i else None  # 홀 쪽 옆판
        k.set(11, 1 + i, z, S("spruce_fence"))           # 손잡이 난간
    k.fill(12, 1, 9, 12, 4, 9, S("spruce_planks"))       # 계단참 아래 벽장
    k.clear(12, 5, 6, 12, 5, 8)                          # 머리 위 개구부
    for z in (6, 7, 8):                                  # 2층 난간 (유리)
        k.set(11, 6, z, S("glass_pane", north=True, south=True))
    k.set(12, 6, 5, S("glass_pane", east=True, west=True))

    # ---------------------------------------------------------------- 창 (위아래 층 같은 열)
    # 정면 (z=0, 북)
    for x0, x1 in ((2, 3), (5, 6)):
        _win(k, x0, x1, 1, 3, z=0)                       # 거실 큰 창
        _win(k, x0, x1, 7, 8, z=0)  # 안방
    _win(k, 15, 17, 1, 3, z=0)                           # 식당
    _win(k, 15, 17, 7, 8, z=0)  # 아이방
    _win(k, 10, 11, 7, 8, z=0)  # 2층 홀
    # 현관: 문 + 옆 유리 + 위 채광창
    k.door(10, 1, 0, "spruce", facing="north")
    _pane(k, 10, 3, 0, "x")
    _win(k, 11, 11, 1, 3, z=0)
    # 서쪽 (x=0)
    _win(k, 2, 4, 1, 3, x=0)
    _win(k, 6, 8, 1, 3, x=0)
    _win(k, 2, 4, 7, 8, x=0)
    # 뒤쪽 (z=10, 남)
    _win(k, 2, 6, 1, 3, z=10)                            # 거실 정원 창
    _win(k, 15, 17, 2, 3, z=10)                          # 개수대 위 창
    _win(k, 3, 5, 7, 8, z=10, glass="white_stained_glass_pane")  # 욕실 불투명
    _win(k, 15, 17, 7, 8, z=10)  # 서재
    _win(k, 10, 10, 7, 8, z=10)  # 2층 홀
    k.door(10, 1, 10, "spruce", facing="south")          # 뒷문 → 정원
    # 동쪽 2층 (x=20): 테라스 문, 서재 창
    k.door(20, 6, 3, "spruce", facing="east")
    _win(k, 8, 8, 7, 8, x=20)

    # ---------------------------------------------------------------- 실내 문
    k.door(8, 6, 3, "spruce", facing="west")            # 안방
    k.door(8, 6, 8, "spruce", facing="west")            # 욕실
    k.door(13, 6, 3, "spruce", facing="east")           # 아이방
    k.door(13, 6, 8, "spruce", facing="east")           # 서재
    k.door(20, 1, 5, "spruce", facing="east")           # 부엌 → 차고

    # ---------------------------------------------------------------- 현관 캐노피·디딤
    for x in range(9, 13):
        for z in (-1, -2):
            k.set(x, 4, z, S("polished_deepslate_slab", type="top"))
            k.set(x, 0, z, S("polished_deepslate_slab"))
    k.hang(10, 3, -1)

    # ---------------------------------------------------------------- 1층 거실 (x1..7)
    for z in (6, 7, 8):
        k.set(3, 1, z, S("gray_wool_stairs", facing="west"))   # 소파
        k.set(7, 1, z, S("barrel", facing="west"))             # TV 장
        k.set(7, 2, z, S("black_concrete"))                    # TV
    k.set(3, 1, 5, S("gray_wool_slab"))                        # 팔걸이
    k.set(3, 1, 9, S("gray_wool_slab"))
    k.set(5, 1, 7, S("spruce_slab"))                           # 낮은 탁자
    k.rug(4, 6, 6, 8, 1, "light_gray")
    k.set(1, 1, 1, S("potted_fern"))
    k.set(1, 1, 9, S("potted_fern"))
    for x in (5, 6, 7):                                        # 홀 쪽 책장 벽
        k.set(x, 1, 1, S("bookshelf"))
        k.set(x, 2, 1, S("spruce_shelf", facing="south"))
    k.set(2, 1, 3, S("gray_wool_stairs", facing="north"))      # 창가 안락의자 둘
    k.set(2, 1, 4, S("spruce_slab"))
    k.set(2, 1, 5, S("gray_wool_stairs", facing="south"))
    k.set(2, 2, 4, S("potted_fern"))
    k.set(5, 4, 7, S("iron_chain", axis="y"))
    k.hang(5, 3, 7)

    # ---------------------------------------------------------------- 1층 홀 (x9..12)
    k.set(9, 1, 1, S("barrel", facing="east"))                 # 신발장
    k.set(9, 2, 1, S("spruce_shelf", facing="east"))
    k.set(11, 1, 9, S("potted_bamboo"))
    k.hang(10, 4, 3)
    k.hang(10, 4, 7)

    # ---------------------------------------------------------------- 1층 부엌·식당 (x14..19)
    for x, blk in ((14, S("barrel", facing="north")), (15, S("smoker", facing="north")),
                   (16, S("water_cauldron", level=3)), (17, S("barrel", facing="north")),
                   (18, S("barrel", facing="north"))):
        k.set(x, 1, 9, blk)
        k.set(x, 3, 9, S("spruce_shelf", facing="north")) if x in (14, 18) else None
    k.set(19, 1, 9, S("iron_block"))                           # 냉장고
    k.set(19, 2, 9, S("iron_block"))
    k.set(19, 1, 8, S("barrel", facing="west"))
    k.set(19, 1, 7, S("crafting_table"))
    k.set(19, 3, 7, S("spruce_shelf", facing="west"))
    k.set(19, 3, 8, S("spruce_shelf", facing="west"))
    for x in (15, 16, 17):                                     # 식탁 3x2 + 의자 6 (벽에서 한 칸 띄움)
        for z in (3, 4):
            k.set(x, 1, z, S("spruce_slab", type="top"))
        k.chair(x, 1, 2, "spruce", "north")
        k.chair(x, 1, 5, "spruce", "south")
    for z in (3, 4):
        k.set(16, 4, z, S("iron_chain", axis="y"))
        k.hang(16, 3, z)
    k.hang(17, 4, 7)

    # ---------------------------------------------------------------- 차고 (x21..26)
    for x in range(22, 26):                                    # 접이식 차고 문 (트랩도어)
        for y in (1, 2, 3):
            k.set(x, y, 0, S("dark_oak_trapdoor", facing="south", open=True, half="top"))
    _win(k, 4, 5, 2, 3, x=27)
    k.set(22, 1, 9, S("crafting_table"))
    k.set(23, 1, 9, S("smithing_table"))
    k.set(24, 1, 9, S("chest", facing="north"))
    k.set(25, 1, 9, S("chest", facing="north"))
    k.set(26, 1, 9, S("barrel", facing="north"))
    k.set(21, 1, 9, S("grindstone", face="floor", facing="east"))
    for x in range(22, 27):
        k.set(x, 3, 9, S("spruce_shelf", facing="north"))
    k.hang(23, 4, 3)
    k.hang(23, 4, 7)

    # ---------------------------------------------------------------- 테라스 (차고 지붕)
    for x in range(21, 28):
        for z in (0, 10):
            k.set(x, 6, z, S("glass_pane", east=True, west=True))
    for z in range(1, 10):
        k.set(27, 6, z, S("glass_pane", north=True, south=True))
    k.set(27, 6, 0, S("glass_pane", west=True, south=True))
    k.set(27, 6, 10, S("glass_pane", west=True, north=True))
    k.table(24, 6, 5, "spruce")
    k.chair(23, 6, 5, "spruce", "west")
    k.chair(25, 6, 5, "spruce", "east")
    k.set(26, 6, 1, S("potted_azalea_bush"))
    k.set(26, 6, 9, S("potted_azalea_bush"))

    # ---------------------------------------------------------------- 2층 안방 (x1..7, z1..5)
    k.bed(3, 6, 4, "white", "south")
    k.bed(4, 6, 4, "white", "south")
    for x in (2, 5):
        k.set(x, 6, 5, S("barrel", facing="up"))               # 협탁
        k.set(x, 7, 5, S("candle", candles=1, lit=True))
    for z in (4, 5):                                           # 붙박이장
        for y in (6, 7):
            k.set(7, y, z, S("barrel", facing="west"))
    k.rug(2, 1, 6, 3, 6, "light_gray")
    k.set(4, 10, 3, S("sea_lantern"))

    # 욕실 (x1..7, z7..9)
    k.set(1, 6, 8, S("water_cauldron", level=3))               # 욕조
    k.set(1, 6, 9, S("water_cauldron", level=3))
    k.set(3, 6, 9, S("quartz_stairs", facing="south"))         # 변기
    k.set(5, 6, 9, S("water_cauldron", level=2))               # 세면대
    k.set(6, 6, 9, S("smooth_quartz"))
    k.set(6, 7, 9, S("birch_shelf", facing="north"))
    k.rug(2, 7, 7, 8, 6, "light_gray")
    _win(k, 8, 8, 7, 8, x=0, glass="white_stained_glass_pane")
    k.set(4, 10, 8, S("sea_lantern"))

    # 2층 홀
    k.set(9, 6, 1, S("bookshelf"))
    k.chair(9, 6, 2, "spruce", "west")
    k.set(10, 10, 2, S("sea_lantern"))
    k.set(10, 10, 8, S("sea_lantern"))

    # 아이방 (x14..19, z1..5)
    k.bed(17, 6, 4, "light_blue", "south")
    k.set(18, 6, 5, S("barrel", facing="up"))
    k.table(15, 6, 1, "spruce")
    k.chair(15, 6, 2, "spruce", "south")
    for z in (4, 5):
        for y in (6, 7):
            k.set(14, y, z, S("barrel", facing="east"))
    k.rug(15, 2, 18, 3, 6, "light_blue")
    k.set(16, 10, 3, S("sea_lantern"))

    # 서재·손님방 (x14..19, z7..9)
    for x in (14, 15):
        for y in (6, 7):
            k.set(x, y, 9, S("bookshelf"))
    k.set(17, 6, 9, S("spruce_slab", type="top"))              # 책상
    k.set(18, 6, 9, S("spruce_slab", type="top"))
    k.chair(17, 6, 8, "spruce", "north")
    k.set(19, 6, 9, S("lectern", facing="west"))
    k.set(19, 6, 7, S("gray_wool_stairs", facing="east"))      # 안락의자
    k.set(18, 6, 7, S("potted_fern"))
    k.set(16, 10, 8, S("sea_lantern"))

    # ---------------------------------------------------------------- 지붕 (박공, 처마 1칸)
    k.gable(-1, 21, -1, 11, 10, ROOF, ridge="x", gable_fill=W, trim=ROOF)
    for x in range(-1, 22):                                    # 처마 밑 반자
        for z in (-1, 11):
            k.set(x, 9, z, S("spruce_slab", type="top"))
    for (x, y, z), b in list(k.cells.items()):                # 차고 외벽: 세로 나무 마감
        if 1 <= y <= 4 and b == W and ((z in (0, 10) and 21 <= x <= 27) or (x == 27 and 0 <= z <= 10)):
            k.set(x, y, z, CLAD)
    return k.build()


def real_templates():
    return [
        {"name": "모던 2층 단독주택", "category": "주택",
         "description": "1블록=1m 실제 비율로 옮긴 흰 벽·검은 슬레이트 박공지붕 주택. "
                        "나무 마감 현관과 캐노피, 차고 위 유리 난간 테라스. "
                        "1층 거실·현관 홀·부엌 식당·차고, 2층 안방·욕실·아이방·서재. "
                        "층고 4칸, 위아래 층 창 정렬, 모든 방은 문과 계단으로 이어진다.",
         "data": family_house()},
    ]
