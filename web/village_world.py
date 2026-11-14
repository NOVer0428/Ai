"""세계 각지 6종 (건물만, 조경 없음).

매스/재료: Codex 설계안 · 디테일: 핀터레스트 관찰(design/references-2026.md) · 구현: seed_detail.Arch
26.3 신규 재료 활용: 양털 계단(차양·돛), 색 사암, 콘크리트 반블록 등 (data/blocks-26.3.json 확인)
"""
import math

from seed_detail import Arch, S, h3
from seed_kit import mix


# ====================================================================== 10. 엘프 나무 집
def elven_treehouse():
    k = Arch()
    CX, CZ = 14, 14
    TRUNK = S("oak_wood", axis="y")
    # 줄기(속 빈 원기둥, 아래는 굵게) + 벌어진 뿌리
    for y in range(0, 26):
        r = 3 if y < 4 else 2
        for dx, dz in k.ring(r):
            k.set(CX + dx, y, CZ + dz, TRUNK)
    for ang in range(0, 360, 45):
        dx, dz = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        for i in range(3, 7):
            k.set(CX + round(dx * i), max(0, 2 - i // 2), CZ + round(dz * i), TRUNK)
    # 줄기를 감아 오르는 나선 계단(반지름 4) → 하부 단(y8)
    for i in range(8):  # 북쪽 정면 대계단 (폭 3, 가장자리 받침 기둥 + 난간)
        z = CZ - 15 + i
        for x in (CX - 1, CX, CX + 1):
            k.set(x, i, z, S("birch_stairs", facing="south"))
            for yy in range(0, i):
                k.set(x, yy, z, S("birch_planks")) if yy == i - 1 else None
        for x in (CX - 2, CX + 2):
            k.fill(x, 0, z, x, i, z, S("stripped_birch_log", axis="y"))
            k.set(x, i + 1, z, S("birch_fence"))
    # 하부 둥근 단(서재) + 난간 + 받침 가지
    for dx, dz in k.disc(7):
        k.set(CX + dx, 8, CZ + dz, S("birch_planks"))
    for dx, dz in k.ring(7):
        k.set(CX + dx, 8, CZ + dz, S("oak_slab", type="top"))
        k.set(CX + dx, 9, CZ + dz, S("birch_fence", north=True, south=True, east=True, west=True))
    for ang in range(0, 360, 60):
        dx, dz = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        for i in range(3, 8):
            k.set(CX + round(dx * i), 8 - (7 - i) // 2, CZ + round(dz * i), S("oak_log", axis="y"))
    for x in (CX - 1, CX, CX + 1):
        k.set(x, 9, CZ - 7, None)
        k.set(x, 8, CZ - 7, S("birch_planks"))
    # 큰 둥근 방(생활실·침실): 자작나무 벽 + 참나무 기둥 + 둥근 창, 꽃잎형 구리 원뿔 지붕
    for y in range(10, 15):
        for dx, dz in k.ring(5):
            k.set(CX + dx, y, CZ + dz, S("stripped_oak_log", axis="y") if (dx + dz) % 3 == 0 else S("birch_planks"))
    for dx, dz in ((-5, 0), (5, 0), (0, 5), (3, 4), (-3, 4)):
        for y in (11, 12):
            k.set(CX + dx, y, CZ + dz, S("glass"))
    for dx, dz in k.disc(5):
        k.set(CX + dx, 15, CZ + dz, S("birch_slab", type="top"))
    k.clear(CX - 1, 10, CZ - 5, CX + 1, 12, CZ - 5)
    k.set(CX, 13, CZ - 5, S("birch_planks"))
    k.cone(CX, CZ, 6, 16, "waxed_oxidized_cut_copper", tip=S("lightning_rod", facing="up"))
    # 작은 둥근 방(동쪽, 높게) + 다리
    PX, PZ = CX + 9, CZ - 2
    for dx, dz in k.disc(3):
        k.set(PX + dx, 17, PZ + dz, S("birch_planks"))
    for y in range(18, 21):
        for dx, dz in k.ring(3):
            k.set(PX + dx, y, PZ + dz, S("birch_planks") if (dx + dz) % 2 else S("stripped_oak_log", axis="y"))
    k.set(PX + 3, 19, PZ, S("glass"))
    k.cone(PX, PZ, 4, 21, "waxed_oxidized_cut_copper", tip=S("lightning_rod", facing="up"))
    for x in range(CX + 3, PX - 2):
        k.set(x, 17, PZ, S("birch_planks"))
        k.set(x, 18, PZ - 1, S("birch_fence", east=True, west=True))
        k.set(x, 18, PZ + 1, S("birch_fence", east=True, west=True))
    k.clear(PX - 3, 18, PZ, PX - 3, 19, PZ)
    for y in range(15, 17):
        k.set(PX, y, PZ, S("oak_log", axis="y"))
    # 잎 덮개: 줄기 꼭대기에서 뻗은 가지 끝의 불규칙한 잎무리 (집을 가리지 않게 바깥쪽)
    leaf = S("oak_leaves", persistent=True, distance=1)
    for (lx, lz, ly, r) in ((4, 6, 24, 3), (24, 8, 26, 3), (5, 22, 23, 3), (22, 22, 24, 3), (14, 24, 27, 2), (12, 4, 27, 2)):
        for dx in range(-r - 1, r + 2):
            for dz in range(-r - 1, r + 2):
                for dy in range(-1, 3):
                    d = dx * dx + dz * dz + 2 * (dy - 0.5) ** 2
                    if d <= r * r + (h3(lx + dx, ly + dy, lz + dz) % 5) - 2:
                        k.set(lx + dx, ly + dy, lz + dz, leaf)
        steps = max(abs(lx - CX), abs(lz - CZ))
        axis = "x" if abs(lx - CX) >= abs(lz - CZ) else "z"
        for i in range(steps):
            bx = CX + round((lx - CX) * i / steps)
            by = 24 + round((ly - 24) * i / steps)
            bz = CZ + round((lz - CZ) * i / steps)
            k.set(bx, by, bz, S("oak_log", axis=axis))
            if i < 3:
                k.set(bx, by - 1, bz, S("oak_wood", axis=axis))
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            for y in (23, 24, 25):
                k.set(CX + dx, y, CZ + dz, S("oak_wood", axis="y"))
    # 실내: 하부 단 서재(책장·선반), 큰 방(침대·탁자·의자·러그), 작은 방(독서 의자), 줄기 속 사다리, 숨긴 조명
    k.set(CX - 6, 9, CZ + 1, S("bookshelf"))
    k.set(CX - 6, 9, CZ - 1, S("bookshelf"))
    k.set(CX - 5, 9, CZ + 4, S("lectern", facing="north"))
    k.floor(CX - 4, CZ - 4, CX + 4, CZ + 4, 9, S("birch_planks"))
    k.bed(CX + 2, 10, CZ + 1, "green", "south")
    k.shelf_wall(CX - 4, CZ + 2, CX - 4, CZ + 3, 11, "birch", "east")
    k.set(CX - 3, 10, CZ - 2, S("chiseled_bookshelf", facing="east"))
    k.table(CX - 2, 10, CZ + 2, "birch")
    k.chair(CX - 2, 10, CZ + 3, "birch", "south")
    k.set(CX + 3, 10, CZ - 3, S("potted_flowering_azalea_bush"))
    for dx, dz in ((-1, -3), (0, -3), (1, -3), (-1, 3), (1, 3)):
        k.set(CX + dx, 10, CZ + dz, S("lime_carpet"))
    k.hang(CX - 3, 14, CZ, "lantern")
    k.hang(CX + 3, 14, CZ - 1, "lantern")
    k.chair(PX + 1, 18, PZ, "birch", "east")
    k.set(PX + 1, 18, PZ + 1, S("birch_shelf", facing="north"))
    k.set(PX, 21, PZ, S("birch_planks"))
    k.hang(PX, 20, PZ, "lantern")
    k.clear(CX - 1, 0, CZ - 1, CX + 1, 25, CZ + 1)
    for y in range(1, 15):
        k.set(CX, y, CZ - 1, S("ladder", facing="north")) if False else None
    for y in range(9, 18):
        k.set(CX + 1, y, CZ, S("ladder", facing="west")) if False else None
    k.fill(CX, 1, CZ + 1, CX, 16, CZ + 1, S("oak_planks"))
    for y in range(1, 17):
        k.set(CX, y, CZ, S("ladder", facing="north"))
    k.set(CX, 0, CZ, S("oak_planks"))
    k.set(CX, 9, CZ - 1, None)
    k.clear(CX, 10, CZ - 2, CX, 11, CZ - 2)
    return k.build()


# ====================================================================== 11. 지중해 빌라
def mediterranean_villa():
    k = Arch()
    WALL = Arch.grad([S("white_concrete"), S("calcite"), S("white_concrete")], 1, 12, 0.6)
    BASE = S("smooth_sandstone")
    ROOF = "polished_granite"
    k.floor(2, 3, 20, 18, 0, BASE)
    # 본채(2층) + 동쪽 탑(3층) + 서쪽 단층 부엌동
    k.walls(4, 7, 14, 17, 1, 9, WALL)
    k.walls(4, 7, 14, 17, 1, 1, BASE)
    k.cornice(4, 7, 14, 17, 5, "smooth_sandstone", half="top")
    k.walls(15, 9, 19, 14, 1, 13, WALL)
    k.walls(15, 9, 19, 14, 1, 1, BASE)
    k.cornice(15, 9, 19, 14, 13, "smooth_sandstone", half="top")
    k.walls(-1, 10, 3, 16, 1, 5, WALL)
    # 정면 아치 회랑(둥근 아치 3개) + 위 발코니
    for x in (4, 7, 10, 13):
        k.fill(x, 1, 4, x, 4, 4, BASE)
    for x0_ in (4, 7, 10):
        k.set(x0_ + 1, 4, 4, S("smooth_sandstone_stairs", facing="east", half="top"))
        k.set(x0_ + 2, 4, 4, S("smooth_sandstone_stairs", facing="west", half="top"))
    for x in range(4, 14):
        k.set(x, 5, 4, BASE)
        k.set(x, 5, 5, BASE)
        k.set(x, 5, 6, BASE)
        k.set(x, 6, 4, S("iron_bars", east=True, west=True))
    k.floor(4, 4, 13, 6, 0, S("cut_sandstone"))
    k.door(6, 1, 7, "jungle")
    k.door(11, 6, 7, "jungle")  # 2층 → 발코니
    # 창: 안쪽 유리 + 파란 덧창 + 창턱
    for x in (9, 12):
        k.recessed_window(x, 2, 7, "north", w=1, h=2, sill="smooth_sandstone", shutter="warped")
    for x in (6, 8):
        k.recessed_window(x, 6, 7, "north", w=1, h=2, sill="smooth_sandstone", shutter="warped")
    for z in (11, 14):
        k.recessed_window(4, 6, z, "west", w=1, h=2, sill="smooth_sandstone", shutter="warped",
                          box=S("flowering_azalea_leaves", persistent=True, distance=1))
    for x in (7, 11):
        k.recessed_window(x, 2, 17, "south", w=1, h=2, sill="smooth_sandstone", shutter="warped")
        k.recessed_window(x, 6, 17, "south", w=1, h=2, sill="smooth_sandstone", shutter="warped")
    for y in (6, 10):
        k.recessed_window(17, y, 9, "north", w=1, h=2, sill="smooth_sandstone", shutter="warped")
        k.recessed_window(19, y, 11, "east", w=2, h=2, sill="smooth_sandstone", shutter="warped")
    k.recessed_window(-1, 2, 13, "west", w=1, h=2, sill="smooth_sandstone", shutter="warped")
    # 파란 포인트 띠 + 분홍 꽃 덩굴(벽에 붙은 화단)
    for x in range(5, 14):
        k.set(x, 1, 17, S("blue_terracotta"))
    for x, y in ((14, 6), (14, 7), (13, 8), (4, 7), (4, 8)):
        k.set(x, y, 6, S("flowering_azalea_leaves", persistent=True, distance=1))
    # 지붕: 완만한 붉은 기와(1:2) — 본채, 탑(낮은 모임지붕), 부엌동
    k.curved_gable(3, 15, 6, 18, 10, ROOF, ridge="x", lift=False, trim=ROOF, gable_fill=WALL(9, 11, 9),
                   wall_top=10, pitch="low")
    k.hip(14, 20, 8, 15, 14, ROOF)
    k.curved_gable(-2, 4, 9, 17, 6, ROOF, ridge="x", lift=False, gable_fill=WALL(2, 7, 9), wall_top=6, pitch="low")
    # 연결 통로: 본채↔탑(1·2층), 본채↔부엌동
    for y0_ in (1, 6):
        k.clear(14, y0_, 11, 15, y0_ + 1, 12)
    k.clear(3, 1, 12, 4, 2, 13)
    # 실내: 1층 거실(소파·러그)·식사실 / 부엌동(조리대·화덕) / 2층 침실·서재 / 탑 휴게실
    k.floor(5, 8, 13, 16, 0, S("orange_glazed_terracotta"))
    k.floor(5, 8, 13, 16, 5, S("birch_planks"))
    for x in range(5, 14):
        k.set(x, 4, 12, S("stripped_jungle_log", axis="x"))
    k.rug(5, 9, 8, 12, 1, "white", border="blue")
    for z in (9, 10, 11):
        k.chair(5, 1, z, "birch", "west")
    k.set(7, 1, 10, S("birch_trapdoor", half="top"))
    k.set(7, 2, 10, S("potted_red_tulip"))
    k.table(11, 1, 14, "birch")
    k.chair(10, 1, 14, "birch", "west")
    k.chair(12, 1, 14, "birch", "east")
    k.floor(0, 11, 2, 15, 0, S("smooth_sandstone"))
    for z in range(11, 16):
        k.set(0, 1, z, S("smoker", facing="east") if z == 13 else S("barrel", facing="east"))
        k.set(0, 2, z, S("smooth_quartz_slab"))
        k.set(0, 3, z, S("birch_shelf", facing="east"))
    for i in range(5):  # 계단(본채 안 동쪽 벽)
        k.set(13, 1 + i, 16 - i, S("birch_stairs", facing="north"))
        for yy in range(1, 1 + i):
            k.set(13, yy, 16 - i, S("birch_planks"))
    k.clear(13, 5, 12, 13, 5, 16)
    k.bed(9, 6, 14, "blue", "south")
    k.set(8, 6, 15, S("birch_trapdoor", half="top"))
    k.set(8, 7, 15, S("blue_candle", candles=2, lit=True))
    k.rug(5, 9, 8, 11, 6, "light_blue")
    k.shelf_wall(5, 16, 7, 16, 7, "birch", "north")
    k.set(6, 6, 10, S("lectern", facing="north"))
    k.floor(16, 10, 18, 13, 5, S("birch_planks"))
    k.floor(16, 10, 18, 13, 10, S("birch_planks"))
    k.set(16, 6, 13, S("barrel", facing="up"))
    for x in (17, 18):
        k.chair(x, 11, 13, "birch", "south")
    k.set(17, 11, 11, S("potted_azalea_bush"))
    k.fill(18, 1, 13, 18, 10, 13, S("ladder", facing="north")) if False else None
    for y in range(1, 11):
        k.set(18, y, 13, S("ladder", facing="north"))
    k.set(18, 5, 13, S("ladder", facing="north"))
    k.set(18, 10, 13, S("ladder", facing="north"))
    k.hang(9, 4, 10, "lantern")
    k.hang(17, 9, 11, "lantern")
    return k.build()


# ====================================================================== 12. 사막 교역소
def desert_trading_post():
    k = Arch()
    MUD = Arch.grad([S("mud_bricks"), S("mud_bricks"), S("packed_mud")], 1, 9, 0.3)
    TRIM = "cut_sandstone"
    k.floor(2, 1, 22, 21, 0, S("smooth_sandstone"))
    # 교역 홀: 진흙 벽돌 + 사암 귓돌·띠 + 지붕선에 튀어나온 들보(비가) + 톱니 난간
    k.walls(3, 8, 14, 18, 1, 8, MUD)
    for x, z in ((3, 8), (14, 8), (3, 18), (14, 18)):
        k.fill(x, 1, z, x, 9, z, S("cut_sandstone"))
    k.cornice(3, 8, 14, 18, 8, "sandstone", half="top")
    k.floor(3, 8, 14, 18, 9, S("cut_sandstone"))
    for x in range(3, 15):
        for z in (8, 18):
            k.set(x, 10, z, S("mud_brick_wall") if x % 2 == 0 else None) if x not in (3, 14) else k.fill(x, 10, z, x, 11, z, S("cut_sandstone"))
    for z in range(9, 18):
        for x in (3, 14):
            k.set(x, 10, z, S("mud_brick_wall") if z % 2 == 0 else None)
    for x in range(5, 14, 2):
        k.set(x, 7, 7, S("stripped_spruce_log", axis="z"))
        k.set(x, 7, 19, S("stripped_spruce_log", axis="z"))
    # 정면: 깊은 아치 출입구(돌출 문틀) + 작은 깊은 창
    k.fill(8, 1, 7, 12, 6, 7, S("cut_sandstone"))
    k.clear(9, 1, 7, 11, 4, 8)
    k.set(9, 4, 7, S("sandstone_stairs", facing="east", half="top"))
    k.set(11, 4, 7, S("sandstone_stairs", facing="west", half="top"))
    k.set(9, 4, 8, S("sandstone_stairs", facing="east", half="top"))
    k.set(11, 4, 8, S("sandstone_stairs", facing="west", half="top"))
    k.fill(8, 6, 6, 12, 6, 6, S("chiseled_sandstone"))
    for x in (5, 13):
        k.recessed_window(x, 3, 8, "north", w=1, h=2, lintel="sandstone", sill="sandstone")
    # 돔실: 원통 받침 + 진짜 반구 돔 + 꼭대기 장식
    k.walls(15, 11, 21, 17, 1, 6, MUD)
    k.cornice(15, 11, 21, 17, 6, "sandstone", half="top")
    k.floor(15, 11, 21, 17, 7, S("cut_sandstone"))
    top = k.dome(18, 14, 3, 8, "smooth_sandstone", cap=S("lightning_rod", facing="up"))
    k.recessed_window(21, 2, 13, "east", w=1, h=3, lintel="sandstone", sill="sandstone")
    k.recessed_window(21, 2, 15, "east", w=1, h=3, lintel="sandstone", sill="sandstone")
    # 감시탑(서북 모서리): 좁은 탑 + 작은 돔
    k.walls(2, 5, 5, 8, 1, 13, MUD)
    k.cornice(2, 5, 5, 8, 13, "sandstone", half="top")
    for y in (6, 10):
        k.set(3, y, 5, S("glass_pane", east=True, west=True))
    k.dome(3, 6, 1, 14, "smooth_sandstone", cap=S("lightning_rod", facing="up")) if False else None
    k.floor(2, 5, 5, 8, 14, S("cut_sandstone"))
    for x, z in ((2, 5), (5, 5), (2, 8), (5, 8)):
        k.set(x, 15, z, S("sandstone_wall"))
    # 시장 차양(정면에 붙음): 26.3 양털 계단으로 흰·주황 줄무늬 경사
    for x in range(3, 15):
        c = "white" if (x // 2) % 2 == 0 else "orange"
        k.set(x, 6, 6, S(f"{c}_wool_slab", type="top"))
        k.set(x, 5, 5, S(f"{c}_wool_stairs", facing="south"))
        k.set(x, 4, 4, S(f"{c}_wool_stairs", facing="south"))
        k.set(x, 4, 3, S(f"{c}_wool_slab"))
    for x in (3, 8, 12, 14):
        k.fill(x, 1, 3, x, 3, 3, S("stripped_acacia_log", axis="y"))
    for x, blk in ((4, S("barrel", facing="up")), (5, S("decorated_pot")), (6, S("hay_block", axis="y")),
                   (10, S("melon")), (11, S("carved_pumpkin", facing="north")), (13, S("decorated_pot"))):
        k.set(x, 1, 4, blk)
    k.set(4, 2, 4, S("potted_cactus"))
    # 후면 창고
    k.walls(3, 19, 8, 21, 1, 5, MUD)
    k.floor(3, 19, 8, 21, 6, S("cut_sandstone"))
    k.clear(5, 1, 18, 6, 2, 19)
    k.clear(14, 1, 13, 15, 2, 14)
    k.clear(3, 1, 9, 3, 2, 9) if False else None
    k.clear(4, 1, 8, 4, 2, 8)
    # 실내: 상인 카운터, 양탄자, 상품 선반, 지도대 / 돔실: 낮은 탁자·방석·찻잔 / 창고: 통 / 탑: 사다리
    k.floor(4, 9, 13, 17, 0, S("smooth_sandstone"))
    k.rug(5, 10, 12, 15, 1, "orange", border="red")
    for x in range(5, 10):
        k.set(x, 1, 16, S("acacia_planks"))
        k.set(x, 2, 16, S("acacia_slab"))
    k.shelf_wall(4, 17, 12, 17, 3, "acacia", "north")
    k.set(12, 1, 10, S("barrel", facing="up"))
    k.set(13, 1, 10, S("decorated_pot"))
    k.set(13, 1, 16, S("cartography_table"))
    k.rug(16, 12, 20, 16, 1, "red", border="yellow")
    k.set(18, 1, 14, S("acacia_trapdoor", half="top"))
    k.set(18, 2, 14, S("white_candle", candles=3, lit=True))
    for x, z in ((17, 13), (19, 15)):
        k.set(x, 1, z, S("yellow_carpet"))
    for x in (4, 5, 6, 7):
        k.set(x, 1, 20, S("barrel", facing="north"))
    for y in range(1, 14):
        k.set(3, y, 7, S("ladder", facing="north"))
    k.clear(3, 14, 7, 3, 14, 7)
    k.hang(8, 8, 12, "lantern")
    k.hang(18, 6, 14, "lantern")
    return k.build()


# ====================================================================== 13. 해안 등대
def lighthouse():
    k = Arch()
    CX, CZ = 14, 14

    def stripe(y):
        return S("white_concrete") if y <= 4 or ((y - 5) // 3) % 2 == 1 else S("red_concrete")
    # 돌 기단(팔각 느낌) + 줄무늬 탑(위로 좁아짐)
    for dx, dz in k.disc(6):
        k.set(CX + dx, 0, CZ + dz, S("stone_bricks"))
    for dx, dz in k.ring(6):
        k.set(CX + dx, 1, CZ + dz, S("stone_brick_wall"))
    for y in range(1, 23):
        r = 4 if y < 12 else 3
        for dx, dz in k.ring(r):
            k.set(CX + dx, y, CZ + dz, stripe(y))
    for y in (8, 15, 19):
        k.set(CX, y, CZ - (4 if y < 12 else 3), S("glass_pane", east=True, west=True))
    # 발코니: 아래 까치발 고리 + 바닥 + 철 난간
    for dx, dz in k.ring(4):
        f = "south" if dz < 0 and abs(dz) >= abs(dx) else "north" if dz > 0 and abs(dz) >= abs(dx) else "east" if dx < 0 else "west"
        k.set(CX + dx, 21, CZ + dz, S("stone_brick_stairs", facing=f, half="top")) if False else None
    for dx, dz in k.ring(5):
        f = ("east" if dx < 0 else "west") if abs(dx) >= abs(dz) else ("south" if dz < 0 else "north")
        k.set(CX + dx, 21, CZ + dz, S("stone_brick_stairs", facing=f, half="top"))
    for dx, dz in k.disc(6):
        k.set(CX + dx, 22, CZ + dz, S("polished_andesite"))
    for dx, dz in k.ring(6):
        k.set(CX + dx, 23, CZ + dz, S("iron_bars", north=True, south=True, east=True, west=True))
    # 등롱실: 유리와 검은 기둥, 가운데 바다 랜턴, 검은 지붕 + 원뿔 + 피뢰침
    for y in (23, 24, 25):
        for dx, dz in k.ring(3):
            k.set(CX + dx, y, CZ + dz, S("glass") if (dx + dz) % 2 else S("black_concrete"))
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            k.set(CX + dx, 24, CZ + dz, S("sea_lantern"))
    for dx, dz in k.disc(4):
        k.set(CX + dx, 26, CZ + dz, S("black_concrete"))
    k.cone(CX, CZ, 3, 27, "dark_prismarine", tip=S("lightning_rod", facing="up"))
    k.set(CX, 23, CZ - 3, None)
    k.set(CX, 24, CZ - 3, None)
    k.door(CX, 23, CZ - 3, "spruce")
    # 탑 입구 + 관리인 집(곡선 지붕) + 연결 복도(양쪽 벽 모두 뚫기)
    k.door(CX, 1, CZ - 4, "spruce")
    k.floor(1, 5, 10, 13, 0, S("stone_bricks"))
    k.walls(1, 5, 8, 13, 1, 5, S("white_concrete"))
    k.walls(1, 5, 8, 13, 1, 1, S("stone_bricks"))
    k.frame(1, 5, 8, 13, 1, 5, "stripped_spruce_log")
    k.curved_gable(0, 9, 4, 14, 6, "dark_prismarine", ridge="x", trim="spruce", gable_fill=S("white_concrete"), wall_top=6)
    k.door(4, 1, 5, "spruce")
    k.recessed_window(6, 2, 5, "north", w=1, h=2, lintel="spruce", sill="spruce", shutter="spruce")
    k.recessed_window(1, 2, 9, "west", w=1, h=2, lintel="spruce", sill="spruce", shutter="spruce")
    k.walls(8, 11, 10, 13, 1, 4, S("white_concrete"))
    k.floor(8, 11, 10, 13, 5, S("dark_prismarine_slab"))
    k.clear(8, 1, 12, 11, 2, 12)
    # 실내: 관리인 집(난로·탁자·지도대·침대·선반) / 탑(층 바닥, 벽에 붙은 사다리, 꼭대기 출구)
    k.floor(2, 6, 7, 12, 0, S("spruce_planks"))
    k.floor(2, 6, 7, 12, 5, S("spruce_planks"))
    k.set(2, 1, 12, S("furnace", facing="east"))
    k.set(3, 1, 12, S("barrel", facing="up"))
    k.table(5, 1, 9, "spruce")
    k.chair(5, 1, 10, "spruce", "south")
    k.set(7, 1, 7, S("cartography_table"))
    k.bed(6, 1, 11, "blue", "east")
    k.shelf_wall(2, 7, 2, 9, 3, "spruce", "east")
    k.rug(3, 7, 6, 8, 1, "blue", border="white")
    k.hang(4, 4, 9, "lantern")
    for y in (6, 12, 18):
        for dx, dz in k.disc(3):
            k.set(CX + dx, y, CZ + dz, S("spruce_planks"))
    for y in range(1, 22):
        z_back = CZ + (4 if y < 12 else 3)
        k.set(CX, y, z_back - 1, S("ladder", facing="north"))
    for y in (12, 18):
        k.set(CX, y, CZ + 2, S("ladder", facing="north"))
    k.set(CX, 22, CZ + 2, None)
    k.set(CX, 22, CZ + 3, None) if False else None
    k.set(CX - 2, 1, CZ + 1, S("chest", facing="east"))
    k.set(CX + 1, 7, CZ, S("lantern"))
    return k.build()


# ====================================================================== 14. 바이킹 롱하우스
def viking_longhouse():
    k = Arch()
    LOG, PLANK = S("spruce_log", axis="y"), S("spruce_planks")
    x0, x1, z0, z1 = 5, 19, 5, 25
    k.floor(x0 - 1, 0, x1 + 1, z1 + 1, 0, S("cobblestone")) if False else None
    k.floor(x0 - 1, z0 - 4, x1 + 1, z1 + 1, 0, S("cobblestone"))
    # 낮은 벽(3칸): 판자 안쪽, 원목 기둥 바깥 한 칸
    k.walls(x0 + 1, z0, x1 - 1, z1, 1, 3, PLANK)
    for z in range(z0, z1 + 1, 3):
        for x in (x0, x1):
            k.fill(x, 1, z, x, 3, z, LOG)
    # 곡선 지붕: 땅 가까이(y4)에서 시작해 가운데로 갈수록 가팔라짐
    profile = [(0, 4), (1, 4), (2, 5), (3, 5), (4, 6), (5, 7), (6, 8), (7, 10), (8, 11), (9, 13)]
    cx = (x0 + x1) // 2
    for z in range(z0 - 2, z1 + 3):
        for d, h in profile:
            for side, face in ((-1, "east"), (1, "west")):
                x = cx + side * (9 - d)
                k.set(x, h, z, S("spruce_stairs", facing=face))
                if d < len(profile) - 1:
                    for y in range(h + 1, profile[d + 1][1]):
                        k.set(x, y, z, PLANK)
        k.set(cx, 14, z, S("spruce_slab"))
        k.set(cx, 13, z, PLANK)
    # 박공 끝 벽(세로 판자 + 원목) + 교차한 용머리
    for z in (z0, z1):
        for d, h in profile:
            for x in range(cx - (9 - d) + 1, cx + (9 - d)):
                for y in range(4, h + 1):
                    k.set(x, y, z, PLANK if (x + y) % 4 else S("stripped_spruce_log", axis="y"))
    for zend, dz in ((z0 - 2, -1), (z1 + 2, 1)):
        k.set(cx - 1, 14, zend, S("spruce_log", axis="y"))
        k.set(cx + 1, 14, zend, S("spruce_log", axis="y"))
        k.set(cx - 2, 15, zend, S("dark_oak_stairs", facing="east"))
        k.set(cx + 2, 15, zend, S("dark_oak_stairs", facing="west"))
        k.set(cx - 2, 15, zend + dz, S("dark_oak_slab", type="top"))
        k.set(cx + 2, 15, zend + dz, S("dark_oak_slab", type="top"))
    # 이끼 지붕(군데군데)
    for z in range(z0, z1, 2):
        for d in (2, 3):
            if h3(d, z, 0) % 3:
                k.set(cx - (9 - d), profile[d][1] + 1, z, S("moss_carpet"))
    # 북쪽 현관: 조각 문틀(짙은 참나무), 이중문, 랜턴, 박공 지붕
    k.walls(9, 1, 15, 5, 1, 4, PLANK)
    k.frame(9, 1, 15, 5, 1, 4, "spruce_log")
    for i in range(4):
        for z in range(0, 5):
            k.set(9 + i, 5 + i, z, S("spruce_stairs", facing="east"))
            k.set(15 - i, 5 + i, z, S("spruce_stairs", facing="west"))
        for x in range(10 + i, 15 - i):
            k.set(x, 5 + i, 1, PLANK)
    for z in range(0, 5):
        k.set(12, 9, z, S("spruce_slab"))
    k.double_door(11, 1, 1, "spruce")
    for x in (10, 13):
        k.set(x, 3, 1, S("stripped_dark_oak_log", axis="y"))
    k.set(11, 3, 0, S("dark_oak_stairs", facing="west", half="top"))
    k.set(12, 3, 0, S("dark_oak_stairs", facing="east", half="top"))
    for x in (10, 14):
        k.set(x, 1, 0, S("dark_oak_fence"))
        k.set(x, 2, 0, S("lantern"))
    k.clear(11, 1, 5, 13, 3, 5)
    # 옆 창고(동쪽) + 문
    k.walls(20, 16, 23, 23, 1, 3, PLANK)
    k.frame(20, 16, 23, 23, 1, 3, "spruce_log")
    for z in range(15, 25):
        k.set(24, 4, z, S("spruce_stairs", facing="west"))
        k.set(23, 4, z, S("spruce_slab", type="top"))
        k.set(22, 5, z, S("spruce_stairs", facing="west"))
        k.set(21, 5, z, S("spruce_slab", type="top"))
        k.set(20, 6, z, S("spruce_stairs", facing="west"))
    k.floor(20, 16, 23, 23, 0, S("cobblestone"))
    k.clear(19, 1, 19, 20, 2, 20)
    # 실내: 가운데 긴 화덕, 긴 탁자와 의자, 벽 깃발, 모피 침상, 술통, 사슬 등
    k.floor(x0 + 1, z0 + 1, x1 - 1, z1 - 1, 0, S("spruce_planks"))
    for z in range(12, 19):
        k.set(cx, 0, z, S("cobblestone"))
        k.set(cx, 1, z, S("campfire", lit=True) if z % 3 == 0 else S("cobblestone_slab"))
    for z in range(9, 22):
        for x in (8, 16):
            k.set(x, 1, z, S("spruce_trapdoor", half="top"))
        if z % 2:
            k.chair(7, 1, z, "spruce", "west")
            k.chair(17, 1, z, "spruce", "east")
    for z in (10, 15, 20):
        k.set(x0 + 2, 3, z, S("red_wall_banner", facing="east"))
        k.set(x1 - 2, 3, z, S("blue_wall_banner", facing="west"))
    for x in (7, 9, 15, 17):
        k.set(x, 1, 24, S("brown_wool") if x < cx else S("white_wool"))
        k.set(x, 2, 24, S("brown_carpet") if x < cx else S("white_carpet"))
    for x in (13, 14):
        k.set(x, 1, 6, S("barrel", facing="up"))
        k.set(x, 2, 6, S("barrel", facing="up"))
    for z in (9, 15, 21):
        k.fill(cx, 10, z, cx, 12, z, S("iron_chain", axis="y"))
        k.set(cx, 9, z, S("lantern", hanging=True))
    for z in (17, 18, 19):
        k.set(22, 1, z, S("barrel", facing="west"))
    k.set(22, 1, 22, S("chest", facing="west"))
    return k.build()


# ====================================================================== 15. 네덜란드식 풍차
def windmill():
    k = Arch()
    CX, CZ = 14, 15
    body = Arch.grad([S("stone_bricks"), S("bricks"), S("bricks"), S("white_terracotta")], 1, 22, 0.15)
    # 팔각 몸체: 아래 넓고 위로 좁아짐(돌 → 벽돌 → 흰 회벽), 단마다 반블록 띠
    for y in range(1, 23):
        r = 5 if y <= 7 else 4 if y <= 14 else 3
        for dx, dz in k.ring(r):
            k.set(CX + dx, y, CZ + dz, body(CX + dx, y, CZ + dz))
    for y in (7, 14, 22):
        r = 5 if y == 7 else 4 if y == 14 else 3
        for dx, dz in k.ring(r + 1):
            k.set(CX + dx, y, CZ + dz, S("spruce_slab", type="top"))
    for dx, dz in k.disc(5):
        k.set(CX + dx, 0, CZ + dz, S("stone_bricks"))
    # 회랑(y12) + 아래 까치발 + 난간 + 출입문
    for dx, dz in k.disc(6):
        if (dx, dz) not in k.disc(4):
            k.set(CX + dx, 12, CZ + dz, S("spruce_planks"))
    for dx, dz in k.ring(6):
        k.set(CX + dx, 13, CZ + dz, S("spruce_fence", north=True, south=True, east=True, west=True))
        f = ("east" if dx < 0 else "west") if abs(dx) >= abs(dz) else ("south" if dz < 0 else "north")
        k.set(CX + dx, 11, CZ + dz, S("spruce_stairs", facing=f, half="top"))
    k.set(CX + 4, 13, CZ, None)
    k.set(CX + 4, 14, CZ, None)
    k.door(CX + 4, 13, CZ, "spruce", facing="east")
    # 창 + 1층 문
    for y in (5, 10, 18):
        r = 5 if y <= 7 else 4 if y <= 14 else 3
        k.set(CX, y, CZ - r, S("glass_pane", east=True, west=True))
        k.set(CX - r, y, CZ, S("glass_pane", north=True, south=True))
    # 모자 지붕(원뿔) + 꼭대기
    k.cone(CX, CZ, 4, 23, "spruce")
    # 축과 십자 날개: 팔은 원목, 돛은 팔 한쪽에 26.3 흰 양털 계단(바람 받는 경사) + 가로살
    hub = (CX, 18, 8)
    k.fill(CX, 18, 8, CX, 18, 11, S("stripped_spruce_log", axis="z"))
    k.set(*hub, S("spruce_planks"))
    arms = [((0, 1), (1, 0)), ((1, 0), (0, -1)), ((0, -1), (-1, 0)), ((-1, 0), (0, 1))]
    for (ax, ay), (sx, sy) in arms:
        for i in range(1, 13):
            x, y = hub[0] + ax * i, hub[1] + ay * i
            if y < 1:
                break
            k.set(x, y, 7, S("stripped_spruce_log", axis="x" if ax else "y"))
            if i >= 3:
                for w in (1, 2, 3):
                    blk = S("spruce_planks") if i % 3 == 0 else S("white_wool")
                    k.set(x + sx * w, y + sy * w, 7, blk)
    # 방앗간(서쪽) + 곡선 지붕 + 문
    k.floor(1, 9, 9, 21, 0, S("stone_bricks"))
    k.walls(1, 10, 9, 20, 1, 5, S("bricks"))
    k.walls(1, 10, 9, 20, 1, 1, S("stone_bricks"))
    k.frame(1, 10, 9, 20, 1, 5, "stripped_spruce_log", posts_every=5)
    k.curved_gable(0, 10, 9, 21, 6, "spruce", ridge="x", trim="dark_oak", gable_fill=S("bricks"), wall_top=6)
    k.double_door(4, 1, 10, "spruce")
    k.recessed_window(7, 2, 10, "north", w=1, h=2, lintel="brick", sill="brick", shutter="spruce")
    k.recessed_window(1, 2, 14, "west", w=2, h=2, lintel="brick", sill="brick", shutter="spruce")
    k.clear(9, 1, 14, 9, 2, 15)
    k.clear(CX - 5, 1, 14, CX - 5, 2, 15)
    # 실내: 맷돌(숫돌)과 중심 축, 밀 더미, 통, 빵 화덕, 작업대, 탁자 / 탑 층마다 바닥과 벽에 붙은 사다리
    k.floor(2, 11, 8, 19, 0, S("spruce_planks"))
    k.set(CX, 1, CZ, S("grindstone", face="floor", facing="north"))
    k.fill(CX, 2, CZ, CX, 17, CZ, S("stripped_spruce_log", axis="y"))
    for dx, dz in ((2, 2), (-2, 2), (2, -2)):
        k.set(CX + dx, 1, CZ + dz, S("hay_block", axis="y"))
    k.set(CX - 2, 1, CZ - 2, S("barrel", facing="up"))
    for y in (8, 15):
        r = 4 if y == 8 else 3
        for dx, dz in k.disc(r - 1):
            if (dx, dz) != (0, 0):
                k.set(CX + dx, y, CZ + dz, S("spruce_planks"))
    for y in range(1, 22):
        r = 5 if y <= 7 else 4 if y <= 14 else 3
        k.set(CX + r - 1, y, CZ + 1, S("ladder", facing="west")) if False else None
    for y in range(1, 22):
        z_back = CZ + (5 if y <= 7 else 4 if y <= 14 else 3)
        k.set(CX, y, z_back - 1, S("ladder", facing="north")) if (CX, y, z_back) in k.cells else None
    k.set(2, 1, 19, S("smoker", facing="east"))
    k.set(3, 1, 19, S("barrel", facing="north"))
    k.set(2, 1, 17, S("crafting_table"))
    k.table(6, 1, 16, "spruce")
    k.chair(6, 1, 17, "spruce", "south")
    k.shelf_wall(8, 17, 8, 19, 3, "spruce", "west")
    k.rug(3, 12, 6, 14, 1, "yellow", border="brown")
    k.floor(2, 11, 8, 19, 6, S("spruce_planks")) if False else None
    k.hang(5, 5, 15, "lantern") if False else None
    k.set(5, 5, 15, S("lantern", hanging=True)) if False else None
    return k.build()


def world_templates():
    return [
        {"name": "엘프 나무 집", "category": "판타지",
         "description": "벌어진 뿌리의 거대한 줄기를 나선 계단이 감아 오르고, 둥근 단과 큰 둥근 방, 다리로 이어진 높은 작은 방에 청록 구리 원뿔 지붕. 가지 끝 잎무리. 서재·침실·독서 의자, 줄기 속 사다리.",
         "data": elven_treehouse()},
        {"name": "지중해 빌라", "category": "주거",
         "description": "흰 회벽에 완만한 붉은 기와, 둥근 아치 회랑 위 발코니, 파란 덧창과 꽃 화단, 3층 탑과 부엌동. 유약 타일 거실·식사실, 2층 침실·서재, 탑 꼭대기 휴게실.",
         "data": mediterranean_villa()},
        {"name": "사막 교역소", "category": "상업",
         "description": "사암 귓돌과 튀어나온 들보, 톱니 난간의 진흙 벽돌 홀, 둥근 반구 돔실과 감시탑. 흰·주황 양털 계단 줄무늬 차양 아래 노점 진열. 상인 카운터와 양탄자, 돔 아래 차 마시는 자리, 창고.",
         "data": desert_trading_post()},
        {"name": "해안 등대", "category": "랜드마크",
         "description": "빨강·흰 줄무늬 원형 탑, 까치발이 받치는 철 난간 발코니와 바다 랜턴 등롱실. 곡선 지붕 관리인 집과 연결 복도. 층마다 바닥과 벽 사다리, 난로·지도대·침대.",
         "data": lighthouse()},
        {"name": "바이킹 롱하우스", "category": "주거",
         "description": "땅 가까이에서 시작해 가운데로 갈수록 가팔라지는 긴 곡선 지붕, 교차한 용머리와 이끼 지붕, 조각 문틀 현관과 창고. 가운데 긴 화덕과 연회 탁자, 벽 깃발과 모피 침상.",
         "data": viking_longhouse()},
        {"name": "네덜란드식 풍차", "category": "농업",
         "description": "돌·벽돌·흰 회벽으로 좁아지는 팔각 몸체, 까치발 회랑과 출입문, 흰 양털 돛의 십자 날개, 곡선 지붕 방앗간. 맷돌과 중심 축, 밀 더미, 빵 화덕, 층마다 사다리.",
         "data": windmill()},
    ]
