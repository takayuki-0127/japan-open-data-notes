"""e-Stat 統計GIS から、国勢調査の小地域（町丁・字等）の年齢別人口と境界データをダウンロードして展開する。
2000年：統計表 T000002（年齢5歳階級別・男女別人口）、境界 A002005212000
2020年：統計表 T001082（年齢5歳階級別・男女別人口）、境界 A002005212020
対象：北海道(01)・神奈川県(14)・福岡県(40)
"""
import io, zipfile, time
import requests
from common import RAW

BASE = "https://www.e-stat.go.jp/gis/statmap-search/data"
JOBS = []
for c in ["01", "14", "40"]:
    JOBS.append((f"{BASE}?statsId=T000002&code={c}&downloadType=2", f"tblT000002C{c}"))
    JOBS.append((f"{BASE}?statsId=T001082&code={c}&downloadType=2", f"tblT001082C{c}"))
    for y in ["2000", "2020"]:
        JOBS.append((f"{BASE}?dlserveyId=A00200521{y}&code={c}&coordSys=1&format=shape&downloadType=5&datum=2000",
                     f"A00200521{y}DDSWC{c}"))

if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for url, name in JOBS:
        out = RAW / name
        if out.exists():
            continue
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        zipfile.ZipFile(io.BytesIO(r.content)).extractall(out)
        print("saved", name, len(r.content))
        time.sleep(2)
