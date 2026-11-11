"""F271 06 図：6枚。図1は3つの画面の最初の画面（パソコン、2026年8月）を Playwright で撮って並べる。"""
import os, json, asyncio
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
R = os.path.join(ROOT, "results"); F = os.path.join(ROOT, "figures"); os.makedirs(F, exist_ok=True)
for f in fm.findSystemFonts():
    if "NotoSansCJK-Regular" in f: fm.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 150})
t = pd.read_csv(os.path.join(R, "tasks.csv")); J = json.load(open(os.path.join(R, "main.json")))
BASE = dict(P=1.1, B=0.1, K=0.28, M=1.35, C=1.35, R=0.3, SCR=1.1, S=0.05)
t["sec"] = t.P * 1.1 + t.B * 0.1 + t.K * 0.28 + t.M * 1.35 + t.C * 1.35 + t.R * 0.3 + t.SCR * 1.1 + t.SRCH * 0.05 / 2
NAME = {"d1": "D1 水準グラフ型", "d2": "D2 表型", "d3": "D3 問いから作る型", "d4": "D4 D3＋水準（問い直し）"}
CL = {"d1": "#0969da", "d2": "#9a6700", "d3": "#1a7f37", "d4": "#8250df"}
QN = {"Q1": "Q1 合計の前年同月比", "Q2": "Q2 いちばん伸びた業態", "Q3": "Q3 マイナスの業態", "Q4": "Q4 スーパーは先月より上か",
      "Q5": "Q5 ドラッグは前年より多いか", "Q6": "Q6 いつもの揺れの外", "Q7": "Q7 直近12か月は前年より多いか", "Q8": "Q8 最新月",
      "X1": "X1 百貨店の販売額", "X2": "X2 コンビニは2019年より多いか", "X3": "X3 販売額がいちばん大きい業態", "X4": "X4 ホームセンターの過去最高の月"}
# ---- 図1：画面
async def shots():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": 1366, "height": 768})
        for d in ["d1", "d2", "d3"]:
            await pg.goto(f"file://{ROOT}/dashboard/{d}.html?m=2026-08"); await pg.wait_for_timeout(200)
            await pg.screenshot(path=os.path.join(R, f"screen_{d}_pc_2026-08.png"))
        await b.close()
asyncio.run(shots())
fig, ax = plt.subplots(1, 3, figsize=(16, 3.9))
for a, d in zip(ax, ["d1", "d2", "d3"]):
    im = plt.imread(os.path.join(R, f"screen_{d}_pc_2026-08.png")); a.imshow(im[:, 80:1290]); a.set_title(NAME[d], fontsize=13); a.axis("off")
fig.suptitle("同じデータから作った3つの画面（パソコン1366×768で最初に見える範囲、最新月＝2026年8月）", fontsize=13)
fig.tight_layout(); fig.savefig(os.path.join(F, "fig1_three_screens.png")); plt.close(fig)
# ---- 図2：問いごとの見積もり時間（パソコン）
x = t[(t.vp == "pc") & (t.period == "main") & t.design.isin(["d1", "d2", "d3"])]
m = x.groupby(["q", "design"]).sec.median().unstack()
qs = [q for q in QN if q.startswith("Q")]
fig, a = plt.subplots(figsize=(10, 6.2)); y = np.arange(len(qs))
for j, d in enumerate(["d1", "d2", "d3"]):
    a.barh(y + (j - 1) * 0.26, m.loc[qs, d], height=0.25, color=CL[d], label=NAME[d])
a.set_xscale("log"); a.set_yticks(y); a.set_yticklabels([QN[q] for q in qs]); a.invert_yaxis()
a.set_xlabel("答えるまでの見積もり時間（秒、24か月の中央値、対数目盛り）"); a.axvline(10, color="#8c959f", lw=0.8, ls=":")
a.legend(loc="lower right", frameon=False); a.set_title("主な8問：答えるまでの見積もり時間（KLM、パソコン）")
fig.tight_layout(); fig.savefig(os.path.join(F, "fig2_time_by_question.png")); plt.close(fig)
# ---- 図3：最初の画面だけで答えられる割合
vps = [("pc", "パソコン\n1366×768"), ("pc_s", "パソコン\n1280×720"), ("pc_l", "パソコン\n1920×1080"), ("sp", "スマートフォン\n390×844")]
fs = t[(t.period == "main") & t.q.str.startswith("Q") & t.design.isin(["d1", "d2", "d3"])].groupby(["vp", "design"])["first"].mean().unstack()
fig, a = plt.subplots(figsize=(10, 4.6)); xx = np.arange(len(vps))
for j, d in enumerate(["d1", "d2", "d3"]):
    v = [fs.loc[k, d] * 100 for k, _ in vps]; a.bar(xx + (j - 1) * 0.26, v, width=0.25, color=CL[d], label=NAME[d])
    for xi, vi in zip(xx + (j - 1) * 0.26, v): a.text(xi, vi + 1.5, f"{vi:.0f}%", ha="center", fontsize=9)
a.set_xticks(xx); a.set_xticklabels([n for _, n in vps]); a.set_ylim(0, 128); a.set_ylabel("割合（%）")
a.set_title("主な8問のうち、最初の画面だけで答えられた割合（スクロール・クリック・マウス当て・計算なし）"); a.legend(frameon=False, ncol=3, loc="upper left")
fig.tight_layout(); fig.savefig(os.path.join(F, "fig3_first_screen.png")); plt.close(fig)
# ---- 図4：読み違い
mr = pd.read_csv(os.path.join(R, "misread_d1_single.csv"))
fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
g = mr.groupby("g").p.mean().sort_values() * 100
ax[0].barh(g.index, g.values, color="#0969da"); ax[0].axvline(10, color="#bc4c00", ls="--", lw=1); ax[0].text(10.3, -0.4, "計画の基準10%", color="#bc4c00", fontsize=9)
ax[0].set_xlabel("「前年同月より多いか」を間違える割合（%）"); ax[0].set_title("D1 の折れ線を位置で読むとき（24か月の平均）")
ax[1].scatter(mr.yoy.abs(), mr.p * 100, s=14, color="#0969da", alpha=0.6); ax[1].set_xlabel("前年同月比の大きさ（%、絶対値）"); ax[1].set_ylabel("間違える割合（%）")
ax[1].set_title("前年との差が小さい月ほど読み違える"); ax[1].set_xlim(0, 12)
fig.suptitle("読む位置の誤差＝描画の高さの1.5%（標準偏差）としたときの読み違い", fontsize=12); fig.tight_layout(); fig.savefig(os.path.join(F, "fig4_misread.png")); plt.close(fig)
# ---- 図5：想定内と想定外の問い（問い直しの D4 を含む）
x = t[(t.vp == "pc") & (t.period == "main")]
mm = x.assign(set=np.where(x.q.str.startswith("Q"), "主な8問（D3 の設計に使った）", "想定外の4問")).groupby(["set", "design"]).sec.median().unstack()
fig, a = plt.subplots(figsize=(10, 4.6)); sets = ["主な8問（D3 の設計に使った）", "想定外の4問"]; xx = np.arange(2)
for j, d in enumerate(["d1", "d2", "d3", "d4"]):
    v = [mm.loc[s, d] for s in sets]; a.bar(xx + (j - 1.5) * 0.2, v, width=0.19, color=CL[d], label=NAME[d])
    for xi, vi in zip(xx + (j - 1.5) * 0.2, v): a.text(xi, vi * 1.08, f"{vi:.1f}", ha="center", fontsize=9)
a.set_yscale("log"); a.set_xticks(xx); a.set_xticklabels(sets); a.set_ylabel("見積もり時間の中央値（秒、対数）")
a.set_title("問いから作った画面は、想定外の問いでは遅くなる（パソコン）"); a.legend(frameon=False, fontsize=9, ncol=2, loc="upper left")
a.set_ylim(0.3, 200); fig.tight_layout(); fig.savefig(os.path.join(F, "fig5_holdout_and_d4.png")); plt.close(fig)
# ---- 図6：時間の内訳
dd = pd.read_csv(os.path.join(R, "reask_decomposition.csv")); dd = dd[dd.vp == "pc"]
parts = ["探す", "スクロール", "マウス当て", "クリック操作", "読む", "比べる", "計算"]
PC = ["#8c959f", "#d4a72c", "#0969da", "#8250df", "#1a7f37", "#bc4c00", "#cf222e"]
fig, ax = plt.subplots(1, 2, figsize=(13, 4.8))
for a, qset in zip(ax, ["主な8問", "想定外4問"]):
    sub = dd[dd.qset == qset].set_index("design").loc[["d1", "d2", "d3", "d4"]]; left = np.zeros(4); tot = sub[parts].sum(axis=1).values
    for pt, c in zip(parts, PC):
        v = sub[pt].values / tot * 100; a.barh([NAME[d] for d in sub.index], v, left=left, color=c, label=pt); left += v
    for i, tt in enumerate(tot): a.text(101, i, f"平均{tt:.1f}秒", va="center", fontsize=9)
    a.invert_yaxis(); a.set_xlim(0, 125); a.set_title(f"{qset}：1問あたりの時間の内訳（パソコン）"); a.set_xlabel("平均時間に占める割合（%）")
fig.legend(*ax[0].get_legend_handles_labels(), frameon=False, fontsize=9, loc="lower center", ncol=7); fig.subplots_adjust(bottom=0.2)
fig.tight_layout(rect=(0, 0.08, 1, 1)); fig.savefig(os.path.join(F, "fig6_time_breakdown.png")); plt.close(fig)
print(sorted(os.listdir(F)))
