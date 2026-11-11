"""04 図：6枚。"""
import os, json
import numpy as np
R0 = lambda x: int(np.floor(x + 0.5))
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if os.path.exists(f):
        fm.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
HERE = os.path.dirname(__file__); R = os.path.join(HERE, "..", "results"); F = os.path.join(HERE, "..", "figures")
os.makedirs(F, exist_ok=True)
main = json.load(open(os.path.join(R, "main.json"))); rr = json.load(open(os.path.join(R, "robust_reask.json")))
M = pd.read_csv(os.path.join(R, "A_measure.csv"))
C1, C2, C3 = "#4C72B0", "#DD8452", "#55A868"

# 図1 読む量
fig, axs = plt.subplots(1, 2, figsize=(9, 4))
for ax, reader, reps, cols in [(axs[0], "経営", ["C", "E"], [C1, C2]), (axs[1], "店長", ["C", "S"], [C1, C3])]:
    for i, mode in enumerate(["linear", "jump"]):
        d = M[(M.reader == reader) & (M["mode"] == mode)].dropna(subset=["cost"]).groupby("report").cost.median()
        for j, r in enumerate(reps):
            ax.bar(j * 3 + i, d[r], color=cols[j], alpha=1 if i == 0 else 0.5)
            ax.text(j * 3 + i, d[r], f"{d[r]:,.0f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks([0.5, 3.5]); ax.set_xticklabels([f"{r}（{'共通版' if r == 'C' else '経営向け' if r == 'E' else '現場向け'}）" for r in reps])
    ax.set_title(f"{reader}の8問に答えるまでに読む文字数（中央値）", fontsize=10, loc="left")
    ax.set_ylabel("文字数")
axs[0].text(0.98, 0.95, "濃い：上から順に読む\n薄い：見出しから飛ぶ", transform=axs[0].transAxes, va="top", ha="right", fontsize=8)
fig.suptitle(f"共通版では、経営は約{main['exec_cost_ratio_C_over_E']:.0f}倍、店長は約{main['store_cost_ratio_C_over_S']:.0f}倍の文字を読む", fontsize=12)
fig.tight_layout(); fig.savefig(os.path.join(F, "fig1_read_cost.png"), dpi=150); plt.close()

# 図2 切ったときに答えられる問い
fig, axs = plt.subplots(1, 2, figsize=(9, 4))
caps = [1000, 1500, 2500]
for ax, reader, reps, cols in [(axs[0], "経営", ["C", "E"], [C1, C2]), (axs[1], "店長", ["C", "S"], [C1, C3])]:
    for r, c in zip(reps, cols):
        y = [main[f"{'exec' if reader == '経営' else 'store'}_ans{k}"][r] * 100 for k in caps]
        ax.plot(caps, y, marker="o", color=c, label=f"{r}（{'共通版' if r == 'C' else '経営向け' if r == 'E' else '現場向け'}）")
        for x, yy in zip(caps, y):
            ax.text(x, yy + 2, f"{R0(yy)}%", ha="center", fontsize=8, color=c)
    ax.axvline(1500, color="gray", ls=":", lw=1)
    ax.set_ylim(0, 110); ax.set_xlabel("先頭から切る文字数"); ax.set_ylabel("答えが残る問いの割合（%）")
    ax.set_title(f"{reader}の問い", fontsize=10, loc="left"); ax.legend(fontsize=8, loc="lower right")
fig.suptitle(f"1,500字（点線）で切ると、共通版で答えが残るのは経営の問いの{R0(main['exec_ans1500']['C']*100)}%、店長の問いの{R0(main['store_ans1500']['C']*100)}%", fontsize=11)
fig.tight_layout(); fig.savefig(os.path.join(F, "fig2_cut_coverage.png"), dpi=150); plt.close()

# 図3 店の並びと1,500字で答えられる割合（共通版）
fig, ax = plt.subplots(figsize=(8, 3.6))
d = main["store_ans1500_C_by_store"]
ax.bar(list(d.keys()), [x * 100 for x in d.values()], color=C1)
ax.set_ylim(0, 100); ax.set_ylabel("答えが残る問いの割合（%）")
ax.set_title("共通版を1,500字で切ったとき、店長の8問のうち答えが残る割合（店ごと、12か月の平均）", fontsize=10, loc="left")
ax.text(0.99, 0.95, "表の後ろにある店（S09〜S12＝規模S）ほど、切られて答えが消える", transform=ax.transAxes, ha="right", va="top", fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(F, "fig3_store_order.png"), dpi=150); plt.close()

# 図4 店の数を変える
B = pd.DataFrame(rr["by_nstores"])
fig, axs = plt.subplots(1, 2, figsize=(9, 3.8))
n = [6, 12, 24]
axs[0].plot(n, B.exec_ratio, marker="o", color=C2, label="経営：C÷E")
axs[0].plot(n, B.store_ratio, marker="o", color=C3, label="店長：C÷S")
for x, a, b in zip(n, B.exec_ratio, B.store_ratio):
    axs[0].text(x, a + 0.6, f"{a:.1f}倍", ha="center", fontsize=8, color=C2); axs[0].text(x, b + 0.6, f"{b:.1f}倍", ha="center", fontsize=8, color=C3)
axs[0].axhline(3, color="gray", ls=":", lw=1); axs[0].set_ylim(0, max(B.store_ratio) * 1.15); axs[0].set_xticks(n); axs[0].set_xlabel("店の数"); axs[0].set_ylabel("読む文字数の比")
axs[0].set_title("読む量の比（点線はH1の基準3倍）", fontsize=10, loc="left"); axs[0].legend(fontsize=8)
axs[1].plot(n, B.store_ans1500_C * 100, marker="o", color=C1, label="C（共通版）")
axs[1].plot(n, B.store_ans1500_S * 100, marker="o", color=C3, label="S（現場向け）")
for x, a in zip(n, B.store_ans1500_C * 100):
    axs[1].text(x, a + 3, f"{a:.0f}%", ha="center", fontsize=8, color=C1)
axs[1].axhline(50, color="gray", ls=":", lw=1); axs[1].set_ylim(0, 110); axs[1].set_xticks(n); axs[1].set_xlabel("店の数")
axs[1].set_ylabel("%"); axs[1].set_title("1,500字で店長の問いに答えられる割合（点線はH2の基準50%）", fontsize=10, loc="left"); axs[1].legend(fontsize=8)
fig.suptitle("店が増えるほど、共通版の不利は大きくなる", fontsize=12)
fig.tight_layout(); fig.savefig(os.path.join(F, "fig4_nstores.png"), dpi=150); plt.close()

# 図5 丸めの食い違い
Rr = pd.read_csv(os.path.join(R, "B_rounding.csv")); S = pd.read_csv(os.path.join(R, "C_rounding_seeds.csv"))
fig, axs = plt.subplots(1, 2, figsize=(9.5, 3.8), gridspec_kw=dict(width_ratios=[1.6, 1]))
mat = Rr[["dept_oku", "store_mil", "share_pct"]].T.astype(int).values
axs[0].imshow(mat, cmap="Oranges", vmin=0, vmax=1.4, aspect="auto")
axs[0].set_yticks(range(3)); axs[0].set_yticklabels(["部門の合計（億円・小数1桁）", "店の合計（百万円・整数）", "部門の構成比（%・整数）"], fontsize=8)
axs[0].set_xticks(range(12)); axs[0].set_xticklabels([m[2:] for m in Rr.month], fontsize=7, rotation=45)
for j, (a, b, c) in enumerate(zip(Rr.dept_gap, Rr.store_gap, Rr.share_gap)):
    for i, gap in enumerate([a, b, c]):
        if abs(gap) > 1e-9:
            axs[0].text(j, i, f"{gap:+g}", ha="center", va="center", fontsize=7)
axs[0].set_title("別々に丸めて合計が合わない表（色つき、数字は全社−合計）", fontsize=9, loc="left")
axs[1].hist(S["any"], bins=np.arange(-0.5, 13.5, 1), color=C2)
axs[1].axvline(3.6, color="gray", ls=":", lw=1)
axs[1].set_xlabel("12か月のうち合わない月の数"); axs[1].set_ylabel("乱数の種の数")
axs[1].set_title("乱数の種20通り（点線は3割）", fontsize=9, loc="left")
fig.suptitle(f"別々に丸めると、12か月中{main['rounding_months_any']}か月で合計が合わない。最大剰余法なら0", fontsize=11)
fig.tight_layout(); fig.savefig(os.path.join(F, "fig5_rounding.png"), dpi=150); plt.close()

# 図6 問い直し
h = rr["reask"]["hit_rate"]; nf = rr["reask"]["null_flag_rate"]
fig, ax = plt.subplots(figsize=(8, 3.8))
lab = list(h.keys()); val = [h[k] * 100 for k in lab]
ax.barh(lab[::-1], val[::-1], color=[C2 if v > 50 else "#999999" for v in val[::-1]])
ax.axvline(nf * 100, color="gray", ls=":", lw=1)
ax.text(nf * 100 + 1, 3.45, f"点線：動きのない店が幅の外になる割合 {nf*100:.0f}%", fontsize=8, color="gray")
for i, v in enumerate(val[::-1]):
    ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=8)
ax.set_xlim(0, 110); ax.set_xlabel("動きの後の月のうち、経営向けの「幅の外」に出た割合（%、乱数の種20通り）")
ax.set_title("入れておいた本当の動きは、経営向けの例外の欄に出たか", fontsize=10, loc="left")
fig.tight_layout(); fig.savefig(os.path.join(F, "fig6_reask.png"), dpi=150); plt.close()
print("ok")
