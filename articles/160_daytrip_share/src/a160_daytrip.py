"""日本人の国内旅行は「日帰り化」していたのか（旅行・観光消費動向調査 2014〜2025年）"""
from common import *

d = load("domestic_trips_by_age.csv")  # 延べ旅行者数（千人回）
d["day_share"] = d.day / d.total
t = d[d.age == "年齢計"].set_index("year").sort_index()
for p in ["kanko", "kisei", "shutcho"]:
    t[f"day_share_{p}"] = t[f"day_{p}"] / (t[f"day_{p}"] + t[f"stay_{p}"])
t.round(4).to_csv(RES / "a160_total.csv", encoding="utf-8")
ages = [a for a in d.age.unique() if a != "年齢計"]
a = d[d.age != "年齢計"].copy()
a["period"] = np.where(a.year <= 2019, "2014-19", np.where(a.year >= 2023, "2023-25", "2020-22"))
pa = a.groupby(["period", "age"], sort=False)[["day", "total", "day_kanko", "stay_kanko"]].sum()
pa["day_share"] = pa.day / pa.total
ps = pa.day_share.unstack(0).loc[ages]
ps.round(4).to_csv(RES / "a160_age_share.csv", encoding="utf-8")
L = ["延べ旅行者数（億人回）と日帰りの割合:\n" + "\n".join(f"  {y} 計 {r.total/1e5:.2f} 宿泊 {r.stay/1e5:.2f} 日帰り {r.day/1e5:.2f} 日帰り割合 {r.day_share:.1%} 観光 {r.day_share_kanko:.1%} 帰省 {r.day_share_kisei:.1%} 出張 {r.day_share_shutcho:.1%}" for y, r in t.iterrows())]
L.append("年齢別 日帰り割合（期間合計）:\n" + (ps * 100).round(1).to_string())
L.append(f"2019→2025: 宿泊 {t.stay[2025]/t.stay[2019]*100:.1f}、日帰り {t.day[2025]/t.day[2019]*100:.1f}（2019=100）")
L.append(f"2014→2019: 宿泊 {t.stay[2019]/t.stay[2014]*100:.1f}、日帰り {t.day[2019]/t.day[2014]*100:.1f}")
(RES / "a160_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：延べ旅行者数
fig, ax = plt.subplots(figsize=(10, 5.2))
x = t.index
ax.bar(x, t.stay / 1e5, color=BLUE, width=0.7, label="宿泊旅行")
ax.bar(x, t.day / 1e5, bottom=t.stay / 1e5, color=LIGHT, width=0.7, label="日帰り旅行")
for xx, s, dd in zip(x, t.stay / 1e5, t.day / 1e5):
    ax.text(xx, s + dd + 0.05, f"{s+dd:.2f}", ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_ylabel("延べ旅行者数（億人回）")
ax.legend(frameon=False, loc="upper right"); ax.set_title("日本人の国内旅行（延べ旅行者数）")
save(fig, "a160_trips.png")

# 図2：日帰りの割合（目的別）
fig, ax = plt.subplots(figsize=(10, 5.2))
for c, col, lab, lw in [("day_share", INK, "全体", 2.6), ("day_share_kanko", ORANGE, "観光・レクリエーション", 1.8), ("day_share_kisei", GREEN, "帰省・知人訪問等", 1.8), ("day_share_shutcho", PURPLE, "出張・業務", 1.8)]:
    ax.plot(x, t[c] * 100, marker="o", ms=4, color=col, lw=lw, label=lab)
ax.axvspan(2019.5, 2022.5, color=GRAY, alpha=0.12)
ax.text(2021, 61, "コロナ禍", ha="center", color=GRAY, fontsize=9)
ax.set_xticks(x); ax.set_ylabel("延べ旅行者のうち日帰りの割合（%）"); ax.set_ylim(25, 65)
ax.legend(frameon=False, ncol=2, loc="lower left", fontsize=9.5); ax.set_title("国内旅行のうち日帰りの割合")
save(fig, "a160_share.png")

# 図3：年齢別
fig, ax = plt.subplots(figsize=(10, 5.2))
w = 0.38; xi = np.arange(len(ages))
ax.bar(xi - w / 2, ps["2014-19"] * 100, width=w, color=LIGHT, label="2014〜19年")
ax.bar(xi + w / 2, ps["2023-25"] * 100, width=w, color=BLUE, label="2023〜25年")
for i, (v1, v2) in enumerate(zip(ps["2014-19"], ps["2023-25"])):
    ax.text(i + w / 2, v2 * 100 + 0.6, f"{v2*100:.0f}", ha="center", fontsize=8.5)
ax.set_xticks(xi); ax.set_xticklabels([s.replace("代以上", "代〜") for s in ages])
ax.set_ylabel("日帰りの割合（%）"); ax.set_ylim(0, 65)
ax.legend(frameon=False, loc="upper left"); ax.set_title("年代別に見た、国内旅行のうち日帰りの割合")
save(fig, "a160_age.png")
