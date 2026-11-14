"""동양·모던 4종 (건물만, 조경 없음).

레퍼런스: design/references-2026.md (핀터레스트 이미지 관찰) · 매스/재료: Codex 설계안 · 구현: seed_detail.Arch
"""
from seed_detail import Arch, S


# ====================================================================== 1. 벚꽃 찻집
def teahouse():
    k = Arch()
    POST = "dark_oak_log"
    PAPER = S("white_concrete")
    x0, z0, x1, z1 = 3, 3, 17, 13
    # 띄운 기단 + 엔가와(툇마루): 본채 아래만 돌, 툇마루는 짧은 기둥 위
    k.box(x0, 0, z0, x1, 1, z1, S("stone_bricks"))
    k.walls(x0, z0, x1, z1, 0, 1, S("polished_andesite"))
    k.floor(1, 1, 19, 15, 2, S("spruce_planks"))
    for x in range(1, 20, 3):
        for z in (1, 15):
            k.fill(x, 0, z, x, 1, z, S(POST, axis="y"))
    for z in range(1, 16, 3):
        for x in (1, 19):
            k.fill(x, 0, z, x, 1, z, S(POST, axis="y"))
    k.walls(1, 1, 19, 15, 2, 2, S("dark_oak_planks"))
    for x in (9, 10, 11):
        k.set(x, 1, 0, S("stone_brick_stairs", facing="south"))
        k.set(x, 0, -1, S("stone_brick_stairs", facing="south"))
    # 본채: 어두운 기둥 2칸 간격, 창호 판, 허리 들보, 위 들보
    k.walls(x0, z0, x1, z1, 3, 7, PAPER)
    k.frame(x0, z0, x1, z1, 3, 7, POST, beam=True, posts_every=2)
    for x in range(x0, x1 + 1):
        for z in (z0, z1):
            if (x - x0) % 2:
                k.set(x, 5, z, S("stripped_dark_oak_log", axis="x"))
    for z in range(z0, z1 + 1):
        for x in (x0, x1):
            if (z - z0) % 2:
                k.set(x, 5, z, S("stripped_dark_oak_log", axis="z"))
    # 정면: 두 칸 들어간 현관 + 노렌 + 등
    for x in range(9, 12):
        for y in range(3, 6):
            k.set(x, y, z0, None)
            k.set(x, y, z0 + 1, None)
        k.set(x, 6, z0 - 1, S("red_wall_banner", facing="north"))
    for x, hinge in ((9, "left"), (11, "right")):
        k.set(x, 3, z0 + 2, S("cherry_door", facing="north", half="lower", hinge=hinge))
        k.set(x, 4, z0 + 2, S("cherry_door", facing="north", half="upper", hinge=hinge))
    k.set(10, 3, z0 + 2, S("cherry_planks"))
    k.set(10, 4, z0 + 2, S("cherry_planks"))
    for x in (8, 12):
        k.set(x, 3, z0 - 1, S("dark_oak_fence"))
        k.set(x, 4, z0 - 1, S("lantern"))
    # 격자 창(울타리 격자, 한 칸 들어감)
    for z in (5, 7, 9, 11):
        for x, inner in ((x0, x0 + 1), (x1, x1 - 1)):
            k.set(x, 4, z, None)
            k.set(inner, 4, z, S("dark_oak_fence", north=True, south=True))
    for x in (5, 7, 13, 15):
        for z, inner in ((z0, z0 + 1), (z1, z1 - 1)):
            k.set(x, 4, z, None)
            k.set(x, 4, inner, S("dark_oak_fence", east=True, west=True))
    # 아래 처마(치마 지붕): 얇은 처마 + 들린 모서리 + 두 고리
    k.eave_ring(0, 0, 20, 16, 8, "deepslate_tile", kind="slab", horn=True)
    k.eave_ring(1, 1, 19, 15, 8, "deepslate_tile", horn=False)
    k.eave_ring(2, 2, 18, 14, 9, "deepslate_tile", horn=False)
    for x, z in ((1, 1), (19, 1), (1, 15), (19, 15)):
        k.hang(x, 7, z)
    # 위 곡선 박공 + 흰 삼각벽 + 어두운 처마띠 + 용마루 끝 장식
    top = k.curved_gable(x0, x1, z0 - 1, z1 + 1, 10, "deepslate_tile", ridge="x", trim="dark_oak",
                         gable_fill=PAPER, wall_top=8)
    for x in (x0, x1):
        k.set(x, top + 1, 8, S("deepslate_tile_wall"))
    # 실내 바닥(다다미) / 천장 격자 + 트랩도어로 가린 조명
    for x in range(x0 + 1, x1):
        for z in range(z0 + 1, z1):
            k.set(x, 2, z, S("dark_oak_planks") if (x - x0) % 3 == 0 or z in (z0 + 1, z1 - 1) else S("bamboo_mosaic"))
            k.set(x, 8, z, S("stripped_dark_oak_log", axis="x") if (z - z0) % 3 == 0 else S("cherry_slab", type="top"))
    for x, z in ((6, 7), (6, 10), (14, 7), (14, 10)):
        k.set(x, 9, z, S("shroomlight"))
        k.set(x, 8, z, S("cherry_trapdoor", half="top"))
    # 창호 칸막이: 서쪽 접객실 / 동쪽 준비실
    for z in range(z0 + 1, z1):
        if z not in (7, 8, 9):
            k.fill(12, 3, z, 12, 7, z, PAPER)
    k.fill(12, 3, 6, 12, 7, 6, S(POST, axis="y"))
    k.fill(12, 3, 10, 12, 7, 10, S(POST, axis="y"))
    # 접객실: 낮은 탁자, 방석, 찻잔(초), 도코노마(분재·족자)
    k.floor(6, 7, 8, 9, 3, S("dark_oak_slab"))
    for x in range(6, 9):
        k.set(x, 3, 6, S("red_carpet"))
        k.set(x, 3, 10, S("red_carpet"))
    k.set(7, 4, 8, S("white_candle", candles=2, lit=True))
    k.box(6, 3, 12, 8, 3, 12, S("dark_oak_slab", type="top"))
    k.set(7, 4, 12, S("potted_cherry_sapling"))
    k.set(7, 5, 12, S("white_wall_banner", facing="north"))
    k.set(5, 3, 12, S("decorated_pot"))
    # 준비실: 조리대(통 + 벚나무 다락문), 물 가마솥, 선반
    for z in range(5, 12):
        k.set(16, 3, z, S("barrel", facing="west"))
        k.set(16, 4, z, S("cherry_trapdoor", half="bottom", facing="west"))
    k.set(16, 3, 8, S("water_cauldron", level=2))
    k.set(16, 4, 8, None)
    k.shelf_wall(13, 12, 15, 12, 5, "cherry", "north")
    k.set(14, 3, 12, S("decorated_pot"))
    return k.build()


# ====================================================================== 2. 오층 목탑
def pagoda():
    k = Arch()
    PIL = S("stripped_mangrove_log", axis="y")
    WALL = S("calcite")
    ROOF = "oxidized_cut_copper"
    C = 9
    # 두 단 기단 + 계단
    k.box(0, 0, 0, 18, 0, 18, S("stone_bricks"))
    k.box(2, 1, 2, 16, 1, 16, S("polished_andesite"))
    for x in (8, 9, 10):
        k.set(x, 0, -1, S("stone_brick_stairs", facing="south"))
        k.set(x, 1, 1, S("polished_andesite_stairs", facing="south"))
    tiers = [(5, 13, 5), (6, 12, 4), (6, 12, 4), (7, 11, 4), (7, 11, 4)]
    floors = []
    y = 2
    for t, (a, b, h) in enumerate(tiers):
        floors.append(y)
        # 몸체: 흰 벽 + 벽 밖으로 한 칸 나온 붉은 기둥(모서리 + 가운데 양옆)
        k.walls(a, a, b, b, y, y + h - 1, WALL)
        for c in (a, C - 1, C + 1, b):
            for d in (a - 1, b + 1):
                k.fill(c, y, d, c, y + h - 1, d, PIL)
                k.fill(d, y, c, d, y + h - 1, c, PIL)
        # 기둥 위 까치발(처마 받침, 한 칸 더 바깥)
        for c in range(a - 1, b + 2):
            k.set(c, y + h - 1, a - 2, S("dark_oak_stairs", facing="south", half="top"))
            k.set(c, y + h - 1, b + 2, S("dark_oak_stairs", facing="north", half="top"))
            k.set(a - 2, y + h - 1, c, S("dark_oak_stairs", facing="east", half="top"))
            k.set(b + 2, y + h - 1, c, S("dark_oak_stairs", facing="west", half="top"))
        k.floor(a, a, b, b, y - 1, S("dark_oak_planks"))
        if t == 0:
            k.set(C, y, a - 1, None)
            k.set(C, y + 1, a - 1, None)
            k.door(C, y, a, "dark_oak")
        else:
            for p, along in (((C, y + 1, a), "x"), ((C, y + 1, b), "x"), ((a, y + 1, C), "z"), ((b, y + 1, C), "z")):
                k.set(*p, S("dark_oak_fence", **({"east": True, "west": True} if along == "x" else {"north": True, "south": True})))
        # 처마: 얇은 반블록 처마 + 들린 뿔 모서리 + 안쪽 고리들
        top = y + h
        off = 4
        k.eave_ring(a - off, a - off, b + off, b + off, top, ROOF, kind="slab", horn=True)
        k.eave_ring(a - off + 1, a - off + 1, b + off - 1, b + off - 1, top, ROOF, horn=False)
        k.eave_ring(a - off + 2, a - off + 2, b + off - 2, b + off - 2, top + 1, ROOF, horn=False)
        k.eave_ring(a - 1, a - 1, b + 1, b + 1, top + 2, ROOF, horn=False)
        for cx, cz in ((a - off, a - off), (b + off, a - off), (a - off, b + off), (b + off, b + off)):
            k.hang(cx, top - 1, cz)
        k.floor(a, a, b, b, top + 2, S("dark_oak_planks"))
        if t < len(tiers) - 1:
            na, nb = tiers[t + 1][0], tiers[t + 1][1]
            k.floor(na - 2, na - 2, nb + 2, nb + 2, top + 2, S("dark_oak_planks"))
            k.walls(na - 2, na - 2, nb + 2, nb + 2, top + 3, top + 3,
                    S("mangrove_fence", north=True, south=True, east=True, west=True))
        y = top + 3
    # 꼭대기 들림 모임지붕 + 상륜(금·사슬·피뢰침)
    peak, _ = k.flared_hip(3, 3, 15, 15, y, ROOF, until=1)
    k.set(C, peak, C, S(ROOF))
    k.set(C, peak + 1, C, S("gold_block"))
    for i in range(2, 5):
        k.set(C, peak + i, C, S("iron_chain", axis="y"))
    k.set(C, peak + 5, C, S("lightning_rod", facing="up"))
    # 실내: 중심 기둥 + 사다리, 층별 용도(참배실/서고/명상실/종실/전망실), 숨긴 조명
    k.fill(C, 2, C, C, y - 1, C, PIL)
    for fy in floors[1:]:
        k.set(C + 2, fy - 1, C + 1, None)
    for yl in range(2, y):
        k.set(C + 2, yl, C + 1, S("ladder", facing="east")) if k.cells.get((C + 1, yl, C + 1)) is None else None
    k.fill(C + 1, 2, C + 1, C + 1, y - 1, C + 1, S("dark_oak_planks"))
    f0, f1, f2, f3, f4 = floors
    k.box(7, f0, 12, 11, f0, 12, S("dark_oak_slab", type="top"))
    k.set(9, f0 + 1, 12, S("decorated_pot"))
    for x in (7, 11):
        k.set(x, f0 + 1, 12, S("red_candle", candles=3, lit=True))
    k.rug(7, 7, 8, 10, f0, "red", border="yellow")
    k.set(6, f0, 6, S("barrel", facing="up"))
    k.shelf_wall(7, 7, 7, 11, f1 + 1, "mangrove", "east")
    k.set(8, f1, 11, S("chiseled_bookshelf", facing="north"))
    k.set(8, f1, 7, S("lectern", facing="south"))
    for x in (8, 10):
        k.set(x, f2, 7, S("red_carpet"))
        k.set(x, f2, 11, S("red_carpet"))
    k.set(8, f3 + 3, 9, S("dark_oak_planks"))
    k.set(8, f3 + 2, 9, S("bell", attachment="ceiling", facing="north"))
    for fy in floors:
        k.set(C - 2, fy + 3, C - 2, S("shroomlight"))
    return k.build()


# ====================================================================== 3. 모던 화이트 빌라
def modern_villa():
    k = Arch()
    W, G, D = S("white_concrete"), S("light_gray_concrete"), S("gray_concrete")
    GL = "glass_pane"
    k.floor(3, 4, 21, 18, 0, S("smooth_stone"))
    # 1층 유리 거실동: 돌출된 회색 세로 띠, 유리는 한 칸 뒤
    k.walls(3, 9, 18, 18, 1, 5, W)
    for x in range(4, 18):
        for y in range(1, 5):
            k.set(x, y, 9, None)
            k.set(x, y, 10, S(GL, east=True, west=True))
    for x in (3, 6, 9, 12, 15, 18):
        k.fill(x, 1, 8, x, 5, 8, D)
    for z in range(11, 18):
        for y in (2, 3, 4):
            if z % 3:
                k.set(18, y, z, S(GL, north=True, south=True))
    # 현관동: 낮은 상자 + 나무 기둥 + 세로 루버
    k.walls(3, 5, 8, 8, 1, 4, W)
    k.floor(2, 4, 9, 9, 5, D)
    k.door(5, 1, 5, "dark_oak")
    k.set(5, 1, 10, None)
    k.set(5, 2, 10, None)
    k.door(5, 1, 10, "dark_oak")
    k.clear(5, 1, 8, 5, 2, 9)
    k.set(5, 3, 5, S(GL, east=True, west=True))
    k.box(6, 1, 5, 7, 4, 5, S("stripped_spruce_wood", axis="y"))
    for x in (3, 7):
        for y in (1, 2, 3, 4):
            k.set(x, y, 4, S("spruce_trapdoor", facing="north", open=True))
    # 2층: 북쪽 2칸·동쪽 3칸 튀어나온 흰 상자, 띠창, 동쪽 통유리, 동남쪽 기둥 하나, 나무 루버
    k.walls(9, 7, 21, 18, 6, 10, W)
    k.floor(9, 7, 21, 18, 6, G)
    for x in range(10, 21):
        for y in (7, 8, 9):
            k.set(x, y, 7, None)
            k.set(x, y, 8, S("black_stained_glass_pane", east=True, west=True) if x % 4 == 0 else S(GL, east=True, west=True))
    for z in range(8, 18):
        for y in (7, 8, 9):
            k.set(21, y, z, S(GL, north=True, south=True))
    k.fill(21, 1, 18, 21, 5, 18, D)
    for x in range(17, 21, 2):
        for y in range(6, 11):
            k.set(x, y, 6, S("spruce_trapdoor", facing="north", open=True))
    # 지붕: 얇은 반블록 차양 + 안쪽 높은 덮개 + 천창
    k.floor(8, 6, 22, 19, 11, S("smooth_quartz_slab"))
    k.floor(10, 9, 19, 16, 12, W)
    k.floor(11, 10, 18, 15, 13, S("smooth_quartz_slab"))
    for x in range(12, 18, 2):
        k.set(x, 12, 9, S("glass"))
    # 1층 지붕 테라스(서쪽): 유리 난간 + 화분
    k.floor(3, 9, 8, 18, 6, S("smooth_quartz"))
    for z in range(9, 19):
        k.set(3, 7, z, S(GL, north=True, south=True))
    for x in range(3, 9):
        k.set(x, 7, 18, S(GL, east=True, west=True))
    k.set(4, 7, 10, S("potted_bamboo"))
    k.set(4, 7, 17, S("potted_azalea_bush"))
    # 1층 실내: 거실 / 주방 / 식탁, 천장 매입 조명
    k.floor(4, 10, 17, 17, 0, S("smooth_quartz"))
    k.rug(4, 11, 8, 15, 1, "light_gray", border="gray")
    for z in range(11, 15):
        k.chair(4, 1, z, "quartz", "west")
    for x in range(5, 8):
        k.chair(x, 1, 15, "quartz", "south")
    k.set(6, 1, 12, S("dark_oak_trapdoor", half="top"))
    k.set(6, 2, 12, S("potted_fern"))
    for x in range(11, 15):
        k.set(x, 1, 13, S("barrel", facing="north"))
        k.set(x, 2, 13, S("smooth_quartz_slab"))
    for x in (11, 14):
        k.set(x, 1, 12, S("dark_oak_stairs", facing="south"))
    for x in range(11, 18):
        k.set(x, 1, 17, S("smoker", facing="north") if x == 13 else S("water_cauldron", level=3) if x == 15 else S("dark_oak_planks"))
        k.set(x, 2, 17, S("smooth_quartz_slab")) if x != 15 else None
        k.set(x, 4, 17, S("dark_oak_trapdoor", facing="north", half="top", open=True))
    k.table(16, 1, 11, "dark_oak")
    k.chair(16, 1, 12, "dark_oak", "south")
    k.chair(17, 1, 11, "dark_oak", "east")
    for x, z in ((6, 13), (12, 15), (15, 11), (9, 12)):
        k.set(x, 5, z, S("ochre_froglight", axis="y"))
    for i in range(5):  # 계단: 2층 안쪽 x=10, 남→북으로 오름
        k.set(10, 1 + i, 17 - i, S("smooth_quartz_stairs", facing="north"))
        for yy in range(1, 1 + i):
            k.set(10, yy, 17 - i, S("smooth_quartz"))
    k.clear(10, 6, 13, 10, 7, 17)
    # 2층 실내: 침실 / 서재 / 욕실
    k.floor(10, 8, 20, 17, 6, S("pale_oak_planks"))
    k.clear(10, 6, 13, 10, 7, 17)  # 계단 구멍(바닥을 깐 뒤 다시 뚫기)
    k.bed(18, 7, 12, "white", "east")
    k.bed(18, 7, 13, "white", "east")
    k.set(20, 7, 11, S("pale_oak_trapdoor", half="top"))
    k.set(20, 8, 11, S("white_candle", candles=1, lit=True))
    k.set(20, 7, 14, S("pale_oak_trapdoor", half="top"))
    k.rug(15, 10, 20, 15, 7, "light_gray")
    k.shelf_wall(11, 9, 14, 9, 8, "pale_oak", "south")
    k.set(12, 7, 11, S("pale_oak_trapdoor", half="top"))
    k.chair(12, 7, 12, "pale_oak", "south")
    k.set(13, 7, 11, S("lectern", facing="south"))
    k.set(16, 7, 17, S("water_cauldron", level=3))
    k.set(17, 7, 17, S("water_cauldron", level=3))
    k.set(18, 7, 17, S("smooth_quartz"))
    for x, z in ((12, 13), (18, 10), (16, 15)):
        k.set(x, 10, z, S("pearlescent_froglight", axis="y"))
    return k.build()


# ====================================================================== 4. 모퉁이 카페
def corner_cafe():
    k = Arch()
    brick = Arch.grad([S("bricks"), S("bricks"), S("mud_bricks")], 1, 12, jitter=0.15)
    x0, z0, x1, z1 = 0, 0, 14, 11
    k.floor(x0, z0, x1, z1, 0, S("polished_andesite"))
    k.walls(x0, z0, x1, z1, 1, 11, brick)
    # 1층 가게 정면: 유리 한 칸 뒤 + 흑암 돌출 기둥 + 어두운 간판 띠
    for x in range(1, 14):
        for y in (1, 2, 3):
            k.set(x, y, z0, None)
            k.set(x, y, z0 + 1, S("glass_pane", east=True, west=True))
        k.set(x, 4, z0, S("dark_oak_planks"))
        k.set(x, 5, z0, S("dark_oak_planks"))
        if x not in (6, 7, 8):
            k.set(x, 1, z0 + 1, S("dark_oak_planks"))
    for x in (0, 5, 9, 14):
        k.pilaster(x, z0, "north", 1, 5, S("polished_blackstone_bricks"), base="polished_blackstone_brick",
                   cap="polished_blackstone_brick")
    k.clear(6, 1, z0 + 1, 8, 3, z0 + 1)
    k.double_door(6, 1, z0 + 2, "dark_oak")
    k.set(8, 1, z0 + 2, S("dark_oak_planks"))
    k.set(8, 2, z0 + 2, S("dark_oak_planks"))
    # 줄무늬 차양: 위는 양털, 앞은 같은 색 카펫을 트랩도어 위에 → 두 단 경사
    for x in range(1, 14):
        c = "red" if x % 2 else "white"
        k.set(x, 4, z0 - 1, S(f"{c}_wool"))
        k.set(x, 3, z0 - 2, S("dark_oak_trapdoor", half="top", facing="south"))
        k.set(x, 4, z0 - 2, S(f"{c}_carpet"))
    # 2·3층: 들어간 창 + 인방 + 창턱 + 화단 / 동쪽 창은 덧창
    for x, w in ((2, 2), (6, 3), (11, 2)):
        k.recessed_window(x, 7, z0, "north", w=w, h=2, lintel="brick", sill="brick",
                          box=S("flowering_azalea_leaves", persistent=True, distance=1))
        k.recessed_window(x, 10, z0, "north", w=w, h=1, lintel="brick", sill="brick")
    for z in (3, 7):
        k.recessed_window(x1, 7, z, "east", w=2, h=2, lintel="brick", sill="brick", shutter="dark_oak")
        k.recessed_window(x1, 2, z, "east", w=2, h=2, lintel="brick", sill="brick")
    for z in range(3, 9):  # 서쪽 쇼윈도
        for y in (2, 3):
            k.set(x0, y, z, None)
            k.set(x0 + 1, y, z, S("glass_pane", north=True, south=True))
        k.set(x0 - 1, 1, z, S("brick_stairs", facing="east"))
    for x in (2, 6, 11):
        k.recessed_window(x, 7, z1, "south", w=1, h=2, lintel="brick", sill="brick")
    # 층 띠 + 지붕 코니스 + 난간
    k.cornice(x0, z0, x1, z1, 6, "brick", half="top")
    k.cornice(x0, z0, x1, z1, 12, "polished_blackstone_brick", half="top")
    k.walls(x0, z0, x1, z1, 12, 12, S("brick_wall"))
    # 모서리 탑(정면 동쪽): 돌출 4×4 + 모임 지붕 + 피뢰침
    k.walls(12, -3, 15, 0, 6, 12, brick)
    for y in (8, 11):
        k.set(13, y, -3, S("glass_pane", east=True, west=True))
        k.set(14, y, -3, S("glass_pane", east=True, west=True))
        k.set(15, y, -2, S("glass_pane", north=True, south=True))
    for x in range(12, 16):
        k.set(x, 5, -3, S("brick_stairs", facing="south", half="top"))
    k.hip(11, 16, -4, 1, 13, "deepslate_tile")
    k.set(13, 16, -2, S("lightning_rod", facing="up"))
    # 옥상: 굴뚝 + 채광창
    k.floor(1, 1, 13, 10, 11, S("smooth_stone"))
    k.fill(2, 12, 9, 3, 15, 10, S("bricks"))
    k.set(2, 16, 9, S("campfire", lit=True))
    k.set(3, 16, 10, S("brick_slab"))
    k.fill(6, 11, 5, 8, 11, 6, S("glass"))
    # 1층 실내: 체크무늬 바닥, 카운터(케이크·양조대·진열 유리), 수납, 손님 탁자, 숨긴 조명
    for x in range(1, 14):
        for z in range(2, 11):
            k.set(x, 0, z, S("white_concrete") if (x + z) % 2 else S("black_concrete"))
    for x in range(7, 13):
        k.set(x, 1, 7, S("dark_oak_planks"))
        k.set(x, 2, 7, S("smooth_quartz_slab"))
    k.set(8, 2, 7, S("cake"))
    k.set(10, 2, 7, S("brewing_stand"))
    k.set(12, 2, 7, S("glass"))
    for x in range(7, 13):
        k.set(x, 1, 10, S("smoker", facing="south") if x == 9 else S("barrel", facing="south"))
        k.set(x, 3, 10, S("spruce_shelf", facing="south"))
    for x, z in ((3, 4), (3, 7)):
        k.table(x, 1, z, "dark_oak")
        k.chair(x, 1, z - 1, "dark_oak", "north") if z == 4 else None
        k.chair(x - 1, 1, z, "dark_oak", "west")
        k.chair(x + 1, 1, z, "dark_oak", "east")
    k.set(1, 1, 10, S("potted_fern"))
    for x, z in ((4, 5), (10, 4), (10, 9)):
        k.set(x, 5, z, S("shroomlight"))
    # 2층 주인집 / 3층 다락 작업실
    k.floor(1, 1, 13, 10, 6, S("spruce_planks"))
    k.floor(1, 1, 13, 10, 9, S("spruce_planks"))
    for i in range(5):
        k.set(1 + i, 1 + i, 9, S("spruce_stairs", facing="east"))
        for yy in range(1, 1 + i):
            k.set(1 + i, yy, 9, S("spruce_planks"))
    k.clear(3, 6, 9, 5, 6, 10)
    for i in range(3):
        k.set(9 + i, 7 + i, 9, S("spruce_stairs", facing="east"))
    k.clear(10, 9, 9, 12, 9, 10)
    k.bed(11, 7, 2, "brown", "south")
    k.rug(2, 2, 6, 5, 7, "brown", border="orange")
    for x in (2, 3, 4):
        k.chair(x, 7, 2, "spruce", "north")
    k.set(5, 7, 2, S("spruce_trapdoor", half="top"))
    k.set(5, 8, 2, S("potted_red_tulip"))
    k.shelf_wall(13, 4, 13, 6, 8, "spruce", "west")
    k.set(4, 10, 3, S("crafting_table"))
    k.set(5, 10, 3, S("loom", facing="north"))
    k.bed(10, 10, 3, "orange", "south")
    k.hang(7, 8, 5)
    k.hang(7, 10, 5) if False else None
    return k.build()


def east_templates():
    return [
        {"name": "벚꽃 찻집", "category": "동양",
         "description": "기둥 위에 띄운 툇마루와 들린 모서리 처마, 오목하게 휘는 박공 지붕의 일본식 찻집. 들어간 현관의 노렌과 등. 다다미 접객실의 낮은 탁자와 도코노마, 창호 칸막이 너머 준비실.",
         "data": teahouse()},
        {"name": "오층 목탑", "category": "동양",
         "description": "벽 밖으로 나온 붉은 기둥과 까치발, 층마다 얇게 뜨고 모서리가 들린 청록 구리 처마. 1층 참배실부터 서고·명상실·종실·전망실까지 중심 기둥을 따라 오른다.",
         "data": pagoda()},
        {"name": "모던 화이트 빌라", "category": "모던",
         "description": "돌출된 회색 세로 띠 뒤로 물러난 유리 거실, 북·동쪽으로 튀어나온 2층 흰 상자와 기둥 하나, 나무 루버와 두 단 평지붕. 아일랜드 주방, 침실·서재·욕실.",
         "data": modern_villa()},
        {"name": "모퉁이 카페", "category": "상업",
         "description": "흑암 기둥 사이 큰 가게 창과 두 단 줄무늬 차양, 인방·창턱이 있는 들어간 창, 층 띠와 코니스, 모서리 탑. 체크무늬 바닥 카페, 위층 주인집과 다락 작업실.",
         "data": corner_cafe()},
    ]
