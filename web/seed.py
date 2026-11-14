"""기본 제공 건물 템플릿 생성기. 정면(입구)은 z = 0, 북쪽(-z)을 바라본다."""

from template_format import normalize


class Builder:
    """size 를 주면 그 범위 밖은 버리고, 생략하면 음수 좌표도 허용한 뒤 build() 때 0 기준으로 옮긴다."""

    def __init__(self, sx=None, sy=None, sz=None):
        self.size = [sx, sy, sz] if sx is not None else None
        self.cells = {}

    def set(self, x, y, z, block):
        if self.size is None or (0 <= x < self.size[0] and 0 <= y < self.size[1] and 0 <= z < self.size[2]):
            if block is None:
                self.cells.pop((x, y, z), None)
            else:
                # 모든 블록은 26.3 블록 데이터로 검사·완성된 전체 상태로 저장 (없는 블록이면 오류)
                self.cells[(x, y, z)] = normalize(block)

    def fill(self, x1, y1, z1, x2, y2, z2, block):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.set(x, y, z, block)

    def hollow(self, x1, y1, z1, x2, y2, z2, block):
        for x in range(x1, x2 + 1):
            for y in range(y1, y2 + 1):
                for z in range(z1, z2 + 1):
                    if x in (x1, x2) or z in (z1, z2):
                        self.set(x, y, z, block)

    def door(self, x, y, z, wood="oak", facing="north"):
        self.set(x, y, z, f"minecraft:{wood}_door[facing={facing},half=lower,hinge=left,open=false]")
        self.set(x, y + 1, z, f"minecraft:{wood}_door[facing={facing},half=upper,hinge=left,open=false]")

    def build(self):
        size = self.size
        ox = oy = oz = 0
        if size is None:
            xs, ys, zs = zip(*self.cells)
            ox, oy, oz = min(xs), min(ys), min(zs)
            size = [max(xs) - ox + 1, max(ys) - oy + 1, max(zs) - oz + 1]
        palette, index, blocks = [], {}, []
        for (x, y, z), b in sorted(self.cells.items(), key=lambda kv: (kv[0][1], kv[0][2], kv[0][0])):
            if b not in index:
                index[b] = len(palette)
                palette.append(b)
            blocks.append([x - ox, y - oy, z - oz, index[b]])
        return {"size": size, "palette": palette, "blocks": blocks}


def cottage():
    b = Builder(9, 8, 7)
    b.fill(0, 0, 0, 8, 0, 6, "minecraft:cobblestone")
    b.hollow(0, 1, 0, 8, 3, 6, "minecraft:oak_planks")
    for x, z in [(0, 0), (8, 0), (0, 6), (8, 6)]:
        b.fill(x, 1, z, x, 3, z, "minecraft:oak_log[axis=y]")
    b.door(4, 1, 0)
    for x in (2, 6):
        b.set(x, 2, 0, "minecraft:glass_pane")
        b.set(x, 2, 6, "minecraft:glass_pane")
    b.set(0, 2, 3, "minecraft:glass_pane")
    b.set(8, 2, 3, "minecraft:glass_pane")
    # 박공 지붕: z 방향으로 경사
    for step in range(4):
        y = 4 + step
        b.fill(0, y, step, 8, y, step, "minecraft:spruce_stairs[facing=south,half=bottom,shape=straight]")
        b.fill(0, y, 6 - step, 8, y, 6 - step, "minecraft:spruce_stairs[facing=north,half=bottom,shape=straight]")
        if step > 0:
            for x in (0, 8):
                b.fill(x, y - 1, step, x, y - 1, 6 - step, "minecraft:oak_planks")
    b.fill(0, 7, 3, 8, 7, 3, "minecraft:spruce_slab[type=bottom]")
    b.set(4, 3, 5, "minecraft:lantern[hanging=false]")
    b.set(1, 1, 5, "minecraft:crafting_table")
    b.set(2, 1, 5, "minecraft:furnace[facing=north]")
    return b.build()


def watchtower():
    b = Builder(7, 16, 7)
    b.fill(0, 0, 0, 6, 0, 6, "minecraft:stone_bricks")
    b.hollow(1, 1, 1, 5, 11, 5, "minecraft:stone_bricks")
    for y in (4, 8):
        b.set(3, y, 1, "minecraft:iron_bars")
        b.set(3, y, 5, "minecraft:iron_bars")
        b.set(1, y, 3, "minecraft:iron_bars")
        b.set(5, y, 3, "minecraft:iron_bars")
    b.set(3, 1, 1, None)
    b.set(3, 2, 1, None)
    b.fill(2, 1, 4, 2, 11, 4, "minecraft:ladder[facing=north]")
    b.fill(0, 12, 0, 6, 12, 6, "minecraft:spruce_planks")
    b.set(2, 12, 4, None)
    for x in range(7):
        for z in range(7):
            if x in (0, 6) or z in (0, 6):
                b.set(x, 13, z, "minecraft:stone_brick_wall[up=true]" if (x + z) % 2 == 0 else "minecraft:air")
    b.cells = {k: v for k, v in b.cells.items() if v != "minecraft:air"}
    for x, z in [(0, 0), (6, 0), (0, 6), (6, 6)]:
        b.set(x, 13, z, "minecraft:stone_bricks")
        b.set(x, 14, z, "minecraft:torch")
    return b.build()


def well():
    b = Builder(5, 6, 5)
    b.fill(0, 0, 0, 4, 0, 4, "minecraft:cobblestone")
    b.hollow(0, 1, 0, 4, 1, 4, "minecraft:cobblestone")
    b.fill(1, 0, 1, 3, 0, 3, "minecraft:water[level=0]")
    for x, z in [(0, 0), (4, 0), (0, 4), (4, 4)]:
        b.fill(x, 2, z, x, 3, z, "minecraft:oak_fence")
    b.fill(0, 4, 0, 4, 4, 4, "minecraft:oak_slab[type=bottom]")
    b.set(2, 5, 2, "minecraft:oak_slab[type=bottom]")
    b.set(2, 3, 2, "minecraft:lantern[hanging=true]")
    return b.build()


def market_stall():
    b = Builder(5, 5, 4)
    b.fill(0, 0, 0, 4, 0, 3, "minecraft:spruce_planks")
    for x, z in [(0, 0), (4, 0), (0, 3), (4, 3)]:
        b.fill(x, 1, z, x, 3, z, "minecraft:spruce_fence")
    b.fill(1, 1, 0, 3, 1, 0, "minecraft:barrel[facing=up]")
    for x in range(5):
        color = "red" if x % 2 == 0 else "white"
        b.fill(x, 4, 0, x, 4, 3, f"minecraft:{color}_wool")
    b.set(2, 2, 0, "minecraft:lantern[hanging=false]")
    return b.build()


def garden_gazebo():
    b = Builder(7, 6, 7)
    b.fill(0, 0, 0, 6, 0, 6, "minecraft:smooth_stone")
    b.fill(1, 0, 1, 5, 0, 5, "minecraft:moss_block")
    for x, z in [(1, 1), (5, 1), (1, 5), (5, 5)]:
        b.fill(x, 1, z, x, 3, z, "minecraft:birch_log[axis=y]")
    b.fill(0, 4, 0, 6, 4, 6, "minecraft:birch_slab[type=bottom]")
    b.fill(1, 5, 1, 5, 5, 5, "minecraft:birch_slab[type=bottom]")
    for x, z in [(0, 2), (0, 4), (6, 2), (6, 4), (2, 6), (4, 6)]:
        b.set(x, 1, z, "minecraft:flowering_azalea")
    b.set(3, 1, 3, "minecraft:birch_planks")
    return b.build()


def seed_templates():
    from seed_medieval import medieval_templates

    return medieval_templates() + [
        {"name": "아늑한 오두막", "category": "주거",
         "description": "참나무와 가문비나무 지붕으로 만든 1인용 오두막. 작업대와 화로 포함.",
         "data": cottage()},
        {"name": "석재 감시탑", "category": "방어",
         "description": "사다리로 올라가는 16칸 높이의 돌벽돌 감시탑. 꼭대기에 횃불.",
         "data": watchtower()},
        {"name": "마을 우물", "category": "장식",
         "description": "물이 채워진 조약돌 우물과 지붕, 걸린 랜턴.",
         "data": well()},
        {"name": "시장 가판대", "category": "상업",
         "description": "빨강/하양 줄무늬 천막을 두른 작은 가판대.",
         "data": market_stall()},
        {"name": "정원 정자", "category": "장식",
         "description": "자작나무 기둥과 이끼 바닥, 꽃 핀 진달래로 꾸민 정자.",
         "data": garden_gazebo()},
    ]
