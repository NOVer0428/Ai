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


def seed_templates():
    """기본 제공 템플릿 목록. 여기서 빠진 기본 템플릿은 DB 에서도 지워진다 (db.init_db)."""
    from seed_townhouse import townhouse_templates
    from seed_village import village_templates

    return townhouse_templates() + village_templates()
