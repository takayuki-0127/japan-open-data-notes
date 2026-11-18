"""03b_requestion.py（問い直し、結果を見てから足した）
(1) 2019年→2020年の伸びは、比べる2019年の値（古い方法／新しい方法）でどれだけ変わるか。
(2) 産業計の差のうち、企業規模の人数の構成の違い（10〜99人が多く数えられる）で説明できる分はどれだけか。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"
d = pd.read_csv(ROOT / "data" / "wage_long.csv")


def pick(method, year, size="計", sex="計", industry="TOTAL", age="計"):
    s = d[(d["method"] == method) & (d["year"] == year) & (d["industry"] == industry) & (d["size"] == size) & (d["sex"] == sex) & (d["age"] == age)]
    assert len(s) == 1
    return s.iloc[0]


rows = []
for sex in ["計", "男", "女"]:
    for size in ["計", "1000+", "100-999", "10-99"]:
        v20 = pick("new2020", 2020, size, sex)["shoteinai"]
        vo = pick("old", 2019, size, sex)["shoteinai"]; vn = pick("new", 2019, size, sex)["shoteinai"]
        rows.append(dict(sex=sex, size=size, y2020=v20, old_2019=vo, new_2019=vn,
                         growth_vs_old=round(100 * (v20 / vo - 1), 2), growth_vs_new=round(100 * (v20 / vn - 1), 2)))
G = pd.DataFrame(rows)
G["gap_pt"] = (G["growth_vs_new"] - G["growth_vs_old"]).round(2)
G.to_csv(R / "requestion_2020_growth.csv", index=False)

# 規模の構成で分ける
sz = ["1000+", "100-999", "10-99"]
o = pd.DataFrame({z: pick("old", 2019, z) for z in sz}).T
n = pd.DataFrame({z: pick("new", 2019, z) for z in sz}).T
wo = o["workers"].astype(float) / o["workers"].astype(float).sum(); wn = n["workers"].astype(float) / n["workers"].astype(float).sum()
xo, xn = o["shoteinai"].astype(float), n["shoteinai"].astype(float)
size_ss = dict(recon_old=round(float((wo * xo).sum()), 2), recon_new=round(float((wn * xn).sum()), 2),
               wage_effect=round(float((wo * (xn - xo)).sum()), 2), composition_effect=round(float(((wn - wo) * xn).sum()), 2),
               share_old={z: round(float(wo[z]) * 100, 1) for z in sz}, share_new={z: round(float(wn[z]) * 100, 1) for z in sz})
out = {"growth_2020": G.to_dict(orient="records"), "size_shift_share": size_ss}
json.dump(out, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(G.to_string()); print(size_ss)
