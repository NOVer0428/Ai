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


# ---------------------------------------------------------------- 엄격 점검 (현실형 템플릿)
# 몸이 지나갈 수 있는 블록 (충돌 없음 또는 열 수 있음)
BODY_OPEN = PASSABLE + ("_trapdoor", "fence_gate", "_sign", "lever", "redstone_wire", "_sapling", "flower")
# 걸어서 손이 닿아야 하는 가구
USE_TARGETS = ("_bed", "chest", "crafting_table", "furnace", "smoker", "barrel", "lectern", "cauldron",
               "smithing_table", "anvil", "loom", "cartography_table", "grindstone")
CLOSED_WHEN_SHUT = ("_door", "_trapdoor", "fence_gate")


def strict_check(data):
    """현실형 템플릿 점검.
      외피 구멍: 문·트랩도어를 닫은 상태에서 바깥 공기가 실내 가구에 닿음(벽·지붕의 빈 곳)
      걸어서 못 감: 계단 한 칸 높이·머리 위 2칸을 지키며 걸어서 닿지 못하는 가구
      외톨이 블록: 어느 면에도 붙지 않고 떠 있는 블록"""
    pal = data["palette"]
    cells = {(x, y, z): parse(pal[i]) for x, y, z, i in data["blocks"]}
    sx, sy, sz = data["size"]
    issues = []

    def inside(p, m=2):
        return -m <= p[0] < sx + m and 0 <= p[1] < sy + m and -m <= p[2] < sz + m

    def body_open(p):
        if p not in cells:
            return True
        n = cells[p][0]
        return any(k in n for k in BODY_OPEN)

    def air_open(p):  # 문을 닫았을 때 공기가 지나가는가
        if p not in cells:
            return True
        n = cells[p][0]
        if any(n.endswith(k) for k in CLOSED_WHEN_SHUT):
            return False
        return any(k in n for k in PASSABLE)

    def ground(p):  # 발밑이 받쳐지는가 (템플릿 아래는 땅)
        b = (p[0], p[1] - 1, p[2])
        return b[1] < 0 or not body_open(b)

    # 1) 외피 구멍
    seen = {(-1, 0, -1)}
    q = deque(seen)
    while q:
        x, y, z = q.popleft()
        for dx, dy, dz in DIRS6:
            p = (x + dx, y + dy, z + dz)
            if p not in seen and inside(p, 1) and air_open(p):
                seen.add(p)
                q.append(p)
    targets = [p for p, (n, _) in cells.items() if any(k in n for k in USE_TARGETS)]
    for p in targets:
        if any((p[0] + a, p[1] + b, p[2] + c) in seen for a, b, c in DIRS6):
            issues.append(("외피 구멍(바깥 공기가 닿음)", cells[p][0], p))
    # 벽 속 계단·반블록: 한쪽은 바깥 공기, 반대쪽은 실내 공기면 빈 곳으로 밖이 보인다
    # (계단은 디딤판 세운 면이 막고 있어 계단 방향 축으로는 안 보이고, 옆 방향 축으로만 뚫린다)
    for p, (n, props) in cells.items():
        if not (n.endswith("_stairs") or n.endswith("_slab") and props.get("type") != "double"):
            continue
        f = FACE.get(props.get("facing")) if n.endswith("_stairs") else None
        axes = [(f[2], f[0])] if f else [(1, 0), (0, 1)]       # 계단: 방향과 직각인 축만
        for dx, dz in axes:
            a, b = (p[0] + dx, p[1], p[2] + dz), (p[0] - dx, p[1], p[2] - dz)
            if any(o in seen and i not in seen and inside(i, 0) and air_open(i) for o, i in ((a, b), (b, a))):
                issues.append(("벽 속 계단·반블록 틈(밖이 보임)", n, p))

    # 2) 걸어서 닿는지
    def stand(p):
        if not (body_open(p) and body_open((p[0], p[1] + 1, p[2]))):
            return False
        n = cells.get(p, ("",))[0]
        return ground(p) or n == "ladder"

    def surface(p, came=None):
        """p 칸에 선 발의 높이. 밑이 아래쪽 반블록이면 반 칸 낮다.
        계단은 낮은 쪽(올라가는 방향과 계단 방향이 같을 때)으로 들어설 때만 반 칸, 옆·뒤에서는 한 칸."""
        n, props = cells.get((p[0], p[1] - 1, p[2]), ("", {}))
        if n.endswith("_slab") and props.get("type") == "bottom" or n.endswith("_bed"):   # 침대 높이 0.56
            return p[1] - 0.5
        if n.endswith("_stairs") and props.get("half") == "bottom" and came is not None:
            f = FACE.get(props.get("facing"))
            if f and (f[0], f[2]) == came:
                return p[1] - 0.5
        return p[1]

    start = (-2, 0, -2)
    reach = {start}
    q = deque([start])
    while q:
        x, y, z = q.popleft()
        moves = []
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = x + dx, z + dz
            if body_open((nx, y, nz)) and body_open((nx, y + 1, nz)):
                for dy in (0, -1, -2, -3):  # 같은 높이로 걷거나 내려가기
                    t = (nx, y + dy, nz)
                    if all(body_open((nx, y - k, nz)) for k in range(0, -dy + 1)) and stand(t):
                        moves.append(t)
                        break
            # 한 칸 올라가기: 실제 단차가 반 칸 이하일 때만 (점프 없이 걷는 높이 0.6)
            on_ladder = cells.get((x, y, z), ("",))[0] == "ladder"     # 사다리 끝에서는 타고 올라 내림
            if (body_open((x, y + 2, z)) and stand((nx, y + 1, nz))
                    and (on_ladder or surface((nx, y + 1, nz), (dx, dz)) - surface((x, y, z)) <= 0.6)):
                moves.append((nx, y + 1, nz))
        if cells.get((x, y, z), ("",))[0] == "ladder":
            moves += [(x, y + 1, z), (x, y - 1, z)]
        for t in moves:
            if t not in reach and inside(t) and stand(t):
                reach.add(t)
                q.append(t)
    body = reach | {(x, y + 1, z) for x, y, z in reach}
    for p in targets:
        near = [(p[0] + a, p[1], p[2] + c) for a, c in ((1, 0), (-1, 0), (0, 1), (0, -1))] + [(p[0], p[1] + 1, p[2])]
        if not any(c in body for c in near):
            issues.append(("걸어서 못 감", cells[p][0], p))

    # 문 앞뒤 두 칸은 몸이 지나갈 수 있어야 한다 (들어서자마자 가구에 막히지 않게)
    for p, (n, props) in cells.items():
        f = FACE.get(props.get("facing"))
        if not (n.endswith("_door") and props.get("half") == "lower" and f):
            continue
        for s in (1, -1):
            ahead = [(p[0] + f[0] * s * k, p[1] + h, p[2] + f[2] * s * k) for k in (1, 2) for h in (0, 1)]
            if not all(body_open(c) for c in ahead):
                issues.append(("문 앞이 막힘", n, p))

    # 3) 떠 있는 외톨이 블록
    for p, (n, _) in cells.items():
        if not any((p[0] + a, p[1] + b, p[2] + c) in cells for a, b, c in DIRS6) and p[1] > 0:
            issues.append(("떠 있는 블록", n, p))
    return issues
