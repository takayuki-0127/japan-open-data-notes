"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F, D = ROOT / "results", ROOT / "figures", ROOT / "data"
F.mkdir(exist_ok=True)
SRC = "出典：財務省「本邦対外資産負債残高」、日本銀行「国際収支統計」「外国為替相場」をもとに作成者が加工して作成"
SRC2 = "出典：財務省「本邦対外資産負債残高 増減要因（試算）」（各年末の概要の参考1）をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
nb = pd.read_csv(R / "net_by_item.csv", index_col="year")
ITEMS = ["直接投資", "証券投資", "外貨準備", "その他投資", "金融派生商品"]
COL = {"直接投資": C[0], "証券投資": C[1], "外貨準備": C[2], "その他投資": C[3], "金融派生商品": C[5]}

# 図1 項目別の純額（積み上げ）と合計
fig, ax = plt.subplots(figsize=(8.8, 5.2))
yrs = nb.index.values
pos = np.zeros(len(yrs)); neg = np.zeros(len(yrs))
for it in ITEMS:
    v = nb[it].values
    bt = np.where(v >= 0, pos, neg)
    ax.bar(yrs, v, bottom=bt, color=COL[it], width=0.75, label=it + ("（資産のみ）" if it == "外貨準備" else "（資産−負債）"))
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
ax.plot(yrs, nb["合計"].values, color=INK, marker="o", ms=3.5, lw=1.4, label="対外純資産（合計）")
ax.axhline(0, color=INK2, lw=0.8)
ax.annotate(f"{m['net_2025_tn']:.1f}兆円", (2025, m["net_2025_tn"]), xytext=(2017.2, 640), fontsize=9.5,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_xticks(range(1996, 2026, 3)); ax.set_ylabel("兆円（暦年末）")
ax.legend(frameon=False, loc="upper left", fontsize=8.6)
style(ax)
ax.set_title(f"対外純資産の中身：{m['di_largest_since']}年末から直接投資が最大の項目に（2025年末は{m['share_直接投資_2025_pct']:.0f}%）", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.12)
save(fig, F / "fig1_net_by_item.png", SRC, note="2013年末までは国際収支マニュアル第5版の計数を第6版の基準に組み替えた値。その他投資の負債には特別引出権（SDR）を含む")

# 図2 円建てとドル建て（2012年末＝100）
fig, ax = plt.subplots(figsize=(8.8, 5.2))
b = nb.loc[2012]
yen = nb["合計"] / b["合計"] * 100; usd = nb["net_usd_bn"] / b["net_usd_bn"] * 100
ax.plot(yrs, yen, color=C[0], lw=2.2, marker="o", ms=3.5, label="円建て")
ax.plot(yrs, usd, color=C[1], lw=2.2, marker="o", ms=3.5, label="ドル建て（12月末のドル円で換算）")
ax.axhline(100, color=INK2, lw=0.8)
ax.annotate(f"円建て +{m['yen_change_2012_2025_pct']:.1f}%", (2025, yen[2025]), xytext=(2019.6, yen[2025] + 6), fontsize=9.5, color=C[0])
ax.annotate(f"ドル建て +{m['usd_change_2012_2025_pct']:.1f}%", (2025, usd[2025]), xytext=(2019.6, usd[2025] - 18), fontsize=9.5, color=C[1])
ax.set_xticks(range(1996, 2026, 3)); ax.set_ylabel("2012年末＝100")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title("2012年末から、円建てでは1.9倍、ドル建てではほぼ横ばい", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.12)
save(fig, F / "fig2_yen_vs_usd.png", SRC, note=f"ドル円は東京市場17時時点の12月末（2012年末 {m['usdjpy_2012']:.2f}円、2025年末 {m['usdjpy_2025']:.2f}円）")

# 図3 財務省の試算：年ごとの増減の要因
fn = pd.read_csv(R / "factors_net.csv", index_col="year") / 1000
fig, ax = plt.subplots(figsize=(8.8, 5.2))
x = np.arange(len(fn)); w = 0.26
ax.bar(x - w, fn["flow"], w, color=C[0], label="取引")
ax.bar(x, fn["fx"], w, color=C[2], label="為替相場の変動")
ax.bar(x + w, fn["other"], w, color=C[3], label="その他調整（株価・債券価格の変化など）")
ax.scatter(x, fn["change"], color=INK, zorder=3, s=26, label="前年末からの増減")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x); ax.set_xticklabels([f"{y}年" for y in fn.index])
ax.set_ylabel("兆円")
ax.legend(frameon=False, loc="lower left", fontsize=8.8, ncol=2)
style(ax)
t = q["net_total"]
ax.set_title(f"2019〜25年の純資産の増減：為替で+{t['fx']:.0f}兆円、その他調整で{t['other']:.0f}兆円", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.12)
save(fig, F / "fig3_mof_factors.png", SRC2, note="各年の公表時の試算の値（のちの改訂は反映していない）。取引の合計は+%.0f兆円" % t["flow"])

# 図4 問い直し：為替とその他調整を、項目ごとの純額で
rq = pd.read_csv(R / "requestion_net_by_item.csv", index_col="item")
order = ["直接投資", "証券投資", "外貨準備", "その他投資", "金融派生商品"]
fig, ax = plt.subplots(figsize=(8.8, 5.2))
y = np.arange(len(order))[::-1]; h = 0.36
ax.barh(y + h / 2, rq.loc[order, "net_fx_tn"], h, color=C[2], label="為替相場の変動（資産−負債）")
ax.barh(y - h / 2, rq.loc[order, "net_other_tn"], h, color=C[3], label="その他調整（資産−負債）")
for yy, it in zip(y, order):
    for off, col in [(h / 2, "net_fx_tn"), (-h / 2, "net_other_tn")]:
        v = rq.loc[it, col]
        ax.text(v + (3 if v >= 0 else -3), yy + off, f"{v:+.1f}", va="center", ha="left" if v >= 0 else "right", fontsize=8.8)
ax.set_yticks(y); ax.set_yticklabels(order)
ax.axvline(0, color=INK2, lw=0.8); ax.set_xlim(-160, 190)
ax.set_xlabel("2019〜2025年の累計（兆円）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.legend(frameon=False, loc="lower right", fontsize=8.8)
ax.set_title(f"為替による増加を打ち消したのは、証券投資のその他調整（{q['portfolio_net_other_tn']:+.1f}兆円）。負債側が大きく増えた", loc="left", fontsize=10.5)
fig.subplots_adjust(left=0.14, right=0.97, top=0.92, bottom=0.17)
save(fig, F / "fig4_other_by_item.png", SRC2, note=f"証券投資のその他調整は、資産側+{q['portfolio_assets_other_tn']:.1f}兆円、負債側+{q['portfolio_liab_other_tn']:.1f}兆円（負債の増加は純資産を減らす）")
