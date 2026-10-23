"""70年の引っ越し：都道府県間移動者数、移動率、東京圏の転入超過、10年ごとの転入超過、月の偏り"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import *

# 第1表（全国）：年計・月別・移動率
df = read_xl(RAW / "000040430814_昭和29年.xls", header=None)
years = [int(v) if str(v).strip().isdigit() else None for v in df.iloc[6].tolist()]
J = [j for j, y in enumerate(years) if y]
YR = [years[j] for j in J]
def row(i): return [num(df.iat[i, j]) for j in J]
lab = df.iloc[:, 0].astype(str).str.strip().tolist()
i_all, i_intra, i_inter = 9, 24, 39  # 年計の行
assert "年計" in lab[i_inter] and "年計" in lab[i_all]
T = pd.DataFrame({"year": YR, "all": row(i_all), "intra": row(i_intra), "inter": row(i_inter)})
months = {}
for k in range(12): months[k + 1] = row(i_inter + 1 + k)
M = pd.DataFrame(months, index=YR)
T["rate_all"] = [num(df.iat[54, j]) or np.nan for j in J]
T["rate_inter"] = [num(df.iat[56, j]) or np.nan for j in J]
T.loc[T.rate_inter == 0, ["rate_all", "rate_inter"]] = np.nan
T["marapr_share"] = ((M[3] + M[4]) / M.sum(axis=1) * 100).values
T.to_csv(RES / "g1_national.csv", index=False, encoding="utf-8-sig")
pk = T.loc[T.inter.idxmax()]
print("peak", int(pk.year), int(pk.inter), "2025", int(T.inter.iloc[-1]), "ratio", T.inter.iloc[-1] / pk.inter)
print(T[T.year.isin([1954, 1960, 1970, 1973, 1980, 1990, 2000, 2010, 2018, 2020, 2025])].round(2).to_string())

# 第5表：転入超過数（都道府県×年）
N = series_table("000040430818_昭和29年.xls")
area = pd.DataFrame({"東京圏": N[TOKYO_AREA].sum(axis=1), "名古屋圏": N[NAGOYA_AREA].sum(axis=1), "大阪圏": N[OSAKA_AREA].sum(axis=1)})
area["東京都"] = N[13]
area.index.name = "year"; area.to_csv(RES / "g1_area_net.csv", encoding="utf-8-sig")
print(area.loc[[1962, 1967, 1975, 1987, 1994, 1995, 2007, 2019, 2020, 2021, 2022, 2023, 2024, 2025]])
print("東京圏の最大", area["東京圏"].idxmax(), area["東京圏"].max(), "最小", area["東京圏"].idxmin(), area["東京圏"].min())
print("大阪圏が転出超過になった最初の年", area.index[area["大阪圏"] < 0][0])

# 10年ごとの転入超過（合計）
dec = []
for d0 in range(1960, 2030, 10):
    s = N.loc[(N.index >= d0) & (N.index < d0 + 10)].sum()
    gain = s[s > 0].sort_values(ascending=False)
    dec.append({"decade": f"{d0}年代", "years": f"{max(d0,1954)}-{min(d0+9,2025)}", "n_gain": len(gain),
                "gainers": "、".join(f"{PREF[c-1]}({int(v):,})" for c, v in gain.items())})
D = pd.DataFrame(dec); D.to_csv(RES / "g1_decade_gainers.csv", index=False, encoding="utf-8-sig"); print(D.to_string())

# 月の構成（1960年代 vs 2020年代）
prof = pd.DataFrame({"1960年代": (M.loc[1960:1969].sum() / M.loc[1960:1969].sum().sum() * 100),
                     "1990年代": (M.loc[1990:1999].sum() / M.loc[1990:1999].sum().sum() * 100),
                     "2020〜25年": (M.loc[2020:2025].sum() / M.loc[2020:2025].sum().sum() * 100)})
prof.to_csv(RES / "g1_month_profile.csv", encoding="utf-8-sig"); print(prof.round(1)); print("3〜4月の割合 最大", T.loc[T.marapr_share.idxmax(), ["year", "marapr_share"]].tolist())

# 図1：都道府県間移動者数と移動率
fig, ax = plt.subplots(figsize=(8.6, 4.2))
ax.bar(T.year, T.inter / 1e4, color=LIGHT, width=0.85, label="都道府県間移動者（左軸、万人）")
ax.plot(T.year, T.intra / 1e4, color=GRAY, lw=1.6, label="都道府県内移動者（左軸、万人）")
ax.set_ylabel("万人"); ax.set_xlim(1952, 2027)
ax2 = ax.twinx(); ax2.plot(T.year, T.rate_inter, color=ORANGE, lw=2.2, label="都道府県間の移動率（右軸、%）")
ax2.set_ylabel("移動率（%）"); ax2.set_ylim(0, 4.5); ax2.spines["top"].set_visible(False)
ax.annotate(f"{int(pk.year)}年 {pk.inter/1e4:.0f}万人", (pk.year, pk.inter / 1e4), xytext=(pk.year + 6, pk.inter / 1e4 + 15), arrowprops=dict(arrowstyle="-", color=INK, lw=.7), fontsize=9)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=8.5, loc="upper right")
ax.set_title("引っ越しの数：都道府県をまたぐ移動は1970年代がピーク", loc="left")
note(ax, SOURCE + "\n日本人移動者。移動率は日本人人口に対する割合（2018年まで掲載）", -0.13)
fig.savefig(FIG / "g1_national.png"); plt.close(fig)

# 図2：3大都市圏の転入超過
fig, ax = plt.subplots(figsize=(8.6, 4.3))
for c, col in [("東京圏", BLUE), ("名古屋圏", GREEN), ("大阪圏", ORANGE)]:
    ax.plot(area.index, area[c] / 1e4, color=col, lw=2, label=c)
ax.axhline(0, color=INK, lw=.7)
for y, t, dy in [(1962, "高度成長期", 2), (1987, "バブル期", 2.5), (2007, "2000年代", 2.5), (2021, "コロナ", -4)]:
    ax.annotate(t, (y, area.loc[y, "東京圏"] / 1e4), xytext=(y, area.loc[y, "東京圏"] / 1e4 + dy), ha="center", fontsize=8.5, color=BLUE)
ax.set_ylim(-6, 45)
ax.set_ylabel("転入超過数（万人）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("3大都市圏の転入超過（転入−転出）", loc="left")
note(ax, SOURCE + "\n東京圏＝埼玉・千葉・東京・神奈川、名古屋圏＝岐阜・愛知・三重、大阪圏＝京都・大阪・兵庫・奈良", -0.13)
fig.savefig(FIG / "g1_area_net.png"); plt.close(fig)

# 図3：3〜4月の集中
fig, axes = plt.subplots(1, 2, figsize=(10, 3.9))
axes[0].plot(T.year, T.marapr_share, color=PURPLE, lw=2)
axes[0].set_ylabel("3月と4月の割合（%）"); axes[0].set_title("都道府県間の移動のうち3〜4月の割合", loc="left", fontsize=11)
for c, col in [("1960年代", GRAY), ("1990年代", GREEN), ("2020〜25年", ORANGE)]:
    axes[1].plot(range(1, 13), prof[c], "o-", color=col, lw=1.8, ms=4, label=c)
axes[1].set_xticks(range(1, 13)); axes[1].set_xticklabels([f"{m}月" for m in range(1, 13)], fontsize=8)
axes[1].set_ylabel("年間に占める割合（%）"); axes[1].legend(frameon=False, fontsize=9); axes[1].set_title("月ごとの割合", loc="left", fontsize=11)
note(axes[0], SOURCE, -0.14)
fig.savefig(FIG / "g1_month.png"); plt.close(fig)
