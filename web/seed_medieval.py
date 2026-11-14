"""중세풍 건물 템플릿 생성기 (직접 설계한 오리지널 건물).

공통 규칙: 정면(입구)은 z 가 가장 작은 쪽이고 북쪽(-z)을 바라본다.
돌 기초 1층 + 반목조(통나무 골조 + 회벽) 위층 + 경사 지붕 구조.
"""
from seed import Builder
from template_format import state

FACE = {(0, -1): "north", (0, 1): "south", (-1, 0): "west", (1, 0): "east"}
FLOWER_BOX = state("flowering_azalea_leaves", persistent=True, distance=1)
STONE_MIX = [state("stone_bricks")] * 6 + [state("cobblestone")] * 2 + [
    state("mossy_stone_bricks"), state("cracked_stone_bricks")]


def stairs(material, facing, half="bottom"):
    return state(f"{material}_stairs", facing=facing, half=half)


def log(kind, axis):
    return state(kind, axis=axis)


def stone_at(x, y, z):
    return STONE_MIX[(x * 73856093 ^ y * 19349663 ^ z * 83492791) % len(STONE_MIX)]


def pane(axis):
    # 벽 방향으로 이어지는 유리판
    if axis == "x":
        return state("glass_pane", east=True, west=True)
    return state("glass_pane", north=True, south=True)


def window(b, x, y, z, out, wood, shutters=True, flowers=True, skip=()):
    """벽의 (x, y, z) 에 창문. out = 바깥 방향 벡터. 덧창(트랩도어)과 꽃 화단을 붙인다."""
    ox, oz = out
    b.set(x, y, z, pane("x" if oz else "z"))
    sx, sz = (1, 0) if oz else (0, 1)
    if shutters:
        for d in (-1, 1):
            p = (x + sx * d + ox, y, z + sz * d + oz)
            if p not in skip:
                b.set(*p, state(f"{wood}_trapdoor", facing=FACE[out], open=True))
    if flowers:
        b.set(x + ox, y - 1, z + oz, FLOWER_BOX)


def ring(b, x0, x1, z0, z1, y, log_kind):
    """벽 위 테두리 들보."""
    for x in range(x0, x1 + 1):
        b.set(x, y, z0, log(log_kind, "x"))
        b.set(x, y, z1, log(log_kind, "x"))
    for z in range(z0 + 1, z1):
        b.set(x0, y, z, log(log_kind, "z"))
        b.set(x1, y, z, log(log_kind, "z"))


def timber_walls(b, x0, x1, z0, z1, y0, y1, log_kind, plaster):
    """통나무 기둥(모서리 + 가운데) 사이를 회벽으로 채운 반목조 벽."""
    xs = {x0, (x0 + x1) // 2, x1}
    zs = {z0, (z0 + z1) // 2, z1}
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if x not in (x0, x1) and z not in (z0, z1):
                    continue
                post = (x in xs and z in (z0, z1)) or (z in zs and x in (x0, x1))
                b.set(x, y, z, log(log_kind, "y") if post else plaster)


def gable_roof(b, xa, xb, za, zb, y0, roof, roof_full, roof_slab, gable_xs, plaster, log_kind, wood):
    """용마루가 x 방향인 박공지붕. 앞뒤(z)로 경사, 양옆(gable_xs) 삼각벽은 회벽. 꼭대기 y 반환."""
    n = zb - za + 1
    steps = n // 2
    # 삼각 벽
    for gx in gable_xs:
        for i in range(1, steps):
            for z in range(za + i + 1, zb - i):
                b.set(gx, y0 + i, z, plaster)
        mid = (za + zb) // 2
        for y in range(y0 + 1, y0 + steps):
            if za + (y - y0) + 1 <= mid <= zb - (y - y0) - 1:
                b.set(gx, y, mid, log(log_kind, "y"))
        if steps >= 4:
            out = (-1, 0) if gx == min(gable_xs) else (1, 0)
            window(b, gx, y0 + 2, mid - 1 if n % 2 == 0 else mid, out, wood, shutters=False, flowers=False)
    # 지붕면
    for i in range(steps):
        for x in range(xa, xb + 1):
            b.set(x, y0 + i, za + i, stairs(roof, "south"))
            b.set(x, y0 + i, zb - i, stairs(roof, "north"))
    peak = y0 + steps - 1
    if n % 2:
        zm = za + steps
        for x in range(xa, xb + 1):
            b.set(x, y0 + steps - 1, zm, roof_full)
            b.set(x, y0 + steps, zm, state(f"{roof_slab}", type="bottom", waterlogged=False))
        peak = y0 + steps
    # 처마 끝 아래 장식 (뒤집힌 계단)
    for x in (xa, xb):
        b.set(x, y0 - 1, za, stairs(wood, "south", "top"))
        b.set(x, y0 - 1, zb, stairs(wood, "north", "top"))
    return peak


def medieval_house(W, D, upper, *, wood, log_kind, plaster, roof, roof_full, roof_slab,
                   jetty=True, side_skip=(), extra=None):
    b = Builder()
    plaster, roof_full = state(plaster), state(roof_full)
    x0, x1, z0, z1 = 0, W - 1, 0, D - 1
    door_x = W // 2
    mid_x = (x0 + x1) // 2

    # 기초 + 1층 돌벽
    b.fill(x0, 0, z0, x1, 0, z1, state("stone_bricks"))
    for y in range(1, 4):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                if x in (x0, x1) or z in (z0, z1):
                    b.set(x, y, z, stone_at(x, y, z))
    b.door(door_x, 1, z0, wood)
    b.set(door_x, 0, z0 - 1, stairs("stone_brick", "south"))

    off = max(2, W // 4)
    front_skip = {(door_x, 2, z0 - 1)}
    for x in (door_x - off, door_x + off):
        window(b, x, 2, z0, (0, -1), wood, skip=front_skip)
        window(b, x, 2, z1, (0, 1), wood)
    if "west" not in side_skip:
        window(b, x0, 2, D // 2, (-1, 0), wood)
    if "east" not in side_skip:
        window(b, x1, 2, D // 2, (1, 0), wood)

    # 위층 (반목조). 앞쪽은 한 칸 튀어나오게(jetty)
    uz0 = z0 - 1 if (jetty and upper) else z0
    y = 4
    floors = []
    for _ in range(upper):
        ring(b, x0, x1, uz0, z1, y, log_kind)
        b.fill(x0 + 1, y, uz0 + 1, x1 - 1, y, z1 - 1, state(f"{wood}_planks"))
        timber_walls(b, x0, x1, uz0, z1, y + 1, y + 3, log_kind, plaster)
        for x in ((x0 + mid_x) // 2, (mid_x + x1) // 2):
            window(b, x, y + 2, uz0, (0, -1), wood)
            window(b, x, y + 2, z1, (0, 1), wood)
        zmid = (uz0 + z1) // 2
        for z in ((uz0 + zmid) // 2, (zmid + z1) // 2):
            window(b, x0, y + 2, z, (-1, 0), wood)
            window(b, x1, y + 2, z, (1, 0), wood)
        floors.append(y)
        y += 4
    ring(b, x0, x1, uz0, z1, y, log_kind)

    if jetty and upper:
        # 튀어나온 2층을 받치는 까치발 + 현관 랜턴
        for x in (x0, mid_x, x1):
            b.set(x, 3, z0 - 1, stairs(wood, "south", "top"))
        for x in (door_x - 1, door_x + 1):
            b.set(x, 3, z0 - 1, state("lantern", hanging=True, waterlogged=False))

    peak = gable_roof(b, x0 - 1, x1 + 1, uz0 - 1, z1 + 1, y, roof, roof_full, roof_slab,
                      (x0, x1), plaster, log_kind, wood)

    # 굴뚝: 뒤쪽 안쪽 모서리에서 지붕 위로
    cx, cz = x1 - 1, z1 - 1
    for cy in range(1, peak + 2):
        b.set(cx, cy, cz, state("bricks"))
    b.set(cx, peak + 2, cz, state("campfire", facing="north", lit=True, signal_fire=False, waterlogged=False))

    # 1층 실내
    b.set(cx - 1, 1, cz, state("furnace", facing="north", lit=False))
    b.set(x0 + 1, 1, z0 + 1, state("barrel", facing="up", open=False))
    b.set(x0 + 2, 1, z1 - 1, state("crafting_table"))
    b.set(mid_x, 1, (z0 + z1) // 2 + 1, state(f"{wood}_fence", east=False, north=False, south=False, waterlogged=False, west=False))
    b.set(mid_x, 2, (z0 + z1) // 2 + 1, state(f"{wood}_pressure_plate", powered=False))

    if floors:
        # 사다리: 서쪽 벽을 따라 꼭대기 층까지
        for ly in range(1, floors[-1] + 1):
            b.set(x0 + 1, ly, z1 - 1, state("ladder", facing="east", waterlogged=False))
        b.set(mid_x, 3, (z0 + z1) // 2, state("lantern", hanging=True, waterlogged=False))
        top = floors[-1] + 1
        b.set(x0 + 2, top, uz0 + 1, state("red_bed", facing="east", occupied=False, part="foot"))
        b.set(x0 + 3, top, uz0 + 1, state("red_bed", facing="east", occupied=False, part="head"))
        b.set(x1 - 1, top, uz0 + 1, state("chest", facing="south", type="single", waterlogged=False))
        b.set(mid_x, top, (uz0 + z1) // 2, state("lantern", hanging=False, waterlogged=False))
        for fy in floors[:-1]:
            b.set(x1 - 2, fy + 1, uz0 + 1, state("bookshelf"))
            b.set(x1 - 3, fy + 1, uz0 + 1, state("bookshelf"))

    if extra:
        extra(b, x0, x1, z0, z1)
    return b.build()


def _bakery_extra(b, x0, x1, z0, z1):
    b.set(x0 + 1, 1, z0 + 2, state("smoker", facing="east", lit=True))
    b.set(x0 + 1, 2, z0 + 1, state("potted_red_tulip"))
    for x in range(x0 + 1, x1):
        b.set(x, 0, z0 - 2, state("dirt_path"))


def _smithy_extra(b, x0, x1, z0, z1):
    # 동쪽 벽에 문, 그 밖으로 반쯤 열린 작업장(처마)
    b.set(x1, 1, 3, state("spruce_door", facing="east", half="lower", hinge="left", open=False, powered=False))
    b.set(x1, 2, 3, state("spruce_door", facing="east", half="upper", hinge="left", open=False, powered=False))
    lx0, lx1 = x1 + 1, x1 + 4
    b.fill(lx0, 0, z0, lx1, 0, z1, state("cobblestone"))
    for z in (z0, 3, z1):
        b.fill(lx1, 1, z, lx1, 3, z, log("spruce_log", "y"))
    for z in range(z0 - 1, z1 + 2):
        for x in range(lx0 + 1, lx1 + 2):
            b.set(x, 4, z, state("spruce_slab", type="top", waterlogged=False))
    b.set(lx0, 1, z0 + 1, state("smithing_table"))
    b.set(lx0 + 1, 1, z0 + 1, state("anvil", facing="east"))
    b.set(lx0 + 2, 1, z0 + 1, state("grindstone", face="floor", facing="north"))
    b.set(lx0, 1, z1 - 1, state("blast_furnace", facing="east", lit=True))
    b.set(lx0 + 1, 1, z1 - 1, state("lava_cauldron"))
    b.set(lx0 + 2, 1, z1 - 1, state("water_cauldron", level=3))
    b.set(lx0 + 2, 3, 3, state("lantern", hanging=True, waterlogged=False))


def medieval_templates():
    return [
        {"name": "반목조 2층 주택", "category": "주거",
         "description": "돌 기초 위에 가문비나무 골조와 흰 회벽을 올린 2층 집. 앞으로 튀어나온 2층, "
                        "덧창과 꽃 화단, 심층암 기와 지붕과 벽돌 굴뚝.",
         "data": medieval_house(9, 8, 1, wood="spruce", log_kind="spruce_log", plaster="calcite",
                                roof="deepslate_tile", roof_full="deepslate_tiles",
                                roof_slab="deepslate_tile_slab")},
        {"name": "마을 빵집", "category": "상업",
         "description": "짙은 참나무 골조와 흰 테라코타 벽의 아담한 빵집. 훈연기와 화분, 가게 앞 흙길.",
         "data": medieval_house(7, 7, 1, wood="dark_oak", log_kind="dark_oak_log",
                                plaster="white_terracotta", roof="dark_oak",
                                roof_full="dark_oak_planks", roof_slab="dark_oak_slab",
                                extra=_bakery_extra)},
        {"name": "중세 여관", "category": "상업",
         "description": "3층 높이의 큰 여관. 층마다 반목조 벽과 창문, 책장이 있는 2층 휴게실, 높은 기와 지붕.",
         "data": medieval_house(13, 9, 2, wood="spruce", log_kind="stripped_spruce_log",
                                plaster="calcite", roof="deepslate_tile",
                                roof_full="deepslate_tiles", roof_slab="deepslate_tile_slab")},
        {"name": "대장간", "category": "상업",
         "description": "돌로 지은 단층 대장간과 옆으로 붙은 작업장 처마. 모루, 숫돌, 용광로, 용암 가마솥.",
         "data": medieval_house(7, 7, 0, wood="spruce", log_kind="spruce_log", plaster="stone_bricks",
                                roof="deepslate_brick", roof_full="deepslate_bricks",
                                roof_slab="deepslate_brick_slab", side_skip=("east",), extra=_smithy_extra)},
    ]
