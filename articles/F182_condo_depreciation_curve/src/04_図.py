"""04 図：5枚"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, SOURCE, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE

C = pd.read_csv(RES / "age_curves.csv"); S = pd.read_csv(RES / "summary_by_spec.csv")
M = C[C.spec == "基本（全国）"].sort_values("age"); med = pd.read_csv(RES / "raw_median_by_age.csv")
foot = lambda f: f.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top", wrap=True)
h = S.set_index("spec").loc["基本（全国）", "半値の築年数"]

# 1 減価曲線
f, ax = plt.subplots(figsize=(8, 4.8))
ax.fill_between(M.age, M.lo * 100, M.hi * 100, color=LIGHT, alpha=.6, lw=0)
ax.plot(M.age, M.rel * 100, color=BLUE, lw=2.2, label="物件の特徴と市区町村×四半期をそろえた値")
mm = med[med.age <= 50]
ax.plot(mm.age, mm.rel_median * 100, color=GRAY, lw=1.4, ls="--", label="何もそろえない㎡単価の中央値")
ax.axhline(50, color=INK, lw=.8, ls=":")
ax.annotate(f"築{h:.1f}年で\n築1年の半分", xy=(h, 50), xytext=(h + 4, 70), fontsize=10, arrowprops=dict(arrowstyle="->", color=INK))
ax.set_xlabel("築年数（取引した年 − 建築年）"); ax.set_ylabel("築1年＝100 とした㎡単価")
ax.set_title("中古マンションの㎡単価は、築年数でどう下がるか（全国、2015〜2025年）", loc="left")
ax.set_ylim(15, 115); ax.set_xlim(0, 50); ax.legend(frameon=False, loc="upper right", fontsize=9)
foot(f); f.savefig(FIG / "f182_1_curve.png"); plt.close(f)

# 2 1年ごとの下がり方
f, ax = plt.subplots(figsize=(8, 4.4))
y = M.set_index("age").rel; ch = (y / y.shift(1) - 1).dropna() * 100
cols = [ORANGE if a <= 3 else BLUE for a in ch.index]
ax.bar(ch.index, ch.values, color=cols, width=.8)
avg = S.set_index("spec").loc["基本（全国）", "築3〜20年の年率"]
ax.axhline(avg, color=INK, lw=.8, ls=":"); ax.text(51, avg - 0.3, f"築3〜20年\nの平均\n{avg:.1f}%", va="top", fontsize=9)
ax.set_xlabel("築年数（その年までの1年間の変化）"); ax.set_ylabel("前の築年数からの変化（%）")
ax.set_title("値下がりが速いのは最初の3年。そのあとは年2〜3%台で続く", loc="left")
ax.set_xlim(0, 56)
foot(f); f.savefig(FIG / "f182_2_yearly_change.png"); plt.close(f)

# 3 地域
f, ax = plt.subplots(figsize=(8, 4.8))
pal = {"地域：東京23区": INK, "地域：東京圏": BLUE, "地域：大阪圏": ORANGE, "地域：名古屋圏": GREEN, "地域：地方の中心4道県": PURPLE, "地域：その他": GRAY}
for k, c in pal.items():
    r = C[C.spec == k].sort_values("age"); hh = S.set_index("spec").loc[k, "半値の築年数"]
    ax.plot(r.age, r.rel * 100, color=c, lw=2 if "23区" in k else 1.6, label=f"{k.replace('地域：', '')}（半分は築{hh:.0f}年）")
ax.axhline(50, color=INK, lw=.8, ls=":")
ax.set_xlabel("築年数"); ax.set_ylabel("築1年＝100 とした㎡単価"); ax.set_xlim(0, 50); ax.set_ylim(10, 115)
ax.set_title("半分になる築年数は、地域で19年から30年まで違う", loc="left"); ax.legend(frameon=False, fontsize=9)
f.text(0.01, -0.02, "東京圏＝東京・神奈川・埼玉・千葉、大阪圏＝大阪・京都・兵庫・奈良、名古屋圏＝愛知・岐阜・三重、地方の中心4道県＝北海道・宮城・広島・福岡。" + SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top", wrap=True)
f.savefig(FIG / "f182_3_regions.png"); plt.close(f)

# 4 期間
f, ax = plt.subplots(figsize=(8, 4.6))
for k, c in [("期間：2015〜2017年", GRAY), ("期間：2019〜2021年", LIGHT), ("期間：2023〜2025年", BLUE)]:
    r = C[C.spec == k].sort_values("age"); s = S.set_index("spec").loc[k]
    ax.plot(r.age, r.rel * 100, color=c, lw=2, label=f"{k.replace('期間：', '')}（最初の3年 {s['築0→3年の下がり']:.0f}%、半分は築{s['半値の築年数']:.0f}年）")
ax.axhline(50, color=INK, lw=.8, ls=":")
ax.set_xlabel("築年数"); ax.set_ylabel("築1年＝100 とした㎡単価"); ax.set_xlim(0, 50); ax.set_ylim(15, 115)
ax.set_title("値上がりが続いた2023〜2025年は、最初の3年の下がりが小さい", loc="left"); ax.legend(frameon=False, fontsize=9)
foot(f); f.savefig(FIG / "f182_4_periods.png"); plt.close(f)

# 5 条件を変えた結果
f, axs = plt.subplots(1, 2, figsize=(9.5, 5.2), sharey=True)
Sd = S.iloc[::-1].reset_index(drop=True)
for ax, col, ttl, c in [(axs[0], "築0→3年は築3〜20年の何年分", "最初の3年の下がりは、\nその後の何年分か", ORANGE), (axs[1], "半値の築年数", "築1年の半分になる築年数", BLUE)]:
    ax.scatter(Sd[col], Sd.index, color=[INK if s == "基本（全国）" else c for s in Sd.spec], s=36, zorder=3)
    ax.axvline(S.set_index("spec").loc["基本（全国）", col], color=INK, lw=.8, ls=":")
    ax.set_title(ttl, loc="left", fontsize=11); ax.grid(axis="x", color="#eee")
    for i, v in enumerate(Sd[col]): ax.text(v + 0.3, i, f"{v:.1f}", va="center", fontsize=8)
axs[0].set_yticks(Sd.index); axs[0].set_yticklabels(Sd.spec, fontsize=9)
axs[0].set_xlabel("年分"); axs[1].set_xlabel("年")
f.suptitle("条件を変えても、最初の3年の下がりは「その後の3〜9年分」", x=0.01, y=1.0, ha="left", fontsize=13); f.subplots_adjust(top=0.86)
foot(f); f.savefig(FIG / "f182_5_robustness.png"); plt.close(f)
print("ok")
