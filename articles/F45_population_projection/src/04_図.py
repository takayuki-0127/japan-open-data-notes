"""F45 の図を作る（figures/ に PNG で出力）。"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, AGES

plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10.5, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e6e6", "grid.linewidth": 0.8,
                     "axes.axisbelow": True, "figure.dpi": 150})
BLUE, ORANGE, GRAY, GREEN, RED, PURPLE = "#2a6fb0", "#e08a2c", "#9a9a9a", "#3a9a5b", "#c8463d", "#7b5ea7"
S = json.load(open(RES / "summary.json"))

# ---- 図1 しくみ：全国の人口ピラミッド（2020年の実績と、社人研の2050年）
p = pd.read_csv(DATA / "pop_2023.csv")
A = [f"a{i}" for i in range(20)]
pa = p[(p.kind == "a")]
def nat(y, s):
    return pa[(pa.year == y) & (pa.sex == s)][A].sum().to_numpy() / 1e4
fig = plt.figure(figsize=(10.5, 5.4))
ax = fig.add_axes([0.09, 0.11, 0.56, 0.8])
yy = np.arange(20)
ax.barh(yy, -nat(2020, "M"), color=BLUE, alpha=0.35, label="2020年（国勢調査）")
ax.barh(yy, nat(2020, "F"), color=ORANGE, alpha=0.35)
ax.barh(yy, -nat(2050, "M"), fill=False, edgecolor=BLUE, lw=1.6, label="2050年（社人研の推計）")
ax.barh(yy, nat(2050, "F"), fill=False, edgecolor=ORANGE, lw=1.6)
ax.set_yticks(yy); ax.set_yticklabels(AGES, fontsize=8)
ax.set_xlabel("人口（万人）　← 男　　　女 →")
ax.set_xticks([-500, -250, 0, 250, 500]); ax.set_xticklabels(["500", "250", "0", "250", "500"])
ax.legend(loc="lower right", frameon=False, fontsize=9)
txt = ("5年ごとに、次の3つを順に当てるだけ\n"
       "① 生残率：5歳上の階級へ生き残る割合\n"
       "② 純移動率：転入－転出の割合\n　 （期首の人口あたり）\n"
       "③ 子ども女性比：0～4歳 ÷ 女性20～44歳\n"
       "→ 5歳以上は ①＋② を掛けてずらし、\n　 0～4歳は ③ で作る")
fig.text(0.675, 0.86, txt, va="top", fontsize=9.5, linespacing=1.7,
         bbox=dict(boxstyle="round,pad=0.6", fc="white", ec="#cccccc"))
fig.text(0.68, 0.42, f"全国の人口\n2020年 {pa[pa.year == 2020][A].sum().sum()/1e6:.1f}百万人\n2050年 {pa[pa.year == 2050][A].sum().sum()/1e6:.1f}百万人（社人研）",
         va="top", fontsize=9.5, linespacing=1.6)
ax.set_title("コーホート要因法：年齢の階級を5年ずつずらし、生残・移動・出生を当てる", fontsize=11.5, loc="left")
fig.savefig(FIG / "f45_1_mechanism.png"); plt.close(fig)

# ---- 図2 自作の素朴な推計と社人研：2050年の人口（2020年＝1）
nv = pd.read_csv(RES / "r2_naive_vs_ipss_muni.csv")
size = pd.cut(nv.pop2020, [0, 5000, 20000, 100000, 1e8], labels=["5千人未満", "5千～2万人", "2万～10万人", "10万人以上"])
cols = dict(zip(size.cat.categories, [RED, ORANGE, GREEN, BLUE]))
fig, ax = plt.subplots(figsize=(7.2, 6.2))
for k, c in cols.items():
    g = nv[size == k]
    ax.scatter(g.ipss_ratio, g.naive_ratio, s=7, alpha=0.55, color=c, label=f"{k}（{len(g)}）", lw=0)
lim = [0.15, 1.6]
ax.plot(lim, lim, color="#555555", lw=1)
ax.plot(lim, [x * 1.1 for x in lim], color="#999999", lw=0.8, ls="--")
ax.plot(lim, [x * 0.9 for x in lim], color="#999999", lw=0.8, ls="--")
ax.set_xscale("log"); ax.set_yscale("log")
ticks = [0.2, 0.3, 0.5, 0.7, 1.0, 1.4]
ax.set_xticks(ticks); ax.set_xticklabels([str(t) for t in ticks]); ax.set_yticks(ticks); ax.set_yticklabels([str(t) for t in ticks])
ax.set_xlim(lim); ax.set_ylim(lim)
from matplotlib.ticker import NullFormatter
ax.xaxis.set_minor_formatter(NullFormatter()); ax.yaxis.set_minor_formatter(NullFormatter())
ax.set_xlabel("社人研の推計（2050年 ÷ 2020年）"); ax.set_ylabel("自作の素朴な推計（2050年 ÷ 2020年）")
s2 = S["naive_vs_ipss_muni"]
ax.text(0.02, 0.98, f"{s2['n']:,}市区町村\n相関（対数）{s2['corr_ratio']:.2f}\n±10%以内：{s2['share_within_10pct']*100:.0f}%\n破線は±10%",
        transform=ax.transAxes, va="top", fontsize=9)
ax.legend(loc="lower right", frameon=False, fontsize=8.5, title="2020年の人口", title_fontsize=8.5)
ax.set_title("2015→20年の動きが続くとした自作の推計と、社人研の推計", fontsize=11.5, loc="left")
fig.tight_layout(); fig.savefig(FIG / "f45_2_naive_vs_ipss.png"); plt.close(fig)

# ---- 図3 答え合わせ：2025年国勢調査（市区町村）と、過去の推計（都道府県）
bs = S["bt2025_by_size"]
labs = list(bs.keys())
bt = pd.read_csv(RES / "r3_backtest_2025_muni.csv")
both = bt[bt.err_naive.notna()]
flat = [float(np.abs(g.err_flat).mean() * 100) for _, g in both.groupby(pd.Categorical(both["size"], categories=labs), observed=True)]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw=dict(width_ratios=[1.35, 1]))
ax = axes[0]
x = np.arange(len(labs)); w = 0.27
v1 = [bs[k]["ipss"]["mape"] for k in labs]; v2 = [bs[k]["naive"]["mape"] for k in labs]
ax.bar(x - w, v1, w, color=BLUE, label="社人研（2023年推計）")
ax.bar(x, v2, w, color=ORANGE, label="自作の素朴な推計")
ax.bar(x + w, flat, w, color=GRAY, label="2020年のまま")
for xi, a, b, c in zip(x, v1, v2, flat):
    ax.text(xi - w, a + 0.15, f"{a:.1f}", ha="center", fontsize=8); ax.text(xi, b + 0.15, f"{b:.1f}", ha="center", fontsize=8)
    ax.text(xi + w, c + 0.15, f"{c:.1f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([f"{k}\n({bs[k]['n']})" for k in labs], fontsize=9)
ax.set_ylabel("2025年の人口の外れ（平均絶対誤差、%）")
ax.legend(frameon=False, fontsize=8.5)
ax.set_title("5年先の答え合わせ（令和7年国勢調査、市区町村）", fontsize=11, loc="left")
ax = axes[1]
bv = S["bt_vintages_pref"]
keys = ["2013年推計_5年先", "2013年推計_10年先", "2013年推計_15年先", "2018年推計_5年先", "2018年推計_10年先", "2023年推計_5年先"]
lab2 = ["2013年推計\n5年先", "2013年推計\n10年先", "2013年推計\n15年先", "2018年推計\n5年先", "2018年推計\n10年先", "2023年推計\n5年先"]
cc = [PURPLE, PURPLE, PURPLE, GREEN, GREEN, BLUE]
ax.bar(range(6), [bv[k]["mape"] for k in keys], color=cc)
for i, k in enumerate(keys):
    ax.text(i, bv[k]["mape"] + 0.04, f"{bv[k]['mape']:.2f}%\n(全国 {bv[k]['japan_err']:+.1f}%)", ha="center", fontsize=7.5)
ax.set_xticks(range(6)); ax.set_xticklabels(lab2, fontsize=8)
ax.set_ylabel("都道府県の人口の外れ（平均絶対誤差、%）")
ax.set_ylim(0, max(bv[k]["mape"] for k in keys) * 1.35)
ax.set_title("過去の社人研の推計（都道府県）", fontsize=11, loc="left")
fig.tight_layout(); fig.savefig(FIG / "f45_3_backtest.png"); plt.close(fig)

# ---- 図4 シナリオ：全国の人口
sc = pd.read_csv(RES / "r4_scenarios.csv")
order = ["自作（2015→20年の動きが続く）", "子ども女性比 +10%", "子ども女性比を2020年のまま", "社人研の仮定", "子ども女性比 −10%", "移動を半分", "移動ゼロ"]
colmap = {"社人研の仮定": "#222222", "移動ゼロ": RED, "移動を半分": "#e38b84", "子ども女性比 +10%": GREEN,
          "子ども女性比 −10%": "#8fc9a2", "子ども女性比を2020年のまま": GRAY, "自作（2015→20年の動きが続く）": ORANGE}
fig, ax = plt.subplots(figsize=(8.6, 5.2))
for nm in order:
    g = sc[sc.scenario == nm]
    ax.plot(g.year, g.japan / 1e6, color=colmap[nm], lw=2.6 if nm == "社人研の仮定" else 1.8,
            ls="--" if "自作" in nm else "-", marker="o", ms=3)
    ax.text(2050.6, g.japan.iloc[-1] / 1e6, f"{nm}  {g.japan.iloc[-1]/1e6:.1f}", va="center", fontsize=8.5, color=colmap[nm])
ax.set_xlim(2019, 2063); ax.set_xticks(range(2020, 2051, 5))
ax.set_ylabel("全国の人口（百万人）")
ax.set_title("2050年の人口は、仮定の置き方でどれだけ変わるか（都道府県の合計）", fontsize=11.5, loc="left")
fig.tight_layout(); fig.savefig(FIG / "f45_4_scenarios.png"); plt.close(fig)

# ---- 図5 外れやすいところ：人口規模と年齢
fx = pd.read_csv(RES / "r5_miss_features.csv")
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw=dict(width_ratios=[1.25, 1]))
ax = axes[0]
ax.scatter(fx.pop2020, fx.err_ipss * 100, s=6, alpha=0.4, color=BLUE, lw=0)
bins = np.logspace(np.log10(fx.pop2020.min()), np.log10(fx.pop2020.max()), 14)
mid, med, q1, q9 = [], [], [], []
for a, b in zip(bins[:-1], bins[1:]):
    g = fx[(fx.pop2020 >= a) & (fx.pop2020 < b)].err_ipss * 100
    if len(g) >= 8:
        mid.append(np.sqrt(a * b)); med.append(g.median()); q1.append(g.quantile(0.1)); q9.append(g.quantile(0.9))
ax.plot(mid, med, color="#222222", lw=2, label="中央値")
ax.fill_between(mid, q1, q9, color=GRAY, alpha=0.25, label="10～90%の範囲")
ax.axhline(0, color="#555555", lw=0.8)
ax.set_xscale("log"); ax.set_ylim(-15, 15)
ax.set_xlabel("2020年の人口（対数目盛）"); ax.set_ylabel("2025年の推計 ÷ 実績 − 1（%）")
ax.legend(frameon=False, fontsize=8.5, loc="upper right")
ax.set_title("小さい町ほど外れの幅が大きい（社人研2023年推計）", fontsize=11, loc="left")
ax = axes[1]
ag = S["bt2025_age_ipss_pct"]
vals = [ag[str(i)] for i in range(20)]
ax.barh(range(20), vals, color=[RED if abs(v) > 2 else BLUE for v in vals])
ax.set_yticks(range(20)); ax.set_yticklabels(AGES, fontsize=7.5)
ax.axvline(0, color="#555555", lw=0.8)
for i, v in enumerate(vals):
    if abs(v) > 2:
        ax.text(v + (0.3 if v > 0 else -0.3), i, f"{v:+.1f}%", va="center", ha="left" if v > 0 else "right", fontsize=8)
ax.set_xlabel("全国の年齢別：2025年の推計 ÷ 実績 − 1（%）")
ax.set_xlim(-8, 16)
ax.set_title("年齢別では、0～4歳と高齢の端が多めに出た", fontsize=11, loc="left")
fig.tight_layout(); fig.savefig(FIG / "f45_5_miss.png"); plt.close(fig)

# ---- 図6 頑健性
rp = S["robust_pref"]; sm = S["robust_small_merged"]; sx = S["robust_sex_combined_muni"]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
ax = axes[0]
labs = ["社人研の仮定", "自作\n（2015→20年）", "自作\n（2010→15年）", "自作\n（男女まとめた\n移動率）"]
vals = [rp["japan2050"]["ipss"], rp["japan2050"]["base1520"], rp["japan2050"]["base1015"], rp["japan2050"]["sex_combined"]]
ax.bar(range(4), np.array(vals) / 1e6, color=["#222222", ORANGE, "#f0b778", "#c9a27a"])
for i, v in enumerate(vals):
    ax.text(i, v / 1e6 + 0.5, f"{v/1e6:.1f}", ha="center", fontsize=9)
ax.set_ylim(90, 115); ax.set_xticks(range(4)); ax.set_xticklabels(labs, fontsize=8.5)
ax.set_ylabel("2050年の全国の人口（百万人）")
ax.set_title("移動率の基準期間で、2050年の全国は700万人変わる", fontsize=11, loc="left")
ax = axes[1]
labs = ["5千人未満の町村\n（1つずつ）", "同じ県の5千人未満を\nまとめた場合"]
x = np.arange(2); w = 0.36
ax.bar(x - w / 2, [sm["individual"]["ipss"]["mape"], sm["merged"]["ipss"]["mape"]], w, color=BLUE, label="社人研（2023年推計）")
ax.bar(x + w / 2, [sm["individual"]["naive"]["mape"], sm["merged"]["naive"]["mape"]], w, color=ORANGE, label="自作の素朴な推計")
for xi, a, b in zip(x, [sm["individual"]["ipss"]["mape"], sm["merged"]["ipss"]["mape"]],
                    [sm["individual"]["naive"]["mape"], sm["merged"]["naive"]["mape"]]):
    ax.text(xi - w / 2, a + 0.08, f"{a:.1f}", ha="center", fontsize=9); ax.text(xi + w / 2, b + 0.08, f"{b:.1f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"{labs[0]}（{sm['individual']['ipss']['n']}）", f"{labs[1]}（{sm['merged']['ipss']['n']}）"], fontsize=8.5)
ax.set_ylabel("2025年の外れ（平均絶対誤差、%）")
ax.legend(frameon=False, fontsize=8.5)
ax.set_title("小さい町村をまとめると、外れは小さくなる", fontsize=11, loc="left")
fig.tight_layout(); fig.savefig(FIG / "f45_6_robustness.png"); plt.close(fig)
print("ok")
