"""介護をしながら働く人は5年でどれだけ増えたか（就業構造基本調査 2017・2022年）"""
from common import *

d = load("workers_by_care.csv")
# 年齢を2017年の区分にそろえる
M = {"01": "30歳未満", "02": "30歳未満", "03": "30歳未満", "04": "30～39歳", "05": "30～39歳", "06": "40～44歳", "07": "45～49歳",
     "08": "50～54歳", "09": "55～59歳", "10": "60～64歳", "11": "65～69歳", "12": "70歳以上", "13": "70歳以上", "00": "総数"}
d["agegrp"] = np.where(d.year == 2022, d.age.str[:2].map(M), d.age.str.split("_").str[1])
d["sexn"] = d.sex.str.split("_").str[1]
d["carer"] = d.care.str.startswith("1_")
g = d.groupby(["year", "sexn", "agegrp", "carer"])[["workers", "employees", "regular", "nonregular"]].sum().reset_index()
AG = ["30歳未満", "30～39歳", "40～44歳", "45～49歳", "50～54歳", "55～59歳", "60～64歳", "65～69歳", "70歳以上"]
c = g[g.carer].pivot_table(index=["sexn", "agegrp"], columns="year", values="workers")
a = g[~g.carer].pivot_table(index=["sexn", "agegrp"], columns="year", values="workers")
rate = c / a * 100
out = pd.concat({"carers": c, "all_workers": a, "rate_pct": rate.round(2)}, axis=1)
out.to_csv(RES / "a162_by_age.csv", encoding="utf-8")
L = []
for s in ["総数", "男", "女"]:
    L.append(f"{s}: 介護をしている有業者 2017 {c.loc[(s,'総数'),2017]/1e4:.1f}万 → 2022 {c.loc[(s,'総数'),2022]/1e4:.1f}万（{c.loc[(s,'総数'),2022]-c.loc[(s,'総数'),2017]:+,.0f}、{c.loc[(s,'総数'),2022]/c.loc[(s,'総数'),2017]-1:+.1%}）"
             f" 有業者に占める割合 {rate.loc[(s,'総数'),2017]:.2f}% → {rate.loc[(s,'総数'),2022]:.2f}%")
L.append("年齢別（男女計）: " + "、".join(f"{ag} {c.loc[('総数',ag),2017]/1e4:.1f}→{c.loc[('総数',ag),2022]/1e4:.1f}万（割合 {rate.loc[('総数',ag),2017]:.1f}→{rate.loc[('総数',ag),2022]:.1f}%）" for ag in AG))
diff = (c.loc["総数"][2022] - c.loc["総数"][2017]).reindex(AG)
L.append("増減（万人）: " + "、".join(f"{ag} {v/1e4:+.1f}" for ag, v in diff.items()))
L.append(f"50〜64歳の増加 {diff[['50～54歳','55～59歳','60～64歳']].sum()/1e4:+.1f}万、40歳未満 {diff[['30歳未満','30～39歳']].sum()/1e4:+.1f}万")
x = pd.DataFrame({"r17": rate.loc["総数"][2017], "w22": a.loc["総数"][2022]}).drop("総数")
exp22 = (x.r17 / 100 * x.w22).sum(); c17 = c.loc[("総数", "総数"), 2017]; c22 = c.loc[("総数", "総数"), 2022]
L.append(f"2017年の年齢別の割合のまま2022年の働く人の年齢構成にすると {exp22/1e4:.1f}万人 → 増加 {(c22-c17)/1e4:.1f}万人のうち {(exp22-c17)/1e4:.1f}万人（{(exp22-c17)/(c22-c17):.0%}）が年齢構成の変化で説明できる")
e = g[g.agegrp == "総数"].set_index(["year", "sexn", "carer"])
e["nonreg_share"] = e.nonregular / (e.regular + e.nonregular) * 100
L.append("雇用者のうち非正規の割合: " + "、".join(f"{y}{s}{'介護者' if cr else '全体'} {e.loc[(y,s,cr),'nonreg_share']:.1f}%" for y in [2017, 2022] for s in ["男", "女"] for cr in [True, False]))
e.reset_index().to_csv(RES / "a162_employment_type.csv", index=False, encoding="utf-8")
(RES / "a162_summary.txt").write_text("\n".join(L), encoding="utf-8")
print("\n".join(L))

# 図1：年齢別の人数（2017・2022）
fig, ax = plt.subplots(figsize=(10, 5))
x = np.arange(len(AG)); w = 0.38
v17 = c.loc["総数"][2017].reindex(AG) / 1e4; v22 = c.loc["総数"][2022].reindex(AG) / 1e4
ax.bar(x - w/2, v17, w, color=LIGHT, label="2017年"); ax.bar(x + w/2, v22, w, color=BLUE, label="2022年")
for xx, a1, b1 in zip(x, v17, v22):
    ax.text(xx + w/2, b1 + 1, f"{b1-a1:+.1f}", ha="center", fontsize=9, color=ORANGE if b1 > a1 else GRAY)
ax.set_xticks(x); ax.set_xticklabels(AG, fontsize=9.5); ax.set_ylabel("介護をしている有業者（万人）")
ax.legend(frameon=False); ax.set_title(f"介護をしながら働く人は {v17.sum():.0f}万人 → {v22.sum():.0f}万人（数字は5年の増減・万人）")
save(fig, "a162_count.png")

# 図2：有業者に占める割合（男女別）
fig, ax = plt.subplots(figsize=(10, 5))
for s, col in [("男", BLUE), ("女", ORANGE)]:
    ax.plot(AG, rate.loc[s][2017].reindex(AG), color=col, ls="--", marker="o", ms=4, lw=1.3, label=f"{s}性 2017年")
    ax.plot(AG, rate.loc[s][2022].reindex(AG), color=col, marker="o", ms=5, lw=2.3, label=f"{s}性 2022年")
ax.set_ylabel("有業者のうち介護をしている人の割合（%）"); ax.set_ylim(0, 17.5); ax.legend(frameon=False, ncol=2, loc="upper left")
ax.tick_params(axis="x", labelsize=9.5); ax.set_title("働く人のうち介護をしている割合は、50代後半の女性で16%")
save(fig, "a162_rate.png")

# 図3：雇用形態（正規・非正規）
fig, ax = plt.subplots(figsize=(10, 4.6))
labs, vals = [], []
for s in ["男", "女"]:
    for cr, nm in [(False, "雇用者全体"), (True, "介護をしている雇用者")]:
        for y in [2017, 2022]:
            labs.append(f"{s}性・{nm}・{y}"); vals.append(e.loc[(y, s, cr), "nonreg_share"])
yy = np.arange(len(labs))[::-1]
cols = [GRAY if "全体" in l else (BLUE if "男" in l else ORANGE) for l in labs]
ax.barh(yy, vals, color=cols, height=0.65)
for y0, v in zip(yy, vals): ax.text(v + 0.6, y0, f"{v:.1f}%", va="center", fontsize=9)
ax.set_yticks(yy); ax.set_yticklabels(labs, fontsize=9); ax.set_xlim(0, 75)
ax.set_xlabel("役員を除く雇用者のうち非正規の割合（%）"); ax.set_title("介護をしながら働く人は非正規の割合が高い")
save(fig, "a162_type.png")
