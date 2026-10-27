"""図を作る"""
import ast, json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG

S = json.load(open(RES / "summary.json"))
C1, C2, C3, GR = "#2a6f97", "#d1495b", "#edae49", "#888888"

# 1. 全国の出生率と折れ目
f = pd.read_csv(RES / "national_fit.csv")
ci = S["break_ci90"]
fig, ax = plt.subplots(figsize=(9, 4.6))
for c in ci:
    ax.axvspan(c["lo"] - 0.5, c["hi"] + 0.5, color=C3, alpha=0.18, lw=0)
    ax.axvline(c["est"] - 0.5, color=C3, lw=1.2, ls="--")
ax.plot(f.year, f.tfr, "o", ms=3.2, color=C1, label="合計特殊出生率")
yrs = [1950] + [c["est"] for c in ci] + [2024]
for a, b in zip(yrs[:-1], yrs[1:]):
    m = (f.year >= a) & (f.year < b) & (f.year != 1966)
    ax.plot(f.year[m], f.fitted[m], color=C2, lw=2)
ax.annotate("1966年（丙午）", (1966, f.tfr[f.year == 1966].iloc[0]), xytext=(1972, 1.45), fontsize=9,
            arrowprops=dict(arrowstyle="-", color=GR), color=GR)
for c, seg in zip(ci, S["national_segments"][1:]):
    ax.text(c["est"] + 0.3, 3.35, f"{c['est']}年〜\n傾き {seg['slope']*10:+.2f}/10年", fontsize=8.5, va="top")
ax.set_ylim(1.0, 3.8); ax.set_xlim(1949, 2024)
ax.set_title("全国の合計特殊出生率（1950〜2023年）と、データから推定した4つの折れ目", fontsize=12)
ax.set_ylabel("合計特殊出生率")
ax.plot([], [], color=C2, lw=2, label="区間ごとの直線（Bai–Perron、BIC）")
ax.fill_between([], [], color=C3, alpha=0.3, label="折れ目の年の90%区間（ブートストラップ）")
ax.legend(loc="upper right", fontsize=8.5, frameon=False)
ax.text(1949.5, 1.03, "出典：国立社会保障・人口問題研究所『人口統計資料集（2025年版）』表12-33（元は厚生労働省『人口動態統計』）", fontsize=7.5, color=GR)
fig.tight_layout(); fig.savefig(FIG / "f44_national_breaks.png"); plt.close()

# 2. 折れ目の数と BIC・LWZ
ic = pd.read_csv(RES / "national_ic.csv")
fig, ax = plt.subplots(figsize=(7.5, 4))
ax.plot(ic.m, ic.bic, "o-", color=C1, label="BIC")
ax.plot(ic.m, ic.lwz, "s--", color=C2, label="LWZ（重い罰則）")
for r in ic.itertuples():
    lab = r.breaks.replace("[", "").replace("]", "") or "なし"
    off = -7 if r.m % 2 == 0 else 7
    ax.text(r.m, r.bic + off, lab, fontsize=7.5, ha="center", va="top" if off < 0 else "bottom", color=C1,
            bbox=dict(facecolor="white", edgecolor="none", pad=0.5))
ax.axvline(S["national_base"]["m"], color=GR, ls=":", lw=1)
ax.set_xlabel("折れ目の数"); ax.set_ylabel("情報量規準（小さいほどよい）")
ax.set_title("折れ目の数を選ぶ：BIC は4つ（5つとほぼ同点）、LWZ は3つで最小", fontsize=11.5)
ax.set_ylim(ic[["bic","lwz"]].min().min() - 25, ic[["bic","lwz"]].max().max() + 10)
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(FIG / "f44_ic.png"); plt.close()

# 3. ブートストラップでの折れ目の年
bs = pd.read_csv(RES / "bootstrap_break_years.csv")
fig, axes = plt.subplots(1, len(bs.columns), figsize=(10, 3.4), sharey=True)
for ax, col, c in zip(axes, bs.columns, ci):
    vc = bs[col].value_counts().sort_index()
    ax.bar(vc.index, vc.values / len(bs), color=C1, width=0.8)
    ax.axvline(c["est"], color=C2, lw=1.5)
    ax.set_title(f"{c['est']}年の折れ目\n90%区間 {c['lo']}〜{c['hi']}年", fontsize=10)
    ax.set_xlim(c["est"] - 20, c["est"] + 8)
axes[0].set_ylabel("299回のうちの割合")
fig.suptitle("折れ目の年はどこまで確かか：誤差を作り直して299回推定し直した結果", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f44_bootstrap.png"); plt.close()

# 4. 都道府県の折れ目の年の分布
pr = pd.read_csv(RES / "pref_breaks.csv")
yrs = [y for s in pr.years_bic for y in ast.literal_eval(s)]
vc = pd.Series(yrs).value_counts().sort_index()
fig, ax = plt.subplots(figsize=(9, 4.2))
ax.bar(vc.index, vc.values, color=C1, width=0.8, label="都道府県の折れ目（47都道府県、BIC）")
for y in S["national_1972"]["years"]:
    ax.axvline(y, color=C2, ls="--", lw=1.3)
ax.plot([], [], color=C2, ls="--", label="全国（同じ1972〜2023年）の折れ目")
ax.set_xlim(1971, 2024); ax.set_xlabel("新しい区間が始まる年"); ax.set_ylabel("都道府県の数")
ax.set_title("都道府県ごとに推定しても、折れ目は全国とほぼ同じ4つの時期に集まった", fontsize=12)
ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(FIG / "f44_pref_hist.png"); plt.close()

# 5. CUSUM
cu = pd.read_csv(RES / "cusum_1975_2023.csv")
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(cu.year, cu.cusum, color=C1, lw=2, label="再帰的残差の累積和（CUSUM）")
ax.plot(cu.year, cu.hi, color=GR, ls="--", lw=1, label="5%の境界")
ax.plot(cu.year, cu.lo, color=GR, ls="--", lw=1)
ax.axhline(0, color="black", lw=0.5)
fx = S["cusum"]["first_exceed"]
ax.annotate(f"{fx}年に境界を超える", (fx, cu.cusum[cu.year == fx].iloc[0]), xytext=(1990, 22), arrowprops=dict(arrowstyle="->", color=C2), color=C2, fontsize=10)
ax.set_title("1975〜2023年を1本の直線とみなすと、2016年に「安定していない」の線を超えた", fontsize=11.5)
ax.legend(frameon=False, fontsize=9, loc="upper left")
fig.tight_layout(); fig.savefig(FIG / "f44_cusum.png"); plt.close()

# 6. 頑健性（全国）
rb = pd.read_csv(RES / "robust_national.csv")
fig, ax = plt.subplots(figsize=(9, 4.4))
for i, r in enumerate(rb.itertuples()):
    ys = ast.literal_eval(r.years)
    ax.scatter(ys, [i] * len(ys), color=C2 if i == 0 else C1, s=40, zorder=3)
for x in [2006, 2016]:
    ax.axvspan(x - 1.5, x + 1.5, color=C3, alpha=0.2, lw=0)
ax.set_yticks(range(len(rb))); ax.set_yticklabels(rb.setting, fontsize=9); ax.invert_yaxis()
ax.set_xlim(1950, 2024); ax.set_xlabel("推定された折れ目の年")
ax.set_title("設定を変えても、2006年前後と2016年前後の折れ目はほぼ毎回出た", fontsize=12)
fig.tight_layout(); fig.savefig(FIG / "f44_robust.png"); plt.close()
print("ok")
