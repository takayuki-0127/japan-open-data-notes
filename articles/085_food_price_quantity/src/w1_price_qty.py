"""W1：値上げで「量」を減らした品目・減らさなかった品目
- 2021→2025年の品目ごとの平均価格と購入数量の変化（二人以上の世帯の平均、食料の末端品目）
- 食料の品目をまとめた価格指数・数量指数（トルンクビスト式の連鎖、2021年＝100）
- 見かけの価格弾力性：年の差分（Δlog 数量 = β Δlog 価格 + 年の効果 + 品目の効果）。
  平均価格は「支出金額÷購入数量」なので、数量の標本誤差がそのまま価格に逆向きで入り、βが負に偏る（division bias）。
  そこで五分位を2つの組（Ⅰ・Ⅲ・Ⅴ／Ⅱ・Ⅳ）に分け、片方の組の数量の変化を、もう片方の組の価格の変化を操作変数にして推定する（標準誤差は品目でクラスター）"""
from common import *

m = merged_panel()
food = m[m.big == "食料"].copy()

# ---- 1. 2021→2025年 ----
B, E = 2021, 2025
w = food.pivot_table(index="code", columns="year", values=["E", "Q", "P"])
info = food.groupby("code")[["name", "mid"]].last()
d = info.assign(E21=w["E"][B], E25=w["E"][E], P21=w["P"][B], P25=w["P"][E], Q21=w["Q"][B], Q25=w["Q"][E]).dropna()
d["price_pct"] = (d.P25 / d.P21 - 1) * 100
d["qty_pct"] = (d.Q25 / d.Q21 - 1) * 100
d["spend_pct"] = (d.E25 / d.E21 - 1) * 100
d = d.sort_values("price_pct", ascending=False)
d.round(2).to_csv(RES / "w1_items_2021_2025.csv", encoding="utf-8-sig")
wt = d.E21 / d.E21.sum()
lp, lq = np.log(d.P25 / d.P21), np.log(d.Q25 / d.Q21)
summary = {"items": len(d), "price_up_share": (d.price_pct > 0).mean(), "price_up_qty_down_share": ((d.price_pct > 0) & (d.qty_pct < 0)).mean(),
           "wavg_price_pct": (np.exp((wt * lp).sum()) - 1) * 100, "wavg_qty_pct": (np.exp((wt * lq).sum()) - 1) * 100,
           "big20_price_up_qty_not_down": ", ".join(d[(d.price_pct >= 20) & (d.qty_pct >= -5)].name)}
print(summary)

# ---- 2. 連鎖の価格指数・数量指数 ----
rows = []
for y in range(2008, 2026):
    a, b = food[food.year == y - 1].set_index("code"), food[food.year == y].set_index("code")
    ix = a.index.intersection(b.index)
    a, b = a.loc[ix], b.loc[ix]
    s = (a.E / a.E.sum() + b.E / b.E.sum()) / 2
    rows.append({"year": y, "dlp": (s * np.log(b.P / a.P)).sum(), "dlq": (s * np.log(b.Q / a.Q)).sum(), "n": len(ix)})
ch = pd.DataFrame(rows)
ch = pd.concat([pd.DataFrame([{"year": 2007, "dlp": 0, "dlq": 0, "n": np.nan}]), ch])
ch["price_idx"] = np.exp(ch.dlp.cumsum()); ch["qty_idx"] = np.exp(ch.dlq.cumsum())
for c in ["price_idx", "qty_idx"]:
    ch[c] = ch[c] / ch.loc[ch.year == B, c].iloc[0] * 100
ch.round(4).to_csv(RES / "w1_food_index.csv", index=False)
print(ch[["year", "price_idx", "qty_idx"]].round(1).to_string(index=False))

# ---- 3. 見かけの価格弾力性 ----
A_, B_ = [1, 3, 5], [2, 4]
for g, ix in (("A", A_), ("B", B_)):
    food["E" + g] = food[[f"E{j}" for j in ix]].mean(1)
    food["Q" + g] = food[[f"Q{j}" for j in ix]].mean(1)
    food["P" + g] = food["E" + g] / food["Q" + g]
food = food.sort_values(["code", "year"])
for c in ["Q", "P", "QA", "PA", "QB", "PB"]:
    food["d" + c] = food.groupby("code")[c].transform(lambda s: np.log(s).diff())
food["gap"] = food.groupby("code").year.diff()
p = food[food.gap == 1].replace([np.inf, -np.inf], np.nan).dropna(subset=["dQ", "dP", "dQA", "dPA", "dQB", "dPB"])


def demean(df, cols, fe):
    X = df[cols].copy()
    for _ in range(100):
        for f in fe:
            X = X - X.groupby(df[f].values).transform("mean")
    return X


def iv(df, y, x, z, fe):
    D = demean(df, list(dict.fromkeys([y, x, z])), fe)
    Y, X, Z = D[y].values, D[x].values, D[z].values
    b = (Z @ Y) / (Z @ X); u = Y - b * X
    cl = df["code"].values
    num = sum(((Z[cl == c] * u[cl == c]).sum()) ** 2 for c in np.unique(cl))
    return b, np.sqrt(num) / abs(Z @ X)


s1 = p[["year", "code", "mid"]].assign(y=p.dQA, x=p.dPA, z=p.dPB, half="A")
s2 = p[["year", "code", "mid"]].assign(y=p.dQB, x=p.dPB, z=p.dPA, half="B")
st = pd.concat([s1, s2])
st["yh"] = st.year.astype(str) + st.half; st["ch"] = st.code + st.half
res = []
b, se = iv(p, "dQ", "dP", "dP", ("year", "code")); res.append({"group": "食料全体（平均で最小二乗）", "items": p.code.nunique(), "beta": b, "se": se})
b, se = iv(st, "y", "x", "z", ("yh", "ch")); res.append({"group": "食料全体", "items": p.code.nunique(), "beta": b, "se": se})
b, se = iv(st[st.year != 2018], "y", "x", "z", ("yh", "ch")); res.append({"group": "食料全体（2017→18年を除く）", "items": p.code.nunique(), "beta": b, "se": se})
for mid, g in st.groupby("mid"):
    b, se = iv(g, "y", "x", "z", ("yh", "ch"))
    res.append({"group": mid, "items": g.code.nunique(), "beta": b, "se": se})
res = pd.DataFrame(res)
res["lo"], res["hi"] = res.beta - 1.96 * res.se, res.beta + 1.96 * res.se
res.round(3).to_csv(RES / "w1_elasticity.csv", index=False, encoding="utf-8-sig")
print(res.round(3).to_string(index=False))

# ---- 図 ----
# 図1：2021→2025年の価格と数量
fig, ax = plt.subplots(figsize=(8.2, 6))
sz = d.E21 / d.E21.max() * 900 + 8
ax.scatter(d.price_pct, d.qty_pct, s=sz, color=BLUE, alpha=.35, edgecolor="white", lw=.5)
ax.axhline(0, color=GRAY, lw=.8); ax.axvline(0, color=GRAY, lw=.8)
lab = {"米": (-6, 8), "卵": (6, 4), "キャベツ": (6, -10), "はくさい": (6, 2), "コーヒー": (6, 4), "ほたて貝": (6, 2), "あさり": (6, 2),
       "食用油": (6, -10), "牛乳": (-30, -12), "食パン": (6, 4), "牛肉": (-30, -12), "豚肉": (-30, 6), "鶏肉": (6, 4), "バナナ": (6, 4),
       "りんご": (6, 2), "ビール": (6, 4), "発泡酒": (6, -10)}
for _, r in d[d.name.isin(list(lab))].iterrows():
    ax.annotate(r["name"], (r.price_pct, r.qty_pct), fontsize=8.5, xytext=lab[r["name"]], textcoords="offset points", color=INK)
ax.set_xlabel("平均価格の変化（%）"); ax.set_ylabel("購入数量の変化（%）")
ax.set_title(f"2021→2025年：値上がりした品目と、買った量の変化（食料{len(d)}品目）", loc="left")
ax.set_ylim(-80, 60)
note(ax, SOURCE + "（二人以上の世帯、1世帯当たり年間。円の大きさは2021年の支出金額）", y=-0.11)
fig.savefig(FIG / "w1_scatter.png"); plt.close(fig)

# 図2：連鎖指数
fig, ax = plt.subplots(figsize=(8.2, 4.6))
ax.plot(ch.year, ch.price_idx, color=ORANGE, lw=2.2, marker="o", ms=3.5, label="価格（平均価格）")
ax.plot(ch.year, ch.qty_idx, color=BLUE, lw=2.2, marker="o", ms=3.5, label="量（購入数量）")
ax.axhline(100, color=GRAY, lw=.8)
for c, col in (("price_idx", ORANGE), ("qty_idx", BLUE)):
    v = ch[c].iloc[-1]; ax.text(2025.25, v, f"{v:.0f}", color=col, va="center", fontsize=10)
ax.set_xticks(range(2007, 2026, 2)); ax.set_ylabel("2021年＝100")
ax.set_title(f"食料{food.code.nunique()}品目をまとめた価格と量（連鎖指数）", loc="left"); ax.legend(frameon=False, loc="upper left")
note(ax, SOURCE + "（二人以上の世帯。トルンクビスト式で前年とつないだ）", y=-0.13)
fig.savefig(FIG / "w1_index.png"); plt.close(fig)

# 図3：分類別の弾力性
r = res[~res.group.str.startswith("食料全体") & (res["items"] >= 4) & (res.group != "酒類")].sort_values("beta")
allr = res[res.group == "食料全体"].iloc[0]
fig, ax = plt.subplots(figsize=(8.2, 4.8))
yy = np.arange(len(r))
ax.errorbar(r.beta, yy, xerr=1.96 * r.se, fmt="o", color=BLUE, ecolor=LIGHT, elinewidth=4, capsize=0, ms=7)
ax.axvline(0, color=GRAY, lw=.8); ax.axvline(allr.beta, color=ORANGE, lw=1.2, ls="--")
ax.text(allr.beta, -.75, f" 食料全体 {allr.beta:.2f}", color=ORANGE, fontsize=9.5)
ax.set_ylim(-1, len(r) - .4)
ax.set_yticks(yy); ax.set_yticklabels([f"{g}（{n}品目）" for g, n in zip(r.group, r["items"])])
for yv, b in zip(yy, r.beta):
    ax.text(b, yv + .22, f"{b:.2f}", ha="center", fontsize=9, color=INK)
ax.set_xlabel("価格が1%上がったときの購入数量の変化（%）")
ax.set_title("見かけの価格弾力性（2007〜2025年の年ごとの変化、95%区間）", loc="left")
note(ax, SOURCE + "（五分位を2組に分けた操作変数法、年と品目の効果を除く。酒類は品目が少なく不安定なので省いた）", y=-0.15)
fig.savefig(FIG / "w1_elasticity.png"); plt.close(fig)
