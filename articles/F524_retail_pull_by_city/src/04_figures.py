"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：経済産業省「商業統計」、総務省・経済産業省「経済センサス‐活動調査」、総務省「国勢調査」をもとに作成者が加工して作成"
META = {"Software": None}


def finish(fig, ax, title, grid="y"):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.grid(axis=grid, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.01, SRC, fontsize=7.6, color=INK2)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.89, bottom=0.19)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)


m = json.load(open(R / "main.json", encoding="utf-8"))
d = pd.read_csv(R / "index_by_municipality.csv", dtype={"code": str})
cap = pd.read_csv(R / "requestion_capitals.csv", dtype={"code": str}).sort_values("code").reset_index(drop=True)
LABELS = ["5千人未満", "5千〜1万人", "1万〜3万人", "3万〜10万人", "10万〜30万人", "30万人以上"]
v = d[d.idx2021.notna()]


def boxes(ax, groups, labels):
    x = np.arange(len(groups))
    rng = np.random.default_rng(0)
    for i, g in enumerate(groups):
        y = g.clip(upper=3).values
        ax.scatter(i + rng.uniform(-0.2, 0.2, len(y)), y, s=5, color=C[0], alpha=0.3, lw=0)
    ax.boxplot([g.values for g in groups], positions=x, widths=0.5, showfliers=False, medianprops={"color": C[1], "lw": 2.2},
               boxprops={"color": INK2}, whiskerprops={"color": INK2}, capprops={"color": INK2})
    ax.axhline(1, color=INK2, lw=1, ls="--")
    ax.set_xticks(x, labels, fontsize=9.5)
    ax.set_ylim(0, 3.1)


# 図1：人口規模別
fig, ax = plt.subplots(figsize=(9, 5.4))
g = [v[v["size"] == s].idx2021 for s in LABELS]
boxes(ax, g, [f"{s}\n1超え {m['size_over1_2021'][s]:.0f}%" for s in LABELS])
ax.set_ylabel("小売吸引力指数（2021年、3で頭打ちにして表示）")
ax.text(-0.45, 1.03, "全国平均＝1", ha="left", va="bottom", fontsize=9, color=INK2)
finish(fig, ax, f"人口の多い市ほど客を集める：中央値は5千人未満 {m['size_median_2021']['5千人未満']:.2f}、30万人以上 {m['size_median_2021']['30万人以上']:.2f}")
save(fig, "fig1_index_by_size.png")

# 図2：都市圏の中心市・周辺市町村
fig, ax = plt.subplots(figsize=(9, 5.4))
roles = [("中心市", "都市圏の中心市"), ("周辺市町村", "都市圏の周辺市町村"), ("なし", "都市圏の外")]
g = [v[v.role == k].idx2021 for k, _ in roles]
boxes(ax, g, [f"{lab}（{len(x)}）\n1超え {m['role_over1_2021'][k]:.0f}%" for (k, lab), x in zip(roles, g)])
ax.set_ylabel("小売吸引力指数（2021年、3で頭打ちにして表示）")
finish(fig, ax, f"都市圏の中心市は中央値 {m['role_median_2021']['中心市']:.2f}、周辺の市町村は {m['role_median_2021']['周辺市町村']:.2f}")
save(fig, "fig2_index_by_role.png")

# 図3：県庁所在市 2014→2021（北から南）
fig, ax = plt.subplots(figsize=(10, 5.6))
x = np.arange(len(cap))
nm = [n.replace("特別区部", "東京23区") for n in cap.name]
ax.vlines(x, cap.idx2014, cap.idx2021.clip(upper=1.7), color=GRID, lw=2.2)
ax.scatter(x, cap.idx2014, s=24, color="#b9b8b3", label="2014年", zorder=3)
ax.scatter(x, cap.idx2021.clip(upper=1.7), s=26, color=C[0], label="2021年", zorder=3)
yq = int(cap.index[cap.idx2021 > 1.7][0]) if (cap.idx2021 > 1.7).any() else None
if yq is not None:
    ax.annotate(f"{cap.idx2021[yq]:.2f}（店の売上だけでは {cap.idx_store2021[yq]:.2f}）", (yq, 1.7), xytext=(yq - 0.5, 1.66), ha="right", fontsize=8.5, color=C[0])
ax.axhline(1, color=INK2, lw=1, ls="--")
ax.set_xticks(x, nm, rotation=90, fontsize=8.5); ax.set_xlim(-0.8, len(cap) - 0.2); ax.set_ylim(0.6, 1.75)
ax.set_ylabel("小売吸引力指数")
ax.legend(loc="upper left", frameon=False, fontsize=9.5, ncol=2)
finish(fig, ax, f"県庁所在市：47市のうち{m['capital_down']}市で下がった（中央値 {m['capital_median']['2014']:.2f} → {m['capital_median']['2021']:.2f}）")
fig.subplots_adjust(bottom=0.24)
save(fig, "fig3_capitals_2014_2021.png")

# 図4：販売額のシェアの変化と人口のシェアの変化
fig, ax = plt.subplots(figsize=(9, 5.6))
c = cap[cap.sales_share_chg_pct < 50]
dn = c.idx2021 < c.idx2014
ax.scatter(c[~dn].pop_share_chg_pct, c[~dn].sales_share_chg_pct, s=30, color=C[0], label="指数が上がった市", lw=0)
ax.scatter(c[dn].pop_share_chg_pct, c[dn].sales_share_chg_pct, s=30, color=C[1], label="指数が下がった市", lw=0)
lim = [min(c.pop_share_chg_pct.min(), -6) - 1, max(c.pop_share_chg_pct.max(), 4) + 1]
xs = np.linspace(lim[0], lim[1], 10)
ax.plot(xs, xs, color=INK2, lw=1, ls="--")
ax.text(xs[-1], xs[-1] - 0.5, "指数が変わらない線", ha="right", va="top", fontsize=9, color=INK2)
ax.axhline(0, color=GRID, lw=0.8); ax.axvline(0, color=GRID, lw=0.8)
ax.set_xlabel("人口の全国シェアの変化（%、2015→2020年）"); ax.set_ylabel("小売販売額の全国シェアの変化（%、2014→2021年）")
ax.legend(loc="upper left", frameon=False, fontsize=9.5)
q = m["requestion"]
finish(fig, ax, f"下がった{q['n_down']}市のうち{q['n_down_with_sales_share_down']}市は販売額のシェアが落ちていた（山口市は図の外）", grid="both")
fig.subplots_adjust(bottom=0.19)
save(fig, "fig4_share_change.png")
