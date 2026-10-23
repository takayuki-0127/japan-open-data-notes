"""入院患者の平均年齢・65歳以上/75歳以上の割合の長期推移と、年齢別の受療率の変化"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import load, summarize, FIG, RES, BLUE, ORANGE, GRAY, INK, GREEN, SOURCE

df = load()
ip, op = summarize(df, "入院"), summarize(df, "外来")
s = pd.concat([ip, op]); s.to_csv(RES / "a131_summary_by_year.csv", index=False)

# 図1 平均年齢
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(ip.year, ip.mean_age, "-o", ms=3.5, color=BLUE, label="入院患者")
ax.plot(op.year, op.mean_age, "-o", ms=3.5, color=ORANGE, label="外来患者")
ax.plot(ip.year, ip.pop_mean_age, "--", color=GRAY, label="人口（推計患者数÷受療率から逆算）")
for d, c in ((ip, BLUE), (op, ORANGE)):
    for y in (1960, 2023):
        v = d.loc[d.year == y, "mean_age"].iloc[0]
        ax.annotate(f"{v:.1f}歳", (y, v), textcoords="offset points", xytext=(4 if y == 1960 else -40, 6), color=c, fontsize=9)
ax.set_ylabel("平均年齢（歳）"); ax.set_ylim(20, 80)
ax.set_title("入院患者の平均年齢は1960年の36歳から2023年は73歳に")
ax.legend(frameon=False, loc="upper left")
fig.text(0.01, -0.04, "注：年齢階級の中央値で計算。最上位の階級（75歳以上〜90歳以上）は82〜92.5歳と仮定。1983年以前は7月、1984年以降は10月の調査\n" + SOURCE, fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a131_mean_age.png"); plt.close(fig)

# 図2 65歳以上・75歳以上の割合（入院患者と人口）
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(ip.year, ip.share65, "-o", ms=3.5, color=BLUE, label="入院患者：65歳以上")
ax.plot(ip.year, ip.share75, "-o", ms=3.5, color=GREEN, label="入院患者：75歳以上")
ax.plot(ip.year, ip.pop_share65, "--", color=BLUE, alpha=.6, label="人口：65歳以上")
ax.plot(ip.year, ip.pop_share75, "--", color=GREEN, alpha=.6, label="人口：75歳以上")
ax.set_ylabel("%"); ax.set_ylim(0, 85)
ax.set_title("2023年は入院患者の4人に3人が65歳以上、半分以上が75歳以上")
ax.legend(frameon=False, loc="upper left", ncol=2)
fig.text(0.01, -0.03, SOURCE, fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a131_share.png"); plt.close(fig)

# 図3 年齢別の入院受療率 1999 vs 2023 と、1999年の受療率のままだった場合
d = df[df.kind == "入院"]
a = d[d.year == 1999].set_index("age"); b = d[d.year == 2023].set_index("age")
ages = [x for x in b.index if x in a.index]
rt = pd.DataFrame({"rate1999": a.loc[ages, "rate_per100k"], "rate2023": b.loc[ages, "rate_per100k"]})
rt["ratio"] = (rt.rate2023 / rt.rate1999).round(3)
rt.to_csv(RES / "a131_rate_1999_2023.csv")
pop23 = b.patients_k * 1000 / b.rate_per100k * 1e5
cf = float((a.loc[ages, "rate_per100k"] * pop23.loc[ages] / 1e5 / 1000).sum())
# 1999年の人口で2023年の受療率なら
pop99 = a.patients_k * 1000 / a.rate_per100k * 1e5
cf2 = float((b.loc[ages, "rate_per100k"] * pop99.loc[ages] / 1e5 / 1000).sum())
dec = pd.DataFrame([dict(inpatients_1999=a.patients_k.sum(), inpatients_2023=b.patients_k.sum(),
                         if_1999_rates_2023_pop=round(cf, 1), if_2023_rates_1999_pop=round(cf2, 1))])
dec.to_csv(RES / "a131_counterfactual.csv", index=False)
fig, ax = plt.subplots(figsize=(8.6, 4.6))
x = np.arange(len(ages))
ax.bar(x - 0.2, rt.rate1999, 0.4, color=GRAY, label="1999年")
ax.bar(x + 0.2, rt.rate2023, 0.4, color=BLUE, label="2023年")
ax.set_xticks(x); ax.set_xticklabels(ages, rotation=60, fontsize=8)
ax.set_ylabel("入院受療率（人口10万対）")
ax.set_title("どの年齢でも入院する人の割合は下がった（75〜79歳は4,093→2,033）")
ax.legend(frameon=False)
fig.text(0.01, -0.12, f"注：1999年の年齢別受療率のままなら、2023年の入院患者は{cf/10:.0f}万人（実際は{b.patients_k.sum()/10:.0f}万人）\n" + SOURCE, fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a131_rate.png"); plt.close(fig)
print(ip[["year", "mean_age", "share65", "share75", "pop_mean_age", "pop_share65", "pop_share75"]].to_string(index=False))
print(op[["year", "mean_age", "share65", "share75"]].tail(3).to_string(index=False))
print(rt.to_string()); print(dec.to_string())
