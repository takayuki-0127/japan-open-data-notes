"""01 取得：JIPデータベース2023 の3つの Excel を data/raw に置き、md5 を確かめる。
ファイルが無ければ RIETI のサイトから取る（ネットワークに出られる環境で）。
"""
import hashlib, json, pathlib, sys, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
BASE = "https://www.rieti.go.jp/jp/database/JIP2023/data/"
FILES = {
    "jip2023_2.xlsx": "430aaf3dfca4ad7a589825c3c5cf1764",    # 資本（投資・資産マトリックス）
    "jip2023_4.xlsx": "3517b51ff6e859a8e7bf2ddef30db345",    # 成長会計
    "jip2023_3-8.xlsx": "eef5d7716db69ae6e0d3e7a61f3d684d",  # 部門別マンアワー（水準）
}
RAW.mkdir(parents=True, exist_ok=True)
out = {}
for f, md5 in FILES.items():
    p = RAW / f
    if not p.exists():
        req = urllib.request.Request(BASE + f, headers={"User-Agent": "Mozilla/5.0"})
        p.write_bytes(urllib.request.urlopen(req, timeout=120).read())
    h = hashlib.md5(p.read_bytes()).hexdigest()
    out[f] = {"md5": h, "ok": h == md5, "url": BASE + f}
    print(f, h, "OK" if h == md5 else "NG（版が変わった可能性）")
(ROOT / "data" / "MANIFEST.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
if not all(v["ok"] for v in out.values()):
    sys.exit("md5 が一致しない")
