"""S4：外国人の延べ宿泊者数は、コロナ前（2019年）に戻ったか。戻り方は都道府県でどう違うか"""
from common import *
d, lab = read("SSDSE-B-2026")
d = d.rename(columns={d.columns[0]: "year", d.columns[1]: "code", d.columns[2]: "pref"})
p = d[d.code != "R00000"]
w = p.pivot(index="pref", columns="year", values="G7102")             # 外国人延べ宿泊者数（人泊）
tot = w.sum(); share = w.div(tot)
ratio = (w[2023] / w[2019]).sort_values()
pd.DataFrame({"2019": w[2019], "2023": w[2023], "ratio_2023_2019": ratio, "share_2019": share[2019], "share_2023": share[2023]}).sort_values("ratio_2023_2019").round(3).to_csv(RES / "s4_pref.csv", encoding="utf-8-sig")
top3 = share.apply(lambda c: c.nlargest(3).sum())
pd.DataFrame({"total_man": tot / 1e4, "top3_share": top3}).round(3).to_csv(RES / "s4_total.csv", encoding="utf-8-sig")
s = {"total_2019_man": tot[2019] / 1e4, "total_2023_man": tot[2023] / 1e4, "recovery": tot[2023] / tot[2019], "total_2021_man": tot[2021] / 1e4,
     "n_pref_recovered": int((ratio >= 1).sum()), "top3_2019": top3[2019], "top3_2023": top3[2023], "tokyo_share_2019": share.loc["東京都", 2019], "tokyo_share_2023": share.loc["東京都", 2023],
     "max_pref": ratio.index[-1], "max_ratio": ratio.iloc[-1], "min_pref": ratio.index[0], "min_ratio": ratio.iloc[0]}
pd.Series(s).to_csv(RES / "s4_summary.csv", header=["value"]); print(pd.Series(s))
SRC = source("SSDSE-県別推移（SSDSE-B-2026）") + "（元は観光庁「宿泊旅行統計調査」）"

fig, ax = plt.subplots(figsize=(8, 3.8))
ax.bar(tot.index, tot / 1e4, color=[ORANGE if y in (2020, 2021, 2022) else BLUE for y in tot.index])
for y, v in tot.items():
    ax.text(y, v / 1e4 + 150, f"{v / 1e4:,.0f}", ha="center", fontsize=8)
ax.set_ylabel("外国人の延べ宿泊者数（万人泊）"); ax.set_xticks(list(tot.index), [str(y) for y in tot.index], fontsize=9)
ax.set_title(f"2023年は2019年の{s['recovery'] * 100:.0f}%まで戻った", loc="left")
fig.text(0.01, -0.05, SRC, fontsize=7.5, color="#8a8984"); fig.savefig(FIG / "s4_total.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 9)); y = np.arange(len(ratio))
ax.barh(y, ratio * 100, color=[BLUE if v >= 1 else LIGHT for v in ratio], height=0.7)
ax.axvline(100, color=INK, lw=0.8)
for yi, v in zip(y, ratio):
    ax.text(v * 100 + 1, yi, f"{v * 100:.0f}%", va="center", fontsize=7.5)
ax.set_yticks(y, ratio.index, fontsize=8); ax.set_xlabel("2023年の外国人延べ宿泊者数 ÷ 2019年（%）"); ax.set_xlim(0, 140)
ax.set_title("2019年を超えたのは東京・福岡・京都など一部の都府県", loc="left")
fig.text(0.01, -0.02, SRC, fontsize=7.5, color="#8a8984"); fig.savefig(FIG / "s4_ratio.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 3.6))
ax.plot(top3.index, top3 * 100, color=BLUE, marker="o", ms=4, label="上位3都道府県のシェア")
ax.plot(share.columns, share.loc["東京都"] * 100, color=ORANGE, marker="o", ms=4, label="東京都のシェア")
ax.set_ylim(0, 70); ax.set_ylabel("全国に占める割合（%）"); ax.legend(frameon=False, fontsize=9, loc="lower left")
ax.set_xticks(list(top3.index), [str(y) for y in top3.index], fontsize=9)
ax.set_title("コロナ後は、東京・大阪・京都への集中が強まった", loc="left")
fig.text(0.01, -0.05, SRC, fontsize=7.5, color="#8a8984"); fig.savefig(FIG / "s4_share.png"); plt.close(fig)
