import json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from common import DATA, RES, FIG, EVENTS
for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f: fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
C = {"mb": "#c0392b", "m2": "#2471a3", "loan": "#1e8449", "gray": "#7f8c8d"}
w = pd.read_csv(DATA / "monthly.csv", index_col=0); w.index = pd.PeriodIndex(w.index, freq="M").to_timestamp()
o = json.load(open(RES / "results.json"))
yoy = pd.read_csv(RES / "yoy_growth.csv", index_col=0); yoy.index = pd.PeriodIndex(yoy.index, freq="M").to_timestamp()

# 1 指数（1998年4月=100、対数目盛）
d = w[["mb", "m2", "loan_banks"]].loc["1998-04":].dropna()
ix = 100 * d / d.iloc[0]
fig, ax = plt.subplots(figsize=(9, 5))
for c, lab, col in [("mb", "マネタリーベース", C["mb"]), ("m2", "マネーストック M2", C["m2"]), ("loan_banks", "銀行の貸出", C["loan"])]:
    ax.plot(ix.index, ix[c], color=col, lw=2, label=lab)
    ax.text(ix.index[-1], ix[c].iloc[-1], f" {ix[c].iloc[-1]/100:.1f}倍", color=col, va="center", fontsize=10)
ax.set_yscale("log"); ax.set_yticks([50, 100, 200, 500, 1000, 2000]); ax.set_yticklabels(["50", "100", "200", "500", "1000", "2000"])
for e, lab in EVENTS:
    t = pd.Timestamp(e); ax.axvline(t, color=C["gray"], lw=0.7, ls=":"); ax.text(t, 2300, lab, rotation=90, fontsize=8, color=C["gray"], va="top", ha="right")
ax.set_ylim(40, 2500); ax.set_ylabel("1998年4月＝100（対数目盛）"); ax.legend(loc="center left", frameon=False)
ax.set_title("お金の量は約10倍、貸出は1.2倍（平均残高、月次）", loc="left")
fig.tight_layout(); fig.savefig(FIG / "f191_index.png", dpi=150); plt.close()

# 2 前年比
y = yoy.loc["1999-04":]
fig, ax = plt.subplots(figsize=(9, 5)); ax2 = ax.twinx()
ax2.fill_between(y.index, y.mb, 0, color=C["mb"], alpha=0.18, lw=0); ax2.set_ylabel("マネタリーベースの前年比（%、右・薄い赤）", color=C["mb"])
ax.plot(y.index, y.loan_banks, color=C["loan"], lw=2, label="銀行の貸出")
ax.plot(y.index, y.m2, color=C["m2"], lw=1.6, label="M2")
ax.axhline(0, color="black", lw=0.6); ax.set_ylabel("前年比（%、左）"); ax.set_ylim(-10, 15); ax2.set_ylim(-30, 45)
ax2.spines["right"].set_visible(True); ax.legend(loc="upper left", frameon=False)
ax.set_title("前年比で見ると、お金の量の伸びと貸出の伸びは別々に動く", loc="left")
fig.tight_layout(); fig.savefig(FIG / "f191_yoy.png", dpi=150); plt.close()

# 3 ラグ相関
lc = o["lagcorr"]; ks = list(range(0, 37))
fig, ax = plt.subplots(figsize=(9, 5))
bp = o["block_perm"]; ax.axhspan(bp["q025"], bp["q975"], color=C["gray"], alpha=0.15, label="無関係でも出る幅（MB→貸出、ずれ0、95%）")
for k, lab, col in [("mb_to_loan", "MB → 貸出", C["mb"]), ("m2_to_loan", "M2 → 貸出", C["m2"]), ("mb_to_m2", "MB → M2", C["gray"])]:
    ax.plot(ks, [lc[k][str(i)] for i in ks], color=col, lw=2, label=lab, marker="o", ms=3)
ax.axhline(0, color="black", lw=0.6); ax.set_xlabel("先に動く側を何か月ずらしたか"); ax.set_ylabel("前年比どうしの相関（1999年4月〜）")
ax.set_ylim(-0.6, 0.7); ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.set_title("どれだけずらしても、MB と貸出の相関はほぼ0", loc="left")
fig.tight_layout(); fig.savefig(FIG / "f191_lagcorr.png", dpi=150); plt.close()

# 4 出来事のあと24か月
ev = o["events"]; lab = [f"{e['event']}\n({e['month'][:4]}年)" for e in ev]
x = np.arange(len(ev)); wd = 0.27
fig, ax = plt.subplots(figsize=(9.5, 5))
for i, (k, l, col) in enumerate([("mb_after", "マネタリーベース", C["mb"]), ("m2_after", "M2", C["m2"]), ("loan_after", "銀行の貸出", C["loan"])]):
    v = [e[k] for e in ev]; ax.bar(x + (i - 1) * wd, v, wd, color=col, label=l)
    for xi, vi in zip(x, v): ax.text(xi + (i - 1) * wd, vi + (2 if vi >= 0 else -2), f"{vi:+.0f}", ha="center", va="bottom" if vi >= 0 else "top", fontsize=8)
ax.axhline(0, color="black", lw=0.6); ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=9); ax.set_ylabel("その後24か月の増減（%）")
ax.legend(frameon=False); ax.set_ylim(-30, 115)
ax.set_title("緩和でお金の量が増えたあとも、貸出の伸びはほとんど変わらない", loc="left")
fig.tight_layout(); fig.savefig(FIG / "f191_events.png", dpi=150); plt.close()

# 5 頑健性
rob = pd.read_csv(RES / "robustness_grid.csv")
order = ["MB", "日銀当座預金", "銀行券", "M2", "M3"]
fig, ax = plt.subplots(figsize=(9, 4.6))
for i, m in enumerate(order):
    r = rob[rob.money == m]; n = len(r)
    pos = ((r.b > 0) & (r.p < .05)).sum(); neg = ((r.b < 0) & (r.p < .05)).sum(); ns = n - pos - neg
    left = 0
    for v, col, l in [(pos, C["loan"], "はっきりプラス"), (ns, "#d5d8dc", "はっきりしない"), (neg, C["mb"], "はっきりマイナス")]:
        ax.barh(i, v, left=left, color=col, label=l if i == 0 else None); 
        if v >= 4: ax.text(left + v / 2, i, str(v), ha="center", va="center", fontsize=9)
        left += v
ax.set_yticks(range(len(order))); ax.set_yticklabels([f"{m}の伸び" for m in order]); ax.invert_yaxis()
ax.set_xlabel("80通り（期間5×貸出の定義4×ずれ4）のうちの数"); ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0))
ax.set_title("貸出の伸びとの関係：条件を変えた400通り", loc="left", pad=28)
fig.tight_layout(); fig.savefig(FIG / "f191_robustness.png", dpi=150); plt.close()
print("ok")
