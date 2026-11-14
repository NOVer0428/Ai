"""템플릿 구조 자동 점검 (게임에서 무너지거나 못 들어가는 곳 찾기).

  python qa.py            # 기본 템플릿 전부 점검
점검 항목
  지지: 사다리·벽걸이(뒤), 매다는 것(위), 바닥에 놓는 것(아래), 문 아래
  짝: 문 위/아래, 침대 머리/발
  유체: 물·용암 아래·옆이 비어 흘러넘칠 곳
  막힌 방: 바깥에서 사람이 지나갈 수 있는 칸(공기·문·사다리·카펫…)으로 닿지 않는 가구 있는 공간
"""
from collections import deque

DIRS6 = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
FACE = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0)}

NEEDS_BELOW = ("carpet", "pressure_plate", "candle", "flower_pot", "potted_", "_sapling", "rail", "torch",
               "redstone_wire", "repeater", "comparator", "lily_pad", "short_grass", "fern", "azalea",
               "eyeblossom", "tulip", "bluet", "bamboo", "cake", "brewing_stand", "decorated_pot")
NEEDS_ABOVE = ("hanging_roots", "spore_blossom", "pale_hanging_moss")
FURNITURE = ("bed", "chest", "barrel", "crafting_table", "furnace", "smoker", "anvil", "lectern", "cauldron",
             "brewing_stand", "_shelf", "bookshelf", "smithing_table", "grindstone", "crafter", "bell",
             "cartography_table", "loom", "composter")
PASSABLE = ("_door", "ladder", "carpet", "pressure_plate", "wall_banner", "candle", "button", "vine",
            "hanging_roots", "spore_blossom", "pale_hanging_moss", "short_grass", "torch", "rail")


def parse(state):
    bid, _, rest = state.partition("[")
    props = dict(kv.split("=", 1) for kv in rest.rstrip("]").split(",")) if rest else {}
    return bid.split(":", 1)[1], props


def check(data):
    pal = data["palette"]
    cells = {(x, y, z): pal[i] for x, y, z, i in data["blocks"]}
    issues = []

    def has(p):
        return p in cells

    def name(p):
        return parse(cells[p])[0] if p in cells else None

    for p, st in cells.items():
        x, y, z = p
        n, pr = parse(st)
        below, above = (x, y - 1, z), (x, y + 1, z)
        # 매다는 것
        if pr.get("hanging") == "true" or any(k in n for k in NEEDS_ABOVE) or \
                (n == "bell" and pr.get("attachment") == "ceiling"):
            if not has(above):
                issues.append(("위 지지 없음", n, p))
        # 바닥에 놓는 것
        elif (any(k in n for k in NEEDS_BELOW) and "wall" not in n and not n.endswith("_leaves")) or \
                (n in ("lantern", "soul_lantern", "copper_lantern") and pr.get("hanging") == "false") or \
                (n == "bell" and pr.get("attachment") == "floor"):
            if not has(below):
                issues.append(("아래 지지 없음", n, p))
        # 문 아래
        if n.endswith("_door") and pr.get("half") == "lower" and not has(below):
            issues.append(("문 아래 비어 있음", n, p))
        # 벽에 붙는 것
        if n == "ladder" or n.endswith("wall_banner") or n.endswith("wall_hanging_sign"):
            dx, dy, dz = FACE[pr["facing"]]
            back = (x - dx, y, z - dz)
            if not has(back) or name(back) in ("ladder",):
                issues.append(("뒤 벽 없음", n, p))
        # 짝
        if n.endswith("_door"):
            other = above if pr.get("half") == "lower" else below
            if name(other) != n:
                issues.append(("문 짝 없음", n, p))
        if n.endswith("_bed"):
            dx, _, dz = FACE[pr["facing"]]
            other = (x + dx, y, z + dz) if pr.get("part") == "foot" else (x - dx, y, z - dz)
            if name(other) != n:
                issues.append(("침대 짝 없음", n, p))
        # 유체
        if n in ("water", "lava"):
            for d in [(0, -1, 0), (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1)]:
                q = (x + d[0], y + d[1], z + d[2])
                if not has(q):
                    issues.append(("유체가 샐 수 있음", n, p))
                    break

    # 막힌 방: 템플릿 둘레 한 칸 바깥에서 지나갈 수 있는 칸으로 채우기
    sx, sy, sz = data["size"]

    def passable(p):
        if p not in cells:
            return True
        n, pr = parse(cells[p])
        if any(k in n for k in PASSABLE):
            return True
        if n.endswith("_trapdoor") and pr.get("open") == "true":
            return True
        return False
    seen = set()
    start = (-1, 0, -1)
    q = deque([start])
    seen.add(start)
    while q:
        x, y, z = q.popleft()
        for dx, dy, dz in DIRS6:
            p = (x + dx, y + dy, z + dz)
            if p in seen or not (-1 <= p[0] <= sx and -1 <= p[1] <= sy and -1 <= p[2] <= sz):
                continue
            if passable(p):
                seen.add(p)
                q.append(p)
    sealed = set()
    for p, st in cells.items():
        n, _ = parse(st)
        if not any(k in n for k in FURNITURE):
            continue
        reach = any((p[0] + dx, p[1] + dy, p[2] + dz) in seen for dx, dy, dz in DIRS6)
        if not reach:
            sealed.add(n)
            issues.append(("들어갈 수 없는 곳의 가구", n, p))
    return issues


def main():
    import sys
    sys.path.insert(0, ".")
    from seed import seed_templates
    from template_format import validate
    total = 0
    for t in seed_templates():
        issues = check(validate(t["data"]))
        total += len(issues)
        print(f"== {t['name']}: {len(issues)}")
        for kind, n, p in issues[:40]:
            print(f"   {kind}: {n} @ {p}")
    print("합계", total)


if __name__ == "__main__":
    main()
