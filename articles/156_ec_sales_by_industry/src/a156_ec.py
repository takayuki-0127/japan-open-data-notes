"""ネット販売（一般消費者との電子商取引）の売上比率が高い業種はどこか（経済センサス‐活動調査 2012・2016）"""
from common import *

d = load("ec_by_industry.csv")
for c in d.columns[2:]:
    d[c] = pd.to_numeric(d[c], errors="coerce")  # X（秘匿）・-（該当なし）は欠損
d["code"] = d.industry.str.split(" ").str[0]
d["name"] = d.industry.str.split(" ", n=1).str[1].str.replace("(", "（").str.replace(")", "）")
d["level"] = np.where(d.code.str.fullmatch(r"\d{2}"), "中分類", np.where(d.code.str.fullmatch(r"[A-R]"), "大分類", "計"))
d["ec_firm_rate"] = d.firms_ec / d.firms                     # 電子商取引をした企業の割合
d["b2c_firm_rate"] = d.firms_b2c / d.firms                   # 一般消費者と電子商取引をした企業の割合
d["b2c_sales_share"] = d.b2c_amount / d.sales                # 業種の売上全体に占めるネット販売（BtoC）の額
d["b2c_ratio_in_b2c_firms"] = d.b2c_amount / d.sales_b2c_known  # ネット販売をした企業の売上に占める割合
d.to_csv(RES / "a156_metrics.csv", index=False, encoding="utf-8")

m = d[(d.level == "中分類")].pivot_table(index=["code"], columns="year", values=["b2c_sales_share", "b2c_firm_rate", "b2c_ratio_in_b2c_firms", "b2c_amount", "sales", "firms_b2c"])
names = d[(d.level == "中分類") & (d.year == 2015)].set_index("code").name
big = d[d.level == "大分類"].pivot_table(index="code", columns="year", values=["ec_firm_rate", "b2c_firm_rate", "b2c_sales_share"])
bign = d[(d.level == "大分類") & (d.year == 2015)].set_index("code").name
L = []
tot = d[d.year == 2015][d.level == "大分類"].sum(numeric_only=True); tot11 = d[(d.year == 2011) & (d.level == "大分類")].sum(numeric_only=True)
for y, t in [(2011, tot11), (2015, tot)]:
    L.append(f"{y}年 全産業（大分類の合計）: 企業 {t.firms:,.0f}、EC実施 {t.firms_ec/t.firms:.2%}、BtoC実施 {t.firms_b2c/t.firms:.2%}、BtoC額 {t.b2c_amount/1e6:.2f}兆円＝売上の {t.b2c_amount/t.sales:.2%}、BtoC企業の売上に占める割合 {t.b2c_amount/t.sales_b2c_known:.1%}")
s15 = m["b2c_sales_share"][2015].dropna().sort_values(ascending=False)
L.append("2015 BtoC額/業種売上 上位15:\n" + "\n".join(f"  {c} {names[c]} {v:.2%}（2011 {m['b2c_sales_share'][2011].get(c, np.nan):.2%}） BtoC額 {m['b2c_amount'][2015][c]/100:,.0f}億円 BtoC企業割合 {m['b2c_firm_rate'][2015][c]:.1%}" for c, v in s15.head(15).items()))
L.append("2015 下位10:\n" + "\n".join(f"  {c} {names[c]} {v:.3%}" for c, v in s15.tail(10).items()))
r = m["b2c_ratio_in_b2c_firms"][2015].dropna().sort_values(ascending=False)
L.append("2015 ネット販売をした企業の売上に占めるBtoC額 上位10:\n" + "\n".join(f"  {c} {names[c]} {v:.1%}（企業数 {m['firms_b2c'][2015][c]:,.0f}）" for c, v in r.head(10).items()))
L.append("大分類 EC実施企業割合 2011→2015:\n" + "\n".join(f"  {c} {bign[c]} {big['ec_firm_rate'][2011][c]:.1%}→{big['ec_firm_rate'][2015][c]:.1%}  BtoC額/売上 {big['b2c_sales_share'][2011][c]:.2%}→{big['b2c_sales_share'][2015][c]:.2%}" for c in big.index))
(RES / "a156_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：BtoC額/業種売上 上位15（2015）と2011
top = s15.head(15)[::-1]
fig, ax = plt.subplots(figsize=(9.5, 6))
y = np.arange(len(top))
ax.barh(y, top.values * 100, color=BLUE, height=0.6, label="2015年")
ax.scatter([m["b2c_sales_share"][2011].get(c, np.nan) * 100 for c in top.index], y, color=ORANGE, zorder=3, label="2011年", s=30)
for yy, v, c in zip(y, top.values, top.index):
    ax.text(max(v, m["b2c_sales_share"][2011].get(c, 0) if pd.notna(m["b2c_sales_share"][2011].get(c, np.nan)) else 0) * 100 + 0.8, yy, f"{v*100:.1f}%", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels([names[c] for c in top.index], fontsize=9.5)
ax.set_xlabel("業種の売上全体に占める、一般消費者とのネット販売（BtoC-EC）の額（%）")
ax.legend(frameon=False, loc="lower right"); ax.set_title("ネット販売の売上比率が高い業種（中分類、上位15）")
save(fig, "a156_top.png")

# 図2：大分類 EC実施企業割合
bb = big["ec_firm_rate"][2015].sort_values()
fig, ax = plt.subplots(figsize=(9.5, 5.6))
y = np.arange(len(bb))
ax.barh(y - 0.18, big["ec_firm_rate"][2011][bb.index] * 100, height=0.36, color=LIGHT, label="2011年")
ax.barh(y + 0.18, big["ec_firm_rate"][2015][bb.index] * 100, height=0.36, color=BLUE, label="2015年")
ax.set_yticks(y); ax.set_yticklabels([bign[c] for c in bb.index], fontsize=9.5)
ax.set_xlabel("電子商取引（ネットでの受注・販売）をした企業の割合（%）")
ax.legend(frameon=False, loc="lower right"); ax.set_title("電子商取引をしている企業の割合（大分類）")
save(fig, "a156_firms.png")

# 図3：BtoC企業の割合 × その企業の売上に占めるBtoC額（中分類 2015）
x = m["b2c_firm_rate"][2015] * 100; yv = m["b2c_ratio_in_b2c_firms"][2015] * 100; sz = m["b2c_amount"][2015] / 100
ok = x.notna() & yv.notna() & (m["firms_b2c"][2015] >= 100)
top5 = sz[ok].nlargest(5).index
fig, ax = plt.subplots(figsize=(9.5, 5.6))
ax.scatter(x[ok], yv[ok], s=np.clip(sz[ok] / 40, 8, 700), color=BLUE, alpha=0.55, edgecolor="white")
for c in ok[ok].index:
    if yv[c] > 55 or x[c] > 15 or c in top5:
        ax.annotate(names[c], (x[c], yv[c]), fontsize=8.5, xytext=(4, 3), textcoords="offset points")
ax.set_xlabel("一般消費者とネット販売をした企業の割合（%）"); ax.set_ylabel("その企業の売上に占めるネット販売の額（%）")
ax.set_title("ネット販売をする企業の多さと、売上に占める大きさ（中分類、2015年）\n円の大きさはネット販売の額")
save(fig, "a156_scatter.png")
