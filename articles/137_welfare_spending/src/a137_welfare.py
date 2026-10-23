"""市区町村の歳出のうち、民生費（福祉）はどれだけを占め、何が増えたか（2012・2016・2020・2024年度決算）"""
from common import *

d = load()
Y = [2012, 2016, 2020, 2024]
g = d.groupby("fiscal_year").sum(numeric_only=True)
L = []
for y in Y:
    L.append(f"{y}年度 歳出合計 {g.loc[y,'歳出合計']/1e9:.2f}兆円  民生費 {g.loc[y,'民生費・総額']/1e9:.2f}兆円（{g.loc[y,'民生費・総額']/g.loc[y,'歳出合計']:.1%}）"
             f"  総務費を除く歳出に対して {g.loc[y,'民生費・総額']/(g.loc[y,'歳出合計']-g.loc[y,'総務費・総額']):.1%}  団体数 {int((d.fiscal_year==y).sum())}")
L.append(f"2012→2024 民生費 {g.loc[2024,'民生費・総額']/g.loc[2012,'民生費・総額']-1:+.1%}、歳出合計 {g.loc[2024,'歳出合計']/g.loc[2012,'歳出合計']-1:+.1%}")
for c, n in ITEMS.items():
    L.append(f"{n}: " + "、".join(f"{y}年度 {g.loc[y,c]/1e9:.2f}兆円（民生費の{g.loc[y,c]/g.loc[y,'民生費・総額']:.1%}）" for y in Y)
             + f"  2012→2024 {g.loc[2024,c]/g.loc[2012,c]-1:+.1%}")
for c in ["国庫支出金", "都道府県支出金", "地方債", "一般財源等"]:
    L.append(f"民生費の財源 {c}: " + "、".join(f"{y} {g.loc[y,'民生費財源・'+c]/g.loc[y,'民生費・総額']:.1%}" for y in Y))
kan = ["総務費・総額", "衛生費・総額", "土木費・総額", "教育費・総額", "公債費"]
for c in kan:
    L.append(f"{c} 歳出に占める割合 2012 {g.loc[2012,c]/g.loc[2012,'歳出合計']:.1%} → 2024 {g.loc[2024,c]/g.loc[2024,'歳出合計']:.1%}")
g.to_csv(RES / "a137_national.csv", encoding="utf-8")

x = d[d.fiscal_year == 2024].copy()
order = ["東京23区", "中核市", "政令指定都市", "その他の市", "町村"]
gg = x.groupby("group").sum(numeric_only=True).loc[order]
grp = gg[["民生費・総額"] + list(ITEMS)].div(gg["歳出合計"], axis=0)
grp["団体数"] = x.groupby("group").size().loc[order]
grp["割合の中央値"] = x.groupby("group").share.median().loc[order]
grp.to_csv(RES / "a137_group_2024.csv", encoding="utf-8")
L.append("2024年度 区分別（合計で割った割合）:\n" + grp.round(3).to_string())
md = d.groupby("fiscal_year").share.median()
L.append("市区町村ごとの割合の中央値: " + "、".join(f"{y} {md[y]:.1%}" for y in Y))
L.append(f"2024年度 40%以上 {(x.share>=0.4).sum()}団体（{(x.share>=0.4).mean():.1%}）、50%以上 {(x.share>=0.5).sum()}、20%未満 {(x.share<0.2).sum()}")
w = d[d.fiscal_year == 2012]
L.append(f"2012年度 40%以上 {(w.share>=0.4).sum()}団体（{(w.share>=0.4).mean():.1%}）、50%以上 {(w.share>=0.5).sum()}、20%未満 {(w.share<0.2).sum()}")
m = d.pivot_table(index="code", columns="fiscal_year", values="share")[[2012, 2024]].dropna()
L.append(f"2012・2024年度の両方ある {len(m)}団体のうち割合が上がった {(m[2024]>m[2012]).sum()}（{(m[2024]>m[2012]).mean():.1%}）")
cols = ["pref", "name", "group", "share", "民生費・総額", "歳出合計"]
top, low = x.nlargest(15, "share")[cols], x.nsmallest(15, "share")[cols]
pd.concat([top.assign(rank="上位"), low.assign(rank="下位")]).to_csv(RES / "a137_rank_2024.csv", index=False, encoding="utf-8")
L.append("上位:\n" + top[["pref", "name", "group", "share"]].round(3).to_string(index=False))
L.append("下位:\n" + low[["pref", "name", "group", "share"]].round(3).to_string(index=False))
(RES / "a137_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：市区町村の民生費（合計）と内訳、歳出に占める割合
fig, ax = plt.subplots(figsize=(9.5, 4.6))
cols_c = [ORANGE, BLUE, GREEN, PURPLE]
bottom = np.zeros(len(Y)); xs = np.arange(len(Y))
for (c, n), col in zip(ITEMS.items(), cols_c):
    v = g.loc[Y, c].values / 1e9
    ax.bar(xs, v, bottom=bottom, color=col, width=0.6, label=n)
    bottom += v
other = g.loc[Y, "民生費・総額"].values / 1e9 - bottom
ax.bar(xs, other, bottom=bottom, color=GRAY, width=0.6, label="災害救助費")
for i, y in enumerate(Y):
    ax.text(i, g.loc[y, "民生費・総額"] / 1e9 + 0.4, f"{g.loc[y,'民生費・総額']/1e9:.1f}兆円\n（歳出の{g.loc[y,'民生費・総額']/g.loc[y,'歳出合計']:.0%}）",
            ha="center", va="bottom", fontsize=10)
ax.set_xticks(xs); ax.set_xticklabels([f"{y}年度" for y in Y]); ax.set_ylim(0, 33)
ax.set_ylabel("兆円"); ax.legend(loc="upper left", fontsize=9, frameon=False, ncol=1)
ax.set_title("全国の市区町村の民生費（合計）と内訳")
ax.text(2, 29.0, "2020年度は特別定額給付金（総務費）で\n歳出全体がふくらみ、割合は下がった", ha="center", fontsize=8.5, color=GRAY)
save(fig, "a137_national.png")

# 図2：区分別、歳出に占める民生費の内訳（2024年度）
fig, ax = plt.subplots(figsize=(9.5, 4.2))
left = np.zeros(len(order)); ys = np.arange(len(order))[::-1]
for (c, n), col in zip(ITEMS.items(), cols_c):
    v = grp[c].values * 100
    ax.barh(ys, v, left=left, color=col, height=0.6, label=n)
    left += v
rest = grp["民生費・総額"].values * 100 - left
ax.barh(ys, rest, left=left, color=GRAY, height=0.6)
for yy, tot, n in zip(ys, grp["民生費・総額"].values * 100, grp["団体数"].values):
    ax.text(tot + 0.6, yy, f"{tot:.0f}%", va="center", fontsize=10)
ax.set_yticks(ys); ax.set_yticklabels([f"{o}（{n}）" for o, n in zip(order, grp['団体数'].values)])
ax.set_xlim(0, 60); ax.set_xlabel("歳出合計に占める割合（%、2024年度、区分ごとの合計で計算）")
ax.legend(loc="lower right", fontsize=9, frameon=False)
ax.set_title("歳出に占める民生費と内訳（2024年度）")
save(fig, "a137_groups.png")

# 図3：市区町村ごとの民生費の割合の分布（2012年度と2024年度）
fig, ax = plt.subplots(figsize=(9.5, 4.2))
bins = np.arange(0, 0.62, 0.02)
ax.hist(w.share, bins=bins, color=GRAY, alpha=0.6, label=f"2012年度（中央値 {md[2012]:.0%}）")
ax.hist(x.share, bins=bins, histtype="step", color=BLUE, lw=2.2, label=f"2024年度（中央値 {md[2024]:.0%}）")
ax.set_xticks(np.arange(0, 0.61, 0.1)); ax.set_xticklabels([f"{v:.0%}" for v in np.arange(0, 0.61, 0.1)])
ax.set_xlabel("歳出合計に占める民生費の割合"); ax.set_ylabel("市区町村の数")
ax.legend(frameon=False, fontsize=10)
ax.set_title("市区町村ごとの民生費の割合（1,741団体）")
save(fig, "a137_dist.png")
