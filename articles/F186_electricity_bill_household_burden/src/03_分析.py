"""電気代の値上がりを「単価」と「使用量」に分け、世帯の区分ごとの負担を比べる。

- 年次：電気代 = 1kWh あたりの単価 × 購入数量(kWh) を対数平均で分解（LMDI）
- 補助：国の値引き単価（使用月）× 推計した月別 kWh で、補助がなかった場合の電気代を作る
- 月次：電気代の支出を消費者物価指数（電気代）で割り、使用量の目安を作る
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

B = Path(__file__).resolve().parents[1]
D, RES = B / "data", B / "results"
RES.mkdir(exist_ok=True)

nat = pd.read_csv(D / "annual_national.csv")
grp = pd.read_csv(D / "annual_groups_tidy.csv")
mon = pd.read_csv(D / "monthly_national.csv")
hh = pd.read_csv(D / "annual_households.csv")
sub = pd.read_csv(D / "raw" / "subsidy_rates.csv")
out = {}


def lmdi(s0, s1, p0, p1, q0, q1):
    """支出の差 s1-s0 を、単価と数量の寄与（円）に分ける。"""
    w = (s1 - s0) / (np.log(s1) - np.log(s0)) if s1 != s0 else s0
    return w * np.log(p1 / p0), w * np.log(q1 / q0)


# ---------- 1. 補助の推計（支払月ベース） ----------
mon["kwh_proxy"] = mon.elec_spend / mon.cpi_elec
mon["year"] = mon.month.str[:4].astype(int)
rate = dict(zip(sub.usage_month, sub.yen_per_kwh))
# 家計調査は支払ベース：支払月 t の電気代はおおむね前月 t-1 の使用分
prev = pd.PeriodIndex(mon.month, freq="M") - 1
mon["sub_rate_paid"] = [rate.get(str(p), 0.0) for p in prev]
# 月別 kWh の推計：年間 kWh を、電気代÷物価指数 の月別の形で割り振る
natk = dict(zip(nat.year, nat.kwh))
mon["kwh_est"] = np.nan
for y, d in mon.dropna(subset=["elec_spend"]).groupby("year"):
    if y in natk:
        mon.loc[d.index, "kwh_est"] = d.kwh_proxy / d.kwh_proxy.sum() * natk[y]
mon["subsidy_yen"] = mon.sub_rate_paid * mon.kwh_est
subs = mon.groupby("year").agg(subsidy=("subsidy_yen", "sum"), kwh=("kwh_est", "sum"))
subs["rate_per_kwh"] = subs.subsidy / subs.kwh  # 年間の kWh あたり平均値引き
out["subsidy_by_year"] = {int(y): {"yen": round(r.subsidy), "yen_per_kwh_avg": round(r.rate_per_kwh, 3)}
                          for y, r in subs.iterrows() if r.subsidy > 0}
# 季節の形を変えた頑健性：月別 kWh を均等割にした場合
alt = {}
for y in [2023, 2024, 2025]:
    d = mon[mon.year == y]
    alt[y] = round(float((d.sub_rate_paid * natk[y] / 12).sum()))
out["subsidy_flat_profile"] = alt
sub_rate = subs.rate_per_kwh.to_dict()

# ---------- 2. 全国の年次分解 ----------
nat["elec_nosub"] = nat.elec + nat.year.map(lambda y: sub_rate.get(y, 0.0)) * nat.kwh
nat["p_nosub"] = nat.elec_nosub / nat.kwh
rows = []
for base in [2019, 2021]:
    b = nat[nat.year == base].iloc[0]
    for y in range(base + 1, 2026):
        r = nat[nat.year == y].iloc[0]
        for kind, s0, s1, p0, p1 in [("記録どおり", b.elec, r.elec, b.yen_per_kwh, r.yen_per_kwh),
                                     ("補助を足し戻す", b.elec_nosub, r.elec_nosub, b.p_nosub, r.p_nosub)]:
            pe, qe = lmdi(s0, s1, p0, p1, b.kwh, r.kwh)
            rows.append(dict(base=base, year=y, kind=kind, d_spend=s1 - s0, price_eff=pe, qty_eff=qe,
                             p_change=p1 / p0 - 1, q_change=r.kwh / b.kwh - 1))
decomp = pd.DataFrame(rows)
decomp.to_csv(RES / "national_decomposition.csv", index=False)
out["national_2021_2025"] = decomp[(decomp.base == 2021) & (decomp.year == 2025)].round(4).to_dict("records")
out["national_2021_2023"] = decomp[(decomp.base == 2021) & (decomp.year == 2023)].round(4).to_dict("records")
out["national_2019_2025"] = decomp[(decomp.base == 2019) & (decomp.year == 2025)].round(4).to_dict("records")
out["national_levels"] = nat[nat.year >= 2015].round(3).to_dict("records")

# ---------- 3. 月次：単価（物価指数）と使用量の目安 ----------
m = mon.dropna(subset=["elec_spend"]).copy()
m["mm"] = m.month.str[5:]
base21 = m[m.year == 2021].set_index("mm")
m["d_ln_spend"] = np.log(m.elec_spend / m.mm.map(base21.elec_spend))
m["d_ln_price"] = np.log(m.cpi_elec / m.mm.map(base21.cpi_elec))
m["d_ln_qty"] = m.d_ln_spend - m.d_ln_price
m.to_csv(RES / "monthly_vs2021.csv", index=False)
ann = m[m.year >= 2022].groupby("year")[["d_ln_spend", "d_ln_price", "d_ln_qty"]].mean()
out["monthly_mean_vs2021"] = ann.round(4).to_dict("index")
# 物価指数の電気代：補助が始まる前のピーク（2023年1月）と最新
out["cpi_elec"] = {"2021avg": round(m[m.year == 2021].cpi_elec.mean(), 1),
                   "peak": m.loc[m.cpi_elec.idxmax(), ["month", "cpi_elec"]].tolist(),
                   "latest": mon.iloc[-1][["month", "cpi_elec"]].tolist()}
# 電気代の物価指数と、家計調査の kWh 単価（年次）の動きの一致
cpi_y = mon.groupby("year").cpi_elec.mean()
cmp_ = nat[nat.year.between(2015, 2025)].set_index("year")
r_cpi = np.corrcoef(np.log(cpi_y.loc[2015:2025]).diff().dropna(), np.log(cmp_.yen_per_kwh).diff().dropna())[0, 1]
out["corr_dlog_cpi_vs_unitprice"] = round(float(r_cpi), 3)

# ---------- 4. 世帯の区分ごとの負担 ----------
grp["sub_yen"] = grp.year.map(lambda y: sub_rate.get(y, 0.0)) * grp.kwh
grp["elec_nosub"] = grp.elec + grp.sub_yen
rows = []
for (tab, gname), d in grp.groupby(["tab", "group"]):
    d = d.set_index("year")
    lab = d.label.iloc[0]
    for b0, y1 in [(2021, 2025), (2021, 2023), (2020, 2025), (2021, 2024)]:
        a, z = d.loc[b0], d.loc[y1]
        for kind, s0, s1 in [("記録どおり", a.elec, z.elec), ("補助を足し戻す", a.elec_nosub, z.elec_nosub)]:
            p0, p1 = s0 / a.kwh, s1 / z.kwh
            pe, qe = lmdi(s0, s1, p0, p1, a.kwh, z.kwh)
            rows.append(dict(tab=tab, group=gname, label=lab, base=b0, year=y1, kind=kind,
                             elec0=s0, elec1=s1, d_yen=s1 - s0, d_pct=s1 / s0 - 1,
                             price_eff=pe, qty_eff=qe, p0=p0, p1=p1, p_change=p1 / p0 - 1,
                             kwh0=a.kwh, kwh1=z.kwh, q_change=z.kwh / a.kwh - 1,
                             share0=s0 / a.cons, share1=s1 / z.cons, d_share_pt=(s1 / z.cons - s0 / a.cons) * 100,
                             cons_change=z.cons / a.cons - 1))
gd = pd.DataFrame(rows)
gd.to_csv(RES / "group_decomposition.csv", index=False)
main = gd[(gd.base == 2021) & (gd.year == 2025) & (gd.kind == "記録どおり")]
out["groups_2021_2025"] = main[["tab", "label", "elec0", "elec1", "d_yen", "d_pct", "price_eff", "qty_eff",
                                "p0", "p1", "p_change", "q_change", "share0", "share1", "d_share_pt",
                                "cons_change"]].round(4).to_dict("records")

# 単価の差：区分の間で、1kWh あたりの単価はどれだけ違うか（2021・2025）
spread = {}
for tab in ["q5", "age", "city", "reg"]:
    d = grp[(grp.tab == tab) & (~grp.group.isin(["avg", "nat"])) & grp.year.isin([2021, 2025])]
    spread[tab] = {int(y): [round(float(x.yen_per_kwh.min()), 2), round(float(x.yen_per_kwh.max()), 2)]
                   for y, x in d.groupby("year")}
out["unitprice_range"] = spread

# ---------- 5. 頑健性：区分のとり方・期間・補助の扱いで「負担率の上がり幅が大きい区分」は変わるか ----------
rob = []
for tab in ["q5", "age", "city", "reg"]:
    for (b0, y1), kind in [(x, k) for x in [(2021, 2025), (2021, 2023), (2020, 2025), (2021, 2024)]
                           for k in ["記録どおり", "補助を足し戻す"]]:
        d = gd[(gd.tab == tab) & (gd.base == b0) & (gd.year == y1) & (gd.kind == kind) & (~gd.group.isin(["avg", "nat"]))]
        top_share = d.loc[d.d_share_pt.idxmax(), "label"]
        top_yen = d.loc[d.d_yen.idxmax(), "label"]
        low_yen = d.loc[d.d_yen.idxmin(), "label"]
        # 単価の寄与が大半か：単価の寄与 / 支出の差
        pshare = (d.price_eff / d.d_yen).median()
        rob.append(dict(tab=tab, period=f"{b0}→{y1}", kind=kind, top_share_rise=top_share,
                        max_d_share_pt=round(d.d_share_pt.max(), 3), min_d_share_pt=round(d.d_share_pt.min(), 3),
                        top_yen=top_yen, low_yen=low_yen, price_share_median=round(float(pshare), 3)))
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness_groups.csv", index=False)
out["robustness"] = rob.to_dict("records")

# 収入五分位：第Ⅰと第Ⅴの比較（負担率の差の変化）
q = gd[(gd.tab == "q5") & (gd.kind == "記録どおり")]
qq = {}
for (b0, y1), d in q.groupby(["base", "year"]):
    d = d.set_index("group")
    qq[f"{b0}→{y1}"] = {"Q1_d_share_pt": round(d.loc["Q1", "d_share_pt"], 3), "Q5_d_share_pt": round(d.loc["Q5", "d_share_pt"], 3),
                        "Q1_d_yen": round(d.loc["Q1", "d_yen"]), "Q5_d_yen": round(d.loc["Q5", "d_yen"]),
                        "Q1_share1": round(d.loc["Q1", "share1"] * 100, 2), "Q5_share1": round(d.loc["Q5", "share1"] * 100, 2)}
out["q1_vs_q5"] = qq

# ---------- 6. 単身世帯との比較（金額だけ） ----------
hp = hh.pivot(index="year", columns="type", values="elec")
hc = hh.pivot(index="year", columns="type", values="cons")
o = {}
for t in hp.columns:
    o[t] = {"2021": hp.loc[2021, t], "2025": hp.loc[2025, t], "d_pct": round(hp.loc[2025, t] / hp.loc[2021, t] - 1, 4),
            "share2021": round(hp.loc[2021, t] / hc.loc[2021, t] * 100, 2), "share2025": round(hp.loc[2025, t] / hc.loc[2025, t] * 100, 2)}
out["household_types"] = o

# ---------- 7. 実質（総合の物価で割る） ----------
cpi_tot_y = mon.groupby("year").cpi_total.mean()
r0 = nat.set_index("year")
out["real_2021_2025"] = {"nominal_pct": round(r0.loc[2025, "elec"] / r0.loc[2021, "elec"] - 1, 4),
                         "real_pct": round((r0.loc[2025, "elec"] / cpi_tot_y[2025]) / (r0.loc[2021, "elec"] / cpi_tot_y[2021]) - 1, 4),
                         "cpi_total_pct": round(cpi_tot_y[2025] / cpi_tot_y[2021] - 1, 4)}

json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: out[k] for k in ["subsidy_by_year", "subsidy_flat_profile", "national_2021_2025", "national_2019_2025",
                                      "monthly_mean_vs2021", "cpi_elec", "corr_dlog_cpi_vs_unitprice", "q1_vs_q5",
                                      "household_types", "real_2021_2025", "unitprice_range"]},
                 ensure_ascii=False, indent=0, default=float))
