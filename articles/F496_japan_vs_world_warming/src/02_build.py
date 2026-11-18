"""data/raw の CSV・テキスト・解説ページから、年ごとの表 data/annual.csv・季節の表 data/seasonal.csv・公表値 data/published.json を作る。ネットにはつながない。"""
import pathlib, re, json, io, html
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
rd = lambda f: pd.read_csv(io.StringIO((RAW / f).read_bytes().decode("cp932")))
j = rd("an_jpn.csv"); j.columns = ["year", "japan"]
w = rd("an_wld.csv"); w.columns = ["year", "world", "nh", "sh"]
sst = []
for line in (RAW / "sst_global.txt").read_text(encoding="utf-8", errors="replace").splitlines():
    m = re.match(r"^\s*(\d{4})\s+(-?\d+\.\d+)\s*$", line)
    if m:
        sst.append((int(m.group(1)), float(m.group(2))))
s = pd.DataFrame(sst, columns=["year", "sst"])
a = w.merge(j, on="year", how="left").merge(s, on="year", how="left").sort_values("year")
a.to_csv(ROOT / "data" / "annual.csv", index=False)

sj = rd("ssn_jpn.csv"); sw = rd("ssn_wld.csv")
names = ["winter", "spring", "summer", "autumn"]
sj.columns = ["year"] + [f"japan_{n}" for n in names]; sw.columns = ["year"] + [f"world_{n}" for n in names]
ss = sw.merge(sj, on="year", how="left").sort_values("year")
ss.to_csv(ROOT / "data" / "seasonal.csv", index=False)

pub = {}
for key, f in [("japan", "page_an_jpn.html"), ("world", "page_an_wld.html"), ("world_land", "page_land_an_wld.html")]:
    t = re.sub(r"<[^>]+>", "", html.unescape((RAW / f).read_text(encoding="utf-8")))
    m = re.search(r"100年あたり([0-9.]+)℃", t)
    pub[key] = float(m.group(1))
json.dump(pub, open(ROOT / "data" / "published.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(a.year.min(), a.year.max(), a.japan.notna().sum(), a.sst.notna().sum(), pub)
