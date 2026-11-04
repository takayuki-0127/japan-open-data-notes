"""04 図：figures/ に5枚の PNG を出す。"""
import json, logging, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

warnings.filterwarnings("ignore"); logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
DATA, RES, FIG = ROOT / "data", ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#3aa07a", "#7a5bd6"
SRC = "出典：国土交通省「建築着工統計調査」、日本銀行「基準割引率および基準貸付利率」「貸出約定平均金利」、総務省「人口推計」を加工して作成"
S = json.load(open(RES / "summary.json"))


def foot(fig, extra="", y=-0.02):
    fig.text(0.01, y, (extra + "\n" if extra else "") + SRC, fontsize=7.5, color=GRAY, ha="left", va="top")


# 1. 長い推移
a = pd.read_csv(DATA / "annual.csv").set_index("year").loc[1965:]
fig, ax = plt.subplots(3, 1, figsize=(9, 8.2), sharex=True, gridspec_kw={"height_ratios": [2.2, 1, 1]})
ax[0].stackplot(a.index, a.owner / 1e4, a.rental / 1e4, a.sale / 1e4, a.company / 1e4,
                labels=["持家", "貸家", "分譲", "給与住宅"], colors=[BLUE, ORANGE, GREEN, GRAY], alpha=0.85)
ax[0].set_ylabel("新設住宅着工（万戸）"); ax[0].legend(loc="upper right", ncol=4, frameon=False, fontsize=9)
ax[0].set_title("新設住宅の着工戸数と、金利・25〜44歳人口（1965〜2025年）", loc="left")
ax[1].plot(a.index, a.basic_rate, color=PURPLE, label="基準割引率")
ax[1].plot(a.index, a.loan_lt_city_stock, color=PURPLE, ls="--", label="都市銀行の長期貸出金利（残高）")
ax[1].set_ylabel("金利（%）"); ax[1].legend(frameon=False, fontsize=9)
ax[2].plot(a.index, a.pop_25_44 / 1e3, color=INK); ax[2].set_ylabel("25〜44歳（百万人）")
for x in (1973, 1996, 2009):
    for k in ax: k.axvline(x, color=GRAY, lw=0.6, ls=":")
foot(fig); fig.savefig(FIG / "f181_1_long_run.png"); plt.close(fig)

# 2. ピーク以降の減少と、人口に比例した場合
p73, p96 = S["percap_1973"], S["percap_1996"]
lab = ["1973→2024年", "1996→2024年"]
act = [p73["starts_pct"] * 100, p96["starts_pct"] * 100]
prop = [p73["pop_pct"] * 100, p96["pop_pct"] * 100]
fig, ax = plt.subplots(figsize=(8.5, 4.6))
x = np.arange(2); w = 0.36
b1 = ax.bar(x - w / 2, act, w, color=BLUE, label="着工戸数の実際の変化")
b2 = ax.bar(x + w / 2, prop, w, color=GRAY, label="25〜44歳人口の変化（着工が人口に比例するなら、この分だけ減る）")
for b in list(b1) + list(b2):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() - 1.5, f"{b.get_height():.0f}%", ha="center", va="top", fontsize=11, color=INK)
ax.set_xticks(x, lab); ax.axhline(0, color=INK, lw=0.8); ax.set_ylabel("変化（%）"); ax.set_ylim(-72, 5)
ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=1)
ax.set_title("着工の減り方は、人口の減り方の2倍以上。金利はこの間むしろ下がった", loc="left", fontsize=12)
foot(fig, "25〜44歳1,000人あたりの着工：1973年 54.6戸 → 1996年 48.8戸 → 2024年 28.9戸", y=-0.13)
fig.savefig(FIG / "f181_2_decline_vs_population.png"); plt.close(fig)

# 3. 分散分解（基本）
sh = pd.read_csv(RES / "var_main_shares.csv")
fig, axs = plt.subplots(1, 2, figsize=(9.5, 4.4), sharey=True)
for ax, col, ttl in zip(axs, ("chol", "gen"), ("コレスキー分解（人口→金利→着工）", "一般化分散分解（並べ順によらない）")):
    t = sh.pivot(index="h", columns="var", values=col).loc[[4, 20, 40]]
    bottom = np.zeros(3)
    for v, c, l in (("r", PURPLE, "金利"), ("pop", INK, "25〜44歳人口"), ("st", GRAY, "着工自身（その他の要因）")):
        ax.bar(["1年先", "5年先", "10年先"], t[v] * 100, bottom=bottom, color=c, label=l, width=0.6)
        for i, (bt, vv) in enumerate(zip(bottom, t[v] * 100)):
            if vv > 4: ax.text(i, bt + vv / 2, f"{vv:.0f}%", ha="center", va="center", color="white", fontsize=10)
        bottom += t[v].values * 100
    ax.set_title(ttl, fontsize=11, loc="left")
axs[0].set_ylabel("着工の予測の外れの内訳（%）"); axs[0].legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(1.05, -0.1), ncol=3)
fig.suptitle("四半期の VAR（1977〜2024年）：着工の動きの2割強が金利、人口は6%", x=0.01, ha="left", fontsize=13)
foot(fig, y=-0.1, extra="VAR：25〜44歳人口（対数）・都市銀行の長期貸出金利・着工戸数（季節調整値、対数）、ラグ2、定数とトレンドあり")
fig.savefig(FIG / "f181_3_fevd_main.png"); plt.close(fig)

# 4. 頑健性（5年先）
rb = pd.read_csv(RES / "var_robustness.csv").query("h == 20").drop_duplicates("case")
rb = rb[~rb.case.isin(["ラグ2"])]
fig, ax = plt.subplots(figsize=(9, 6.2))
y = np.arange(len(rb))[::-1]
ax.scatter(rb.rate_gen * 100, y, color=PURPLE, s=40, label="金利", zorder=3)
ax.scatter(rb.pop_gen * 100, y, color=INK, s=40, marker="s", label="25〜44歳人口", zorder=3)
for yy, r, p_ in zip(y, rb.rate_gen * 100, rb.pop_gen * 100):
    ax.plot([min(r, p_), max(r, p_)], [yy, yy], color=GRAY, lw=1, zorder=1)
ax.set_yticks(y, rb.case); ax.set_xlabel("5年先の予測の外れのうち、その変数で説明される割合（%、一般化分散分解）")
ax.axvline(0, color=INK, lw=0.6); ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1.0, 0.93))
ax.set_title("条件を変えると、金利と人口の取り分は入れ替わることもある", loc="left", fontsize=12)
foot(fig); fig.savefig(FIG / "f181_4_robustness.png"); plt.close(fig)

# 5. 都道府県（2012→2023）
cc = pd.read_csv(RES / "pref_change_2012_2023.csv")
fig, ax = plt.subplots(figsize=(7.6, 5.2))
ax.scatter(cc.dlpop * 100, cc.dlst * 100, color=BLUE, alpha=0.75, s=30)
xx = np.linspace(cc.dlpop.min(), cc.dlpop.max(), 10)
b = S["pref_change"]["b"]; c0 = cc.dlst.mean() - b * cc.dlpop.mean()
ax.plot(xx * 100, (c0 + b * xx) * 100, color=ORANGE, lw=1.5, label=f"回帰直線（傾き {b:.2f}、R² {S['pref_change']['r2']:.2f}）")
ax.plot(xx * 100, (cc.dlst.mean() - cc.dlpop.mean() + xx) * 100, color=GRAY, ls="--", lw=1, label="人口に比例する場合（傾き1）")
ax.axhline(0, color=GRAY, lw=0.5); ax.set_xlabel("総人口の変化（%、対数差×100）"); ax.set_ylabel("着工戸数の変化（%、対数差×100）")
ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.set_title("都道府県：人口の減り方と着工の減り方は、ほぼ無関係（2012→2023年）", loc="left", fontsize=11.5)
foot(fig, "1点が1都道府県。県名は示していません。出典に SSDSE-B（統計センター）を含む")
fig.savefig(FIG / "f181_5_pref_change.png"); plt.close(fig)
print("ok")
