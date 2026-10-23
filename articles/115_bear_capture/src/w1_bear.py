"""W1：狩猟で獲られたクマ（ツキノワグマ・ヒグマ）の数は、年度・都道府県でどう変わったか"""
from common import *

hunt, permit, lic = load()
nat = hunt[hunt.area == "全国"].pivot(index="fy", columns="species", values="value")
bear = pd.DataFrame({"ツキノワグマ": nat["ツキノワグマ"], "ヒグマ": nat["ヒグマ"], "獣類計": nat["獣類計"],
                     "ニホンジカ": nat["ニホンジカ"], "イノシシ": nat["イノシシ"]})
bear["クマ類"] = bear["ツキノワグマ"] + bear["ヒグマ"]
bear["クマ類の割合%"] = 100 * bear["クマ類"] / bear["獣類計"]
bear["シカ・イノシシの割合%"] = 100 * (bear["ニホンジカ"] + bear["イノシシ"]) / bear["獣類計"]
bear.round(3).to_csv(RES / "w1_bear_national.csv")

# 期間別の平均と、多い年・少ない年
per = {"1998-2005": (1998, 2005), "2006-2013": (2006, 2013), "2014-2021": (2014, 2021)}
summ = pd.DataFrame({k: bear.loc[a:b, ["ツキノワグマ", "ヒグマ", "獣類計", "ニホンジカ", "イノシシ"]].mean() for k, (a, b) in per.items()}).T
summ.round(1).to_csv(RES / "w1_period_mean.csv")
print(bear[["ツキノワグマ", "ヒグマ", "クマ類の割合%", "シカ・イノシシの割合%"]].round(2).to_string())
print(summ.round(1).to_string())
tk = bear["ツキノワグマ"]
print("ツキノワグマ 最多", tk.idxmax(), tk.max(), "最少", tk.idxmin(), tk.min(), "中央値", tk.median())
# 前年度比で大きく減った年
chg = (tk / tk.shift(1) - 1) * 100
print("前年度比", chg.round(0).to_dict())

# 都道府県別（ツキノワグマ）
pref = hunt[(hunt.area != "全国") & (hunt.species == "ツキノワグマ")].pivot(index="area", columns="fy", values="value").fillna(0)
pt = pd.DataFrame({k: pref.loc[:, a:b].sum(axis=1) for k, (a, b) in per.items()})
pt["合計"] = pt.sum(axis=1)
pt["2014-2021の割合%"] = 100 * pt["2014-2021"] / pt["2014-2021"].sum()
pt = pt.sort_values("2014-2021", ascending=False)
pt.round(2).to_csv(RES / "w1_bear_pref.csv")
print(pt.head(12).round(1).to_string())
print("2014-2021にツキノワグマの狩猟捕獲があった都府県", int((pt["2014-2021"] > 0).sum()))
top5 = pt["2014-2021"].head(5).sum() / pt["2014-2021"].sum() * 100
print("上位5県の割合", round(top5, 1))
hg = hunt[(hunt.area == "北海道") & (hunt.species == "ヒグマ")].set_index("fy").value
print("北海道ヒグマ", hg.to_dict())
# 年度ごとの捕獲があった県の数
ny = (pref > 0).sum(); print("捕獲があった県の数", ny.to_dict())

# 図1：推移
fig, ax = plt.subplots(figsize=(8.6, 4.4))
ax.bar(bear.index, bear["ツキノワグマ"], color=BLUE, label="ツキノワグマ")
ax.bar(bear.index, bear["ヒグマ"], bottom=bear["ツキノワグマ"], color=ORANGE, label="ヒグマ（北海道）")
for y in (2006, 2010):
    ax.annotate(f"{y}年度\n{int(tk[y])}頭", (y, tk[y] + bear.loc[y, 'ヒグマ']), xytext=(0, 18), textcoords="offset points", ha="center", fontsize=9, color=INK,
                arrowprops=dict(arrowstyle="-", color=GRAY))
ax.set_title("狩猟で獲られたクマの数（全国、年度）")
ax.set_ylabel("頭"); ax.legend(frameon=False, loc="upper right")
ax.set_xlim(1997.3, 2021.7)
foot(fig, "狩猟者登録を受けた者による捕獲数（表11）。許可による捕獲（有害鳥獣捕獲など）は含まない。2002年度までのツキノワグマは表の「クマ」")
fig.savefig(FIG / "w1_trend.png"); plt.close(fig)

# 図2：都道府県（2014〜2021年度の合計）
top = pt.head(15)[::-1]
fig, ax = plt.subplots(figsize=(7.6, 5.4))
ax.barh(top.index, top["2014-2021"], color=BLUE, label="2014〜2021年度")
ax.scatter(top["1998-2005"], top.index, color=ORANGE, zorder=3, label="1998〜2005年度", s=22)
for i, (k, v) in enumerate(top["2014-2021"].items()):
    if v > 80:
        ax.text(v - 8, i, f"{int(v)}", va="center", ha="right", fontsize=8.5, color="white")
    else:
        ax.text(v + 8, i, f"{int(v)}", va="center", ha="left", fontsize=8.5, color=INK)
ax.set_title("ツキノワグマの狩猟による捕獲数（8年度の合計、上位15都府県）")
ax.set_xlabel("頭"); ax.legend(frameon=False, loc="lower right")
foot(fig)
fig.savefig(FIG / "w1_pref.png"); plt.close(fig)

# 図3：狩猟で獲られた獣の内訳
oth = bear["獣類計"] - bear["ニホンジカ"] - bear["イノシシ"] - bear["クマ類"]
fig, ax = plt.subplots(figsize=(8.6, 4.4))
ax.stackplot(bear.index, bear["ニホンジカ"] / 1e4, bear["イノシシ"] / 1e4, oth / 1e4, bear["クマ類"] / 1e4,
             colors=[BLUE, ORANGE, LIGHT, INK], labels=["ニホンジカ", "イノシシ", "そのほかの獣", "クマ類"])
ax.set_title("狩猟で獲られた獣の数と内訳（全国、年度）")
ax.set_ylabel("万頭・匹"); ax.legend(frameon=False, loc="upper left", ncol=4, fontsize=9)
ax.set_xlim(1998, 2021); ax.set_ylim(0, 50)
foot(fig, "クマ類（ツキノワグマとヒグマ）は獣類の0.1〜0.3%で、図ではほとんど見えない。そのほかはタヌキ、アライグマ、ノウサギ、ハクビシンなど")
fig.savefig(FIG / "w1_mix.png"); plt.close(fig)
