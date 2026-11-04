"""04 図"""
import json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from common import DATA, RAW, RES, FIG

for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25, "figure.dpi": 150})
BLUE, ORANGE, GRAY, GREEN, RED = "#2563EB", "#EA580C", "#9CA3AF", "#059669", "#DC2626"

m = pd.read_csv(DATA / "monthly.csv", parse_dates=["month"]).set_index("month")
P = pd.read_csv(RES / "probs_all.csv", parse_dates=["month"]).set_index("month")
R = pd.read_csv(RES / "models_all.csv").set_index("key")
RT = pd.read_csv(RES / "realtime_probs.csv", parse_dates=["month"]).set_index("month")
choice = json.load(open(RES / "main_choice.json"))
MK = choice["main_key"]

def shade(ax, start="1975-01-01"):
    r = m.rec.loc[start:]
    on = False
    for d, v in r.items():
        if v and not on:
            s = d; on = True
        if not v and on:
            ax.axvspan(s, d, color=GRAY, alpha=0.3, lw=0); on = False

# 1 本体の確率
fig, ax = plt.subplots(figsize=(10, 4.2))
shade(ax)
ax.plot(P.index, P[MK], color=BLUE, lw=1.4, label="一致7系列をそのまま並べたモデル（3状態）")
ax.plot(P.index, P["ci_K3"], color=ORANGE, lw=1.1, alpha=0.9, label="CI一致指数1本のモデル（3状態、1985年〜）")
ax.axhline(0.5, color="k", lw=0.7, ls=":")
ax.set_ylim(-0.02, 1.02); ax.set_ylabel("後退の状態にいる確率")
ax.set_title("景気の「後退」の確率（全期間のデータで推定）と公式の後退期（灰色）", loc="left", fontsize=12)
ax.legend(loc="lower left", fontsize=9, framealpha=0.9)
fig.tight_layout(); fig.savefig(FIG / "f174_probs.png"); plt.close(fig)

# 2 状態の数と共分散
A = R[R.block == "A"].copy()
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
for cov, c, lab in (("diag", GRAY, "系列どうし無関係とみなす（対角）"), ("full", BLUE, "系列どうしの連動を認める（フル）")):
    a = A[A["cov"] == cov].sort_values("K")
    axes[0].plot(a.K, a.bic, "o-", color=c, label=lab)
    axes[1].plot(a.K, a.acc_1975 * 100, "o-", color=c, label=lab)
axes[0].set_title("BIC（小さいほど当てはまりがよい）", loc="left", fontsize=11)
axes[1].set_title("公式の局面との一致率（%、1975年〜）", loc="left", fontsize=11)
for ax in axes:
    ax.set_xlabel("状態の数"); ax.set_xticks([2, 3, 4, 5])
axes[0].legend(fontsize=8.5)
b = A.loc[MK]
axes[0].annotate("BIC 最小", (b.K, b.bic), xytext=(b.K + 0.3, b.bic + 500), arrowprops=dict(arrowstyle="->"), fontsize=9)
fig.tight_layout(); fig.savefig(FIG / "f174_states_bic.png"); plt.close(fig)

# 3 1本にまとめてから推定した場合との比較（1985年〜で評価）
keys = [(MK, "7系列を並べたまま"), ("ci_K3", "CI一致指数1本"), ("avg7_K3", "7系列の単純平均1本"), ("pc1_K3", "7系列の第1主成分1本")]
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
y = np.arange(len(keys))[::-1]
w = 0.26
for j, (col, c, lab) in enumerate((("acc_1985", BLUE, "一致率"), ("sens_1985", GREEN, "公式の後退期を後退と判定"), ("spec_1985", ORANGE, "公式の拡張期を拡張と判定"))):
    axes[0].barh(y + (1 - j) * w, [R.loc[k, col] * 100 for k, _ in keys], height=w, color=c, label=lab)
axes[0].set_yticks(y); axes[0].set_yticklabels([l for _, l in keys]); axes[0].set_xlim(0, 100)
axes[0].set_title("一致の度合い（%、1985年4月〜）", loc="left", fontsize=11); axes[0].legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, frameon=False)
axes[1].barh(y, [R.loc[k, "false_1985"] for k, _ in keys], color=GRAY)
for yy, (k, _) in zip(y, keys):
    axes[1].text(R.loc[k, "false_1985"] + 0.1, yy, f"{int(R.loc[k, 'false_1985'])}回", va="center", fontsize=9)
axes[1].set_yticks(y); axes[1].set_yticklabels([]); axes[1].set_title("公式にない後退期（回）", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f174_compare.png"); plt.close(fig)

# 4 頑健性
C = R[R.block == "C"].copy()
rows = [("本体（BIC 最小：フル・3状態）", R.loc[MK, "acc_1975"], R.loc[MK, "missed_1975"], R.loc[MK, "false_1975"])]
lab = {"rule_lowest": "後退＝いちばん低い状態だけ", "rule_answer": "後退＝公式の後退期が多い状態（後知恵）",
       "minlen_1": "最短の長さ 1か月", "minlen_6": "最短の長さ 6か月", "add_C6C7": "C6・C7 を足す（9系列）",
       "h6": "6か月前比", "pre_covid": "コロナ期を除く（〜2019年）", "seed_1": "初期値の乱数を変える ①",
       "seed_2": "初期値の乱数を変える ②", "seed_3": "初期値の乱数を変える ③", "drop_C9": "有効求人倍率を抜く",
       "drop_C1": "生産指数を抜く"}
for k, v in lab.items():
    rows.append((v, C.loc[k, "acc_1975"], C.loc[k, "missed_1975"], C.loc[k, "false_1975"]))
others = [k for k in C.index if k.startswith("drop_") and k not in ("drop_C9", "drop_C1")]
rows.append(("ほかの系列を1本ずつ抜く（5通り）", np.mean([C.loc[k, "acc_1975"] for k in others]), np.nan, np.nan))
D = pd.DataFrame(rows, columns=["label", "acc", "missed", "false"])
fig, ax = plt.subplots(figsize=(10, 5.4))
yy = np.arange(len(D))[::-1]
cols = [BLUE if i == 0 else (RED if "乱数" in l else GRAY) for i, l in enumerate(D.label)]
ax.scatter(D.acc * 100, yy, color=cols, s=45, zorder=3)
ax.axvline(D.acc[0] * 100, color=BLUE, lw=0.8, ls=":")
for y_, (_, r) in zip(yy, D.iterrows()):
    t = f"{r.acc * 100:.1f}%"
    if not np.isnan(r.missed):
        t += f"（見逃し{int(r.missed)}・公式にない{int(r['false'])}）"
    else:
        t += "（平均）"
    ax.text(r.acc * 100 + 0.8, y_, t, va="center", fontsize=8.5)
ax.set_yticks(yy); ax.set_yticklabels(D.label, fontsize=9); ax.set_xlim(55, 100)
ax.set_xlabel("公式の局面との一致率（%、1975年〜。6か月前比は1975年7月〜）")
ax.set_title("設定を1つずつ変えると一致率はどう動くか（赤＝当てはまりがほぼ同じ別の解）", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f174_robustness.png"); plt.close(fig)

# 5 その時点までのデータだけで
fig, ax = plt.subplots(figsize=(10, 4.2))
r = m.rec.loc["1995-01-01":]
on = False
for d, v in r.items():
    if v and not on:
        s = d; on = True
    if not v and on:
        ax.axvspan(s, d, color=GRAY, alpha=0.3, lw=0); on = False
ax.plot(RT.index, RT["multi7"], color=BLUE, lw=1.2, label="一致7系列を並べたまま")
ax.plot(RT.index, RT["ci"], color=ORANGE, lw=1.0, alpha=0.85, label="CI一致指数1本")
ax.axhline(0.5, color="k", lw=0.7, ls=":")
ax.set_ylim(-0.02, 1.02); ax.set_ylabel("その月までのデータでの後退の確率")
ax.set_title("その時点までのデータだけで判定した後退の確率（1995年1月〜2026年8月）", loc="left", fontsize=12)
ax.legend(loc="upper left", fontsize=9, framealpha=0.9)
fig.tight_layout(); fig.savefig(FIG / "f174_realtime.png"); plt.close(fig)
print("figures saved")
