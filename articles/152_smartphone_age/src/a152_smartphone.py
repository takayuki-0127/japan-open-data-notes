"""スマートフォンの保有率が9割を超えるのは何歳までか。年齢別の推移（2016〜2025年、2020年は除く）"""
from common import *

d = load("smartphone_by_age.csv")
a = d[d.sex == "計"]
P = a.pivot(index="year", columns="age", values="smart")
AGES = ["6-12", "13-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"]
LAB = {"6-12": "6〜12歳", "13-19": "13〜19歳", "20-29": "20代", "30-39": "30代", "40-49": "40代", "50-59": "50代", "60-69": "60代", "70-79": "70代", "80+": "80歳以上"}
P = P[AGES]
P.to_csv(RES / "a152_smart_by_age.csv", encoding="utf-8")
L = ["スマホ保有率（%、年齢別）:\n" + P.to_string()]
for y in P.index:
    over = [LAB[x] for x in AGES[2:] if P.loc[y, x] >= 90]
    L.append(f"{y}年 9割以上: {'・'.join(over) if over else 'なし'}")
L.append("2016→2025 増加（ポイント）:\n" + (P.loc[2025] - P.loc[2016]).round(1).to_string())
# 10年後の同じ世代（おおよそ）：2016年のX代 と 2025年の(X+10)代
coh = [(f"2016年{LAB[a1]}→2025年{LAB[a2]}", P.loc[2016, a1], P.loc[2025, a2]) for a1, a2 in [("40-49", "50-59"), ("50-59", "60-69"), ("60-69", "70-79"), ("70-79", "80+")]]
L.append("おおよそ同じ世代の比較:\n" + "\n".join(f"{n}: {x:.1f}%→{y:.1f}%" for n, x, y in coh))
c = (P.loc[2025] - P.loc[2016])
nb = d[(d.sex != "計")].pivot_table(index=["age", "sex"], columns="year", values="smart")
L.append("性別（70代・80歳以上）:\n" + nb.to_string())
fe = a[a.year >= 2021].pivot(index="year", columns="age", values="feature")[AGES]
L.append("携帯電話（スマホ以外）の保有率:\n" + fe.to_string())
(RES / "a152_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：年齢別の推移
fig, ax = plt.subplots(figsize=(9.5, 4.8))
cols = {"20-29": "#a9c9ef", "40-49": BLUE, "50-59": "#1b4f9c", "60-69": GREEN, "70-79": ORANGE, "80+": PURPLE}
off = {"20-29": 4.5, "40-49": 0.5, "50-59": -3.5, "60-69": -7}
for k, col in cols.items():
    s = P[k]
    ax.plot(s.index, s.values, marker="o", color=col, lw=2)
    ax.text(2025.15, s.loc[2025] + off.get(k, 0), LAB[k], va="center", fontsize=9.5, color=col)
ax.axhline(90, color=GRAY, lw=0.8, ls=":")
ax.set_xticks(P.index); ax.set_xlim(2015.6, 2026.3); ax.set_ylim(0, 100)
ax.set_ylabel("スマートフォンを持っている人の割合（%）")
ax.set_title("年齢別のスマートフォン保有率（2020年は表の形式が違うため除く）")
save(fig, "a152_trend.png")

# 図2：2016年と2025年の年齢カーブ
fig, ax = plt.subplots(figsize=(9.5, 4.4))
x = np.arange(len(AGES))
for y, col in [(2016, GRAY), (2019, LIGHT), (2025, BLUE)]:
    ax.plot(x, P.loc[y].values, marker="o", lw=2.2, color=col, label=f"{y}年")
ax.axhline(90, color=GRAY, lw=0.8, ls=":"); ax.text(8.2, 91, "90%", fontsize=9, color=GRAY)
ax.set_xticks(x); ax.set_xticklabels([LAB[k] for k in AGES]); ax.set_ylim(0, 100)
ax.set_ylabel("%"); ax.legend(frameon=False)
ax.set_title("年齢ごとのスマートフォン保有率（2016・2019・2025年）")
save(fig, "a152_profile.png")

# 図3：70代・80歳以上の持ち方の内訳（2021〜2025年）
fig, ax = plt.subplots(figsize=(9.5, 4.4))
yrs = [2021, 2022, 2023, 2024, 2025]
for k, col, off in [("70-79", ORANGE, -0.2), ("80+", PURPLE, 0.2)]:
    s = a[(a.age == k) & a.year.isin(yrs)].set_index("year")
    ax.bar(np.array(yrs) + off, s.smart, width=0.38, color=col, label=f"{LAB[k]}：スマホ")
    ax.bar(np.array(yrs) + off, s.mobile - s.smart, bottom=s.smart, width=0.38, color=col, alpha=0.35, label=f"{LAB[k]}：スマホ以外の携帯だけ")
ax.set_xticks(yrs); ax.set_ylim(0, 100); ax.set_ylabel("%")
ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper left")
ax.set_title("70代・80歳以上：スマホと、スマホ以外の携帯だけの人（モバイル端末の保有率の内訳）")
save(fig, "a152_elderly.png")
