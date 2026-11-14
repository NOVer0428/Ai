"""사용: python sheet.py 출력.png 모듈:함수 ... — 템플릿 썸네일 모음(3열)"""
import importlib, sys
sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), ".."))
from PIL import Image, ImageDraw
from template_format import validate
import thumbnail
out, specs = sys.argv[1], sys.argv[2:]
rot = 0
W, H = 520, 400
cols = 3
rows = (len(specs) + cols - 1) // cols
o = Image.new("RGB", (W * cols, H * rows), (232, 226, 214))
d = ImageDraw.Draw(o)
for i, sp in enumerate(specs):
    mod, fn = sp.split(":")
    r = 0
    if "@" in fn:
        fn, r = fn.split("@"); r = int(r)
    data = validate(getattr(importlib.import_module(mod), fn)())
    im = thumbnail.render(data, rotation=r, size=(W, H))
    o.paste(im, ((i % cols) * W, (i // cols) * H), im)
    d.text(((i % cols) * W + 8, (i // cols) * H + 6), fn, fill=(40, 40, 40))
o.save(out)
