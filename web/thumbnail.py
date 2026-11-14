"""실제 마인크래프트 26.3 블록 텍스처·모델로 템플릿 썸네일(아이소메트릭 PNG)을 그린다.

에셋은 tools/fetch_assets.py 로 Mojang 공식 client.jar 에서 꺼낸 web/instance/assets 를 쓴다.
blockstates → models(부모 상속) → elements(직육면체) 를 따라가며 각 면을 텍스처로 그려서
계단·문·유리판·랜턴 같은 블록도 실제 모양대로 나온다.
"""
import hashlib
import json
import math
import threading
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

BASE = Path(__file__).parent
ASSETS = BASE / "instance" / "assets"
CACHE = BASE / "instance" / "thumbs"
RENDER_VERSION = "3"  # 렌더러가 바뀌면 올려서 캐시 무효화

COS30 = math.cos(math.radians(30))
# 면 방향별 밝기 (마인크래프트 기본 음영)
SHADE = {"up": 1.0, "down": 0.5, "north": 0.8, "south": 0.8, "east": 0.6, "west": 0.6}
DIRS = {"up": (0, 1, 0), "down": (0, -1, 0), "north": (0, 0, -1), "south": (0, 0, 1),
        "west": (-1, 0, 0), "east": (1, 0, 0)}
TRANSLUCENT = ("glass", "leaves", "ice", "slime", "honey_block", "spawner", "barrier",
               "water", "lava", "scaffolding", "cobweb")
_locks = {}
_locks_guard = threading.Lock()


def available():
    return (ASSETS / "blockstates").is_dir()


# ---------------------------------------------------------------- 에셋 로딩

def _read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def _strip_ns(name):
    return name.split(":", 1)[-1]


@lru_cache(maxsize=None)
def blockstate(block_id):
    return _read_json(ASSETS / "blockstates" / f"{_strip_ns(block_id)}.json")


@lru_cache(maxsize=None)
def model(name):
    """부모를 따라 올라가며 textures 를 합치고 가장 가까운 elements 를 쓴다."""
    path = _strip_ns(name)
    data = _read_json(ASSETS / "models" / f"{path}.json")
    if data is None:
        return {"textures": {}, "elements": None}
    parent = model(data["parent"]) if "parent" in data else {"textures": {}, "elements": None}
    textures = dict(parent["textures"])
    textures.update(data.get("textures", {}))
    elements = data.get("elements", parent["elements"])
    return {"textures": textures, "elements": elements}


@lru_cache(maxsize=None)
def texture(name):
    """텍스처 PNG (애니메이션 세로 스트립이면 첫 프레임만)."""
    path = ASSETS / "textures" / f"{_strip_ns(name)}.png"
    if not path.exists():
        return None
    img = Image.open(path).convert("RGBA")
    w, h = img.size
    if h > w:
        img = img.crop((0, 0, w, w))
    return img


def resolve_texture(textures, ref, depth=0):
    # 26.x 모델은 텍스처를 {"sprite": "...", "force_translucent": true} 객체로 쓰기도 한다
    if isinstance(ref, dict):
        ref = ref.get("sprite")
    while isinstance(ref, str) and ref.startswith("#") and depth < 10:
        ref = textures.get(ref[1:])
        if isinstance(ref, dict):
            ref = ref.get("sprite")
        depth += 1
    return ref if isinstance(ref, str) else None


def parse_state(state):
    bid, _, rest = state.partition("[")
    props = dict(kv.split("=", 1) for kv in rest.rstrip("]").split(",")) if rest else {}
    return bid, props


def _when_matches(when, props):
    if "OR" in when:
        return any(_when_matches(w, props) for w in when["OR"])
    if "AND" in when:
        return all(_when_matches(w, props) for w in when["AND"])
    return all(props.get(k) in str(v).split("|") for k, v in when.items())


def models_for(state):
    """블록 상태 → [(모델, x회전, y회전)]"""
    bid, props = parse_state(state)
    bs = blockstate(bid)
    if bs is None:
        return []
    out = []
    if "variants" in bs:
        for key, variant in bs["variants"].items():
            conds = dict(kv.split("=", 1) for kv in key.split(",")) if key else {}
            if all(props.get(k) == v for k, v in conds.items()):
                v = variant[0] if isinstance(variant, list) else variant
                out.append((v["model"], v.get("x", 0), v.get("y", 0)))
                break
    for part in bs.get("multipart", []):
        if "when" not in part or _when_matches(part["when"], props):
            v = part["apply"][0] if isinstance(part["apply"], list) else part["apply"]
            out.append((v["model"], v.get("x", 0), v.get("y", 0)))
    return out


def _tint(block_id):
    bid = _strip_ns(block_id)
    if "water" in bid:
        return (63, 118, 228)
    if bid == "spruce_leaves":
        return (97, 153, 97)
    if bid == "birch_leaves":
        return (128, 167, 85)
    if bid in ("grass_block", "short_grass", "tall_grass", "fern", "large_fern", "sugar_cane"):
        return (145, 189, 89)
    return (119, 171, 47)


# ---------------------------------------------------------------- 기하 계산

def _rot_x(p, deg):
    x, y, z = p
    for _ in range((deg // 90) % 4):  # 위 → 북
        y, z = z, -y
    return x, y, z


def _rot_y(p, deg):
    x, y, z = p
    for _ in range((deg // 90) % 4):  # 북 → 동 (위에서 볼 때 시계방향)
        x, z = -z, x
    return x, y, z


def _rot_elem(p, rot):
    if not rot:
        return p
    ox, oy, oz = rot.get("origin", [8, 8, 8])
    a = math.radians(rot.get("angle", 0))
    c, s = math.cos(a), math.sin(a)
    x, y, z = p[0] - ox, p[1] - oy, p[2] - oz
    axis = rot.get("axis", "y")
    if axis == "x":
        y, z = y * c - z * s, y * s + z * c
    elif axis == "y":
        x, z = x * c + z * s, -x * s + z * c
    else:
        x, y = x * c - y * s, x * s + y * c
    return x + ox, y + oy, z + oz


def _face_corners(f, t, face):
    """면을 바깥에서 볼 때 텍스처 기준 [좌상, 우상, 우하, 좌하]."""
    fx, fy, fz = f
    tx, ty, tz = t
    return {
        "north": [(tx, ty, fz), (fx, ty, fz), (fx, fy, fz), (tx, fy, fz)],
        "south": [(fx, ty, tz), (tx, ty, tz), (tx, fy, tz), (fx, fy, tz)],
        "west": [(fx, ty, fz), (fx, ty, tz), (fx, fy, tz), (fx, fy, fz)],
        "east": [(tx, ty, tz), (tx, ty, fz), (tx, fy, fz), (tx, fy, tz)],
        "up": [(fx, ty, fz), (tx, ty, fz), (tx, ty, tz), (fx, ty, tz)],
        "down": [(fx, fy, tz), (tx, fy, tz), (tx, fy, fz), (fx, fy, fz)],
    }[face]


def _default_uv(f, t, face):
    fx, fy, fz = f
    tx, ty, tz = t
    return {
        "north": [16 - tx, 16 - ty, 16 - fx, 16 - fy],
        "south": [fx, 16 - ty, tx, 16 - fy],
        "west": [fz, 16 - ty, tz, 16 - fy],
        "east": [16 - tz, 16 - ty, 16 - fz, 16 - fy],
        "up": [fx, fz, tx, tz],
        "down": [fx, 16 - tz, tx, 16 - fz],
    }[face]


FULL_CUBE = [{"from": [0, 0, 0], "to": [16, 16, 16],
              "faces": {d: {"texture": "#all"} for d in DIRS}}]


def _fallback(bid, textures):
    """엔티티로 그려지는 블록(상자, 침대, 물 등)은 비슷한 모양의 상자로 대신한다."""
    name = _strip_ns(bid)
    if name in ("water", "lava"):
        tex = f"block/{name}_still"
        return [{"from": [0, 0, 0], "to": [16, 14, 16],
                 "faces": {d: {"texture": tex, "tintindex": 0 if name == "water" else None} for d in DIRS}}]
    if name.endswith("_bed"):
        color = name[: -len("_bed")]
        return [{"from": [0, 3, 0], "to": [16, 9, 16],
                 "faces": {d: {"texture": f"block/{color}_wool" if d == "up" else "block/oak_planks"}
                           for d in DIRS}}]
    if "chest" in name:
        tex = "block/oak_planks"
        return [{"from": [1, 0, 1], "to": [15, 14, 15], "faces": {d: {"texture": tex} for d in DIRS}}]
    tex = resolve_texture(textures, textures.get("particle"))
    if not tex:
        return []
    return [{"from": [1, 0, 1], "to": [15, 15, 15], "faces": {d: {"texture": tex} for d in DIRS}}]


def block_quads(state):
    """블록 상태 하나를 모델 좌표(0~16) 면 목록으로: (꼭짓점4, uv4, 텍스처, 방향, 틴트)"""
    bid, _ = parse_state(state)
    quads = []
    for model_name, mx, my in models_for(state):
        m = model(model_name)
        elements = m["elements"]
        textures = m["textures"]
        if not elements:
            elements = _fallback(bid, textures)
        for el in elements:
            f, t = el["from"], el["to"]
            for face, spec in el.get("faces", {}).items():
                tex = resolve_texture(textures, spec["texture"])
                if not tex:
                    continue
                uv = spec.get("uv") or _default_uv(f, t, face)
                u1, v1, u2, v2 = uv
                uvs = [(u1, v1), (u2, v1), (u2, v2), (u1, v2)]
                k = (spec.get("rotation", 0) // 90) % 4
                uvs = [uvs[(i - k) % 4] for i in range(4)]
                pts = []
                for p in _face_corners(f, t, face):
                    p = _rot_elem(p, el.get("rotation"))
                    p = (p[0] - 8, p[1] - 8, p[2] - 8)
                    p = _rot_y(_rot_x(p, mx), my)
                    pts.append((p[0] + 8, p[1] + 8, p[2] + 8))
                normal = _rot_y(_rot_x(DIRS[face], mx), my)
                tint = _tint(bid) if spec.get("tintindex") is not None else None
                quads.append((pts, uvs, tex, normal, tint))
    return quads


@lru_cache(maxsize=None)
def cached_quads(state):
    return block_quads(state)


def is_opaque_cube(state):
    bid, _ = parse_state(state)
    if any(k in bid for k in TRANSLUCENT):
        return False
    for model_name, _, _ in models_for(state):
        els = model(model_name)["elements"]
        if not els or len(els) != 1:
            return False
        if els[0]["from"] != [0, 0, 0] or els[0]["to"] != [16, 16, 16]:
            return False
        return True
    return False


# ---------------------------------------------------------------- 그리기

def _affine_from(src, dst):
    """dst(화면) 3점 → src(텍스처) 3점 으로 가는 아핀 변환 계수 (Pillow AFFINE 용)."""
    (x0, y0), (x1, y1), (x2, y2) = dst
    det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    if abs(det) < 1e-9:
        return None
    out = []
    for i in range(2):
        s0, s1, s2 = src[0][i], src[1][i], src[2][i]
        a = ((s1 - s0) * (y2 - y0) - (s2 - s0) * (y1 - y0)) / det
        b = ((s2 - s0) * (x1 - x0) - (s1 - s0) * (x2 - x0)) / det
        c = s0 - a * x0 - b * y0
        out += [a, b, c]
    return out


@lru_cache(maxsize=None)
def _shaded(tex_name, shade, tint):
    img = texture(tex_name)
    if img is None:
        return None
    r, g, b, a = img.split()
    tr, tg, tb = tint if tint else (255, 255, 255)
    r = r.point(lambda v: int(v * shade * tr / 255))
    g = g.point(lambda v: int(v * shade * tg / 255))
    b = b.point(lambda v: int(v * shade * tb / 255))
    return Image.merge("RGBA", (r, g, b, a))


def render(data, rotation=0, max_y=None, size=(640, 480), supersample=2):
    sx_, sy_, sz_ = data["size"]
    palette = data["palette"]
    cells = {}
    for x, y, z, i in data["blocks"]:
        if max_y is None or y <= max_y:
            cells[(x, y, z)] = palette[i]
    opaque = {p for p, s in cells.items() if is_opaque_cube(s)}

    # 보기 회전: rotation 0 = 정면(z=0)과 서쪽 면이 보이도록 180도 돌린 상태
    def view(p):
        x, y, z = p
        x, z = x - sx_ / 2, z - sz_ / 2
        for _ in range((rotation + 2) % 4):
            x, z = -z, x
        return x, y, z

    faces = []
    for (bx, by, bz), st in cells.items():
        for pts, uvs, tex, normal, tint in cached_quads(st):
            # 이웃이 불투명한 꽉 찬 블록이면 맞닿은 면은 안 보이므로 생략
            if normal in DIRS.values():
                n = (bx + normal[0], by + normal[1], bz + normal[2])
                on_edge = all(
                    (normal[a] == 0) or (pts[0][a] == (16 if normal[a] > 0 else 0)) for a in range(3)
                ) and all(p[a] == pts[0][a] for p in pts for a in range(3) if normal[a] != 0)
                if on_edge and n in opaque:
                    continue
            world = [view((bx + p[0] / 16, by + p[1] / 16, bz + p[2] / 16)) for p in pts]
            vn = view((normal[0], normal[1], normal[2]))
            vo = view((0, 0, 0))
            vn = (vn[0] - vo[0], vn[1] - vo[1], vn[2] - vo[2])
            if vn[0] + vn[1] + vn[2] <= 1e-6:  # 카메라 반대쪽 면
                continue
            cx = sum(p[0] for p in world) / 4
            cy = sum(p[1] for p in world) / 4
            cz = sum(p[2] for p in world) / 4
            face_dir = max(DIRS, key=lambda d: sum(DIRS[d][a] * vn[a] for a in range(3)))
            faces.append((cx + cy + cz, world, uvs, tex, SHADE[face_dir], tint))
    if not faces:
        return Image.new("RGBA", size, (0, 0, 0, 0))

    def proj(p):
        x, y, z = p
        return (x - z) * COS30, (x + z) * 0.5 - y

    xs, ys = [], []
    for _, world, *_ in faces:
        for p in world:
            px, py = proj(p)
            xs.append(px)
            ys.append(py)
    W, H = size[0] * supersample, size[1] * supersample
    pad = 0.06
    scale = min(W * (1 - 2 * pad) / (max(xs) - min(xs)), H * (1 - 2 * pad) / (max(ys) - min(ys)))
    ox = W / 2 - (max(xs) + min(xs)) / 2 * scale
    oy = H / 2 - (max(ys) + min(ys)) / 2 * scale

    def screen(p):
        px, py = proj(p)
        return ox + px * scale, oy + py * scale

    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # 바닥 그림자
    shadow = Image.new("L", (W, H), 0)
    foot = [screen(view(p)) for p in [(0, 0, 0), (sx_, 0, 0), (sx_, 0, sz_), (0, 0, sz_)]]
    ImageDraw.Draw(shadow).polygon(foot, fill=90)
    shadow = shadow.filter(ImageFilter.GaussianBlur(scale * 0.6))
    canvas.paste(Image.new("RGBA", (W, H), (20, 16, 10, 255)), (0, 0), shadow)

    faces.sort(key=lambda f: f[0])
    for _, world, uvs, tex, shade, tint in faces:
        img = _shaded(tex, shade, tint)
        if img is None:
            continue
        tw = img.size[0] / 16
        scr = [screen(p) for p in world]
        x0 = int(math.floor(min(p[0] for p in scr))) - 1
        y0 = int(math.floor(min(p[1] for p in scr))) - 1
        x1 = int(math.ceil(max(p[0] for p in scr))) + 1
        y1 = int(math.ceil(max(p[1] for p in scr))) + 1
        bw, bh = x1 - x0, y1 - y0
        if bw <= 0 or bh <= 0 or x0 < 0 or y0 < 0 or x1 > W or y1 > H:
            continue
        local = [(p[0] - x0, p[1] - y0) for p in scr]
        src = [(u * tw, v * tw) for u, v in (uvs[0], uvs[1], uvs[3])]
        coef = _affine_from(src, (local[0], local[1], local[3]))
        if coef is None:
            continue
        tile = img.transform((bw, bh), Image.AFFINE, coef, resample=Image.NEAREST)
        mask = Image.new("L", (bw, bh), 0)
        ImageDraw.Draw(mask).polygon(local, fill=255, outline=255)
        alpha = tile.getchannel("A")
        tile.putalpha(ImageChops.multiply(alpha, mask))
        canvas.alpha_composite(tile, (x0, y0))
    return canvas.resize(size, Image.LANCZOS)


def icon_texture(state):
    """재료 목록에 쓸 블록 대표 텍스처 (텍스처 파일 경로)."""
    bid, _ = parse_state(state)
    special = {"minecraft:water": "block/water_still", "minecraft:lava": "block/lava_still"}
    if bid in special:
        return ASSETS / "textures" / f"{special[bid]}.png"
    if bid.endswith("_bed"):
        return ASSETS / "textures" / "block" / f"{_strip_ns(bid)[:-4]}_wool.png"
    for model_name, _, _ in models_for(state):
        tex = model(model_name)["textures"]
        for key in ("all", "side", "texture", "front", "pane", "cross", "top", "particle"):
            ref = resolve_texture(tex, tex.get(key))
            if ref and (ASSETS / "textures" / f"{_strip_ns(ref)}.png").exists():
                return ASSETS / "textures" / f"{_strip_ns(ref)}.png"
    return None


# ---------------------------------------------------------------- 캐시

def thumbnail_path(template_id, data_json, rotation=0, max_y=None):
    """썸네일 PNG 경로 (없으면 그려서 저장). 같은 템플릿을 동시에 그리지 않도록 잠금."""
    key = hashlib.sha1(f"{RENDER_VERSION}|{data_json}|{rotation}|{max_y}".encode()).hexdigest()[:16]
    path = CACHE / f"{template_id}-{key}.png"
    if path.exists():
        return path
    with _locks_guard:
        lock = _locks.setdefault(key, threading.Lock())
    with lock:
        if not path.exists():
            CACHE.mkdir(parents=True, exist_ok=True)
            img = render(json.loads(data_json), rotation, max_y)
            tmp = path.with_suffix(".tmp")
            img.save(tmp, "PNG", optimize=True)
            tmp.replace(path)
    return path
