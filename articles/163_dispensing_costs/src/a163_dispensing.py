"""A163 調剤医療費の伸びは、技術料と薬剤料のどちらか：寄与度分解"""
from common import *

c = load("costs_fy.csv").set_index("fy")
o = load("oral_3factor.csv").set_index("fy")
c["drug_other"] = c["drug_tonpuku"] + c["drug_ext"]

# 1) 期間ごとの増加額と寄与（合計の伸びに対する各項目の寄与、%ポイント）
parts = {"技術料": "tech", "内服薬": "drug_oral", "注射薬": "drug_inj", "外用薬・屯服薬他": "drug_other", "特定保険医療材料料": "material"}
rows = []
for a, b in [(2012, 2024), (2012, 2019), (2019, 2024)]:
    base = c.loc[a, "total"]
    r = {"期間": f"{a}→{b}年度", "総額_増加(億円)": c.loc[b, "total"] - base, "総額_伸び(%)": round((c.loc[b, "total"] / base - 1) * 100, 1)}
    for k, col in parts.items():
        d = c.loc[b, col] - c.loc[a, col]
        r[f"{k}_増加(億円)"] = d
        r[f"{k}_寄与(pt)"] = round(d / base * 100, 1)
        r[f"{k}_増加に占める割合(%)"] = round(d / (c.loc[b, "total"] - base) * 100, 1)
    rows.append(r)
per = pd.DataFrame(rows)
per.to_csv(RES / "a163_period_contrib.csv", index=False, encoding="utf-8-sig")

# 2) 年度ごとの寄与度（前年度比、pt）
yc = pd.DataFrame({k: c[col].diff() / c["total"].shift() * 100 for k, col in parts.items()})
yc["総額の伸び率"] = c["total"].pct_change() * 100
yc = yc.dropna().round(2)
yc.to_csv(RES / "a163_yearly_contrib.csv", encoding="utf-8-sig")

# 3) 処方箋枚数と1枚当たりへの分解（対数で分ける）
lt = np.log(c.loc[2024, "total"] / c.loc[2012, "total"])
ln = np.log(c.loc[2024, "rx_10k"] / c.loc[2012, "rx_10k"])
rx_share = ln / lt

# 4) 内服薬 1枚当たり薬剤料の3要素（2012=100）
idx = (o / o.loc[2012] * 100).round(1)
idx.to_csv(RES / "a163_oral_index.csv", encoding="utf-8-sig")

with open(RES / "a163_summary.txt", "w", encoding="utf-8") as f:
    f.write(per.T.to_string() + "\n\n")
    f.write(f"技術料の割合: 2012 {c.loc[2012,'tech']/c.loc[2012,'total']*100:.1f}% -> 2024 {c.loc[2024,'tech']/c.loc[2024,'total']*100:.1f}%\n")
    f.write(f"処方箋枚数: {c.loc[2012,'rx_10k']:,}万枚 -> {c.loc[2024,'rx_10k']:,}万枚 ({(c.loc[2024,'rx_10k']/c.loc[2012,'rx_10k']-1)*100:.1f}%)、1枚当たり {c.loc[2012,'per_rx_yen']:,}円 -> {c.loc[2024,'per_rx_yen']:,}円 ({(c.loc[2024,'per_rx_yen']/c.loc[2012,'per_rx_yen']-1)*100:.1f}%)\n")
    f.write(f"総額の伸び(対数)のうち処方箋枚数の寄与: {rx_share*100:.0f}%\n")
    f.write(f"注射薬: {c.loc[2012,'drug_inj']:,} -> {c.loc[2024,'drug_inj']:,}億円 ({c.loc[2024,'drug_inj']/c.loc[2012,'drug_inj']:.2f}倍)\n")
    f.write(f"後発医薬品 薬剤料: {c.loc[2012,'drug_generic']:,} -> {c.loc[2024,'drug_generic']:,}億円\n")
    f.write("内服薬3要素 指数(2012=100):\n" + idx.loc[[2019, 2020, 2024]].to_string() + "\n")
    f.write("年度別寄与度:\n" + yc.to_string() + "\n")

# 図1 総額の内訳
fig, ax = plt.subplots(figsize=(8.6, 4.6))
x = c.index
ax.bar(x, c["tech"] / 1e4, color=ORANGE, label="技術料")
ax.bar(x, c["drug"] / 1e4, bottom=c["tech"] / 1e4, color=BLUE, label="薬剤料")
for y in [2012, 2019, 2024]:
    ax.text(y, c.loc[y, "total"] / 1e4 + 0.15, f"{c.loc[y,'total']/1e4:.2f}", ha="center", fontsize=9, color=INK)
    ax.text(y, c.loc[y, "tech"] / 2e4, f"{c.loc[y,'tech']/1e4:.2f}", ha="center", fontsize=8.5, color="white")
ax.set_xticks(list(x)); ax.set_xticklabels([str(v) for v in x], fontsize=9)
ax.set_ylabel("兆円"); ax.set_ylim(0, 9.6)
ax.set_title("調剤医療費（電算処理分）の内訳（年度、特定保険医療材料料は省略）")
ax.legend(loc="upper left", frameon=False, ncol=2)
save(fig, "a163_level.png")

# 図2 年度ごとの寄与度
fig, ax = plt.subplots(figsize=(8.6, 4.8))
cols = {"技術料": ORANGE, "内服薬": BLUE, "注射薬": PURPLE, "外用薬・屯服薬他": LIGHT, "特定保険医療材料料": GRAY}
pos = np.zeros(len(yc)); neg = np.zeros(len(yc))
for k, colr in cols.items():
    v = yc[k].values
    b = np.where(v >= 0, pos, neg)
    ax.bar(yc.index, v, bottom=b, color=colr, label=k, width=0.7)
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
ax.plot(yc.index, yc["総額の伸び率"], "o", color=INK, ms=5, label="総額の伸び率")
ax.axhline(0, color=INK, lw=0.8)
ax.set_xticks(list(yc.index)); ax.set_xticklabels([str(v) for v in yc.index], fontsize=9)
ax.set_ylabel("前年度比への寄与（%ポイント）")
ax.set_title("調剤医療費の伸び率と、項目ごとの寄与度（年度）")
ax.legend(loc="lower left", frameon=False, ncol=3, fontsize=8.5)
ax.set_ylim(-9.5, 11)
save(fig, "a163_contrib.png")

# 図3 内服薬の3要素
fig, ax = plt.subplots(figsize=(8.6, 4.6))
lab = {"per_rx_oral": ("処方箋1枚当たり内服薬の薬剤料", INK), "kinds": ("1枚当たり薬剤種類数", GREEN), "days": ("1種類当たり投薬日数", BLUE), "yen_per_day": ("1種類1日当たり薬剤料", ORANGE)}
for k, (l, colr) in lab.items():
    ax.plot(idx.index, idx[k], marker="o", ms=3.5, color=colr, lw=2.2 if k == "per_rx_oral" else 1.6)
    ax.text(2024.25, idx.loc[2024, k], f"{l} {idx.loc[2024,k]:.0f}", va="center", fontsize=9, color=colr)
ax.axhline(100, color=GRAY, lw=0.8, ls=":")
ax.set_xticks(list(idx.index)); ax.set_xticklabels([str(v) for v in idx.index], fontsize=9)
ax.set_xlim(2011.6, 2030.5); ax.set_ylabel("2012年度＝100")
ax.set_title("内服薬の1枚当たり薬剤料を3つに分ける（2012年度＝100）")
save(fig, "a163_oral.png")
print(open(RES / "a163_summary.txt", encoding="utf-8").read())
