"""현실형 템플릿: 실제 건물을 1블록=1m 비율로 옮긴 집.

규칙
  층고: 1층 바닥 y0, 실내 y1~4, 2층 바닥 y5, 실내 y6~9, 천장 y10 (실내 높이 4칸)
  벽 두께 1칸, 창은 위아래 층 같은 열에 맞춘다.
  모든 방은 문으로 이어지고, 계단은 한 칸씩 오르며 머리 위 2칸을 비운다.
  qa.check + qa.strict_check 0건 (외피 구멍·걸어서 못 감·떠 있는 블록 없음).
"""
from seed_detail import Arch
from seed_kit import S, full_of, mix

W = S("white_concrete")
PLINTH = S("polished_deepslate")
OAK = S("oak_planks")
CLAD = S("stripped_spruce_log", axis="y")
ROOF = "deepslate_tile"
SILL = S("polished_deepslate_slab", type="top")


def _pane(k, x, y, z, along, glass="glass_pane"):
    k.pane(x, y, z, along, glass)


def _win(k, x0, x1, y0, y1, z=None, x=None, glass="glass_pane", sill=False, out=None, frame=False):
    """벽면 창. z 를 주면 남북 벽(x0..x1), x 를 주면 동서 벽(x0..x1 을 z 범위로).
    frame: 바깥 한 칸에 어두운 세로틀. 벽이 1칸이라 안으로 들이지 않고 틀을 밖으로 내어 깊이를 만든다.
    인방은 따로 두지 않는다: 1층 창 위는 층 띠(y5), 2층 창 위는 처마 반자(y9)가 그 역할을 한다."""
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
    if frame:
        d = -1 if out in ("north", "west") else 1
        at = (lambda a, y: (a, y, z + d)) if z is not None else (lambda a, y: (x + d, y, a))
        for y in range(y0, y1 + 1):                       # 세로틀: 벽에 붙은 트랩도어
            for a, side in ((x0 - 1, 0), (x1 + 1, 1)):
                facing = (("west", "east") if z is not None else ("north", "south"))[side]
                k.set(*at(a, y), S("dark_oak_trapdoor", facing=facing, open=True))


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
        _win(k, x0, x1, 1, 3, z=0, out="north", frame=True)   # 거실 큰 창
        _win(k, x0, x1, 7, 8, z=0, out="north", frame=True)   # 안방
    _win(k, 15, 17, 1, 3, z=0, out="north", frame=True)       # 식당
    _win(k, 15, 17, 7, 8, z=0, out="north", frame=True)       # 아이방
    _win(k, 10, 11, 7, 8, z=0)  # 2층 홀
    # 현관: 문 + 옆 유리 + 위 채광창
    k.door(10, 1, 0, "spruce", facing="north")
    _pane(k, 10, 3, 0, "x")
    _win(k, 11, 11, 1, 3, z=0)
    # 서쪽 (x=0)
    _win(k, 2, 4, 1, 3, x=0, out="west", frame=True)
    _win(k, 6, 8, 1, 3, x=0, out="west", frame=True)
    _win(k, 2, 4, 7, 8, x=0, out="west", frame=True)
    # 뒤쪽 (z=10, 남)
    _win(k, 2, 6, 1, 3, z=10, out="south", frame=True)        # 거실 정원 창
    _win(k, 15, 17, 2, 3, z=10, out="south", frame=True)      # 개수대 위 창
    _win(k, 3, 5, 7, 8, z=10, glass="white_stained_glass_pane", out="south", frame=True)  # 욕실 불투명
    _win(k, 15, 17, 7, 8, z=10, out="south", frame=True)      # 서재
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

    # ---------------------------------------------------------------- 벽 깊이: 층 띠 + 현관 기둥
    # 2층 바닥 높이에 어두운 띠를 둘러 층을 나누고, 현관 칸(x9..12)만 띠를 끊어 세로로 강조한다.
    k.cornice(0, 0, 27, 10, 5, "polished_deepslate")
    k.clear(9, 5, -1, 12, 5, -1)
    for x in (8, 13):                                        # 현관 양옆 기둥 (깊이 층: 기둥 > 나무벽 > 문)
        k.pilaster(x, 0, "north", 1, 8, PLINTH)

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
    for z in (2, 4, 6, 8):                                     # 천장 들보 (짧은 변 방향)
        for x in range(1, 8):
            k.set(x, 4, z, S("spruce_trapdoor", facing="north", half="top"))

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
    for z in (2, 5, 8):                                        # 천장 들보 (거실과 같은 결)
        for x in range(14, 20):
            k.set(x, 4, z, S("spruce_trapdoor", facing="north", half="top"))
    k.set(17, 2, 9, S("light_weighted_pressure_plate"))        # 조리대 위 도마

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
    k.set(3, 6, 3, S("spruce_slab"))                           # 침대 발치 벤치
    k.set(4, 6, 3, S("spruce_slab"))
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


# ==================================================================== 한옥 (ㄱ자 안채)
# 근거: design/references-2026.md "한옥" 절. 1칸 = 기둥 사이 4블록, 정면(북) 마당 쪽이 밝고 뒤가 닫힌다.
TILE = "deepslate_tile"
POST = S("stripped_spruce_log", axis="y")
PLASTER = S("calcite")
BOARD = S("spruce_planks")
MARU = S("oak_planks")                     # 마루 (밝은 소나무 판)
JANGPAN = S("birch_planks")                # 방바닥 장판 (노란 기름종이 느낌)


def _beam(axis):
    return S("stripped_spruce_log", axis=axis)


def _wing_tops(x0, x1, z0, z1, ridge, ends):
    """한 날개 지붕의 칸별 높이(반 칸 단위). ridge: 용마루 방향('x'|'z').
    ends: (작은 쪽 끝, 큰 쪽 끝) 각각 'hip'(추녀만, 모임) / 'paljak'(아래는 추녀, 위는 합각) / None(다른 날개에 묻힘).
    팔작: 끝에서 S칸까지는 모임지붕, 그 안쪽은 맞배라서 경계에 세모 합각벽이 생긴다."""
    S_END = 3
    m = ((z1 - z0) if ridge == "x" else (x1 - x0)) // 2 + 1
    # 처마 쪽 4칸은 반 칸씩(완만), 그 위는 한 칸씩(45°) 오르는 오목 곡선. 한 번에 한 칸 넘게 뛰면 계단 벽이 생긴다.
    curve = [1, 2, 3, 4] + [4 + 2 * i for i in range(1, m)]
    out = {}
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            a, b, a0, a1, b0, b1 = (x, z, x0, x1, z0, z1) if ridge == "x" else (z, x, z0, z1, x0, x1)
            db = min(b - b0, b1 - b)
            da = min([d for d, e in ((a - a0, ends[0]), (a1 - a, ends[1])) if e] or [99])
            kind = [e for d, e in ((a - a0, ends[0]), (a1 - a, ends[1])) if e and d == da]
            hip = kind and (kind[0] == "hip" or da < S_END)
            h = min(db, da) if hip else db
            t = curve[min(h, len(curve) - 1)]
            if db <= 1 and da <= 1:            # 앙곡: 추녀 끝 두 칸을 들어 올린다
                t += 2 - max(db, da)
            gable = bool(kind) and kind[0] == "paljak" and da == S_END and db > S_END - 1
            hipline = bool(hip) and db == da and 2 <= db
            out[(x, z)] = (t, gable, hipline)
    return out


def _field_roof(k, tops, y0, mat, gable_fill):
    """칸별 높이 지도로 지붕을 깐다. 홀수 = 반블록, 짝수 = 오르막 쪽을 보는 계단(꼭대기는 꽉 찬 블록).
    각 칸은 이웃 칸 블록 높이까지 아래를 채워 틈이 없게 한다. 돌려주는 값: {(x,z): 지붕 블록 y}."""
    full = S(full_of(mat))
    ys = {p: y0 + (t - 1) // 2 if t % 2 else y0 + t // 2 - 1 for p, (t, *_) in tops.items()}
    for (x, z), (t, gable, _) in tops.items():
        nb = [((dx, dz), tops[(x + dx, z + dz)][0]) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))
              if (x + dx, z + dz) in tops]
        y = ys[(x, z)]
        hi = max(nb, key=lambda n: n[1]) if nb else None
        if t % 2:
            blk = S(f"{mat}_slab")
        elif hi and hi[1] > t:
            blk = S(f"{mat}_stairs", facing={(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}[hi[0]])
        else:
            blk = full
        k.set(x, y, z, blk)
        low = min([ys[(x + dx, z + dz)] for (dx, dz), _ in nb] + [y])
        for yy in range(low, y):
            k.set(x, yy, z, gable_fill if gable else full)
    return ys


def _seal_up(k, x, z, y_from, blk):
    """벽 위부터 지붕 밑까지 빈 칸을 막는다 (방과 부엌 다락을 대청 쪽 바깥 공기와 나눔)."""
    y = y_from
    while (x, y, z) not in k.cells and y < y_from + 12:
        k.set(x, y, z, blk)
        y += 1


def _hanok_wall(k, x0, z0, x1, z1, posts, y_top=5):
    """기둥·창방·하방·회벽 벽 한 줄 (x0==x1 이면 남북 방향).
    y1 하방(기둥 자리는 주춧돌), y2~4 회벽, y5 창방. 기둥은 posts 좌표에."""
    along = "z" if x0 == x1 else "x"
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            a = z if along == "z" else x
            if a in posts:
                k.set(x, 1, z, S("polished_andesite"))   # 주춧돌
                k.fill(x, 2, z, x, y_top - 1, z, POST)
                k.set(x, y_top, z, POST)
            else:
                k.set(x, 1, z, BOARD)                    # 하방
                k.fill(x, 2, z, x, y_top - 1, z, PLASTER)
                k.set(x, y_top, z, _beam(along))         # 창방


def _changho(k, x, z, along, y0=3, y1=4):
    """창호: 아래 머름(널판) 위 창호지(흰 유리판)."""
    k.set(x, 2, z, BOARD)
    for y in range(y0, y1 + 1):
        k.pane(x, y, z, along, "white_stained_glass_pane")


def hanok():
    k = Arch()
    stone = mix((S("cobblestone"), 4), (S("andesite"), 2), (S("stone"), 2), (S("mossy_cobblestone"), 1))

    # ---------------------------------------------------------------- 기단 (막돌, 기둥선 밖 1칸)
    for x0, z0, x1, z1 in ((-1, 6, 25, 16), (-1, -1, 9, 8)):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                k.set(x, 0, z, stone(x, 0, z))
    for x in (11, 12, 13):                              # 대청 앞 디딤돌
        k.set(x, 0, 5, S("smooth_stone_slab"))

    # ---------------------------------------------------------------- 바닥
    k.fill(9, 1, 7, 23, 1, 8, MARU)                    # 툇마루
    k.fill(9, 1, 10, 15, 1, 14, MARU)                  # 대청
    for z in (10, 12, 14):                             # 우물마루 귀틀
        k.fill(9, 1, z, 15, 1, z, _beam("x"))
    k.fill(1, 1, 10, 7, 1, 14, JANGPAN)                # 안방
    k.fill(17, 1, 10, 23, 1, 14, JANGPAN)              # 건넌방
    k.fill(1, 0, 1, 7, 0, 8, S("packed_mud"))          # 부엌 흙바닥 (한 단 낮음)

    # ---------------------------------------------------------------- 벽과 기둥
    main_posts_x = {0, 4, 8, 12, 16, 20, 24}
    _hanok_wall(k, 0, 15, 24, 15, main_posts_x)         # 뒷벽
    _hanok_wall(k, 16, 9, 24, 9, main_posts_x)          # 건넌방 앞벽
    _hanok_wall(k, 0, 9, 8, 9, main_posts_x)            # 안방|부엌
    _hanok_wall(k, 0, 9, 0, 15, {9, 12, 15})            # 서쪽 끝
    _hanok_wall(k, 24, 9, 24, 15, {9, 12, 15})          # 동쪽 끝
    _hanok_wall(k, 8, 9, 8, 15, {9, 12, 15})            # 안방|대청
    _hanok_wall(k, 16, 9, 16, 15, {9, 12, 15})          # 대청|건넌방
    _hanok_wall(k, 0, 0, 8, 0, {0, 4, 8})               # 부엌 앞(북)
    _hanok_wall(k, 0, 0, 0, 9, {0, 4, 9})               # 부엌 서쪽
    _hanok_wall(k, 8, 0, 8, 9, {0, 4, 9})               # 부엌 동쪽 (마당 쪽)
    for x in range(8, 25, 4):                          # 툇기둥 (앞이 트인 줄)
        k.set(x, 1, 7, S("polished_andesite"))
        k.fill(x, 2, 7, x, 4, 7, POST)
    k.fill(8, 5, 7, 24, 5, 7, _beam("x"))              # 툇 창방
    for x in range(8, 25, 4):
        k.set(x, 5, 8, _beam("z"))                     # 툇보 (기둥 → 벽)
        k.set(x, 5, 7, POST)
    for x in (9, 10, 11, 13, 14, 15):                  # 대청 앞: 들어열개를 걷어 올려 트인 상태
        k.set(x, 1, 9, MARU)
    k.fill(9, 5, 9, 15, 5, 9, _beam("x"))
    k.set(12, 1, 9, S("polished_andesite"))
    k.fill(12, 2, 9, 12, 5, 9, POST)
    k.fill(12, 5, 10, 12, 5, 14, _beam("z"))           # 대들보

    # ---------------------------------------------------------------- 창호와 문
    for x in (2, 3, 5, 6):                             # 안방 뒤 창
        _changho(k, x, 15, "x")
    for x in (9, 10, 14, 15):                          # 대청 뒤 바라지창
        _changho(k, x, 15, "x")
    k.door(13, 2, 15, "spruce", facing="south")        # 대청 뒷문 (판문)
    for x in (21, 22):                                 # 건넌방 앞·뒤 창
        _changho(k, x, 9, "x")
        _changho(k, x, 15, "x")
    for z in (13, 14):                                 # 건넌방 동쪽 창
        _changho(k, 24, z, "z")
    for z in (11, 13):                                 # 안방 서쪽 창
        _changho(k, 0, z, "z")
    k.door(18, 2, 9, "spruce", facing="north")         # 건넌방 ← 툇마루
    k.door(16, 2, 13, "spruce", facing="east")         # 건넌방 ← 대청 (문지방)
    k.door(8, 2, 11, "spruce", facing="west")          # 안방 ← 대청
    k.door(7, 2, 9, "spruce", facing="north")          # 안방 ← 부엌 (한 단 높음)
    k.door(2, 1, 0, "spruce", facing="north")          # 부엌 ← 마당
    k.door(8, 1, 6, "spruce", facing="east")           # 부엌 옆문
    for z in (2, 3):                                   # 부엌 살창 (연기 빠지는 나무 창살)
        for y in (3, 4):
            k.set(0, y, z, S("spruce_fence"))
    for x in (5, 6):
        for y in (3, 4):
            k.set(x, y, 0, S("spruce_fence"))

    # ---------------------------------------------------------------- 지붕 (ㄱ자 팔작, 처마 2칸)
    tops = {}
    for wing in (_wing_tops(-2, 26, 5, 17, "x", ("hip", "paljak")),        # 몸채: 서쪽은 부엌채와 모임
                 _wing_tops(-2, 10, -2, 17, "z", ("paljak", "hip"))):     # 부엌채: 북쪽 끝이 합각
        for p, v in wing.items():
            if p not in tops or v[0] > tops[p][0]:
                tops[p] = v
    ys = _field_roof(k, tops, 5, TILE, BOARD)
    for (x, z), (t, *_) in tops.items():               # 처마 밑 서까래: 처마 둘째 줄 아래 나무 띠
        if t == 2 and ys[(x, z)] == 5 and (x, 4, z) not in k.cells:
            k.set(x, 4, z, S("spruce_trapdoor", facing="north", half="top"))
    top = max(t for t, *_ in tops.values())
    ridge = [p for p, (t, *_) in tops.items() if t == top]
    for x, z in ridge:                                  # 용마루 (반 칸)
        k.set(x, ys[(x, z)] + 1, z, S(f"{TILE}_slab"))
    for (x, z), (t, _, hipline) in tops.items():        # 추녀마루: 추녀선 위 반 칸 띠
        if hipline and t < top:
            k.set(x, ys[(x, z)] + 1, z, S(f"{TILE}_slab"))
    rx = [x for x, z in ridge if z == 11]
    rz = [z for x, z in ridge if x == 4]
    k.set(max(rx), ys[(max(rx), 11)] + 1, 11, S(f"{TILE}_stairs", facing="west"))   # 용마루 끝 들림
    k.set(4, ys[(4, min(rz))] + 1, min(rz), S(f"{TILE}_stairs", facing="south"))

    # 다락 막기: 안방·부엌 다락을 트인 대청 다락과 나눈다
    for z in range(0, 16):
        _seal_up(k, 8, z, 6, PLASTER)
    # 방 천장 (반자)
    k.fill(1, 5, 10, 7, 5, 14, S("birch_planks"))
    k.fill(17, 5, 10, 23, 5, 14, S("birch_planks"))
    # 대청 연등천장: 지붕 밑에 서까래를 드러낸다
    for x in range(9, 16):
        for z in range(10, 15):
            y = min(yy for (xx, yy, zz) in k.cells if xx == x and zz == z and yy > 5)
            k.set(x, y - 1, z, _beam("z") if x % 2 else BOARD)

    # ---------------------------------------------------------------- 부엌 (흙바닥 y0, 아궁이·부뚜막)
    for x in range(1, 6):
        if x in (2, 4):
            k.set(x, 1, 8, S("furnace", facing="north", lit=True))   # 아궁이 (안방 구들로 불길)
            k.set(x, 2, 8, S("water_cauldron", level=3))            # 솥
        else:
            k.set(x, 1, 8, S("mud_bricks"))
            k.set(x, 2, 8, S("mud_brick_slab"))
    k.shelf_wall(1, 4, 1, 6, 3, "spruce", "east")                # 살강
    k.set(7, 1, 1, S("decorated_pot"))                           # 물독
    k.set(6, 1, 1, S("decorated_pot"))
    k.set(1, 1, 1, S("barrel", facing="up"))                     # 쌀독
    k.set(1, 2, 1, S("barrel", facing="up"))
    for z in (1, 2):                                             # 장작
        k.set(7, 1, z + 2, S("oak_log", axis="x"))
    k.set(7, 2, 3, S("oak_log", axis="x"))
    k.fill(1, 5, 4, 7, 5, 4, _beam("x"))                       # 부엌 대들보 (연기에 그을린 보)
    k.set(4, 4, 4, S("iron_chain", axis="y"))
    k.hang(4, 3, 4)

    # ---------------------------------------------------------------- 안방 (x1..7, z10..14)
    for x in (1, 2, 3):                                          # 장롱 (반닫이 위 머릿장)
        k.set(x, 2, 14, S("chest", facing="north"))
        k.set(x, 3, 14, S("spruce_trapdoor", facing="north", half="bottom"))
    k.set(4, 2, 14, S("barrel", facing="north"))                 # 머릿장
    k.set(4, 3, 14, S("decorated_pot"))
    k.rug(2, 10, 5, 12, 2, "red", border="yellow")               # 보료·요
    k.set(6, 2, 12, S("red_wool_slab"))                          # 방석
    k.set(6, 2, 10, S("spruce_slab"))                            # 소반
    k.set(1, 2, 10, S("spruce_shelf", facing="east"))            # 경대
    k.hang(4, 4, 12)
    # ---------------------------------------------------------------- 대청 (트인 마루: 상자 없이)
    k.set(9, 2, 14, S("spruce_planks"))                          # 뒤주
    k.set(9, 3, 14, S("spruce_slab"))
    k.set(10, 2, 14, S("decorated_pot"))
    k.set(15, 2, 14, S("decorated_pot"))
    k.set(13, 2, 11, S("spruce_slab"))                           # 좌식 탁자
    k.set(13, 2, 12, S("spruce_slab"))
    k.set(14, 2, 11, S("red_wool_slab"))
    k.set(14, 2, 12, S("red_wool_slab"))
    k.hang(12, 4, 12)
    # ---------------------------------------------------------------- 건넌방 (x17..23, z10..14)
    k.bed(22, 2, 12, "white", "south")                           # 요 대신 낮은 잠자리
    k.set(17, 2, 14, S("chest", facing="north"))                 # 반닫이
    k.set(18, 2, 14, S("chest", facing="north"))
    k.set(17, 3, 14, S("decorated_pot"))
    k.set(19, 2, 10, S("spruce_slab", type="top"))               # 서안 (낮은 책상)
    k.set(19, 2, 11, S("red_wool_slab"))
    k.set(17, 2, 10, S("lectern", facing="east"))                # 경상
    k.shelf_wall(23, 10, 23, 11, 3, "spruce", "west")            # 문갑
    k.rug(18, 12, 20, 13, 2, "light_gray")
    k.hang(20, 4, 12)
    # ---------------------------------------------------------------- 굴뚝 (뒤뜰, 낮게)
    k.fill(2, 1, 16, 2, 3, 16, S("bricks"))
    k.set(2, 4, 16, S("brick_slab"))
    return k.build()


def real_templates():
    return [
        {"name": "모던 2층 단독주택", "category": "주택",
         "description": "1블록=1m 실제 비율로 옮긴 흰 벽·검은 슬레이트 박공지붕 주택. "
                        "나무 마감 현관과 캐노피, 차고 위 유리 난간 테라스. "
                        "어두운 창틀·층 띠·현관 기둥으로 벽에 깊이를 주고, 1층 천장에 나무 들보. "
                        "1층 거실·현관 홀·부엌 식당·차고, 2층 안방·욕실·아이방·서재. "
                        "층고 4칸, 위아래 층 창 정렬, 모든 방은 문과 계단으로 이어진다.",
         "data": family_house()},
        {"name": "ㄱ자 한옥", "category": "주택",
         "description": "부엌채가 마당 쪽으로 꺾인 ㄱ자 안채. 막돌 기단 위 주춧돌·기둥·창방, 흰 회벽과 창호지 창. "
                        "처마 2칸에 추녀 끝이 들린 팔작 기와지붕, 두 지붕이 만나는 회첨. "
                        "흙바닥 부엌(아궁이·솥·살강) → 한 단 높은 안방(장롱·보료), 우물마루 대청(연등천장), "
                        "건넌방, 앞쪽 툇마루.",
         "data": hanok()},
    ]
