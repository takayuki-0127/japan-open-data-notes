"""F275 04: 図を作る（results/ の CSV から）"""
import os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f and "Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.dpi": 150, "svg.hashsalt": "f275", "path.simplify": False})
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES, FIG = os.path.join(ROOT, "results"), os.path.join(ROOT, "figures")
os.makedirs(FIG, exist_ok=True)
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zz_f275_sqlgen as G
C = {"S1": "#d9534f", "S2": "#f0ad4e", "S3": "#337ab7"}
NAME = {"S1": "S1 コピペ型", "S2": "S2 CTE 型（定義は各ファイル）", "S3": "S3 共通ビュー型"}
CRL = {k: f"{k} {v[0]}" for k, v in G.CRS.items()}


def save(fig, name):
    fig.savefig(os.path.join(FIG, name), bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)


# 図1 直す場所の数
ed = pd.read_csv(os.path.join(RES, "A_edits.csv"))
fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), sharey=True, gridspec_kw={"wspace": 0.08})
crs = list(G.CRS)
w = 0.27
for ax, col, lab in [(axes[0], "files", "直すファイルの数"), (axes[1], "lines", "直す行の数")]:
    for i, s in enumerate(["S1", "S2", "S3"]):
        v = ed[ed["style"] == s].set_index("cr").loc[crs, col].values
        ax.barh(np.arange(len(crs)) + (i - 1) * w, v, height=w, color=C[s], label=NAME[s])
        for y, x in zip(np.arange(len(crs)) + (i - 1) * w, v):
            ax.text(x + 0.3, y, str(int(x)), va="center", fontsize=8)
    ax.set_xlabel(lab)
axes[0].set_yticks(range(len(crs))); axes[0].set_yticklabels([CRL[c] for c in crs]); axes[0].invert_yaxis()
axes[1].tick_params(labelleft=False)
axes[0].set_xlim(0, 9.2)
axes[1].legend(loc="lower right", fontsize=9, frameon=False)
axes[0].set_title("1つの変更依頼で直すファイルの数", fontsize=12)
axes[1].set_title("直す行の数（変更前後の差分）", fontsize=12)
fig.suptitle("8本のレポート × 8つの変更依頼：書き方ごとの「直す場所」", fontsize=13, y=1.01)
save(fig, "fig1_edits.png")

# 図2 テストごとに見つかった割合
b = pd.read_csv(os.path.join(RES, "B_mutants.csv"))
m = b[(b.seed == 2751) & (b.engine == "duckdb") & (b.tol == "exact") & (b.reps.astype(str) == "8") & (b.fixture == "boundary")]
grp = [("S1", "1つだけ直し忘れ"), ("S2", "1つだけ直し忘れ"), ("S1", "全部直し忘れ"), ("S3", "全部直し忘れ")]
tests = [("T1", "T1\nレポート間の照合"), ("T2", "T2\n中の整合"), ("T12", "T1＋T2"), ("T3", "T3\nR1だけ答え合わせ"), ("T4", "T4\n全レポート答え合わせ")]
fig, ax = plt.subplots(figsize=(11, 5))
for i, (s, k) in enumerate(grp):
    d = m[(m["style"] == s) & (m.kind == k)]
    vals = [d[t].mean() * 100 for t, _ in tests]
    xs = np.arange(len(tests)) + (i - 1.5) * 0.2
    ax.bar(xs, vals, width=0.2, color=C[s], alpha=1 if k == "1つだけ直し忘れ" else 0.45,
           hatch=None if k == "1つだけ直し忘れ" else "//", label=f"{NAME[s].split('（')[0]}・{k}（{len(d)}個）")
    for x, v in zip(xs, vals):
        ax.text(x, v + 1, f"{v:.0f}", ha="center", fontsize=8)
ax.set_xticks(range(len(tests))); ax.set_xticklabels([t[1] for t in tests])
ax.set_ylabel("直し忘れの変異のうち、見つかった割合（%）"); ax.set_ylim(0, 112)
ax.legend(fontsize=9, frameon=False, ncol=2, loc="upper left")
ax.set_title("直し忘れは、どのテストで見つかるか（本番データ・DuckDB・完全一致）", fontsize=12)
save(fig, "fig2_detection.png")

# 図3 S1 の「1つだけ直し忘れ」：どの変異が照合をすり抜けたか
one = m[(m["style"] == "S1") & (m.kind == "1つだけ直し忘れ")]
fig, ax = plt.subplots(figsize=(11, 5.2))
for _, r in one.iterrows():
    y = crs.index(r.cr); x = G.REPORTS.index(r.missed)
    col = "#5cb85c" if r.T12 else ("#d9534f" if r.T4 else "#333333")
    ax.scatter(x, y, s=560, color=col, marker="s", edgecolors="black" if not r.T4 else "none", linewidths=2.5)
    lab = f"{r.max_rel_pct:.1f}%" if r.max_rel_pct > 0 else (f"{r.max_pt:.1f}pt" if r.max_pt > 0 else "0")
    if r.max_pt > 0 and r.max_rel_pct > 0:
        lab = f"{r.max_rel_pct:.1f}%\n{r.max_pt:.1f}pt"
    ax.text(x, y, lab, ha="center", va="center", fontsize=7, color="white")
SHORT = {"R1": "全社", "R2": "店舗別", "R3": "部門別", "R4": "既存店前年比", "R5": "客数・客単価", "R6": "店舗×部門", "R7": "KPIまとめ", "R8": "直近月の日別"}
ax.set_xticks(range(8)); ax.set_xticklabels([f"{r}\n{SHORT[r]}" for r in G.REPORTS], fontsize=9)
ax.set_yticks(range(len(crs))); ax.set_yticklabels([CRL[c] for c in crs]); ax.invert_yaxis()
ax.set_xlim(-0.6, 7.6)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color="#5cb85c", label="T1＋T2（照合）で見つかった"), Patch(color="#d9534f", label="照合をすり抜け、T4（答え合わせ）で見つかった"),
                   Patch(facecolor="white", edgecolor="black", linewidth=2, label="黒枠：T4 でも見つからなかった")],
          fontsize=9, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=3)
ax.set_title("S1 コピペ型：直し忘れたファイル（横）と変更依頼（縦）。中の数字は、そのレポートの最大のずれ", fontsize=11)
save(fig, "fig3_s1_matrix.png")

# 図4 頑健性
rob = pd.read_csv(os.path.join(RES, "C_detection_robustness.csv"))
rm = pd.read_csv(os.path.join(RES, "D_random_miss.csv")); rmm = rm[rm.k > 0]
rows = []
r1 = rob[(rob["style"] == "S1") & (rob.kind == "1つだけ直し忘れ")]
for _, r in r1.iterrows():
    if r.engine == "duckdb" and r.tol == "exact" and str(r.reps) == "8" and r.fixture == "boundary":
        rows.append((f"乱数の種 {r.seed}", r.T12 * 100, r.T4 * 100))
for _, r in r1[r1.seed == 2751].iterrows():
    if r.engine == "sqlite":
        rows.append(("SQLite で実行", r.T12 * 100, r.T4 * 100))
    if r.tol == "0.5%":
        rows.append(("照合の許容 0.5%", r.T12 * 100, r.T4 * 100))
    if str(r.reps) == "5":
        rows.append(("レポートを5本（R1〜R5）", r.T12 * 100, r.T4 * 100))
    if r.fixture == "plain":
        rows.append(("答え合わせに境目のケースなし", r.T12 * 100, r.T4 * 100))
d = rmm[rmm["style"] == "S1"]
rows.append(("各場所を20%ずつ直し忘れ（S1）", d.T12.mean() * 100, d.T4.mean() * 100))
fig, ax = plt.subplots(figsize=(10, 5.4))
ys = np.arange(len(rows))
ax.barh(ys - 0.18, [r[1] for r in rows], height=0.36, color="#5cb85c", label="T1＋T2（照合）")
ax.barh(ys + 0.18, [r[2] for r in rows], height=0.36, color="#337ab7", label="T4（全レポートの答え合わせ）")
for y, r in zip(ys, rows):
    ax.text(r[1] + 0.8, y - 0.18, f"{r[1]:.0f}", va="center", fontsize=8); ax.text(r[2] + 0.8, y + 0.18, f"{r[2]:.0f}", va="center", fontsize=8)
ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows]); ax.invert_yaxis()
ax.axvline(70, color="gray", ls=":", lw=1); ax.axvline(90, color="gray", ls="--", lw=1)
ax.set_xlim(0, 112); ax.set_xlabel("S1 の直し忘れの変異のうち、見つかった割合（%）")
ax.legend(fontsize=9, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2)
ax.set_title("条件を変えても：照合は一部をすり抜け、答え合わせはほぼ全部を見つける", fontsize=12)
save(fig, "fig4_robustness.png")

# 図5 問い直し：共通の定義に誤りを入れると
rq = pd.read_csv(os.path.join(RES, "E_reask_bugs.csv"))
bugs = list(dict.fromkeys(rq.bug))
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
for i, s in enumerate(["S1", "S2", "S3"]):
    vals = [rq[(rq["style"] == s) & (rq.bug == bg)].T12.mean() * 100 for bg in bugs]
    nw = [rq[(rq["style"] == s) & (rq.bug == bg)].n_wrong.mean() for bg in bugs]
    xs = np.arange(len(bugs)) + (i - 1) * 0.27
    axes[0].bar(xs, vals, width=0.27, color=C[s], label=NAME[s])
    axes[1].bar(xs, nw, width=0.27, color=C[s], label=NAME[s])
    for x, v in zip(xs, vals):
        axes[0].text(x, v + 1.5, f"{v:.0f}", ha="center", fontsize=8)
    for x, v in zip(xs, nw):
        axes[1].text(x, v + 0.1, f"{v:.1f}", ha="center", fontsize=8)
nm = dict(zip(rq.bug, rq.bug_name))
for ax in axes:
    SB = {"B1": "キャンセルの\n除外漏れ", "B2": "返品の結合\nキー不足", "B3": "既存店の\n境目のずれ", "B4": "客数で明細の\nないレシートも"}
    ax.set_xticks(range(len(bugs))); ax.set_xticklabels([f"{b}\n{SB[b]}" for b in bugs], fontsize=9)
axes[0].set_ylabel("T1＋T2（照合）で見つかった割合（%）"); axes[0].set_ylim(0, 115)
axes[1].set_ylabel("誤りで数字が変わったレポートの数（平均）"); axes[1].set_ylim(0, 9)
axes[0].legend(fontsize=8, frameon=False, loc="upper right")
axes[0].set_title("1か所の書き間違いは、照合で見つかるか", fontsize=11)
axes[1].set_title("書き間違いが広がるレポートの数", fontsize=11)
fig.suptitle("問い直し：定義を1か所にまとめると、書き間違いは全レポートにそろって入り、照合では見つからない", fontsize=12, y=1.02)
save(fig, "fig5_reask.png")

print("figures ok")
