"""141：賃上げ率は企業規模でどれだけ差があったのか（1975〜2025年）"""
import numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import *

t1 = table1(); t4 = table4(); t6 = table6()
t1.to_csv(DATA / "table1_rate_by_size.csv", index=False)
t4.to_csv(DATA / "table4_implementation_by_size.csv", index=False)
t6.to_csv(DATA / "table6_factor_by_size.csv", index=False)

rate = t1.pivot(index="year", columns="size", values="rate_pct")[SIZES]
amt = t1.pivot(index="year", columns="size", values="amount_yen")[SIZES]
gap = pd.DataFrame({"rate_gap_pt": rate["5,000人以上"] - rate["100～299人"],
                    "amount_gap_yen": amt["5,000人以上"] - amt["100～299人"],
                    "rate_large": rate["5,000人以上"], "rate_small": rate["100～299人"], "rate_all": rate["計"]})
gap.round(2).to_csv(RES / "a141_gap_by_year.csv")

periods = {"1975〜1989": (1975, 1989), "1990〜1999": (1990, 1999), "2000〜2012": (2000, 2012),
           "2013〜2022": (2013, 2022), "2023〜2025": (2023, 2025)}
rows = []
for k, (a, b) in periods.items():
    g = gap.loc[a:b]
    rows.append({"period": k, "rate_large": g.rate_large.mean(), "rate_small": g.rate_small.mean(),
                 "gap_pt": g.rate_gap_pt.mean(), "years_large_higher": int((g.rate_gap_pt > 0).sum()),
                 "years_small_higher": int((g.rate_gap_pt < 0).sum()), "years": len(g)})
per = pd.DataFrame(rows).round(2); per.to_csv(RES / "a141_gap_by_period.csv", index=False)
print(per.to_string())
print(gap.loc[2019:].round(2).to_string())

# 引き上げた企業の割合
raised = t4.pivot(index="year", columns="size", values="raised")[SIZES]
raised.round(1).to_csv(RES / "a141_raised_share.csv")
print(raised.loc[[2000, 2010, 2019, 2022, 2023, 2024, 2025]].to_string())
f6 = t6[t6.year.isin([2019, 2022, 2023, 2024, 2025])].set_index(["size", "year"])[
    ["業績", "世間相場", "労働力の確保・定着", "消費者物価", "雇用の維持"]].sort_index()
f6.to_csv(RES / "a141_factor_recent.csv")

# 図1 規模別の改定率
fig, ax = plt.subplots(figsize=(8.6, 4.4))
cols = {"5,000人以上": ORANGE, "1,000～4,999人": "#f3a77f", "300～999人": LIGHT, "100～299人": BLUE}
for s, c in cols.items():
    ax.plot(rate.index, rate[s], color=c, lw=2 if s in ("5,000人以上", "100～299人") else 1.2, label=s)
ax.set_xlim(1974, 2026); ax.set_ylabel("1人平均賃金の改定率（％）")
ax.set_title("企業規模別 1人平均賃金の改定率（1975〜2025年）", loc="left")
ax.legend(frameon=False, ncol=4, fontsize=9, loc="upper right", bbox_to_anchor=(1, 1.02))
ax2 = fig.add_axes([0.5, 0.5, 0.33, 0.27])
for s, c in cols.items():
    ax2.plot(rate.loc[2015:].index, rate.loc[2015:, s], color=c, lw=1.6, marker="o", ms=2.5)
ax2.set_title("2015〜2025年", fontsize=9); ax2.tick_params(labelsize=8)
for sp in ("top", "right"): ax2.spines[sp].set_visible(False)
fig.text(0.0, -0.02, SOURCE + "（単純平均は1979年まで、1980年以降は加重平均）", fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a141_rate.png"); plt.close(fig)

# 図2 差（5,000人以上 − 100〜299人）
fig, ax = plt.subplots(figsize=(8.6, 4.0))
g = gap.rate_gap_pt
ax.bar(g.index, g.where(g > 0, 0), color=ORANGE, width=0.8, label="5,000人以上のほうが高い")
ax.bar(g.index, g.where(g < 0, 0), color=BLUE, width=0.8, label="100〜299人のほうが高い")
ax.axhline(0, color=INK, lw=0.8)
ax.set_ylabel("改定率の差（ポイント）"); ax.set_xlim(1974, 2026)
ax.set_title("5,000人以上と100〜299人の改定率の差", loc="left")
ax.legend(frameon=False, fontsize=9, loc="upper left")
fig.text(0.0, -0.03, SOURCE, fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a141_gap.png"); plt.close(fig)

# 図3 引き上げた企業の割合
fig, ax = plt.subplots(figsize=(8.6, 4.0))
r2 = raised.loc[1999:]
for s, c in cols.items():
    ax.plot(r2.index, r2[s], color=c, lw=2 if s in ("5,000人以上", "100～299人") else 1.2, label=s)
ax.set_ylabel("1人平均賃金を引き上げた・引き上げる企業（％）"); ax.set_ylim(50, 101)
ax.set_title("賃金を引き上げた企業の割合（1999〜2025年）", loc="left")
ax.legend(frameon=False, ncol=2, fontsize=9, loc="lower right")
fig.text(0.0, -0.03, SOURCE, fontsize=7.5, color=GRAY)
fig.savefig(FIG / "a141_raised.png"); plt.close(fig)
