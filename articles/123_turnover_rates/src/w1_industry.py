"""W1：辞める人が多い産業は、入ってくる人も多いか。転職して賃金が上がる人は増えたか"""
from common import *

d = industry_rates()
d.to_csv(DATA / "industry_rates.csv", index=False, encoding="utf-8-sig")
ind = d[d["産業"] != "調査産業計"].copy()

# 1) 産業ごとの入職率と離職率の関係（2025年、2009〜2025年の平均）
avg = ind.groupby("産業")[["入職率", "離職率"]].mean()
y25 = ind[ind["年"] == 2025].set_index("産業")[["入職率", "離職率"]]
tab = avg.add_suffix("_平均2009_2025").join(y25.add_suffix("_2025"))
tab["入職超過_平均"] = tab["入職率_平均2009_2025"] - tab["離職率_平均2009_2025"]
tab = tab.sort_values("離職率_平均2009_2025", ascending=False).round(2)
tab.insert(0, "略称", [SHORT[i] for i in tab.index])
tab.to_csv(RES / "w1_industry_2025_avg.csv", encoding="utf-8-sig")

def fit(x, y):
    b, a = np.polyfit(x, y, 1)
    return np.corrcoef(x, y)[0, 1], b, a
r25, b25, a25 = fit(y25["離職率"], y25["入職率"])
ra, ba, aa = fit(avg["離職率"], avg["入職率"])
# 年ごとの産業間相関
yr = ind.groupby("年").apply(lambda g: np.corrcoef(g["離職率"], g["入職率"])[0, 1]).rename("産業間の相関")
# 産業ごとの年々の変化（前年差）どうしの相関：同じ年に離職が増えると入職も増えるか
ind = ind.sort_values(["産業", "年"])
ind["d入"] = ind.groupby("産業")["入職率"].diff(); ind["d離"] = ind.groupby("産業")["離職率"].diff()
dd = ind.dropna(subset=["d入", "d離"])
r_diff = np.corrcoef(dd["d離"], dd["d入"])[0, 1]
stats = pd.DataFrame({"項目": ["相関_2025", "傾き_2025", "相関_平均2009_2025", "傾き_平均2009_2025",
                              "前年差どうしの相関（産業×年）", "前年差の組の数", "年ごとの相関_最小", "年ごとの相関_最大"],
                      "値": [r25, b25, ra, ba, r_diff, len(dd), yr.min(), yr.max()]}).round(3)
stats.to_csv(RES / "w1_correlation.csv", index=False, encoding="utf-8-sig")

# 2) 推移：全体（1991〜2025年、第1表）と宿泊・飲食など（2009〜2025年、第2表）
t1 = read_table("hyo01.xls")
tot = pd.DataFrame({"入職率": t1.loc["入職率|計|計"], "離職率": t1.loc["離職率|計|計"],
                    "転職入職率": t1.loc["入職率|転職入職率|計|計"]})
tot.index.name = "年"
tot.to_csv(RES / "w1_total_1991_2025.csv", encoding="utf-8-sig")
focus = ["宿泊業，飲食サービス業", "生活関連サービス業，娯楽業", "医療,福祉", "製造業"]
tr = d[d["産業"].isin(focus + ["調査産業計"])].pivot_table(index="年", columns="産業", values=["入職率", "離職率"])
tr.round(1).to_csv(RES / "w1_trend_2009_2025.csv", encoding="utf-8-sig")

# 3) 転職入職者の賃金変動（前の勤め先と比べて）
t11 = read_table("hyo11.xls")
ages = ["計", "19歳以下", "20～29歳", "30～44歳", "45～59歳", "60歳以上"]
wage = pd.concat({a: pd.DataFrame({"増加": t11.loc[f"{a}|１割以上増加"], "変わらない": t11.loc[f"{a}|１割未満増減"],
                                   "減少": t11.loc[f"{a}|１割以上減少"]}) for a in ages}, axis=1)
for a in ages:
    wage[(a, "増加−減少")] = wage[(a, "増加")] - wage[(a, "減少")]
wage = wage.sort_index(axis=1)
wage.index.name = "年"
wage.to_csv(RES / "w1_wage_change.csv", encoding="utf-8-sig")

# ---- 図 ----
fig, ax = plt.subplots(figsize=(7.4, 6))
lim = (4, 38)
LAB = {"宿泊業，飲食サービス業": (6, -3), "生活関連サービス業，娯楽業": (6, -10), "サービス業（他に分類されないもの）": (6, 2),
       "医療,福祉": (6, -8), "教育，学習支援業": (6, 0), "情報通信業": (-22, 7), "製造業": (6, -6), "建設業": (-30, -3),
       "複合サービス事業": (6, -3), "金融業，保険業": (6, -3)}
ax.plot(lim, lim, color=GRAY, lw=0.8, ls="--")
ax.text(33, 34.5, "入職率＝離職率", color=GRAY, fontsize=8, rotation=38)
for nm, r in avg.iterrows():
    ax.scatter(r["離職率"], r["入職率"], color=LIGHT, s=30, zorder=2)
for nm, r in y25.iterrows():
    hl = nm in focus
    ax.scatter(r["離職率"], r["入職率"], color=ORANGE if hl else BLUE, s=45, zorder=3)
    if nm in LAB:
        ax.annotate(SHORT[nm], (r["離職率"], r["入職率"]), xytext=LAB[nm], textcoords="offset points", fontsize=8.5, color=INK)
xs = np.array(lim)
ax.plot(xs, a25 + b25 * xs, color=BLUE, lw=1)
ax.set_xlim(*lim); ax.set_ylim(*lim)
ax.text(37, 5, "ラベルは一部の産業のみ", fontsize=8, color=GRAY, ha="right")
ax.set_xlabel("離職率（％）"); ax.set_ylabel("入職率（％）")
ax.set_title(f"産業別の入職率と離職率（2025年、相関{r25:.2f}）", loc="left")
ax.scatter([], [], color=BLUE, label="2025年"); ax.scatter([], [], color=LIGHT, label="2009〜2025年の平均")
ax.legend(frameon=False, loc="upper left", fontsize=9)
note(fig); fig.savefig(FIG / "w1_scatter.png"); plt.close(fig)

fig, axs = plt.subplots(1, 2, figsize=(11, 4.4), sharey=False)
ax = axs[0]
ax.plot(tot.index, tot["入職率"], color=BLUE, label="入職率"); ax.plot(tot.index, tot["離職率"], color=ORANGE, label="離職率")
ax.set_title("全体（1991〜2025年）", loc="left"); ax.set_ylabel("％"); ax.legend(frameon=False); ax.set_ylim(10, 20)
ax = axs[1]
cols = {"宿泊業，飲食サービス業": ORANGE, "生活関連サービス業，娯楽業": PURPLE, "医療,福祉": GREEN, "製造業": GRAY, "調査産業計": INK}
for nm, c in cols.items():
    ax.plot(tr.index, tr[("入職率", nm)], color=c, lw=1.8, label=SHORT[nm] + "（入職）")
    ax.plot(tr.index, tr[("離職率", nm)], color=c, lw=1.2, ls="--")
ax.set_title("産業別（2009〜2025年、実線＝入職率・点線＝離職率）", loc="left", fontsize=11)
ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper right"); ax.set_ylim(0, 45)
ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
note(fig); fig.savefig(FIG / "w1_trend.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8.6, 4.6))
ax.plot(wage.index, wage[("計", "増加")], color=BLUE, lw=2, label="1割以上増えた")
ax.plot(wage.index, wage[("計", "減少")], color=ORANGE, lw=2, label="1割以上減った")
ax.plot(wage.index, wage[("20～29歳", "増加")], color=BLUE, lw=1, ls="--", label="増えた（20〜29歳）")
ax.plot(wage.index, wage[("45～59歳", "増加")], color=BLUE, lw=1, ls=":", label="増えた（45〜59歳）")
ax.axvline(2006.5, color=GRAY, lw=0.6)
ax.text(2007, 44, "2007年から不詳を含めた割合", fontsize=8, color=GRAY)
ax.set_ylabel("転職入職者に占める割合（％）"); ax.set_ylim(0, 50)
ax.set_title("転職で賃金が増えた人・減った人の割合（前の勤め先との比較）", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="lower left")
note(fig); fig.savefig(FIG / "w1_wage.png"); plt.close(fig)

print(tab.to_string()); print(stats.to_string()); print(yr.round(2).to_string())
print(tr.loc[[2009, 2019, 2020, 2021, 2025]].round(1).T.to_string())
print(tot.loc[[1991, 2000, 2009, 2015, 2019, 2024, 2025]])
print(wage.loc[[1991, 1997, 1998, 2009, 2019, 2023, 2024, 2025]].round(1).T.to_string())
