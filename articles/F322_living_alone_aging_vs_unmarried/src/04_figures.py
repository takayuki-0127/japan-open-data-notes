"""04 図：fig1〜fig4（PNG、日付などのメタデータなし）。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
RES = ROOT / "results"
p = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if pathlib.Path(p).exists():
    fm.fontManager.addfont(p)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e5e0",
                     "grid.linewidth": 0.6, "axes.axisbelow": True})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK2 = "#52514e"
SRC = "出典：総務省「国勢調査」時系列データ（世帯 第4表【参考】、配偶関係 第4表）、令和2年国勢調査 第12-1表（不詳補完値）をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
FACT = ["人口の大きさ", "年齢・男女の構成", "配偶関係の構成", "ひとりで暮らす割合"]

def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)

# fig1 配偶関係別のひとり暮らしの数
A = pd.read_csv(RES / "alone_by_year_marital.csv").set_index("year")
fig, ax = plt.subplots(figsize=(8, 4.6))
x = np.arange(len(A)); bottom = np.zeros(len(A))
for k, mm in enumerate(["未婚", "有配偶", "死別", "離別"]):
    v = A[mm].values / 1e6
    ax.bar(x, v, bottom=bottom, color=C[k], width=0.6, label=mm, edgecolor="#fcfcfb")
    bottom += v
for i, y in enumerate(A.index):
    ax.text(i, bottom[i] + 0.3, f"{A.loc[y,'alone']/1e4:,.0f}万人\n（{A.loc[y,'ひとり暮らしの割合_%']:.1f}%）", ha="center", fontsize=8.5, color=INK2)
ax.set_xticks(x, [f"{y}年" for y in A.index])
ax.set_ylabel("ひとり暮らしの人数（百万人）"); ax.set_ylim(0, 25)
ax.set_title("ひとり暮らしは35年で2.7倍に。6割前後は未婚の人", loc="left")
ax.legend(frameon=False, ncol=4, loc="upper left", title="配偶関係", fontsize=8.5, title_fontsize=8.5)
fig.subplots_adjust(bottom=0.17, left=0.09, right=0.98, top=0.9)
save(fig, "fig1_alone_by_marital.png", "15歳以上。（ ）は15歳以上人口に占める割合。2010・2015年は配偶関係別の表がそろわず省いた")

# fig2 要因分解（主結果と期間・男女の確かめ）
D = pd.read_csv(RES / "decomposition.csv")
labs = ["全体", "全体（1985→2005、同じ旧分類）", "全体（1995→2020）", "全体（2005→2020）", "男", "女"]
show = ["全体 1985→2020", "1985→2005", "1995→2020", "2005→2020", "男 1985→2020", "女 1985→2020"]
Dd = D.set_index("分析").loc[labs]
fig, ax = plt.subplots(figsize=(8, 4.8))
y = np.arange(len(labs))[::-1]
left_p = np.zeros(len(labs)); left_n = np.zeros(len(labs))
for k, f in enumerate(FACT):
    v = Dd[f"{f}_%"].values
    l = np.where(v >= 0, left_p, left_n)
    ax.barh(y, v, left=l, color=C[k], height=0.6, label=f, edgecolor="#fcfcfb")
    left_p += np.where(v >= 0, v, 0); left_n += np.where(v < 0, v, 0)
for i in range(len(labs)):
    ax.text(114, y[i], f"配偶関係 {Dd['配偶関係の構成_%'].iloc[i]:.0f}%／割合 {Dd['ひとりで暮らす割合_%'].iloc[i]:.0f}%", va="center", fontsize=8, color=INK2)
ax.axvline(0, color="#0b0b0b", lw=0.8)
ax.set_yticks(y, show)
ax.set_xlim(-15, 165); ax.set_xticks([0, 20, 40, 60, 80, 100])
ax.set_xlabel("ひとり暮らしの増加に対する寄与（%、合計100%）")
ax.set_title(f"増加の{M['主結果_1985_2020']['ひとりで暮らす割合_%']:.0f}%は暮らし方、{M['主結果_1985_2020']['配偶関係の構成_%']:.0f}%は配偶関係。年齢構成は{M['主結果_1985_2020']['年齢・男女の構成_%']:.1f}%", loc="left")
ax.legend(frameon=False, ncol=4, fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.12))
ax.grid(axis="y", visible=False)
fig.subplots_adjust(bottom=0.27, left=0.16, right=0.98, top=0.9)
save(fig, "fig2_decomposition.png", "4つの要因の順番を入れ替えた24通りの平均（シャープレイ値）")

# fig3 65歳以上と15〜64歳
H = M["H4"]
fig, ax = plt.subplots(figsize=(8, 4.4))
grp = ["15〜64歳", "65歳以上"]
y = np.arange(2)[::-1]
left_p = np.zeros(2); left_n = np.zeros(2)
for k, f in enumerate(FACT):
    v = np.array([H[g][f"{f}_人"] for g in grp]) / 1e6
    l = np.where(v >= 0, left_p, left_n)
    ax.barh(y, v, left=l, color=C[k], height=0.55, label=f, edgecolor="#fcfcfb")
    left_p += np.where(v >= 0, v, 0); left_n += np.where(v < 0, v, 0)
for i, g in enumerate(grp):
    ax.text(left_p[i] + 0.1, y[i], f"増加 {H[g]['増加']/1e4:,.0f}万人", va="center", fontsize=9, color=INK2)
ax.axvline(0, color="#0b0b0b", lw=0.8)
ax.set_yticks(y, grp); ax.set_xlim(-2, 10.5)
ax.set_xlabel("1985→2020年のひとり暮らしの増加への寄与（百万人）")
ax.set_title("65歳以上は人口の増加、15〜64歳は配偶関係の変化が大きい", loc="left")
ax.legend(frameon=False, ncol=4, fontsize=8, loc="upper left", bbox_to_anchor=(0, -0.15))
ax.grid(axis="y", visible=False)
fig.subplots_adjust(bottom=0.3, left=0.12, right=0.98, top=0.9)
save(fig, "fig3_by_age_group.png", "それぞれの年齢の中で4つの要因に分けた。65歳以上の「人口の大きさ」は65歳以上の人口の増加（高齢化）にあたる")

# fig4 問い直し：どのセルで生じたか（寄与の絶対値が増加の2%以上）
Q = pd.read_csv(RES / "requestion_cells.csv")
Q = Q[Q["増加に対する_%"].abs() >= 2].copy()
Q["lab"] = Q["年齢帯"] + "・" + Q["配偶関係"]
Q["ord"] = Q["要因"].map({"年齢・男女の構成": 2, "配偶関係の構成": 1, "ひとりで暮らす割合": 0})
Q = Q.sort_values(["ord", "増加に対する_%"], ascending=[True, True])
fig, ax = plt.subplots(figsize=(8, 6.2))
y = np.arange(len(Q))
CM = {"年齢・男女の構成": C[1], "配偶関係の構成": C[2], "ひとりで暮らす割合": C[3]}
NM = {"年齢・男女の構成": "年齢構成", "配偶関係の構成": "配偶関係", "ひとりで暮らす割合": "暮らし方"}
cols = [CM[f] for f in Q["要因"]]
ax.barh(y, Q["増加に対する_%"], color=cols, height=0.6)
for i, v in enumerate(Q["増加に対する_%"]):
    ax.text(v + (0.4 if v >= 0 else -0.4), y[i], f"{v:.1f}%", va="center", ha="left" if v >= 0 else "right", fontsize=8.5, color=INK2)
ax.set_yticks(y, [f"{a.replace('・（すべて）', '')}（{NM[f]}）" for a, f in zip(Q["lab"], Q["要因"])], fontsize=8.5)
ax.axvline(0, color="#0b0b0b", lw=0.8)
ax.set_xlim(-22, 40)
ax.set_xlabel("ひとり暮らしの増加（1985→2020年）に対する寄与（%）")
ax.set_title("高齢化の寄与（+22%）は15〜64歳の割合の低下で打ち消され、未婚の増加が残った", loc="left", fontsize=10)
ax.grid(axis="y", visible=False)
fig.subplots_adjust(bottom=0.16, left=0.3, right=0.98, top=0.92)
save(fig, "fig4_cells.png", "「年齢構成」は年齢帯ごと、「配偶関係」「暮らし方」は年齢帯×配偶関係ごとに寄与を分けた（増加の2%以上のものだけ表示）")
print("figures ok")
