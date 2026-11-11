"""01 取得：損害保険料率算出機構「火災保険・地震保険の概況」2015〜2025年度版の Excel を data/raw に置く。
ファイルが既にあれば md5 を表示するだけ。無ければ公開 URL から取る（2026-11-11 に取得）。"""
import hashlib, pathlib, sys, urllib.request
RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
URL = "https://www.giroj.or.jp/publication/outline_k/k_{y}.xlsx"
RAW.mkdir(parents=True, exist_ok=True)
for y in range(2015, 2026):
    p = RAW / f"k_{y}.xlsx"
    if not p.exists():
        print("download", y, file=sys.stderr)
        urllib.request.urlretrieve(URL.format(y=y), p)
    print(p.name, hashlib.md5(p.read_bytes()).hexdigest())
