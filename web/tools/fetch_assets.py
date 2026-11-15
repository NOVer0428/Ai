"""Mojang 공식 26.3 client.jar 에서 썸네일 렌더링에 필요한 블록 에셋만 꺼낸다.

    python tools/fetch_assets.py            # web/instance/assets 에 저장

꺼내는 것: assets/minecraft/{blockstates, models/block, textures/block, textures/item,
          textures/colormap, lang/en_us.json} + 공식 에셋 서버의 lang/ko_kr.json (아이템 한국어 이름)
Mojang 에셋이므로 저장소에는 커밋하지 않는다 (web/instance/ 는 .gitignore).
"""
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

VERSION = "26.3"
MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
OUT = Path(__file__).resolve().parent.parent / "instance" / "assets"
KEEP = ("assets/minecraft/blockstates/", "assets/minecraft/models/block/",
        "assets/minecraft/textures/block/", "assets/minecraft/textures/item/",
        "assets/minecraft/textures/colormap/", "assets/minecraft/lang/en_us.json")
LANGS = ("ko_kr",)


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return r.read()


def main():
    manifest = json.loads(get(MANIFEST))
    entry = next(v for v in manifest["versions"] if v["id"] == VERSION)
    meta = json.loads(get(entry["url"]))
    client = meta["downloads"]["client"]
    print(f"{VERSION} client.jar 다운로드 중 ({client['size'] / 1e6:.1f} MB)...")
    data = get(client["url"])
    if hashlib.sha1(data).hexdigest() != client["sha1"]:
        sys.exit("SHA1 불일치: 다운로드가 손상되었습니다.")
    count = 0
    with zipfile.ZipFile(io.BytesIO(data)) as jar:
        for name in jar.namelist():
            if name.endswith("/") or not name.startswith(KEEP):
                continue
            # zip 경로 조작 방지
            rel = Path(name).relative_to("assets/minecraft")
            if ".." in rel.parts:
                continue
            dest = OUT / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(jar.read(name))
            count += 1
    # 다른 언어 파일은 client.jar 가 아니라 공식 에셋 서버에 해시 이름으로 있다
    objects = json.loads(get(meta["assetIndex"]["url"]))["objects"]
    for lang in LANGS:
        obj = objects[f"minecraft/lang/{lang}.json"]
        h = obj["hash"]
        raw = get(f"https://resources.download.minecraft.net/{h[:2]}/{h}")
        if hashlib.sha1(raw).hexdigest() != h:
            sys.exit(f"SHA1 불일치: {lang}.json")
        dest = OUT / "lang" / f"{lang}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        count += 1
    (OUT / "VERSION").write_text(VERSION, encoding="utf-8")
    print(f"완료: {count}개 파일 → {OUT}")


if __name__ == "__main__":
    main()
