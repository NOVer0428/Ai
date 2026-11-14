"""건물 템플릿 데이터 형식.

{
  "size":    [x, y, z],                     # 바운딩 박스 크기
  "palette": ["minecraft:oak_planks", ...],  # 블록 데이터 문자열 (Bukkit.createBlockData 형식)
  "blocks":  [[x, y, z, paletteIndex], ...]  # 0 <= x < size[0] ... (공기 블록은 생략)
}

방향 규칙: 템플릿의 정면(입구)은 z = 0 쪽이며 북쪽(-z)을 바라본다.
플러그인은 플레이어가 바라보는 방향에 맞춰 회전해서 짓는다.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

MAX_SIZE = 128
MAX_BLOCKS = 200_000
MAX_PALETTE = 1024
BLOCK_RE = re.compile(r"^minecraft:[a-z0-9_]+(\[[a-z0-9_]+=[a-z0-9_]+(,[a-z0-9_]+=[a-z0-9_]+)*\])?$")


BLOCKS_FILE = Path(__file__).resolve().parent.parent / "data" / "blocks-26.3.json"


class TemplateError(ValueError):
    pass


@lru_cache(maxsize=1)
def block_registry():
    """Paper 26.3 블록 목록 (바닐라 server.jar --reports 로 생성). 없으면 None → 형식만 검사."""
    try:
        return json.loads(BLOCKS_FILE.read_text(encoding="utf-8"))["blocks"]
    except FileNotFoundError:
        return None


def check_block(text):
    """'minecraft:oak_stairs[facing=north]' 가 26.3 에 실제로 있는 블록/속성/값인지 확인."""
    reg = block_registry()
    if reg is None:
        return
    bid, _, rest = text.partition("[")
    info = reg.get(bid)
    if info is None:
        raise TemplateError(f"26.3 에 없는 블록입니다: {bid}")
    if rest:
        for pair in rest.rstrip("]").split(","):
            key, _, value = pair.partition("=")
            allowed = info["properties"].get(key)
            if allowed is None:
                raise TemplateError(f"{bid} 에는 '{key}' 속성이 없습니다.")
            if value not in allowed:
                raise TemplateError(f"{bid} 의 {key} 값은 {', '.join(allowed)} 중 하나여야 합니다: {value}")


def _is_int(v):
    # bool 은 int 의 하위 타입이라 따로 걸러낸다 (true/false 가 좌표로 들어오는 것 방지)
    return isinstance(v, int) and not isinstance(v, bool)


def validate(data):
    if not isinstance(data, dict):
        raise TemplateError("템플릿은 JSON 객체여야 합니다.")
    size = data.get("size")
    palette = data.get("palette")
    blocks = data.get("blocks")

    if (not isinstance(size, list) or len(size) != 3
            or not all(_is_int(v) and 1 <= v <= MAX_SIZE for v in size)):
        raise TemplateError(f"size는 1~{MAX_SIZE} 사이 정수 3개여야 합니다.")
    if not isinstance(palette, list) or not 1 <= len(palette) <= MAX_PALETTE:
        raise TemplateError("palette가 비어있거나 너무 큽니다.")
    for p in palette:
        if not isinstance(p, str) or not BLOCK_RE.match(p):
            raise TemplateError(f"잘못된 블록 이름: {p!r}")
        check_block(p)
    if not isinstance(blocks, list) or not 1 <= len(blocks) <= MAX_BLOCKS:
        raise TemplateError(f"blocks는 1~{MAX_BLOCKS}개여야 합니다.")

    seen = set()
    clean = []
    for b in blocks:
        if not (isinstance(b, list) and len(b) == 4 and all(_is_int(v) for v in b)):
            raise TemplateError("각 블록은 [x, y, z, paletteIndex] 형식이어야 합니다.")
        x, y, z, i = b
        if not (0 <= x < size[0] and 0 <= y < size[1] and 0 <= z < size[2]):
            raise TemplateError(f"블록 좌표가 size 범위를 벗어났습니다: {b}")
        if not 0 <= i < len(palette):
            raise TemplateError(f"palette 인덱스가 범위를 벗어났습니다: {b}")
        if palette[i] in ("minecraft:air", "minecraft:cave_air", "minecraft:void_air"):
            continue
        if (x, y, z) in seen:
            raise TemplateError(f"중복 좌표: {b}")
        seen.add((x, y, z))
        clean.append([x, y, z, i])
    if not clean:
        raise TemplateError("공기 외 블록이 하나도 없습니다.")
    return {"size": size, "palette": palette, "blocks": clean}
