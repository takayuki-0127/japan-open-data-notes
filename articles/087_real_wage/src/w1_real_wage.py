"""W1：実質賃金の変化を「時間当たりの名目賃金・労働時間・物価」と「パート比率」に分ける（規模5人以上、1991〜2025年）"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import *

x = load()
G = lambda item, form="0", size="T", month="CY", ind="TL": series(x, "伸び率", item, ind, size, form, month) / 100

# --- 1. 公表の伸び率をつないだ水準（1990年＝100）。指数そのものはベンチマーク更新などで段差があるため伸び率でつなぐ
def chain(g, base=1990):
    g = g[g.index > base]
    return pd.concat([pd.Series({base: 100.0}), 100 * (1 + g).cumprod()])

lv = pd.DataFrame({"名目賃金（1人当たり）": chain(G("現金給与総額")),
                   "実質賃金（1人当たり）": chain(G("実質賃金指数（現金給与総額）")),
                   "総実労働時間": chain(G("総実労働時間"))})
lv["物価"] = 100 * lv["名目賃金（1人当たり）"] / lv["実質賃金（1人当たり）"]
lv["名目賃金（1時間当たり）"] = 100 * lv["名目賃金（1人当たり）"] / lv["総実労働時間"]
lv["実質賃金（1時間当たり）"] = 100 * lv["実質賃金（1人当たり）"] / lv["総実労働時間"]
lv.index.name = "年"
lv.round(2).to_csv(RES / "w1_levels_1990eq100.csv", encoding="utf-8-sig")

# 30人以上の長い系列（1971年〜）
lv30 = pd.DataFrame({"名目": chain(G("現金給与総額", size="0"), 1970), "実質": chain(G("実質賃金指数（現金給与総額）", size="0"), 1970)})
lv30.index.name = "年"
lv30.round(2).to_csv(RES / "w1_levels_30plus_1970eq100.csv", encoding="utf-8-sig")

# --- 2. 年ごとの寄与（対数差）
gn, gr, gh = G("現金給与総額"), G("実質賃金指数（現金給与総額）"), G("総実労働時間")
d = pd.DataFrame({"名目1人": np.log1p(gn), "実質1人": np.log1p(gr), "時間": np.log1p(gh)}).dropna()
d["物価"] = d["名目1人"] - d["実質1人"]
d["時間当たり名目"] = d["名目1人"] - d["時間"]
# パート比率：名目1人当たり＝一般とパートの賃金の伸び（前年の賃金総額のウェイト）＋構成の変化
J = lambda item, form: series(x, "実数", item, "TL", "T", form, "CY")
wg, wp = J("現金給与総額", "1"), J("現金給与総額", "2")
p = series(x, "指数", "パートタイム労働者比率", "TL", "T", "0", "CY") / 100
gg, gp = G("現金給与総額", "1"), G("現金給与総額", "2")
rows = []
for y in d.index:
    if y - 1 not in wg.index or y not in gg.index or y - 1 not in p.index: continue
    sg = (1 - p[y - 1]) * wg[y - 1]; sp = p[y - 1] * wp[y - 1]
    within_g, within_p = sg / (sg + sp) * gg[y], sp / (sg + sp) * gp[y]
    rows.append({"年": y, "一般労働者の賃金": within_g, "パートの賃金": within_p,
                 "パート比率の変化": gn[y] - within_g - within_p, "パート比率": p[y]})
pc = pd.DataFrame(rows).set_index("年")
d = d.join(pc)
d.round(5).to_csv(RES / "w1_decomp_annual.csv", encoding="utf-8-sig")

# 期間ごとの合計（％ポイント、対数差×100）
periods = [(1991, 1997), (1997, 2012), (2012, 2021), (2021, 2025)]
cols = ["実質1人", "時間当たり名目", "時間", "物価", "名目1人", "一般労働者の賃金", "パートの賃金", "パート比率の変化"]
tab = pd.DataFrame({f"{a}→{b}年": 100 * d.loc[a + 1:b, cols].sum() for a, b in periods}).T
tab["物価"] = -tab["物価"]  # 実質へのマイナスの寄与として表示
tab = tab.rename(columns={"物価": "物価（実質への寄与）"})
tab.round(1).to_csv(RES / "w1_decomp_periods.csv", encoding="utf-8-sig")
print(tab.round(1).to_string())

# --- 3. 直近の月次（前年同月比）
m = x[(x["種別"] == "伸び率") & (x["産業分類"] == "TL") & (x["規模"] == "T") & (x["就業形態"] == "0") & (x["月"] != "CY")]
m = m[m["年"] >= 2022].copy()
m["年月"] = m["年"].astype(str) + "-" + m["月"]
mm = m.set_index("年月")[["現金給与総額", "実質賃金指数（現金給与総額）", "きまって支給する給与", "実質賃金指数（きまって支給する給与）", "総実労働時間"]].sort_index()
mm["物価（推計）"] = 100 * ((1 + mm["現金給与総額"] / 100) / (1 + mm["実質賃金指数（現金給与総額）"] / 100) - 1)
mm.round(2).to_csv(RES / "w1_monthly_since2022.csv", encoding="utf-8-sig")
pos = (mm["実質賃金指数（現金給与総額）"] > 0)
print("月次", mm.index[0], "〜", mm.index[-1], "実質プラスの月", pos.sum(), "/", len(mm), "プラス月:", list(mm.index[pos]))
print(mm.tail(8).round(1).to_string())

# --- 図1：水準
fig, ax = plt.subplots(figsize=(8, 4.6))
for c_, col, ls in [("名目賃金（1人当たり）", BLUE, "-"), ("実質賃金（1人当たり）", ORANGE, "-"), ("物価", GRAY, "--"),
                    ("実質賃金（1時間当たり）", GREEN, "-")]:
    ax.plot(lv.index, lv[c_], color=col, ls=ls, lw=2, label=c_)
    ax.text(lv.index[-1] + 0.4, lv[c_].iloc[-1], f"{lv[c_].iloc[-1]:.0f}", color=col, va="center", fontsize=9)
ax.axhline(100, color=INK, lw=0.6)
ax.set_title("1990年を100とした名目賃金・実質賃金・物価（規模5人以上、年平均）", loc="left")
ax.legend(frameon=False, fontsize=9, loc="lower left"); ax.set_xlim(1990, 2027.5)
note(ax, SOURCE + "。公表の前年比をつないで作成", -0.1)
fig.savefig(FIG / "w1_levels.png"); plt.close(fig)

# --- 図2：年ごとの寄与
fig, ax = plt.subplots(figsize=(8.6, 4.6))
yy = d.index
parts = [("時間当たり名目", BLUE, "時間当たりの名目賃金"), ("時間", GREEN, "労働時間"), ("物価", ORANGE, "物価（マイナスで表示）")]
pos_b = np.zeros(len(yy)); neg_b = np.zeros(len(yy))
for k, col, lab in parts:
    v = 100 * (d[k] if k != "物価" else -d[k]).values
    b = np.where(v >= 0, pos_b, neg_b)
    ax.bar(yy, v, bottom=b, color=col, width=0.8, label=lab)
    pos_b += np.where(v >= 0, v, 0); neg_b += np.where(v < 0, v, 0)
ax.plot(yy, 100 * d["実質1人"], color=INK, marker="o", ms=3, lw=1.3, label="実質賃金（1人当たり）")
ax.axhline(0, color=INK, lw=0.6)
ax.set_title("実質賃金の前年比の内訳（％、対数差）", loc="left")
ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="lower left")
note(ax, SOURCE, -0.1)
fig.savefig(FIG / "w1_decomp.png"); plt.close(fig)

# --- 図3：名目1人当たりの伸びの累積：一般・パート・パート比率
fig, ax = plt.subplots(figsize=(8, 4.6))
q = d[["一般労働者の賃金", "パートの賃金", "パート比率の変化", "名目1人"]].dropna()
cum = 100 * q.cumsum()
for k, col in [("一般労働者の賃金", BLUE), ("パートの賃金", GREEN), ("パート比率の変化", ORANGE), ("名目1人", INK)]:
    ax.plot(cum.index, cum[k], color=col, lw=2 if k != "名目1人" else 1.4, ls="-" if k != "名目1人" else "--",
            label={"名目1人": "名目賃金（1人当たり）の合計"}.get(k, k))
    ax.text(cum.index[-1] + 0.4, cum[k].iloc[-1], f"{cum[k].iloc[-1]:+.1f}", color=col, va="center", fontsize=9)
ax.axhline(0, color=INK, lw=0.6)
ax.set_title(f"1人当たり名目賃金の伸びの累計を3つに分ける（{q.index[0]-1}年から、％ポイント）", loc="left")
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_xlim(q.index[0] - 1, 2027.5)
note(ax, SOURCE, -0.1)
fig.savefig(FIG / "w1_part.png"); plt.close(fig)
print(lv.loc[[1990, 1996, 1997, 2012, 2019, 2020, 2021, 2022, 2023, 2024, 2025]].round(1).to_string())
print(d[["パート比率"]].dropna().iloc[[0, -1]])
print(lv30.loc[[1970, 1996, 1997, 2025]].round(1))
