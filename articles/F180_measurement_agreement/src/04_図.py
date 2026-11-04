"""04 図（5枚）"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
B = pathlib.Path(__file__).resolve().parents[1]; D = B / "data"; RS = B / "results"; FG = B / "figures"; FG.mkdir(exist_ok=True)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f: font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
C1, C2, C3, C4, GR = "#2a6f97", "#d1495b", "#edae49", "#66a182", "#9a9a9a"
P = pd.read_csv(D / "pairs_pref.csv"); T = pd.read_csv(RS / "agreement_table.csv"); SZ = pd.read_csv(RS / "muni_by_size.csv")
M = pd.read_csv(D / "pairs_muni.csv", dtype={"code5": str})
EVAC = {"07211", "07212", "07308", "07541", "07542", "07543", "07544", "07545", "07546", "07547", "07548", "07564"}

# 1 人口の Bland–Altman（都道府県、2015・2020）
fig, ax = plt.subplots(figsize=(8, 5.2))
for yr, c, mk in [(2015, GR, "o"), (2020, C1, "o")]:
    g = P[P.year == yr]; d = 100 * np.log(g.juki_pop_total / g.A1101); m = (g.A1101 + g.juki_pop_total) / 2 / 1e4
    ax.scatter(m, d, s=28, color=c, alpha=.85, label=f"{yr}年（国勢調査）と翌1月1日の住基", marker=mk)
    t = T[(T.pair == "pop_total") & (T.year == yr) & (T.unit == "都道府県")].iloc[0]
    for v, ls in [(t.bias, "-"), (t.loa_lo, "--"), (t.loa_hi, "--")]: ax.axhline(v, color=c, ls=ls, lw=1)
ax.axhline(0, color="black", lw=.8)
ax.set_xscale("log"); ax.set_xlabel("2つの統計の平均人口（万人、対数目盛）"); ax.set_ylabel("住基と国勢調査の差（%、対数の差×100）")
ax.set_title("人口：相関は1.00でも、住基が平均0.9〜1.2%多い（実線＝平均のずれ、破線＝一致の限界）", fontsize=11)
ax.legend(frameon=False, fontsize=10); fig.tight_layout(); fig.savefig(FG / "f180_1_population_bland_altman.png", dpi=150); plt.close(fig)

# 2 組ごとの平均のずれと一致の限界（%）
pairs = [("pop_total", "人口（総数）"), ("pop_japanese", "日本人人口"), ("pop15", "15歳以上人口\n（労働力調査）"), ("households", "世帯数"), ("employed", "就業者数\n（労働力調査）"), ("pop_foreign", "外国人人口")]
fig, ax = plt.subplots(figsize=(8, 5.4))
for i, (pid, lab) in enumerate(pairs):
    for k, (yr, c) in enumerate([(2015, GR), (2020, C1)]):
        t = T[(T.pair == pid) & (T.year == yr) & (T.unit == "都道府県")].iloc[0]; yy = i + (k - .5) * .28
        ax.plot([t.loa_lo, t.loa_hi], [yy, yy], color=c, lw=3, alpha=.6); ax.plot(t.bias, yy, "o", color=c, ms=7, label=f"{yr}年" if i == 0 else None)
ax.axvline(0, color="black", lw=.8); ax.set_yticks(range(len(pairs))); ax.set_yticklabels([p[1] for p in pairs]); ax.invert_yaxis()
ax.set_xlabel("もう一方の統計と国勢調査の差（%、対数の差×100）。点＝平均のずれ、線＝47都道府県の95%が入る幅")
ax.set_title("同じ名前の数字でも、ずれの大きさは組ごとに0.9%から21%まで", fontsize=11)
ax.legend(frameon=False, loc="lower right"); fig.tight_layout(); fig.savefig(FG / "f180_2_bias_by_pair.png", dpi=150); plt.close(fig)

# 3 完全失業率：散布図と Bland–Altman
fig, axs = plt.subplots(1, 2, figsize=(9.6, 4.8))
for yr, c in [(2015, GR), (2020, C1)]:
    g = P[P.year == yr]; x, y = g.cen_unemp_rate, g.lfs_unemp_rate
    axs[0].scatter(x, y, s=24, color=c, alpha=.85, label=f"{yr}年")
    b = np.polyfit(x, y, 1); xs = np.linspace(x.min(), x.max(), 10); axs[0].plot(xs, np.polyval(b, xs), color=c, lw=1)
    axs[1].scatter((x + y) / 2, y - x, s=24, color=c, alpha=.85)
    t = T[(T.pair == "unemp_rate") & (T.year == yr)].iloc[0]
    for v, ls in [(t.bias, "-"), (t.loa_lo, "--"), (t.loa_hi, "--")]: axs[1].axhline(v, color=c, ls=ls, lw=1)
lim = [1.5, 7]; axs[0].plot(lim, lim, color="black", lw=.8, ls=":"); axs[0].set_xlim(lim); axs[0].set_ylim(lim)
axs[0].set_xlabel("国勢調査の完全失業率（%）"); axs[0].set_ylabel("労働力調査（モデル推計）の完全失業率（%）")
axs[0].set_title("点線＝完全に一致する線", fontsize=10); axs[0].legend(frameon=False)
axs[1].axhline(0, color="black", lw=.8); axs[1].set_xlabel("2つの平均（%）"); axs[1].set_ylabel("労働力調査 − 国勢調査（ポイント）")
axs[1].set_title("労働力調査が1.1〜1.4ポイント低い", fontsize=10)
fig.suptitle("完全失業率：相関0.75〜0.84でも、一致相関（CCC）は0.13〜0.30", fontsize=11); fig.tight_layout(); fig.savefig(FG / "f180_3_unemployment.png", dpi=150); plt.close(fig)

# 4 就業率：国勢調査の分母と「不詳」の割合
fig, axs = plt.subplots(1, 2, figsize=(9.6, 4.6), sharey=True)
for ax, k, ttl in [(axs[0], "cen_emp_rate_known", "分母から「不詳」を除く"), (axs[1], "cen_emp_rate_all15", "分母に「不詳」を含める")]:
    for yr, c in [(2015, GR), (2020, C1)]:
        g = P[P.year == yr]; ax.scatter(g.cen_labor_unknown_share, g.lfs_emp_rate - g[k], s=24, color=c, alpha=.85, label=f"{yr}年")
    ax.axhline(0, color="black", lw=.8); ax.set_xlabel("国勢調査で労働力状態が「不詳」の割合（%）"); ax.set_title(ttl, fontsize=10)
axs[0].set_ylabel("労働力調査 − 国勢調査の就業率（ポイント）"); axs[0].legend(frameon=False)
fig.suptitle("就業率：国勢調査の分母の決め方で、ずれが0.2〜0.9ポイントから2.5〜5.4ポイントに", fontsize=11)
fig.tight_layout(); fig.savefig(FG / "f180_4_employment_rate_unknown.png", dpi=150); plt.close(fig)

# 5 市区町村：人口規模別のずれ（12市町村を除く）と、除いた12市町村
M = M[(M.A1101 > 0) & (M.A7101 > 0)].copy(); M["d"] = 100 * np.log(M.juki_pop / M.A1101); M["ev"] = M.code5.isin(EVAC)
bins = [0, 5e3, 2e4, 1e5, 1e6, 1e8]; labs = ["5千人未満", "5千〜2万", "2万〜10万", "10万〜100万", "100万以上"]
M["size"] = pd.cut(M.A1101, bins, labels=labs)
fig, ax = plt.subplots(figsize=(8.4, 5))
g = M[(M.year == 2020) & ~M.ev]
data = [g[g["size"] == l]["d"].values for l in labs]
bp = ax.boxplot(data, whis=(5, 95), showfliers=False, patch_artist=True, widths=.55)
for b in bp["boxes"]: b.set_facecolor("#cfe0ec"); b.set_edgecolor(C1)
for i, l in enumerate(labs): ax.text(i + 1, -7.6, f"{len(data[i])}", ha="center", fontsize=9, color=GR)
ax.axhline(0, color="black", lw=.8); ax.set_xticks(range(1, 6)); ax.set_xticklabels(labs); ax.set_ylim(-8, 13)
ax.set_xlabel("市区町村の人口（国勢調査、2020年）。数字は市区町村の数"); ax.set_ylabel("住基と国勢調査の差（%、対数の差×100）")
ev = M[(M.year == 2020) & M.ev]
ax.set_title(f"人口が小さい町村ほど住基が多く、ずれの幅も広い（2020年、箱＝中央50%、ひげ＝5〜95%）\n"
             f"原発事故の避難指示区域が設定された12市町村は除外（住基が国勢調査の{np.exp(ev.d.median()/100):.1f}倍〔中央値〕）", fontsize=10)
fig.tight_layout(); fig.savefig(FG / "f180_5_municipal_by_size.png", dpi=150); plt.close(fig)
print("ok", sorted(p.name for p in FG.glob("*.png")))
