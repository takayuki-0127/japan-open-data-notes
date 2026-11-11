"""274 季節の山がいちばん大きい業種はどこか（鉱工業指数の季節指数）"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, setup_font

setup_font()
d = pd.read_csv(DATA / "prod_seasonal_2018_2026.csv", dtype={"code": str})
d = d[d.ym <= 202512].copy(); d["y"] = d.ym // 100; d["m"] = d.ym % 100
name = d.drop_duplicates("code").set_index("code").name
IND = [c for c in name.index if c not in ("1000000000", "1100000000", "1200000000")]
sf = d[d.kind == "prod_sf"]
g = sf.groupby(["code", "m"]).value.mean().unstack()   # 2018〜2025年の月ごとの平均の季節指数
amp = (g.max(1) - g.min(1))
tab = pd.DataFrame({"name": name[g.index], "weight": d.drop_duplicates("code").set_index("code").weight[g.index],
                    "amp": amp.round(1), "peak_m": g.idxmax(1), "trough_m": g.idxmin(1), "sd": g.std(1, ddof=0).round(1),
                    "mar": g[3].round(1), "aug": g[8].round(1), "dec": g[12].round(1), "jan": g[1].round(1)}).sort_values("amp", ascending=False)
tab.to_csv(RES / "a274_amplitude_by_industry.csv")
g.round(2).to_csv(RES / "a274_seasonal_factor_by_month.csv")
ay = sf.groupby(["code", "y"]).value.agg(lambda v: v.max() - v.min()).unstack()
ay.round(1).to_csv(RES / "a274_amplitude_by_year.csv")
# 原指数の前月比の揺れのうち、季節で説明できる分
r = d[d.kind.isin(["prod_nsa", "prod_sa"])].pivot_table(index=["code", "ym"], columns="kind", values="value").reset_index()
share = {}
for c in list(g.index):
    x = r[r.code == c].sort_values("ym")
    dn = np.log(x.prod_nsa).diff(); ds = np.log(x.prod_sa).diff(); dsf = dn - ds
    share[c] = round(float(1 - ds.var() / dn.var()) * 100, 1)
tab["share_mom_var_seasonal_pct"] = pd.Series(share)
tab.to_csv(RES / "a274_amplitude_by_industry.csv")
# 頑健性：コロナ前（2018〜2019年）だけ／2023〜2025年だけで振れ幅の順位を比べる
def amp_of(years):
    gg = sf[sf.y.isin(years)].groupby(["code", "m"]).value.mean().unstack(); return gg.max(1) - gg.min(1)
a1, a2 = amp_of([2018, 2019]), amp_of([2023, 2024, 2025])
rank_corr = float(pd.Series(a1[IND]).rank().corr(pd.Series(a2[IND]).rank()))
# 頑健性：季節指数そのものではなく 原指数÷季節調整済指数 で計算
g2 = r.assign(f=r.prod_nsa / r.prod_sa * 100, m=r.ym % 100).groupby(["code", "m"]).f.mean().unstack()
amp2 = g2.max(1) - g2.min(1)
top3 = list(tab[tab.index.isin(IND)].index[:3])
main = {"period": "2018-01..2025-12", "n_industries": len(IND), "table": tab.reset_index().to_dict("records"),
        "total_amp": round(float(amp["1000000000"]), 1), "mfg_amp": round(float(amp["1100000000"]), 1),
        "rank_corr_2018_19_vs_2023_25": round(rank_corr, 2), "top3": [name[c] for c in top3],
        "top3_amp_2018_19": [round(float(a1[c]), 1) for c in top3], "top3_amp_2023_25": [round(float(a2[c]), 1) for c in top3],
        "max_abs_diff_amp_sf_vs_ratio": round(float((amp - amp2[amp.index]).abs().max()), 2),
        "march_peak_count": int((tab[tab.index.isin(IND)].peak_m == 3).sum()), "aug_trough_count": int((tab[tab.index.isin(IND)].trough_m == 8).sum()),
        "may_trough_count": int((tab[tab.index.isin(IND)].trough_m == 5).sum())}
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)

short = lambda s: "鉱工業全体" if s == "鉱工業" else s.replace("工業", "").replace("・紙加工品", "")
# 図1：振れ幅の棒
t = tab[tab.index.isin(IND)].sort_values("amp")
fig, ax = plt.subplots(figsize=(8, 5.4))
cols = ["#d1495b" if v in top3 else "#8a8a8a" for v in t.index]
ax.barh([short(n) for n in t.name], t.amp, color=cols)
for i, (v, p, q) in enumerate(zip(t.amp, t.peak_m, t.trough_m)):
    ax.text(v + 0.4, i, f"{v:.0f}（山{p}月・谷{q}月）", va="center", fontsize=8)
ax.axvline(amp["1000000000"], color="#333", ls="--", lw=1); ax.text(amp["1000000000"] + 0.3, -0.9, f"鉱工業全体 {amp['1000000000']:.0f}", fontsize=8)
ax.set_xlabel("季節指数の山と谷の差（ポイント、2018〜2025年の月ごとの平均）"); ax.set_xlim(0, t.amp.max() * 1.35)
ax.set_title("季節の山と谷の差が大きい業種", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "a274_amplitude.png", dpi=150); plt.close()

# 図2：月ごとの季節指数（上位3業種＋石油・食料品＋鉱工業）
fig, ax = plt.subplots(figsize=(8.5, 4.6))
show = top3 + ["1111000000", "1114000000", "1000000000"]
colors = ["#d1495b", "#e07a5f", "#f2a541", "#2e86ab", "#5b8e7d", "#333333"]
for c, col in zip(show, colors):
    ax.plot(range(1, 13), g.loc[c].values, marker="o", ms=3.5, color=col, lw=2 if c == "1000000000" else 1.5, label=short(name[c]))
ax.axhline(100, color="#bbb", lw=0.8); ax.set_xticks(range(1, 13)); ax.set_xticklabels([f"{m}月" for m in range(1, 13)])
ax.set_ylabel("季節指数（年平均がほぼ100）"); ax.set_title("機械は3月に山、石油・食料品は12月に山", fontsize=11)
ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper center")
fig.tight_layout(); fig.savefig(FIG / "a274_monthly.png", dpi=150); plt.close()

# 図3：年ごとの振れ幅（上位3業種と、いちばん小さい2業種）
fig, ax = plt.subplots(figsize=(8, 4.2))
low2 = list(tab[tab.index.isin(IND)].index[-2:])
for c, col in zip(top3 + low2, colors[:3] + ["#2e86ab", "#5b8e7d"]):
    ax.plot(ay.columns, ay.loc[c].values, marker="o", ms=3.5, color=col, label=short(name[c]))
ax.set_ylabel("その年の季節指数の山と谷の差（ポイント）"); ax.set_ylim(0, ay.loc[top3 + low2].values.max() * 1.2)
ax.set_title("年ごとに見ても、振れ幅の大きい業種の順番はほぼ同じ", fontsize=11); ax.legend(frameon=False, fontsize=8, ncol=3)
fig.tight_layout(); fig.savefig(FIG / "a274_by_year.png", dpi=150); plt.close()
print(tab.to_string()); print({k: v for k, v in main.items() if k != "table"})
