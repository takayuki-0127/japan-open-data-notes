"""F83 03 分析：労働生産性の伸びのシフトシェア分解
P = Σ p_i s_i （p_i：産業の1人当たり実質付加価値、s_i：就業者のシェア）
ΔP = Σ Δp_i s_i0（産業内）+ Σ p_i0 Δs_i（静学的シフト）+ Σ Δp_i Δs_i（動学的シフト＝交差項）
"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, MAJOR, MFG

RES.mkdir(exist_ok=True)
pan = pd.read_csv(DATA / "panel.csv")
tot = pan[pan.level == "total"].set_index("year")
PERIODS = [(1994, 2024), (1994, 2000), (2000, 2008), (2008, 2013), (2013, 2019), (2019, 2024)]


def frame(inds, va="real", lab="emp", drop=()):
    x = pan[pan.ind.isin(inds) & ~pan.ind.isin(drop)].copy()
    x["L"] = x["emp"] * (x["hours"] if lab == "hours" else 1.0)
    x["Y"] = x[va]
    return x


def decomp(x, y0, y1):
    a = x[x.year == y0].set_index("ind")
    b = x[x.year == y1].set_index("ind")
    s0, s1 = a.L / a.L.sum(), b.L / b.L.sum()
    p0, p1 = a.Y / a.L, b.Y / b.L
    P0, P1 = (p0 * s0).sum(), (p1 * s1).sum()
    w = (p1 - p0) * s0
    st = p0 * (s1 - s0)
    it = (p1 - p0) * (s1 - s0)
    n = y1 - y0
    tot_g = P1 / P0 - 1
    out = dict(y0=y0, y1=y1, P0=P0, P1=P1, growth=tot_g,
               within=w.sum() / P0, static=st.sum() / P0, inter=it.sum() / P0)
    # 年率（ポイント）：成長率の年率を、各成分の割合で配分
    ann = (P1 / P0) ** (1 / n) - 1
    for k in ["within", "static", "inter"]:
        out[k + "_ann"] = ann * out[k] / tot_g if tot_g != 0 else np.nan
    out["ann"] = ann
    det = pd.DataFrame(dict(s0=s0, s1=s1, p0=p0, p1=p1, within=w / P0, static=st / P0, inter=it / P0))
    return out, det


def chained(x, y0, y1):
    """1年ごとに分解して積み上げる（期間の端の選び方に左右されにくい）"""
    acc = dict(within=0.0, static=0.0, inter=0.0)
    g = 1.0
    for y in range(y0, y1):
        o, _ = decomp(x, y, y + 1)
        for k in acc:
            acc[k] += o[k] * g
        g *= 1 + o["growth"]
    return dict(growth=g - 1, **acc)


base = frame(MAJOR)
res = []
dets = {}
for y0, y1 in PERIODS:
    o, det = decomp(base, y0, y1)
    res.append(o)
    dets[f"{y0}-{y1}"] = det
R = pd.DataFrame(res)
R.to_csv(RES / "decomp_periods.csv", index=False)
dets["1994-2024"].to_csv(RES / "decomp_by_industry_1994_2024.csv")
dets["2013-2019"].to_csv(RES / "decomp_by_industry_2013_2019.csv")
dets["2019-2024"].to_csv(RES / "decomp_by_industry_2019_2024.csv")

# 産業の水準と伸び
lv = base[base.year.isin([1994, 2024])].pivot(index="ind", columns="year", values=["Y", "L"])
ind = pd.DataFrame({
    "p1994_man": lv[("Y", 1994)] / lv[("L", 1994)] * 10,   # 万円/人（実質2020年価格）
    "p2024_man": lv[("Y", 2024)] / lv[("L", 2024)] * 10,
    "s1994": lv[("L", 1994)] / lv[("L", 1994)].sum(),
    "s2024": lv[("L", 2024)] / lv[("L", 2024)].sum(),
})
ind["g_ann"] = (ind.p2024_man / ind.p1994_man) ** (1 / 30) - 1
ind["ds"] = ind.s2024 - ind.s1994
ind.to_csv(RES / "industry_levels.csv")
rho = ind[["g_ann", "ds"]].corr(method="spearman").iloc[0, 1]
rel = ind.p1994_man / (ind.p1994_man * ind.s1994).sum()
rho_lvl = pd.Series(rel).corr(ind.ds, method="spearman")

# 足し上げた実質と公式の合計（連鎖の非加法性の確認）
sumreal = base.groupby("year").Y.sum()
off = tot["real"]
nonadd = (sumreal / off - 1).loc[[1994, 2008, 2024]].round(4).to_dict()
P_off = (off / tot["emp"])
g_off = P_off[2024] / P_off[1994] - 1

# 頑健性（1994→2024 と 2013→2019）
var = {
    "基本（16産業・就業者）": frame(MAJOR),
    "労働時間あたり": frame(MAJOR, lab="hours"),
    "不動産業を除く": frame(MAJOR, drop=("不動産業",)),
    "製造業を14業種に分ける（29産業）": frame([m for m in MAJOR if m != "製造業"] + MFG),
    "名目付加価値": frame(MAJOR, va="nom"),
}
rob = []
for k, x in var.items():
    for y0, y1 in [(1994, 2024), (2013, 2019), (2019, 2024)]:
        o, _ = decomp(x, y0, y1)
        rob.append(dict(variant=k, period=f"{y0}-{y1}", growth=o["growth"], within=o["within"],
                        static=o["static"], inter=o["inter"]))
for y0, y1 in [(1994, 2024), (2013, 2019), (2019, 2024)]:
    c = chained(base, y0, y1)
    rob.append(dict(variant="1年ごとに分解して積み上げ", period=f"{y0}-{y1}", **c))
ROB = pd.DataFrame(rob)
ROB.to_csv(RES / "robustness.csv", index=False)

summ = dict(
    periods=R.round(5).to_dict("records"),
    nonadditivity_sum_vs_official=nonadd,
    official_P_growth_1994_2024=round(g_off, 4),
    spearman_growth_vs_share_change=round(rho, 3),
    spearman_level1994_vs_share_change=round(rho_lvl, 3),
    industries=ind.round(4).reset_index().to_dict("records"),
)
json.dump(summ, open(RES / "summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 200)
print(R[["y0", "y1", "growth", "within", "static", "inter", "ann", "within_ann", "static_ann", "inter_ann"]].round(4))
print(ind.sort_values("g_ann").round(3))
print("nonadd", nonadd, "official growth", round(g_off, 4), "rho", rho, rho_lvl)
print(ROB.round(4))
