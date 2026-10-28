"""F102 図"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, FIG, setup_font

plt = setup_font()
S = json.load(open(RES / "summary.json"))
reg = pd.read_csv(RES / "regimes.csv", parse_dates=["month"])
yoy = pd.read_csv(DATA / "yoy_for_figures.csv", index_col=0, parse_dates=True)
grid = pd.read_csv(RES / "threshold_grid.csv")
LRb = pd.read_csv(RES / "supLR_bootstrap.csv")["LR_boot"]
irf = pd.read_csv(RES / "irf_regimes.csv")
LP = pd.read_csv(RES / "local_projections.csv")
ga = pd.read_csv(RES / "girf_summary_all.csv")
rob = pd.read_csv(RES / "robustness.csv")
g = S["gamma"]
C_HI, C_LO, C_LIN = "#c0392b", "#2c6fbb", "#555555"


def shade(ax):
    on = reg["high"].values == 1
    m = reg["month"].values
    i = 0
    while i < len(on):
        if on[i]:
            j = i
            while j + 1 < len(on) and on[j + 1]:
                j += 1
            ax.axvspan(m[i], m[j] + np.timedelta64(31, "D"), color=C_HI, alpha=0.15, lw=0)
            i = j + 1
        else:
            i += 1


# 図1 局面の時期
fig, ax = plt.subplots(2, 1, figsize=(10, 6.4), sharex=True)
ax[0].plot(reg["month"], reg["z12"], color="#333", lw=1)
ax[0].axhline(g, color=C_HI, ls="--", lw=1)
ax[0].axhline(0, color="#999", lw=0.6)
ax[0].text(reg["month"].iloc[40], g + 9, f"しきい値 +{g:.1f}%", color=C_HI, fontsize=10, bbox=dict(fc="white", ec="none", alpha=0.85))
shade(ax[0])
ax[0].set_ylabel("%")
ax[0].set_title("ドル円の過去12か月の変化（＋が円安）と「大きな円安」の局面（赤い帯）", fontsize=12, loc="left")
y = yoy.loc[reg["month"].min():]
ax[1].plot(y.index, y["cpi_adj"], color="#333", lw=1.2, label="消費者物価（生鮮除く、消費税などの段差を除く）")
ax[1].axhline(0, color="#999", lw=0.6)
shade(ax[1])
ax[1].set_ylabel("前年比（%）")
ax[1].legend(loc="upper right", fontsize=9, frameon=False)
ax[1].set_title("消費者物価の前年比", fontsize=12, loc="left")
fig.text(0.01, 0.005, "出典：日本銀行 時系列統計データ、総務省 消費者物価指数。季節性と特殊な月を除いた前月比から作成", fontsize=8, color="#666")
fig.tight_layout(rect=(0, 0.02, 1, 1))
fig.savefig(FIG / "fig1_regimes.png", dpi=150)
plt.close(fig)

# 図2 しきい値の探索と線形との比較
T = S["n"]
ld_lin = S["supLR"] / T + grid["logdet"].min()
lr = T * (ld_lin - grid["logdet"])
crit = np.percentile(LRb, 95)
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(grid["gamma"], lr, color="#333", lw=1.4, marker="o", ms=2.5)
ax.axhline(crit, color="#888", ls="--", lw=1)
ax.text(grid["gamma"].min(), crit + 0.8, f"線形と同じでも出る大きさ（上位5%）：{crit:.1f}", fontsize=9, color="#666")
ax.axvline(g, color=C_HI, ls=":", lw=1)
ax.annotate(f"いちばん当てはまるしきい値 +{g:.1f}%\n（線形との差 {S['supLR']:.1f}、p={S['supLR_p']:.3f}）",
            xy=(g, lr.max()), xytext=(g + 4, lr.max() - 6), fontsize=10, color=C_HI,
            arrowprops=dict(arrowstyle="->", color=C_HI))
ax.set_xlabel("しきい値（ドル円の過去12か月の変化、%）")
ax.set_ylabel("線形の VAR より当てはまりが良くなる分（LR）")
ax.set_title("2つの局面に分けると、当てはまりは線形より良くなる", fontsize=12, loc="left")
fig.tight_layout()
fig.savefig(FIG / "fig2_threshold_search.png", dpi=150)
plt.close(fig)

# 図3 局面ごとの反応
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6), sharex=True)
for ax, v, tt in zip(axs, ["ppi", "cpi"], ["国内企業物価", "消費者物価（生鮮除く）"]):
    d = irf[irf["var"] == v]
    ax.fill_between(d["h"], d["high_lo"], d["high_hi"], color=C_HI, alpha=0.15)
    ax.fill_between(d["h"], d["low_lo"], d["low_hi"], color=C_LO, alpha=0.15)
    ax.plot(d["h"], d["high"], color=C_HI, lw=2, label=f"大きな円安の局面（過去12か月で+{g:.0f}%超）")
    ax.plot(d["h"], d["low"], color=C_LO, lw=2, label="それ以外")
    ax.plot(d["h"], d["linear"], color=C_LIN, lw=1, ls="--", label="分けない（線形 VAR）")
    ax.axhline(0, color="#999", lw=0.6)
    ax.set_title(tt, fontsize=12, loc="left")
    ax.set_xlabel("ショックからの月数")
axs[0].set_ylabel("累積の反応（%）")
axs[1].legend(fontsize=9, frameon=False, loc="upper left")
fig.suptitle("ドル円が当月1%円安になったときの反応（帯は90%区間）", fontsize=12, x=0.01, ha="left")
fig.tight_layout()
fig.savefig(FIG / "fig3_irf_by_regime.png", dpi=150)
plt.close(fig)

# 図4 手法をまたいだ比較（24か月後の消費者物価）
rows = []
d = irf[(irf["var"] == "cpi") & (irf["h"] == 24)].iloc[0]
rows.append(("閾値 VAR：大きな円安の局面", d["high"], d["high_lo"], d["high_hi"], C_HI))
rows.append(("閾値 VAR：それ以外", d["low"], d["low_lo"], d["low_hi"], C_LO))
lab = {"state": ("局所射影：大きな円安の局面", "局所射影：それ以外"),
       "size": ("局所射影：その月の動きが大きい（上位20%）", "局所射影：その月の動きが小さい"),
       "sign": ("局所射影：円安の月", "局所射影：円高の月")}
for sp, (la, lb) in lab.items():
    r = LP[(LP.split == sp) & (LP.h == 24) & (LP["var"] == "cpi")].iloc[0]
    rows.append((la, r["a"], r["a"] - 1.645 * r["a_se"], r["a"] + 1.645 * r["a_se"], C_HI))
    rows.append((lb, r["b"], r["b"] - 1.645 * r["b_se"], r["b"] + 1.645 * r["b_se"], C_LO))
fig, axs = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw=dict(width_ratios=[1.6, 1]))
ax = axs[0]
for i, (nm, v, lo, hi, c) in enumerate(rows[::-1]):
    ax.plot([lo, hi], [i, i], color=c, lw=2, alpha=0.6)
    ax.plot(v, i, "o", color=c)
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([r[0] for r in rows[::-1]], fontsize=9)
ax.axvline(0, color="#999", lw=0.6)
ax.set_xlabel("24か月後までの消費者物価の上昇（%、当月1%の円安あたり）")
ax.set_title("分け方を変えても、区間は大きく重なる（線は90%区間）", fontsize=11, loc="left")
ax = axs[1]
ga = ga.sort_values("delta")
x = np.arange(len(ga))
ax.bar(x, ga["cpi24"] / ga["fx0"], color=[C_LO if v < 0 else C_HI for v in ga["delta"]])
ax.set_xticks(x)
ax.set_xticklabels([f"{int(v):+d}σ" for v in ga["delta"]])
ax.set_xlabel("ドル円のショックの大きさ（標準偏差、−は円高）")
ax.set_ylabel("当月1%あたりの消費者物価の反応（%）")
ax.set_title("ショックの大きさを変えた GIRF（24か月後）", fontsize=11, loc="left")
for xi, v in zip(x, ga["cpi24"] / ga["fx0"]):
    ax.text(xi, v + 0.001, f"{v:.3f}", ha="center", fontsize=9)
fig.tight_layout()
fig.savefig(FIG / "fig4_methods_compare.png", dpi=150)
plt.close(fig)

# 図5 頑健性
fig, ax = plt.subplots(figsize=(10, 0.42 * len(rob) + 1.4))
yy = np.arange(len(rob))[::-1]
for yv, (_, r) in zip(yy, rob.iterrows()):
    ax.plot([r["pt24_high_lo"], r["pt24_high_hi"]], [yv + 0.15] * 2, color=C_HI, lw=2, alpha=0.5)
    ax.plot(r["pt24_high"], yv + 0.15, "o", color=C_HI, ms=5)
    ax.plot([r["pt24_low_lo"], r["pt24_low_hi"]], [yv - 0.15] * 2, color=C_LO, lw=2, alpha=0.5)
    ax.plot(r["pt24_low"], yv - 0.15, "o", color=C_LO, ms=5)
    ax.text(ax.get_xlim()[1] if False else 0.205, yv, f"上の局面 {r['share_high']*100:.0f}%", fontsize=8, va="center", color="#666")
ax.set_yticks(yy)
ax.set_yticklabels(rob["variant"], fontsize=9)
ax.axvline(0, color="#999", lw=0.6)
ax.set_xlim(-0.12, 0.25)
ax.plot([], [], "o", color=C_HI, label="しきい値より上の局面")
ax.plot([], [], "o", color=C_LO, label="しきい値より下の局面")
ax.legend(fontsize=9, frameon=False, loc="lower right", bbox_to_anchor=(1, 1.0), ncol=2)
ax.set_xlabel("パススルー率（24か月後の消費者物価の累積の反応 ÷ ドル円の累積の反応、線は95%区間）")
ax.set_title("設定を変えたときのパススルー率", fontsize=12, loc="left")
fig.tight_layout()
fig.savefig(FIG / "fig5_robustness.png", dpi=150)
plt.close(fig)
print("figures done")
