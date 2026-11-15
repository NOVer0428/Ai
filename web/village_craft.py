"""구리·고딕·판타지 5종 (건물만, 조경 없음).

매스/재료: Codex 설계안 · 디테일: 핀터레스트 관찰(design/references-2026.md) · 구현: seed_detail.Arch
"""
from seed_detail import Arch, S, h3, math
from seed_kit import mix

COPPER_STAGES = ["waxed_cut_copper", "waxed_exposed_cut_copper", "waxed_weathered_cut_copper",
                 "waxed_oxidized_cut_copper"]


def copper_stage(z, z0, z1):
    t = (z - z0) / max(1, z1 - z0)
    return COPPER_STAGES[min(3, int(t * 4))]


# ====================================================================== 5. 구리 증기 공방
def copper_workshop():
    k = Arch()
    tuff = Arch.grad([S("polished_tuff"), S("tuff_bricks"), S("tuff_bricks"), S("chiseled_tuff_bricks")], 1, 8, 0.2)
    PIL = S("waxed_copper_block")
    k.floor(2, 5, 19, 15, 0, S("polished_tuff"))
    # 작업장 몸체 + 돌출 구리 기둥 + 처마띠
    k.walls(2, 5, 13, 15, 1, 8, tuff)
    for x in (2, 6, 9, 13):
        k.pilaster(x, 5, "north", 1, 8, PIL, base="waxed_cut_copper", cap="waxed_cut_copper")
    for z in (5, 10, 15):
        k.pilaster(2, z, "west", 1, 8, PIL, base="waxed_cut_copper", cap="waxed_cut_copper")
    k.cornice(2, 5, 13, 15, 8, "waxed_cut_copper", half="top")
    # 정면: 아치 이중문 + 위 둥근 톱니 창 + 양옆 아치 창
    k.clear(7, 1, 5, 8, 3, 5)
    k.double_door(7, 1, 6, "waxed_copper")
    k.set(7, 3, 5, S("waxed_cut_copper_stairs", facing="west", half="top"))
    k.set(8, 3, 5, S("waxed_cut_copper_stairs", facing="east", half="top"))
    k.round_window(7, 6, 5, "x", 1, S("waxed_exposed_cut_copper"), S("glass_pane", east=True, west=True))
    k.round_window(8, 6, 5, "x", 1, S("waxed_exposed_cut_copper"), S("glass_pane", east=True, west=True))
    for x in (4, 11):
        k.arch_window(x, 2, 5, "north", 1, 3, "glass_pane", "waxed_cut_copper")
    for z in (8, 12):
        k.arch_window(2, 2, z, "west", 1, 4, "glass_pane", "waxed_cut_copper")
        k.arch_window(13, 2, z, "east", 1, 4, "glass_pane", "waxed_cut_copper")
    k.set(7, 4, 4, S("waxed_copper_bulb", lit=True))
    k.set(8, 4, 4, S("waxed_copper_bulb", lit=True))
    # 톱니 지붕 3구간: 서→동 경사 + 동쪽 수직 채광 유리, 북→남 구리 산화 그라데이션
    for sx in (2, 6, 10):
        for z in range(5, 16):
            mat = copper_stage(z, 5, 15)
            for i in range(3):
                k.set(sx + i, 9 + i, z, S(f"{mat}_stairs", facing="east"))
            k.set(sx + 3, 12, z, S(f"{mat}_slab"))
            for y in (9, 10, 11):
                k.set(sx + 3, y, z, PIL if z in (5, 15) else S("glass_pane", north=True, south=True))
        for z in (5, 15):
            for i in range(3):
                for y in range(9, 9 + i):
                    k.set(sx + i, y, z, tuff(sx + i, y, z))
    # 보일러실 + 지붕 위 둥근 물탱크 + 굴뚝
    k.walls(14, 8, 19, 14, 1, 10, S("waxed_copper_block"))
    k.walls(14, 8, 19, 14, 1, 2, tuff)
    k.cornice(14, 8, 19, 14, 10, "waxed_exposed_cut_copper", half="top")
    k.floor(15, 9, 18, 13, 10, S("waxed_copper_grate"))
    k.cylinder(16, 10, 2, 11, 14, S("waxed_exposed_copper"))
    for dx, dz in k.disc(2):
        k.set(16 + dx, 15, 10 + dz, S("waxed_exposed_cut_copper_slab"))
    k.walls(17, 12, 19, 14, 11, 19, S("bricks"))
    k.walls(16, 11, 20, 15, 20, 20, S("waxed_oxidized_cut_copper_slab"))
    k.set(18, 19, 13, S("campfire", lit=True))
    for x in (4, 8):
        k.fill(x, 9, 15, x, 15, 15, S("bricks"))
        k.set(x, 16, 15, S("waxed_oxidized_cut_copper_slab"))
        k.set(x, 15, 15, S("campfire", lit=True))
    # 톱니바퀴 장식(보일러 정면) + 배관(가는 관 = 피뢰침 눕힘)
    for dx, dy in ((0, 2), (1, 2), (2, 1), (2, 0), (1, -1), (0, -1), (-1, 0), (-1, 1)):
        k.set(16 + dx, 6 + dy, 7, S("waxed_exposed_cut_copper"))
    k.set(16, 6, 7, S("waxed_copper_bulb", lit=True))
    k.fill(15, 1, 3, 15, 7, 3, S("waxed_cut_copper"))
    for z in range(3, 8):
        k.set(15, 8, z, S("lightning_rod", facing="south"))
    for x in range(14, 20):
        k.set(x, 4, 7, S("lightning_rod", facing="east")) if x not in (15, 16, 17) else None
    k.fill(20, 1, 9, 20, 7, 9, S("waxed_exposed_cut_copper"))
    for z in range(10, 14):
        k.set(20, 7, z, S("lightning_rod", facing="south"))
    # 실내: 크래프터 작업대 줄, 구리 상자, 공구 선반, 모루, 구리 골렘 조각상, 천장 전구
    k.floor(3, 6, 12, 14, 0, S("polished_tuff"))
    for x in range(3, 12, 2):
        k.set(x, 1, 14, S("crafter", orientation="north_up"))
        if x < 11:
            k.set(x + 1, 1, 14, S("waxed_copper_chest", facing="north"))
    k.shelf_wall(3, 14, 12, 14, 3, "spruce", "north")
    for x in (5, 9):
        k.set(x, 1, 10, S("smithing_table"))
        k.set(x + 1, 1, 10, S("anvil", facing="east"))
        k.set(x - 1, 1, 10, S("grindstone", face="floor", facing="north"))
    k.set(12, 1, 6, S("waxed_copper_golem_statue", facing="west"))
    k.rug(6, 7, 9, 8, 1, "orange")
    for x, z in ((4, 8), (8, 8), (11, 8), (4, 12), (8, 12), (11, 12)):
        k.set(x, 8, z, S("waxed_copper_bulb", lit=True))
    k.floor(15, 9, 18, 13, 0, S("polished_tuff"))
    for z in (9, 10, 11):
        k.set(18, 1, z, S("blast_furnace", facing="west", lit=True))
    k.set(15, 1, 13, S("lava_cauldron"))
    k.set(16, 1, 13, S("water_cauldron", level=3))
    k.set(15, 1, 9, S("copper_lantern"))
    k.clear(13, 1, 10, 14, 2, 11)
    return k.build()


# ====================================================================== 6. 구리 시계탑
def clock_tower():
    k = Arch()
    body = Arch.grad([S("polished_tuff"), S("tuff_bricks"), S("tuff_bricks")], 1, 21, 0.15)
    k.floor(2, 4, 14, 16, 0, S("polished_tuff"))
    for x in (6, 7, 8, 9, 10):
        k.set(x, 0, 3, S("polished_tuff_stairs", facing="south"))

    def octagon(x0, z0, x1, z1, y0, y1, blk, cut=2):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                for z in range(z0, z1 + 1):
                    dx, dz = min(x - x0, x1 - x), min(z - z0, z1 - z)
                    if dx + dz < cut:
                        continue
                    if dx == 0 or dz == 0 or dx + dz == cut:
                        k.set(x, y, z, blk(x, y, z) if callable(blk) else blk)
    octagon(4, 6, 12, 14, 1, 13, body)
    octagon(5, 7, 11, 13, 14, 21, body)
    for x in range(4, 13):
        for z in range(6, 15):
            if (x in (4, 12) or z in (6, 14)) and k.cells.get((x, 13, z)):
                k.set(x, 14, z, S("tuff_brick_slab"))
    # 구리 세로 띠(대각 면) + 한 칸 돌출 수평 띠
    for (x, z) in ((5, 7), (11, 7), (5, 13), (11, 13)):
        k.fill(x, 1, z, x, 21, z, S("waxed_copper_block"))
    for y in (8, 14):
        for x in range(6, 11):
            k.set(x, y, 5, S("waxed_cut_copper_stairs", facing="south", half="top"))
            k.set(x, y, 15, S("waxed_cut_copper_stairs", facing="north", half="top"))
        for z in range(8, 13):
            k.set(3, y, z, S("waxed_cut_copper_stairs", facing="east", half="top"))
            k.set(13, y, z, S("waxed_cut_copper_stairs", facing="west", half="top"))
    # 세로 아치 창 + 정면 아치 문
    for y0 in (10, 16):
        k.arch_window(8, y0, 6, "north", 1, 3, "glass_pane", "tuff_brick")
        k.arch_window(4, y0, 10, "west", 1, 3, "glass_pane", "tuff_brick")
        k.arch_window(12, y0, 10, "east", 1, 3, "glass_pane", "tuff_brick")
    k.clear(7, 1, 6, 9, 3, 6)
    k.double_door(7, 1, 7, "waxed_copper")
    k.set(9, 1, 7, S("tuff_bricks"))
    k.set(7, 3, 6, S("tuff_brick_stairs", facing="west", half="top"))
    k.set(9, 3, 6, S("tuff_brick_stairs", facing="east", half="top"))
    k.set(8, 4, 5, S("waxed_copper_bulb", lit=True))
    # 시계실(머리): 몸체보다 넓게 + 처마띠 + 네 면 둥근 시계판(구리 테두리·흰 판·검은 바늘·전구 중심)
    k.walls(3, 5, 13, 15, 20, 28, S("waxed_copper_block"))
    k.cornice(3, 5, 13, 15, 20, "waxed_cut_copper", half="top")
    k.cornice(3, 5, 13, 15, 28, "waxed_cut_copper", half="top")
    face = S("white_concrete")
    for plane, axis in ((5, "x"), (15, "x"), (3, "z"), (13, "z")):
        k.round_window(8 if axis == "x" else 10, 24, plane, axis, 3, S("waxed_exposed_cut_copper"), face)
        c = 8 if axis == "x" else 10
        for d, dy in ((0, 1), (0, 2), (1, 0), (2, 0)):
            p = (c + d, 24 + dy, plane) if axis == "x" else (plane, 24 + dy, c + d)
            k.set(*p, S("black_concrete"))
        p = (c, 24, plane) if axis == "x" else (plane, 24, c)
        k.set(*p, S("waxed_copper_bulb", lit=True))
        for d, dy in ((0, 3), (0, -3), (3, 0), (-3, 0)):
            p = (c + d, 24 + dy, plane) if axis == "x" else (plane, 24 + dy, c + d)
            k.set(*p, S("waxed_oxidized_copper"))
    # 지붕: 산화 구리 들림 모임지붕 + 첨탑 + 모서리 작은 첨탑 넷
    k.eave_ring(2, 4, 14, 16, 29, "waxed_oxidized_cut_copper", kind="slab", horn=False)
    peak = k.spire(8, 10, 5, 29, "waxed_oxidized_cut_copper", rise=2, tip=S("lightning_rod", facing="up"))
    for x, z in ((3, 5), (13, 5), (3, 15), (13, 15)):
        k.set(x, 29, z, S("waxed_oxidized_copper"))
        k.set(x, 30, z, S("lightning_rod", facing="up"))
    # 관리실(서쪽 앞) + 곡선 지붕
    k.floor(-1, 3, 4, 9, 0, S("polished_tuff"))
    k.walls(-1, 3, 4, 9, 1, 5, body)
    k.floor(0, 4, 3, 8, 6, S("spruce_planks"))
    k.frame(-1, 3, 4, 9, 1, 5, "stripped_spruce_log")
    k.curved_gable(-2, 5, 2, 10, 6, "waxed_exposed_cut_copper", ridge="x", gable_fill=S("tuff_bricks"), wall_top=6)
    k.door(1, 1, 3, "spruce")
    k.recessed_window(3, 2, 3, "north", w=1, h=2, lintel="tuff_brick", sill="tuff_brick")
    k.recessed_window(-1, 2, 6, "west", w=2, h=2, lintel="tuff_brick", sill="tuff_brick")
    # 실내: 관리실(독서대·선반·책상) / 탑(층마다 바닥, 사다리) / 기계실(관측기·비교기·종)
    k.floor(0, 4, 3, 8, 0, S("spruce_planks"))
    k.clear(4, 1, 7, 4, 2, 7)
    k.set(0, 1, 8, S("lectern", facing="east"))
    k.shelf_wall(0, 4, 0, 6, 2, "spruce", "east")
    k.set(2, 1, 7, S("spruce_trapdoor", half="top"))
    k.chair(2, 1, 6, "spruce", "north")
    k.hang(1, 5, 6, "copper_lantern")
    for yy in range(4, 20, 5):
        k.floor(5, 7, 11, 13, yy, S("spruce_planks"))
    for yy in range(1, 21):
        k.set(8, yy, 13 if yy <= 13 else 12, S("ladder", facing="north"))
    k.rug(6, 8, 8, 10, 1, "orange", border="brown")
    k.set(6, 1, 12, S("waxed_copper_chest", facing="east"))
    k.floor(4, 6, 12, 14, 20, S("waxed_copper_grate"))
    k.set(8, 20, 12, S("ladder", facing="north"))  # 바닥을 깐 뒤 사다리 구멍 다시
    for x in range(6, 11):
        k.set(x, 21, 9, S("observer", facing="north"))
        k.set(x, 21, 11, S("comparator", facing="south"))
    k.set(10, 21, 13, S("bell", attachment="floor", facing="north"))
    for x, z in ((5, 7), (11, 7), (5, 13), (11, 13)):
        k.set(x, 27, z, S("waxed_copper_bulb", lit=True))
    return k.build()


# ====================================================================== 7. 창백한 정원 예배당 (고딕)
def pale_chapel():
    k = Arch()
    stone = Arch.grad([S("mossy_stone_bricks"), S("tuff_bricks"), S("tuff_bricks"), S("polished_tuff")], 1, 12, 0.25)
    PALE, PLOG = S("pale_oak_planks"), S("pale_oak_log", axis="y")
    k.floor(5, 3, 15, 24, 0, S("polished_tuff"))
    # 본당: 돌벽 + 버팀벽(계단식 머리 + 작은 첨탑)
    k.walls(6, 8, 14, 21, 1, 11, stone)
    for z in (8, 11, 14, 17, 21):
        for x, out in ((6, "west"), (14, "east")):
            ox = -1 if out == "west" else 1
            k.fill(x + ox, 1, z, x + ox, 8, z, stone)
            k.fill(x + 2 * ox, 1, z, x + 2 * ox, 5, z, stone)
            k.set(x + 2 * ox, 6, z, S("tuff_brick_stairs", facing="east" if out == "west" else "west"))
            k.set(x + ox, 9, z, S("tuff_brick_stairs", facing="east" if out == "west" else "west"))
            k.set(x + ox, 10, z, S("tuff_brick_wall"))
            k.set(x + ox, 11, z, S("lightning_rod", facing="up"))
    # 뾰족 아치 창(창백한 참나무 창살 느낌의 회색 유리) 3칸 폭 × 6칸
    for z in (9, 12, 15, 18):
        k.arch_window(6, 3, z, "west", 2, 5, "gray_stained_glass_pane", "resin_brick")
        k.arch_window(14, 3, z, "east", 2, 5, "gray_stained_glass_pane", "resin_brick")
    # 가파른 지붕(용마루 z, 정면 박공) + 수지 처마띠
    k.gable(5, 15, 7, 22, 12, "deepslate_tile", ridge="z", gable_fill=stone(10, 13, 7), trim="resin_brick")
    # 정면 탑: 본당 앞 가운데, 정문 + 장미창 + 가파른 첨탑 + 모서리 첨탑
    k.walls(7, 3, 13, 8, 1, 20, stone)
    for x, z in ((7, 3), (13, 3), (7, 8), (13, 8)):
        k.fill(x, 1, z, x, 20, z, S("polished_tuff"))
    k.cornice(7, 3, 13, 8, 12, "tuff_brick", half="top")
    k.cornice(7, 3, 13, 8, 20, "tuff_brick", half="top")
    # 정문: 깊은 뾰족 아치(두 겹) + 창백한 참나무 문
    for d in (3, 4):
        k.clear(9, 1, d, 11, 4, d)
    k.set(9, 4, 3, S("resin_brick_stairs", facing="west", half="top"))
    k.set(11, 4, 3, S("resin_brick_stairs", facing="east", half="top"))
    k.set(10, 5, 3, S("chiseled_resin_bricks"))
    k.double_door(9, 1, 5, "pale_oak")
    k.clear(9, 1, 8, 11, 3, 8)  # 탑 → 본당
    k.set(11, 1, 5, PALE)
    k.set(11, 2, 5, PALE)
    for x in (8, 12):
        k.set(x, 1, 2, S("pale_oak_fence"))
        k.set(x, 2, 2, S("white_candle", candles=3, lit=True))
    # 장미창 + 종탑 창
    k.round_window(10, 9, 3, "x", 2, S("resin_bricks"), S("gray_stained_glass_pane", east=True, west=True))
    k.set(10, 9, 3, S("magenta_stained_glass_pane", east=True, west=True))
    for y in (15, 16, 17):
        k.set(10, y, 3, None)
        k.set(7, y, 5, None)
        k.set(13, y, 5, None)
    k.set(10, 17, 5, S("bell", attachment="ceiling", facing="north"))
    k.floor(8, 4, 12, 7, 18, S("pale_oak_planks"))
    sp = k.spire(10, 5, 3, 21, "deepslate_tile", rise=3, tip=S("lightning_rod", facing="up"))
    for x, z in ((7, 3), (13, 3), (7, 8), (13, 8)):
        k.set(x, 21, z, S("tuff_brick_wall"))
        k.set(x, 22, z, S("tuff_brick_wall"))
        k.set(x, 23, z, S("lightning_rod", facing="up"))
    # 후진(다각형 느낌: 모서리 깎음) + 모임 지붕
    k.walls(7, 21, 13, 24, 1, 9, stone)
    for x, z in ((7, 24), (13, 24)):
        k.set(x, 1, z, None) if False else None
    for x in (9, 11):
        k.arch_window(x, 3, 24, "south", 1, 4, "gray_stained_glass_pane", "resin_brick")
    k.hip(6, 14, 21, 25, 10, "deepslate_tile")
    k.clear(8, 1, 21, 12, 9, 21)
    # 실내: 장의자, 통로 카펫, 제단과 초, 독서대, 사슬 샹들리에, 창백한 참나무 선반, 삐걱 심장 장식
    k.floor(7, 9, 13, 23, 0, S("polished_tuff"))
    for z in range(10, 19, 2):
        for x in (7, 8, 12, 13):
            k.chair(x, 1, z, "pale_oak", "north")
    for z in range(6, 21):
        for x in (10,):
            k.set(x, 1, z, S("light_gray_carpet"))
    k.box(8, 1, 22, 12, 1, 22, S("chiseled_resin_bricks"))
    for x in (8, 12):
        k.set(x, 2, 22, S("white_candle", candles=4, lit=True))
    k.set(10, 2, 22, S("decorated_pot"))
    k.set(10, 1, 20, S("lectern", facing="north"))
    for z in (12, 17):
        k.fill(10, 13, z, 10, 15, z, S("iron_chain", axis="y"))
        k.set(10, 12, z, S("pale_oak_trapdoor", half="top"))
        k.set(10, 11, z, S("lantern", hanging=True))
    for z in (10, 19):
        k.set(7, 3, z, S("pale_oak_shelf", facing="east"))
        k.set(13, 3, z, S("pale_oak_shelf", facing="west"))
    k.set(8, 1, 23, S("creaking_heart", axis="y", creaking_heart_state="dormant", natural=False))
    k.set(12, 1, 23, S("creaking_heart", axis="y", creaking_heart_state="dormant", natural=False))
    return k.build()


# ====================================================================== 8. 마녀의 늪 오두막
def witch_hut():
    k = Arch()
    wall = mix((S("mud_bricks"), 5), (S("packed_mud"), 2), (S("mangrove_planks"), 2))
    PLANK = S("mangrove_planks")
    # 맹그로브 기둥 + 벌어진 뿌리 (물·진흙 지형은 없음)
    for x, z in ((5, 7), (14, 7), (5, 15), (14, 15), (18, 11), (18, 17)):
        k.fill(x, 0, z, x, 4, z, S("mangrove_log", axis="y"))
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            k.set(x + dx, 0, z + dz, S("mangrove_roots"))
        k.set(x + 1, 1, z, S("mangrove_roots"))
        k.set(x, 1, z - 1, S("mangrove_roots"))
    k.floor(4, 6, 15, 16, 5, PLANK)
    k.floor(13, 10, 19, 18, 5, PLANK)
    k.walls(4, 6, 15, 16, 5, 5, S("stripped_mangrove_log", axis="x"))
    # 본채 벽 + 골조 + 들어간 창/둥근 창
    k.walls(5, 7, 14, 15, 6, 10, wall)
    k.frame(5, 7, 14, 15, 6, 10, "mangrove_log", beam=True)
    k.door(9, 6, 7, "mangrove")
    k.recessed_window(7, 8, 7, "north", w=1, h=2, lintel="mangrove", sill="mangrove", shutter="mangrove")
    k.round_window(12, 8, 7, "x", 1, S("mangrove_planks"), S("purple_stained_glass_pane", east=True, west=True))
    for z in (10, 12):
        k.recessed_window(5, 8, z, "west", w=1, h=2, lintel="mangrove", sill="mangrove", shutter="mangrove")
    # 비대칭 지붕: 서쪽은 가파르게, 동쪽은 완만하게, 꼭대기는 마녀 모자처럼 휘어짐
    for z in range(5, 18):
        for i in range(8):
            k.set(3 + i, 11 + i, z, S("dark_oak_stairs", facing="east"))
        prev = 10
        for x, h in ((16, 11), (15, 11), (14, 12), (13, 13), (12, 15), (11, 17), (10, 18)):
            k.set(x, h, z, S("dark_oak_stairs", facing="west"))
            for yy in range(prev + 1, h):
                k.set(x, yy, z, S("dark_oak_planks"))
            prev = h
        k.set(10, 18, z, S("dark_oak_planks"))
    for x in range(4, 16):
        for y in range(11, 18):
            for z in (7, 15):
                east = {16: 11, 15: 11, 14: 12, 13: 13, 12: 15, 11: 17, 10: 18}
                if 4 + (y - 11) + 1 <= x <= 15 and y < east.get(x, 19):
                    k.set(x, y, z, PLANK)
    for z in (10, 11, 12):
        for i, (x, y) in enumerate(((10, 19), (10, 20), (11, 20), (11, 21), (12, 21), (12, 22), (13, 22))):
            if z != 11 and i >= 5:
                continue
            k.set(x, y, z, S("dark_oak_planks") if i < 6 else S("dark_oak_stairs", facing="west"))
    for z in range(6, 17, 3):
        k.set(4 + (z % 2), 12 + (z % 2), z, S("moss_block"))
    # 약초방(별채) + 낮은 지붕
    k.walls(14, 11, 18, 17, 6, 8, PLANK)
    k.frame(14, 11, 18, 17, 6, 8, "mangrove_log")
    k.gable(13, 19, 10, 18, 9, "dark_oak", ridge="x")
    k.clear(14, 6, 12, 14, 7, 14)
    # 비뚤어진 굴뚝 + 연기
    for y in range(10, 17):
        k.set(14 - (1 if y > 13 else 0), y, 13 + (1 if y > 15 else 0), S("mud_bricks"))
    k.set(13, 17, 14, S("campfire", lit=True))
    # 계단(땅 → 현관) + 영혼 랜턴
    for i in range(5):
        k.set(9, 1 + i, 1 + i, S("mangrove_stairs", facing="south"))
        for yy in range(0, 1 + i):
            k.set(9, yy, 1 + i, S("mangrove_log", axis="y")) if yy < i else None
    k.set(9, 5, 6, PLANK)
    for x in (8, 10):
        k.hang(x, 4, 6, "soul_lantern")
    k.set(4, 6, 6, S("mangrove_fence"))
    k.set(4, 7, 6, S("soul_lantern"))
    k.floor(6, 8, 13, 14, 11, S("mangrove_planks"))
    k.floor(15, 12, 17, 16, 9, S("mangrove_planks"))
    # 실내: 가마솥, 양조대, 물약 선반, 책장, 침대, 러그, 매달린 약초·포자꽃, 촛불
    k.set(7, 6, 13, S("water_cauldron", level=3))
    k.set(8, 6, 14, S("brewing_stand"))
    k.set(6, 6, 14, S("brewing_stand"))
    k.shelf_wall(6, 14, 9, 14, 8, "mangrove", "north")
    k.set(13, 6, 9, S("chiseled_bookshelf", facing="west"))
    k.set(13, 7, 9, S("chiseled_bookshelf", facing="west"))
    k.bed(12, 6, 13, "purple", "south")
    k.rug(7, 9, 11, 11, 6, "purple", border="black")
    for x, z in ((7, 9), (11, 11), (9, 13)):
        k.set(x, 10, z, S("hanging_roots"))
    k.set(10, 10, 11, S("spore_blossom"))
    k.set(6, 6, 9, S("purple_candle", candles=3, lit=True))
    k.set(12, 6, 8, S("potted_red_mushroom"))
    k.set(16, 6, 16, S("barrel", facing="up"))
    k.set(17, 6, 12, S("composter"))
    k.set(16, 6, 12, S("flower_pot"))
    k.hang(16, 8, 14, "soul_lantern")
    return k.build()


# ====================================================================== 9. 드워프 대장간
def dwarven_forge():
    k = Arch()
    _rock = mix((S("cobbled_deepslate"), 5), (S("deepslate"), 4), (S("tuff"), 2))

    def rock(x, y, z):  # 3칸 덩어리 단위로 같은 돌 → 바위 덩어리처럼 보이게
        return _rock(x // 3, y // 3, z // 3)
    BB = S("polished_blackstone_bricks")

    def height(x, z):
        ridge = 9 + 5 * math.exp(-((x - 15) ** 2) / 40 - ((z - 15) ** 2) / 30)
        bumps = 1.2 * math.sin(x * 0.9) + 1.0 * math.cos(z * 1.1 + x * 0.3)
        edge = min(x, 24 - x, z - 4, 20 - z)
        return int(min(ridge + bumps, 4 + edge * 2.2))
    # 바위산처럼 깎은 외피(속 빔): 뒤쪽 봉우리, 윗면 군데군데 이끼
    for x in range(0, 25):
        for z in range(4, 21):
            h = max(2, height(x, z))
            for y in range(0, h + 1):
                if y == h or y == 0 or x in (0, 24) or z in (4, 20) or y >= h - 1:
                    k.set(x, y, z, rock(x, y, z))
            if h3(x // 2, h, z // 2) % 6 == 0:
                k.set(x, h, z, S("moss_block"))
    k.clear(6, 1, 7, 18, 7, 17)
    k.clear(16, 1, 9, 22, 9, 15)
    k.floor(6, 7, 22, 17, 0, S("polished_deepslate"))
    k.floor(5, 6, 19, 18, 8, S("deepslate_bricks"))
    # 정면 포털: 흑암 기둥(금 머리) + 계단식 박공 + 깊은 아치 통로 + 화로 + 룬(조각 흑암)
    k.box(6, 0, 1, 18, 0, 6, BB)
    for x in (7, 8, 16, 17):
        k.fill(x, 1, 2, x, 9, 4, BB)
    for x in (7, 17):
        k.set(x, 10, 2, S("gold_block"))
        k.set(x, 10, 3, S("gold_block"))
        k.set(x, 5, 1, S("chiseled_polished_blackstone"))
    k.fill(9, 8, 2, 15, 9, 4, BB)
    for i in range(5):
        k.set(8 + i, 10 + i // 2, 2, S("polished_blackstone_brick_stairs", facing="east"))
        k.set(16 - i, 10 + i // 2, 2, S("polished_blackstone_brick_stairs", facing="west"))
    k.fill(11, 12, 2, 13, 12, 2, BB)
    k.set(12, 13, 2, S("gold_block"))
    for x in (10, 12, 14):
        k.set(x, 8, 1, S("chiseled_polished_blackstone"))
    k.clear(10, 1, 2, 14, 6, 8)
    k.set(10, 6, 2, S("polished_blackstone_brick_stairs", facing="east", half="top"))
    k.set(14, 6, 2, S("polished_blackstone_brick_stairs", facing="west", half="top"))
    k.set(10, 5, 2, S("polished_blackstone_brick_stairs", facing="east", half="top"))
    k.set(14, 5, 2, S("polished_blackstone_brick_stairs", facing="west", half="top"))
    for x in (11, 13):
        k.set(x, 6, 3, S("iron_chain", axis="y"))
        k.set(x, 5, 3, S("lantern", hanging=True))
    for x in (5, 19):
        k.fill(x, 1, 1, x, 2, 1, BB)
        k.set(x, 3, 1, S("campfire", lit=True))
    # 굴뚝(속 빈 3×3, 구리 모자, 연기)
    k.walls(19, 11, 21, 13, 9, 16, S("bricks"))
    k.walls(18, 10, 22, 14, 17, 17, S("waxed_oxidized_cut_copper_slab"))
    k.set(20, 16, 12, S("campfire", lit=True))
    # 화덕실: 용광로 셋, 용암 수로(돌 테두리 + 쇠창살), 모루·대장장이 작업대·숫돌
    for x in (18, 19, 20):
        k.set(x, 1, 14, S("blast_furnace", facing="north", lit=True))
        k.set(x, 2, 14, BB)
    k.fill(16, -1, 11, 22, -1, 13, S("deepslate"))
    for x in range(17, 22):
        k.set(x, 0, 12, S("lava"))
        k.set(x, 1, 12, S("iron_bars", east=True, west=True))
    k.set(19, 1, 11, S("anvil", facing="east"))
    k.set(20, 1, 11, S("smithing_table"))
    k.set(21, 1, 10, S("grindstone", face="floor", facing="west"))
    # 작업실: 원석 통, 무기 선반, 금 머리 기둥, 사슬 등, 술통 탁자와 의자, 러그
    for x, z in ((7, 8), (7, 9), (8, 8)):
        k.set(x, 1, z, S("barrel", facing="up"))
    k.set(7, 1, 10, S("raw_iron_block"))
    k.set(8, 1, 9, S("raw_gold_block"))
    k.set(7, 2, 8, S("raw_copper_block"))
    k.shelf_wall(6, 12, 6, 16, 3, "dark_oak", "east")
    for x, z in ((9, 11), (15, 11), (9, 15), (15, 15)):
        k.fill(x, 1, z, x, 7, z, BB)
        k.set(x, 4, z, S("gold_block"))
    for x, z in ((12, 10), (12, 14)):
        k.fill(x, 6, z, x, 7, z, S("iron_chain", axis="y"))
        k.set(x, 5, z, S("lantern", hanging=True))
    for x in (11, 12):
        k.table(x, 1, 13, "dark_oak")
        k.chair(x, 1, 12, "dark_oak", "north")
        k.chair(x, 1, 14, "dark_oak", "south")
    for z in (15, 16):
        k.set(7, 1, z, S("barrel", facing="east"))
        k.set(7, 2, z, S("barrel", facing="east"))
    k.rug(10, 8, 14, 9, 1, "red", border="black")
    return k.build()


def craft_templates():
    return [
        {"name": "구리 증기 공방", "category": "스팀펑크",
         "description": "돌출 구리 기둥과 아치 창, 둥근 톱니 창의 응회암 공방. 새 구리에서 산화 구리로 변해 가는 톱니 지붕과 채광 유리, 둥근 물탱크를 얹은 보일러실, 가는 구리 배관. 크래프터 작업대 줄과 구리 골렘 조각상.",
         "data": copper_workshop()},
        {"name": "구리 시계탑", "category": "스팀펑크",
         "description": "모서리를 깎은 응회암 탑에 구리 세로 띠와 돌출 수평 띠, 넓게 튀어나온 구리 시계실의 네 면 둥근 시계판, 들린 처마 첨탑과 모서리 작은 첨탑. 관리실과 층층 사다리, 꼭대기 기계실과 종.",
         "data": clock_tower()},
        {"name": "창백한 정원 예배당", "category": "고딕",
         "description": "버팀벽과 작은 첨탑이 줄지은 돌 본당, 뾰족 아치 창, 장미창과 깊은 아치 정문이 있는 정면 탑과 가파른 첨탑. 창백한 참나무 장의자와 촛불 제단, 사슬 샹들리에, 삐걱 심장 장식.",
         "data": pale_chapel()},
        {"name": "마녀의 늪 오두막", "category": "판타지",
         "description": "뿌리처럼 벌어진 맹그로브 기둥 위, 한쪽만 가파르고 끝이 휘어진 마녀 모자 지붕. 보라 둥근 창, 영혼 랜턴 현관, 비뚤어진 굴뚝. 가마솥과 양조대, 물약 선반, 매달린 약초.",
         "data": witch_hut()},
        {"name": "드워프 대장간", "category": "판타지",
         "description": "바위산을 깎은 외피에 금 머리 흑암 기둥과 계단식 박공, 룬을 새긴 깊은 아치 포털과 화로. 용광로 셋과 용암 수로의 화덕실, 원석 통과 무기 선반, 사슬 등과 술통 탁자.",
         "data": dwarven_forge()},
    ]
