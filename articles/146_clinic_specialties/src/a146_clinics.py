"""一般診療所はどの診療科で増えたか。開設・廃止と開設者の変化もあわせて見る"""
from common import *

oc = read("clinic_open_close.csv").set_index("year")
own = read("clinics_by_owner.csv").set_index("year")
spc = read("clinics_by_specialty_2008_2023.csv").set_index("specialty")
old = read("clinics_by_specialty_1984_2002.csv").set_index("specialty")
L = []
# 1 開設・廃止
oc["turnover_rate"] = oc.opened / oc.clinics_oct1.shift(1)
L.append(f"一般診療所 2011年 {oc.clinics_oct1[2011]:,} → 2025年 {oc.clinics_oct1[2025]:,}（{oc.clinics_oct1[2025]-oc.clinics_oct1[2011]:+,}）")
L.append("開設・廃止（10月〜翌9月）:\n" + oc[["opened", "closed", "net_change"]].to_string())
L.append(f"2011〜2025年の合計 開設 {oc.opened.sum():,} 廃止 {oc.closed.sum():,}、純増 {oc.net_change.sum():,}")
oc.to_csv(RES / "a146_open_close.csv")
# 2 診療科
g = spc.copy()
g["chg_2008_2023"] = g["2023"] / g["2008"] - 1
g["chg_2020_2023"] = g["2023"] / g["2020"] - 1
g["diff_2008_2023"] = g["2023"] - g["2008"]
big = g[g["2008"] >= 300].drop(index="一般診療所（総数）")
big = big.sort_values("chg_2008_2023")
big.to_csv(RES / "a146_specialty_change.csv")
L.append(f"総数 2008→2023 {g.loc['一般診療所（総数）','chg_2008_2023']:+.1%}")
L.append("2008年に300施設以上の科の増減率（2008→2023）:\n" + big[["2008", "2023", "chg_2008_2023", "chg_2020_2023", "diff_2008_2023"]].round(3).to_string())
L.append("1984→2002（一部の科）:\n" + (old["2002"] / old["1984"] - 1).round(2).to_string())
# 3 開設者
own["individual_share"] = own.individual / own.total
own["corp_share"] = own.medical_corporation / own.total
own.to_csv(RES / "a146_owner.csv")
L.append("開設者:\n" + own[["total", "medical_corporation", "individual", "individual_share", "corp_share"]].round(3).to_string())
bo = read("clinic_open_close_by_owner.csv")
p = bo.pivot_table(index="year", columns="owner", values=["opened", "closed"])
L.append("開設者別の開設・廃止:\n" + p.to_string())
(RES / "a146_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1 開設・廃止と施設数
fig, ax = plt.subplots(figsize=(9.5, 4.4))
x = oc.index.values
ax.bar(x - 0.2, oc.opened / 1000, width=0.4, color=BLUE, label="開設")
ax.bar(x + 0.2, oc.closed / 1000, width=0.4, color=ORANGE, label="廃止")
ax.set_ylabel("施設数（千、10月〜翌9月）"); ax.set_ylim(0, 13)
ax2 = ax.twinx(); ax2.spines["right"].set_visible(True)
ax2.plot(x, oc.clinics_oct1 / 1000, color=INK, lw=2, marker="o", ms=4, label="一般診療所の数（10月1日、右）")
ax2.set_ylim(95, 107); ax2.set_ylabel("一般診療所の数（千）")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"{v}" for v in x], rotation=45)
ax.set_title("一般診療所の開設・廃止と施設数")
save(fig, "a146_open_close.png")

# 図2 診療科（標榜）の増減率
sel = big.copy()
fig, ax = plt.subplots(figsize=(9.5, 8.6))
cols = [BLUE if v > 0 else ORANGE for v in sel.chg_2008_2023]
ax.barh(range(len(sel)), sel.chg_2008_2023 * 100, color=cols, height=0.65)
for i, (n, r) in enumerate(sel.iterrows()):
    v = r.chg_2008_2023 * 100
    ax.text((v if v >= 0 else 0) + 2, i, f"{v:+.0f}%（{int(r['2023']):,}）", va="center", ha="left", fontsize=8.5)
ax.set_yticks(range(len(sel))); ax.set_yticklabels(sel.index, fontsize=9)
ax.axvline(g.loc["一般診療所（総数）", "chg_2008_2023"] * 100, color=GRAY, ls=":", lw=1)
ax.set_xlim(-75, 220); ax.set_xlabel("2008→2023年の増減率（%）　カッコ内は2023年の施設数")
ax.set_title("その診療科を掲げる一般診療所の数の増減（重複計上）")
save(fig, "a146_specialty.png")

# 図3 開設者
fig, ax = plt.subplots(figsize=(9.5, 4.2))
ax.plot(own.index, own.individual / 1000, color=ORANGE, lw=2.2, marker="o", ms=4, label="個人")
ax.plot(own.index, own.medical_corporation / 1000, color=BLUE, lw=2.2, marker="o", ms=4, label="医療法人")
ax.plot(own.index, own.social_welfare / 1000, color=GREEN, lw=1.5, marker="o", ms=3, label="社会福祉法人")
for c, col in [("individual", ORANGE), ("medical_corporation", BLUE)]:
    ax.text(own.index[-1] + 0.3, own[c].iloc[-1] / 1000, f"{own[c].iloc[-1]/own.total.iloc[-1]:.0%}", color=col, va="center", fontsize=10)
ax.set_ylabel("一般診療所の数（千）"); ax.set_ylim(0, 66)
ax.legend(frameon=False, loc="upper center", ncol=3); ax.set_title("開設者別の一般診療所の数（右端の%は2025年の割合）")
save(fig, "a146_owner.png")
