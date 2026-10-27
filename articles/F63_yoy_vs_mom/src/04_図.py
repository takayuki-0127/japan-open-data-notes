"""04 図"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, IND, COL, cycle_table

ind = pd.read_csv(DATA / "indicators.csv", parse_dates=["date"])
cyc = cycle_table()


def tp_lines(ax, start, end):
    for _, r in cyc.iterrows():
        if start <= r.date <= end:
            ax.axvline(r.date, color="#202124", lw=1, ls="--")
            ax.text(r.date, ax.get_ylim()[1], " 山" if r.type == "peak" else " 谷", va="top", ha="left", fontsize=9)


# 1. 例：2つの局面で4つの見方を並べる
fig, axes = plt.subplots(2, 1, figsize=(9, 7.5))
for ax, (name, s, e, title) in zip(axes, [
        ("鉱工業生産", "2017-07-01", "2021-06-01", "鉱工業生産（2018年10月の山・2020年5月の谷）"),
        ("景気動向指数（CI一致）", "2007-01-01", "2010-12-01", "景気動向指数 CI一致（2008年2月の山・2009年3月の谷）")]):
    d = ind[(ind.series == name) & (ind.date >= s) & (ind.date <= e)].set_index("date")
    for i in IND:
        ax.plot(d.index, d[i], color=COL[i], lw=2.2 if i in ("前年比", "3か月前比") else 1.2, label=i)
    ax.axhline(0, color="#5f6368", lw=0.8)
    lim = np.nanpercentile(np.abs(d[IND].values), 97) * 1.15
    ax.set_ylim(-lim, lim)
    tp_lines(ax, pd.Timestamp(s), pd.Timestamp(e))
    ax.set_title(title, fontsize=11, loc="left")
    ax.set_ylabel("%（はみ出た値は切っている）")
axes[0].legend(ncol=4, fontsize=9, loc="lower left")
fig.tight_layout()
fig.savefig(FIG / "f63_example.png", dpi=150)
plt.close(fig)

# 2. 転換点からサインが出るまでの遅れ（k=2）
lags = pd.read_csv(RES / "detection_lags.csv")
l = lags[lags.k == 2]
fig, ax = plt.subplots(figsize=(9, 5))
rng = np.random.default_rng(1)
for j, i in enumerate(IND):
    for t, off, mk in [("peak", -0.17, "v"), ("trough", 0.17, "^")]:
        v = l[(l["見方"] == i) & (l.type == t)]["遅れ"].dropna()
        x = j + off + rng.uniform(-0.07, 0.07, len(v))
        ax.scatter(x, v, s=18, color=COL[i], alpha=0.55, marker=mk)
        ax.plot([j + off - 0.12, j + off + 0.12], [v.median()] * 2, color="#202124", lw=2.5)
        ax.text(j + off, v.median() + 0.4, f"{v.median():.0f}", ha="center", fontsize=9)
ax.set_xticks(range(len(IND)))
ax.set_xticklabels(IND)
ax.set_ylabel("転換点から何か月後に分かったか")
ax.set_title("2か月続けて向きが変わったら「転換」と判定（▼山 ▲谷、横線は中央値。5系列×62の転換点）", fontsize=10, loc="left")
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig(FIG / "f63_lags.png", dpi=150)
plt.close(fig)

# 3. 早さと空振りのトレードオフ（実データとシミュレーション）
fr = pd.read_csv(RES / "frontier_real.csv")
sim = pd.read_csv(RES / "simulation_summary.csv")
sim = sim[sim["ノイズ倍率"] == 1.0]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=False)
for ax, df, xcol, ycol, title in [(axes[0], fr, "空振り（10年あたり）", "遅れの平均", "実データ（5系列）"),
                                  (axes[1], sim, "空振り", "遅れ", "シミュレーション（答えが分かっている人工データ）")]:
    for i in IND:
        d = df[df["見方"] == i].sort_values("k")
        ax.plot(d[xcol], d[ycol], "-o", color=COL[i], label=i, lw=2)
        for _, r in d.iterrows():
            ax.annotate(f"k={int(r.k)}", (r[xcol], r[ycol]), textcoords="offset points", xytext=(4, 3), fontsize=7, color=COL[i])
    ax.set_xlabel("空振り（10年あたりの回数）")
    ax.set_ylabel("遅れの平均（か月）")
    ax.set_title(title, fontsize=10, loc="left")
    ax.grid(alpha=0.3)
axes[0].legend(fontsize=9)
fig.suptitle("左下ほど良い（早くて空振りが少ない）。k＝何か月続いたら判定するか", fontsize=10, x=0.01, ha="left")
fig.tight_layout()
fig.savefig(FIG / "f63_frontier.png", dpi=150)
plt.close(fig)

# 4. 何か月前の動きを映しているか（相互相関）
prof = pd.read_csv(RES / "cross_correlation_profile.csv")
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
for ax, name in zip(axes, ["鉱工業生産", "景気動向指数（CI一致）"]):
    p = prof[prof.series == name]
    for i in IND:
        q = p[p["見方"] == i].sort_values("h")
        ax.plot(-q.h, q["相関"], "-o", ms=3, color=COL[i], label=i, lw=2)
    ax.set_xlabel("何か月前の「本当の動き」との相関か")
    ax.set_title(name, fontsize=10, loc="left")
    ax.invert_xaxis()
    ax.grid(alpha=0.3)
axes[0].set_ylabel("「本当の動き」との相関")
fig.suptitle("本当の動き＝あとから計算した中心化12か月移動平均の前月比", fontsize=9, x=0.01, ha="left")
axes[0].legend(fontsize=9)
fig.tight_layout()
fig.savefig(FIG / "f63_xcorr.png", dpi=150)
plt.close(fig)

# 5. ノイズ：1年に何回、符号が変わるか
fl = pd.read_csv(RES / "sign_flips.csv")
ser = fl.series.unique().tolist()
fig, ax = plt.subplots(figsize=(10, 4.5))
w = 0.2
for j, i in enumerate(IND):
    v = fl[fl["見方"] == i].set_index("series").reindex(ser)["符号が変わった回数（年あたり）"]
    ax.bar(np.arange(len(ser)) + (j - 1.5) * w, v, w, color=COL[i], label=i)
ax.set_xticks(range(len(ser)))
ax.set_xticklabels(ser, fontsize=9)
ax.set_ylabel("プラス・マイナスが入れ替わった回数（1年あたり）")
ax.legend(fontsize=9, ncol=4)
ax.grid(axis="y", alpha=0.3)
fig.tight_layout()
fig.savefig(FIG / "f63_noise.png", dpi=150)
plt.close(fig)

# 6. 頑健性
rob = pd.read_csv(RES / "robustness.csv")
rob = rob[rob["見方"].isin(IND)]
sets = rob["設定"].unique().tolist()
sets = [s for s in sets if not s.startswith("参考")]
fig, axes = plt.subplots(1, 2, figsize=(11, 6), sharey=True)
for ax, col, lab in [(axes[0], "遅れの中央値", "遅れの中央値（か月）"), (axes[1], "空振り（10年あたり）", "空振り（10年あたり）")]:
    for j, i in enumerate(IND):
        d = rob[rob["見方"] == i].set_index("設定").reindex(sets)[col]
        ax.scatter(d.values, np.arange(len(sets)) + (j - 1.5) * 0.15, color=COL[i], s=22, label=i)
    ax.set_xlabel(lab)
    ax.grid(alpha=0.3)
axes[0].set_yticks(range(len(sets)))
axes[0].set_yticklabels(sets, fontsize=8)
axes[0].invert_yaxis()
axes[1].legend(fontsize=8, loc="lower right")
fig.tight_layout()
fig.savefig(FIG / "f63_robust.png", dpi=150)
plt.close(fig)
print("ok")
