"""04 図：figures/ に5枚の図を書く（05_月最大.py のあとに実行）。"""
import importlib.util
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = Path(__file__).resolve().parents[1]
D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
for p in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"]:
    if Path(p).exists():
        fm.fontManager.addfont(p)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "figure.dpi": 150,
                     "axes.spines.top": False, "axes.spines.right": False})
BLUE, ORANGE, GRAY, LIGHT = "#2b6cb0", "#dd6b20", "#718096", "#cbd5e0"

spec = importlib.util.spec_from_file_location("a", ROOT / "src" / "03_分析.py")
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
S = A.load()
sp = pd.read_csv(R / "split_1901_1960_to_1961_2025.csv").set_index("station")

# 図1 4地点の年最大と、1901〜1960年で決めた「100年に1度」
fig, axes = plt.subplots(2, 2, figsize=(9, 6), sharex=True)
for ax, s in zip(axes.flat, ["高知", "名古屋", "東京", "札幌"]):
    x = S[s]
    thr = sp.loc[s, "rl"]
    over = (x.index >= 1961) & (x.values > thr)
    ax.bar(x.index, x.values, width=0.8, color=LIGHT)
    ax.bar(x.index[over], x.values[over], width=0.8, color=ORANGE)
    ax.axvspan(1901, 1960.5, color="#ebf4ff", zorder=0)
    ax.axhline(thr, color=BLUE, lw=1.4)
    ax.text(1903, thr * 1.03, f"1901〜1960年で決めた100年に1度：{thr:.0f}mm", color=BLUE, fontsize=8)
    ax.set_title(f"{s}（超えた年：{int(over.sum())}回）", loc="left", fontsize=10)
    ax.set_ylim(0, max(x.max(), thr) * 1.18)
for ax in axes[:, 0]:
    ax.set_ylabel("年最大の日降水量（mm）")
fig.suptitle("年ごとの最大日降水量。青い帯の60年で「100年に1度」を決め、1961年以降に超えた年をオレンジに", x=0.01, ha="left", fontsize=11)
fig.tight_layout()
fig.savefig(F / "f167_1_examples.png")
plt.close()

# 図2 超えた回数：観測・単純な期待値・気候が変わらない世界の期待値
rob = pd.read_csv(R / "robustness_split.csv")
lab = {"主分析 1901-60→1961-2025 最尤": "主分析：1901〜60年で決め、1961〜2025年に数える",
       "推定法 L積率": "推定法を L積率法に",
       "区切り 1901-50→1951-2025": "区切りを1950年に",
       "区切り 1901-70→1971-2025": "区切りを1970年に",
       "学習30年 1931-60→1961-2025": "30年分で決める（1931〜60年）",
       "学習30年 1961-90→1991-2025": "30年分で決める（1961〜90年→1991年以降）",
       "学習90年 1901-90→1991-2025": "90年分で決める（1901〜90年→1991年以降）",
       "50年に1度 1901-60→1961-2025": "「50年に1度」で数える",
       "20年に1度 1901-60→1961-2025": "「20年に1度」で数える"}
rr = rob.copy()
rr["obs_n"] = rr.observed / rr.naive_expected
rr["sta_n"] = rr.stationary_expected / rr.naive_expected
fig, ax = plt.subplots(figsize=(9, 5.4))
y = np.arange(len(rr))[::-1]
ax.axvline(1, color=GRAY, lw=1, ls="--")
ax.scatter(rr.sta_n, y, marker="|", s=300, color=BLUE, label="気候が変わらなくても出る回数（推定の揺れを含む）", zorder=3)
ax.scatter(rr.obs_n, y, color=ORANGE, s=45, label="実際に超えた回数", zorder=4)
for yi, (_, r) in zip(y, rr.iterrows()):
    ax.text(max(r.obs_n, r.sta_n) + 0.08, yi, f"{r.observed}回／{r.station_years:,}地点年", va="center", fontsize=8)
ax.set_yticks(y, [lab[s] for s in rr.setting], fontsize=9)
ax.set_xlabel("「年数×確率」で計算した単純な期待回数を1としたときの比")
ax.set_xlim(0, 3.6)
ax.legend(loc="upper center", bbox_to_anchor=(0.4, -0.12), ncol=2, fontsize=8, frameon=False)
ax.set_title("決めた「○年に1度」を、その後に何回超えたか（28地点の年最大日降水量）", loc="left", fontsize=11)
fig.tight_layout()
fig.savefig(F / "f167_2_counts.png")
plt.close()

# 図3 全期間で推定した100年値と、その95%区間・観測史上最大
full = pd.read_csv(R / "gev_full_period.csv").sort_values("rl100_mle")
fig, ax = plt.subplots(figsize=(8, 7))
yy = np.arange(len(full))
ax.hlines(yy, full.rl100_lo, full.rl100_hi, color=LIGHT, lw=6)
ax.scatter(full.rl100_mle, yy, color=BLUE, s=25, zorder=3, label="100年に1度の値（推定）と95%区間")
ax.scatter(full.record, yy, color=ORANGE, marker="x", s=30, zorder=4, label="その地点の観測史上最大（1901〜2025年）")
ax.set_yticks(yy, [f"{s}（{n}年）" for s, n in zip(full.station, full.n)], fontsize=8)
ax.set_xlabel("年最大の日降水量（mm）")
ax.legend(loc="lower right", fontsize=8, frameon=False)
ax.set_title("100年以上のデータがあっても、「100年に1度」の値は幅をもってしか決まらない", loc="left", fontsize=10.5)
fig.tight_layout()
fig.savefig(F / "f167_3_uncertainty.png")
plt.close()

# 図4 30年ごとの変化：ふだんの年の最大（中央値）・10年値・100年値
w = pd.read_csv(R / "gev_by_30yr_window.csv")
fig, ax = plt.subplots(figsize=(8.5, 4.6))
items = [("median", "ふだんの年の最大\n（30年の中央値）"), ("rl10_mle", "10年に1度の値"), ("rl100_mle", "100年に1度の値\n（最尤法）"),
         ("rl100_lmom", "100年に1度の値\n（L積率法）")]
rng = np.random.default_rng(0)
for i, (v, nm) in enumerate(items):
    p = w.pivot(index="station", columns="window", values=v).dropna()
    r = p["1991-2020"] / p["1901-1930"] - 1
    ax.scatter(i + rng.uniform(-0.12, 0.12, len(r)), r * 100, color=BLUE if i < 2 else GRAY, alpha=0.6, s=18)
    ax.hlines(r.median() * 100, i - 0.25, i + 0.25, color=ORANGE, lw=2.5)
    ax.text(i + 0.28, r.median() * 100, f"中央値 {r.median()*100:+.0f}%\n{int((r > 0).sum())}/{len(r)}地点で増", fontsize=8, va="center")
ax.axhline(0, color=GRAY, lw=1, ls="--")
ax.set_xticks(range(len(items)), [nm for _, nm in items], fontsize=9)
ax.set_xlim(-0.5, len(items) - 0.1)
ax.set_ylabel("1991〜2020年 ÷ 1901〜1930年 − 1（%）")
ax.set_title("30年ずつで比べると、ふだんの大雨は増えたが、100年値は揺れが大きくて変化が見えない（25地点）", loc="left", fontsize=10)
fig.tight_layout()
fig.savefig(F / "f167_4_windows.png")
plt.close()

# 図5 しきい値・ブロックの長さで100年値と超えた回数がどう変わるか（8地点）
mres = pd.read_csv(R / "monthly_block_threshold_rl100.csv").set_index("station")
msum = pd.read_csv(R / "monthly_split_summary.csv").set_index("method")
cols = [("gev_半年", "GEV 半年ごと", "GEV 半年"), ("gev_1年", "GEV 1年ごと", "GEV 1年"), ("gev_2年", "GEV 2年ごと", "GEV 2年"),
        ("gpd_上位10%", "GPD 上位10%", "GPD 上位10%"), ("gpd_上位5%", "GPD 上位5%", "GPD 上位5%"), ("gpd_上位2.5%", "GPD 上位2.5%", "GPD 上位2.5%")]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.4), gridspec_kw={"width_ratios": [1.4, 1]})
for s in mres.index:
    vals = [mres.loc[s, c] / mres.loc[s, "gev_1年"] for c, _, _ in cols]
    a1.plot(range(len(cols)), vals, marker="o", ms=4, lw=1, alpha=0.75, label=s)
a1.axhline(1, color=GRAY, lw=1, ls="--")
a1.set_xticks(range(len(cols)), [n for _, n, _ in cols], fontsize=8, rotation=25)
a1.set_ylabel("「GEV 1年ごと」の100年値に対する比")
a1.legend(fontsize=7, ncol=2, frameon=False)
a1.set_title("全期間の100年値", loc="left", fontsize=10)
obs = [msum.loc[m, "observed"] for _, _, m in cols]
a2.barh(range(len(cols))[::-1], obs, color=[BLUE, BLUE, BLUE, ORANGE, ORANGE, ORANGE])
a2.axvline(msum.naive_expected.iloc[0], color=GRAY, ls="--", lw=1)
a2.text(msum.naive_expected.iloc[0] + 0.2, 5.4, "年数×1%", fontsize=8, color=GRAY)
a2.set_yticks(range(len(cols))[::-1], [n for _, n, _ in cols], fontsize=8)
for i, o in zip(range(len(cols))[::-1], obs):
    a2.text(o + 0.2, i, str(o), va="center", fontsize=8)
a2.set_xlabel("1961〜2025年に超えた回数（8地点・520地点年）")
a2.set_title("1901〜60年で決めた100年値を超えた回数", loc="left", fontsize=10)
fig.suptitle("しきい値とブロックの長さを変えると（月ごとの最大日降水量がそろう8地点）", x=0.01, ha="left", fontsize=11)
fig.tight_layout()
fig.savefig(F / "f167_5_methods.png")
plt.close()
print("ok")
