"""売上高の上位1%の企業が全体の何割を占めるか（令和3年経済センサス‐活動調査 主要統計表 第9表）"""
from common import *
from scipy.optimize import brentq

d = load("enterprises_by_sales_class_2021.csv")
CL = ["300万円未満", "300～1000万円未満", "1000～3000万円未満", "3000万円～1億円未満", "1～3億円未満", "3～10億円未満", "10～100億円未満", "100億円以上"]
LO = [0, 3, 10, 30, 100, 300, 1000, 10000]  # 百万円
HI = LO[1:] + [np.inf]


def tp_alpha(L, U, m):
    """[L,U] の切断パレート分布で平均が m になる α"""
    def mean(a):
        r = (L / U) ** a
        if abs(a - 1) < 1e-9:
            return L * np.log(U / L) / (1 - r)
        return a * L ** a * (U ** (1 - a) - L ** (1 - a)) / ((1 - a) * (1 - r))
    return brentq(lambda a: mean(a) - m, 1e-4, 50)


def top_share(g, p):
    """上位 p（企業数の割合）の売上シェア。境界の階級内は（切断）パレート分布で補間"""
    g = g.set_index("sales_class").loc[CL]
    N, S = g.enterprises.sum(), g.sales_million_yen.sum()
    need, acc = p * N, 0.0
    for i in range(7, -1, -1):
        n, s = g.enterprises.iloc[i], g.sales_million_yen.iloc[i]
        if n == 0:
            continue
        if need >= n:
            need -= n; acc += s; continue
        q = need / n; L, U, m = LO[i], HI[i], s / n
        if i == 7:  # 上は開いた階級：パレート
            a = m / (m - L); t = L * q ** (-1 / a); acc += need * a * t / (a - 1)
        elif L == 0:
            acc += s * q  # 最下位階級は一様とみなす
        else:
            a = tp_alpha(L, U, m); r = (L / U) ** a
            t = L / (q * (1 - r) + r) ** (1 / a)  # 上位 q の下限（P(X>t)=q）
            if abs(a - 1) < 1e-9:
                part = L * np.log(U / t) / (1 - r)
            else:
                part = a * L ** a * (U ** (1 - a) - t ** (1 - a)) / ((1 - a) * (1 - r))
            acc += n * part
        return acc / S, (L, U)
    return acc / S, None


def lorenz(g):
    g = g.set_index("sales_class").loc[CL]
    x = np.r_[0, g.enterprises.cumsum() / g.enterprises.sum()]
    y = np.r_[0, g.sales_million_yen.cumsum() / g.sales_million_yen.sum()]
    return x, y


def gini(g):
    x, y = lorenz(g)
    return 1 - np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1]))


a = d[d.industry == "全産業"]
g = a[a.sales_class != "計"].set_index("sales_class").loc[CL]
g["firm_share_pct"] = g.enterprises / g.enterprises.sum() * 100
g["sales_share_pct"] = g.sales_million_yen / g.sales_million_yen.sum() * 100
g["gva_share_pct"] = g.gross_value_added_million_yen / g.gross_value_added_million_yen.sum() * 100
g["mean_sales_oku"] = g.sales_million_yen / g.enterprises / 100
g.round(3).to_csv(RES / "a185_by_class_all.csv", encoding="utf-8")
L = []
N, S = g.enterprises.sum(), g.sales_million_yen.sum()
L.append(f"企業等数 {N:,}、売上（収入）金額 {S/1e6:.1f}兆円")
top = g.iloc[::-1]
cf = top.enterprises.cumsum() / N * 100; cs = top.sales_million_yen.cumsum() / S * 100; cv = top.gross_value_added_million_yen.cumsum() / g.gross_value_added_million_yen.sum() * 100
for k in CL[::-1][:4]:
    L.append(f"売上{k}以上の累計：企業 {top.enterprises.cumsum()[k]:,}（{cf[k]:.2f}%）、売上 {cs[k]:.1f}%、粗付加価値 {cv[k]:.1f}%")
L.append(f"売上3000万円未満（{g.loc[CL[:3],'firm_share_pct'].sum():.1f}%の企業）の売上シェア {g.loc[CL[:3],'sales_share_pct'].sum():.2f}%")
L.append(f"売上1億円未満（{g.loc[CL[:4],'firm_share_pct'].sum():.1f}%の企業）の売上シェア {g.loc[CL[:4],'sales_share_pct'].sum():.2f}%、粗付加価値 {g.loc[CL[:4],'gva_share_pct'].sum():.2f}%")
for p in [0.001, 0.01, 0.05, 0.10]:
    sh, _ = top_share(a[a.sales_class != "計"], p)
    L.append(f"上位{p*100:g}%（{p*N:,.0f}社）の売上シェア（パレート補間）{sh*100:.1f}%")
# 上位1%の上限・下限（10〜100億の階級内）
n7, s7 = g.enterprises.iloc[6], g.sales_million_yen.iloc[6]; k = 0.01 * N - g.enterprises.iloc[7]
lo = (g.sales_million_yen.iloc[7] + k * s7 / n7) / S; hi = (g.sales_million_yen.iloc[7] + min(k * 10000, s7 - (n7 - k) * 1000)) / S
L.append(f"上位1%の売上シェアの範囲（階級内の分布を仮定しない）：{lo*100:.1f}〜{hi*100:.1f}%")
L.append(f"ジニ係数（階級データの折れ線、下限） {gini(a[a.sales_class!='計']):.3f}")
rows = []
for ind, h in d[d.sales_class != "計"].groupby("industry"):
    if ind in ["全産業", "非農林漁業"]:
        continue
    hh = h.set_index("sales_class").loc[CL]
    t1, _ = top_share(h, 0.01)
    rows.append((ind, hh.enterprises.sum(), hh.sales_million_yen.sum() / 1e6, hh.enterprises.iloc[7] / hh.enterprises.sum() * 100,
                 hh.sales_million_yen.iloc[7] / hh.sales_million_yen.sum() * 100, t1 * 100, gini(h)))
ii = pd.DataFrame(rows, columns=["industry", "enterprises", "sales_trillion_yen", "firm_share_100oku_pct", "sales_share_100oku_pct", "top1pct_sales_share_pct", "gini_lower"]).sort_values("top1pct_sales_share_pct", ascending=False)
ii.round(3).to_csv(RES / "a185_by_industry.csv", index=False, encoding="utf-8")
L.append("産業別 上位1%の売上シェア：" + "、".join(f"{r.industry} {r.top1pct_sales_share_pct:.1f}%" for r in ii.itertuples()))
L.append("産業別 100億円以上の企業割合と売上シェア：" + "、".join(f"{r.industry} {r.firm_share_100oku_pct:.2f}%→{r.sales_share_100oku_pct:.1f}%" for r in ii.itertuples()))
(RES / "a185_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1 ローレンツ曲線（上位から）
x, y = lorenz(a[a.sales_class != "計"])
fig, ax = plt.subplots(figsize=(7.5, 5.5))
tx, ty = (1 - x[::-1]) * 100, (1 - y[::-1]) * 100
ax.plot(tx, ty, "-o", color=BLUE, ms=4)
ax.plot([0, 100], [0, 100], color=GRAY, ls="--", lw=.8)
t1, _ = top_share(a[a.sales_class != "計"], .01)
ax.scatter([1], [t1 * 100], color=ORANGE, zorder=4, s=50)
ax.annotate(f"上位1%で約{t1*100:.0f}%（推計）", (1, t1 * 100), xytext=(5, 70), color=ORANGE, arrowprops=dict(arrowstyle="-", color=ORANGE))
ax.annotate(f"売上100億円以上\n企業の{cf['100億円以上']:.2f}%で売上の{cs['100億円以上']:.1f}%", (cf["100億円以上"], cs["100億円以上"]), xytext=(6, 55), arrowprops=dict(arrowstyle="-", color=GRAY), fontsize=9.5)
ax.annotate(f"売上10億円以上\n{cf['10～100億円未満']:.1f}%で{cs['10～100億円未満']:.1f}%", (cf["10～100億円未満"], cs["10～100億円未満"]), xytext=(10, 78), arrowprops=dict(arrowstyle="-", color=GRAY), fontsize=9.5)
ax.set_xlim(0, 25); ax.set_ylim(0, 102)
ax.set_xlabel("売上の大きい順に並べた企業の累積割合（%、上位25%まで）"); ax.set_ylabel("売上（収入）金額の累積割合（%）")
ax.set_title("売上の集中（全産業、2020年の売上、企業等）")
save(fig, "a185_lorenz.png")
# 図2 階級別の企業割合と売上割合
fig, ax = plt.subplots(figsize=(9.5, 4.8))
xx = np.arange(8); w = .38
ax.bar(xx - w / 2, g.firm_share_pct, w, color=LIGHT, label="企業等数の割合")
ax.bar(xx + w / 2, g.sales_share_pct, w, color=BLUE, label="売上（収入）金額の割合")
for i in range(8):
    ax.text(i - w / 2, g.firm_share_pct.iloc[i] + 1, f"{g.firm_share_pct.iloc[i]:.1f}", ha="center", fontsize=8.5)
    ax.text(i + w / 2, g.sales_share_pct.iloc[i] + 1, f"{g.sales_share_pct.iloc[i]:.1f}", ha="center", fontsize=8.5)
ax.set_xticks(xx, ["300万円\n未満", "300万〜\n1000万円", "1000万〜\n3000万円", "3000万〜\n1億円", "1億〜\n3億円", "3億〜\n10億円", "10億〜\n100億円", "100億円\n以上"], fontsize=9)
ax.set_ylabel("%"); ax.set_ylim(0, 78); ax.legend(frameon=False, loc="upper left")
ax.set_title("売上金額の階級別、企業等数と売上の割合（全産業）")
save(fig, "a185_classes.png")
# 図3 産業別
jj = ii.sort_values("top1pct_sales_share_pct")
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(jj.industry, jj.top1pct_sales_share_pct, color=BLUE)
for i, r in enumerate(jj.itertuples()):
    ax.text(r.top1pct_sales_share_pct + .8, i, f"{r.top1pct_sales_share_pct:.0f}%", va="center", fontsize=9)
ax.axvline(t1 * 100, color=ORANGE, ls="--", lw=1); ax.text(t1 * 100 + .5, len(jj) - .4, f"全産業 {t1*100:.0f}%", color=ORANGE, fontsize=9)
ax.set_xlim(0, 105); ax.set_xlabel("各産業の売上の大きい上位1%の企業が占める売上の割合（%、推計）")
ax.set_title("産業別、上位1%の企業の売上シェア")
save(fig, "a185_industry.png")
