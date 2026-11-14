"""사용: python tools/runqa.py 결과.txt 모듈:함수 ... — 구조 점검 결과를 UTF-8 파일로 저장"""
import sys, io
sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), ".."))
from collections import Counter
import importlib
from qa import check
from template_format import validate
out = io.open(sys.argv[1], "w", encoding="utf-8")
for spec in sys.argv[2:]:
    mod, fn = spec.split(":")
    iss = check(validate(getattr(importlib.import_module(mod), fn)()))
    out.write(f"== {fn}: {len(iss)} {dict(Counter(i[0] for i in iss))}\n")
    for kind, n, p in iss[:25]:
        out.write(f"   {kind}: {n} @ {p}\n")
out.close()
