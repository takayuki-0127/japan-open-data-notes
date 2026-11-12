"""398 住宅の所有の関係ごとの通勤時間（1988〜2023年）：住宅・土地統計調査 時系列統計表 第23-1表
家計を主に支える者が雇用者である世帯。区分のそろう1988・1993・2008・2013・2018・2023年を使う"""
import csv, json, re
from collections import OrderedDict
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save
SRC = "出典：総務省統計局「令和5年住宅・土地統計調査」時系列統計表 第23-1表をもとに作成者が加工して作成"
raw = list(csv.reader(open(DATA / "raw" / "hlts_ts_t23_1.csv", encoding="utf-8")))
sh = OrderedDict()
for x in raw:
    sh.setdefault(x[0], []).append(x[1:])
YEAR = {"昭和63年": 1988, "平成5年": 1993, "平成20年": 2008, "平成25年": 2013, "平成30年": 2018, "令和５年": 2023}
# 列の並び（総数のあと）：年ごとに違うので、そろえた8区分にまとめる位置を決める
LAY = {1988: dict(home=1, u15=2, m15=3, m30=4, m45=5, m60=[6], m90=[7], m120=8, unk=9, med=10),
       1993: dict(home=1, u15=2, m15=3, m30=4, m45=5, m60=[6, 7], m90=[8], m120=9, unk=10, med=11),
       2008: dict(home=1, u15=2, m15=3, m30=4, m45=5, m60=[6, 7], m90=[8, 9], m120=10, unk=11, med=12),
       2013: dict(home=1, u15=2, m15=3, m30=4, m45=5, m60=[6], m90=[7], m120=8, unk=9, med=10)}
LAY[2018] = LAY[2023] = LAY[2013]
num = lambda s: 0.0 if s.strip() in ("-", "") else float(s)
def tenure(lab):
    lab = lab.replace("　", "").replace("\n", "").strip()
    if lab == "総数": return "総数"
    if lab == "持ち家": return "持ち家"
    if lab.startswith("公営"): return "公営の借家"
    if lab.startswith("公団") or lab.startswith("都市再生機構"): return "UR・公社の借家"
    if lab.startswith("民営借家(木造"): return "民営借家（木造）"
    if lab.startswith("民営借家(非木造"): return "民営借家（非木造）"
    if lab.startswith("給与住宅"): return "給与住宅"
    return None
rec = []
for k, rows in sh.items():
    if k not in YEAR: continue
    y = YEAR[k]; L = LAY[y]; seen = set()
    j0 = next(i for i, x in enumerate(rows) if x[1].strip() == "全国")
    for x in rows[j0 + 1:]:
        t = tenure(x[1])
        if x[1].strip() in ("３大都市圏", "関東大都市圏") : break
        if t is None or (t, ) in seen or not x[3].strip(): continue
        v = [num(c) for c in x[3:]]
        # 民営借家（木造）は1988・1993年に2行（設備専用・共用）あるので足す
        r = dict(year=y, tenure=t, total=v[0], home=v[L["home"]], u15=v[L["u15"]], m15=v[L["m15"]], m30=v[L["m30"]], m45=v[L["m45"]],
                 m60=sum(v[i] for i in L["m60"]), m90=sum(v[i] for i in L["m90"]), m120=v[L["m120"]], unk=v[L["unk"]], median_pub=v[L["med"]])
        rec.append(r)
d = pd.DataFrame(rec)
b = ["home", "u15", "m15", "m30", "m45", "m60", "m90", "m120", "unk"]
agg = {c: "sum" for c in ["total"] + b}; agg["median_pub"] = "first"
d = d.groupby(["year", "tenure"], as_index=False).agg(agg)
assert len(d) == 6 * 7, len(d)
assert ((d[b].sum(axis=1) - d.total).abs() <= 600).all(), (d[b].sum(axis=1) - d.total).abs().max()
# 民営借家（木造＋非木造）をまとめた行を足す
m = d[d.tenure.str.startswith("民営借家")].groupby("year", as_index=False)[["total"] + b].sum(); m["tenure"] = "民営借家"; m["median_pub"] = np.nan
d = pd.concat([d, m], ignore_index=True)
d["known"] = d.total - d.unk
d["p60"] = (d.m60 + d.m90 + d.m120) / d.known * 100
d["p90"] = (d.m90 + d.m120) / d.known * 100
d["p_u15"] = (d.home + d.u15) / d.known * 100
d["p_u30"] = (d.home + d.u15 + d.m15) / d.known * 100
d["p_unk"] = d.unk / d.total * 100
# 中央値を区分から自分で出す（自宅は0分として最初の区分に入れる。区分の中は一様と置く）
edges = [0, 15, 30, 45, 60, 90, 120, 180]
def med(r):
    c = np.array([r.home + r.u15, r.m15, r.m30, r.m45, r.m60, r.m90, r.m120]); cum = np.cumsum(c); h = cum[-1] / 2
    i = int(np.searchsorted(cum, h)); lo = cum[i - 1] if i else 0
    return edges[i] + (h - lo) / c[i] * (edges[i + 1] - edges[i])
d["median_calc"] = d.apply(med, axis=1)
d.to_csv(DATA / "commute_by_tenure.csv", index=False)
T = ["総数", "持ち家", "民営借家", "公営の借家", "UR・公社の借家", "給与住宅"]
pv = lambda c: d.pivot(index="tenure", columns="year", values=c).loc[T + ["民営借家（木造）", "民営借家（非木造）"]]
for c in ["p60", "p90", "p_u15", "p_u30", "median_pub", "median_calc", "p_unk", "total"]:
    pv(c).round(2).to_csv(RES / f"a398_{c}.csv")
g = d.set_index(["tenure", "year"])
res = {c: {t: {int(y): round(float(g.loc[(t, y), c]), 1) for y in sorted(YEAR.values())} for t in T} for c in ["p60", "p90", "p_u15", "median_calc", "p_unk"]}
res["median_pub"] = {t: {int(y): float(g.loc[(t, y), "median_pub"]) for y in sorted(YEAR.values())} for t in ["総数", "持ち家", "公営の借家", "UR・公社の借家", "給与住宅", "民営借家（木造）", "民営借家（非木造）"]}
res["median_gap_calc_vs_pub_max"] = float((d.median_calc - d.median_pub).abs().max())
res["total"] = {t: {int(y): int(g.loc[(t, y), "total"]) for y in (1988, 2023)} for t in T}
res["gap_owner_minus_private_p60"] = {int(y): round(float(g.loc[("持ち家", y), "p60"] - g.loc[("民営借家", y), "p60"]), 1) for y in sorted(YEAR.values())}
# 不詳をすべて「60分以上」または「60分未満」と置いたときの幅（給与住宅の不詳が多いため）
res["p60_bounds_2023"] = {t: [round(float((g.loc[(t, 2023), ["m60", "m90", "m120"]].sum()) / g.loc[(t, 2023), "total"] * 100), 1),
                              round(float((g.loc[(t, 2023), ["m60", "m90", "m120", "unk"]].sum()) / g.loc[(t, 2023), "total"] * 100), 1)] for t in T}
# 全体の変化を、所有の関係の構成と、それぞれの中の変化に分ける（1988→2023、5区分）
parts = ["持ち家", "民営借家", "公営の借家", "UR・公社の借家", "給与住宅"]
w0 = np.array([g.loc[(t, 1988), "known"] for t in parts]); w1 = np.array([g.loc[(t, 2023), "known"] for t in parts]); w0 = w0 / w0.sum(); w1 = w1 / w1.sum()
r0 = np.array([g.loc[(t, 1988), "p60"] for t in parts]); r1 = np.array([g.loc[(t, 2023), "p60"] for t in parts])
res["decomp_1988_2023"] = {"all5_1988": float((w0 * r0).sum()), "all5_2023": float((w1 * r1).sum()), "within": float(((w0 + w1) / 2 * (r1 - r0)).sum()), "mix": float(((r0 + r1) / 2 * (w1 - w0)).sum()),
                           "share_1988": dict(zip(parts, (w0 * 100).round(1))), "share_2023": dict(zip(parts, (w1 * 100).round(1)))}
json.dump(res, open(RES / "a398_main.json", "w"), ensure_ascii=False, indent=1)

col = {"総数": INK, "持ち家": BLUE, "民営借家": ORANGE, "公営の借家": GREEN, "UR・公社の借家": "#8a5cc2", "給与住宅": GRAY}
ys = sorted(YEAR.values())
fig, ax = plt.subplots(figsize=(9, 4.6))
for t in T:
    v = [g.loc[(t, y), "p60"] for y in ys]; ax.plot(ys, v, marker="o", color=col[t], lw=2.4 if t == "総数" else 1.6, ls="--" if t == "総数" else "-", label=t)
    ax.text(2023.6, v[-1], f"{v[-1]:.1f}%", color=col[t], fontsize=9, va="center")
ax.set_xticks(ys); ax.set_xlim(1986, 2027); ax.set_ylabel("通勤1時間以上の割合（%、不詳を除く）"); ax.set_title("通勤に片道1時間以上かかる世帯の割合（住宅の所有の関係別）"); ax.legend(frameon=False, ncol=3, fontsize=9)
ax.text(1994, ax.get_ylim()[0] + 0.5, "1998・2003年は区分が違うため除いた", fontsize=8, color=GRAY)
save(fig, "a398_over60.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.6))
lab = ["自宅・15分未満", "15〜29分", "30〜44分", "45〜59分", "60〜89分", "90分以上"]; cs = ["#cfe0f5", LIGHT, BLUE, "#1c5aa8", ORANGE, "#b5461c"]
left = np.zeros(len(T))
for l, c, k in zip(lab, cs, [["home", "u15"], ["m15"], ["m30"], ["m45"], ["m60"], ["m90", "m120"]]):
    v = np.array([g.loc[(t, 2023), k].sum() / g.loc[(t, 2023), "known"] * 100 for t in T]); ax.barh(T[::-1], v[::-1], left=left[::-1], color=c, label=l)
    for i, (vv, ll) in enumerate(zip(v[::-1], left[::-1])):
        if vv >= 6: ax.text(ll + vv / 2, i, f"{vv:.0f}", ha="center", va="center", fontsize=8.5, color="white" if c not in ("#cfe0f5", LIGHT) else INK)
    left += v
ax.set_xlim(0, 100); ax.set_xlabel("%（不詳を除く）"); ax.set_title("通勤時間の分布（2023年）"); ax.legend(frameon=False, ncol=6, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12))
save(fig, "a398_distribution_2023.png", SRC, y=-0.1)

fig, ax = plt.subplots(figsize=(9, 4.4))
x = np.arange(len(T)); a = [g.loc[(t, 1988), "median_calc"] for t in T]; c = [g.loc[(t, 2023), "median_calc"] for t in T]
ax.bar(x - 0.2, a, 0.4, color=LIGHT, label="1988年"); ax.bar(x + 0.2, c, 0.4, color=BLUE, label="2023年")
for i in range(len(T)):
    ax.text(i - 0.2, a[i] + 0.5, f"{a[i]:.1f}", ha="center", fontsize=9); ax.text(i + 0.2, c[i] + 0.5, f"{c[i]:.1f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(T, fontsize=9); ax.set_ylabel("通勤時間の中央値（分、区分から計算）"); ax.set_title("通勤時間の中央値：1988年と2023年"); ax.legend(frameon=False)
save(fig, "a398_median.png", SRC)
print(json.dumps(res, ensure_ascii=False))
