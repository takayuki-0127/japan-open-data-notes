"""390 年間の予算を月に割る方法で、月ごとの達成率はどれだけ変わるのか
商業動態統計（6業態・月次）を実績に見立てる。年間の予算は、その年の実績の合計と同じ（年間の達成率は必ず100%）にして、
月への割り方だけで、月ごとの達成率がどれだけ動くかを見る。"""
import json, calendar
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import *

d = pd.read_csv(DATA / "meti_sales_monthly.csv", parse_dates=["ym"])
d["year"], d["month"] = d.ym.dt.year, d.ym.dt.month
G = ["百貨店", "スーパー", "コンビニ", "家電大型専門店", "ドラッグストア", "ホームセンター"]
YEARS = list(range(2017, 2026))                              # 前3年が要るので2017年から。2026年は年の途中なので使わない
W = d.pivot_table(index=["gyotai", "year"], columns="month", values="sales")
METHODS = ["均等（12分の1）", "日数の割合", "前年の月の割合", "前3年の平均の割合"]


def shares(g, y, m):
    if m == METHODS[0]: return np.full(12, 1 / 12)
    if m == METHODS[1]:
        dd = np.array([calendar.monthrange(y, k)[1] for k in range(1, 13)]); return dd / dd.sum()
    if m == METHODS[2]:
        p = W.loc[(g, y - 1)].to_numpy(); return p / p.sum()
    p = np.mean([W.loc[(g, y - k)].to_numpy() / W.loc[(g, y - k)].sum() for k in (1, 2, 3)], axis=0); return p / p.sum()


rows = []; mon = []
for g in G:
    for y in YEARS:
        act = W.loc[(g, y)].to_numpy().astype(float); budget = act.sum()        # 年間の予算＝年間の実績
        for m in METHODS:
            b = budget * shares(g, y, m); r = 100 * act / b
            ytd6 = 100 * act[:6].sum() / b[:6].sum()
            rows.append({"業態": g, "年": y, "割り方": m, "達成率の最小%": round(r.min(), 1), "達成率の最大%": round(r.max(), 1),
                         "幅（ポイント）": round(r.max() - r.min(), 1), "100%未満の月": int((r < 100).sum()),
                         "95%未満の月": int((r < 95).sum()), "105%以上の月": int((r >= 105).sum()),
                         "6月までの累計の達成率%": round(ytd6, 1)})
            for k in range(12): mon.append({"業態": g, "年": y, "月": k + 1, "割り方": m, "実績": act[k], "予算": round(b[k], 1), "達成率%": round(r[k], 2)})
res = pd.DataFrame(rows); res.to_csv(RES / "by_industry_year_method.csv", index=False)
mon = pd.DataFrame(mon); mon.to_csv(RES / "monthly_achievement.csv", index=False)

def summ(x):
    return x.groupby(["業態", "割り方"], sort=False).agg(幅の中央値=("幅（ポイント）", "median"), 未満95の月_年平均=("95%未満の月", "mean"),
                                                 以上105の月_年平均=("105%以上の月", "mean"), 未満100の月_年平均=("100%未満の月", "mean"),
                                                 累計6月の最小=("6月までの累計の達成率%", "min"), 累計6月の最大=("6月までの累計の達成率%", "max")).round(1).reset_index()
s_all = summ(res); s_all.to_csv(RES / "summary_all_years.csv", index=False)
calm = res[~res["年"].isin([2019, 2020, 2021])]              # 消費税率の引き上げ（2019年10月）とコロナの年を除く
s_calm = summ(calm); s_calm.to_csv(RES / "summary_excl_2019_2021.csv", index=False)
tot = res.groupby("割り方", sort=False).agg(幅の中央値=("幅（ポイント）", "median"), 未満95の月_年平均=("95%未満の月", "mean"),
                                         以上105の月_年平均=("105%以上の月", "mean"), 未満100の月_年平均=("100%未満の月", "mean")).round(1)
tot_calm = calm.groupby("割り方", sort=False).agg(幅の中央値=("幅（ポイント）", "median"), 未満95の月_年平均=("95%未満の月", "mean"),
                                              以上105の月_年平均=("105%以上の月", "mean")).round(1)
tot.to_csv(RES / "summary_by_method.csv")

# 月ごとの「くせ」：均等に割ったとき、どの月がいつも未達になるか（2017〜2025年の9年のうち何年か）
eq = mon[mon["割り方"] == METHODS[0]].assign(u=lambda t: t["達成率%"] < 100).pivot_table(index="業態", columns="月", values="u", aggfunc="sum").loc[G]
eq.to_csv(RES / "equal_split_months_below_100.csv")

# ---- 図 ----
SRC = "経済産業省「商業動態統計」業態別販売額（月次）をもとに作成者が加工して作成。年間の予算＝その年の実績の合計と置いた場合"
fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.4), sharey=False)
for a, g in zip(axs, ("百貨店", "コンビニ")):
    for m, c, ls in zip(METHODS, (GRAY, LIGHT, BLUE, ORANGE), ("-", "-", "-", "--")):
        x = mon[(mon["業態"] == g) & (mon["年"] == 2025) & (mon["割り方"] == m)]
        a.plot(x["月"], x["達成率%"], "o-", ms=3, color=c, ls=ls, label=m)
    a.axhline(100, color=INK, lw=0.8); a.set_xticks(range(1, 13)); a.set_xlabel("月"); a.set_ylabel("月の達成率（%）")
    a.set_title(f"{g}（2025年）", fontsize=11)
axs[0].legend(fontsize=8.5, frameon=False)
fig.suptitle("同じ実績・同じ年間予算でも、月への割り方で月の達成率は変わる", y=1.02)
save(fig, "a390_example_2025.png", SRC)

fig, ax = plt.subplots(figsize=(10, 4.6)); x = np.arange(len(G)); w = 0.2
for i, (m, c) in enumerate(zip(METHODS, (GRAY, LIGHT, BLUE, ORANGE))):
    v = [float(s_all[(s_all["業態"] == g) & (s_all["割り方"] == m)]["幅の中央値"].iloc[0]) for g in G]
    ax.bar(x + (i - 1.5) * w, v, w, color=c, label=m)
    for xi, t in zip(x, v): ax.text(xi + (i - 1.5) * w, t + 0.4, f"{t:.0f}", ha="center", fontsize=7.5)
ax.set_xticks(x); ax.set_xticklabels(G); ax.set_ylabel("月の達成率の幅（最大−最小、ポイント）")
ax.set_title("月の達成率の幅（2017〜2025年の9年の中央値）"); ax.legend(fontsize=8.5, frameon=False)
save(fig, "a390_range_by_industry.png", SRC)

fig, ax = plt.subplots(figsize=(10, 4.6))
for i, (m, c) in enumerate(zip(METHODS, (GRAY, LIGHT, BLUE, ORANGE))):
    v = [float(s_all[(s_all["業態"] == g) & (s_all["割り方"] == m)]["未満95の月_年平均"].iloc[0]) for g in G]
    ax.bar(x + (i - 1.5) * w, v, w, color=c, label=m)
    for xi, t in zip(x, v): ax.text(xi + (i - 1.5) * w, t + 0.05, f"{t:.1f}", ha="center", fontsize=7.5)
ax.set_xticks(x); ax.set_xticklabels(G); ax.set_ylabel("達成率が95%未満の月の数（1年あたり）")
ax.set_title("年間では100%なのに「未達」（95%未満）と出る月の数（9年の平均）"); ax.legend(fontsize=8.5, frameon=False)
save(fig, "a390_months_below_95.png", SRC)

ex = res[(res["業態"] == "百貨店") & (res["年"] == 2025)].set_index("割り方")
main = {"業態": G, "年": [YEARS[0], YEARS[-1]], "割り方ごと（6業態×9年）": tot.reset_index().to_dict("records"),
        "2019〜2021年を除く": tot_calm.reset_index().to_dict("records"),
        "百貨店2025年": ex[["達成率の最小%", "達成率の最大%", "幅（ポイント）", "95%未満の月", "6月までの累計の達成率%"]].reset_index().to_dict("records")}
json.dump(main, open(RES / "a390_main.json", "w"), ensure_ascii=False, indent=1)
print(s_all.to_string()); print(tot.to_string()); print(tot_calm.to_string()); print(eq.to_string()); print(ex.to_string())
print(res[(res["年"].isin([2020, 2021])) & (res["割り方"] == METHODS[2])].to_string())
