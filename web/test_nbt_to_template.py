"""변환기 테스트: python -m unittest test_nbt_to_template"""
import gzip
import json
import struct
import tempfile
import unittest
from pathlib import Path

from nbt_to_template import convert, main, rotate_props
from template_format import TemplateError


# ---- 테스트용 최소 NBT 인코더 (값 타입으로 태그 종류를 고른다)
class Int(int):
    pass


class Bytes(bytes):
    pass


class Short(int):
    pass


def _tag(v):
    if isinstance(v, Short):
        return 2
    if isinstance(v, Bytes):
        return 7
    if isinstance(v, str):
        return 8
    if isinstance(v, list):
        return 9
    if isinstance(v, dict):
        return 10
    return 3


def _payload(v):
    t = _tag(v)
    if t == 2:
        return struct.pack(">h", v)
    if t == 3:
        return struct.pack(">i", v)
    if t == 7:
        return struct.pack(">i", len(v)) + bytes(v)
    if t == 8:
        b = v.encode()
        return struct.pack(">H", len(b)) + b
    if t == 9:
        et = _tag(v[0]) if v else 0
        return struct.pack(">bi", et, len(v)) + b"".join(_payload(x) for x in v)
    out = b""
    for k, x in v.items():
        kb = k.encode()
        out += struct.pack(">bH", _tag(x), len(kb)) + kb + _payload(x)
    return out + b"\x00"


def nbt(root):
    return gzip.compress(b"\x0a\x00\x00" + _payload(root))


def structure(size, palette, blocks):
    return nbt({
        "size": list(size),
        "palette": [{"Name": n, **({"Properties": p} if p else {})} for n, p in palette],
        "blocks": [{"pos": [x, y, z], "state": s, **extra} for x, y, z, s, *rest in blocks
                   for extra in [rest[0] if rest else {}]],
    })


def varints(vals):
    out = bytearray()
    for v in vals:
        while True:
            b = v & 0x7F
            v >>= 7
            out.append(b | (0x80 if v else 0))
            if not v:
                break
    return Bytes(out)


def at(data, x, y, z):
    for bx, by, bz, i in data["blocks"]:
        if (bx, by, bz) == (x, y, z):
            return data["palette"][i]
    return None


class ConvertTest(unittest.TestCase):
    def test_structure_basic_drops_air_and_crops(self):
        raw = structure((5, 3, 5),
                        [("minecraft:air", None), ("minecraft:stone", None), ("minecraft:structure_void", None)],
                        [(1, 0, 1, 1), (2, 1, 2, 1), (0, 0, 0, 0), (4, 2, 4, 2)])
        data, info = convert(raw, ".nbt")
        self.assertEqual(data["size"], [2, 2, 2])
        self.assertEqual(data["palette"], ["minecraft:stone"])
        self.assertEqual(sorted(data["blocks"]), [[0, 0, 0, 0], [1, 1, 1, 0]])
        self.assertEqual(info["rotated"], 0)

    def test_no_crop_keeps_size(self):
        raw = structure((5, 3, 5), [("minecraft:stone", None)], [(1, 0, 1, 0)])
        data, _ = convert(raw, ".nbt", crop=False)
        self.assertEqual(data["size"], [5, 3, 5])
        self.assertEqual(data["blocks"], [[1, 0, 1, 0]])

    def test_entrance_south_rotates_180(self):
        # 3(x) x 1 x 2(z). 입구(문)가 남쪽(+z, z=1)에 있고 남쪽을 바라봄
        raw = structure((3, 1, 2), [
            ("minecraft:stone", None),
            ("minecraft:oak_door", {"facing": "south", "half": "lower", "hinge": "left", "open": "false",
                                    "powered": "false"}),
        ], [(0, 0, 0, 0), (2, 0, 0, 0), (1, 0, 1, 1)])
        data, info = convert(raw, ".nbt", facing="south")
        self.assertEqual(info["rotated"], 180)
        self.assertEqual(data["size"], [3, 1, 2])
        door = at(data, 1, 0, 0)  # 입구가 z=0 으로 옴
        self.assertIn("facing=north", door)
        self.assertIn("hinge=left", door)
        self.assertEqual(at(data, 0, 0, 1), "minecraft:stone")

    def test_entrance_east_rotates_270_and_swaps_size(self):
        # 2(x) x 1 x 3(z). 동쪽(x=1) 에 계단, 동쪽을 바라봄
        raw = structure((2, 1, 3), [
            ("minecraft:stone", None),
            ("minecraft:oak_stairs", {"facing": "east", "half": "bottom", "shape": "straight",
                                      "waterlogged": "false"}),
            ("minecraft:oak_log", {"axis": "x"}),
        ], [(0, 0, 0, 0), (1, 0, 1, 1), (0, 0, 2, 2)])
        data, info = convert(raw, ".nbt", facing="east")
        self.assertEqual(info["rotated"], 270)
        self.assertEqual(data["size"], [3, 1, 2])
        stairs = at(data, 1, 0, 0)
        self.assertIn("facing=north", stairs)
        self.assertIn("shape=straight", stairs)
        self.assertEqual(at(data, 2, 0, 1), "minecraft:oak_log[axis=z]")

    def test_rotate_props_misc(self):
        p = rotate_props("minecraft:oak_fence", {"north": "true", "east": "false", "south": "false",
                                                 "west": "false", "waterlogged": "false"}, 1)
        self.assertEqual(p["east"], "true")
        self.assertEqual(p["north"], "false")
        self.assertEqual(rotate_props("minecraft:oak_sign", {"rotation": "14"}, 1)["rotation"], "2")
        self.assertEqual(rotate_props("minecraft:rail", {"shape": "north_south"}, 1)["shape"], "east_west")
        self.assertEqual(rotate_props("minecraft:rail", {"shape": "north_east"}, 1)["shape"], "south_east")
        self.assertEqual(rotate_props("minecraft:rail", {"shape": "ascending_west"}, 2)["shape"], "ascending_east")
        self.assertEqual(rotate_props("minecraft:lever", {"facing": "up"}, 1)["facing"], "up")
        self.assertEqual(rotate_props("minecraft:oak_stairs", {"shape": "inner_left", "facing": "north"}, 1),
                         {"shape": "inner_left", "facing": "east"})

    def test_block_entities_counted(self):
        raw = structure((1, 1, 1), [("minecraft:chest", {"facing": "north"})],
                        [(0, 0, 0, 0, {"nbt": {"id": "minecraft:chest"}})])
        data, info = convert(raw, ".nbt")
        self.assertEqual(info["dropped_block_entities"], 1)
        self.assertEqual(data["palette"], ["minecraft:chest[facing=north]"])

    def test_sponge_v2(self):
        # 2x1x2, 인덱스 = x + z*W + y*W*L
        pal = {"minecraft:air": Int(0), "minecraft:stone": Int(1), "minecraft:oak_log[axis=y]": Int(2)}
        raw = nbt({"Version": 2, "Width": 2, "Height": 1, "Length": 2, "Palette": pal,
                   "BlockData": varints([1, 0, 0, 2])})
        data, _ = convert(raw, ".schem", crop=False)
        self.assertEqual(at(data, 0, 0, 0), "minecraft:stone")
        self.assertEqual(at(data, 1, 0, 1), "minecraft:oak_log[axis=y]")
        self.assertIsNone(at(data, 1, 0, 0))

    def test_sponge_v3_with_large_palette_index(self):
        pal = {f"minecraft:block_{i}": Int(i) for i in range(200)}
        raw = nbt({"Schematic": {"Version": 3, "Width": 1, "Height": 2, "Length": 1,
                                 "Blocks": {"Palette": pal, "Data": varints([150, 199])}}})
        data, _ = convert(raw, ".schem")
        self.assertEqual(at(data, 0, 0, 0), "minecraft:block_150")
        self.assertEqual(at(data, 0, 1, 0), "minecraft:block_199")

    def test_sponge_unsigned_width_and_implicit_namespace(self):
        # Width 40000 은 Short 로 -25536 이 된다. 나머지는 공기라 1x1x1 로 잘려야 함
        w = 40000
        raw = nbt({"Version": 2, "Width": Short(w - 65536), "Height": Short(1), "Length": Short(1),
                   "Palette": {"air": 0, "oak_stairs[facing=east]": 1},
                   "BlockData": varints([1] + [0] * (w - 1))})
        data, _ = convert(raw, ".schem")
        self.assertEqual(data["size"], [1, 1, 1])
        self.assertEqual(data["palette"], ["minecraft:oak_stairs[facing=east]"])

    def test_sponge_bad_varints(self):
        base = {"Version": 2, "Width": Short(1), "Height": Short(1), "Length": Short(1),
                "Palette": {"minecraft:stone": 0}}
        for bad in (b"\x80\x80\x80\x80\x80\x00", b"\x00\x00", b""):
            with self.assertRaises(TemplateError, msg=bad):
                convert(nbt({**base, "BlockData": Bytes(bad)}), ".schem")

    def test_structure_block_outside_size(self):
        with self.assertRaises(TemplateError):
            convert(structure((1, 1, 1), [("minecraft:stone", None)], [(99, 0, 99, 0)]), ".nbt")

    def test_deep_nesting_is_rejected(self):
        deep = []
        for _ in range(300):
            deep = [deep]
        raw = structure((1, 1, 1), [("minecraft:chest", None)], [(0, 0, 0, 0, {"nbt": {"x": deep}})])
        with self.assertRaises(TemplateError):
            convert(raw, ".nbt")

    def test_errors(self):
        with self.assertRaises(TemplateError):
            convert(structure((1, 1, 1), [("minecraft:air", None)], [(0, 0, 0, 0)]), ".nbt")
        with self.assertRaises(TemplateError):  # 사이트는 minecraft: 네임스페이스만 허용
            convert(structure((1, 1, 1), [("create:shaft", None)], [(0, 0, 0, 0)]), ".nbt")
        with self.assertRaises(TemplateError):
            convert(structure((200, 1, 1), [("minecraft:stone", None)], [(0, 0, 0, 0), (199, 0, 0, 0)]), ".nbt")
        with self.assertRaises(TemplateError):
            convert(gzip.compress(b"\x0a\x00\x00\x03"), ".nbt")

    def test_cli_writes_json(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "hut.nbt"
            src.write_bytes(structure((1, 1, 1), [("minecraft:stone", None)], [(0, 0, 0, 0)]))
            self.assertEqual(main([str(src)]), 0)
            out = json.loads((Path(d) / "hut.json").read_text(encoding="utf-8"))
            self.assertEqual(out, {"size": [1, 1, 1], "palette": ["minecraft:stone"], "blocks": [[0, 0, 0, 0]]})
            bad = Path(d) / "bad.nbt"
            bad.write_bytes(b"not nbt")
            self.assertEqual(main([str(bad)]), 1)


if __name__ == "__main__":
    unittest.main()
