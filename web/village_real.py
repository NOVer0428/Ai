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


def _wing_tops(x0, x1, z0, z1, ridge, ends, steep=False):
    """한 날개 지붕의 칸별 높이(반 칸 단위). ridge: 용마루 방향('x'|'z').
    ends: (작은 쪽 끝, 큰 쪽 끝) 각각 'hip'(추녀만, 모임) / 'paljak'(아래는 추녀, 위는 합각) / None(다른 날개에 묻힘).
    팔작: 끝에서 S칸까지는 모임지붕, 그 안쪽은 맞배라서 경계에 세모 합각벽이 생긴다."""
    S_END = 3
    m = ((z1 - z0) if ridge == "x" else (x1 - x0)) // 2 + 1
    # 처마 쪽 4칸은 반 칸씩(완만), 그 위는 한 칸씩(45°) 오르는 오목 곡선. 한 번에 한 칸 넘게 뛰면 계단 벽이 생긴다.
    curve = [1, 2, 3, 4] + [4 + 2 * i for i in range(1, m)]
    if steep:                                  # 서양 중세 지붕: 처음부터 45° (모든 칸 계단)
        curve = [2 + 2 * i for i in range(m + 1)]
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
    name = mat if callable(mat) else (lambda x, z: mat)       # mat: 재료 이름 또는 (x,z)->이름 (지붕 질감 섞기)
    ys = {p: y0 + (t - 1) // 2 if t % 2 else y0 + t // 2 - 1 for p, (t, *_) in tops.items()}
    for (x, z), (t, gable, _) in tops.items():
        m_ = name(x, z)
        full = S(full_of(m_))
        nb = [((dx, dz), tops[(x + dx, z + dz)][0]) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))
              if (x + dx, z + dz) in tops]
        y = ys[(x, z)]
        hi = max(nb, key=lambda n: n[1]) if nb else None
        if t % 2:
            blk = S(f"{m_}_slab")
        elif hi and hi[1] > t:
            blk = S(f"{m_}_stairs", facing={(1, 0): "east", (-1, 0): "west", (0, 1): "south", (0, -1): "north"}[hi[0]])
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


# ==================================================================== 중세 여관 (선술집 겸 여관)
# 근거: design/references-2026.md "중세 여관" 절. 아래는 돌, 위는 목조 골조(2층 앞뒤로 내민 제티),
# 홀수 벽 길이(15×11), 덩어리마다 다른 지붕 높이(본채 > 앞 박공 > 지붕창 > 부엌채), 45° 지붕, 굴뚝은 용마루보다 높게.
IN_STONE = mix((S("stone_bricks"), 5), (S("cobblestone"), 2), (S("andesite"), 2),
               (S("cracked_stone_bricks"), 1), (S("stone"), 1))
IN_BASE = mix((S("cobblestone"), 3), (S("mossy_cobblestone"), 1), (S("stone_bricks"), 2))
IN_POST = S("stripped_dark_oak_log", axis="y")
IN_FILL = S("calcite")                      # 회벽 (흰 테라코타는 분홍빛이라 방해석)
IN_FLOOR = S("spruce_planks")
_BACK = {"north": "south", "south": "north"}


def _dlog(axis):
    return S("stripped_dark_oak_log", axis=axis)


def _roof_mat(x, z):
    from seed_detail import h3
    return "deepslate_brick" if h3(x, 7, z) % 9 == 0 else "deepslate_tile"   # 기와 질감 섞기 (드물게)


def _frame_wall(k, plane, fixed, a0, a1, posts, windows, braces=()):
    """목조 골조 벽 한 면(2층). plane='z'면 z=fixed 인 남북면(a=x), 'x'면 x=fixed 인 동서면(a=z).
    y5 하인방, y6~8 기둥·회벽(창은 y6~7 유리), y9 상인방. braces: 창 없는 2칸 판 (a, a+1)에 넣는 까치발.
    까치발은 벽 바깥 한 칸에 붙인다: 벽이 1칸이라 벽 안에 계단을 박으면 계단의 빈 곳으로 밖이 보인다."""
    along = "x" if plane == "z" else "z"
    out = -1 if fixed <= 0 else 1                 # 바깥 방향 (서·북 면은 -, 동·남 면은 +)

    def at(a, y, d=0):
        return (a, y, fixed + d) if plane == "z" else (fixed + d, y, a)
    for a in range(a0, a1 + 1):
        k.set(*at(a, 5), _dlog(along))
        k.set(*at(a, 9), _dlog(along))
        for y in (6, 7, 8):
            if a in posts:
                k.set(*at(a, y), IN_POST)
            elif a in windows and y < 8:
                k.pane(*at(a, y), along, "glass_pane")
            else:
                k.set(*at(a, y), IN_FILL)
    lo, hi = ("west", "east") if plane == "z" else ("north", "south")
    for a in braces:                        # 위 모서리는 뒤집힌 계단, 아래는 계단 → 기둥 쪽으로 버팀
        for b, f in ((a, lo), (a + 1, hi)):
            k.set(*at(b, 8, out), S("dark_oak_stairs", facing=f, half="top"))
            k.set(*at(b, 6, out), S("dark_oak_stairs", facing=f))


def _gable_fill(k, plane, fixed, a_range, y_from, posts, windows=()):
    """박공 세모벽: 지붕 바로 밑까지 회벽을 채우고 기둥·창을 넣는다."""
    along = "x" if plane == "z" else "z"
    for a in a_range:
        y = y_from
        while y <= y_from + 12:
            p = (a, y, fixed) if plane == "z" else (fixed, y, a)
            if p in k.cells:
                break
            if (a, y) in windows:
                k.pane(*p, along, "glass_pane")
            else:
                k.set(*p, IN_POST if a in posts else IN_FILL)
            y += 1


def _lips(k, tops, ys, out):
    """처마·박공 끝 밑에 뒤집힌 계단(두께감). out(x,z) → 안쪽 방향(facing) 또는 None."""
    for (x, z) in tops:
        f = out(x, z)
        y = ys[(x, z)] - 1
        if f and (x, y, z) not in k.cells:
            k.set(x, y, z, S("dark_oak_stairs", facing=f, half="top"))


def _chimney(k, xs, zs, top, flue=None):
    for x in xs:
        for z in zs:
            for y in range(0, top):
                if flue and (x, z) == flue[:2] and y >= flue[2]:
                    k.set(x, y, z, None)
                else:
                    k.set(x, y, z, IN_STONE(x, y, z))


def medieval_inn():
    k = Arch()

    # ---------------------------------------------------------------- 1층: 돌 (본채 x0..14 z0..10, 부엌채 x-6..0 z1..9)
    hall_floor = mix((S("polished_andesite"), 3), (S("stone_bricks"), 2), (S("andesite"), 1))
    for x0, z0, x1, z1 in ((0, 0, 14, 10), (-6, 1, 0, 9)):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                edge = x in (x0, x1) or z in (z0, z1)
                k.set(x, 0, z, IN_BASE(x, 0, z) if edge else hall_floor(x, 0, z))
                if edge:
                    for y in range(1, 5):
                        k.set(x, y, z, IN_STONE(x, y, z))
    for x, z in ((0, 0), (4, 0), (10, 0), (14, 0), (0, 10), (4, 10), (10, 10), (14, 10), (-6, 1), (-6, 9)):
        k.fill(x, 1, z, x, 4, z, S("spruce_log", axis="y"))          # 1층 기둥 (돌벽 구간 나누기)
    for z in range(1, 10):                                            # 부엌채 상인방
        k.set(-6, 5, z, S("spruce_log", axis="z"))
    for x in range(-6, 1):
        k.set(x, 5, 1, S("spruce_log", axis="x"))
        k.set(x, 5, 9, S("spruce_log", axis="x"))

    def plinth(x, z, f):                                              # 벽 밑 계단 띠 (밑단 무게감)
        if (x, 0, z) not in k.cells:
            k.set(x, 0, z, S("stone_brick_stairs", facing=f))
    k.set(7, 0, -1, S("stone_brick_stairs", facing="south"))          # 문 앞 디딤
    for x in range(0, 15):
        plinth(x, -1, "south")
        plinth(x, 11, "north")
    for z in range(0, 11):
        if z not in (4, 5, 6):
            plinth(15, z, "west")
    for z in (0, 10):
        plinth(-1, z, "east")
    for x in range(-6, 0):
        plinth(x, 0, "south")
        plinth(x, 10, "north")
    for z in range(1, 10):
        if z not in (4, 5, 6):
            plinth(-7, z, "east")

    # ---------------------------------------------------------------- 2층 바닥과 제티 (앞뒤로 한 칸 내밈)
    k.fill(0, 5, -1, 14, 5, 11, IN_FLOOR)
    for x in (3, 7):
        k.fill(x, 4, 1, x, 4, 9, S("stripped_spruce_log", axis="z"))  # 1층 천장 큰 보
    k.fill(11, 4, 1, 11, 4, 8, S("stripped_spruce_log", axis="z"))
    for x in (0, 4, 10, 14):                                          # 제티 까치발
        k.set(x, 4, -1, S("dark_oak_stairs", facing="south", half="top"))
        k.set(x, 4, 11, S("dark_oak_stairs", facing="north", half="top"))

    # ---------------------------------------------------------------- 2층 목조 골조
    fb_posts = {0, 2, 5, 9, 12, 14}                                   # 방 칸막이(x5·x9)와 맞춘 기둥
    _frame_wall(k, "z", -1, 0, 14, fb_posts, {3, 4, 7, 10, 11}, braces=())
    _frame_wall(k, "z", 11, 0, 14, fb_posts, {3, 4, 10, 11}, braces=(6,))
    side_posts = {-1, 1, 4, 7, 9, 11}
    _frame_wall(k, "x", 0, -1, 11, side_posts, {10}, braces=(2, 5))
    _frame_wall(k, "x", 14, -1, 11, side_posts, {2, 3, 10}, braces=(5,))
    k.fill(1, 9, 0, 13, 9, 10, IN_FLOOR)                              # 다락 바닥

    for x, pot in ((3, "potted_poppy"), (4, "potted_cornflower"), (7, "potted_azure_bluet"),
                   (10, "potted_allium"), (11, "potted_poppy")):
        k.set(x, 5, -2, S("dark_oak_slab", type="top"))              # 창턱 선반 + 화분 (가볍게)
        k.set(x, 6, -2, S(pot))

    # ---------------------------------------------------------------- 1층 문과 창
    for z, f, dx in ((0, "north", 7), (10, "south", 6)):
        k.fill(dx - 1, 1, z, dx - 1, 3, z, S("stripped_spruce_log", axis="y"))
        k.fill(dx + 1, 1, z, dx + 1, 3, z, S("stripped_spruce_log", axis="y"))
        k.set(dx, 3, z, S("stripped_spruce_log", axis="x"))
        k.door(dx, 1, z, "spruce", facing=f)
    for x0, x1, z, out in ((2, 3, 0, "north"), (11, 12, 0, "north"), (12, 13, 10, "south")):  # 뒷창은 계단 밑을 피해 동쪽
        dz = -1 if out == "north" else 1
        for x in range(x0, x1 + 1):
            for y in (2, 3):
                k.pane(x, y, z, "x")
            k.set(x, 1, z + dz, S("stone_brick_stairs", facing=_BACK[out], half="top"))   # 창턱
            k.set(x, 4, z + dz, S("stone_brick_stairs", facing=_BACK[out], half="top"))   # 인방
    for z0 in (2, 7):                                                 # 동쪽 창
        for z in (z0, z0 + 1):
            for y in (2, 3):
                k.pane(14, y, z, "z")
    for x in (-4, -2):                                                # 부엌 앞창
        for y in (2, 3):
            k.pane(x, y, 1, "x")
    k.door(-3, 1, 9, "spruce", facing="south")                       # 부엌 뒷문
    k.door(0, 1, 8, "spruce", facing="west")                         # 홀 ↔ 부엌
    k.hang(5, 4, -1)                                                  # 제티 밑 등
    k.hang(9, 4, -1)
    k.set(13, 4, -1, S("spruce_hanging_sign", attached=False, rotation=4))   # 간판 (길과 직각)

    # ---------------------------------------------------------------- 지붕
    kt = _wing_tops(-7, -1, 0, 10, "x", (None, None), steep=True)             # 부엌채 (낮음)
    kys = _field_roof(k, kt, 5, _roof_mat, IN_FILL)
    tops = {}
    for wing, lift in ((_wing_tops(-1, 15, -2, 12, "x", (None, None), steep=True), 0),   # 본채
                       (_wing_tops(3, 11, -2, 6, "z", (None, None), steep=True), 0),     # 앞 박공 (입구 위)
                       (_wing_tops(1, 5, 6, 12, "z", (None, None), steep=True), 2),      # 뒤 지붕창: 한 칸 높게
                       (_wing_tops(9, 13, 6, 12, "z", (None, None), steep=True), 2)):
        for p, (t, *rest) in wing.items():
            if p not in tops or t + lift > tops[p][0]:
                tops[p] = (t + lift, *rest)
    ys = _field_roof(k, tops, 9, _roof_mat, IN_FILL)

    _gable_fill(k, "x", 0, range(-1, 12), 10, {-1, 2, 5, 8, 11}, {(4, 11), (4, 12), (6, 11), (6, 12)})
    # 다락 바닥이 y9 라 y10 창은 발밑이 된다 → 박공 창은 눈높이 y11 부터
    _gable_fill(k, "x", 14, range(-1, 12), 10, {-1, 2, 5, 8, 11}, {(1, 11), (9, 11)})
    _gable_fill(k, "z", -1, range(4, 11), 10, {5, 7, 9}, {(6, 11), (8, 11)})
    _gable_fill(k, "x", -6, range(1, 10), 6, {1, 3, 5, 7, 9})
    for cx in (3, 11):                                                # 지붕창 앞면
        for z in (9, 10):
            for y in (10, 11):
                k.set(cx, y, z, None)
        k.set(cx - 1, 10, 11, IN_POST)
        k.set(cx + 1, 10, 11, IN_POST)
        k.set(cx, 10, 11, IN_FILL)                                    # 창 밑 벽: 다락 바닥 바로 위 유리를 없애고
        k.pane(cx, 11, 11, "x")                                       # 눈높이 한 칸만 유리

    def main_out(x, z):
        return "south" if z == -2 else "north" if z == 12 else "east" if x == -1 else "west" if x == 15 else None
    _lips(k, tops, ys, main_out)
    _lips(k, kt, kys, lambda x, z: "south" if z == 0 else "north" if z == 10 else "east" if x == -7 else None)

    # ---------------------------------------------------------------- 굴뚝: 지붕을 뚫고 용마루보다 높게
    _chimney(k, (15, 16), (4, 5, 6), 18, flue=(15, 5, 2))             # 동쪽 벽난로 (연도로 연기 빠짐)
    k.set(15, 1, 5, S("campfire", lit=True))
    for x, z in ((15, 4), (15, 6), (16, 4), (16, 5), (16, 6)):
        k.set(x, 18, z, S("stone_brick_slab"))
    for y in (1, 2):
        k.set(14, y, 5, S("iron_bars"))                               # 불 앞 쇠창살
    for z in (4, 5, 6):
        k.set(13, 3, z, S("stone_brick_stairs", facing="east", half="top"))   # 벽난로 선반
        k.set(13, 0, z, S("bricks"))
    _chimney(k, (-8, -7), (4, 5, 6), 12)                              # 부엌 굴뚝
    k.set(-7, 12, 5, S("campfire", lit=True))

    # ---------------------------------------------------------------- 1층 홀 (x1..13, z1..9)
    for x in (1, 2, 3):                                               # 술 카운터
        k.set(x, 1, 6, S("barrel", facing="south"))
    for z in (6, 7, 8):
        k.set(4, 1, z, S("barrel", facing="east"))
    k.set(2, 2, 6, S("brewing_stand"))
    k.set(3, 2, 6, S("candle", candles=3, lit=True))
    k.set(4, 2, 7, S("decorated_pot"))
    for y in (1, 2):
        k.set(1, y, 7, S("barrel", facing="east"))                    # 술통
    for x in (2, 3):
        for y in (2, 3):
            k.set(x, y, 9, S("spruce_shelf", facing="north"))         # 뒤 선반
    for x in (2, 4):
        k.set(x, 1, 5, S("spruce_slab"))                             # 바 의자
    for z0 in (3, 7):                                                 # 긴 식탁 + 의자 (x5..7 은 정문에서 곧장 들어오는 통로)
        for x in range(8, 11):
            k.set(x, 1, z0, S("spruce_slab", type="top"))
            k.set(x, 1, z0 - 1, S("spruce_stairs", facing="north"))
            k.set(x, 1, z0 + 1, S("spruce_stairs", facing="south"))
        k.set(9, 2, z0, S("candle", candles=2, lit=True))
        k.set(9, 4, z0, S("iron_chain", axis="y"))                   # 보가 없는 칸이라 사슬로 2층 바닥에 매닮
        k.hang(9, 3, z0)
    k.set(12, 1, 4, S("spruce_stairs", facing="west"))               # 벽난로 앞 안락의자
    k.set(12, 1, 6, S("spruce_stairs", facing="west"))
    k.rug(11, 4, 12, 6, 1, "red", border="brown")
    k.set(1, 1, 1, S("barrel", facing="up"))
    k.set(1, 2, 1, S("decorated_pot"))
    k.set(13, 1, 1, S("hay_block", axis="y"))
    k.hang(3, 3, 3)
    k.hang(11, 3, 2)
    # 계단 (뒷벽 따라 서쪽으로 오름). 5칸이라 마지막 칸 윗면이 2층 바닥과 같고,
    # 동쪽 x13 을 비워 두어 첫 칸을 낮은 쪽(정면)에서 밟는다.
    for i, x in enumerate((12, 11, 10, 9, 8)):
        k.set(x, 1 + i, 9, S("spruce_stairs", facing="west"))
        for y in range(1, 1 + i):
            k.set(x, y, 9, IN_FLOOR)
    for x in (9, 10, 11):                                            # 계단 위 머리 공간 (위층 바닥 구멍)
        k.set(x, 5, 9, None)

    # ---------------------------------------------------------------- 부엌 (x-5..-1, z2..8)
    k.set(-5, 1, 4, S("smoker", facing="east", lit=True))
    k.set(-5, 1, 5, S("water_cauldron", level=3))
    k.set(-5, 1, 6, S("furnace", facing="east", lit=True))
    k.set(-4, 1, 2, S("crafting_table"))
    k.set(-3, 1, 2, S("barrel", facing="south"))
    k.set(-2, 1, 2, S("chest", facing="south"))
    for x in (-4, -3, -2):
        k.set(x, 3, 2, S("spruce_shelf", facing="south"))
    k.set(-2, 1, 5, S("spruce_slab", type="top"))                    # 작업대
    k.set(-2, 1, 6, S("spruce_slab", type="top"))
    k.set(-2, 2, 5, S("decorated_pot"))
    k.fill(-5, 5, 5, -1, 5, 5, S("stripped_spruce_log", axis="x"))   # 부엌 대들보
    k.hang(-3, 4, 5)
    k.set(-1, 1, 7, S("barrel", facing="up"))
    k.set(-1, 2, 7, S("barrel", facing="up"))

    # ---------------------------------------------------------------- 2층 객실 (y5 바닥, y6..8)
    k.fill(5, 6, 0, 5, 8, 6, IN_FLOOR)                                # 칸막이
    k.fill(9, 6, 0, 9, 8, 6, IN_FLOOR)
    k.fill(1, 6, 7, 13, 8, 7, IN_FLOOR)
    for x in (5, 9):
        k.fill(x, 6, 7, x, 8, 7, S("stripped_spruce_log", axis="y"))
    for x in (2, 7, 12):
        k.door(x, 6, 7, "spruce", facing="north")
    k.bed(1, 6, 1, "red", "north")                                   # 서쪽 방: 2인 (머리는 앞벽)
    k.bed(2, 6, 1, "red", "north")
    k.set(1, 6, 2, S("chest", facing="south"))
    k.set(3, 6, 6, S("barrel", facing="up"))
    k.set(3, 7, 6, S("candle", candles=1, lit=True))
    k.rug(1, 1, 4, 3, 6, "brown")
    k.hang(3, 8, 3)
    k.bed(8, 6, 1, "blue", "north")                                  # 가운데 방: 1인
    k.set(8, 6, 2, S("chest", facing="south"))
    k.set(8, 6, 6, S("barrel", facing="up"))
    k.set(8, 7, 6, S("candle", candles=1, lit=True))
    k.set(6, 6, 1, S("lectern", facing="east"))
    k.hang(7, 8, 3)
    for x in (10, 13):                                                # 동쪽 방: 1인 침대 둘
        k.bed(x, 6, 1, "green", "north")
        k.set(x, 6, 2, S("chest", facing="south"))
    k.set(11, 6, 6, S("barrel", facing="up"))
    k.set(11, 7, 6, S("candle", candles=2, lit=True))
    k.rug(11, 1, 12, 3, 6, "green")
    k.hang(12, 8, 3)
    for x in (9, 10, 11):                                             # 계단 구멍 난간
        k.set(x, 6, 8, S("spruce_fence"))
    k.ladder(1, 8, 6, 9, "east")                                      # 다락 사다리
    k.set(6, 6, 10, S("spruce_stairs", facing="south"))              # 복도 의자
    k.set(7, 6, 10, S("spruce_stairs", facing="south"))
    k.hang(5, 8, 9)
    k.hang(9, 8, 9)

    # ---------------------------------------------------------------- 다락 (y9 바닥)
    for x, b in ((5, "barrel"), (6, "chest"), (8, "barrel"), (9, "barrel")):
        k.set(x, 10, 5, S(b, facing="up") if b == "barrel" else S(b, facing="south"))
    k.set(5, 11, 5, S("barrel", facing="up"))
    k.set(12, 10, 5, S("hay_block", axis="y"))
    k.hang(7, ys[(7, 5)] - 1, 5)

    k.settle()                                                        # 계단 모서리·울타리·판유리 연결
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
        {"name": "중세 여관", "category": "상업",
         "description": "1층은 돌, 2층은 앞뒤로 내민 목조 골조(제티·까치발)인 선술집 겸 여관. "
                        "45° 기와지붕에 입구 위 앞 박공, 뒤 지붕창 둘, 낮은 부엌채, 용마루보다 높은 굴뚝 둘. "
                        "1층 홀(술 카운터·술통·긴 식탁·벽난로·보), 부엌(훈연기·화로·솥), 2층 객실 셋, 다락 창고.",
         "data": medieval_inn()},
    ]
