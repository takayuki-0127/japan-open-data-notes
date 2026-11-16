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
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"]
INK2 = "#52514e"
SRC = "出典：総務省「住宅・土地統計調査」（平成30年調査 時系列 第21-1表、令和5年調査 第44-1表）をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
T = pd.read_csv(RES / "rate_age_by_year.csv").set_index("age"); T.columns = T.columns.astype(int)
Cc = pd.read_csv(RES / "rate_cohort_by_age.csv").set_index("cohort")
AGES = list(T.index); AJ = [a.replace("-", "〜") for a in AGES]

def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)

NOTE = "持ち家率＝持ち家÷（持ち家＋借家）。主世帯、全国。年齢は家計を主に支える者"
# fig1 年齢別の推移
fig, ax = plt.subplots(figsize=(8, 4.8))
for a, c in [("30-34", C[1]), ("35-39", C[3]), ("45-49", C[2]), ("55-59", C[0])]:
    ax.plot(T.columns, T.loc[a], color=c, lw=2, marker="o", ms=4, label=a.replace("-", "〜") + "歳")
ax.set_xticks(T.columns); ax.set_ylim(0, 90)
ax.set_ylabel("持ち家率（%）"); ax.set_xlabel("調査年")
ax.set_title(f"30〜34歳の持ち家率は1983年{M['H1']['30_34_1983']:.0f}%→2023年{M['H1']['30_34_2023']:.0f}%。下がったのは主に1983〜93年", loc="left", fontsize=10)
ax.legend(frameon=False, ncol=4, fontsize=8.5, loc="lower left")
fig.subplots_adjust(bottom=0.17, left=0.09, right=0.98, top=0.9)
save(fig, "fig1_rate_by_year.png", NOTE)

# fig2 世代で追う
fig, ax = plt.subplots(figsize=(8, 4.8))
x = np.arange(len(AGES))
for k, coh in enumerate([1946, 1956, 1966, 1976, 1986]):
    v = Cc.loc[coh, AGES].values
    ax.plot(x, v, color=C[k], lw=2, marker="o", ms=4, label=f"{coh}年ごろ生まれ")
ax.set_xticks(x, [a + "歳" for a in AJ], fontsize=8.5); ax.set_ylim(0, 90)
ax.set_ylabel("持ち家率（%）"); ax.set_xlabel("家計を主に支える者の年齢")
ax.set_title("新しい世代ほど低いところから始まり、年齢とともに上がるが、前の世代には届いていない", loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8.5, loc="lower right")
fig.subplots_adjust(bottom=0.17, left=0.09, right=0.98, top=0.9)
save(fig, "fig2_cohorts.png", "生まれ年は「調査年−年齢の中央」で近似。" + NOTE)

# fig3 2023年と1983年の差（年齢別）
G = pd.read_csv(RES / "gap_by_age.csv").set_index("age")
fig, ax = plt.subplots(figsize=(8, 4.4))
v = G["2023年−1983年"].values
ax.bar(x, v, color=C[0], width=0.6)
for i in range(len(x)):
    ax.text(x[i], v[i] - 0.5, f"{v[i]:.1f}", ha="center", va="top", fontsize=8.5, color=INK2)
ax.axhline(0, color="#0b0b0b", lw=0.8)
ax.set_xticks(x, [a + "歳" for a in AJ], fontsize=8.5); ax.set_ylim(-24, 3)
ax.set_ylabel("2023年−1983年（ポイント）")
ax.set_title("同じ年齢で比べた差は、30代前半の−20ポイントから、40代〜50代でも−13ポイント前後残る", loc="left", fontsize=10)
fig.subplots_adjust(bottom=0.17, left=0.09, right=0.98, top=0.9)
save(fig, "fig3_gap_by_age.png", NOTE)

# fig4 問い直し：この15年で下がった年齢
q = M["問い直し"]
fig, ax = plt.subplots(figsize=(8, 4.4))
v1 = [q["1983_1993_変化_pt"][a] for a in AGES]; v2 = [q["2008_2023_変化_pt"][a] for a in AGES]
ax.bar(x - 0.19, v1, width=0.38, color=C[3], label="1983→1993年")
ax.bar(x + 0.19, v2, width=0.38, color=C[1], label="2008→2023年")
ax.axhline(0, color="#0b0b0b", lw=0.8)
ax.set_xticks(x, [a + "歳" for a in AJ], fontsize=8.5)
ax.set_ylabel("持ち家率の変化（ポイント）")
ax.set_title("1983〜93年は20〜30代、この15年（2008〜23年）は40代後半〜50代で下がった", loc="left", fontsize=10)
ax.legend(frameon=False, loc="lower right", fontsize=8.5)
fig.subplots_adjust(bottom=0.17, left=0.09, right=0.98, top=0.9)
save(fig, "fig4_where_it_fell.png", NOTE)
print("figures ok")
