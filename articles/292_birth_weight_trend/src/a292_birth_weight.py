"""292 生まれたときの体重は、どれだけ軽くなったのか（全国の集計のみ）
人口動態統計 確定数 上巻 4-25（性・年次別の出生時体重）、4-27（単産－複産別）、4-28（母の年齢別 2,500g未満）、4-6（母の年齢別出生数）
"""
import numpy as np, pandas as pd
from common import rows, num, save_json, savefig, plt, RES


def weight_table(name):
    r = rows(name)
    hdr = next(x for x in r if x and x[0] == "" and len(x) > 5 and x[1][:4].isdigit())
    yrs = [int(v[:4]) for v in hdr[1:] if v[:4].isdigit()]
    i_pct = next(i for i, x in enumerate(r) if x and x[0].startswith("百分率"))
    def row(label, after=0):
        for x in r[after:]:
            if x and x[0].replace(" ", "") == label: return pd.Series([num(v) for v in x[1:1 + len(yrs)]], index=yrs)
        raise KeyError(label)
    return pd.DataFrame({"n_total": row("総数"), "n_lbw": row("2.5kg未満"), "n_unknown": row("不詳"),
                         "n_lt1": row("1.0kg未満"), "n_1_15": row("1.0～1.5kg"),
                         "n_35_40": row("3.5～4.0kg"), "n_40_45": row("4.0～4.5kg"), "n_45p": row("4.5kg以上"),
                         "pct_lbw": row("2.5kg未満", i_pct), "mean_kg": row("平均体重")})

m = weight_table("jinkou_r7_jokan_4-25-1_birth_weight_male.csv")
f = weight_table("jinkou_r7_jokan_4-25-2_birth_weight_female.csv")
yrs = list(m.index)
known = (m.n_total - m.n_unknown) + (f.n_total - f.n_unknown)
tot = pd.DataFrame({"lbw_pct": (m.n_lbw + f.n_lbw) / known * 100, "vlbw_pct": (m.n_lt1 + m.n_1_15 + f.n_lt1 + f.n_1_15) / known * 100,
                    "ge35_pct": (m.n_35_40 + m.n_40_45 + m.n_45p + f.n_35_40 + f.n_40_45 + f.n_45p) / known * 100,
                    "mean_male": m.mean_kg, "mean_female": f.mean_kg, "lbw_male": m.pct_lbw, "lbw_female": f.pct_lbw,
                    "births": m.n_total + f.n_total, "lbw_n": m.n_lbw + f.n_lbw})
tot.round(3).to_csv(RES / "a292_weight_by_year.csv")

# 2025年：母の年齢別・単産－複産別の 2,500g 未満の割合（4-28）
r = rows("jinkou_r7_jokan_4-28_lbw_by_mother_age.csv")
AG = ["19歳以下", "20～24歳", "25～29歳", "30～34歳", "35～39歳", "40～44歳", "45歳以上"]
def z2h(s): return s.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
blk, cur = {}, None
for x in r:
    if len(x) < 5: continue
    if x[0] in ("総数", "単産", "複産"): cur = x[0]; blk[cur] = {}
    if cur: blk[cur][z2h(x[1])] = [num(v) for v in x[2:5]]
lbw25 = pd.DataFrame({k: {a: blk[k][a][1] / blk[k][a][0] for a in AG} for k in blk})
n25 = pd.DataFrame({k: {a: blk[k][a][0] for a in AG} for k in blk})
lbw25.round(4).to_csv(RES / "a292_lbw_rate_by_age_2025.csv")
mult_share_lbw = blk["複産"]["総数"][1] / blk["総数"]["総数"][1]
single_lbw_pct = blk["単産"]["総数"][1] / blk["単産"]["総数"][0] * 100
mult_birth_share = blk["複産"]["総数"][0] / blk["総数"]["総数"][0] * 100

# 母の年齢構成だけが変わったら：2025年の年齢別の割合を、各年の母の年齢構成に当てる（直接標準化）
r6 = rows("jinkou_r7_jokan_4-6_births_mother_age.csv")
h6 = next(x for x in r6 if x and x[0] == "" and len(x) > 5 and x[1][:4].isdigit())
y6 = [int(v[:4]) for v in h6[1:] if v[:4].isdigit()]
i6 = next(i for i, x in enumerate(r6) if x and x[0].replace(" ", "") == "百分率")
g = {}
for x in r6[:i6]:
    k = x[0].replace(" ", "") if x else ""
    if k in ("14歳以下", "15～19歳", "20～24歳", "25～29歳", "30～34歳", "35～39歳", "40～44歳", "45～49歳", "50歳以上"):
        g[k] = [num(v) for v in x[1:1 + len(y6)]]
g = pd.DataFrame(g, index=y6)
age7 = pd.DataFrame({"19歳以下": g["14歳以下"] + g["15～19歳"], "20～24歳": g["20～24歳"], "25～29歳": g["25～29歳"],
                     "30～34歳": g["30～34歳"], "35～39歳": g["35～39歳"], "40～44歳": g["40～44歳"], "45歳以上": g["45～49歳"] + g["50歳以上"]})
w = age7.div(age7.sum(axis=1), axis=0)
std_all = (w * lbw25["総数"]).sum(axis=1) * 100
std_single = (w * lbw25["単産"]).sum(axis=1) * 100
stdz = pd.DataFrame({"expected_lbw_pct_age_only(2025 rates)": std_all, "expected_single_lbw_pct": std_single})
stdz["actual_lbw_pct"] = [tot.loc[y, "lbw_pct"] if y in tot.index else np.nan for y in stdz.index]
stdz.round(3).to_csv(RES / "a292_age_standardized.csv")
cmp_years = [y for y in (1975, 1985, 1995, 2005) if y in stdz.index]
age_part = {y: dict(actual_change=float(tot.loc[2025, "lbw_pct"] - tot.loc[y, "lbw_pct"]),
                    age_only_change=float(std_all.loc[2025] - std_all.loc[y])) for y in cmp_years}
for y in age_part: age_part[y]["age_share"] = age_part[y]["age_only_change"] / age_part[y]["actual_change"] if age_part[y]["actual_change"] else None

out = dict(
    years=[yrs[0], yrs[-1]], mean={y: dict(male=tot.loc[y, "mean_male"], female=tot.loc[y, "mean_female"]) for y in (1951, 1975, 1980, 2000, 2005, 2025)},
    lbw_pct={y: float(tot.loc[y, "lbw_pct"]) for y in (1951, 1975, 1980, 1990, 2000, 2005, 2010, 2015, 2020, 2025)},
    vlbw_pct={y: float(tot.loc[y, "vlbw_pct"]) for y in (1975, 2005, 2025)}, ge35_pct={y: float(tot.loc[y, "ge35_pct"]) for y in (1975, 2005, 2025)},
    lbw_min_year=int(tot["lbw_pct"].idxmin()), mean_male_max_year=int(tot["mean_male"].idxmax()),
    lbw_range_2005_2025=[float(tot.loc[[y for y in yrs if y >= 2005], "lbw_pct"].min()), float(tot.loc[[y for y in yrs if y >= 2005], "lbw_pct"].max())],
    births_2025=float(tot.loc[2025, "births"]), lbw_n_2025=float(tot.loc[2025, "lbw_n"]),
    rate_by_age_2025={a: float(lbw25.loc[a, "総数"]) for a in AG}, single_rate_by_age_2025={a: float(lbw25.loc[a, "単産"]) for a in AG},
    multiple_rate_2025=float(blk["複産"]["総数"][1] / blk["複産"]["総数"][0]), single_lbw_pct_2025=single_lbw_pct,
    multiple_birth_share_2025=mult_birth_share, multiple_share_of_lbw_2025=mult_share_lbw,
    age_standardized={y: float(std_all.loc[y]) for y in (1975, 1985, 1995, 2005, 2015, 2025)}, age_part=age_part,
)
save_json(out)

# 図1：平均体重（男女）
fig, ax = plt.subplots(figsize=(8, 3.9))
ax.plot(yrs, tot.mean_male, color="#1a73e8", marker="o", ms=3, lw=2, label="男")
ax.plot(yrs, tot.mean_female, color="#d93025", marker="o", ms=3, lw=2, label="女")
ax.set_ylabel("出生時の平均体重（kg）"); ax.legend(frameon=False)
ax.set_title("生まれたときの平均体重：1975年ごろがいちばん重く、2005年ごろから横ばい")
savefig(fig, "a292_mean.png")

# 図2：2,500g未満の割合と、母の年齢構成だけで説明できる分
fig, ax = plt.subplots(figsize=(8, 4.1))
ax.plot(yrs, tot.lbw_pct, color="#202124", marker="o", ms=3, lw=2, label="2,500g未満の割合（実際）")
sy = [y for y in stdz.index if y >= 1950]
ax.plot(sy, std_all.loc[sy], color="#f29900", ls="--", marker="s", ms=3, lw=1.5, label="母の年齢構成だけを動かした場合\n（年齢別の割合は2025年の値で固定）")
ax.set_ylabel("出生に占める割合（%）"); ax.set_ylim(0, None); ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.set_title("2,500g未満で生まれる割合：母の年齢構成で説明できるのは一部")
savefig(fig, "a292_lbw_age.png")

# 図3：2025年 母の年齢別の 2,500g 未満の割合（単産・複産）
fig, ax = plt.subplots(figsize=(8, 3.9))
x = np.arange(len(AG)); lab = ["〜19歳", "20〜24", "25〜29", "30〜34", "35〜39", "40〜44", "45歳〜"]
ax.bar(x - 0.2, lbw25["単産"] * 100, width=0.4, color="#7baaf7", label="単産（1人で生まれた）")
ax.bar(x + 0.2, lbw25["総数"] * 100, width=0.4, color="#174ea6", label="総数（双子などを含む）")
for i, a in enumerate(AG): ax.text(i - 0.2, lbw25.loc[a, "単産"] * 100 + 0.3, f"{lbw25.loc[a, '単産']*100:.1f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(lab); ax.set_ylabel("2,500g未満の割合（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("2025年：母の年齢別にみた 2,500g 未満で生まれる割合")
savefig(fig, "a292_by_age_2025.png")
print(tot.loc[[1951, 1975, 1980, 1990, 2000, 2005, 2010, 2015, 2020, 2025], ["lbw_pct", "vlbw_pct", "ge35_pct", "mean_male", "mean_female"]].round(2).to_string())
print(stdz.loc[[1975, 1985, 1995, 2005, 2015, 2025]].round(2).to_string()); print(age_part); print(mult_share_lbw, single_lbw_pct, mult_birth_share)
