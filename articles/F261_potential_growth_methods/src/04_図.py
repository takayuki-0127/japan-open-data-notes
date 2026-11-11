"""F261 図：figures/ に PNG を6枚（図6は 05_問い直し.py のあとに描く）。"""
import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f or "NotoSansCJKjp-Regular" in f:
        fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.8, "figure.facecolor": "#fcfcfb",
                     "axes.facecolor": "#fcfcfb", "savefig.dpi": 160})
INK, INK2 = "#0b0b0b", "#52514e"
C = {"CAO": "#2a78d6", "BOJ": "#eb6834", "HP1600": "#1baf7a", "BK": "#9a9893", "CF": "#e87ba4", "HAM": "#eda100",
     "UC": "#7b5cd6", "LIN": "#3f3e3b"}
LAB = {"CAO": "内閣府（生産関数）", "BOJ": "日本銀行（生産関数）", "HP1600": "HP フィルター", "BK": "Baxter–King",
       "CF": "Christiano–Fitzgerald", "HAM": "Hamilton", "UC": "状態空間モデル", "LIN": "折れ線トレンド"}
M = json.loads((RES / "main.json").read_text())
fy = pd.read_csv(RES / "fy_pg.csv", index_col=0)
mq = pd.read_csv(RES / "methods_q.csv", header=[0, 1], index_col=0)
ep = pd.read_csv(RES / "endpoint.csv")


def save(fig, name):
    fig.savefig(FIG / name, bbox_inches="tight")
    plt.close(fig)


def qx(idx):
    return np.array([int(q[:4]) + (int(q[-1]) - 0.5) / 4 for q in idx])


# 図1：年度の潜在成長率、手法ごと
f = fy.loc[2000:2025]
fig, ax = plt.subplots(figsize=(10, 5.4))
stat = [c for c in f.columns if c not in ("CAO", "BOJ")]
ax.fill_between(f.index, f.min(axis=1), f.max(axis=1), color="#e6e5e0", alpha=0.9, lw=0, label="8つの手法の幅（最大〜最小）")
for c in stat:
    ax.plot(f.index, f[c], color=C[c], lw=1.1, alpha=0.85, label=LAB[c])
for c in ("CAO", "BOJ"):
    ax.plot(f.index, f[c], color=C[c], lw=2.8, label=LAB[c])
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xlim(2000, 2025.4)
ax.set_ylabel("潜在成長率（％、年度平均の前年比）")
rmed = M["H1"]["range_fy_median_2000_2025"]
ax.set_title(f"潜在成長率は計算の仕方でこれだけ違う：手法の間の幅は年度の中央値で {rmed:.1f}ポイント（FY2000〜FY2025）", loc="left", fontsize=12)
ax.legend(ncol=3, fontsize=8.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1))
save(fig, "fig1_pg_by_method_fy.png")

# 図2：FY2025 の値
v = pd.Series(M["H1"]["fy2025"]).sort_values()
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.hlines(range(len(v)), 0, v.values, color="#e6e5e0", lw=6)
ax.scatter(v.values, range(len(v)), s=[160 if k in ("CAO", "BOJ") else 90 for k in v.index],
           color=[C[k] for k in v.index], zorder=3)
for i, (k, x) in enumerate(v.items()):
    ax.text(x + 0.02, i, f"{x:.2f}%", va="center", fontsize=10, color=INK)
ax.set_yticks(range(len(v)), [LAB[k] for k in v.index])
ax.set_xlim(0, 1.2)
ax.set_xlabel("FY2025 の潜在成長率（％）")
ax.set_title(f"FY2025 の潜在成長率：いちばん低い {v.min():.2f}% と高い {v.max():.2f}% で {v.max()-v.min():.2f}ポイント差",
             loc="left", fontsize=12)
ax.grid(axis="y", visible=False)
save(fig, "fig2_fy2025_dotplot.png")

# 図3：GDP ギャップ。公表の2つと、統計の手法の幅
g = mq["gap"].loc["2000Q1":"2026Q2"]
x = qx(g.index)
fig, ax = plt.subplots(figsize=(10, 5.4))
st = g[[c for c in g.columns if c not in ("CAO", "BOJ")]]
ax.fill_between(x, st.min(axis=1), st.max(axis=1), color="#e6e5e0", lw=0, label="統計の手法6つの幅")
for c in ("CAO", "BOJ"):
    ax.plot(x, g[c], color=C[c], lw=2.2, label=LAB[c])
s = np.sign(g)
split = ((s > 0).sum(axis=1) > 0) & ((s < 0).sum(axis=1) > 0)
ax.scatter(x[split.values], np.full(split.sum(), -9.4), marker="|", color=INK2, s=40,
           label=f"手法の間で＋と−が割れた四半期（{split.mean()*100:.0f}%）")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylim(-10, 5)
ax.set_ylabel("GDP ギャップ（％）")
ax.set_title("GDP ギャップの符号（足りない／余っている）は、10四半期のうち6つで手法の間で割れた",
             loc="left", fontsize=12)
ax.legend(fontsize=9, frameon=False, loc="lower left", ncol=2, bbox_to_anchor=(0, 0.04))
save(fig, "fig3_gap_by_method.png")

# 図4：内閣府と日本銀行の差の内訳（年度）
by = pd.DataFrame(M["H3"]["by_fy"]).T
by.index = by.index.astype(int)
comp = [("tfp", "TFP（全要素生産性）", "#2a78d6"), ("capital", "資本", "#1baf7a"), ("hours", "労働時間", "#eda100"),
        ("employed", "就業者数", "#e87ba4")]
fig, ax = plt.subplots(figsize=(10, 5.2))
pos = np.zeros(len(by))
neg = np.zeros(len(by))
for k, lab, col in comp:
    val = by[k].values
    ax.bar(by.index, np.where(val > 0, val, 0), bottom=pos, color=col, width=0.72, label=lab)
    ax.bar(by.index, np.where(val < 0, val, 0), bottom=neg, color=col, width=0.72)
    pos += np.where(val > 0, val, 0)
    neg += np.where(val < 0, val, 0)
ax.plot(by.index, by["pg"], color=INK, marker="o", lw=1.6, label="潜在成長率の差（内閣府−日本銀行）")
ax.axhline(0, color=INK2, lw=0.8)
sh = M["H3"]["abs_share"]
ax.set_ylabel("ポイント（内閣府−日本銀行）")
ax.set_title(f"内閣府と日本銀行の差は TFP だけではない：差の大きさのうち TFP {sh['tfp']*100:.0f}%・労働時間 {sh['hours']*100:.0f}%",
             loc="left", fontsize=12)
ax.legend(fontsize=9, frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.08))
save(fig, "fig4_cao_boj_decomposition.png")

# 図5：端点（HP フィルター）。その時点の推計と、いまの推計
e = ep[ep.method == "HP1600"].copy()
xe = qx(e.ref)
fig, ax = plt.subplots(figsize=(10, 5.2))
ax.plot(xe, e.final, color=INK, lw=2.4, label="いまのデータで全期間を推計した値")
ax.plot(xe, e.pseudo, color=C["HP1600"], lw=1.4, ls="--", label="その時点までのデータだけで推計（いまのデータ）")
ax.plot(xe, e.real, color=C["BOJ"], lw=1.4, label="その時点に公表されていたデータで推計")
h = M["H4"]["by_method"]["HP1600"]
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("潜在成長率（％、前年同期比）")
ax.set_title(f"「直近の潜在成長率」はあとで書き換わる（HP フィルター、平均 {h['mad_real_vs_final']:.2f}ポイント）",
             loc="left", fontsize=12)
ax.set_xticks(range(2005, 2025, 5), [str(y) for y in range(2005, 2025, 5)])
ax.legend(fontsize=9, frameon=False, loc="lower left")
save(fig, "fig5_endpoint_hp.png")
print("ok figures 1-5")

# 図6：問い直し。データが何四半期増えると落ち着くか
rp = RES / "reask.json"
if rp.exists():
    R = json.loads(rp.read_text())
    fig, ax = plt.subplots(figsize=(10, 5.0))
    for k in ("HP1600", "UC", "CF", "HAM"):
        d = R["by_method"][k]["mad_by_h"]
        hh = sorted(int(i) for i in d)
        ax.plot(hh, [d[str(i)] for i in hh], marker="o", ms=4, color=C[k], lw=1.8, label=LAB[k])
    ax.axhline(0.2, color=INK2, lw=0.9, ls=":")
    ax.text(20, 0.21, "0.2ポイント", ha="right", fontsize=9, color=INK2)
    ax.set_xlabel("その時点のあとに増えたデータ（四半期）")
    ax.set_ylabel("いまの推計との差（平均、ポイント）")
    ax.set_xticks(range(0, 21, 4))
    hp = R["by_method"]["HP1600"]
    ax.set_title(f"直近の推計が落ち着くまで：HP フィルターは平均の差が 0.2ポイントになるのに {hp['first_h_mad_le_0.2']}四半期",
                 loc="left", fontsize=12)
    ax.legend(fontsize=9, frameon=False)
    ax.set_ylim(0, None)
    save(fig, "fig6_reask_convergence.png")
    print("ok figure 6")
