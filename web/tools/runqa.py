"""사용: python tools/runqa.py 결과.txt 모듈:함수 ... — 구조 점검(+엄격 점검) 결과를 UTF-8 파일로 저장"""
import importlib
import io
import os
import sys
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from qa import check, strict_check  # noqa: E402
from template_format import validate  # noqa: E402

out = io.open(sys.argv[1], "w", encoding="utf-8")
for spec in sys.argv[2:]:
    mod, fn = spec.split(":")
    data = validate(getattr(importlib.import_module(mod), fn)())
    iss = check(data) + strict_check(data)
    out.write(f"== {fn}: {len(iss)} {dict(Counter(i[0] for i in iss))}\n")
    for kind, n, p in iss[:40]:
        out.write(f"   {kind}: {n} @ {p}\n")
out.close()
