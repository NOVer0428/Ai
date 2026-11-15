"""실내 단면: 각 템플릿을 지정 높이에서 잘라 위에서 본 모습(4열)"""
import importlib, sys
sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), ".."))
from PIL import Image, ImageDraw
from template_format import validate
import thumbnail
out = sys.argv[1]
specs = [a.split("=") for a in sys.argv[2:]]  # 모듈:함수=잘라낼 y
W, H, cols = 420, 330, 4
rows = (len(specs) + cols - 1) // cols
o = Image.new("RGB", (W * cols, H * rows), (40, 44, 52))
d = ImageDraw.Draw(o)
for i, (sp, cut) in enumerate(specs):
    mod, fn = sp.split(":")
    data = validate(getattr(importlib.import_module(mod), fn)())
    im = thumbnail.render(data, rotation=0, max_y=int(cut), size=(W, H), shadow=False)
    o.paste(im, ((i % cols) * W, (i // cols) * H), im)
    d.text(((i % cols) * W + 8, (i // cols) * H + 6), f"{fn} (y<={cut})", fill=(230, 230, 230))
o.save(out)
