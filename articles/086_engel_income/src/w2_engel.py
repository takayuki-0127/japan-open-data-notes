"""W2：年収五分位別のエンゲル係数と、物価高の負担の差
- エンゲル係数＝食料÷消費支出（五分位別、2007〜2025年）
- 2021年に買っていた食料とエネルギー（電気代・プロパンガス・灯油・ガソリン）を、2025年の平均価格で買い直すといくら増えるか
  （ラスパイレス式。重みは各五分位の2021年の支出、価格の変化は二人以上の世帯全体の平均価格で共通）
- 食料の購入数量の変化（五分位別、トルンクビスト式）"""
from common import *

QN = {0: "平均", 1: "Ⅰ（低い）", 2: "Ⅱ", 3: "Ⅲ", 4: "Ⅳ", 5: "Ⅴ（高い）"}
t = totals()
t["engel"] = t.food / t.cons * 100
eng = t.pivot(index="year", columns="quintile", values="engel").rename(columns=QN)
eng.round(2).to_csv(RES / "w2_engel.csv", encoding="utf-8-sig")
print(eng.round(1).to_string())

m = merged_panel()
m = m[(m.big == "食料") | m.name.isin(ENERGY)].copy()
m["grp"] = np.where(m.big == "食料", "食料", "エネルギー")
B, E = 2021, 2025
x, z = m[m.year == B].set_index("code"), m[m.year == E].set_index("code")
ix = x.index.intersection(z.index); x, z = x.loc[ix], z.loc[ix]
rel = z.P / x.P
cons = t[t.year == B].set_index("quintile").cons
rows = []
for j in range(0, 6):
    Ej = x.E if j == 0 else x[f"E{j}"]
    extra = Ej * (rel - 1)
    r = {"quintile": QN[j], "cons_2021_month": cons[j] / 12, "basket_2021_month": Ej.sum() / 12,
         "basket_share_pct": Ej.sum() / cons[j] * 100, "basket_price_pct": extra.sum() / Ej.sum() * 100,
         "extra_month_yen": extra.sum() / 12, "extra_pct_of_cons": extra.sum() / cons[j] * 100}
    for g in ["食料", "エネルギー"]:
        r[f"extra_pct_of_cons_{g}"] = extra[x.grp == g].sum() / cons[j] * 100
    # 食料の購入数量（トルンクビスト式）
    f = x.grp == "食料"
    if j == 0:
        q0, q1, e0, e1 = x.Q, z.Q, x.E, z.E
    else:
        q0, q1, e0, e1 = x[f"Q{j}"], z[f"Q{j}"], x[f"E{j}"], z[f"E{j}"]
    dq = np.log(q1 / q0)[f]; ok = np.isfinite(dq)
    s = ((e0[f] / e0[f].sum() + e1[f] / e1[f].sum()) / 2)[ok]
    r["food_qty_pct"] = (np.exp((s * dq[ok]).sum() / s.sum()) - 1) * 100
    rows.append(r)
bur = pd.DataFrame(rows)
bur.round(2).to_csv(RES / "w2_burden_2021_2025.csv", index=False, encoding="utf-8-sig")
print(bur.round(2).to_string(index=False))
print("品目数", len(ix), "食料", int((x.grp == "食料").sum()))

# 消費支出の変化（名目、2021→2025）
ch = t[t.year.isin([B, E])].pivot(index="quintile", columns="year", values=["cons", "food"])
cc = pd.DataFrame({"quintile": [QN[j] for j in ch.index], "cons_pct": (ch["cons"][E] / ch["cons"][B] - 1).values * 100,
                   "food_pct": (ch["food"][E] / ch["food"][B] - 1).values * 100})
cc.round(2).to_csv(RES / "w2_spending_change.csv", index=False, encoding="utf-8-sig")
print(cc.round(1).to_string(index=False))

# ---- 図 ----
cols = {1: ORANGE, 2: "#f0a07a", 3: GRAY, 4: LIGHT, 5: BLUE}
fig, ax = plt.subplots(figsize=(8.2, 4.8))
for j in range(1, 6):
    s = eng[QN[j]]
    ax.plot(s.index, s.values, color=cols[j], lw=2.2 if j in (1, 5) else 1.5, marker="o", ms=3)
    ax.text(2025.3, s.values[-1], f"{QN[j]} {s.values[-1]:.1f}%", color=cols[j], va="center", fontsize=9.5)
ax.set_xticks(range(2007, 2026, 2)); ax.set_ylabel("食料÷消費支出（%）"); ax.set_xlim(2006.5, 2028.3)
ax.set_title("年間収入の五分位別エンゲル係数（二人以上の世帯）", loc="left")
note(ax, SOURCE + "（Ⅰは年収が低い20%、Ⅴは高い20%）", y=-0.13)
fig.savefig(FIG / "w2_engel.png"); plt.close(fig)

b5 = bur[bur.quintile != "平均"]
fig, ax = plt.subplots(figsize=(8.2, 4.6))
yy = np.arange(len(b5))[::-1]
f1 = b5["extra_pct_of_cons_食料"].values; f2 = b5["extra_pct_of_cons_エネルギー"].values
ax.barh(yy, f1, color=ORANGE, label=f"食料（{int((x.grp == '食料').sum())}品目）", height=.6)
ax.barh(yy, f2, left=f1, color=PURPLE, label="エネルギー（電気・LPガス・灯油・ガソリン）", height=.6)
for yv, a, b_, yen in zip(yy, f1, f2, b5.extra_month_yen):
    ax.text(a + b_ + .08, yv, f"{a + b_:.1f}%（月{yen:,.0f}円）", va="center", fontsize=10)
ax.set_yticks(yy); ax.set_yticklabels(b5.quintile); ax.set_xlim(0, 11.5)
ax.set_xlabel("2021年と同じものを2025年の価格で買うと増える額（2021年の消費支出に対する%）")
ax.set_title("値上がりの負担：年収の低い世帯ほど支出に対して重い", loc="left"); ax.legend(frameon=False, loc="lower right", fontsize=8.5)
note(ax, SOURCE + "（二人以上の世帯。価格の変化は全世帯の平均価格）", y=-0.17)
fig.savefig(FIG / "w2_burden.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8.2, 4.4))
yy = np.arange(len(b5))[::-1]
ax.barh(yy, b5.food_qty_pct, color=BLUE, height=.6)
for yv, v in zip(yy, b5.food_qty_pct):
    ax.text(v - .3, yv, f"{v:.1f}%", va="center", ha="right", fontsize=10)
ax.axvline(0, color=GRAY, lw=.8)
ax.set_yticks(yy); ax.set_yticklabels(b5.quintile); ax.set_xlim(-20, 1)
ax.set_xlabel(f"食料{int((x.grp == '食料').sum())}品目の購入数量の変化（2021→2025年、%）")
ax.set_title("買った量をどれだけ減らしたか（五分位別）", loc="left")
note(ax, SOURCE + "（二人以上の世帯。トルンクビスト式で品目をまとめた）", y=-0.17)
fig.savefig(FIG / "w2_quantity.png"); plt.close(fig)
