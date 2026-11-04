import json, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    try: fm.fontManager.addfont(f)
    except Exception: pass
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
C1, C2, C3, G = "#2b6cb0", "#dd6b20", "#2f855a", "#718096"
nat = pd.read_csv("data/national.csv").set_index("year"); pr = pd.read_csv("results/pref_change_points.csv").set_index("pref")
kr = pd.read_csv("results/kei_by_pref.csv").set_index("pref"); pp = pd.read_csv("data/pref_panel.csv")
pr["dens_g"] = pd.qcut(pr.density_hab, 3, labels=["人口密度 低", "中", "高"])
cols = {"人口密度 低": C3, "中": C2, "高": C1}

# 1 全国
fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
ax[0].plot(nat.index, nat.rate, color=C1, lw=2); ax[0].axvline(2006, color=G, ls=":"); ax[0].annotate("2006年 1.112台（最高）", (2006, 1.112), (1983, 1.08), arrowprops=dict(arrowstyle="->", color=G))
ax[0].annotate("2026年 1.001台", (2026, 1.001), (2010, 0.9), arrowprops=dict(arrowstyle="->", color=G))
ax[0].set_title("自家用乗用車の世帯当たり台数（全国、各年3月末）"); ax[0].set_ylabel("台／世帯")
idx = nat.loc[2000:] / nat.loc[2006]
ax[1].plot(idx.index, 100 * idx.cars, color=C2, lw=2, label="自家用乗用車の台数"); ax[1].plot(idx.index, 100 * idx.hh, color=C3, lw=2, label="世帯数")
ax[1].plot(idx.index, 100 * idx.rate, color=C1, lw=2, ls="--", label="世帯当たり台数")
ax[1].axvline(2014, color=G, ls=":"); ax[1].text(2014.3, 92, "2014年から世帯数に\n外国人世帯を含む", fontsize=9, color=G)
ax[1].set_title("2006年＝100：台数は増え続け、世帯数が上回った"); ax[1].legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig("figures/f183_1_national.png", dpi=150); plt.close(fig)

# 2 変化点の分布
fig, ax = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
yrs = np.arange(2005, 2027)
for a, col, ttl in zip(ax, ["peak_rate_year", "hinge_tau", "peak_cars_year"], ["世帯当たり台数が最も高かった年", "折れ線の当てはめで減りはじめた年", "台数そのものが最も多かった年"]):
    bottom = np.zeros(len(yrs))
    for g in ["人口密度 低", "中", "高"]:
        c = pr[pr.dens_g == g][col].value_counts().reindex(yrs, fill_value=0).values
        a.bar(yrs, c, bottom=bottom, color=cols[g], label=g, width=0.8); bottom += c
    a.set_title(ttl, fontsize=11); a.set_xticks([2005, 2010, 2015, 2020, 2025])
ax[0].set_ylabel("都道府県の数"); ax[0].legend(frameon=False, fontsize=9)
ax[0].text(2005, -3.2, "※2005年は集計の最初の年（それ以前に最高だった可能性）", fontsize=8, color=G)
ax[2].text(2007.5, 16, "2026年＝まだ増えている →", fontsize=9, color=G)
fig.suptitle("「減りはじめた年」は、何で測るかで大きく違う（47都道府県）", fontsize=12); fig.tight_layout(); fig.savefig("figures/f183_2_change_points.png", dpi=150); plt.close(fig)

# 3 分解
fig, ax = plt.subplots(figsize=(6.6, 5.4))
for g in ["人口密度 低", "中", "高"]:
    d = pr[pr.dens_g == g]; ax.scatter(100 * d.dlog_hh_16_26, 100 * d.dlog_cars_16_26, color=cols[g], s=40, label=g, alpha=.85)
x = np.linspace(-3, 16, 10); ax.plot(x, x, color=G, ls="--", lw=1); ax.text(10.5, 11.8, "この線より下＝世帯当たりは減る", color=G, fontsize=9)
ax.axhline(0, color=G, lw=.8); ax.axvline(0, color=G, lw=.8)
ax.set_xlabel("世帯数の増え方（2016→2026年、%）"); ax.set_ylabel("自家用乗用車の台数の増え方（%）")
ax.set_title("世帯当たりの減少は、台数の減少より世帯の増加で起きた", fontsize=11); ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig("figures/f183_3_decomposition.png", dpi=150); plt.close(fig)

# 4 鉄道・高齢化との関係
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
ax[0].scatter(pr.rail_per1000, pr.peak_rate_year, color=C1, s=35, alpha=.8); ax[0].set_xscale("log")
ax[0].set_xlabel("鉄道の乗降客数（人口千人あたり・1日、対数）"); ax[0].set_ylabel("世帯当たり台数が最も高かった年"); ax[0].set_title("鉄道が多い県ほど早く頭打ち（順位相関 −0.81）", fontsize=11)
ax[1].scatter(100 * pr.share65, 100 * pr.dlog_hh_16_26, color=C2, s=35, alpha=.8)
ax[1].set_xlabel("65歳以上の割合（2024年、%）"); ax[1].set_ylabel("世帯数の増え方（2016→2026年、%）"); ax[1].set_title("ただし鉄道・人口密度・高齢化はほぼ重なっている", fontsize=11)
fig.tight_layout(); fig.savefig("figures/f183_4_rail_aging.png", dpi=150); plt.close(fig)

# 5 分母・車種の頑健性
s = pd.DataFrame({"世帯当たり\n（2016→26）": 100 * pr.dlog_rate_16_26, "台数そのもの\n（2016→26）": 100 * pr.dlog_cars_16_26,
                  "人口当たり\n（2013→24）": 100 * pr.dlog_cpc_13_24, "軽四輪の世帯当たり\n（2015→25、12月末）": 100 * np.log(kr.kei2025 / kr.kei2015).reindex(pr.index)})
s["g"] = pr.dens_g; m = s.groupby("g", observed=True).median().T
fig, ax = plt.subplots(figsize=(10, 4.3)); w = .26; xs = np.arange(len(m))
for i, g in enumerate(["人口密度 低", "中", "高"]): ax.bar(xs + (i - 1) * w, m[g], w, color=cols[g], label=g)
ax.axhline(0, color=G, lw=.8); ax.set_xticks(xs); ax.set_xticklabels(m.index); ax.set_ylabel("変化（%、中央値）")
ax.set_title("分母と車種を変えると「減っている」は消える（人口密度の3グループ）", fontsize=11); ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig("figures/f183_5_denominator.png", dpi=150); plt.close(fig)
print("ok")
