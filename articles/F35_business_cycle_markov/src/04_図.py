"""04 図"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from common import DATA, RES, FIG, episodes

FIG.mkdir(exist_ok=True)
d = pd.read_csv(DATA / "monthly.csv", parse_dates=["month"]).set_index("month")
pm = pd.read_csv(RES / "probs_main.csv", index_col=0, parse_dates=True)
pv = pd.read_csv(RES / "probs_variants.csv", index_col=0, parse_dates=True)
acc = pd.read_csv(RES / "accuracy_models.csv")
tp = pd.read_csv(RES / "turning_points_main.csv")
rt_path = RES / "realtime_probs.csv"
rt = pd.read_csv(rt_path, index_col=0, parse_dates=True).iloc[:, 0] if rt_path.exists() else None
GRAY = "#d9d9d9"; BLUE = "#2b6cb0"; RED = "#c53030"; ORANGE = "#dd6b20"


def shade(ax, start="1985-01"):
    rec = d["recession"][start:]
    for s, e in episodes(rec):
        ax.axvspan(s, e + pd.offsets.MonthEnd(0), color=GRAY, lw=0, zorder=0)


def fmt(ax):
    ax.xaxis.set_major_locator(mdates.YearLocator(5))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.spines[["top", "right"]].set_visible(False)


# 1. CI一致指数と景気基準日付
fig, axs = plt.subplots(2, 1, figsize=(9, 5.6), sharex=True, gridspec_kw={"height_ratios": [1.3, 1]})
x = d["1985-01":]
axs[0].plot(x.index, x["ci_level"], color=BLUE, lw=1.4); shade(axs[0]); fmt(axs[0])
axs[0].set_ylabel("CI一致指数（2020年=100）"); axs[0].set_title("CI一致指数と内閣府の景気の後退期（灰色）", loc="left")
axs[1].plot(x.index, x["ci_m3"], color="#444", lw=1); axs[1].axhline(0, color="#888", lw=0.7); shade(axs[1]); fmt(axs[1])
axs[1].set_ylabel("3か月前比（%/月）"); axs[1].set_ylim(-8, 4)
fig.tight_layout(); fig.savefig(FIG / "f35_ci_cycles.png"); plt.close(fig)

# 2. 後退期の確率（本体、平滑化）
fig, ax = plt.subplots(figsize=(9, 3.6))
shade(ax); ax.plot(pm.index, pm["後退期の確率（平滑化）"], color=RED, lw=1.3)
ax.axhline(0.5, color="#888", lw=0.7, ls="--"); fmt(ax); ax.set_ylim(-0.02, 1.02)
ax.set_ylabel("後退期にいる確率")
ax.set_title("マルコフ切り替えモデルが推定した「後退期にいる確率」（灰色は公式の後退期）", loc="left", fontsize=11)
for lab, m, yv in (("東日本大震災", "2011-04", 0.72), ("消費増税", "2014-05", 0.6), ("部品不足など", "2021-09", 0.72)):
    ax.annotate(lab, (pd.Timestamp(m), yv), fontsize=8, ha="center", color="#555")
fig.tight_layout(); fig.savefig(FIG / "f35_prob_main.png"); plt.close(fig)

# 3. 山・谷とのずれ
t = tp.dropna(subset=["始まりのずれ（月）"]).copy()
lab = [f"{a[:4]}年の山" for a in t["山"]]
yy = np.arange(len(t))
fig, ax = plt.subplots(figsize=(7.5, 4.2))
ax.barh(yy + 0.2, t["始まりのずれ（月）"], height=0.38, color=RED, label="後退の始まり（山の翌月との差）")
ax.barh(yy - 0.2, t["終わりのずれ（月）"], height=0.38, color=BLUE, label="後退の終わり（谷との差）")
for i, (a, b) in enumerate(zip(t["始まりのずれ（月）"], t["終わりのずれ（月）"])):
    ax.text(a + (0.15 if a >= 0 else -0.15), i + 0.2, f"{int(a):+d}", va="center", ha="left" if a >= 0 else "right", fontsize=8)
    ax.text(b + (0.15 if b >= 0 else -0.15), i - 0.2, f"{int(b):+d}", va="center", ha="left" if b >= 0 else "right", fontsize=8)
ax.set_yticks(yy); ax.set_yticklabels(lab); ax.axvline(0, color="#444", lw=0.8)
ax.set_xlabel("推定 − 公式（月）　マイナス＝公式より早い"); ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2, frameon=False)
ax.set_title("推定した後退期と公式の山・谷のずれ（1985年の後退は見つからず）", loc="left", fontsize=11)
ax.spines[["top", "right"]].set_visible(False); ax.set_xlim(-6, 6)
fig.tight_layout(); fig.savefig(FIG / "f35_turning_gaps.png"); plt.close(fig)

# 4. 3状態の中身と、2状態との比較
fig, axs = plt.subplots(2, 1, figsize=(9, 5.4), sharex=True)
axs[0].stackplot(pm.index, pm["急落"], pm["後退"], pm["拡張"], colors=["#742a2a", "#f6ad55", "#9ae6b4"],
                 labels=["急落", "後退", "拡張"], lw=0)
axs[0].legend(loc="lower left", ncol=3, fontsize=8, frameon=True); fmt(axs[0]); axs[0].set_ylim(0, 1)
axs[0].set_title("本体（3状態）：それぞれの状態にいる確率", loc="left", fontsize=11)
k2 = pv["2状態（平均と分散が切り替わる）"]
shade(axs[1]); axs[1].plot(k2.index, k2, color=ORANGE, lw=1.2); axs[1].axhline(0.5, color="#888", lw=0.7, ls="--"); fmt(axs[1])
axs[1].set_ylim(-0.02, 1.02); axs[1].set_ylabel("後退期の確率")
axs[1].set_title("2状態（平均と分散が切り替わる）：大きな落ち込み以外の後退を拾いにくい", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f35_states.png"); plt.close(fig)

# 5. その時点までのデータだけで推定した確率
if rt is not None:
    fig, ax = plt.subplots(figsize=(9, 4.0))
    shade(ax, "1995-01")
    ax.plot(pm["1995-01":].index, pm["後退期の確率（平滑化）"]["1995-01":], color="#999", lw=1, label="全期間のデータで推定（あと知恵）")
    ax.plot(rt.index, rt, color=RED, lw=1.3, label="その月までのデータだけで推定")
    ax.axhline(0.5, color="#888", lw=0.7, ls="--"); fmt(ax); ax.set_ylim(-0.02, 1.02)
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2, frameon=False); ax.set_ylabel("後退期にいる確率")
    ax.set_title("その時点で分かっていたデータだけで推定すると（灰色は公式の後退期）", loc="left", fontsize=11)
    fig.tight_layout(); fig.savefig(FIG / "f35_realtime.png"); plt.close(fig)

# 6. 頑健性：モデルごとの一致
a = acc.copy()
a["短い名前"] = a["モデル"].str.replace("本体：CI一致・3か月前比・3状態（平均だけ切り替わる）", "本体（CI一致・3か月前比・3状態）", regex=False)
a = a.iloc[::-1]
fig, ax = plt.subplots(figsize=(8.5, 5.0))
ax.barh(a["短い名前"], a["後退期を後退と判定した割合"], color=RED, height=0.4, label="公式の後退期のうち後退と判定")
ax.barh(np.arange(len(a)) - 0.4, a["拡張期を拡張と判定した割合"], color=BLUE, height=0.4, label="公式の拡張期のうち拡張と判定")
for i, (s, n) in enumerate(zip(a["後退期を後退と判定した割合"], a["見つからなかった公式の後退期"])):
    ax.text(1.01, i - 0.2, f"見つからず {int(n)}", fontsize=7.5, va="center", color="#555")
ax.set_xlim(0, 1.2); ax.set_xticks([0, 0.25, 0.5, 0.75, 1]); ax.tick_params(axis="y", labelsize=8)
ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.45, -0.08), ncol=2, frameon=False); ax.spines[["top", "right"]].set_visible(False)
ax.set_title("モデルを変えたときの一致（右は、見つけられなかった公式の後退期の数）", loc="left", fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "f35_robustness.png"); plt.close(fig)
print("ok")
