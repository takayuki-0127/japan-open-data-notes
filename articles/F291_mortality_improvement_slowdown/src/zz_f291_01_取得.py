"""01 取得：新しい取得はしない。F86（JMD）と F268（簡易生命表）で取得済みのファイルを写して md5 を記録する。"""
import hashlib, json
from common import RAW, DATA
out = {}
for f in sorted(RAW.glob("*.csv")):
    out[f.name] = hashlib.md5(f.read_bytes()).hexdigest()
(DATA / "MANIFEST.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(out)
