"""갈림길 모퉁이 주택 — 직접 설계한 템플릿 (설계 근거: design/taste-profile.md, design/crossroads-townhouse.md)

정면(입구) = z 가 작은 쪽(북쪽). 모든 블록은 template_format.state() 로 26.3 블록 데이터에서 만든다.

매스 구성
  A 본채   x 0..10, z 0..9   돌 1층(y1-4) + 반목조 2층(y5-9, 앞으로 1칸 jetty) + 정면 박공 지붕(용마루 z 방향)
  B 날개   x 11..17, z 2..8 돌 1층 + 반목조 다락층, 교차 박공(용마루 x 방향, 동쪽을 향함)
  C 돌출창 본채 2층 정면 가운데 x 4..6
  D 처마   서쪽 x -4..-1, z 3..8 기둥으로 받친 작업 공간
  E 굴뚝   본채 뒤 바깥 x 2..3, z 10..11, 용마루보다 높이
"""
from seed import Builder
from template_format import state as S

FRAME = "stripped_oak_log"
WOOD = "oak"             # 계단·트랩도어·울타리 (골조와 같은 나무)
DARK = "spruce"          # 덧창·처마 띠 (대비색)
ROOF = "deepslate_tile"
PLASTER = S("calcite")
FLOWERS = S("flowering_azalea_leaves", persistent=True, distance=1)
FACE = {(0, -1): "north", (0, 1): "south", (-1, 0): "west", (1, 0): "east"}


def log(axis, kind=FRAME):
    return S(kind, axis=axis)


def stone(x, y, z):
    """회색 돌벽: 조약돌 위주 + 돌벽돌·안산암, 아래쪽일수록 이끼."""
    h = (x * 73856093 ^ y * 19349663 ^ z * 83492791) % 20
    if y <= 1 and h < 6 or y == 2 and h < 3:
        return S("mossy_cobblestone")
    if h < 11:
        return S("cobblestone")
    if h < 17:
        return S("stone_bricks")
    return S("andesite")


def roof_stair(facing, half="bottom", m=ROOF):
    return S(f"{m}_stairs", facing=facing, half=half)


def window(b, x, y, z, out, *, height=1, shutters=True, box=True):
    """창(유리판) + 양옆 덧창 + 아래 꽃 화단. out = 바깥 방향."""
    ox, oz = out
    along_x = oz != 0
    for dy in range(height):
        b.set(x, y + dy, z, S("glass_pane", **({"east": True, "west": True} if along_x
                                                 else {"north": True, "south": True})))
        if shutters:
            sx, sz = (1, 0) if along_x else (0, 1)
            for d in (-1, 1):
                b.set(x + sx * d + ox, y + dy, z + sz * d + oz,
                      S(f"{DARK}_trapdoor", facing=FACE[out], open=True))
    if box:
        b.set(x + ox, y - 1, z + oz, FLOWERS)


def gable_wall(b, plane, axis, lo, hi, y0, center_window=True):
    """박공 삼각벽: 회벽 + 가운데 기둥 + 들보 + 작은 창.
    axis='x' 이면 z=plane 인 벽(정면/뒷면), 'z' 이면 x=plane 인 벽."""
    steps = (hi - lo + 2) // 2
    mid = (lo + hi) // 2
    for i in range(steps):
        y = y0 + i
        for c in range(lo + i, hi - i + 1):
            blk = PLASTER
            if c == mid and i > 0:
                blk = log("y")                                   # 가운데 기둥
            p = (c, y, plane) if axis == "x" else (plane, y, c)
            b.set(*p, blk)
    if center_window and steps >= 4:
        for c in (mid - 1, mid + 1):
            p = (c, y0 + 2, plane) if axis == "x" else (plane, y0 + 2, c)
            b.set(*p, S("glass_pane", **({"east": True, "west": True} if axis == "x"
                                          else {"north": True, "south": True})))


def roof_ridge_z(b, xa, xb, za, zb, y0):
    """용마루가 z 방향. 좌우(x)로 경사. 처마 끝은 두꺼운 띠(뒤집힌 계단)로."""
    n = xb - xa + 1
    steps = n // 2
    for i in range(steps):
        for z in range(za, zb + 1):
            b.set(xa + i, y0 + i, z, roof_stair("east"))
            b.set(xb - i, y0 + i, z, roof_stair("west"))
        # 앞뒤 박공 끝: 지붕 아래 띠
        if i > 0:
            for z in (za, zb):
                b.set(xa + i, y0 + i - 1, z, roof_stair("west", "top", DARK))
                b.set(xb - i, y0 + i - 1, z, roof_stair("east", "top", DARK))
    mid = xa + steps
    for z in range(za, zb + 1):
        b.set(mid, y0 + steps - 1, z, S(f"{ROOF}s"))
        b.set(mid, y0 + steps, z, S(f"{ROOF}_slab"))
    return y0 + steps


def roof_ridge_x(b, xa, xb, za, zb, y0):
    """용마루가 x 방향. 앞뒤(z)로 경사."""
    n = zb - za + 1
    steps = n // 2
    for i in range(steps):
        for x in range(xa, xb + 1):
            b.set(x, y0 + i, za + i, roof_stair("south"))
            b.set(x, y0 + i, zb - i, roof_stair("north"))
        if i > 0:
            b.set(xb, y0 + i - 1, za + i, roof_stair("north", "top", DARK))
            b.set(xb, y0 + i - 1, zb - i, roof_stair("south", "top", DARK))
    if n % 2:
        for x in range(xa, xb + 1):
            b.set(x, y0 + steps - 1, za + steps, S(f"{ROOF}s"))
            b.set(x, y0 + steps, za + steps, S(f"{ROOF}_slab"))
    return y0 + steps


def timber_story(b, x0, x1, z0, z1, y0, y1, posts_x, posts_z, skip_walls=()):
    """반목조 층: 아래 들보(y0), 위 들보(y1), 기둥, 회벽 채움. skip_walls: 'west'/'east'/'north'/'south'"""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                side = ("north" if z == z0 else "south" if z == z1 else
                        "west" if x == x0 else "east" if x == x1 else None)
                if side is None or side in skip_walls:
                    continue
                on_xwall = z in (z0, z1)
                if y in (y0, y1):
                    blk = log("x" if on_xwall else "z")
                elif (on_xwall and x in posts_x) or (not on_xwall and z in posts_z):
                    blk = log("y")
                else:
                    blk = PLASTER
                b.set(x, y, z, blk)


def crossroads_townhouse():
    b = Builder()

    # ---------------------------------------------------------------- A 본채
    # 기초와 앞 디딤단
    b.fill(0, 0, 0, 10, 0, 9, S("stone_bricks"))
    b.fill(0, 0, -1, 10, 0, -1, S("stone_bricks"))
    b.fill(1, 0, 1, 9, 0, 8, S("spruce_planks"))
    # 1층 돌벽 (모서리는 다듬은 안산암 귓돌)
    for y in range(1, 5):
        for x in range(0, 11):
            for z in range(0, 10):
                if x in (0, 10) or z in (0, 9):
                    corner = x in (0, 10) and z in (0, 9)
                    b.set(x, y, z, S("polished_andesite") if corner and y % 2 else stone(x, y, z))
    # 현관: 문 + 돌 문틀 + 차양 대신 위 돌출창이 지붕 역할
    b.door(5, 1, 0, "spruce")
    b.set(5, 3, 0, S("stone_brick_stairs", facing="south", half="top"))
    b.set(5, 0, -1, S("stone_brick_stairs", facing="south"))
    b.set(5, 0, -2, S("stone_brick_slab"))
    for x in (2, 8):
        window(b, x, 2, 0, (0, -1), height=2)
    b.set(3, 1, -1, S("potted_red_tulip"))
    b.set(7, 1, -1, S("potted_azure_bluet"))
    for x in (4, 6):
        b.set(x, 4, -1, S("lantern", hanging=True))
    # 뒤·옆 1층 창
    window(b, 6, 2, 9, (0, 1), height=2)
    window(b, 0, 2, 1, (-1, 0), height=2)

    # 2층 반목조 (앞으로 1칸 jetty)
    b.fill(1, 5, 0, 9, 5, 8, S("oak_planks"))
    timber_story(b, 0, 10, -1, 9, 5, 9, posts_x={0, 3, 7, 10}, posts_z={-1, 4, 9})
    # jetty 까치발
    for x in (0, 3, 7, 10):
        b.set(x, 4, -1, S(f"{WOOD}_stairs", facing="south", half="top"))
    # 정면 양쪽 칸: 2칸짜리 창 + 화단
    for x in (1, 2, 8, 9):
        window(b, x, 7, -1, (0, -1), shutters=False)
    # 뒤·옆 2층 창
    for x in (2, 8):
        window(b, x, 7, 9, (0, 1))
    for z in (1, 7):
        window(b, 0, 7, z, (-1, 0))
        window(b, 10, 7, z, (1, 0), box=False)

    # ---------------------------------------------------------------- C 돌출창
    for x in (4, 6):
        for y in (6, 7, 8):
            b.set(x, y, -2, log("y"))
    for y in (6, 7):
        b.set(5, y, -2, S("glass_pane", east=True, west=True))
        b.set(4, y, -1, None)
        b.set(6, y, -1, None)
        b.set(5, y, -1, None)
    b.set(5, 8, -2, PLASTER)
    for x in (4, 5, 6):
        b.set(x, 5, -2, S(f"{WOOD}_stairs", facing="south", half="top"))
        b.set(x, 9, -2, roof_stair("south"))
    b.set(5, 6, -3, FLOWERS)

    # ---------------------------------------------------------------- 본채 지붕 + 박공
    gable_wall(b, -1, "x", 0, 10, 10)
    gable_wall(b, 9, "x", 0, 10, 10, center_window=False)
    main_peak = roof_ridge_z(b, -1, 11, -2, 10, 10)

    # ---------------------------------------------------------------- B 동쪽 날개
    b.fill(11, 0, 2, 17, 0, 8, S("stone_bricks"))
    b.fill(11, 0, 3, 16, 0, 7, S("spruce_planks"))
    for y in range(1, 5):
        for x in range(11, 18):
            for z in range(2, 9):
                if x == 17 or z in (2, 8):
                    corner = x == 17 and z in (2, 8)
                    b.set(x, y, z, S("polished_andesite") if corner and y % 2 else stone(x, y, z))
    b.door(14, 1, 2, "spruce")
    b.set(14, 0, 1, S("stone_brick_stairs", facing="south"))
    for x in (13, 14, 15):
        b.set(x, 4, 1, S(f"{DARK}_trapdoor", facing="north", half="top"))
    b.set(14, 3, 1, S("lantern", hanging=True))
    window(b, 12, 2, 2, (0, -1), height=2)
    window(b, 16, 2, 2, (0, -1), height=2)
    window(b, 17, 2, 5, (1, 0), height=2)
    timber_story(b, 11, 17, 2, 8, 5, 8, posts_x={14, 17}, posts_z={2, 5, 8}, skip_walls=("west",))
    b.fill(11, 5, 3, 16, 5, 7, S("oak_planks"))
    window(b, 15, 6, 2, (0, -1), height=2)
    window(b, 12, 6, 8, (0, 1))
    gable_wall(b, 17, "z", 2, 8, 9)
    roof_ridge_x(b, 11, 18, 1, 9, 9)

    # ---------------------------------------------------------------- D 서쪽 처마
    b.fill(-4, 0, 3, -1, 0, 8, S("cobblestone"))
    for i, x in enumerate(range(-4, 0)):
        for z in range(3, 9):
            b.set(x, 4 + i, z, roof_stair("east"))
    for z in (3, 8):
        for y in range(1, 4):
            b.set(-4, y, z, log("y"))
        b.set(-4, 3, z + (1 if z == 3 else -1), S(f"{WOOD}_stairs", facing="south" if z == 3 else "north", half="top"))
    b.set(-1, 1, 4, S("barrel", facing="up"))
    b.set(-1, 1, 5, S("barrel", facing="north"))
    b.set(-1, 2, 4, S("barrel", facing="up"))
    b.set(-2, 1, 7, S("hay_block", axis="x"))
    b.set(-1, 1, 7, S("hay_block", axis="z"))
    b.set(-3, 1, 6, S("chipped_anvil", facing="north"))
    b.set(-1, 1, 6, S("composter"))
    b.set(-3, 2, 4, S("lantern", hanging=True))
    # 처마 쪽 덩굴
    for y in (2, 3, 4):
        b.set(-1, y, 2, S("vine", east=True))

    # ---------------------------------------------------------------- E 굴뚝
    b.fill(1, 0, 10, 4, 1, 11, S("cobblestone"))
    for x in (1, 4):
        b.set(x, 2, 10, S("cobblestone_stairs", facing="east" if x == 1 else "west"))
        b.set(x, 2, 11, S("cobblestone_stairs", facing="east" if x == 1 else "west"))
    b.fill(2, 2, 10, 3, 4, 11, S("cobblestone"))
    b.fill(2, 5, 10, 3, main_peak + 1, 11, S("bricks"))
    top = main_peak + 2
    b.set(2, top, 10, S("campfire", lit=True))
    b.set(3, top, 11, S("campfire", lit=True))
    b.set(3, top, 10, S("brick_slab"))
    b.set(2, top, 11, S("brick_slab"))

    # ---------------------------------------------------------------- 실내
    b.set(2, 1, 8, S("smoker", facing="north"))
    b.set(3, 1, 8, S("furnace", facing="north"))
    b.set(1, 1, 8, S("barrel", facing="up"))
    b.set(5, 1, 5, S("spruce_fence"))
    b.set(5, 2, 5, S("spruce_pressure_plate"))
    b.set(4, 1, 5, S("spruce_stairs", facing="west"))
    b.set(6, 1, 5, S("spruce_stairs", facing="east"))
    b.set(8, 1, 1, S("bookshelf"))
    b.set(9, 1, 1, S("crafting_table"))
    b.set(5, 4, 5, S("lantern", hanging=True))
    for y in range(1, 6):
        b.set(9, y, 8, S("ladder", facing="west"))
    b.set(2, 6, 7, S("red_bed", facing="east", part="foot"))
    b.set(3, 6, 7, S("red_bed", facing="east", part="head"))
    b.set(8, 6, 0, S("chest", facing="south"))
    b.set(5, 6, 4, S("red_carpet"))
    b.set(5, 6, 3, S("red_carpet"))
    b.set(5, 9, 4, S("lantern", hanging=True))
    b.set(15, 1, 6, S("barrel", facing="up"))
    b.set(16, 1, 6, S("barrel", facing="up"))
    b.set(13, 1, 7, S("smithing_table"))

    return b.build()


def townhouse_templates():
    return [{
        "name": "갈림길 모퉁이 주택",
        "category": "주거",
        "description": "길을 향해 박공을 세운 반목조 본채에 낮은 교차 박공 날개와 작업용 처마를 붙인 집. "
                       "튀어나온 2층과 돌출창, 지붕창, 이끼 낀 돌 기초, 지붕 위로 솟은 벽돌 굴뚝.",
        "data": crossroads_townhouse(),
    }]
