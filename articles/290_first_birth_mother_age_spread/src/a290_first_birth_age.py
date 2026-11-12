"""290 第1子を産む母の年齢は、平均だけでなく、ばらつきも広がったのか
人口動態統計 確定数 上巻 4-17（出生順位×母の年齢5歳階級×年次）と 4-19（出生順位別 母の平均年齢）
"""
import numpy as np, pandas as pd
from common import rows, num, save_json, savefig, plt, RES

r = rows("jinkou_r7_jokan_4-17_births_order_mother_age.csv")
hdr = next(x for x in r if x and x[0] == "" and len(x) > 5 and x[1][:4].isdigit())
years = [int(v[:4]) for v in hdr[1:] if v[:4].isdigit()]
AG = ["19歳以下", "20～24歳", "25～29歳", "30～34歳", "35～39歳", "40～44歳", "45歳以上"]
EDGE = [15, 20, 25, 30, 35, 40, 45, 50]   # 階級の端（19歳以下は15〜20、45歳以上は45〜50と置く）
blocks, cur = {}, None
for x in r:
    if not x or not x[0]: continue
    k = x[0].replace(" ", "")
    if k in ("総数", "第１子", "第２子", "第３子以上") and all(v in ("", " ") for v in x[1:3]):
        cur = {"総数": "all", "第１子": "1", "第２子": "2", "第３子以上": "3+"}[k]; blocks[cur] = {}; continue
    if cur and k in AG + ["総数"]:
        blocks[cur][k] = [num(v) for v in x[1:1 + len(years)]]
# 最初の「総数」ブロックは見出し行が「総 数」で始まる
D = {o: pd.DataFrame({a: blocks[o][a] for a in AG}, index=years) for o in blocks}
for o in D:
    assert (D[o].sum(axis=1) - pd.Series(blocks[o]["総数"], index=years)).abs().max() == 0, o


def stats(row):
    n = row.values.astype(float); p = n / n.sum(); cum = np.concatenate([[0], np.cumsum(p)])
    q = lambda t: float(np.interp(t, cum, EDGE))
    mid = np.array([(a + b) / 2 for a, b in zip(EDGE[:-1], EDGE[1:])])
    mean = float((p * mid).sum()); sd = float(np.sqrt((p * (mid - mean) ** 2).sum() + 25 / 12))  # 階級内の一様分布の分を足す
    return dict(mean_mid=mean, sd=sd, p10=q(.1), p25=q(.25), p50=q(.5), p75=q(.75), p90=q(.9),
                share35=float(p[4:].sum() * 100), share40=float(p[5:].sum() * 100), share_u25=float(p[:2].sum() * 100))

S = {o: pd.DataFrame({y: stats(D[o].loc[y]) for y in years}).T for o in D}
for o in S:
    S[o]["iqr"] = S[o]["p75"] - S[o]["p25"]; S[o]["p90_p10"] = S[o]["p90"] - S[o]["p10"]
    S[o].round(3).to_csv(RES / f"a290_stats_order{o.replace('+', 'plus')}.csv")
shares1 = (D["1"].div(D["1"].sum(axis=1), axis=0) * 100).round(3); shares1.to_csv(RES / "a290_first_birth_age_share.csv")

# 公表の平均年齢（4-19）との突き合わせ
r2 = rows("jinkou_r7_jokan_4-19_mother_mean_age.csv")
off = {int(x[0][:4]): [num(v) for v in x[1:5]] for x in r2 if x and x[0][:4].isdigit() and len(x) >= 5}
off = pd.DataFrame(off, index=["all", "1", "2", "3"]).T
chk = pd.DataFrame({"official_first": off.loc[years, "1"], "mid_first": S["1"]["mean_mid"]})
chk["diff"] = chk["mid_first"] - chk["official_first"]
chk.round(3).to_csv(RES / "a290_mean_check.csv")

f = S["1"]
out = dict(
    years=years, official_mean_first={y: off.loc[y, "1"] for y in (1950, 1970, 1975, 1985, 2000, 2010, 2015, 2025)},
    mean_check_max_abs_diff=float(chk["diff"].abs().max()),
    first={y: {k: float(f.loc[y, k]) for k in ["p10", "p25", "p50", "p75", "p90", "iqr", "p90_p10", "sd", "share35", "share40", "share_u25"]} for y in years},
    all_births={y: {k: float(S["all"].loc[y, k]) for k in ["p50", "iqr", "p90_p10", "sd", "share35"]} for y in (1975, 2000, 2025)},
    first_births_count={y: float(D["1"].loc[y].sum()) for y in (1975, 2000, 2015, 2025)},
    first_35plus_count={y: float(D["1"].loc[y, ["35～39歳", "40～44歳", "45歳以上"]].sum()) for y in (1975, 2000, 2015, 2025)},
    p10_change_1975_2025=float(f.loc[2025, "p10"] - f.loc[1975, "p10"]), p90_change_1975_2025=float(f.loc[2025, "p90"] - f.loc[1975, "p90"]),
    iqr_peak_year=int(f["iqr"].idxmax()), sd_peak_year=int(f["sd"].idxmax()),
)
save_json(out)

# 図1：第1子の母の年齢の分布（年齢階級の割合）
fig, ax = plt.subplots(figsize=(8, 4.2))
cols = {1975: "#9aa0a6", 1995: "#7baaf7", 2010: "#1a73e8", 2025: "#d93025"}
w = 0.2
for i, (y, c) in enumerate(cols.items()):
    ax.bar(np.arange(7) + (i - 1.5) * w, shares1.loc[y], width=w, color=c, label=f"{y}年")
ax.set_xticks(range(7)); ax.set_xticklabels(["〜19歳", "20〜24", "25〜29", "30〜34", "35〜39", "40〜44", "45歳〜"])
ax.set_ylabel("第1子の出生に占める割合（%）"); ax.legend(frameon=False)
ax.set_title("第1子を産む母の年齢：25〜29歳の山が低くなり、30代に広がった")
savefig(fig, "a290_distribution.png")

# 図2：10・25・50・75・90%点の推移
fig, ax = plt.subplots(figsize=(8, 4.3))
ax.fill_between(years, f["p10"], f["p90"], color="#d2e3fc", label="10%点〜90%点")
ax.fill_between(years, f["p25"], f["p75"], color="#7baaf7", label="25%点〜75%点")
ax.plot(years, f["p50"], color="#174ea6", lw=2, marker="o", ms=3, label="中央値")
ax.plot(off.index[off.index >= 1950], off.loc[off.index >= 1950, "1"], color="#d93025", lw=1.2, ls="--", label="公表の平均年齢")
ax.set_ylabel("母の年齢（歳）"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("第1子を産む年齢：幅は2014年まで広がり、その後は下の端だけが上がった")
savefig(fig, "a290_quantiles.png")

# 図3：幅（90%点−10%点）と35歳以上の割合
fig, ax1 = plt.subplots(figsize=(8, 3.9))
ax1.plot(years, f["p90_p10"], color="#1a73e8", marker="o", ms=3, lw=2, label="90%点−10%点（歳、左）")
ax1.set_ylabel("年齢の幅（歳）", color="#1a73e8"); ax1.set_ylim(0, None)
ax2 = ax1.twinx(); ax2.plot(years, f["share35"], color="#d93025", marker="s", ms=3, lw=2, label="35歳以上の割合（%、右）")
ax2.set_ylabel("35歳以上の割合（%）", color="#d93025"); ax2.set_ylim(0, None)
h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9, loc="upper left")
ax1.set_title("第1子の母：年齢の幅と35歳以上の割合")
savefig(fig, "a290_width.png")
print(f[["p10", "p25", "p50", "p75", "p90", "iqr", "p90_p10", "sd", "share35", "share40", "share_u25"]].round(2).to_string())
print(chk.round(2).T.to_string())
