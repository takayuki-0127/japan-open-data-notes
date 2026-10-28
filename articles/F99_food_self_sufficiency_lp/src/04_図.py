"""04 図：5枚"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, setup_font

setup_font(); FIG.mkdir(exist_ok=True)
P = pd.read_csv(RES / "crop_params.csv"); G = json.load(open(RES / "params.json", encoding="utf-8"))
S = pd.read_csv(RES / "scenarios.csv"); R = pd.read_csv(RES / "robustness.csv")
NAMES = list(P["作物"])
COL = {"米": "#4C78A8", "小麦": "#E4A33B", "大豆": "#8C6D31", "ばれいしょ": "#B279A2", "かんしょ": "#D6616B", "野菜": "#54A24B"}
BASE = G["domestic_official"] / G["total_kcal"] * 100
SRC = "出典：農林水産省「食料需給表」（令和6年度）・「作物統計」「耕地及び作付面積統計」「野菜生産出荷統計」をもとに作成者が計算"

def foot(fig):
    fig.text(0.01, 0.005, SRC, fontsize=7.5, color="#555")

# 1) 1ha あたりの熱量と、今の自給の度合い
fig, ax = plt.subplots(1, 2, figsize=(11, 4.6))
o = P.sort_values("kcal_10a_年")
ax[0].barh(o["作物"], o["kcal_10a_年"] / 1e4, color=[COL[x] for x in o["作物"]])
for y, v in enumerate(o["kcal_10a_年"] / 1e4):
    ax[0].text(v + 3, y, f"{v:,.0f}万", va="center", fontsize=9)
ax[0].set_xlabel("10a（1反）で1年に作れる食べものの熱量（万kcal）"); ax[0].set_xlim(0, 310)
ax[0].set_title("10aあたりの熱量：かんしょ・米・ばれいしょが大きい", fontsize=11.5)
o2 = P.set_index("作物").loc[NAMES]
y = np.arange(len(NAMES))
ax[1].barh(y, o2["供給熱量_kcal人日"], color="#ddd", label="食べている量（1人1日）")
ax[1].barh(y, o2["国産熱量_kcal人日"], color=[COL[x] for x in NAMES], label="そのうち国産")
for i, (a, b) in enumerate(zip(o2["供給熱量_kcal人日"], o2["国産熱量_kcal人日"])):
    ax[1].text(a + 5, i, f"{b:.0f} / {a:.0f}", va="center", fontsize=9)
ax[1].set_yticks(y, NAMES); ax[1].invert_yaxis(); ax[1].set_xlim(0, 620)
ax[1].set_xlabel("1人1日あたり kcal（2024年度）"); ax[1].legend(loc="lower right", fontsize=8.5, frameon=False)
ax[1].set_title("6作物の熱量と、そのうち国産の分", fontsize=11.5)
fig.tight_layout(rect=(0, 0.04, 1, 1)); foot(fig); fig.savefig(FIG / "f01_kcal_per_area.png"); plt.close(fig)

# 2) 今の 2,248 kcal の内訳
fig, ax = plt.subplots(figsize=(11, 3.6))
parts = [(nm, P.set_index("作物").loc[nm, "国産熱量_kcal人日"], COL[nm]) for nm in NAMES]
parts += [("畜産物", G["livestock_dom"], "#9ecae9"), ("その他", G["other_fixed"], "#bbb")]
left = 0; small = []
for lab, v, c in parts:
    ax.barh(0, v, left=left, color=c, edgecolor="white")
    if v > 60:
        ax.text(left + v / 2, 0, f"{lab}\n{v:.0f}", ha="center", va="center", fontsize=9, color="white" if c not in ("#bbb", "#9ecae9") else "black")
    else:
        small.append(f"{lab} {v:.0f}")
    left += v
ax.barh(0, G["total_kcal"] - left, left=left, color="#f3f3f3", edgecolor="#ccc")
ax.text(left + (G["total_kcal"] - left) / 2, 0, f"輸入（輸入の飼料で育てた畜産物を含む）\n{G['total_kcal'] - left:,.0f}", ha="center", va="center", fontsize=9)
ax.text(left / 2, -0.47, "国産のうち小さいもの：" + "、".join(small) + "（kcal）", ha="center", va="top", fontsize=8.5)
ax.annotate(f"国産 {left:.0f} kcal＝{left / G['total_kcal'] * 100:.1f}%", xy=(left, 0.42), xytext=(left + 60, 0.52), fontsize=10,
            arrowprops=dict(arrowstyle="-", color="k"))
ax.axvline(left, color="k", lw=1)
ax.set_xlim(0, G["total_kcal"]); ax.set_ylim(-0.75, 0.62); ax.set_yticks([]); ax.set_xlabel("1人1日あたり供給熱量 2,248 kcal（2024年度）")
ax.set_title("モデルの出発点：今の国産 860 kcal を、6作物・畜産物（国産の飼料の分）・その他（魚介・砂糖・果実など）に分ける", fontsize=11)
fig.tight_layout(rect=(0, 0.05, 1, 1)); foot(fig); fig.savefig(FIG / "f02_baseline.png"); plt.close(fig)

# 3) シナリオ別の自給率
DL = {"D1": "今の食べ方のまま", "D2": "米を2000年度並み（今の1.3倍）まで\n食べてよい（いもは2倍まで）"}
LL = {"L0": "今の6作物の田と畑だけ", "L1": "＋飼料用米・WCS用稲の田", "L2": "＋畑の飼料作物も"}
fig, ax = plt.subplots(figsize=(11, 5.2))
w = 0.26; x = np.array([0, 1])
for j, L in enumerate(["L0", "L1", "L2"]):
    v1 = [S[(S.diet == d) & (S.land == L) & (S.cropcap == "C1")].ss.iloc[0] for d in ["D1", "D2"]]
    v0 = [S[(S.diet == d) & (S.land == L) & (S.cropcap == "C0")].ss.iloc[0] for d in ["D1", "D2"]]
    ax.bar(x + (j - 1) * w, v1, w * 0.9, color=["#c6dbef", "#6baed6", "#2171b5"][j], label=LL[L])
    ax.scatter(x + (j - 1) * w, v0, marker="_", s=260, color="#d62728", zorder=3, label="作付けの増減に上限を置かないとき" if j == 0 else None)
    for xi, a, c0 in zip(x + (j - 1) * w, v1, v0):
        ax.text(xi, a - 1.6, f"{a:.1f}", ha="center", fontsize=9, color="black" if j < 2 else "white")
        ax.text(xi, c0 + 0.5, f"{c0:.1f}", ha="center", fontsize=8, color="#d62728")
# 参考：カロリーだけを最大に（上限なし）
v3 = [S[(S.diet == "D3") & (S.land == L) & (S.cropcap == "C0")].ss.iloc[0] for L in ["L0", "L1", "L2"]]
for j, v in enumerate(v3):
    ax.bar(2 + (j - 1) * w, v, w * 0.9, color="none", edgecolor=["#c6dbef", "#6baed6", "#2171b5"][j], hatch="///", lw=1.2)
    ax.text(2 + (j - 1) * w, v + 0.5, f"{v:.1f}", ha="center", fontsize=8.5)
ax.axhline(BASE, color="k", ls="--", lw=1); ax.text(-0.45, BASE + 0.5, f"今 {BASE:.1f}%", fontsize=9)
ax.set_xticks([0, 1, 2], [DL["D1"], DL["D2"], "（参考）食べ方を気にせず\nカロリーだけを最大に（上限なし）"])
ax.set_ylim(30, 72); ax.set_xlim(-0.5, 2.5); ax.set_ylabel("カロリーベースの自給率（%）")
ax.legend(fontsize=8.5, frameon=False, loc="upper left", title="使える農地（棒）", title_fontsize=8.5)
ax.set_title("作るものを組み替えたときの自給率の最大値（棒：作付けの増減に上限あり）", fontsize=12)
fig.tight_layout(rect=(0, 0.04, 1, 1)); foot(fig); fig.savefig(FIG / "f03_scenarios.png"); plt.close(fig)

# 4) 面積の配分
sel = [("今（2024年）", None), ("今の食べ方\n今の農地", ("D1", "L0", "C1")), ("今の食べ方\n＋飼料の農地", ("D1", "L2", "C1")),
       ("米を多く食べる\n＋飼料用米・WCS", ("D2", "L1", "C1")), ("米を多く食べる\n＋飼料の農地", ("D2", "L2", "C1")),
       ("（参考）カロリー最大\n上限なし", ("D3", "L2", "C0"))]
fig, ax = plt.subplots(figsize=(11, 5))
for i, (lab, key) in enumerate(sel):
    if key is None:
        a = P.set_index("作物")["面積_ha"].to_dict(); feed = G["feed_rice_ha"] + G["wcs_ha"] + G["feed_land_upland_ha"]
    else:
        r = S[(S.diet == key[0]) & (S.land == key[1]) & (S.cropcap == key[2])].iloc[0]
        a = {nm: r["面積_" + nm] for nm in NAMES}
        feed = G["feed_rice_ha"] + G["wcs_ha"] + G["feed_land_upland_ha"] - r.feed_rice_used - r.wcs_used - r.upland_feed_used
    bot = 0
    for nm in NAMES:
        ax.bar(i, a[nm] / 1e4, bottom=bot, color=COL[nm], label=nm if i == 0 else None, edgecolor="white", lw=0.5); bot += a[nm] / 1e4
    ax.bar(i, feed / 1e4, bottom=bot, color="#ddd", hatch="//", edgecolor="white", label="飼料用（残した分）" if i == 0 else None)
    if key is not None:
        r = S[(S.diet == key[0]) & (S.land == key[1]) & (S.cropcap == key[2])].iloc[0]
        ax.text(i, bot + feed / 1e4 + 3, f"自給率 {r.ss:.1f}%", ha="center", fontsize=9.5)
    else:
        ax.text(i, bot + feed / 1e4 + 3, f"自給率 {BASE:.1f}%", ha="center", fontsize=9.5)
ax.set_xticks(range(len(sel)), [s[0] for s in sel], fontsize=8.8); ax.set_ylabel("作付面積（万ha、延べ）")
ax.legend(fontsize=8.5, frameon=False, ncol=7, loc="upper center", bbox_to_anchor=(0.5, 1.0)); ax.set_ylim(0, 365)
ax.set_title("線形計画が選んだ作付け：今の食べ方では小麦・大豆、米をもっと食べるなら米が増える", fontsize=11.5)
fig.tight_layout(rect=(0, 0.04, 1, 1)); foot(fig); fig.savefig(FIG / "f04_allocation.png"); plt.close(fig)

# 5) 頑健性
fig, axs = plt.subplots(1, 2, figsize=(11.5, 5.4), sharex=False)
for ax, ref, ttl in [(axs[0], "D1-L2-C1", "今の食べ方＋飼料の農地（41.7%）"), (axs[1], "D2-L1-C1", "米を多く食べる＋飼料用米・WCS（41.7%）")]:
    d = R[R.ref == ref].iloc[::-1]
    yy = np.arange(len(d))
    ax.barh(yy, d["diff"], color=["#d62728" if v < 0 else "#2ca02c" for v in d["diff"]])
    ax.set_yticks(yy, d["test"], fontsize=8.5); ax.axvline(0, color="k", lw=0.8)
    for yi, v in zip(yy, d["diff"]):
        ax.text(v + (0.1 if v >= 0 else -0.1), yi, f"{v:+.1f}", va="center", ha="left" if v >= 0 else "right", fontsize=8)
    ax.set_xlim(-4.5, 6); ax.set_xlabel("自給率の差（ポイント）"); ax.set_title(ttl, fontsize=10.5)
fig.suptitle("前提を1つずつ変えると：収量・農地で ±1〜3 ポイント、作付けの上限を外すと最大 +5 ポイント", fontsize=11.5)
fig.tight_layout(rect=(0, 0.04, 1, 0.96)); foot(fig); fig.savefig(FIG / "f05_robustness.png"); plt.close(fig)
print("ok")
