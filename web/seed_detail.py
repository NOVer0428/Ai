"""디테일 건축 도구 (Kit 확장).

레퍼런스와 비교해 부족했던 것을 채운다:
  - 겹벽: 들어간 창 + 인방(위 뒤집힌 계단) + 창턱(아래 계단) + 덧창, 돌출 기둥(받침·머리), 처마띠(코니스)
  - 곡선 지붕: 처마는 완만하고 용마루로 갈수록 가팔라지는 오목 곡선, 박공 끝 들림
  - 들림 처마 고리(탑·찻집), 진짜 반구 돔, 가파른 첨탑, 뾰족 아치 창, 둥근 창
  - 재료 그라데이션: 높이에 따라 아래→위로 자연스럽게 바뀌는 섞기
"""
import math

from seed_kit import DIRS, OPP, Kit, S, full_of


def h3(x, y, z):
    return ((x * 73856093) ^ (y * 19349663) ^ (z * 83492791)) & 0xFFFF


class Arch(Kit):
    # ------------------------------------------------------------ 재료
    @staticmethod
    def grad(blocks, y0, y1, jitter=0.3):
        """높이 그라데이션: blocks[0]이 아래, blocks[-1]이 위. 경계는 무작위로 흐리게."""
        n = len(blocks)

        def pick(x, y, z):
            t = (y - y0) / max(1, y1 - y0)
            t += ((h3(x, y, z) % 1000) / 1000 - 0.5) * jitter
            return blocks[max(0, min(n - 1, int(t * n)))]
        return pick

    # ------------------------------------------------------------ 겹벽
    def recessed_window(self, x, y, z, out, w=1, h=2, glass="glass_pane", lintel=None, sill=None,
                        shutter=None, depth=1, box=None):
        """(x,y,z)=벽면 위 창의 좌표 작은 쪽 아래 칸. 유리는 depth 칸 안쪽, 바깥에 인방·창턱·덧창."""
        ox, oz = DIRS[out]
        along = "x" if oz else "z"
        sx, sz = (1, 0) if along == "x" else (0, 1)
        inward = OPP[out]
        for i in range(w):
            wx, wz = x + sx * i, z + sz * i
            for j in range(h):
                self.set(wx, y + j, wz, None)
                for d in range(1, depth):
                    self.set(wx - ox * d, y + j, wz - oz * d, None)
                self.pane(wx - ox * depth, y + j, wz - oz * depth, along, glass)
            if lintel:
                self.set(wx + ox, y + h, wz + oz, S(f"{lintel}_stairs", facing=inward, half="top"))
            if sill:
                self.set(wx + ox, y - 1, wz + oz, S(f"{sill}_stairs", facing=inward))
            if box:
                self.set(wx + ox, y - 1, wz + oz, box)
        if lintel:
            for i in (-1, w):
                self.set(x + sx * i + ox, y + h, z + sz * i + oz, S(f"{lintel}_slab", type="top"))
        if shutter:
            for j in range(h):
                for i in (-1, w):
                    self.set(x + sx * i + ox, y + j, z + sz * i + oz,
                             S(f"{shutter}_trapdoor", facing=out, open=True))

    def pilaster(self, x, z, out, y0, y1, blk, base=None, cap=None):
        """벽 (x,z) 바깥으로 한 칸 튀어나온 기둥. base/cap 은 계단 재료."""
        ox, oz = DIRS[out]
        px, pz = x + ox, z + oz
        for y in range(y0, y1 + 1):
            self.set(px, y, pz, blk(px, y, pz) if callable(blk) else blk)
        if base:
            self.set(px, y0, pz, S(f"{base}_stairs", facing=OPP[out]))
        if cap:
            self.set(px, y1 + 1, pz, S(f"{cap}_stairs", facing=OPP[out], half="top"))

    def cornice(self, x0, z0, x1, z1, y, mat, half="top"):
        """벽 둘레 바깥 한 칸에 두르는 처마띠/허리띠."""
        for x in range(x0, x1 + 1):
            self.set(x, y, z0 - 1, S(f"{mat}_stairs", facing="south", half=half))
            self.set(x, y, z1 + 1, S(f"{mat}_stairs", facing="north", half=half))
        for z in range(z0, z1 + 1):
            self.set(x0 - 1, y, z, S(f"{mat}_stairs", facing="east", half=half))
            self.set(x1 + 1, y, z, S(f"{mat}_stairs", facing="west", half=half))
        for x, z in ((x0 - 1, z0 - 1), (x1 + 1, z0 - 1), (x0 - 1, z1 + 1), (x1 + 1, z1 + 1)):
            self.set(x, y, z, S(f"{mat}_slab", type="top" if half == "top" else "bottom"))

    # ------------------------------------------------------------ 곡선 지붕
    @staticmethod
    def concave(m, start=1):
        """처마→용마루 오목 곡선의 줄별 꼭대기 높이(반 칸 단위)."""
        tops, t = [], start
        for i in range(m):
            tops.append(t)
            t += 1 if i < 2 else 2 if i < m * 0.6 else 3
        return tops

    def _roof_cell(self, x, z, y0, top, mat, facing, below_top, fill):
        """반 칸 단위 꼭대기 top 에 맞춰 반블록/계단을 놓고, 아래 틈은 꽉 찬 블록으로 메운다."""
        if top % 2:
            y = y0 + (top - 1) // 2
            self.set(x, y, z, S(f"{mat}_slab"))
        else:
            y = y0 + top // 2 - 1
            self.set(x, y, z, S(f"{mat}_stairs", facing=facing))
        bottom_needed = y0 + below_top // 2  # 이전 줄 꼭대기가 반 칸이면 그 칸부터 채워 틈을 없앤다
        for yy in range(bottom_needed, y):
            self.set(x, yy, z, fill)
        return y

    def curved_gable(self, x0, x1, z0, z1, y0, mat, ridge="x", lift=True, trim=None, gable_fill=None,
                     wall_top=None, pitch="concave"):
        """오목 곡선 박공지붕. 범위는 처마 포함. lift: 박공 끝 처마 두 줄을 반 칸 들어 올림.
        gable_fill: 양 끝 삼각벽(한 칸 안쪽), wall_top: 삼각벽을 채우기 시작할 높이."""
        fill = S(full_of(mat))
        if ridge == "x":
            a0, a1, b0, b1 = z0, z1, x0, x1
        else:
            a0, a1, b0, b1 = x0, x1, z0, z1
        n = a1 - a0 + 1
        m = n // 2
        # concave: 처마 완만→용마루 가파름 / low: 한 줄에 반 칸씩(1:2 완만한 기와 지붕)
        tops = self.concave(m) if pitch == "concave" else list(range(1, m + 1))
        lo_face, hi_face = ("south", "north") if ridge == "x" else ("east", "west")
        ridge_y = y0
        for i in range(m):
            prev = tops[i - 1] if i else 0
            for b in range(b0, b1 + 1):
                t = tops[i] + (1 if lift and i < 2 and b in (b0, b1) else 0)
                for a, f in ((a0 + i, lo_face), (a1 - i, hi_face)):
                    x, z = (b, a) if ridge == "x" else (a, b)
                    ridge_y = max(ridge_y, self._roof_cell(x, z, y0, t, mat, f, prev, fill))
                    if trim and b in (b0, b1) and i > 0:
                        tf = hi_face if f == lo_face else lo_face
                        yy = y0 + (tops[i] - 1) // 2 - 1
                        self.set(x, yy, z, S(f"{trim}_stairs", facing=tf, half="top")) if yy >= y0 else None
        top_y = y0 + (tops[-1] + 1) // 2
        if n % 2:
            mid = a0 + m
            for b in range(b0, b1 + 1):
                x, z = (b, mid) if ridge == "x" else (mid, b)
                for yy in range(y0 + (tops[-1]) // 2, top_y + 1):
                    self.set(x, yy, z, fill)
                self.set(x, top_y + 1, z, S(f"{mat}_slab"))
            top_y += 1
        if gable_fill:
            start = wall_top if wall_top is not None else y0
            for i in range(m + (n % 2)):
                lim = tops[min(i, m - 1)]
                ymax = y0 + (lim - 1) // 2 if i < m else top_y - 1
                for side in (b0 + 1, b1 - 1):
                    for a in ((a0 + i, a1 - i) if i < m else (a0 + m,)):
                        for yy in range(start, ymax):
                            x, z = (side, a) if ridge == "x" else (a, side)
                            if self.cells.get((x, yy, z)) is None:
                                self.set(x, yy, z, gable_fill)
        return top_y

    def eave_ring(self, x0, z0, x1, z1, y, mat, kind="stairs", horn=True):
        """사각 고리 처마 한 줄(아래가 바깥). horn: 네 모서리를 한 칸 들어 올린 뿔."""
        def put(x, z, f):
            if kind == "slab":
                self.set(x, y, z, S(f"{mat}_slab"))
            else:
                self.set(x, y, z, S(f"{mat}_stairs", facing=f))
        for x in range(x0 + 1, x1):
            put(x, z0, "south")
            put(x, z1, "north")
        for z in range(z0 + 1, z1):
            put(x0, z, "east")
            put(x1, z, "west")
        for x, z in ((x0, z0), (x1, z0), (x0, z1), (x1, z1)):
            if horn:
                self.set(x, y, z, S(full_of(mat)))
                self.set(x, y + 1, z, S(f"{mat}_slab"))
            else:
                self.set(x, y, z, S(f"{mat}_slab"))

    def flared_hip(self, x0, z0, x1, z1, y, mat, until=1):
        """탑·찻집용 들림 모임지붕: 바깥 고리는 반블록(얇은 처마) + 들린 모서리, 안쪽으로 계단 고리.
        until: 남길 최소 반폭(그보다 작아지면 멈춤). 마지막 y 를 돌려준다."""
        self.eave_ring(x0, z0, x1, z1, y, mat, kind="slab", horn=True)
        x0, z0, x1, z1 = x0 + 1, z0 + 1, x1 - 1, z1 - 1
        while (x1 - x0) // 2 >= until and (z1 - z0) // 2 >= until:
            self.eave_ring(x0, z0, x1, z1, y, mat, horn=False)
            x0, z0, x1, z1, y = x0 + 1, z0 + 1, x1 - 1, z1 - 1, y + 1
        return y, (x0, z0, x1, z1)

    # ------------------------------------------------------------ 둥근 것들
    def dome(self, cx, cz, r, y0, mat, cap=None):
        """반구 껍데기(속 빔). 높이를 반 칸 단위로 계산해 꼭대기는 반블록/꽉 찬 블록으로 둥글게,
        이웃 기둥보다 높은 부분은 아래까지 이어 틈을 없앤다. mat 는 반블록이 있는 재료 이름."""
        R = r + 0.5
        full = S(full_of(mat))
        tops = {}
        for dx in range(-r - 1, r + 2):
            for dz in range(-r - 1, r + 2):
                d2 = dx * dx + dz * dz
                if d2 <= R * R:
                    tops[(dx, dz)] = max(1, int(round(2 * math.sqrt(max(0.0, R * R - d2)))))
        for (dx, dz), t in tops.items():
            nb = [tops.get((dx + a, dz + b), 0) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            low = min(nb) // 2
            top_y = (t - 1) // 2
            for yy in range(low, top_y):
                self.set(cx + dx, y0 + yy, cz + dz, full)
            self.set(cx + dx, y0 + top_y, cz + dz, S(f"{mat}_slab") if t % 2 else full)
        top = y0 + (tops[(0, 0)] - 1) // 2
        if cap:
            self.set(cx, top + 1, cz, cap)
        return top

    def spire(self, cx, cz, r, y0, mat, rise=2, tip=None):
        """가파른 사각 첨탑: 한 단마다 rise 칸씩 올라가며 반폭 1씩 줄어듦."""
        y = y0
        fill = S(full_of(mat))
        while r >= 1:
            x0, x1, z0, z1 = cx - r, cx + r, cz - r, cz + r
            self.eave_ring(x0, z0, x1, z1, y, mat, horn=False)
            for k in range(1, rise):
                for x in range(x0 + 1, x1):
                    self.set(x, y + k, z0 + 1, fill) if r > 1 else None
                    self.set(x, y + k, z1 - 1, fill) if r > 1 else None
                for z in range(z0 + 1, z1):
                    self.set(x0 + 1, y + k, z, fill) if r > 1 else None
                    self.set(x1 - 1, y + k, z, fill) if r > 1 else None
            y += rise
            r -= 1
        self.set(cx, y - rise + 1, cz, fill)
        for k in range(rise):
            self.set(cx, y - rise + 1 + k, cz, fill)
        top = y
        if tip:
            self.set(cx, top, cz, tip)
        return top

    def arch_window(self, x, y, z, out, w, h, glass, stair, depth=1):
        """뾰족 아치 창: 직사각 유리 위에 양 모서리 뒤집힌 계단, 가운데는 한 칸 더 높게."""
        ox, oz = DIRS[out]
        along = "x" if oz else "z"
        sx, sz = (1, 0) if along == "x" else (0, 1)
        lf, rf = ("west", "east") if along == "x" else ("north", "south")
        for i in range(w):
            for j in range(h):
                wx, wz = x + sx * i, z + sz * i
                self.set(wx, y + j, wz, None)
                self.pane(wx - ox * depth, y + j, wz - oz * depth, along, glass)
        if w >= 2:
            self.set(x, y + h - 1, z, S(f"{stair}_stairs", facing=lf, half="top"))
            self.set(x + sx * (w - 1), y + h - 1, z + sz * (w - 1), S(f"{stair}_stairs", facing=rf, half="top"))
        mid = (w - 1) // 2
        mx, mz = x + sx * mid, z + sz * mid
        self.pane(mx - ox * depth, y + h, mz - oz * depth, along, glass)
        self.set(mx, y + h, mz, None)
        if w % 2 == 0:
            self.pane(mx + sx - ox * depth, y + h, mz + sz - oz * depth, along, glass)
            self.set(mx + sx, y + h, mz + sz, None)

    def round_window(self, cx, cy, plane, axis, r, frame, glass, inset=0):
        """세로 평면의 둥근 창. axis='x': z=plane 인 벽(동서로 펼침), 'z': x=plane 인 벽."""
        for a in range(-r - 1, r + 2):
            for b in range(-r - 1, r + 2):
                d = math.sqrt(a * a + b * b)
                if d <= r + 0.5:
                    p = (cx + a, cy + b, plane) if axis == "x" else (plane, cy + b, cx + a)
                    if d > r - 0.6:
                        self.set(*p, frame)
                    else:
                        self.set(*p, glass)


__all__ = ["Arch", "S", "DIRS", "OPP", "full_of", "h3", "math"]
