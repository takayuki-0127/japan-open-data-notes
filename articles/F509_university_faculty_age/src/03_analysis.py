"""主な分析：平均年齢・年齢区分の割合・職名別の平均年齢・シフトシェア分解・設置者別・仮説の判定・頑健性。
結果は results/main.json・by_year.csv・by_position.csv・by_setter.csv・robustness.csv に出す。"""
import json
import pandas as pd
from common import ROOT, load, harmonized, mean_age, share, POS_ORDER

R = ROOT / "results"
R.mkdir(exist_ok=True)
d = load()
off = pd.read_csv(ROOT / "data" / "official_mean_age.csv")
ts = pd.read_csv(ROOT / "data" / "ts_mean_age.csv")
YEARS = sorted(d.year.unique())


def r(x, k=2):
    return round(float(x), k)


# ---- 年度×設置者の要約 ---------------------------------------------------------------------
rows = []
for (s, y), g in d[d.position == "計"].groupby(["setter", "year"], sort=True):
    o = off[(off.year == y) & (off.setter == s) & (off.position == "計")].official_mean_age
    rows.append({"setter": s, "year": y, "n": int(g.n.sum()), "mean_age": r(mean_age(g)),
                 "official_mean_age": r(o.iloc[0], 1) if len(o) else None,
                 "share_u35": r(100 * share(g, hi=35)), "share_u40": r(100 * share(g, hi=40)),
                 "share_u45": r(100 * share(g, hi=45)), "share_40_59": r(100 * share(g, 40, 60)),
                 "share_60p": r(100 * share(g, lo=60)), "share_65p": r(100 * share(g, lo=65)),
                 "n_u40": int(g[g.age < 40].n.sum())})
by = pd.DataFrame(rows)
order = {"計": 0, "国立": 1, "公立": 2, "私立": 3}
by = by.sort_values(["setter", "year"], key=lambda c: c.map(order) if c.name == "setter" else c).reset_index(drop=True)
by.to_csv(R / "by_setter.csv", index=False)
tot = by[by.setter == "計"].set_index("year")
tot.to_csv(R / "by_year.csv")

# ---- 職名別（まとめた職名） -----------------------------------------------------------------
h = harmonized(d)
prow = []
for (p, y), g in h.groupby(["pos", "year"], sort=True):
    prow.append({"pos": p, "year": y, "n": int(g.n.sum()), "mean_age": r(mean_age(g)),
                 "share_u40": r(100 * share(g, hi=40)), "share_60p": r(100 * share(g, lo=60))})
bp = pd.DataFrame(prow)
bp["pos"] = pd.Categorical(bp.pos, POS_ORDER, ordered=True)
bp = bp.sort_values(["pos", "year"]).reset_index(drop=True)
bp["share_of_all"] = bp.apply(lambda q: r(100 * q.n / tot.loc[q.year, "n"]), axis=1)
bp.to_csv(R / "by_position.csv", index=False)


# ---- シフトシェア分解 -------------------------------------------------------------------------
def shift_share(h, y0, y1, top=71, positions=None):
    """平均年齢の差 = Σ s̄Δm（職名内）+ Σ m̄Δs（構成）。s は職名の割合、m は職名の平均年齢。"""
    out = {}
    for y in (y0, y1):
        g = h[h.year == y]
        if positions is not None:
            g = g[g.pos.isin(positions)]
        n = g.groupby("pos").n.sum()
        m = g.groupby("pos").apply(lambda q: mean_age(q, top=top), include_groups=False)
        out[y] = (n / n.sum(), m, mean_age(g, top=top))
    s0, m0, a0 = out[y0]
    s1, m1, a1 = out[y1]
    within = float(((s0 + s1) / 2 * (m1 - m0)).sum())
    comp = float(((m0 + m1) / 2 * (s1 - s0)).sum())
    return {"y0": int(y0), "y1": int(y1), "mean0": r(a0), "mean1": r(a1), "change": r(a1 - a0),
            "within": r(within), "composition": r(comp), "within_share_pct": r(100 * within / (a1 - a0), 1)}


ss = shift_share(h, 1998, 2025)
ss_2007 = shift_share(h, 2007, 2025)

# ---- 設置者 ---------------------------------------------------------------------------------
st = by.set_index(["setter", "year"])
gap25 = st.loc[("私立", 2025), "mean_age"] - st.loc[("国立", 2025), "mean_age"]
gap98 = st.loc[("私立", 1998), "mean_age"] - st.loc[("国立", 1998), "mean_age"]
off_gap25 = float(off[(off.year == 2025) & (off.setter == "私立") & (off.position == "計")].official_mean_age.iloc[0]
                  - off[(off.year == 2025) & (off.setter == "国立") & (off.position == "計")].official_mean_age.iloc[0])

# ---- 仮説 ------------------------------------------------------------------------------------
u98, u25 = tot.loc[1998, "share_u40"], tot.loc[2025, "share_u40"]
p98, p25 = tot.loc[1998, "share_60p"], tot.loc[2025, "share_60p"]
hyp = {
    "H1": {"u40_1998": u98, "u40_2025": u25, "verdict": "支持" if (u25 < u98 and u25 < 30) else "外れ"},
    "H2": {"within_share_pct": ss["within_share_pct"], "verdict": "支持" if ss["within_share_pct"] >= 50 else "外れ"},
    "H3": {"p60_1998": p98, "p60_2025": p25, "diff_pt": r(p25 - p98),
           "verdict": "支持" if p25 - p98 >= 5 else "外れ"},
    "H4": {"private_2025": st.loc[("私立", 2025), "mean_age"], "national_2025": st.loc[("国立", 2025), "mean_age"],
           "gap_2025": r(gap25), "gap_1998": r(gap98), "official_gap_2025": r(off_gap25, 1),
           "verdict": "支持" if gap25 >= 2 else "外れ"},
}

# ---- 頑健性 -----------------------------------------------------------------------------------
rob = []


def add(name, y0, y1, hh=h, top=71, positions=None, lo_hi=(None, 40)):
    s_ = shift_share(hh, y0, y1, top=top, positions=positions)
    g0 = hh[hh.year == y0]; g1 = hh[hh.year == y1]
    if positions is not None:
        g0 = g0[g0.pos.isin(positions)]; g1 = g1[g1.pos.isin(positions)]
    rob.append({"check": name, "period": f"{y0}→{y1}", "mean0": s_["mean0"], "mean1": s_["mean1"],
                "change": s_["change"], "within_share_pct": s_["within_share_pct"],
                "young_share0": r(100 * share(g0, *lo_hi)), "young_share1": r(100 * share(g1, *lo_hi)),
                "young_def": f"{lo_hi[1]}歳未満"})


add("本線（全教員、70歳以上＝71歳）", 1998, 2025)
add("学長・副学長を除く", 1998, 2025, positions=["教授", "准教授", "講師", "助教・助手"])
add("職名の改正後に限る", 2007, 2025)
add("70歳以上＝70歳とみなす", 1998, 2025, top=70)
add("70歳以上＝73歳とみなす", 1998, 2025, top=73)
add("若手の境目＝35歳未満", 1998, 2025, lo_hi=(None, 35))
add("若手の境目＝45歳未満", 1998, 2025, lo_hi=(None, 45))
for s in ["国立", "公立", "私立"]:
    add(f"{s}だけ", 1998, 2025, hh=harmonized(d, s))
o_all = off[(off.setter == "計") & (off.position == "計")].set_index("year").official_mean_age
rob.append({"check": "公表の平均年齢（表の値）", "period": "1998→2025", "mean0": r(o_all[1998], 1), "mean1": r(o_all[2025], 1),
            "change": r(o_all[2025] - o_all[1998], 1), "within_share_pct": None, "young_share0": None, "young_share1": None,
            "young_def": "—"})
rb = pd.DataFrame(rob)
rb.to_csv(R / "robustness.csv", index=False)

main = {
    "years": [int(y) for y in YEARS],
    "total_n": {int(k): int(v) for k, v in tot.n.items()},
    "mean_age_computed": {int(k): float(v) for k, v in tot.mean_age.items()},
    "mean_age_official": {int(k): round(float(v), 1) for k, v in o_all.items()},
    "official_minus_computed_mean": r((o_all - tot.mean_age).mean()),
    "ts_mean_age_1977": float(ts.set_index("year").loc[1977, "mean_all"]),
    "ts_mean_age_2025": float(ts.set_index("year").loc[2025, "mean_all"]),
    "share_u40": {int(k): float(v) for k, v in tot.share_u40.items()},
    "share_60p": {int(k): float(v) for k, v in tot.share_60p.items()},
    "share_65p": {int(k): float(v) for k, v in tot.share_65p.items()},
    "share_40_59": {int(k): float(v) for k, v in tot.share_40_59.items()},
    "n_u40": {int(k): int(v) for k, v in tot.n_u40.items()},
    "position_mean_1998": {p: float(bp[(bp.pos == p) & (bp.year == 1998)].mean_age.iloc[0]) for p in POS_ORDER},
    "position_mean_2025": {p: float(bp[(bp.pos == p) & (bp.year == 2025)].mean_age.iloc[0]) for p in POS_ORDER},
    "position_share_1998": {p: float(bp[(bp.pos == p) & (bp.year == 1998)].share_of_all.iloc[0]) for p in POS_ORDER},
    "position_share_2025": {p: float(bp[(bp.pos == p) & (bp.year == 2025)].share_of_all.iloc[0]) for p in POS_ORDER},
    "shift_share_1998_2025": ss,
    "shift_share_2007_2025": ss_2007,
    "setter_2025": {s: {"mean_age": float(st.loc[(s, 2025), "mean_age"]), "share_u40": float(st.loc[(s, 2025), "share_u40"]),
                        "share_60p": float(st.loc[(s, 2025), "share_60p"])} for s in ["国立", "公立", "私立"]},
    "setter_1998": {s: {"mean_age": float(st.loc[(s, 1998), "mean_age"]), "share_u40": float(st.loc[(s, 1998), "share_u40"]),
                        "share_60p": float(st.loc[(s, 1998), "share_60p"])} for s in ["国立", "公立", "私立"]},
    "hypotheses": hyp,
    "note": "平均年齢は各歳の人数から計算（25歳未満＝24歳、70歳以上＝71歳）。公表の平均年齢は約0.5歳高い（年齢の数え方の違いと思われる）。",
}
(R / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")
