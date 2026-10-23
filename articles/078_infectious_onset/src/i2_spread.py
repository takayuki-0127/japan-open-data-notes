"""流行はどこから始まるか（都道府県ごとの立ち上がりの週）と、全数把握疾患（百日咳・梅毒・劇症型溶連菌・麻しん）の年間の報告数"""
import numpy as np, pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import *

t = load_teiten(); z = load_zensu(); pop = population()
pf = t[t.pref.isin(PREFS)].copy()
lat = pd.Series({p: CAP[p][0] for p in PREFS}); lon = pd.Series({p: CAP[p][1] for p in PREFS})
TOKYO = CAP["東京都"]
dist = pd.Series({p: 6371 * 2 * np.arcsin(np.sqrt(np.sin(np.radians(CAP[p][0] - TOKYO[0]) / 2) ** 2 + np.cos(np.radians(TOKYO[0])) * np.cos(np.radians(CAP[p][0])) * np.sin(np.radians(CAP[p][1] - TOKYO[1]) / 2) ** 2)) for p in PREFS})


def onset(d, season_start_year, thr, season=True):
    x = pf[pf.disease == d].copy()
    if season:
        x = x[((x.year == season_start_year) & (x.week >= 36)) | ((x.year == season_start_year + 1) & (x.week <= 35))]
    else:
        x = x[x.year == season_start_year]
    x = x.sort_values("start")
    first = x.start.min()
    o = {}
    for p, g in x.groupby("pref"):
        h = g[g.per >= thr]
        o[p] = (h.start.iloc[0] - first).days / 7 if len(h) else np.nan
    return pd.Series(o).loc[PREFS]


cases = [("インフルエンザ", 2023, 10, True, "2023/24"), ("インフルエンザ", 2024, 10, True, "2024/25"), ("インフルエンザ", 2025, 10, True, "2025/26"),
         ("インフルエンザ", 2024, 1, True, "2024/25"), ("インフルエンザ", 2025, 1, True, "2025/26"),
         ("手足口病", 2024, 2, False, "2024"), ("手足口病", 2026, 2, False, "2026")]
O = {}
rows = []
for d, y, thr, s, lab in cases:
    o = onset(d, y, thr, s); key = f"{SHORT[d]}_{lab}_{thr}"
    O[key] = o
    ok = o.dropna()
    r_lat = stats.spearmanr(ok, lat[ok.index]); r_dist = stats.spearmanr(ok, dist[ok.index])
    first5 = ok.sort_values().head(5)
    okx = ok.drop("沖縄県", errors="ignore"); r_lat2 = stats.spearmanr(okx, lat[okx.index])
    rows.append({"series": key, "n_crossed": len(ok), "spread_weeks": ok.max() - ok.min(), "median_week": ok.median(),
                 "rho_latitude": r_lat.statistic, "p_latitude": r_lat.pvalue, "rho_lat_ex_okinawa": r_lat2.statistic, "p_lat_ex_okinawa": r_lat2.pvalue, "n_at_week0": int((ok == 0).sum()), "rho_dist_tokyo": r_dist.statistic, "p_dist_tokyo": r_dist.pvalue,
                 "earliest5": "、".join(f"{p}({int(w)})" for p, w in first5.items()), "okinawa_rank": int(ok.rank(method="min").get("沖縄県", np.nan)) if "沖縄県" in ok else None,
                 "tokyo_rank": int(ok.rank(method="min").get("東京都", np.nan)) if "東京都" in ok else None})
R = pd.DataFrame(rows); R.to_csv(RES / "i2_onset_summary.csv", index=False, encoding="utf-8-sig"); print(R.to_string())
OD = pd.DataFrame(O); OD.index.name = "pref"; OD.to_csv(RES / "i2_onset_weeks.csv", encoding="utf-8-sig")
# シーズン間の順位の相関（インフル 注意報レベル10）
k = [c for c in OD.columns if c.startswith("インフルエンザ") and c.endswith("_10")]
C = OD[k].corr(method="spearman").round(2); C.to_csv(RES / "i2_onset_rank_corr.csv", encoding="utf-8-sig"); print(C)

# 全数把握：年間の報告数（その年の最終週の累積）
DZ = ["百日咳", "梅毒", "劇症型溶血性レンサ球菌感染症", "麻しん"]
zz = z[z.disease.isin(DZ)]
ann = zz[zz.pref == "総数"].sort_values("week").groupby(["disease", "year"]).cum.last().unstack()
w41 = zz[(zz.pref == "総数") & (zz.week == 41)].pivot(index="disease", columns="year", values="cum")
A = ann.join(w41.add_prefix("w41_")); A.to_csv(RES / "i2_zensu_annual.csv", encoding="utf-8-sig"); print(A)
# 2025年の都道府県別（人口10万人あたり）
p25 = zz[(zz.year == 2025) & (zz.pref.isin(PREFS))].sort_values("week").groupby(["disease", "pref"]).cum.last().unstack(0)
rate = (p25.div(pop, axis=0) * 1e5).round(2)
rate.to_csv(RES / "i2_zensu_2025_per100k.csv", encoding="utf-8-sig")
print(rate.sort_values("百日咳", ascending=False).head(5)); print(rate.sort_values("梅毒", ascending=False).head(5))

# 図1：インフルの立ち上がり週（注意報レベル）×緯度
fig, axes = plt.subplots(1, 3, figsize=(12, 4.1), sharey=True)
for ax, lab in zip(axes, ["2023/24", "2024/25", "2025/26"]):
    o = OD[f"インフルエンザ_{lab}_10"]; ok = o.dropna()
    ax.scatter(ok, lat[ok.index], s=18, color=BLUE)
    for p in ["沖縄県", "東京都", "北海道", "大阪府", "福岡県"]:
        if p in ok: ax.annotate(p.replace("県", "").replace("都", "").replace("府", ""), (ok[p], lat[p]), fontsize=8, xytext=(3, 2), textcoords="offset points")
    r = R[R.series == f"インフルエンザ_{lab}_10"].iloc[0]
    ax.set_title(f"{lab}（ρ={r.rho_latitude:.2f}）", loc="left", fontsize=11)
    ax.set_xlabel("第36週から何週目に定点当たり10を超えたか")
axes[0].set_ylabel("県庁所在地の緯度（度）")
fig.suptitle("インフルエンザが注意報レベル（定点当たり10）に達した週と緯度（都道府県）", x=.02, ha="left", y=1.02, fontsize=12)
note(axes[0], SOURCE + "　ρはスピアマンの順位相関。超えなかった県は除外", -0.2)
fig.savefig(FIG / "i2_flu_onset.png"); plt.close(fig)

# 図2：手足口病（夏）の立ち上がり週×緯度
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.1), sharey=True)
for ax, lab in zip(axes, ["2024", "2026"]):
    o = OD[f"手足口病_{lab}_2"]; ok = o.dropna()
    wk = ok + 1  # 第1週からの週番号
    ax.scatter(wk, lat[ok.index], s=18, color=ORANGE)
    for p in ["沖縄県", "東京都", "北海道", "大阪府", "福岡県", "宮崎県"]:
        if p in ok: ax.annotate(p.replace("県", "").replace("都", "").replace("府", ""), (wk[p], lat[p]), fontsize=8, xytext=(3, 2), textcoords="offset points")
    r = R[R.series == f"手足口病_{lab}_2"].iloc[0]
    ax.set_title(f"{lab}年（ρ={r.rho_latitude:.2f}）", loc="left", fontsize=11)
    ax.set_xlabel("定点当たり2を初めて超えた週（第何週）")
axes[0].set_ylabel("県庁所在地の緯度（度）")
fig.suptitle("手足口病が定点当たり2に達した週と緯度（流行が大きかった2024年と2026年）", x=.02, ha="left", y=1.02, fontsize=12)
note(axes[0], SOURCE + "　ρはスピアマンの順位相関", -0.2)
fig.savefig(FIG / "i2_hfmd_onset.png"); plt.close(fig)

# 図3：全数把握の年間報告数
fig, axes = plt.subplots(1, 4, figsize=(12, 3.6))
for ax, d in zip(axes, DZ):
    v = ann.loc[d]
    ax.bar([2023, 2024, 2025], v[[2023, 2024, 2025]], color=BLUE)
    ax.bar([2026], v[2026], color=LIGHT)
    for yy in [2023, 2024, 2025, 2026]: ax.text(yy, v[yy], f"{int(v[yy]):,}", ha="center", va="bottom", fontsize=8)
    ax.set_title({"劇症型溶血性レンサ球菌感染症": "劇症型溶連菌感染症"}.get(d, d), loc="left", fontsize=11)
    ax.set_xticks([2023, 2024, 2025, 2026]); ax.set_xticklabels(["2023", "2024", "2025", "2026\n(41週まで)"], fontsize=8)
    ax.set_ylim(0, v.max() * 1.18)
axes[0].set_ylabel("年間の報告数（速報の累積）")
fig.suptitle("全数把握の4疾患の年間報告数", x=.02, ha="left", y=1.03, fontsize=12)
note(axes[0], SOURCE + "　各年の最終週の累積（速報値）。2026年は第41週まで", -0.22)
fig.tight_layout(); fig.savefig(FIG / "i2_zensu.png"); plt.close(fig)
