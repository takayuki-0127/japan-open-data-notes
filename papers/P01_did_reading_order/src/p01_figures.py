"""P01 の図（results/ と data/ から作る）。使い方: cd src && python p01_figures.py"""
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Noto Sans CJK JP"
ROOT = Path(__file__).resolve().parents[1]
RES, FIG, DATA = ROOT / "results", ROOT / "figures", ROOT / "data"
FIG.mkdir(exist_ok=True)
C = {"TWFE": "#b5452b", "CS": "#1f5f8b", "SA": "#2e7d4f", "truth": "#333333"}


def clean(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


# 図1：場面S2の本当の効果と、Bacon の分解（2×2 の推定と重み）
d = pd.read_csv(DATA / "sim_S2_one.csv")
b = pd.read_csv(RES / "bacon_S2_育つ.csv")
fig, axs = plt.subplots(1, 2, figsize=(11, 4.4), dpi=120)
for g, col in zip([6, 11, 16], ["#1f5f8b", "#6b4c9a", "#c0692b"]):
    t = np.arange(1, 21)
    axs[0].plot(t, [0.2 * (tt - g + 1) if tt >= g else 0 for tt in t], color=col, lw=2, label=f"{g}期目に始まる組")
axs[0].plot(np.arange(1, 21), np.zeros(20), color="#999", ls="--", label="処置されない組")
axs[0].set_xlabel("時点"); axs[0].set_ylabel("本当の効果"); axs[0].set_title("場面S2：効果は始まってから毎期 0.2 ずつ育つ")
axs[0].legend(fontsize=8); clean(axs[0])
kinds = {"処置 vs 処置されない": "#1f5f8b", "早い組 vs まだの組": "#2e7d4f", "遅い組 vs すでに処置された組": "#b5452b"}
for k, col in kinds.items():
    s = b[b.kind == k]
    axs[1].scatter(s.w, s.est, s=60, color=col, label=k, edgecolor="white")
axs[1].axhline(1.2667, color="#333", ls="--", lw=1)
axs[1].text(0.125, 1.31, "本当の効果の平均 1.27", fontsize=8)
axs[1].axhline((b.w * b.est).sum(), color="#b5452b", ls=":", lw=1)
axs[1].text(0.125, (b.w * b.est).sum() + 0.05, f"TWFE = 重み付き平均 {(b.w * b.est).sum():.2f}", fontsize=8, color="#b5452b")
axs[1].set_xlabel("TWFE の中での重み"); axs[1].set_ylabel("2×2 の差の差の推定")
axs[1].set_title("Goodman-Bacon の分解：すでに処置された組を\n比較に使う組み合わせが、マイナスに引っぱる", fontsize=10)
axs[1].legend(fontsize=8, loc="lower right"); clean(axs[1])
fig.tight_layout(); fig.savefig(FIG / "p01_01_bacon.png"); plt.close(fig)

# 図2：5つの場面の推定（500回の平均と、本当の値）
s = pd.read_csv(RES / "sim_summary.csv")
sims = pd.read_csv(RES / "sim_reps.csv")
scn = list(s.scenario.unique())
fig, ax = plt.subplots(figsize=(11, 4.8), dpi=120)
for i, sc in enumerate(scn):
    g = sims[sims.scenario == sc]
    for j, est in enumerate(["TWFE", "CS", "SA"]):
        v = (g[est] - g.truth).dropna()
        if v.empty:
            continue
        x = i + (j - 1) * 0.25
        ax.boxplot(v, positions=[x], widths=0.2, patch_artist=True, showfliers=False,
                   boxprops=dict(facecolor=C[est], alpha=.75), medianprops=dict(color="white"))
ax.axhline(0, color="#333", lw=1)
ax.set_xticks(range(len(scn)), [x.replace("_", "\n", 1).replace("_", "・") for x in scn], fontsize=9)
ax.set_ylabel("推定 − 本当の値（500回）")
for est in ["TWFE", "CS", "SA"]:
    ax.plot([], [], color=C[est], lw=8, alpha=.75, label={"TWFE": "TWFE", "CS": "Callaway–Sant'Anna", "SA": "Sun–Abraham"}[est])
ax.legend(fontsize=9, loc="lower left")
ax.set_title("効果が育つと TWFE は半分近く小さく出る。新しい推定は、前提が崩れた場面（S4）と比較の組がない場面（S5）では外れる", fontsize=10)
clean(ax); fig.tight_layout(); fig.savefig(FIG / "p01_02_bias.png"); plt.close(fig)

# 図3：イベントスタディ（S2・1回分）
ev = pd.read_csv(RES / "event_study_S2.csv").set_index("e")
fig, ax = plt.subplots(figsize=(10, 4.6), dpi=120)
ax.plot(ev.index, ev.truth, color=C["truth"], lw=2, ls="--", label="本当の効果")
ax.plot(ev.index, ev.twfe_trimmed, "o-", color=C["TWFE"], label="TWFE（相対時点 −5〜+5 だけダミー）")
ax.plot(ev.index, ev.sun_abraham, "s-", color=C["SA"], label="Sun–Abraham")
ax.axvline(-0.5, color="#bbb", lw=1); ax.axhline(0, color="#bbb", lw=1)
ax.set_xlabel("処置が始まってからの時点（−1 が基準）"); ax.set_ylabel("推定")
ax.set_title("効果が育つだけで、切ったイベントスタディは「事前に下がっていた」ように見え、処置後も小さく出る", fontsize=10)
ax.legend(fontsize=9); clean(ax)
fig.tight_layout(); fig.savefig(FIG / "p01_03_event.png"); plt.close(fig)

# 図4：Rambachan–Roth（簡略版）の感度。シミュレーション S4 と実データ
r4 = pd.read_csv(RES / "rr_S4.csv")
rr = pd.read_csv(RES / "rr_real.csv")
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), dpi=120)
for ax, t, title, tv in ((axs[0], r4, "シミュレーション S4（本当の効果 1.0）", 1.0), (axs[1], rr, "実データ：F296 設計B の就業率（%pt）", None)):
    ax.fill_between(t.Mbar, t.lo, t.hi, color="#1f5f8b", alpha=.25, label="処置直後の効果の区間")
    ax.axhline(0, color="#333", lw=1)
    if tv is not None:
        ax.axhline(tv, color="#2e7d4f", ls="--", lw=1, label="本当の効果")
    ax.set_xlabel("M̄：処置後のずれが、事前の1期ごとの動きの最大の何倍までありうるか")
    ax.set_title(title, fontsize=10); ax.legend(fontsize=8); clean(ax)
axs[0].set_ylabel("効果（区間）")
fig.suptitle("前提のずれをどこまで許すと「効果がある」と言えなくなるか（簡略版）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "p01_04_rr.png"); plt.close(fig)

# 図5：実データのイベントスタディ（CS は1期ずつの差、SA は −1 との差）
er = pd.read_csv(RES / "event_study_real.csv").set_index("e").loc[-9:1]
fig, ax = plt.subplots(figsize=(9, 4.2), dpi=120)
ax.plot(er.index, er.cs_event, "o-", color=C["CS"], label="Callaway–Sant'Anna（各期は1期前との差）")
ax.plot(er.index, er.sa_event, "s-", color=C["SA"], label="Sun–Abraham（各期は −1 との差）")
ax.axvline(-0.5, color="#bbb", lw=1); ax.axhline(0, color="#bbb", lw=1)
ax.set_xlabel("処置が始まってからの年（2024・2025年に始まった9県と、始まっていない38県）"); ax.set_ylabel("就業率の差（%pt）")
ax.set_title("実データ：処置の前年にすでに −0.70%pt 動いていて、処置後の −0.70 と区別できない", fontsize=10)
ax.legend(fontsize=9); clean(ax)
fig.tight_layout(); fig.savefig(FIG / "p01_05_real_event.png"); plt.close(fig)
print("ok")
