"""昼夜間人口比率（昼間人口÷夜間人口×100）が高い・低い市区町村と、1990〜2020年の変化"""
from common import *

x = load()
MIN = 5000  # 夜間人口5千人未満（福島県の避難指示区域の町村など）は順位から除く
u = units(x)
u = u[u.night >= MIN].copy()
name20 = u[u.year == 2020].set_index("code").apply(lambda r: f"{r['name']}（{r['pref']}）", axis=1)

# 1) 2020年の上位・下位15
g = u[u.year == 2020].sort_values("ratio")
top, bot = g.tail(15), g.head(15)
pd.concat([top.assign(rank="上位"), bot.assign(rank="下位")])[["rank", "code", "pref", "name", "night", "day", "ratio"]] \
    .to_csv(RES / "a125_rank_2020.csv", index=False, encoding="utf-8-sig")
fig, axes = plt.subplots(1, 2, figsize=(11, 6))
for ax, d, c, t in [(axes[0], top, ORANGE, "高い15市区町村"), (axes[1], bot.iloc[::-1], BLUE, "低い15市区町村")]:
    lab = [name20.get(k, n) for k, n in zip(d.code, d.name)]
    ax.barh(lab, d.ratio, color=c)
    ax.axvline(100, color=GRAY, lw=1)
    for i, v in enumerate(d.ratio): ax.text(v, i, f" {v:,.0f}", va="center", fontsize=8)
    ax.set_title(f"昼夜間人口比率が{t}（2020年）")
    ax.set_xlabel("昼間人口÷夜間人口×100")
    if c == ORANGE: ax.set_xscale("log")
note(axes[0], SOURCE + "。夜間人口5千人以上の区・市町村", y=-0.1)
plt.tight_layout(); plt.savefig(FIG / "a125_rank.png"); plt.close()

# 2) 都心の区の30年
keys = ["13101", "13102", "13103", "27128", "23106", "13104"]
p = u.pivot_table(index="year", columns="code", values="ratio")
p[keys].round(1).rename(columns=name20).to_csv(RES / "a125_center_trend.csv", encoding="utf-8-sig")
nd = x[x.code.isin(keys)].pivot_table(index="year", columns="code", values=["night", "day"])
nd.to_csv(RES / "a125_center_night_day.csv", encoding="utf-8-sig")
fig, ax = plt.subplots(figsize=(8, 5))
cols = [ORANGE, BLUE, GREEN, "#7a5bd6", INK, GRAY]
for k, c in zip(keys, cols):
    ax.plot(p.index, p[k], marker="o", color=c, label=name20.get(k, k))
ax.set_yscale("log"); ax.set_ylabel("昼夜間人口比率（対数目盛）")
ax.set_title("都心の区の昼夜間人口比率は30年で下がった")
ax.legend(fontsize=8, ncol=2)
note(ax)
plt.tight_layout(); plt.savefig(FIG / "a125_center.png"); plt.close()

# 3) 分布の変化（ベッドタウン型が減った）
rows = []
for y, gg in u.groupby("year"):
    rows.append(dict(year=y, n=len(gg), median=gg.ratio.median(), lt80=(gg.ratio < 80).mean() * 100,
                     lt90=(gg.ratio < 90).mean() * 100, ge150=(gg.ratio >= 150).sum()))
dist = pd.DataFrame(rows); dist.round(2).to_csv(RES / "a125_distribution.csv", index=False, encoding="utf-8-sig")
b = p.T[[1990, 2020]].dropna()
chg = pd.DataFrame({"r1990": b[1990], "r2020": b[2020]}).assign(diff=lambda d: d.r2020 - d.r1990)
chg["name"] = [name20.get(k, k) for k in chg.index]
chg.sort_values("diff").round(1).to_csv(RES / "a125_change_1990_2020.csv", encoding="utf-8-sig")
fig, ax = plt.subplots(figsize=(7, 6))
ax.scatter(chg.r1990, chg.r2020, s=8, color=BLUE, alpha=0.5)
lim = [40, 3000]
ax.plot(lim, lim, color=GRAY, lw=1)
ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlim(lim); ax.set_ylim(lim)
for k in ["13101", "13102", "27128", "09345", "04424"]:
    if k in chg.index: ax.annotate(chg.at[k, "name"], (chg.at[k, "r1990"], chg.at[k, "r2020"]), fontsize=8)
ax.set_xlabel("1990年"); ax.set_ylabel("2020年")
ax.set_title(f"同じ区・市町村の1990年と2020年（{len(chg):,}）")
note(ax, SOURCE + "。両方の年にある市区町村コードだけ", y=-0.12)
plt.tight_layout(); plt.savefig(FIG / "a125_change.png"); plt.close()

t23 = x[x.code == "13100"][["year", "night", "day", "ratio", "in_other"]]
t23.to_csv(RES / "a125_tokyo23.csv", index=False, encoding="utf-8-sig")
print(top[["name", "ratio"]].tail(5).round(1).to_string()); print(bot[["name", "pref", "ratio"]].head(5).round(1).to_string())
print(dist.round(1).to_string()); print(len(chg), chg["diff"].median())
print(t23.round(1).to_string())

# 合併の影響を除くため、1990年と2020年の両方にある区・市町村だけで比べる
bal = pd.DataFrame([dict(year=y, n=len(chg), lt80=(chg[c] < 80).mean() * 100, lt90=(chg[c] < 90).mean() * 100,
                         median=chg[c].median()) for y, c in [(1990, "r1990"), (2020, "r2020")]])
bal.round(2).to_csv(RES / "a125_balanced.csv", index=False, encoding="utf-8-sig")
print(bal.round(1).to_string())
