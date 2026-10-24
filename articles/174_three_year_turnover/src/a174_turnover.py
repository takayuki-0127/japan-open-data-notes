"""「3年で3割辞める」は本当に30年変わらなかったのか（1996〜2023年3月卒）"""
from common import *

d = load("turnover_by_education.csv")
E = ["高校", "短大等", "大学"]; C = {"高校": BLUE, "短大等": GREEN, "大学": ORANGE}
L = []
for e in E:
    x = d[d.education == e].set_index("grad_year")
    L.append(f"{e}: 3年以内 1996 {x.within3y[1996]}% 平均(1996-2023) {x.within3y.mean():.1f}% 最小 {x.within3y.idxmin()} {x.within3y.min()}% 最大 {x.within3y.idxmax()} {x.within3y.max()}% 2023 {x.within3y[2023]}%  1年目 1996 {x.year1[1996]}→2023 {x.year1[2023]}  3年目 {x.year3[1996]}→{x.year3[2023]}")
    L.append(f"  {e} 1年目が3年以内に占める割合 1996-2000平均 {(x.year1/x.within3y).loc[1996:2000].mean():.1%} → 2019-2023平均 {(x.year1/x.within3y).loc[2019:2023].mean():.1%}")
    L.append(f"  {e} 30%以上の年 {int((x.within3y>=30).sum())}/28、期間平均 1996-2005 {x.within3y.loc[1996:2005].mean():.1f} / 2006-2015 {x.within3y.loc[2006:2015].mean():.1f} / 2016-2023 {x.within3y.loc[2016:2023].mean():.1f}")
(RES / "a174_summary.txt").write_text("\n".join(L), encoding="utf-8"); print("\n".join(L))
d.pivot(index="grad_year", columns="education", values="within3y").to_csv(RES / "a174_within3y.csv")

fig, ax = plt.subplots(figsize=(9.5, 4.4))
for e in E:
    x = d[d.education == e]; ax.plot(x.grad_year, x.within3y, lw=2.3, color=C[e], label=e + "卒")
ax.axhline(30, color=GRAY, lw=0.8, ls=":"); ax.text(1996, 30.6, "3割", color=GRAY, fontsize=9)
ax.axvspan(2007.5, 2009.5, color=LIGHT, alpha=0.4, lw=0); ax.text(2008.5, 52, "リーマン・ショック\nのころに就職", ha="center", fontsize=8, color=GRAY)
ax.set_ylim(20, 55); ax.set_ylabel("就職後3年以内の離職率（%）"); ax.set_xlabel("卒業した年（3月卒）"); ax.legend(frameon=False, ncol=3, loc="lower left")
ax.set_title("就職後3年以内に辞めた人の割合（1996〜2023年3月卒）")
save(fig, "a174_trend.png")

u = d[d.education == "大学"].set_index("grad_year")
fig, ax = plt.subplots(figsize=(9.5, 4.2))
for c, n, col in [("year1", "1年目", ORANGE), ("year2", "2年目", BLUE), ("year3", "3年目", GREEN)]:
    ax.plot(u.index, u[c], lw=2.2, color=col, label=n)
ax.set_ylim(6, 17); ax.set_ylabel("離職率（%）"); ax.set_xlabel("卒業した年（3月卒）"); ax.legend(frameon=False, ncol=3)
ax.set_title("大卒の離職率を「何年目に辞めたか」で分ける")
save(fig, "a174_by_year_univ.png")

fig, ax = plt.subplots(figsize=(9.5, 4.2))
for e in ["高校", "大学"]:
    x = d[d.education == e].set_index("grad_year")
    for y, ls in [(1996, ":"), (2023, "-")]:
        r = x.loc[y]; s = [100, 100 - r.year1, 100 - r.year1 - r.year2, 100 - r.within3y]
        ax.plot([0, 1, 2, 3], s, ls=ls, marker="o", color=C[e], lw=2, label=f"{e}卒 {y}年3月卒")
        ax.annotate(f"{s[-1]:.0f}%", (3, s[-1]), xytext=(6, -3), textcoords="offset points", fontsize=9, color=C[e])
ax.set_xticks([0, 1, 2, 3]); ax.set_xticklabels(["就職時", "1年目の終わり", "2年目の終わり", "3年目の終わり"])
ax.set_ylabel("同じ会社に残っている割合（%）"); ax.set_ylim(45, 102); ax.legend(frameon=False, fontsize=9)
ax.set_title("最初の会社に残っている人の割合（定着の曲線）")
save(fig, "a174_survival.png")
