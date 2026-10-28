"""04_図：図1〜6（Noto Sans CJK）"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
RES = ROOT / "results"
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP"], "axes.unicode_minus": False, "figure.dpi": 110,
                     "savefig.dpi": 150, "axes.spines.top": False, "axes.spines.right": False})
COL = {"A": "#1a73e8", "B": "#188038", "C": "#d93025", "D": "#e8710a", "D3": "#9334e6"}
LAB = {"A": "A 再集計", "B": "B 変化なしだけ", "C": "C コード突合", "D": "D 按分（人口比）", "D3": "D 按分（伸び延長）"}

res = json.load(open(RES / "results.json"))
summ = pd.read_csv(RES / "summary_by_method.csv")
rob = pd.read_csv(RES / "robustness.csv")
pp = pd.read_csv(RES / "by_prefecture.csv")
ev = pd.read_csv(ROOT / "data/merger_events.csv", dtype=str)
uA = pd.read_csv(RES / "unit_rates_A.csv", dtype={"code2020": str})
uC = pd.read_csv(RES / "unit_rates_C.csv", dtype={"code": str})

# 図1 市町村数の推移（2000年10月→2020年10月）
ev["n"] = ev.olds.fillna("").str.split(";").str.len()
def delta(r):
    olds = r.olds.split(";") if isinstance(r.olds, str) and r.olds else []
    if r.kind == "新設合併":
        return -(len(olds) - 1)
    if r.kind in ("編入合併", "分割編入"):
        return -len(olds)
    return 0
ev["d"] = ev.apply(delta, axis=1)
ev["date"] = pd.to_datetime(ev.date)
s = ev.groupby("date").d.sum().cumsum() + 3252
s = pd.concat([pd.Series({pd.Timestamp("2000-10-01"): 3252}), s, pd.Series({pd.Timestamp("2020-10-01"): s.iloc[-1]})])
fig, ax = plt.subplots(figsize=(9.5, 4.4))
ax.step(s.index, s.values, where="post", color="#1a73e8", lw=2)
ax.axvspan(pd.Timestamp("2005-04-01"), pd.Timestamp("2006-03-31"), color="#1a73e8", alpha=.08)
ax.text(pd.Timestamp("2005-10-01"), 3150, "合併が\n集中した1年", ha="center", fontsize=9, color="#1a73e8")
for d0, lab in [("2000-10-01", "2000年国勢調査\n3,252"), ("2020-10-01", f"2020年国勢調査\n{int(s.iloc[-1]):,}")]:
    ax.annotate(lab, (pd.Timestamp(d0), s.loc[pd.Timestamp(d0)] if pd.Timestamp(d0) in s.index else s.iloc[-1]),
                xytext=(10, 10) if d0 < "2010" else (-95, 25), textcoords="offset points", fontsize=9)
ax.set_ylabel("市町村の数（東京23区を含む）")
ax.set_title("2000〜2020年に、分析の単位は約半分になった（廃置分合の記録から再現）")
ax.set_ylim(1500, 3400); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "fig1_municipality_count.png"); plt.close()

# 図2 扱い方ごとの増減率の分布
fr = {"A": uA.rate, "C": uC.rate}
o = pd.read_csv(ROOT / "data/old_units_2000.csv", dtype={"code": str})
cw = pd.read_csv(ROOT / "data/crosswalk_2000_2020.csv", dtype={"code2000": str, "code2020": str})
fr["B"] = uA.set_index("code2020").loc[lambda d: d.n_old == 1].rate  # 近似用（下で置き換え）
unch = set(cw.loc[cw.unchanged, "code2020"])
fr["B"] = uA[uA.code2020.isin(unch)].rate
fig, ax = plt.subplots(figsize=(9.5, 4.8))
bins = np.arange(-60, 62, 4)
for k in ["A", "B", "C"]:
    v = fr[k].clip(-60, 60)
    ax.hist(v, bins=bins, histtype="step", lw=2, color=COL[k], density=True,
            label=f"{LAB[k]}（{len(v):,}単位、中央値 {fr[k].median():+.1f}%）")
ax.axvline(0, color="gray", lw=.8)
ax.set_xlabel("2000→2020年の人口増減率（%、±60%で打ち切って表示）"); ax.set_ylabel("密度")
ax.set_title("同じ国勢調査でも、つなぎ方で「増えた町」の割合が変わる")
ax.legend(fontsize=9); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "fig2_rate_distribution.png"); plt.close()

# 図3 3つの指標を扱い方ごとに
keys = ["A", "B", "C", "D", "D3"]
summ.index = ["A", "B", "C", "D", "D2", "D3"]
fig, axs = plt.subplots(1, 3, figsize=(11.5, 4.4))
for ax, col, ttl, fmt in [(axs[0], "median", "増減率の中央値（%）", "{:+.1f}"),
                          (axs[1], "share_increase", "人口が増えた単位の割合（%）", "{:.1f}"),
                          (axs[2], "slope", "「小さい町ほど減る」傾き\n（人口10倍あたりの増減率の差、%pt）", "{:.1f}")]:
    v = summ.loc[keys, col]
    bars = ax.barh([LAB[k] for k in keys], v, color=[COL[k] for k in keys])
    if col == "slope":
        lo, hi = summ.loc[keys, "slope_lo"], summ.loc[keys, "slope_hi"]
        ax.errorbar(v, range(len(keys)), xerr=[v - lo, hi - v], fmt="none", color="black", lw=1, capsize=3)
    pos = summ.loc[keys, "slope_hi"] if col == "slope" else v
    for i, (x, xp) in enumerate(zip(v, pos)):
        ax.text(xp + (0.4 if x >= 0 else -0.4), i, fmt.format(x), va="center", ha="left" if x >= 0 else "right", fontsize=9)
    ax.set_title(ttl, fontsize=10); ax.invert_yaxis(); ax.grid(axis="x", alpha=.3)
    if ax is not axs[0]:
        ax.set_yticklabels([])
axs[0].set_xlim(-22, 4); axs[1].set_xlim(0, 42); axs[2].set_xlim(0, 25)
fig.suptitle("合併の扱い方で、3つの「結論」の数字がどれだけ動くか（2000→2020年）", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "fig3_metrics_by_method.png"); plt.close()

# 図4 コード突合の見かけの増加：吸収した側
fig, ax = plt.subplots(figsize=(9.5, 4.8))
n = uC[~uC.absorber]; a = uC[uC.absorber]
ax.scatter(np.log10(n.pop0), n.rate.clip(-70, 200), s=7, color="#9aa0a6", alpha=.6, label=f"合併に関わらなかった単位（{len(n):,}）")
ax.scatter(np.log10(a.pop0), a.rate.clip(-70, 200), s=14, color=COL["C"], alpha=.8,
           label=f"コードを引き継いだ「吸収した側」（{len(a)}）：中央値 {a.rate.median():+.1f}%")
ax.axhline(0, color="black", lw=.8)
ax.set_xticks([2, 3, 4, 5, 6]); ax.set_xticklabels(["100", "1,000", "1万", "10万", "100万"])
ax.set_xlabel("2000年の人口（そのコードの市町村、対数目盛）")
ax.set_ylabel("増減率（%、200%で打ち切り）")
ax.set_title("同じコードをつなぐだけだと、吸収した町は合併した分だけ「増えた」ように見える")
ax.legend(fontsize=9, loc="upper right"); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "fig4_naive_absorbers.png"); plt.close()

# 図5 都道府県別：合併の多さと、コード突合のずれ
fig, ax = plt.subplots(figsize=(8.4, 5.2))
ax.scatter(pp.merged_share, pp.diff_C_A, s=pp.n2000 / 2.5, color=COL["C"], alpha=.55, edgecolor="white")
b = np.polyfit(pp.merged_share, pp.diff_C_A, 1)
xx = np.linspace(0, 100, 50); ax.plot(xx, np.polyval(b, xx), color="black", lw=1, ls="--")
ax.axhline(0, color="gray", lw=.8)
ax.set_xlabel("2000年の市町村のうち、合併に関わった割合（%）")
ax.set_ylabel("増減率の中央値のずれ\n（C コード突合 − A 再集計、%pt）")
ax.set_title(f"合併が多い県ほど、素朴なつなぎ方のずれが大きい（47都道府県、相関 {res['pref']['corr_merged_share_diffCA']:.2f}）", fontsize=10.5)
ax.text(2, pp.diff_C_A.max() * .95, "円の大きさ＝2000年の市町村数", fontsize=8.5, color="gray")
ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "fig5_prefecture_bias.png"); plt.close()

# 図6 頑健性：傾きの区間
fig, ax = plt.subplots(figsize=(9.5, 5.2))
checks = list(dict.fromkeys(rob.check))
for j, k in enumerate(["A", "B", "C", "D"]):
    g = rob[rob.method == k].set_index("check").loc[checks]
    y = np.arange(len(checks)) + (j - 1.5) * 0.18
    ax.errorbar(g.slope, y, xerr=[g.slope - g.slope_lo, g.slope_hi - g.slope], fmt="o", ms=4, color=COL[k], label=LAB[k], capsize=2)
ax.set_yticks(range(len(checks))); ax.set_yticklabels(checks, fontsize=9); ax.invert_yaxis()
ax.set_xlabel("「小さい町ほど減る」傾き（人口10倍あたりの増減率の差、%pt、95%区間）")
ax.set_title("条件を変えても、扱い方による傾きの差（B・C が大きく、D が小さい）は残る", fontsize=10.5)
ax.legend(fontsize=9, ncol=4, loc="upper center", bbox_to_anchor=(0.4, -0.11), frameon=False); ax.grid(axis="x", alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "fig6_robustness_slope.png"); plt.close()
print("figures:", sorted(p.name for p in FIG.glob("*.png")), "count_end", int(s.iloc[-1]))
