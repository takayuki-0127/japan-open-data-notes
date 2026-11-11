"""A250 連泊は増えているのか
延べ宿泊者数（人泊）÷ 実宿泊者数（人）＝ 1回の宿泊で平均何泊したか（ここでは「平均泊数」と呼ぶ）。
施設ごとの集計なので、同じ旅行で別の宿に移った分は別の宿泊として数えられる。"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import table, RES, FIG, GRAY, SIZES, SIZE_JA, note
from common import C as COL

t2, t3, t4, t5 = table(2), table(3), table(4), table(5)
n2 = t2[t2.month == 0].set_index("year"); n3 = t3[t3.month == 0].set_index("year")
n2["jp"] = n2.total - n2.foreign; n3["jp"] = n3.total - n3.foreign
K = ["total", "jp", "foreign", "tour", "biz"] + SIZES
ratio = (n2[K] / n3[K]).round(4); ratio.to_csv(RES / "a250_nights_per_stay.csv")
T = ["ryokan", "resort", "business", "city", "kani", "kaisha"]
TJ = {"ryokan": "旅館", "resort": "リゾートホテル", "business": "ビジネスホテル", "city": "シティホテル", "kani": "簡易宿所", "kaisha": "会社・団体の宿泊所"}
a4 = t4[t4.month == 0].set_index("year"); a5 = t5[t5.month == 0].set_index("year")
rt = (a4[T] / a5[T]).round(4); rt.to_csv(RES / "a250_by_type.csv")
rtf = (a4[["foreign_" + t for t in T]].values / a5[["foreign_" + t for t in T]].values)
rtj = ((a4[T].values - a4[["foreign_" + t for t in T]].values) / (a5[T].values - a5[["foreign_" + t for t in T]].values))
pd.DataFrame(rtj, index=a4.index, columns=T).round(4).to_csv(RES / "a250_by_type_japanese.csv")
fshare = (n3.foreign / n3.total).round(4)        # 実宿泊者のうち外国人の割合


def decompose(a, b):
    """全体の平均泊数＝日本人の平均泊数×日本人の割合＋外国人の平均泊数×外国人の割合（割合は実宿泊者で）。2つの基準の平均で分ける"""
    ra, rb = ratio.loc[a], ratio.loc[b]; sa, sb = fshare.loc[a], fshare.loc[b]
    wj = ((1 - sa) + (1 - sb)) / 2; wf = (sa + sb) / 2
    jp = wj * (rb.jp - ra.jp); fr = wf * (rb.foreign - ra.foreign)
    mix = (sb - sa) * ((ra.foreign + rb.foreign) / 2 - (ra.jp + rb.jp) / 2)
    return {"from": a, "to": b, "total_from": round(ra.total, 3), "total_to": round(rb.total, 3), "change": round(rb.total - ra.total, 4),
            "japanese_within": round(jp, 4), "foreign_within": round(fr, 4), "foreign_share": round(mix, 4),
            "foreign_share_from": round(sa, 3), "foreign_share_to": round(sb, 3)}

dec = pd.DataFrame([decompose(2015, 2019), decompose(2019, 2025), decompose(2015, 2025)])
dec.to_csv(RES / "a250_decomposition.csv", index=False)
# 頑健性：月別（2025年の各月 − 2019年の同じ月、日本人）
m2 = t2[t2.month > 0].set_index(["year", "month"]); m3 = t3[t3.month > 0].set_index(["year", "month"])
mj = (m2.total - m2.foreign) / (m3.total - m3.foreign)
mon = (mj.loc[2025] - mj.loc[2019]).round(3)
summary = {"ratio": ratio.loc[[2015, 2019, 2022, 2023, 2024, 2025]].round(3).to_dict(orient="index"),
           "by_type_2019": rt.loc[2019].round(3).to_dict(), "by_type_2025": rt.loc[2025].round(3).to_dict(),
           "by_type_japanese_2019": dict(zip(T, np.round(rtj[a4.index.get_loc(2019)], 3))), "by_type_japanese_2025": dict(zip(T, np.round(rtj[a4.index.get_loc(2025)], 3))),
           "foreign_share_guests": fshare.round(3).to_dict(), "decomposition": dec.to_dict(orient="records"),
           "japanese_monthly_2025_minus_2019": mon.to_dict(), "japanese_months_up": int((mon > 0).sum())}
json.dump(summary, open(RES / "a250_summary.json", "w"), ensure_ascii=False, indent=1, default=float)

# 図1：平均泊数の推移
fig, ax = plt.subplots(figsize=(8, 4.4))
for k, col, lab in [("foreign", COL[2], "外国人"), ("total", "black", "全体"), ("jp", COL[0], "日本人")]:
    ax.plot(ratio.index, ratio[k], marker="o", color=col, lw=2, label=lab)
    ax.text(ratio.index[-1] + 0.15, ratio[k].iloc[-1], f"{ratio[k].iloc[-1]:.2f}", va="center", fontsize=9, color=col)
ax.axvspan(2019.5, 2022.5, color="#f1f1f1"); ax.text(2021, 2.13, "コロナの時期", ha="center", fontsize=8, color="#666")
ax.set_xticks(ratio.index); ax.set_xlim(2014.6, 2025.8); ax.set_ylim(1.2, 2.25)
ax.set_ylabel("平均泊数（延べ宿泊者数÷実宿泊者数）"); ax.set_title("1回の宿泊の平均泊数：日本人は1.3泊のまま")
ax.legend(frameon=False, fontsize=9, loc="upper left"); note(ax); fig.savefig(FIG / "a250_ratio_trend.png"); plt.close(fig)

# 図2：全体の伸びの分け方
fig, ax = plt.subplots(figsize=(8, 4.4))
x = np.arange(len(dec)); w = 0.25
ax.bar(x - w, dec.japanese_within, w, color=COL[0], label="日本人の平均泊数の変化")
ax.bar(x, dec.foreign_within, w, color=COL[2], label="外国人の平均泊数の変化")
ax.bar(x + w, dec.foreign_share, w, color=COL[1], label="外国人の割合が増えた分")
ax.scatter(x, dec.change, color="black", zorder=3, label="全体の変化")
for xi, v in zip(x, dec.change):
    ax.text(xi, 0.098, f"全体 {v:+.3f}泊", ha="center", fontsize=9)
ax.axhline(0, color="#888", lw=0.8); ax.set_ylim(-0.02, 0.11)
ax.set_xticks(x); ax.set_xticklabels([f"{a}→{b}年" for a, b in zip(dec["from"], dec["to"])])
ax.set_ylabel("平均泊数の変化（泊）"); ax.set_title("2019→2025年の伸びの4分の3は外国人から")
ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2); note(ax, y=-0.16)
fig.savefig(FIG / "a250_decomposition.png"); plt.close(fig)

# 図3：施設タイプ別（日本人）
fig, ax = plt.subplots(figsize=(8, 4.4))
x = np.arange(len(T)); w = 0.36
j19 = rtj[a4.index.get_loc(2019)]; j25 = rtj[a4.index.get_loc(2025)]
b1 = ax.bar(x - w / 2, j19, w, color=GRAY, label="2019年"); b2 = ax.bar(x + w / 2, j25, w, color=COL[0], label="2025年")
for b in list(b1) + list(b2):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02, f"{b.get_height():.2f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([TJ[t] for t in T], fontsize=9); ax.set_ylim(0, 1.75)
ax.set_ylabel("日本人の平均泊数（泊）"); ax.set_title("日本人の平均泊数：施設タイプ別")
ax.legend(frameon=False, fontsize=9); note(ax); fig.savefig(FIG / "a250_by_type_japanese.png"); plt.close(fig)
print(json.dumps(summary, ensure_ascii=False, default=float)[:3000])
