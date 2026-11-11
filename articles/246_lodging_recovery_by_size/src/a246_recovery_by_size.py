"""A246 施設の大きさ（従業者数）で、客の戻り方は違ったのか"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import table, RES, FIG, C, GRAY, SIZES, SIZE_JA, note

t1, t2, t3, t8 = table(1), table(2), table(3), table(8)
K = SIZES + ["total"]
a2 = t2[t2.month == 0].set_index("year")[K]
a3 = t3[t3.month == 0].set_index("year")[K]
fac = t1.groupby("year")[K].mean()                     # 施設数は12か月の平均
occ = t8[t8.month == 0].set_index("year")[K]           # 客室稼働率（%）

idx = (a2 / a2.loc[2019] * 100).round(1)
idx3 = (a3 / a3.loc[2019] * 100).round(1)
idx.to_csv(RES / "a246_guest_nights_index_2019eq100.csv")
idx3.to_csv(RES / "a246_guests_index_2019eq100.csv")
occ.round(1).to_csv(RES / "a246_room_occupancy.csv")

# 2019→2025 の延べ宿泊者数の変化を、施設数と1施設あたりに分ける（対数で足し算に）
rows = []
for k in K:
    g = np.log(a2.loc[2025, k] / a2.loc[2019, k])
    gf = np.log(fac.loc[2025, k] / fac.loc[2019, k])
    rows.append({"size": k, "nights_2019": int(a2.loc[2019, k]), "nights_2025": int(a2.loc[2025, k]),
                 "change_pct": round((a2.loc[2025, k] / a2.loc[2019, k] - 1) * 100, 1),
                 "facilities_2019": round(fac.loc[2019, k]), "facilities_2025": round(fac.loc[2025, k]),
                 "facilities_pct": round((fac.loc[2025, k] / fac.loc[2019, k] - 1) * 100, 1),
                 "per_facility_pct": round((a2.loc[2025, k] / fac.loc[2025, k] / (a2.loc[2019, k] / fac.loc[2019, k]) - 1) * 100, 1),
                 "log_total": round(g, 4), "log_facilities": round(gf, 4), "log_per_facility": round(g - gf, 4)})
dec = pd.DataFrame(rows); dec.to_csv(RES / "a246_decomposition_2019_2025.csv", index=False)

# 頑健性：同じ月どうし（2025年の各月 ÷ 2019年の同じ月）
m2 = t2[t2.month > 0]
mon = (m2[m2.year == 2025].set_index("month")[K] / m2[m2.year == 2019].set_index("month")[K] * 100).round(1)
mon.to_csv(RES / "a246_monthly_2025_vs_2019.csv")
rank_same = int((mon[SIZES].rank(axis=1, ascending=False)["s100"] == 4).sum())
# 頑健性：2023年・2024年の位置
summary = {
    "index_2019eq100": idx.loc[[2020, 2021, 2022, 2023, 2024, 2025]].to_dict(orient="index"),
    "guests_index_2025": idx3.loc[2025].to_dict(),
    "first_year_over_2019": {k: int(next((y for y in range(2020, 2026) if idx.loc[y, k] >= 100), 0)) for k in K},
    "occupancy_2019": occ.loc[2019].round(1).to_dict(), "occupancy_2025": occ.loc[2025].round(1).to_dict(),
    "decomposition": dec.to_dict(orient="records"),
    "months_2025_where_100plus_is_lowest_of_4": rank_same,
    "monthly_2025_vs_2019_range": {k: [float(mon[k].min()), float(mon[k].max())] for k in K},
}
json.dump(summary, open(RES / "a246_summary.json", "w"), ensure_ascii=False, indent=1)

# 図1：2019年=100 の延べ宿泊者数
fig, ax = plt.subplots(figsize=(8, 4.6))
for i, k in enumerate(SIZES):
    ax.plot(idx.index, idx[k], marker="o", ms=4, color=C[i], lw=2, label=SIZE_JA[k])
ax.plot(idx.index, idx["total"], color=GRAY, lw=1.5, ls="--", label="全体")
ax.axhline(100, color="#888", lw=0.8)
ax.set_xticks(idx.index); ax.set_ylabel("延べ宿泊者数（2019年＝100）")
ax.set_title("延べ宿泊者数の戻り方：施設の従業者数別")
ax.legend(ncol=5, fontsize=9, loc="lower left", frameon=False)
note(ax); fig.savefig(FIG / "a246_index_by_size.png"); plt.close(fig)

# 図2：客室稼働率
fig, ax = plt.subplots(figsize=(8, 4.4))
yrs = [2019, 2022, 2025]; w = 0.26; x = np.arange(len(K))
for j, y in enumerate(yrs):
    b = ax.bar(x + (j - 1) * w, occ.loc[y, K], w, color=[GRAY, C[1], C[0]][j], label=f"{y}年")
    for r in b:
        ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.8, f"{r.get_height():.1f}", ha="center", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels([SIZE_JA[k] for k in K]); ax.set_ylim(0, 85)
ax.set_ylabel("客室稼働率（%）"); ax.set_title("客室稼働率：100人以上の施設は2019年を約5ポイント下回る")
ax.legend(frameon=False, fontsize=9); note(ax); fig.savefig(FIG / "a246_occupancy_by_size.png"); plt.close(fig)

# 図3：2025年の各月 ÷ 2019年の同じ月
fig, ax = plt.subplots(figsize=(8, 4.4))
for i, k in enumerate(SIZES):
    ax.plot(mon.index, mon[k], marker="o", ms=4, color=C[i], lw=2, label=SIZE_JA[k])
ax.axhline(100, color="#888", lw=0.8); ax.set_xticks(mon.index); ax.set_xticklabels([f"{i}月" for i in mon.index])
ax.set_ylabel("2025年の延べ宿泊者数（2019年の同じ月＝100）")
ax.set_title("月ごとに比べても、100人以上の施設の戻りがいちばん小さい")
ax.legend(frameon=False, fontsize=9, ncol=4, loc="upper left"); ax.set_ylim(95, 132); note(ax)
fig.savefig(FIG / "a246_monthly_vs_2019.png"); plt.close(fig)
print(json.dumps(summary, ensure_ascii=False)[:1500])
