"""367：1つの世帯の人数は、100年でどう減ったのか。
国勢調査 時系列データ「世帯人員の人数別一般世帯数－全国」（一般世帯1960・1970〜2020年、参考：普通世帯1920年〜）。
"""
import json
import numpy as np, pandas as pd, openpyxl
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SRC = "出典：総務省統計局「国勢調査」時系列データ（世帯 第2表 世帯人員の人数別一般世帯数－全国）をもとに作成者が加工して作成"
ws = openpyxl.load_workbook(DATA / "raw" / "kokusei_000001086172.xlsx", data_only=True).worksheets[0]
rows = [[("" if v is None else v) for v in r] for r in ws.iter_rows(values_only=True)]
ih = next(i for i, r in enumerate(rows) if str(r[3]).startswith("1960年"))
kinds = rows[ih - 1]; years = rows[ih]
cols = []
kind = None
for j in range(3, len(years)):
    if str(kinds[j]).strip(): kind = "一般世帯" if "一般" in str(kinds[j]) else "普通世帯"
    if str(years[j]).endswith("年"): cols.append((j, kind, int(str(years[j])[:4])))
SIZES = ["1人", "2人", "3人", "4人", "5人", "6人", "7人", "8人", "9人", "10人以上"]
rec = []
for j, kind, y in cols:
    d = {"kind": kind, "year": y}
    for r in rows:
        if r[0] == "世帯数" and r[1] == "総数": d["households"] = float(r[j])
        if r[0] == "世帯数" and r[1] in SIZES: d["n" + r[1].replace("人以上", "").replace("人", "")] = float(r[j]) if isinstance(r[j], (int, float)) else np.nan
        if r[0] == "世帯人員": d["members"] = float(r[j]) if isinstance(r[j], (int, float)) else np.nan
        if str(r[0]).startswith("1世帯当たり"): d["mean_size_published"] = float(r[j]) if isinstance(r[j], (int, float)) else np.nan
    rec.append(d)
T = pd.DataFrame(rec).sort_values(["kind", "year"]).reset_index(drop=True)
N = [f"n{k}" for k in range(1, 11)]
T["sum_check"] = T[N].sum(axis=1) - T.households
T["mean_size"] = T.members / T.households
for k in range(1, 10): T[f"s{k}"] = T[f"n{k}"] / T.households * 100
T["s5plus"] = T[[f"n{k}" for k in range(5, 11)]].sum(axis=1) / T.households * 100
T["s6plus"] = T[[f"n{k}" for k in range(6, 11)]].sum(axis=1) / T.households * 100
T["mode"] = T[[f"n{k}" for k in range(1, 10)]].idxmax(axis=1).str[1:].astype(int)
# 人で数える：k人世帯にいる人の割合（10人以上の世帯の人数は、世帯人員の残りから出す）
for k in range(1, 10): T[f"p{k}"] = k * T[f"n{k}"] / T.members * 100
T["p10"] = 100 - T[[f"p{k}" for k in range(1, 10)]].sum(axis=1)
T["p5plus"] = T[[f"p{k}" for k in range(5, 10)]].sum(axis=1) + T.p10
T["mean_size_10plus"] = (T.members - sum(k * T[f"n{k}"] for k in range(1, 10))) / T.n10
T.to_csv(DATA / "household_size_1920_2020.csv", index=False)

G = T[T.kind == "一般世帯"].set_index("year"); F = T[T.kind == "普通世帯"].set_index("year")
# つないだ系列：1955年までは普通世帯、1960年からは一般世帯
M = pd.concat([F[F.index <= 1955], G]).sort_index()
def first_below(S, col, v): 
    s = S[S[col] < v]; return int(s.index.min()) if len(s) else None
def first_above(S, col, v):
    s = S[S[col] > v]; return int(s.index.min()) if len(s) else None
a, b = G.loc[1960], G.loc[2020]
lh = np.log(b.households / a.households); lp = np.log(b.members / a.members); ls = -np.log(b.mean_size / a.mean_size)
res = {"columns": [(k, y) for _, k, y in cols], "sum_check_max_abs": float(T.sum_check.abs().max()),
       "mean_published_vs_calc_max_abs": float((T.mean_size - T.mean_size_published).abs().max()),
       "futsu": {int(y): {"mean": round(float(r.mean_size), 3), "s1": round(float(r.s1), 2), "s2": round(float(r.s2), 2), "s5plus": round(float(r.s5plus), 2), "mode": int(r["mode"])} for y, r in F.iterrows()},
       "ippan": {int(y): {"mean": round(float(r.mean_size), 3), "s1": round(float(r.s1), 2), "s2": round(float(r.s2), 2), "s3": round(float(r.s3), 2), "s4": round(float(r.s4), 2), "s5plus": round(float(r.s5plus), 2),
                          "mode": int(r["mode"]), "p1": round(float(r.p1), 2), "p2": round(float(r.p2), 2), "p5plus": round(float(r.p5plus), 2), "households_man": round(float(r.households) / 1e4, 1)} for y, r in G.iterrows()},
       "ippan_mean_below_4": first_below(G, "mean_size", 4), "ippan_mean_below_3": first_below(G, "mean_size", 3), "ippan_mean_below_2_5": first_below(G, "mean_size", 2.5),
       "futsu_mean_below_4": first_below(F, "mean_size", 4), "futsu_mean_below_3": first_below(F, "mean_size", 3),
       "ippan_one_person_modal_from": int(G[G["mode"] == 1].index.min()), "futsu_one_person_modal_from": (int(F[F["mode"] == 1].index.min()) if (F["mode"] == 1).any() else None),
       "ippan_s1_over_30": first_above(G, "s1", 30), "ippan_s5plus_below_10": first_below(G, "s5plus", 10),
       "ippan_s12_over_50": int(G[(G.s1 + G.s2) > 50].index.min()),
       "ippan_4person_peak": {"year": int(G.s4.idxmax()), "share": round(float(G.s4.max()), 1), "n_man": round(float(G.n4.max()) / 1e4, 0), "n_peak_year": int(G.n4.idxmax())},
       "futsu_5plus_1920": round(float(F.loc[1920].s5plus), 1), "futsu_5plus_1955": round(float(F.loc[1955].s5plus), 1),
       "decomp_1960_2020": {"households_ratio": round(float(b.households / a.households), 3), "members_ratio": round(float(b.members / a.members), 3), "size_ratio": round(float(b.mean_size / a.mean_size), 3),
                            "share_population": round(float(lp / lh) * 100, 1), "share_smaller_size": round(float(ls / lh) * 100, 1),
                            "households_if_size_1960_man": round(float(b.members / a.mean_size) / 1e4, 0), "households_2020_man": round(float(b.households) / 1e4, 0)},
       "decomp_2000_2020": {"households_ratio": round(float(b.households / G.loc[2000].households), 3), "members_ratio": round(float(b.members / G.loc[2000].members), 3)},
       "overlap_1960": {"ippan_mean": round(float(a.mean_size), 2), "futsu_mean": round(float(F.loc[1960].mean_size), 2), "ippan_s1": round(float(a.s1), 1), "futsu_s1": round(float(F.loc[1960].s1), 1)},
       "overlap_last": {"year": int(F.index.max()), "ippan_mean": round(float(G.loc[F.index.max()].mean_size), 2), "futsu_mean": round(float(F.loc[F.index.max()].mean_size), 2)},
       "people_alone_2020": round(float(b.p1), 1), "people_alone_1960": round(float(a.p1), 1), "people_in_3_4_2020": round(float(b.p3 + b.p4), 1), "people_in_5plus_1960": round(float(a.p5plus), 1), "people_in_5plus_2020": round(float(b.p5plus), 1),
       "people_modal": {int(y): int(max(range(1, 10), key=lambda k: r[f"p{k}"])) for y, r in G.iterrows()}}
json.dump(res, open(RES / "a367_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：1世帯当たり人員
fig, ax = plt.subplots(figsize=(8.6, 4.3))
ax.plot(F.index, F.mean_size, color=GRAY, lw=1.6, marker="o", ms=4, label="普通世帯（間借り・下宿のひとり暮らしなどを含まない）")
ax.plot(G.index, G.mean_size, color=BLUE, lw=2.2, marker="o", ms=4.5, label="一般世帯（いまの数え方）")
for y in [1920, 1955]: ax.annotate(f"{F.loc[y].mean_size:.2f}人", (y, F.loc[y].mean_size), xytext=(0, 8), textcoords="offset points", ha="center", fontsize=9, color=INK)
for y in [1960, 1970, 1990, 2020]: ax.annotate(f"{G.loc[y].mean_size:.2f}人", (y, G.loc[y].mean_size), xytext=(0, -15), textcoords="offset points", ha="center", fontsize=9, color=BLUE)
ax.axhline(4, color=GRAY, lw=0.6, ls=":"); ax.axhline(3, color=GRAY, lw=0.6, ls=":")
ax.set_ylim(1.5, 5.6); ax.set_ylabel("1世帯当たりの人数（人）"); ax.set_title("1世帯の人数は、1955年まで5人。そこから65年で2.2人になった")
ax.legend(frameon=False, loc="lower left", fontsize=9)
save(fig, "a367_mean_size.png", SRC + "\n1945年は調査なし。1940年は人数別の集計がないため、点は1920・1930・1950年〜")

# 図2：人数別の世帯の割合
fig, ax = plt.subplots(figsize=(9.2, 4.5))
ys = list(M.index); x = np.arange(len(ys)); bot = np.zeros(len(ys))
parts = [("1人", M.s1, BLUE), ("2人", M.s2, LIGHT), ("3人", M.s3, GREEN), ("4人", M.s4, "#f2c14e"), ("5人", M.s5, ORANGE), ("6人以上", M.s6plus, GRAY)]
for lab, v, c in parts:
    ax.bar(x, v.values, bottom=bot, color=c, width=0.78, label=lab)
    for i, (vv, bb) in enumerate(zip(v.values, bot)):
        if vv >= 9: ax.text(i, bb + vv / 2, f"{vv:.0f}", ha="center", va="center", fontsize=7.5, color="white" if c in (BLUE, ORANGE, GRAY, GREEN) else INK)
    bot += v.values
ax.set_xticks(x); ax.set_xticklabels([str(y) for y in ys], fontsize=8.5)
nf = sum(1 for y in ys if y <= 1955); ax.axvline(nf - 0.5, color=INK, lw=0.8, ls="--")
ax.text(nf - 0.6, 103, "普通世帯", ha="right", fontsize=8.5); ax.text(nf - 0.4, 103, "一般世帯", ha="left", fontsize=8.5)
ax.set_ylim(0, 108); ax.set_ylabel("世帯の割合（%）"); ax.set_title("5人以上の世帯は半分から5%に。4人世帯がいちばん多かったのは1970〜85年", pad=14)
ax.legend(frameon=False, ncol=6, loc="upper center", bbox_to_anchor=(0.5, -0.08), fontsize=9)
save(fig, "a367_size_shares.png", SRC, y=-0.06)

# 図3：人で数えた割合（一般世帯）
fig, ax = plt.subplots(figsize=(8.6, 4.3))
ax.plot(G.index, G.p1, color=BLUE, lw=2.2, marker="o", ms=4, label="ひとり暮らしの人")
ax.plot(G.index, G.p2, color=LIGHT, lw=2.2, marker="o", ms=4, label="2人世帯の人")
ax.plot(G.index, G.p3 + G.p4, color=GREEN, lw=2.2, marker="o", ms=4, label="3〜4人世帯の人")
ax.plot(G.index, G.p5plus, color=ORANGE, lw=2.2, marker="o", ms=4, label="5人以上の世帯の人")
for col, v in [(BLUE, G.p1), (LIGHT, G.p2), (GREEN, G.p3 + G.p4), (ORANGE, G.p5plus)]:
    ax.annotate(f"{v.loc[2020]:.0f}%", (2020, v.loc[2020]), xytext=(6, -3), textcoords="offset points", fontsize=9, color=INK)
    ax.annotate(f"{v.loc[1960]:.0f}%", (1960, v.loc[1960]), xytext=(-6, -3), textcoords="offset points", fontsize=9, color=INK, ha="right")
ax.set_xlim(1953, 2027); ax.set_ylim(0, 70); ax.set_ylabel("一般世帯で暮らす人に占める割合（%）")
ax.set_title("人で数えると、2020年でも一番多いのは3〜4人世帯で暮らす人")
ax.legend(frameon=False, fontsize=9, loc="upper center", ncol=2)
save(fig, "a367_people_shares.png", SRC + "\n10人以上の世帯の人数は、世帯人員の合計から9人以下の世帯の人数を引いて求めた")
print(json.dumps(res, ensure_ascii=False)[:6000])
