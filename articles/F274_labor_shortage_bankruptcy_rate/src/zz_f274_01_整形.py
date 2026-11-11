"""data/sources.csv（公表値を1件ずつ出典つきで書き写したもの）から、年ごとの表 data/processed/panel.csv を作る。
ネットワークは使わない。元の記事・PDFは著作権のためリポジトリに入れていない（data/raw_local は .gitignore）。"""
import csv, json, os
H = os.path.dirname(os.path.abspath(__file__)) + "/../"
rows = list(csv.DictReader(open(H + "data/sources.csv", encoding="utf-8")))
S = {}
for r in rows:
    S.setdefault(r["series"], {})[int(r["year"])] = float(r["value"])
years = list(range(2014, 2026))
P = []
# 法人数：暦年 t に年度 t を当てる。2025年度はまだ公表されていないので、2023→2024年度の伸び率で延ばす（推測）
hoj = dict(S["nta_hojin_fy"]); g = hoj[2024] / hoj[2023]; hoj[2025] = round(hoj[2024] * g)
# 企業数（経済センサス）：2016・2021年の間は直線、2014-2016も直線、2022年以降は2016→2021年の傾きで延ばす（推測）
kc = S["kigyo_census"]
def kigyo(y):
    if y <= 2016: return kc[2014] + (kc[2016] - kc[2014]) * (y - 2014) / 2
    return kc[2016] + (kc[2021] - kc[2016]) * (y - 2016) / 5
for y in years:
    d = {"year": y, "hojin": hoj.get(y), "hojin_extrap": int(y == 2025), "kigyo": round(kigyo(y)), "kigyo_extrap": int(y > 2021 or y in (2015,) or y in range(2017, 2021)),
         "tdb_jinte": S["tdb_jinte"].get(y), "tdb_total": S["tdb_total"].get(y), "tsr_total": S["tsr_total"].get(y),
         "tsr_kyujinnan": S["tsr_kyujinnan"].get(y), "tsr_taishoku": S["tsr_taishoku"].get(y), "tsr_jinkenhi": S["tsr_jinkenhi"].get(y),
         "tsr_koukeisha": S["tsr_koukeisha"].get(y), "tsr_3f_fy": S["tsr_3f_fy"].get(y), "yuko_kyujin": S["yuko_kyujin"].get(y)}
    f3 = [d["tsr_kyujinnan"], d["tsr_taishoku"], d["tsr_jinkenhi"]]
    d["tsr_3f"] = sum(f3) if None not in f3 else None
    d["tsr_4f"] = d["tsr_3f"] + d["tsr_koukeisha"] if d["tsr_3f"] is not None and d["tsr_koukeisha"] is not None else None
    P.append(d)
os.makedirs(H + "data/processed", exist_ok=True)
with open(H + "data/processed/panel.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(P[0])); w.writeheader()
    for d in P: w.writerow({k: ("" if v is None else (int(v) if isinstance(v, float) and v.is_integer() else v)) for k, v in d.items()})
json.dump({"hojin_2025_growth_used": g}, open(H + "data/processed/notes.json", "w"))
print("rows", len(P), "hojin2025", hoj[2025], "growth", round(g, 4))
