"""템플릿 블록 목록 → 실제 아이템 재료 목록 (한국어 이름 + 아이콘).

블록 상태(oak_stairs[facing=...])가 아니라 플레이어가 인벤토리에 들고 있어야 하는 아이템 기준으로 센다.
  - 문·키 큰 꽃 등 두 칸짜리는 아래 칸만, 침대는 발쪽만 센다
  - 화분 꽃(potted_x) → 화분 + 꽃, 용암/물 가마솥 → 가마솥 + 양동이
  - 벽 횃불·벽 표지판 등은 원래 아이템으로, 겹반블록은 반블록 2개로
"""
import json
from collections import Counter
from functools import lru_cache
from pathlib import Path

import thumbnail
from template_format import TemplateError, normalize

ASSETS = thumbnail.ASSETS
ICONS = Path(__file__).parent / "instance" / "icons"
ICON_VERSION = "3"

POTTED_SPECIAL = {"azalea_bush": "azalea", "flowering_azalea_bush": "flowering_azalea"}
WALL_VARIANTS = (("_wall_hanging_sign", "_hanging_sign"), ("_wall_sign", "_sign"),
                 ("_wall_banner", "_banner"), ("_wall_torch", "_torch"),
                 ("_wall_head", "_head"), ("_wall_skull", "_skull"), ("_wall_fan", "_fan"))
NO_ITEM = {"air", "cave_air", "void_air", "fire", "soul_fire", "moving_piston", "piston_head",
           "nether_portal", "end_portal", "end_gateway", "bubble_column", "frosted_ice"}
BUCKETS = {"water": "water_bucket", "lava": "lava_bucket", "powder_snow": "powder_snow_bucket"}


def _items_for(state):
    """블록 상태 하나 → [(아이템 id, 개수)]"""
    bid, _, rest = state.partition("[")
    name = bid.split(":", 1)[1]
    props = dict(kv.split("=", 1) for kv in rest.rstrip("]").split(",")) if rest else {}
    if name in NO_ITEM:
        return []
    if name in BUCKETS:
        return [(BUCKETS[name], 1)]
    if props.get("half") == "upper":
        return []  # 문·키 큰 꽃 윗칸 (26.3 에서 upper 는 두 칸짜리 블록만 씀. 계단·트랩도어는 top)
    if props.get("part") == "head":
        return []  # 침대 머리 쪽
    if name.startswith("potted_"):
        plant = name[len("potted_"):]
        return [("flower_pot", 1), (POTTED_SPECIAL.get(plant, plant), 1)]
    if name.endswith("_cauldron"):
        liquid = name[: -len("_cauldron")]
        return [("cauldron", 1)] + ([(BUCKETS[liquid], 1)] if liquid in BUCKETS else [])
    if name.endswith("_slab") and props.get("type") == "double":
        return [(name, 2)]
    if name == "wall_torch":
        return [("torch", 1)]
    for wall, item in WALL_VARIANTS:
        if name.endswith(wall):
            return [(name[: -len(wall)] + item, 1)]
    for key in ("candles", "pickles", "eggs", "layers", "flower_amount", "segment_amount"):
        if key in props and props[key].isdigit():
            return [(name, int(props[key]))]
    return [(name, 1)]


@lru_cache(maxsize=None)
def _lang(code):
    try:
        return json.loads((ASSETS / "lang" / f"{code}.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def item_name(item):
    for code in ("ko_kr", "en_us"):
        lang = _lang(code)
        for key in (f"item.minecraft.{item}", f"block.minecraft.{item}"):
            if key in lang:
                return lang[key]
    return item.replace("_", " ")


def materials(data):
    """템플릿 데이터 → [{item, name, count, icon}] (많은 순)"""
    counts = Counter()
    per_index = Counter(b[3] for b in data["blocks"])
    for idx, n in per_index.items():
        for item, k in _items_for(data["palette"][idx]):
            counts[item] += n * k
    icon_ok = thumbnail.available()
    return [{"item": f"minecraft:{item}", "name": item_name(item), "count": n,
             "icon": f"/api/items/{item}/icon.png" if icon_ok else None}
            for item, n in counts.most_common()]


# ---------------------------------------------------------------- 아이콘

def _is_flat(state):
    """세로로 얇은 모델(유리판, 사다리, 덩굴, 꽃처럼 x 나 z 방향 두께가 2 이하)만 평면 그림으로.
    카펫·압력판처럼 바닥에 눕는 얇은 블록이나 퇴비통 같은 속 빈 블록은 입체로 둔다."""
    lo, hi = [16, 16, 16], [0, 0, 0]
    found = False
    for model_name, _, _ in thumbnail.models_for(state):
        for el in thumbnail.model(model_name)["elements"] or []:
            found = True
            for a in range(3):
                lo[a] = min(lo[a], el["from"][a], el["to"][a])
                hi[a] = max(hi[a], el["from"][a], el["to"][a])
    if not found:
        return False
    dims = [hi[a] - lo[a] for a in range(3)]
    return dims[0] <= 2 or dims[2] <= 2 or _is_cross(state)


def _is_cross(state):
    for model_name, _, _ in thumbnail.models_for(state):
        if any(el.get("rotation", {}).get("angle") for el in thumbnail.model(model_name)["elements"] or []):
            return True
    return False


def _tinted(state):
    return any(spec.get("tintindex") is not None
               for model_name, _, _ in thumbnail.models_for(state)
               for el in thumbnail.model(model_name)["elements"] or []
               for spec in el.get("faces", {}).values())


def icon_path(item):
    """아이템 아이콘 PNG 경로 (없으면 만들어서 캐시). 없는 아이템이면 None."""
    if not item.replace("_", "").isalnum():
        return None
    path = ICONS / f"{item}-{ICON_VERSION}.png"
    if path.exists():
        return path
    ICONS.mkdir(parents=True, exist_ok=True)
    flat = ASSETS / "textures" / "item" / f"{item}.png"
    if flat.exists():
        img = thumbnail.texture(f"item/{item}")
    else:
        try:
            state = normalize(f"minecraft:{item}")
        except TemplateError:
            return None
        if _is_flat(state):
            tex = thumbnail.icon_texture(state)
            if tex is None:
                return None
            img = thumbnail.texture(tex.relative_to(ASSETS / "textures").with_suffix("").as_posix())
            if img is not None and _tinted(state):
                img = thumbnail._shaded(tex.relative_to(ASSETS / "textures").with_suffix("").as_posix(),
                                        1.0, thumbnail._tint(state.split("[")[0]))
        else:
            # 블록 아이템은 게임 인벤토리처럼 입체로
            img = thumbnail.render({"size": [1, 1, 1], "palette": [state], "blocks": [[0, 0, 0, 0]]},
                                   size=(64, 64), shadow=False)
    if img is None:
        return None
    img.save(path, "PNG")
    return path
