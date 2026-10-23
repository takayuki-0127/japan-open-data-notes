"""100年分の人口ピラミッド：形の指標・5年分のピラミッド・ベビーブーム世代の追跡"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load, topcode, FIG, RES, BLUE, ORANGE, GRAY, INK, GREEN, PURPLE, SOURCE

df = load()
df = df[df.kazoe == 0]          # 1944〜46年は数え年なので除く
d85 = topcode(df, 85)
years = sorted(d85.year.unique())

# ---- 形の指標 -------------------------------------------------------------
rows = []
for y in years:
    g = d85[d85.year == y].set_index("age").both
    tot = g.sum()
    g5 = g.groupby((g.index // 5) * 5).sum()          # 5歳階級（85+は85）
    single = g[g.index < 85]
    cum = single.cumsum() / tot
    # 中位年齢（各歳の中で線形補間）
    k = int(np.searchsorted(cum.values, 0.5))
    prev = cum.values[k - 1] if k > 0 else 0
    med = single.index[k] + (0.5 - prev) / (cum.values[k] - prev)
    young, old = g[g.index <= 14].sum(), g[g.index >= 65].sum()
    rows.append(dict(year=y, total=tot, share_0_14=young / tot * 100, share_15_64=g[(g.index >= 15) & (g.index <= 64)].sum() / tot * 100,
                     share_65=old / tot * 100, aging_index=old / young * 100, median_age=med,
                     modal_age=int(single.idxmax()), base_0_4=g5.loc[0], widest_5y_age=int(g5[g5.index < 85].idxmax()),
                     base_ratio=g5.loc[0] / g5[g5.index < 85].max(),
                     base_vs_40_44=g5.loc[0] / g5.loc[40]))
ind = pd.DataFrame(rows)
ind.round(3).to_csv(RES / "a140_indicators.csv", index=False)

def first_year(cond):
    s = ind.loc[cond, "year"]
    return int(s.iloc[0]) if len(s) else None

# 0〜4歳がいちばん大きい5歳階級（＝富士山型の裾）だった最後の年
base_widest = ind.loc[ind.widest_5y_age == 0, "year"]
# 0〜4歳が40〜44歳より少なくなった最初の年（中年より裾が細い＝つぼ型の目安）以降ずっとかどうか
below40 = ind.base_vs_40_44 < 1
first_below40 = first_year(below40)
always_after = all(below40[ind.year >= first_below40])
summary = {
    "last_year_base_widest": int(base_widest.max()),
    "first_year_0_4_lt_40_44": first_below40, "stays_after": always_after,
    "first_year_65_gt_0_14": first_year(ind.share_65 > ind.share_0_14),
    "first_year_65_ge_2x_0_14": first_year(ind.aging_index >= 200),
    "median_age_1920": round(ind.set_index("year").median_age[1920], 1),
    "median_age_1950": round(ind.set_index("year").median_age[1950], 1),
    "median_age_2024": round(ind.set_index("year").median_age[2024], 1),
}
for y in (1920, 1950, 1975, 2000, 2024):
    r = ind.set_index("year").loc[y]
    summary[f"y{y}"] = dict(s0_14=round(r.share_0_14, 1), s65=round(r.share_65, 1), modal=int(r.modal_age), widest5=int(r.widest_5y_age), base_ratio=round(r.base_ratio, 2))
pd.Series({k: str(v) for k, v in summary.items()}).to_csv(RES / "a140_summary.csv", header=["value"])
print(summary)

# ---- 図1：5つの年のピラミッド --------------------------------------------
YS = [1920, 1950, 1975, 2000, 2024]
fig, axes = plt.subplots(1, 5, figsize=(15, 5.2), sharey=True)
for ax, y in zip(axes, YS):
    g = d85[d85.year == y].set_index("age")
    tot = g.both.sum()
    g = g[g.index < 85]          # 85歳以上はまとめた値なので描かない
    ax.barh(g.index, -g.male / tot * 100, height=1.0, color=BLUE, lw=0)
    ax.barh(g.index, g.female / tot * 100, height=1.0, color=ORANGE, lw=0)
    ax.axvline(0, color=INK, lw=0.6)
    ax.set_xlim(-1.6, 1.6); ax.set_xticks([-1.5, -1, -0.5, 0, 0.5, 1, 1.5]); ax.set_xticklabels(["1.5", "1", ".5", "0", ".5", "1", "1.5"], fontsize=8)
    r = ind.set_index("year").loc[y]
    ax.set_title(f"{y}年\n0〜14歳 {r.share_0_14:.0f}%・65歳以上 {r.share_65:.0f}%", fontsize=11)
    ax.set_ylim(-1, 85)
axes[0].set_ylabel("年齢（0〜84歳）")
axes[0].text(-1.5, 80, "男", color=BLUE, fontsize=12); axes[0].text(1.0, 80, "女", color=ORANGE, fontsize=12)
fig.suptitle("人口ピラミッド（各歳の人口が総人口に占める割合、%）", x=0.06, y=1.07, ha="left", fontsize=14)
fig.text(0.06, -0.02, SOURCE + "。1945〜71年は沖縄県を含まない。85歳以上は省略", fontsize=8, color=GRAY)
fig.savefig(FIG / "a140_pyramids.png"); plt.close(fig)

# ---- 図2：子どもと高齢者の割合・中位年齢 --------------------------------
fig, ax = plt.subplots(figsize=(9.5, 5))
ax.plot(ind.year, ind.share_0_14, color=BLUE, lw=2.2, label="0〜14歳の割合")
ax.plot(ind.year, ind.share_65, color=ORANGE, lw=2.2, label="65歳以上の割合")
ax.set_ylabel("総人口に占める割合（%）"); ax.set_ylim(0, 45)
ax2 = ax.twinx(); ax2.spines["right"].set_visible(True)
ax2.plot(ind.year, ind.median_age, color=INK, lw=1.4, ls="--", label="中位年齢（右目盛り、歳）")
ax2.set_ylim(0, 60); ax2.set_ylabel("中位年齢（歳）")
y97 = summary["first_year_65_gt_0_14"]
ax.axvline(y97, color=GRAY, lw=0.8, ls=":"); ax.text(y97 + 1, 41, f"{y97}年：65歳以上が\n0〜14歳を上回る", fontsize=9, color=INK)
ax.axvspan(1941, 1946.5, color="#eeeeee", lw=0); ax.text(1941.3, 2, "1941〜46年\nは除く", fontsize=8, color=GRAY)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, frameon=False, loc="center right", bbox_to_anchor=(1.0, 0.62))
ax.set_title("子どもの割合と高齢者の割合（1920〜2024年）", loc="left")
fig.text(0.02, -0.03, SOURCE, fontsize=8, color=GRAY)
fig.savefig(FIG / "a140_shares.png"); plt.close(fig)

# ---- 図3：ベビーブーム世代を追う -----------------------------------------
dd = df[(df.age >= 0) & (df.top == 0)].copy()
dd["birth"] = dd.year - dd.age          # 10月1日現在の年齢なので、生まれ年は ±1年の幅がある
coh = {"1947〜49年生まれ（団塊の世代）": (1947, 1949), "1971〜74年生まれ（団塊ジュニア）": (1971, 1974)}
crow = []
for lab, (a, b) in coh.items():
    s = dd[(dd.birth >= a) & (dd.birth <= b) & (dd.year >= b + 1)].groupby("year").both.sum() / (b - a + 1)
    for y, v in s.items():
        crow.append(dict(cohort=lab, year=y, mean_per_birth_year=v))
coh_df = pd.DataFrame(crow)
# 各年の「最も人口の多い年齢」（85歳未満）
modal = ind[["year", "modal_age"]]
modal.to_csv(RES / "a140_modal_age.csv", index=False)
coh_df.round(1).to_csv(RES / "a140_cohorts.csv", index=False)

fig, (ax, bx) = plt.subplots(1, 2, figsize=(13, 5))
ax.scatter(modal.year, modal.modal_age, s=12, color=INK)
ax.set_ylabel("いちばん人口の多い年齢（歳）"); ax.set_xlabel("年")
xs = np.arange(1950, 2025)
ax.plot(xs, xs - 1948, color=ORANGE, lw=1, alpha=0.8); ax.text(1985, 1985 - 1948 + 6, "1948年生まれ", color=ORANGE, fontsize=9, ha="right")
ax.plot(np.arange(1975, 2025), np.arange(1975, 2025) - 1973, color=PURPLE, lw=1, alpha=0.8); ax.text(2000, 2000 - 1973 - 8, "1973年生まれ", color=PURPLE, fontsize=9)
ax.set_title("いちばん人口の多い年齢", loc="left")
for (lab, g), c in zip(coh_df.groupby("cohort", sort=False), [ORANGE, PURPLE]):
    bx.plot(g.year, g.mean_per_birth_year / 1000, color=c, lw=2, label=lab)
bx.set_ylabel("生まれ年1年あたりの人口（百万人）"); bx.set_ylim(0, 2.8)
bx.legend(frameon=False, loc="lower left"); bx.set_title("2つのベビーブーム世代の人数", loc="left")
fig.text(0.02, -0.03, SOURCE + "。年齢は10月1日現在なので、生まれ年は前後1年ずれる", fontsize=8, color=GRAY)
fig.savefig(FIG / "a140_cohorts.png"); plt.close(fig)

# 数字の確認用
for lab, g in coh_df.groupby("cohort", sort=False):
    g = g.set_index("year").mean_per_birth_year
    print(lab, "max", int(g.idxmax()), round(g.max()), "2024", round(g.get(2024, np.nan)))
print(modal.set_index("year").modal_age.loc[[1950, 1960, 1970, 1975, 1980, 1990, 2000, 2010, 2020, 2024]].to_dict())
print(ind.set_index("year").loc[[1920, 1930, 1940, 1950, 1955, 1960, 1970, 1975, 1980, 1990, 2000, 2010, 2020, 2024],
      ["share_0_14", "share_65", "median_age", "widest_5y_age", "base_ratio", "base_vs_40_44"]].round(2))
