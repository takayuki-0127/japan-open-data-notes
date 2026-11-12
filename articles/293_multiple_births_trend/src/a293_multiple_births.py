"""293 双子・三つ子の出生は、どれだけ増えて、どう変わったのか（全国の集計のみ）
人口動態統計 確定数 上巻 4-36（単産－複産別の分娩件数 1995〜2025年）、4-28（母の年齢別の単産・複産の出生数 2025年）、4-6（母の年齢別出生数）
"""
import re
import numpy as np, pandas as pd
from common import rows, num, save_json, savefig, plt, RES

r = rows("jinkou_r7_jokan_4-36_deliveries_single_multiple.csv")
hdr = next(x for x in r if x and x[0] == "" and len(x) > 5 and x[1][:4].isdigit())
yrs = [int(v[:4]) for v in hdr[1:] if v[:4].isdigit()]
lines = [(x[0], [num(v) for v in x[1:1 + len(yrs)]]) for x in r if x and x[0] and len(x) > 5 and not x[0].startswith("注")]
first = {}
for k, v in lines:
    first.setdefault(k, v)
T = pd.DataFrame({k: first[k] for k in ["総数", "単産", "複産", "双子", "三つ児", "四つ児", "五つ児"]}, index=yrs)
assert (T["複産"] - T[["双子", "三つ児", "四つ児", "五つ児"]].sum(axis=1)).abs().max() <= 2   # 六つ児・七つ児の数件

# 複産の分娩から、生まれた子（出生）の数を数える：「2出生1死産」なら2人
def births_of(label):
    t = label.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    m = re.match(r"^(\d)出生", t)
    return int(m.group(1)) if m else 0
mb = pd.Series(0.0, index=yrs)
for k, v in lines:
    b = births_of(k)
    if b: mb += np.array(v) * b
T["multiple_births"] = mb

# 総出生数（4-6）
r6 = rows("jinkou_r7_jokan_4-6_births_mother_age.csv")
h6 = next(x for x in r6 if x and x[0] == "" and len(x) > 5 and x[1][:4].isdigit())
y6 = [int(v[:4]) for v in h6[1:] if v[:4].isdigit()]
i6 = next(i for i, x in enumerate(r6) if x and x[0].replace(" ", "") == "百分率")
g = {}
for x in r6[:i6]:
    k = x[0].replace(" ", "") if x else ""
    if k in ("総数", "14歳以下", "15～19歳", "20～24歳", "25～29歳", "30～34歳", "35～39歳", "40～44歳", "45～49歳", "50歳以上"):
        g[k] = [num(v) for v in x[1:1 + len(y6)]]
g = pd.DataFrame(g, index=y6)
T["all_births"] = [g.loc[y, "総数"] if y in g.index else np.nan for y in yrs]
T["mult_per_1000_deliveries"] = T["複産"] / T["総数"] * 1000
T["twin_per_1000_deliveries"] = T["双子"] / T["総数"] * 1000
T["triplet_plus_per_10000_deliveries"] = (T["複産"] - T["双子"]) / T["総数"] * 10000
T["mult_birth_share_pct"] = T["multiple_births"] / T["all_births"] * 100
T.round(4).to_csv(RES / "a293_deliveries.csv")

# 2025年の母の年齢別の複産の割合（4-28）
r28 = rows("jinkou_r7_jokan_4-28_lbw_by_mother_age.csv")
AG = ["19歳以下", "20～24歳", "25～29歳", "30～34歳", "35～39歳", "40～44歳", "45歳以上"]
def z2h(s): return s.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
blk, cur = {}, None
for x in r28:
    if len(x) < 5: continue
    if x[0] in ("総数", "単産", "複産"): cur = x[0]; blk[cur] = {}
    if cur: blk[cur][z2h(x[1])] = num(x[2])
rate25 = pd.Series({a: blk["複産"][a] / blk["総数"][a] for a in AG})
rate25.round(5).to_csv(RES / "a293_multiple_share_by_age_2025.csv")
assert blk["複産"]["総数"] == T.loc[2025, "multiple_births"], (blk["複産"]["総数"], T.loc[2025, "multiple_births"])

age7 = pd.DataFrame({"19歳以下": g["14歳以下"] + g["15～19歳"], "20～24歳": g["20～24歳"], "25～29歳": g["25～29歳"],
                     "30～34歳": g["30～34歳"], "35～39歳": g["35～39歳"], "40～44歳": g["40～44歳"], "45歳以上": g["45～49歳"] + g["50歳以上"]})
w = age7.div(age7.sum(axis=1), axis=0)
exp_share = (w * rate25).sum(axis=1) * 100
cmp = pd.DataFrame({"actual_pct": T["mult_birth_share_pct"], "age_only_expected_pct": exp_share.reindex(yrs)})
cmp["actual_minus_expected"] = cmp["actual_pct"] - cmp["age_only_expected_pct"]
cmp.round(4).to_csv(RES / "a293_age_expected.csv")

pk = int(T["mult_per_1000_deliveries"].idxmax())
out = dict(
    years=[yrs[0], yrs[-1]], deliveries={y: dict(total=T.loc[y, "総数"], multiple=T.loc[y, "複産"], twins=T.loc[y, "双子"], triplets=T.loc[y, "三つ児"],
                                                  quads_plus=T.loc[y, ["四つ児", "五つ児"]].sum()) for y in (1995, 2000, 2004, 2005, 2008, 2015, 2025)},
    rate_per_1000={y: float(T.loc[y, "mult_per_1000_deliveries"]) for y in yrs}, peak_year=pk, peak_rate=float(T.loc[pk, "mult_per_1000_deliveries"]),
    triplet_plus_per_10000={y: float(T.loc[y, "triplet_plus_per_10000_deliveries"]) for y in (1995, 2004, 2010, 2025)},
    triplet_share_of_multiple={y: float((T.loc[y, "複産"] - T.loc[y, "双子"]) / T.loc[y, "複産"] * 100) for y in (1995, 2004, 2025)},
    multiple_births={y: float(T.loc[y, "multiple_births"]) for y in (1995, 2004, 2025)},
    mult_birth_share_pct={y: float(T.loc[y, "mult_birth_share_pct"]) for y in (1995, 2004, 2010, 2015, 2025)},
    rate_by_age_2025={a: float(rate25[a] * 100) for a in AG},
    age_expected_pct={y: float(exp_share.loc[y]) for y in (1995, 2005, 2015, 2025)},
    gap_actual_minus_expected={y: float(cmp.loc[y, "actual_minus_expected"]) for y in (1995, 2000, 2004, 2005, 2010, 2015, 2025)},
)
save_json(out)

# 図1：分娩1,000件あたりの複産
fig, ax = plt.subplots(figsize=(8, 3.9))
ax.plot(yrs, T["mult_per_1000_deliveries"], color="#174ea6", lw=2, marker="o", ms=3, label="複産（双子以上）")
ax.plot(yrs, T["twin_per_1000_deliveries"], color="#7baaf7", lw=1.5, marker="o", ms=2, label="うち双子")
ax.set_ylabel("分娩1,000件あたり"); ax.set_ylim(0, None); ax.legend(frameon=False)
ax.annotate(f"{pk}年 {T.loc[pk,'mult_per_1000_deliveries']:.1f}", (pk, T.loc[pk, "mult_per_1000_deliveries"]), textcoords="offset points", xytext=(-75, 6), fontsize=9)
ax.set_title("双子以上の分娩の割合：2005年の山のあと下がり、2016年からまた上がった")
savefig(fig, "a293_rate.png")

# 図2：三つ子以上
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.bar(yrs, T["複産"] - T["双子"], color="#d93025")
ax.set_ylabel("分娩件数（件）"); ax.set_title("三つ子以上の分娩件数（1995〜2025年）")
savefig(fig, "a293_triplets.png")

# 図3：実際の複産の出生の割合と、母の年齢構成だけで見込める割合
fig, ax = plt.subplots(figsize=(8, 4.0))
ax.plot(yrs, cmp["actual_pct"], color="#202124", lw=2, marker="o", ms=3, label="実際（出生に占める複産の子の割合）")
ax.plot(yrs, cmp["age_only_expected_pct"], color="#f29900", lw=1.5, ls="--", marker="s", ms=3, label="母の年齢構成だけで見込める割合\n（年齢別の割合は2025年の値で固定）")
ax.set_ylabel("出生に占める割合（%）"); ax.set_ylim(0, None); ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.set_title("2016年からの上がり方は、母の年齢構成の変化だけでは説明できない")
savefig(fig, "a293_age_expected.png")
print(T[["総数", "複産", "双子", "multiple_births", "mult_per_1000_deliveries", "triplet_plus_per_10000_deliveries", "mult_birth_share_pct"]].round(2).to_string())
print(cmp.round(3).to_string()); print(rate25.round(4).to_dict())
