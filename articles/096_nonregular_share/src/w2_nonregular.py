"""W2：非正規の職員・従業員の割合は、男女・年齢別にどう変わったか（詳細集計、2002〜2025年）"""
from common import *

t = load_type()
t["share"] = t.nonregular / (t.regular + t.nonregular) * 100
YRS = [2002, 2013, 2019, 2025]
# 年齢をまとめた区分
MAP = {"15-19": "15〜24歳", "20-24": "15〜24歳", "25-29": "25〜34歳", "30-34": "25〜34歳", "35-39": "35〜44歳", "40-44": "35〜44歳",
       "45-49": "45〜54歳", "50-54": "45〜54歳", "55-59": "55〜64歳", "60-64": "55〜64歳", "65-69": "65歳以上", "70-74": "65歳以上", "75+": "65歳以上"}
AG = ["15〜24歳", "25〜34歳", "35〜44歳", "45〜54歳", "55〜64歳", "65歳以上"]
s = t[t.age != "総数"].copy(); s["ag"] = s.age.map(MAP)
a = s.groupby(["year", "sex", "ag"])[["regular", "nonregular"]].sum().reset_index()
a["share"] = a.nonregular / (a.regular + a.nonregular) * 100
a.round(1).to_csv(RES / "w2_share_by_age.csv", index=False)
tot = t[t.age == "総数"].set_index(["year", "sex"]).share.unstack()[["男女計", "男", "女"]]
tot.round(1).to_csv(RES / "w2_share_total.csv")
print(tot.loc[[2002, 2008, 2013, 2019, 2020, 2025]].round(1))
pv = a.pivot_table(index=["sex", "ag"], columns="year", values="share")[YRS]
print(pv.round(1))

# 非正規の人数の変化（2002→2025、2013→2025）を年齢で分ける
n = a[a.sex == "男女計"].pivot(index="ag", columns="year", values="nonregular").reindex(AG)
cnt = pd.DataFrame({"2002": n[2002], "2013": n[2013], "2025": n[2025], "増減2002-2025": n[2025] - n[2002], "増減2013-2025": n[2025] - n[2013]})
cnt.loc["計"] = cnt.sum()
cnt.to_csv(RES / "w2_nonregular_count.csv")
print(cnt)
r = a[a.sex == "男女計"].pivot(index="ag", columns="year", values="regular").reindex(AG)
print("正規 2013→2025", (r[2025] - r[2013]).round(0).to_dict(), (r[2025] - r[2013]).sum())

# 全体の割合の変化を「年齢別の割合の変化」と「年齢構成の変化」に分ける（男女×5歳階級）
def ss(y0, y1):
    x = s[s.sex.isin(["男", "女"])].copy(); x["emp2"] = x.regular + x.nonregular
    A = x[x.year == y0].set_index(["sex", "age"]); B = x[x.year == y1].set_index(["sex", "age"])
    w0, w1 = A.emp2 / A.emp2.sum(), B.emp2 / B.emp2.sum()
    within = ((B.share - A.share) * (w0 + w1) / 2).sum()
    comp = ((w1 - w0) * (A.share + B.share) / 2).sum()
    tot0 = (A.nonregular.sum() / A.emp2.sum() * 100); tot1 = (B.nonregular.sum() / B.emp2.sum() * 100)
    # 65歳以上の構成の変化だけ
    old = [i for i in A.index if i[1] in ("65-69", "70-74", "75+")]
    comp_old = ((w1 - w0) * (A.share + B.share) / 2).loc[old].sum()
    return {"period": f"{y0}-{y1}", "share0": tot0, "share1": tot1, "change": tot1 - tot0, "within": within, "composition": comp, "composition_65plus": comp_old}
sh = pd.DataFrame([ss(2002, 2013), ss(2013, 2025), ss(2002, 2025)])
sh.round(2).to_csv(RES / "w2_shiftshare.csv", index=False)
print(sh.round(2))

# --- 図1：全体の推移
fig, ax = plt.subplots(figsize=(8, 4.4))
for c, col in zip(["男女計", "女", "男"], [INK, ORANGE, BLUE]):
    ax.plot(tot.index, tot[c], color=col, lw=2.2 if c == "男女計" else 1.8, label=c)
    ax.text(tot.index[-1] + .3, tot[c].iloc[-1], f"{c} {tot[c].iloc[-1]:.1f}%", color=col, va="center", fontsize=10)
ax.set_xlim(2001.5, 2028.5); ax.set_ylim(0, 60); ax.set_ylabel("%")
ax.set_title("役員を除く雇用者に占める非正規の割合")
save(fig, "w2_trend.png")

# --- 図2：年齢別の割合（男・女、2002・2013・2025）
fig, axs = plt.subplots(1, 2, figsize=(9.5, 4.4), sharey=True)
for ax, sx in zip(axs, ["男", "女"]):
    for y, col in zip([2002, 2013, 2025], [LIGHT, GRAY, BLUE if sx == "男" else ORANGE]):
        v = pv.loc[sx][y].reindex(AG)
        ax.plot(range(len(AG)), v, marker="o", color=col, lw=2, label=str(y))
    ax.set_xticks(range(len(AG)), [x.replace("歳以上", "+").replace("歳", "") for x in AG], fontsize=9)
    ax.set_title(sx); ax.set_ylim(0, 100)
axs[0].set_ylabel("非正規の割合（%）"); axs[1].legend(frameon=False)
fig.suptitle("年齢別の非正規の割合", y=1.0)
save(fig, "w2_age.png")

# --- 図3：非正規の人数の増減（2013→2025、年齢別）
fig, ax = plt.subplots(figsize=(8, 4.2))
v = cnt.loc[AG, "増減2013-2025"]; v2 = (r[2025] - r[2013]).reindex(AG)
x = np.arange(len(AG))
ax.bar(x - .2, v, .4, color=ORANGE, label="非正規")
ax.bar(x + .2, v2, .4, color=BLUE, label="正規")
for i in range(len(AG)):
    ax.text(i - .2, v.iloc[i] + (4 if v.iloc[i] >= 0 else -4), f"{v.iloc[i]:+.0f}", ha="center", va="bottom" if v.iloc[i] >= 0 else "top", fontsize=9)
    ax.text(i + .2, v2.iloc[i] + (4 if v2.iloc[i] >= 0 else -4), f"{v2.iloc[i]:+.0f}", ha="center", va="bottom" if v2.iloc[i] >= 0 else "top", fontsize=9)
ax.axhline(0, color=INK, lw=.8); ax.set_xticks(x, AG); ax.set_ylabel("万人")
ax.set_title("2013→2025年の正規・非正規の増減（年齢別）"); ax.legend(frameon=False)
save(fig, "w2_count.png")
