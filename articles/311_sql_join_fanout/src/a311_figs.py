"""311 図3枚"""
import pandas as pd, numpy as np, matplotlib.pyplot as plt
from common import RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

res = pd.read_csv(RES / "scenarios.csv"); fd = pd.read_csv(RES / "checks_found.csv"); sw = pd.read_csv(RES / "cancel_sweep.csv")
short = ["S1 明細をつないで\n注文の送料を足す", "S2 支払をつないで\n注文の金額を足す", "S3 明細と支払を\n両方つなぐ", "S4 店マスタを\n内部結合", "S5 履歴つきマスタを\n外部結合", "S6 履歴つきマスタを\n内部結合", "S7 増える分と消える分が\n打ち消し合う"]

# 図1：素朴な結合の合計は正解の何倍か
fig, ax = plt.subplots(figsize=(9, 4.6))
v = res["差(%)"].values
col = [ORANGE if x > 0 else BLUE for x in v]
ax.barh(range(7), v, color=col); ax.set_yticks(range(7)); ax.set_yticklabels(short, fontsize=9); ax.invert_yaxis()
ax.axvline(0, color=INK, lw=0.8)
for i, x in enumerate(v):
    ax.text(x + (3 if x >= 0 else -3), i, f"{x:+.1f}%", va="center", ha="left" if x >= 0 else "right", fontsize=10, color=INK)
ax.set_xlim(-25, 175); ax.set_xlabel("素朴な結合の合計と正解の差（%）")
ax.set_title("素朴につなぐと、合計は +152% から −3% までずれた\n（橙＝増えた、青＝減った。S7 は −0.4% で、ほぼ合って見える）", loc="left")
save(fig, "a311_totals.png")

# 図2：どの照合が見つけたか
cols = list(fd.columns[1:]); M = fd[cols].values
fig, ax = plt.subplots(figsize=(9.4, 4.8))
ax.imshow(M, cmap=plt.matplotlib.colors.ListedColormap(["#f1f0ec", LIGHT]), aspect="auto", vmin=0, vmax=1)
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        ax.text(j, i, "見つけた" if M[i, j] else "通した", ha="center", va="center", fontsize=9, color=INK if M[i, j] else ORANGE,
                fontweight="normal" if M[i, j] else "bold")
ax.set_xticks(range(len(cols))); ax.set_xticklabels(["C1\n行数を\n比べる", "C2\n注文番号\nの重なり", "C3\n注文番号\nの欠け", "C4\n合計を\n比べる", "C5\n相手のキー\nの重なり", "C1\n（0.5%以内\nは通す）", "C4\n（0.5%以内\nは通す）"], fontsize=8.5)
ax.set_yticks(range(7)); ax.set_yticklabels(short, fontsize=8.5); ax.xaxis.tick_top()
for s in ax.spines.values(): s.set_visible(False)
ax.set_title("行数と合計をぴったり比べれば7場面すべて見つかる。\n「0.5% 以内は通す」にすると、打ち消し合う S7 を通した", loc="left", pad=58)
save(fig, "a311_checks.png")

# 図3：増える分と消える分が打ち消し合う
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.axhspan(-0.5, 0.5, color="#f1f0ec"); ax.axhline(0, color=INK, lw=0.8)
ax.plot(sw["区分が変わった店の数"], sw["合計の差(%)"], "-o", color=ORANGE, ms=4, label="合計の差")
ax.plot(sw["区分が変わった店の数"], sw["行数の差(%)"], "--", color=BLUE, lw=1.2, label="行数の差")
k = int(sw["合計の差(%)"].abs().idxmin()); r = sw.iloc[k]
ax.annotate(f"店が{k}つのとき：合計 {r['合計の差(%)']:+.2f}%\n増えた {int(r['増えた行']):,}行・消えた {int(r['消えた行']):,}行",
            (k, r["合計の差(%)"]), (k + 2.5, -3.2), fontsize=9.5, arrowprops=dict(arrowstyle="-", color=GRAY))
ax.text(20.4, 1.6, "灰色の帯＝±0.5%", fontsize=8.5, color=GRAY, va="center")
ax.set_xlim(-0.5, 23); ax.set_ylim(-5, 40); ax.set_xticks(range(0, 21, 2))
ax.set_xlabel("履歴の行が2行ある店の数（50店中）"); ax.set_ylabel("正解との差（%）"); ax.legend(frameon=False, loc="upper left")
ax.set_title("消える行（マスタにない店コード）と増える行（履歴の2行）が近いと、\n合計も行数もほぼ合って見える", loc="left")
save(fig, "a311_cancel.png")
