"""各年の表1を読み、年ごとに最も新しい公表の値を選んで、形別・年齢別の CSV を作る。重なる年の公表どうしの差を確かめる。"""
import pathlib, sys
import numpy as np
import pandas as pd
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import ROOT, RAW, read_t1

OUT = ROOT / "data"; RES = ROOT / "results"; RES.mkdir(exist_ok=True)
ORDER = ["2008", "2009", "2009b", "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025"]
files = {k: next(p.name for p in RAW.glob(f"shinki_t1_{k}.*")) for k in ORDER}
D = pd.concat([read_t1(files[k]).assign(pub=i, pubname=k) for i, k in enumerate(ORDER)], ignore_index=True)
D = D[~D.vertical_merge]  # 年齢をまとめた縦の結合セル（2006年の40歳以上）は使わない
D.to_csv(OUT / "t1_long_all_releases.csv", index=False)

# 公表どうしの照合（同じ年・形・行）
g = D.dropna(subset=["value"]).groupby(["year", "form", "row"]).value
rng = (g.max() - g.min()).rename("range").reset_index()
cnt = g.size().rename("n").reset_index()
cmpdf = rng.merge(cnt)
cmpdf = cmpdf[cmpdf.n > 1]
cmpdf.to_csv(RES / "build_release_compare.csv", index=False)

# 年ごとに使う公表（計画どおり、各年の値が載る公表のうち4年分をまとめたもの・最も新しいもの）。
# 2010・2011年の公表には、震災で調べられなかった地域を除いた参考値の列が加わり、列の位置がずれるため、主には使わない。
PRIMARY = {**{y: "2008" for y in (2006, 2007)}, **{y: "2009b" for y in (2008, 2009)}, **{y: "2013" for y in range(2010, 2014)},
           **{y: "2017" for y in range(2014, 2018)}, **{y: "2021" for y in range(2018, 2022)}, **{y: "2025" for y in range(2022, 2026)}}
latest = D.dropna(subset=["value"])
latest = latest[latest.apply(lambda r: PRIMARY.get(r.year) == r.pubname, axis=1)]
W = latest.pivot_table(index=["year", "form"], columns="row", values="value").reset_index()


def col(df, c):
    return df[c] if c in df else pd.Series(np.nan, index=df.index)


W["le39_x"] = col(W, "le39").fillna(col(W, "a15") + col(W, "a20") + col(W, "a30"))
a40 = col(W, "a40").fillna(col(W, "a40_44") + col(W, "a45_49"))
W["le49_x"] = col(W, "le49").fillna(W.le39_x + a40)
W["a40_49_x"] = W.le49_x - W.le39_x
W["a50_x"], W["a60_x"], W["a65_x"] = col(W, "a50"), col(W, "a60"), col(W, "a65")
W["unk_x"] = col(W, "unk").fillna(0.0)
out = W[["year", "form", "all", "le39_x", "le49_x", "a40_49_x", "a50_x", "a60_x", "a65_x", "unk_x"]].rename(columns=lambda c: c.replace("_x", ""))
out = out.sort_values(["year", "form"]).reset_index(drop=True)
src = latest.groupby("year").pubname.max().rename("release")
out = out.merge(src, left_on="year", right_index=True)
out.to_csv(OUT / "new_farmers.csv", index=False)

# 点検
chk = []
chk.append(("公表どうしの最大の差（同じ年・形・行、人）", float(cmpdf["range"].max()), int(len(cmpdf))))
ok = cmpdf[~(cmpdf.year.isin([2009, 2011]) & (cmpdf.form == "sannyu"))]
chk.append(("公表どうしの最大の差（2009・2011年の新規参入者＝参考値の列のずれを除く）", float(ok["range"].max()), int(len(ok))))
t = out.pivot(index="year", columns="form", values="all")
chk.append(("形の和（自営＋雇用＋参入）と計の最大の差（人）", float((t.jiei + t.koyo + t.sannyu - t.total).abs().max()), int(len(t))))
age = out.dropna(subset=["le49", "a50", "a60", "a65"])
s = age.le49 + age.a50 + age.a60 + age.a65 + age.unk
chk.append(("年齢の和（49歳以下＋50〜59＋60〜64＋65以上＋不詳）と計の最大の差（人、2007年〜）", float((s - age["all"]).abs().max()), int(len(age))))
for f in ["total", "jiei", "koyo", "sannyu"]:
    e = out[out.form == f].set_index("year")
    chk.append((f"{f}：49歳以下がそろう最初の年", float(e.le49.first_valid_index()), 0))
pd.DataFrame(chk, columns=["check", "value", "n"]).to_csv(RES / "build_checks.csv", index=False)
print(pd.DataFrame(chk).to_string())
