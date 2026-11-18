"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F, D = ROOT / "results", ROOT / "figures", ROOT / "data"
F.mkdir(exist_ok=True)
SRC = "出典：日本銀行「資金循環統計」「日本銀行勘定」をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
sh = pd.read_csv(R / "shares_quarterly.csv", index_col="period")
t = pd.read_csv(D / "ff_quarterly.csv", index_col="period")
b = pd.read_csv(D / "bs01_quarterly.csv", index_col="period")


def x_of(idx):
    return np.array([int(p[:4]) + (int(p[-1]) - 0.5) / 4 for p in idx])


def qlabel(p):
    return f"{p[:4]}年{['1〜3', '4〜6', '7〜9', '10〜12'][int(p[-1]) - 1]}月期"


# 図1 日銀の保有割合（3つの定義）
x = x_of(sh.index)
tb = (t["FOF_FFAS110A311"] + t["FOF_FFAS110A310"]) / (t["FOF_FFAS420L311"] + t["FOF_FFAS181L311"] + t["FOF_FFAS420L310"] + t["FOF_FFAS181L310"]) * 100
ratio = t["FOF_FFAB420L311"] / t["FOF_FFAS420L311"]
bk = (b["MABJMA5B"] / (t["FOF_FFAB420L311"] + t["FOF_FFAS181L311"] * ratio)).dropna() * 100
fig, ax = plt.subplots(figsize=(8.8, 5.2))
ax.plot(x, sh["中央銀行"], color=C[0], lw=2.2, label="国債・財投債（時価）［基本］")
ax.plot(x_of(tb.index), tb, color=C[3], lw=1.3, ls="--", label="国庫短期証券を含む（時価）")
ax.plot(x_of(bk.index), bk, color=C[2], lw=1.3, ls=":", label="日銀勘定の長期国債（簿価）÷額面に近い発行残高")
ax.axhline(50, color=INK2, lw=0.8, ls="-", alpha=0.6)
pk = m["boj_share_peak_period"]; px = x_of([pk])[0]
ax.annotate(f"頂点 {m['boj_share_peak']:.1f}%\n（{qlabel(pk)}）", (px, m["boj_share_peak"]), xytext=(px - 9, 56),
            fontsize=9.5, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
lx = x[-1]
ax.annotate(f"{m['boj_share_last']:.1f}%\n（{qlabel(m['last_period'])}、速報）", (lx, m["boj_share_last"]), xytext=(lx - 6.5, 35),
            fontsize=9.5, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
ax.set_ylim(0, 62); ax.set_xlim(1997.5, 2027)
ax.set_ylabel("日銀が持つ割合（%）"); ax.set_xticks(range(1998, 2027, 4))
ax.legend(frameon=False, loc="upper left", fontsize=8.8)
style(ax)
ax.set_title(f"国債のうち日銀が持つ割合：時価では{qlabel(pk)}の{m['boj_share_peak']:.1f}%が頂点、その後{m['boj_share_drop_pt']:.1f}%ポイント低下", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.12)
save(fig, F / "fig1_boj_share.png", SRC, note="四半期末。発行残高は一般政府と財政融資資金の国債・財投債。簿価の線の分母は、財政融資資金分を時価×一般政府分の額面／時価の比で近似")

# 図2 保有者の内訳（積み上げ）
MAIN = ["中央銀行", "預金取扱機関", "保険・年金基金", "公的金融機関", "一般政府", "海外", "家計", "その他"]
LAB = {"預金取扱機関": "預金取扱機関（銀行など）", "一般政府": "一般政府（公的年金など）", "公的金融機関": "公的金融機関（財政融資資金など）"}
COL = [C[0], C[1], C[2], "#b9b7b0", C[3], C[4], "#d38bb0", C[5]]
fig, ax = plt.subplots(figsize=(8.8, 5.2))
ax.stackplot(x, [sh[k].clip(lower=0).values for k in MAIN], colors=COL, labels=[LAB.get(k, k) for k in MAIN], alpha=0.92, lw=0)
ax.set_xlim(x[0], x[-1]); ax.set_ylim(0, 100)
ax.set_ylabel("保有の割合（%、時価）"); ax.set_xticks(range(1998, 2027, 4))
ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=8.6, reverse=True)
style(ax, ygrid=False)
ax.set_title("国債・財投債を誰が持っているか：2013年から日銀が増え、銀行などが減った", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.08, right=0.72, top=0.92, bottom=0.12)
save(fig, F / "fig2_holders_stack.png", SRC, note="四半期末の残高（時価）の割合。その他は合計から各部門を引いた残り（証券投資信託、非金融法人企業など）。負の値は0で描いた")

# 図3 頂点→最新の、部門ごとの割合の変化
sc = pd.read_csv(R / "sector_change.csv", index_col="sector")
ORDER = [("中央銀行", "中央銀行"), ("預金取扱機関", "預金取扱機関"), ("  うち国内銀行", "国内銀行"), ("  うち中小企業金融機関等", "中小企業金融機関等"),
         ("保険・年金基金", "保険・年金基金"), ("  うち生命保険", "生命保険"), ("一般政府", "一般政府"), ("  うち公的年金", "うち公的年金"),
         ("海外", "海外"), ("家計", "家計"), ("その他", "その他")]
v = [sc.loc[k, "change_pt"] for _, k in ORDER]
fig, ax = plt.subplots(figsize=(8.8, 5.2))
y = np.arange(len(ORDER))[::-1]
cols = [C[1] if val < 0 else C[0] for val in v]
for yy, val, col, (l, _) in zip(y, v, cols, ORDER):
    ax.barh(yy, val, color=col, height=0.62, alpha=0.5 if l.startswith("  ") else 1.0)
for yy, (l, _), val in zip(y, ORDER, v):
    ax.text(val + (0.15 if val >= 0 else -0.15), yy, f"{val:+.1f}", va="center", ha="left" if val >= 0 else "right", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels([l for l, _ in ORDER], fontsize=9.2)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlim(-8.8, 5.2)
ax.set_xlabel("割合の変化（%ポイント、時価）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
ax.set_title(f"頂点（{qlabel(pk)}）からの割合の変化：日銀が下がり、銀行・公的年金・海外が上がった", loc="left", fontsize=11, x=-0.5)
fig.subplots_adjust(left=0.36, right=0.97, top=0.92, bottom=0.14)
save(fig, F / "fig3_change_since_peak.png", SRC, note="字下げの行は上の部門の内訳。中小企業金融機関等には、信用金庫などを含む")

# 図4 残高の変化を取引と調整に分ける（問い直し）
dd = pd.read_csv(R / "requestion_sector_decomp.csv", index_col="sector")
ROWS = [("中央銀行", "中央銀行"), ("銀行等", "銀行等"), ("保険・年金基金", "保険・年金基金"), ("社会保障基金（公的年金など）", "社会保障基金"),
        ("海外", "海外"), ("家計", "家計"), ("発行残高（合計）", "発行残高（一般政府＋財政融資資金）")]
fl = np.array([dd.loc[k, "flow_tn"] for _, k in ROWS]); ad = np.array([dd.loc[k, "adjustment_tn"] for _, k in ROWS])
tot = np.array([dd.loc[k, "change_tn"] for _, k in ROWS])
fig, ax = plt.subplots(figsize=(8.8, 5.2))
xx = np.arange(len(ROWS)); w = 0.36
ax.bar(xx - w / 2, fl, w, color=C[0], label="取引（買い越しが正）")
ax.bar(xx + w / 2, ad, w, color=C[3], label="調整（時価の変化など）")
ax.scatter(xx, tot, color=INK, zorder=3, s=22, label="残高の変化（取引＋調整）")
for i in range(len(ROWS)):
    ax.text(xx[i] + 0.07, tot[i], f"{tot[i]:+.0f}", ha="left", va="center", fontsize=8.8, color=INK)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(xx)
ax.set_xticklabels(["中央銀行", "銀行等", "保険・\n年金基金", "社会保障基金\n（公的年金など）", "海外", "家計", "発行残高\n（合計）"], fontsize=8.8)
ax.set_ylabel("兆円"); ax.legend(frameon=False, loc="lower left", fontsize=8.8)
style(ax)
ax.set_title(f"{qlabel(pk)}→{qlabel(m['last_period'])}の残高の変化：保険・年金の取引はほぼ0、減ったのは時価の分", loc="left", fontsize=11)
fig.subplots_adjust(left=0.09, right=0.98, top=0.92, bottom=0.17)
save(fig, F / "fig4_flow_vs_adjustment.png", SRC, note="国債・財投債。取引と調整は頂点の次の期から最新の期までの合計。調整には時価の変化のほか、統計上の調整を含む")
