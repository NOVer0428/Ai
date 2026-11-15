"""템플릿 생성용 공용 건축 도구.

좌표: 정면(입구) = z 가 작은 쪽(북쪽). 모든 블록은 26.3 블록 데이터(state)로 만든다.
방향 규칙
  계단 facing=F  : 높은 쪽(등받이)이 F 방향. 지붕은 용마루 쪽을 향하게.
  트랩도어 열림 F: F 반대쪽 벽에 붙는다(덧창은 바깥 방향 F).
  사다리/벽 횃불 F: 벽에서 F 방향으로 튀어나옴.
  침대 facing    : 발 → 머리 방향.
"""
import math

from seed import Builder
from template_format import block_registry
from template_format import state as S

DIRS = {"north": (0, -1), "south": (0, 1), "west": (-1, 0), "east": (1, 0)}
OPP = {"north": "south", "south": "north", "west": "east", "east": "west"}


def full_of(mat):
    """계단 재료 이름 → 같은 재료의 꽉 찬 블록 id (26.3 데이터에서 찾음)."""
    reg = block_registry()
    for c in (mat + "s", mat + "_planks", mat, mat + "_block", mat.replace("_brick", "_bricks")):
        if "minecraft:" + c in reg:
            return c
    raise ValueError(f"꽉 찬 블록을 찾을 수 없음: {mat}")


def axis_of(facing):
    return "x" if facing in ("east", "west") else "z"


class Kit(Builder):
    """Builder + 건축 부품."""

    # ------------------------------------------------------------ 기본
    def fill(self, x1, y1, z1, x2, y2, z2, block):
        """블록 문자열 또는 (x,y,z)->블록 함수(재료 섞기·그라데이션)로 채운다."""
        if not callable(block):
            return super().fill(x1, y1, z1, x2, y2, z2, block)
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    self.set(x, y, z, block(x, y, z))

    def box(self, x0, y0, z0, x1, y1, z1, blk):
        self.fill(x0, y0, z0, x1, y1, z1, blk)

    def clear(self, x0, y0, z0, x1, y1, z1):
        self.fill(x0, y0, z0, x1, y1, z1, None)

    def walls(self, x0, z0, x1, z1, y0, y1, blk):
        """직사각형 둘레 벽. blk 는 블록 문자열 또는 (x,y,z)->블록 함수."""
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                for z in range(z0, z1 + 1):
                    if x in (x0, x1) or z in (z0, z1):
                        self.set(x, y, z, blk(x, y, z) if callable(blk) else blk)

    def floor(self, x0, z0, x1, z1, y, blk):
        self.fill(x0, y, z0, x1, y, z1, blk)

    def frame(self, x0, z0, x1, z1, y0, y1, post, beam=None, posts_every=None):
        """모서리 기둥(+간격 기둥)과 위·아래 테두리 들보."""
        xs = {x0, x1} | (set(range(x0, x1 + 1, posts_every)) if posts_every else set())
        zs = {z0, z1} | (set(range(z0, z1 + 1, posts_every)) if posts_every else set())
        for x in xs:
            for z in (z0, z1):
                self.fill(x, y0, z, x, y1, z, S(post, axis="y"))
        for z in zs:
            for x in (x0, x1):
                self.fill(x, y0, z, x, y1, z, S(post, axis="y"))
        if beam:  # 위 테두리 들보
            for x in range(x0, x1 + 1):
                self.set(x, y1, z0, S(post, axis="x"))
                self.set(x, y1, z1, S(post, axis="x"))
            for z in range(z0, z1 + 1):
                self.set(x0, y1, z, S(post, axis="z"))
                self.set(x1, y1, z, S(post, axis="z"))

    # ------------------------------------------------------------ 개구부
    def pane(self, x, y, z, along, blk="glass_pane"):
        """along='x' 면 동서로 이어지는 유리판 (북/남 벽용)."""
        if along == "x":
            self.set(x, y, z, S(blk, east=True, west=True))
        else:
            self.set(x, y, z, S(blk, north=True, south=True))

    def window(self, x, y, z, out, w=1, h=1, glass="glass_pane", shutter=None, sill=None, box=None):
        """out 방향(바깥)을 보는 벽의 창. (x,y,z)=왼쪽 아래(바깥에서 볼 때 아님, 좌표 작은 쪽).
        shutter: 나무 이름(덧창), sill: 창턱 블록(아래 바깥), box: 화단 블록(아래 바깥)."""
        ox, oz = DIRS[out]
        along = "x" if oz else "z"
        sx, sz = (1, 0) if along == "x" else (0, 1)
        for i in range(w):
            for j in range(h):
                self.pane(x + sx * i, y + j, z + sz * i, along, glass)
        if shutter:
            for j in range(h):
                self.set(x - sx + ox, y + j, z - sz + oz, S(f"{shutter}_trapdoor", facing=out, open=True))
                self.set(x + sx * w + ox, y + j, z + sz * w + oz, S(f"{shutter}_trapdoor", facing=out, open=True))
        for i in range(w):
            if sill:
                self.set(x + sx * i + ox, y - 1, z + sz * i + oz, sill)
            if box:
                self.set(x + sx * i + ox, y - 1, z + sz * i + oz, box)

    def door(self, x, y, z, wood, facing="north", hinge="left"):
        self.set(x, y, z, S(f"{wood}_door", facing=facing, half="lower", hinge=hinge))
        self.set(x, y + 1, z, S(f"{wood}_door", facing=facing, half="upper", hinge=hinge))

    def double_door(self, x, y, z, wood, facing="north"):
        """x(또는 z) 방향으로 두 칸 문."""
        dx, dz = (1, 0) if facing in ("north", "south") else (0, 1)
        self.door(x, y, z, wood, facing, "left")
        self.door(x + dx, y, z + dz, wood, facing, "right")

    # ------------------------------------------------------------ 지붕
    def gable(self, x0, x1, z0, z1, y0, mat, ridge="x", full=None, slab=None,
              gable_fill=None, trim=None):
        """박공지붕. (x0..x1, z0..z1)는 처마 포함 범위. ridge='x' 면 앞뒤(z)로 경사.
        gable_fill: 양 끝 삼각벽 블록(한 칸 안쪽), trim: 처마 끝 아래 뒤집힌 계단 재료."""
        full = full or full_of(mat)
        slab = slab or mat + "_slab"
        if ridge == "x":
            n, a0, a1 = z1 - z0 + 1, z0, z1
        else:
            n, a0, a1 = x1 - x0 + 1, x0, x1
        steps = n // 2
        lo_face, hi_face = ("south", "north") if ridge == "x" else ("east", "west")
        for i in range(steps):
            y = y0 + i
            if ridge == "x":
                for x in range(x0, x1 + 1):
                    self.set(x, y, a0 + i, S(f"{mat}_stairs", facing=lo_face))
                    self.set(x, y, a1 - i, S(f"{mat}_stairs", facing=hi_face))
            else:
                for z in range(z0, z1 + 1):
                    self.set(a0 + i, y, z, S(f"{mat}_stairs", facing=lo_face))
                    self.set(a1 - i, y, z, S(f"{mat}_stairs", facing=hi_face))
            if gable_fill and i >= 1:
                for c in range(a0 + i + 1, a1 - i):
                    if ridge == "x":
                        self.set(x0 + 1, y, c, gable_fill)
                        self.set(x1 - 1, y, c, gable_fill)
                    else:
                        self.set(c, y, z0 + 1, gable_fill)
                        self.set(c, y, z1 - 1, gable_fill)
            if trim and i >= 1:
                if ridge == "x":
                    for x in (x0, x1):
                        self.set(x, y - 1, a0 + i, S(f"{trim}_stairs", facing=hi_face, half="top"))
                        self.set(x, y - 1, a1 - i, S(f"{trim}_stairs", facing=lo_face, half="top"))
                else:
                    for z in (z0, z1):
                        self.set(a0 + i, y - 1, z, S(f"{trim}_stairs", facing=hi_face, half="top"))
                        self.set(a1 - i, y - 1, z, S(f"{trim}_stairs", facing=lo_face, half="top"))
        top = y0 + steps - 1
        if n % 2:
            mid = a0 + steps
            if gable_fill:
                for y in range(y0 + 1, y0 + steps):
                    if ridge == "x":
                        self.set(x0 + 1, y, mid, gable_fill)
                        self.set(x1 - 1, y, mid, gable_fill)
                    else:
                        self.set(mid, y, z0 + 1, gable_fill)
                        self.set(mid, y, z1 - 1, gable_fill)
            rng = range(x0, x1 + 1) if ridge == "x" else range(z0, z1 + 1)
            for c in rng:
                p = (c, y0 + steps - 1, mid) if ridge == "x" else (mid, y0 + steps - 1, c)
                self.set(*p, S(full))
                self.set(p[0], p[1] + 1, p[2], S(slab))
            top = y0 + steps
        return top

    def hip(self, x0, x1, z0, z1, y0, mat, full=None, slab=None, flare=False):
        """모임지붕: 네 방향 모두 경사. 층마다 한 칸씩 줄어든다. 꼭대기 y 반환."""
        full = full or full_of(mat)
        slab = slab or mat + "_slab"
        y = y0
        while x0 <= x1 and z0 <= z1:
            if x1 - x0 < 1 or z1 - z0 < 1:
                for x in range(x0, x1 + 1):
                    for z in range(z0, z1 + 1):
                        self.set(x, y, z, S(slab))
                return y
            for x in range(x0 + 1, x1):
                self.set(x, y, z0, S(f"{mat}_stairs", facing="south"))
                self.set(x, y, z1, S(f"{mat}_stairs", facing="north"))
            for z in range(z0 + 1, z1):
                self.set(x0, y, z, S(f"{mat}_stairs", facing="east"))
                self.set(x1, y, z, S(f"{mat}_stairs", facing="west"))
            self.set(x0, y, z0, S(f"{mat}_stairs", facing="south", shape="outer_left"))
            self.set(x1, y, z0, S(f"{mat}_stairs", facing="south", shape="outer_right"))
            self.set(x0, y, z1, S(f"{mat}_stairs", facing="north", shape="outer_right"))
            self.set(x1, y, z1, S(f"{mat}_stairs", facing="north", shape="outer_left"))
            if flare and y == y0:
                for x in range(x0, x1 + 1):
                    self.set(x, y - 1, z0 - 1, S(f"{mat}_slab", type="top"))
                    self.set(x, y - 1, z1 + 1, S(f"{mat}_slab", type="top"))
                for z in range(z0, z1 + 1):
                    self.set(x0 - 1, y - 1, z, S(f"{mat}_slab", type="top"))
                    self.set(x1 + 1, y - 1, z, S(f"{mat}_slab", type="top"))
            x0, x1, z0, z1, y = x0 + 1, x1 - 1, z0 + 1, z1 - 1, y + 1
        return y - 1

    def flat_roof(self, x0, z0, x1, z1, y, blk, parapet=None, cap=None):
        self.floor(x0, z0, x1, z1, y, blk)
        if parapet:
            self.walls(x0, z0, x1, z1, y + 1, y + 1, parapet)
        if cap:
            self.walls(x0, z0, x1, z1, y + 1, y + 1, cap)

    # ------------------------------------------------------------ 원형
    @staticmethod
    def disc(r):
        """반지름 r 원 안의 (dx,dz)."""
        rr = (r + 0.45) ** 2
        return {(dx, dz) for dx in range(-r - 1, r + 2) for dz in range(-r - 1, r + 2) if dx * dx + dz * dz <= rr}

    @classmethod
    def ring(cls, r):
        d = cls.disc(r)
        return {p for p in d if any((p[0] + a, p[1] + b) not in d for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))}

    def cylinder(self, cx, cz, r, y0, y1, wall, fill=None):
        for y in range(y0, y1 + 1):
            for dx, dz in self.disc(r):
                if (dx, dz) in self.ring(r):
                    self.set(cx + dx, y, cz + dz, wall(cx + dx, y, cz + dz) if callable(wall) else wall)
                elif fill:
                    self.set(cx + dx, y, cz + dz, fill)

    def cone(self, cx, cz, r, y0, mat, tip=None, step=1, full=None):
        """원뿔 지붕: 반지름을 step 층마다 1씩 줄이며 바깥쪽으로 내려가는 계단."""
        y = y0
        while r >= 1:
            for _ in range(step):
                for dx, dz in self.ring(r):
                    if abs(dx) >= abs(dz):
                        f = "west" if dx > 0 else "east"
                    else:
                        f = "north" if dz > 0 else "south"
                    self.set(cx + dx, y, cz + dz, S(f"{mat}_stairs", facing=f))
                y += 1
            r -= 1
        self.set(cx, y, cz, S(full or full_of(mat)))
        if tip:
            self.set(cx, y + 1, cz, tip)
            return y + 1
        return y

    # ------------------------------------------------------------ 실내 가구
    def table(self, x, y, z, wood, top=None):
        self.set(x, y, z, S(f"{wood}_fence"))
        self.set(x, y + 1, z, top or S(f"{wood}_pressure_plate"))

    def chair(self, x, y, z, wood, back):
        """back = 등받이 방향."""
        self.set(x, y, z, S(f"{wood}_stairs", facing=back))

    def bed(self, x, y, z, color, facing):
        dx, dz = DIRS[facing]
        self.set(x, y, z, S(f"{color}_bed", facing=facing, part="foot"))
        self.set(x + dx, y, z + dz, S(f"{color}_bed", facing=facing, part="head"))

    def rug(self, x0, z0, x1, z1, y, color, border=None):
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                edge = x in (x0, x1) or z in (z0, z1)
                cur = self.cells.get((x, y, z))
                if cur is not None and not cur.endswith("_carpet"):
                    continue  # 침대·의자 등 이미 놓인 가구는 그대로 둔다
                self.set(x, y, z, S(f"{(border if edge and border else color)}_carpet"))

    def counter(self, x0, z0, x1, z1, y, wood, facing):
        """부엌 조리대: 아래 통/상자 + 위 뒤집힌 반블록 대신 트랩도어 상판."""
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                self.set(x, y, z, S("barrel", facing=facing))
                self.set(x, y + 1, z, S(f"{wood}_trapdoor", facing=facing, half="bottom"))

    def shelf_wall(self, x0, z0, x1, z1, y, wood, facing):
        """26.x 나무 선반을 벽을 따라."""
        for x in range(x0, x1 + 1):
            for z in range(z0, z1 + 1):
                self.set(x, y, z, S(f"{wood}_shelf", facing=facing))

    def ladder(self, x, z, y0, y1, facing):
        for y in range(y0, y1 + 1):
            self.set(x, y, z, S("ladder", facing=facing))

    def hang(self, x, y, z, blk="lantern"):
        self.set(x, y, z, S(blk, hanging=True))

    def stair_run(self, x, y, z, facing, n, mat, support=None):
        """facing 방향으로 올라가는 계단 n 칸."""
        dx, dz = DIRS[facing]
        for i in range(n):
            self.set(x + dx * i, y + i, z + dz * i, S(f"{mat}_stairs", facing=facing))
            if support:
                for yy in range(y, y + i):
                    self.set(x + dx * i, yy, z + dz * i, support)


def mix(*choices):
    """결정적 재료 섞기: mix((블록, 가중치), ...) → (x,y,z)->블록"""
    total = sum(w for _, w in choices)

    def pick(x, y, z):
        h = (x * 73856093 ^ y * 19349663 ^ z * 83492791) % total
        for blk, w in choices:
            if h < w:
                return blk
            h -= w
        return choices[-1][0]
    return pick


def facing_from(dx, dz):
    if abs(dx) >= abs(dz):
        return "east" if dx > 0 else "west"
    return "south" if dz > 0 else "north"


__all__ = ["Kit", "S", "full_of", "mix", "DIRS", "OPP", "axis_of", "facing_from", "math"]
