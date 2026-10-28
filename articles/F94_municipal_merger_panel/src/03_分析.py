"""03_分析：合併の扱い方（4通り＋按分の3方式）で、2000→2020年の人口増減の分析がどう変わるかを比べる。

扱い方
  A 再集計     … 2000年の旧市町村を2020年の境域に足し上げる（1,741単位）
  B 変化なしだけ … 2000〜2020年に合併に関わらなかった市町村だけ（complete case）
  C コード突合   … 2000年と2020年で同じコードどうしをそのままつなぐ（素朴な結合。消えたコードは落ちる）
  D 按分         … 2020年の人口を2000年の旧市町村に割り戻す（3,251単位）
                   D1 2000年人口の比 / D2 面積の比 / D3 1995→2000年の伸びを延長した比
指標
  中央値・人口加重の平均・20%以上減の割合・増加の割合・p10/p90・
  「人口が小さい町ほど減る」傾き（増減率 ～ log10(2000年人口) の OLS、ブートストラップ95%区間）
"""
import json
import warnings
warnings.filterwarnings("ignore")
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RNG = np.random.default_rng(94)
B = 1000

old = pd.read_csv(ROOT / "data/old_units_2000.csv", dtype={"code": str})
cw = pd.read_csv(ROOT / "data/crosswalk_2000_2020.csv", dtype={"code2000": str, "code2020": str})
ssds = pd.read_csv(ROOT / "data/ssds_present_boundary.csv", dtype={"code": str})
p20 = ssds[ssds.year == 2020].set_index("code").A1101
names20 = ssds[ssds.year == 2020].set_index("code").name

old = old.merge(cw[["code2000", "code2020", "unchanged", "merged"]], left_on="code", right_on="code2000")
old = old[old.pop2000 > 0]          # 三宅村（2000年は全島避難で人口0）を除く
old["pref"] = old.code.str[:2].astype(int)


def stats(df, base="pop0", now="pop1", label=""):
    d = df[(df[base] > 0) & df[now].notna()].copy()
    d["rate"] = (d[now] / d[base] - 1) * 100
    x = np.log10(d[base].values)
    y = d.rate.values

    def slope(ix):
        xx, yy = x[ix], y[ix]
        return np.polyfit(xx, yy, 1)[0]
    s = slope(np.arange(len(d)))
    bs = [slope(RNG.integers(0, len(d), len(d))) for _ in range(B)]
    return dict(label=label, n=int(len(d)),
                median=float(np.median(y)),
                weighted_mean=float((d[now].sum() / d[base].sum() - 1) * 100),
                share_decline20=float((y <= -20).mean() * 100),
                share_increase=float((y > 0).mean() * 100),
                share_increase20=float((y >= 20).mean() * 100),
                p10=float(np.percentile(y, 10)), p90=float(np.percentile(y, 90)),
                slope=float(s), slope_lo=float(np.percentile(bs, 2.5)), slope_hi=float(np.percentile(bs, 97.5))), d


def build(old, base_col="pop2000", alloc="pop"):
    """扱い方ごとの (pop0, pop1) の表を返す"""
    o = old.copy()
    o["pop0"] = o[base_col]
    out = {}
    # A 再集計
    a = o.groupby("code2020").pop0.sum().to_frame()
    a["pop1"] = p20.reindex(a.index)
    a["n_old"] = o.groupby("code2020").size()
    out["A"] = a
    # B 変化なしだけ
    b = o[o.unchanged].groupby("code2020").pop0.sum().to_frame()
    b["pop1"] = p20.reindex(b.index)
    out["B"] = b
    # C コード突合（2000年のコードが2020年にもあればつなぐ）
    c = o.set_index("code")[["pop0", "code2020", "unchanged"]].copy()
    c = c[c.index.isin(p20.index)]
    c["pop1"] = p20.reindex(c.index)
    c["absorber"] = ~c.unchanged
    out["C"] = c
    # D 按分（旧市町村へ割り戻す）
    d = o.set_index("code")[["pop0", "pop2000", "pop1995", "area", "code2020"]].copy()
    if alloc == "pop":
        w = d.pop2000
    elif alloc == "area":
        w = d.area
    else:  # trend: 1995→2000年の伸び率を20年延長（5年×4）
        g = (d.pop2000 / d.pop1995).clip(0.5, 2.0).fillna(1.0)
        w = d.pop2000 * g ** 4
    d["w"] = w / w.groupby(d.code2020).transform("sum")
    d["pop1"] = d.w * p20.reindex(d.code2020).values
    out["D"] = d
    return out


res = {}
frames = {}
main = build(old)
lab = {"A": "A 再集計（2020年の境域）", "B": "B 変化なしだけ", "C": "C コード突合", "D": "D1 按分（2000年人口比）"}
for k, df in main.items():
    res[k], frames[k] = stats(df, label=lab[k])
for alloc, k in [("area", "D2"), ("trend", "D3")]:
    res[k], frames[k] = stats(build(old, alloc=alloc)["D"], label={"D2": "D2 按分（面積比）", "D3": "D3 按分（1995→2000年の伸びを延長）"}[k])

# コード突合の「見かけの増加」：吸収した側の増減率
c = frames["C"]
res["C_detail"] = dict(
    absorbers=int(c.absorber.sum()),
    absorber_median=float(c.loc[c.absorber, "rate"].median()),
    nonabsorber_median=float(c.loc[~c.absorber, "rate"].median()),
    absorber_share_increase20=float((c.loc[c.absorber, "rate"] >= 20).mean() * 100),
    dropped_old_units=int(len(old) - len(c)),
    max_rate=float(c.rate.max()),
    n_over_100=int((c.rate >= 100).sum()),
)
# B に残る単位の特徴（選択の偏り）
a = frames["A"]
res["B_detail"] = dict(
    median_pop2000_B=float(frames["B"].pop0.median()),
    median_pop2000_A=float(a.pop0.median()),
    median_pop2000_merged_in_A=float(a.loc[a.n_old > 1, "pop0"].median()),
    rate_median_merged_in_A=float(a.loc[a.n_old > 1, "rate"].median()),
    rate_median_unmerged_in_A=float(a.loc[a.n_old == 1, "rate"].median()),
)

# ---------------------------------------------------------------- 頑健性
rob = []
def add(tag, frames_dict):
    for k in ["A", "B", "C", "D"]:
        st, _ = stats(frames_dict[k], label=k)
        rob.append(dict(check=tag, method=k, **{x: st[x] for x in ["n", "median", "share_decline20", "share_increase", "slope", "slope_lo", "slope_hi"]}))

add("基本（2000→2020）", main)
# R1 基準年を1995年に（1995年人口は2000年の境域に組み替え済み）
add("基準年1995（1995→2020）", build(old[old.pop1995 > 0], base_col="pop1995"))
# R2 政令市と東京23区を除く
add("政令市・23区を除く", build(old[~old.type.isin(["seirei", "ward23"]) & ~old.code2020.str[2:].astype(int).between(100, 199)]))
# R3 福島県を除く（原発事故の避難指示で2020年の人口が大きく動いた地域を含むため）
add("福島県を除く", build(old[old.pref != 7]))
# R4 2000年人口1,000人未満を除く（小さい分母）
small_groups = old.groupby("code2020").pop2000.transform("sum")
add("2000年人口1,000人未満の単位を除く", build(old[small_groups >= 1000]))
# R5 上九一色村を甲府市側に寄せる（分割編入の割り当てを変える）
alt = old.copy()
alt.loc[alt.code == "19341", "code2020"] = "19201"
add("分割編入の割り当てを変える", build(alt))
rob = pd.DataFrame(rob)
rob.to_csv(ROOT / "results/robustness.csv", index=False)

# 按分の方式の比較（D 内部の差）
d1, d2, d3 = frames["D"], frames["D2"], frames["D3"]
res["alloc_compare"] = dict(
    corr_D1_D3=float(np.corrcoef(d1.rate, d3.rate.reindex(d1.index))[0, 1]),
    within_group_sd_D1=0.0,
    within_group_sd_D3=float(d3[d3.code2020.duplicated(keep=False)].groupby("code2020").rate.std().median()),
    within_group_sd_D2=float(d2[d2.code2020.duplicated(keep=False)].groupby("code2020").rate.std().median()),
)

# ---------------------------------------------------------------- 都道府県別：合併の多さと、扱い方による差
pp = []
for pref, g in old.groupby("pref"):
    fr = build(g)
    sa, _ = stats(fr["A"])
    sc, _ = stats(fr["C"])
    sb, _ = stats(fr["B"]) if fr["B"].shape[0] > 3 else ({"median": np.nan}, None)
    pp.append(dict(pref=pref, n2000=len(g), n2020=g.code2020.nunique(),
                   merged_share=float((~g.unchanged).mean() * 100),
                   median_A=sa["median"], median_C=sc["median"], median_B=sb["median"],
                   n_C=sc["n"]))
pp = pd.DataFrame(pp)
pp["diff_C_A"] = pp.median_C - pp.median_A
pp.to_csv(ROOT / "results/by_prefecture.csv", index=False)
res["pref"] = dict(corr_merged_share_diffCA=float(pp[["merged_share", "diff_C_A"]].corr().iloc[0, 1]),
                   max_diff=float(pp.diff_C_A.max()), min_diff=float(pp.diff_C_A.min()))

# 年ごとの市町村数
ev = pd.read_csv(ROOT / "data/merger_events.csv", dtype=str)
res["timeline_note"] = "市町村数の推移は 04_図 で crosswalk から計算"

summary = pd.DataFrame([res[k] for k in ["A", "B", "C", "D", "D2", "D3"]])
summary.to_csv(ROOT / "results/summary_by_method.csv", index=False)
frames["A"].assign(name=names20.reindex(frames["A"].index)).to_csv(ROOT / "results/unit_rates_A.csv")
frames["C"].to_csv(ROOT / "results/unit_rates_C.csv")
json.dump(res, open(ROOT / "results/results.json", "w"), ensure_ascii=False, indent=1)
print(summary[["label", "n", "median", "weighted_mean", "share_decline20", "share_increase", "share_increase20", "slope", "slope_lo", "slope_hi"]].round(2).to_string())
print(json.dumps({k: res[k] for k in ["C_detail", "B_detail", "alloc_compare", "pref"]}, ensure_ascii=False, indent=1))
print(rob.round(2).to_string())
