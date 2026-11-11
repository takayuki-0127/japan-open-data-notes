"""A249 1施設あたりの宿泊者は、増えたのか
1施設あたり延べ宿泊者数＝年の延べ宿泊者数 ÷ 施設数（月末の施設数の12か月平均）。
全体の1施設あたりの変化を「大きさ（従業者数）ごとの1施設あたりの変化」と「小さい施設が増えた・減った（構成）」に分ける。"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import table, RES, FIG, GRAY, SIZES, SIZE_JA, note
from common import C as COL

t1, t2, t3 = table(1), table(2), table(3)
K = SIZES + ["total"]
fac = t1.groupby("year")[K].mean()
nights = t2[t2.month == 0].set_index("year")[K]
guests = t3[t3.month == 0].set_index("year")[K]
per = nights / fac; perg = guests / fac
tab = pd.concat({"facilities": fac.round(0), "nights": nights, "per_facility_nights": per.round(0), "per_facility_guests": perg.round(0)}, axis=1)
tab.to_csv(RES / "a249_per_facility.csv")
share = fac[SIZES].div(fac[SIZES].sum(axis=1), axis=0)
share.round(4).to_csv(RES / "a249_facility_share.csv")
chk = float((fac[SIZES].sum(axis=1) - fac.total).abs().max())   # 大きさの合計＝総数か


def decompose(a, b, P=per):
    """1施設あたり（全体）の a→b の変化を、大きさごとの1施設あたりの変化（内側）と構成の変化に分ける（2つの基準の平均）"""
    wa, wb, pa, pb = share.loc[a], share.loc[b], P.loc[a, SIZES], P.loc[b, SIZES]
    within = float(((wa + wb) / 2 * (pb - pa)).sum()); mix = float(((wb - wa) * (pa + pb) / 2).sum())
    tot = float((wb * pb).sum() - (wa * pa).sum())
    return {"from": a, "to": b, "per_facility_from": round(float((wa * pa).sum())), "per_facility_to": round(float((wb * pb).sum())),
            "change": round(tot), "within_sizes": round(within), "size_mix": round(mix)}

dec = pd.DataFrame([decompose(2015, 2019), decompose(2019, 2025), decompose(2015, 2025)])
dec.to_csv(RES / "a249_decomposition.csv", index=False)
decg = pd.DataFrame([decompose(2019, 2025, perg), decompose(2015, 2025, perg)])
decg.to_csv(RES / "a249_decomposition_guests.csv", index=False)
# 頑健性：施設数を12月の値にしたとき
fac12 = t1[t1.month == 12].set_index("year")[K]
per12 = nights / fac12
summary = {"facilities": fac.round(0).loc[[2015, 2019, 2023, 2025]].to_dict(orient="index"),
           "per_facility": per.round(0).loc[[2015, 2019, 2023, 2025]].to_dict(orient="index"),
           "per_facility_change_2019_2025_pct": ((per.loc[2025] / per.loc[2019] - 1) * 100).round(1).to_dict(),
           "facility_change_2019_2025_pct": ((fac.loc[2025] / fac.loc[2019] - 1) * 100).round(1).to_dict(),
           "share_0_9": share["s0_9"].round(3).to_dict(), "sum_check_max_abs_diff": chk,
           "decomposition": dec.to_dict(orient="records"), "decomposition_guests": decg.to_dict(orient="records"),
           "per_facility_dec12_change_2019_2025_pct": ((per12.loc[2025] / per12.loc[2019] - 1) * 100).round(1).to_dict()}
json.dump(summary, open(RES / "a249_summary.json", "w"), ensure_ascii=False, indent=1)

# 図1：施設数
fig, ax = plt.subplots(figsize=(8, 4.4))
yrs = fac.index
bottom = np.zeros(len(yrs))
for i, k in enumerate(SIZES):
    ax.bar(yrs, fac[k], bottom=bottom, color=COL[i], label=SIZE_JA[k]); bottom += fac[k].values
for y, v in zip(yrs, fac.total):
    ax.text(y, v + 800, f"{v/10000:.1f}万", ha="center", fontsize=8)
ax.set_xticks(yrs); ax.set_ylabel("施設数（12か月の平均）"); ax.set_ylim(0, 82000)
ax.set_title("施設数は10年で1.45倍。増えたのはほぼ従業者0〜9人の施設"); ax.legend(frameon=False, fontsize=9, ncol=4, loc="upper left")
note(ax); fig.savefig(FIG / "a249_facilities.png"); plt.close(fig)

# 図2：1施設あたり延べ宿泊者数（2019年＝100）
fig, ax = plt.subplots(figsize=(8, 4.4))
ix = per / per.loc[2019] * 100
for i, k in enumerate(SIZES):
    ax.plot(ix.index, ix[k], marker="o", ms=4, color=COL[i], lw=2, label=SIZE_JA[k])
ax.plot(ix.index, ix.total, color="black", lw=2.2, ls="--", label="全体")
ax.axhline(100, color="#888", lw=0.8); ax.set_xticks(ix.index)
ax.set_ylabel("1施設あたり延べ宿泊者数（2019年＝100）"); ax.set_title("1施設あたり：10人以上の施設は2019年を上回り、全体では1割少ない")
ax.legend(frameon=False, fontsize=9, ncol=5, loc="lower left"); note(ax); fig.savefig(FIG / "a249_per_facility_index.png"); plt.close(fig)

# 図3：分解
fig, ax = plt.subplots(figsize=(8, 4.4))
labs = [f"{a}→{b}年" for a, b in zip(dec["from"], dec["to"])]; x = np.arange(len(dec)); w = 0.3
ax.bar(x - w / 2, dec.within_sizes, w, color=COL[3], label="大きさごとの1施設あたりの変化")
ax.bar(x + w / 2, dec.size_mix, w, color=COL[2], label="小さい施設が増えた分（構成）")
ax.scatter(x, dec.change, color="black", zorder=3, label="全体の1施設あたりの変化")
for xi, v in zip(x, dec.change):
    ax.text(xi + 0.02, v - 260 if v < 0 else v + 120, f"{v:+,}人泊", fontsize=9, ha="left")
ax.axhline(0, color="#888", lw=0.8); ax.set_xticks(x); ax.set_xticklabels(labs)
ax.set_ylabel("1施設あたり延べ宿泊者数の変化（人泊）"); ax.set_title("全体の1施設あたりが減ったのは、小さい施設が増えたから")
ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3); note(ax, y=-0.1)
fig.savefig(FIG / "a249_decomposition.png"); plt.close(fig)
print(json.dumps(summary, ensure_ascii=False)[:2500])
