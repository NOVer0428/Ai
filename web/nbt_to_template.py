"""구조물 파일(.nbt / .schem) → 사이트 업로드용 템플릿 JSON 변환기.

사용법:
    python nbt_to_template.py 입력.nbt [-o 출력.json] [--facing south]

- .nbt  : 바닐라 구조물 파일 (구조물 블록, minecraft-builder-skill 출력)
- .schem: Sponge 스키매틱 v2/v3 (WorldEdit, minecraft-build-design 출력)

--facing 에는 원본 건물의 입구가 바라보는 방향을 준다. 템플릿 규칙(입구는 z=0 쪽,
북쪽을 바라봄)에 맞도록 건물과 블록 상태(facing, axis, rotation, 연결 방향 등)를 함께 회전한다.
공기/structure_void 는 빼고, 빈 여백은 잘라낸다. 결과는 template_format.validate 로 검사한다.
외부 패키지 없이 표준 라이브러리만 쓴다.
"""
import argparse
import gzip
import json
import struct
import sys
from pathlib import Path

from template_format import MAX_SIZE, TemplateError, validate

DIRS = ["north", "east", "south", "west"]  # 시계 방향 (위에서 볼 때)
SKIP = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air", "minecraft:structure_void"}


# ---------------------------------------------------------------- NBT 읽기
class _Reader:
    def __init__(self, data):
        self.b = data
        self.i = 0

    def take(self, n):
        if self.i + n > len(self.b):
            raise TemplateError("NBT 데이터가 중간에 끊겼습니다.")
        v = self.b[self.i:self.i + n]
        self.i += n
        return v

    def unpack(self, fmt):
        return struct.unpack(">" + fmt, self.take(struct.calcsize(">" + fmt)))[0]

    def string(self):
        return self.take(self.unpack("H")).decode("utf-8", errors="replace")

    def payload(self, t, depth=0):
        if depth > 128:  # 실제 구조물 NBT 는 10단계 안팎. 파이썬 재귀 한도보다 훨씬 낮게 막는다
            raise TemplateError("NBT 중첩이 너무 깊습니다.")
        if t == 1:
            return self.unpack("b")
        if t == 2:
            return self.unpack("h")
        if t == 3:
            return self.unpack("i")
        if t == 4:
            return self.unpack("q")
        if t == 5:
            return self.unpack("f")
        if t == 6:
            return self.unpack("d")
        if t == 7:
            return self.take(self._len())
        if t == 8:
            return self.string()
        if t == 9:
            et, n = self.unpack("b"), self._len()
            return [self.payload(et, depth + 1) for _ in range(n)]
        if t == 10:
            out = {}
            while True:
                ct = self.unpack("b")
                if ct == 0:
                    return out
                name = self.string()
                out[name] = self.payload(ct, depth + 1)
        if t == 11:
            n = self._len()
            return list(struct.unpack(f">{n}i", self.take(4 * n)))
        if t == 12:
            n = self._len()
            return list(struct.unpack(f">{n}q", self.take(8 * n)))
        raise TemplateError(f"알 수 없는 NBT 태그 종류: {t}")

    def _len(self):
        n = self.unpack("i")
        if n < 0:
            raise TemplateError("NBT 길이 값이 음수입니다.")
        return n


def read_nbt(raw):
    """gzip 압축 여부와 상관없이 루트 컴파운드를 dict 로 돌려준다."""
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    r = _Reader(raw)
    if r.unpack("b") != 10:
        raise TemplateError("NBT 루트가 컴파운드가 아닙니다.")
    r.string()
    return r.payload(10)


# ---------------------------------------------------------------- 형식별 블록 추출
def _ns(name):
    """네임스페이스가 생략된 이름(stone)은 minecraft: 로 본다."""
    return name if ":" in name else "minecraft:" + name


def _state(name, props):
    if not props:
        return name
    return name + "[" + ",".join(f"{k}={props[k]}" for k in sorted(props)) + "]"


def _parse_state(s):
    if "[" not in s:
        return _ns(s), {}
    name, rest = s.split("[", 1)
    name = _ns(name)
    props = {}
    for part in rest.rstrip("]").split(","):
        if part:
            k, _, v = part.partition("=")
            props[k] = v
    return name, props


def from_structure(root, palette_index=0):
    """바닐라 구조물 .nbt → (size, [(x, y, z, name, props)], 블록엔티티 수)."""
    size = root.get("size")
    if not (isinstance(size, list) and len(size) == 3 and all(isinstance(v, int) and v > 0 for v in size)):
        raise TemplateError("구조물 파일에 올바른 size 가 없습니다.")
    if "palette" in root:
        pal = root["palette"]
    elif root.get("palettes"):
        pals = root["palettes"]
        if not 0 <= palette_index < len(pals):
            raise TemplateError(f"palettes 는 {len(pals)}개뿐입니다.")
        pal = pals[palette_index]
    else:
        raise TemplateError("구조물 파일에 palette 가 없습니다.")
    states = [(_ns(p.get("Name", "minecraft:air")), {k: str(v) for k, v in (p.get("Properties") or {}).items()})
              for p in pal]
    out, entities = [], 0
    for b in root.get("blocks", []):
        x, y, z = b["pos"]
        s = b["state"]
        if not 0 <= s < len(states):
            raise TemplateError(f"블록 state 번호가 palette 범위를 벗어났습니다: {s}")
        if not (0 <= x < size[0] and 0 <= y < size[1] and 0 <= z < size[2]):
            raise TemplateError(f"블록 좌표가 구조물 size 를 벗어났습니다: {[x, y, z]}")
        if "nbt" in b:
            entities += 1
        if states[s][0] not in SKIP:
            out.append((x, y, z, *states[s]))
    return list(size), out, entities


def _varints(data, count):
    """varint 를 하나씩 내보낸다 (큰 스키매틱도 전체 목록을 만들지 않도록)."""
    i = 0
    for _ in range(count):
        v = shift = 0
        while True:
            if i >= len(data):
                raise TemplateError("스키매틱 BlockData 가 블록 수보다 짧습니다.")
            byte = data[i] & 0xFF
            i += 1
            v |= (byte & 0x7F) << shift
            if not byte & 0x80:
                break
            shift += 7
            if shift >= 35:  # varint 는 최대 5바이트
                raise TemplateError("스키매틱 BlockData 의 varint 가 잘못됐습니다.")
        yield v
    if i != len(data):
        raise TemplateError("스키매틱 BlockData 가 블록 수보다 깁니다.")


def from_sponge(root):
    """Sponge .schem (v2: 루트에 Palette/BlockData, v3: Schematic.Blocks) → 같은 형식."""
    if "Schematic" in root and isinstance(root["Schematic"], dict):
        root = root["Schematic"]
    dims = [root.get(k) for k in ("Width", "Height", "Length")]
    if not all(isinstance(v, int) for v in dims):
        raise TemplateError("스키매틱에 Width/Height/Length 가 없습니다.")
    w, h, l = (v & 0xFFFF for v in dims)  # unsigned short 로 저장됨 (32768 이상은 음수로 읽힘)
    if not (w and h and l):
        raise TemplateError("스키매틱 크기가 0 입니다.")
    if isinstance(root.get("Blocks"), dict):  # v3
        blk = root["Blocks"]
        palette, data, entities = blk.get("Palette"), blk.get("Data"), len(blk.get("BlockEntities") or [])
    else:  # v2
        palette, data, entities = root.get("Palette"), root.get("BlockData"), len(root.get("BlockEntities") or [])
    if not isinstance(palette, dict) or data is None:
        raise TemplateError("스키매틱에 Palette/BlockData 가 없습니다.")
    by_index = {}
    for s, idx in palette.items():
        by_index[idx] = _parse_state(s)
    out = []
    for n, idx in enumerate(_varints(data, w * h * l)):
        if idx not in by_index:
            raise TemplateError(f"스키매틱 palette 에 없는 번호: {idx}")
        if by_index[idx][0] in SKIP:
            continue
        y, rem = divmod(n, w * l)
        z, x = divmod(rem, w)
        out.append((x, y, z, *by_index[idx]))
    return [w, h, l], out, entities


# ---------------------------------------------------------------- 회전
def _rot_dir(d, steps):
    return DIRS[(DIRS.index(d) + steps) % 4] if d in DIRS else d


def _rot_rail(shape, steps):
    if shape.startswith("ascending_"):
        return "ascending_" + _rot_dir(shape[len("ascending_"):], steps)
    parts = shape.split("_")
    if len(parts) != 2 or not all(p in DIRS for p in parts):
        return shape
    a, b = (_rot_dir(p, steps) for p in parts)
    if {a, b} == {"north", "south"}:
        return "north_south"
    if {a, b} == {"east", "west"}:
        return "east_west"
    ns = a if a in ("north", "south") else b
    return f"{ns}_{b if ns == a else a}"


def rotate_props(name, props, steps):
    """블록 상태를 시계 방향으로 steps*90도 돌린다."""
    if steps % 4 == 0 or not props:
        return props
    p = dict(props)
    if p.get("facing") in DIRS:
        p["facing"] = _rot_dir(p["facing"], steps)
    if "orientation" in p:  # jigsaw, crafter: "north_up", "up_east" 등
        p["orientation"] = "_".join(_rot_dir(t, steps) for t in p["orientation"].split("_"))
    if p.get("axis") in ("x", "z") and steps % 2:
        p["axis"] = "z" if p["axis"] == "x" else "x"
    if "rotation" in p and p["rotation"].isdigit():  # 표지판, 배너, 머리 (0~15)
        p["rotation"] = str((int(p["rotation"]) + 4 * steps) % 16)
    sides = {d: p.pop(d) for d in DIRS if d in p}  # 울타리, 벽, 판유리, 덩굴, 레드스톤 등
    for d, v in sides.items():
        p[_rot_dir(d, steps)] = v
    if "shape" in p and "rail" in name:
        p["shape"] = _rot_rail(p["shape"], steps)
    return p


def rotate_blocks(size, blocks, steps):
    sx, sy, sz = size
    for _ in range(steps % 4):
        # 시계 방향 90도: 북(-z) → 동(+x).  (x, z) → (sz-1-z, x)
        blocks = [(sz - 1 - z, y, x, n, pr) for x, y, z, n, pr in blocks]
        sx, sz = sz, sx
    return [sx, sy, sz], [(x, y, z, n, rotate_props(n, pr, steps)) for x, y, z, n, pr in blocks]


# ---------------------------------------------------------------- 변환
def convert(raw, suffix, facing="north", palette_index=0, crop=True):
    """파일 바이트 → (템플릿 dict, 정보 dict)."""
    root = read_nbt(raw)
    if suffix == ".schem" or "Schematic" in root or "BlockData" in root:
        size, blocks, entities = from_sponge(root)
    else:
        size, blocks, entities = from_structure(root, palette_index)

    blocks = [b for b in blocks if b[3] not in SKIP]
    if not blocks:
        raise TemplateError("공기 외 블록이 하나도 없습니다.")
    if facing not in DIRS:
        raise TemplateError(f"facing 은 {', '.join(DIRS)} 중 하나여야 합니다.")
    steps = (-DIRS.index(facing)) % 4  # 입구 방향 → 북쪽까지 시계 방향 회전 수
    size, blocks = rotate_blocks(size, blocks, steps)

    if crop:
        lo = [min(b[i] for b in blocks) for i in range(3)]
        hi = [max(b[i] for b in blocks) for i in range(3)]
        blocks = [(x - lo[0], y - lo[1], z - lo[2], n, pr) for x, y, z, n, pr in blocks]
        size = [hi[i] - lo[i] + 1 for i in range(3)]

    if max(size) > MAX_SIZE:
        raise TemplateError(f"건물 크기 {size[0]}x{size[1]}x{size[2]} 가 사이트 한도({MAX_SIZE})를 넘습니다. "
                            f"더 작게 만들어야 합니다.")

    palette, index, out = [], {}, []
    for x, y, z, n, pr in sorted(blocks, key=lambda b: (b[1], b[2], b[0])):
        s = _state(n, pr)
        if s not in index:
            index[s] = len(palette)
            palette.append(s)
        out.append([x, y, z, index[s]])

    data = validate({"size": size, "palette": palette, "blocks": out})
    return data, {"rotated": steps * 90, "dropped_block_entities": entities}


def main(argv=None):
    ap = argparse.ArgumentParser(description="구조물 .nbt/.schem 을 사이트 업로드용 템플릿 JSON 으로 변환")
    ap.add_argument("input", type=Path)
    ap.add_argument("-o", "--output", type=Path, help="기본값: 입력 파일 이름.json")
    ap.add_argument("--facing", default="north", choices=DIRS, help="원본 건물 입구가 바라보는 방향 (기본 north)")
    ap.add_argument("--palette-index", type=int, default=0, help="palettes 가 여러 개인 구조물에서 쓸 번호")
    ap.add_argument("--no-crop", action="store_true", help="빈 여백을 잘라내지 않음")
    a = ap.parse_args(argv)

    try:
        data, info = convert(a.input.read_bytes(), a.input.suffix.lower(), a.facing, a.palette_index, not a.no_crop)
    except (TemplateError, OSError, EOFError, KeyError, TypeError, ValueError, RecursionError) as e:
        print(f"변환 실패: {e}", file=sys.stderr)
        return 1
    out = a.output or a.input.with_suffix(".json")
    out.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(f"{out}  크기 {data['size'][0]}x{data['size'][1]}x{data['size'][2]}, "
          f"블록 {len(data['blocks'])}개, 팔레트 {len(data['palette'])}종, 회전 {info['rotated']}도")
    if info["dropped_block_entities"]:
        print(f"참고: 블록 엔티티 데이터 {info['dropped_block_entities']}개(상자 내용물, 표지판 글씨 등)는 "
              f"템플릿 형식에 담을 수 없어 뺐습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
