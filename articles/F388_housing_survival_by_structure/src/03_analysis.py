"""03 分析：同じ建築時期の住宅が5年後にどれだけ残るか（残る割合）から、住宅の生命表を作る。
国交省の「滅失住宅の平均築後年数」と同じ考え方の数字も出して並べる。オフライン。"""
import json, pathlib
import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
RES = BASE / "results"
RES.mkdir(exist_ok=True)

COHORTS = [(1900, 1950), (1951, 1970), (1971, 1980), (1981, 1990), (1991, 2000),
           (2001, 2005), (2006, 2010), (2011, 2015)]
OLD_MID = 1940.0          # 1950年以前の住宅の建築年の真ん中（仮定）
SURVEYS = [1998, 2003, 2008, 2013, 2018, 2023]
STRUCTS = ["total", "wood", "nonwood"]
GRID = np.round(np.arange(0, 200.0001, 0.05), 4)
TAIL_AGE = 80.0           # これより先のハザードは築80年の値で一定

def mid_year(s, e):
    return OLD_MID if s == 1900 else (s + e + 1) / 2.0

def cohort_table(stock, adjust_unknown=False):
    recs = []
    for (st, y), g in stock.groupby(["structure", "year"], sort=True):
        known = g[g.start > 0]
        unk = g.loc[g.start < 0, "dwellings"].sum()
        factor = (known.dwellings.sum() + unk) / known.dwellings.sum() if adjust_unknown else 1.0
        for s, e in COHORTS:
            part = known[(known.start >= s) & (known.end <= e)]
            span = int((part.end - part.start + 1).sum())
            if span != e - s + 1 or e >= y:
                continue
            recs.append(dict(structure=st, year=y, c_start=s, c_end=e,
                             dwellings=float(part.dwellings.sum()) * factor,
                             age=y + 0.75 - mid_year(s, e)))
    return pd.DataFrame(recs)

def survival(ct):
    a = ct.rename(columns={"dwellings": "n0", "age": "age0"})
    b = ct.rename(columns={"dwellings": "n1", "age": "age1"}).copy()
    b["year"] = b["year"] - 5
    m = a.merge(b[["structure", "year", "c_start", "c_end", "n1"]], on=["structure", "year", "c_start", "c_end"])
    m = m.rename(columns={"year": "y0"})
    m["y1"] = m["y0"] + 5
    m["ratio"] = m["n1"] / m["n0"]
    m["hazard"] = -np.log(m["ratio"]) / 5.0
    m["age_mid"] = m["age0"] + 2.5
    m["lost"] = m["n0"] - m["n1"]
    return m.sort_values(["structure", "y0", "c_start"], kind="mergesort").reset_index(drop=True)

def life_table(sv, structure, y0, clip=True, step=False):
    g = sv[(sv.structure == structure) & (sv.y0 == y0)].sort_values("age_mid")
    ages, h = g["age_mid"].to_numpy(), g["hazard"].to_numpy()
    if clip:
        h = np.maximum(h, 0.0)
    if step:
        # 区間で一定：各点の値を、隣の点との真ん中まで使う
        edges = np.concatenate([[-np.inf], (ages[1:] + ages[:-1]) / 2, [np.inf]])
        idx = np.searchsorted(edges, np.minimum(GRID, TAIL_AGE), side="right") - 1
        hz = h[np.clip(idx, 0, len(h) - 1)]
    else:
        hz = np.interp(np.minimum(GRID, TAIL_AGE), ages, h)
    dx = GRID[1] - GRID[0]
    cum = np.concatenate([[0.0], np.cumsum((hz[1:] + hz[:-1]) / 2 * dx)])
    S = np.exp(-cum)
    below = np.where(S <= 0.5)[0]
    median = float(GRID[below[0]]) if len(below) else None   # 築200年までに半分を下回らない
    mean = float(np.sum((S[1:] + S[:-1]) / 2 * dx))
    s30 = float(np.interp(30, GRID, S))
    s50 = float(np.interp(50, GRID, S))
    return dict(structure=structure, y0=int(y0), y1=int(y0) + 5, median=(round(median, 2) if median is not None else None),
                mean=round(mean, 2), surv30=round(s30, 4), surv50=round(s50, 4)), S

def pooled(sv):
    """5つの期間をまとめる：築年数10年ごとの帯で、5年前の数と5年後の数をそれぞれ足してから残る割合を出す。"""
    p = sv.copy()
    p["band"] = np.minimum((p["age_mid"] // 10) * 10, 70)
    g = p.groupby(["structure", "band"], sort=True).agg(n0=("n0", "sum"), n1=("n1", "sum"),
                                                        age_mid=("age_mid", "mean")).reset_index()
    g["ratio"] = g["n1"] / g["n0"]
    g["hazard"] = -np.log(g["ratio"]) / 5.0
    g["y0"] = 0
    return g

def hazard_fn(sv, structure, y0):
    g = sv[(sv.structure == structure) & (sv.y0 == y0)].sort_values("age_mid")
    return lambda a: np.interp(np.minimum(a, TAIL_AGE), g["age_mid"].to_numpy(), np.maximum(g["hazard"].to_numpy(), 0))

def counterfactual(sv, structure):
    """問い直し：stock（建築時期の構成）を期間Aのもの、消え方（ハザード）を期間Bのものにしたときの
    「なくなった住宅の平均築年数」。"""
    rows = []
    for ya in SURVEYS[:-1]:
        g = sv[(sv.structure == structure) & (sv.y0 == ya)]
        for yb in SURVEYS[:-1]:
            h = hazard_fn(sv, structure, yb)(g["age_mid"].to_numpy())
            lost = g["n0"].to_numpy() * (1 - np.exp(-5 * h))
            rows.append(dict(structure=structure, stock_period=f"{ya}-{ya+5}", hazard_period=f"{yb}-{yb+5}",
                             mean_age_lost=round(float((lost * g["age_mid"].to_numpy()).sum() / lost.sum()), 2)))
    return rows

def mean_age_lost(sv, structure, y0, use_end_age=False):
    g = sv[(sv.structure == structure) & (sv.y0 == y0)]
    lost = g["lost"].clip(lower=0)
    age = g["age0"] + 5 if use_end_age else g["age_mid"]
    return float((lost * age).sum() / lost.sum()), float(lost.sum())

def main():
    stock = pd.read_csv(BASE / "data" / "stock_by_period.csv")
    ct = cohort_table(stock)
    sv = survival(ct)
    sv_adj = survival(cohort_table(stock, adjust_unknown=True))
    out = sv.copy()
    for c in ["n0", "n1", "lost"]:
        out[c] = out[c].round(0).astype("int64")
    for c in ["ratio", "hazard"]:
        out[c] = out[c].round(5)
    for c in ["age0", "age_mid"]:
        out[c] = out[c].round(2)
    out[["structure", "y0", "y1", "c_start", "c_end", "age0", "age_mid", "n0", "n1", "lost", "ratio", "hazard"]] \
        .to_csv(RES / "cohort_survival.csv", index=False, lineterminator="\n")

    # 生命表（期間ごと・構造ごと）と、なくなった住宅の平均築年数
    lt_rows, curves = [], {}
    for st in STRUCTS:
        for y0 in SURVEYS[:-1]:
            r, S = life_table(sv, st, y0)
            ma, lost = mean_age_lost(sv, st, y0)
            r["mean_age_lost"] = round(ma, 2)
            r["lost_total"] = int(round(lost))
            r["n_points"] = int(((sv.structure == st) & (sv.y0 == y0)).sum())
            r2, _ = life_table(sv_adj, st, y0)
            r["median_unknown_realloc"] = r2["median"]
            r["mean_unknown_realloc"] = r2["mean"]
            r["mean_age_lost_unknown_realloc"] = round(mean_age_lost(sv_adj, st, y0)[0], 2)
            lt_rows.append(r)
            curves[(st, y0)] = S
    pl = pooled(sv)
    pl_adj = pooled(sv_adj)
    for st in STRUCTS:
        r, S = life_table(pl, st, 0)
        r2, _ = life_table(pl_adj, st, 0)
        r.update(y0=1998, y1=2023, mean_age_lost=round(mean_age_lost(sv[sv.y0 >= 0].assign(y0=0), st, 0)[0], 2),
                 lost_total=None, n_points=int((pl.structure == st).sum()),
                 median_unknown_realloc=r2["median"], mean_unknown_realloc=r2["mean"],
                 mean_age_lost_unknown_realloc=round(mean_age_lost(sv_adj.assign(y0=0), st, 0)[0], 2))
        lt_rows.append(r)
        curves[(st, "pooled")] = S
    lt = pd.DataFrame(lt_rows)
    pl.assign(n0=pl.n0.round(0).astype("int64"), n1=pl.n1.round(0).astype("int64"),
              ratio=pl.ratio.round(5), hazard=pl.hazard.round(5), age_mid=pl.age_mid.round(2)) \
      .drop(columns="y0").to_csv(RES / "pooled_bands.csv", index=False, lineterminator="\n")
    cf = pd.DataFrame(sum([counterfactual(sv, st) for st in STRUCTS], []))
    cf.to_csv(RES / "requestion_counterfactual.csv", index=False, lineterminator="\n")
    lt.to_csv(RES / "life_table_summary.csv", index=False, lineterminator="\n")
    cv = pd.DataFrame({"age": GRID[GRID <= 100]})
    for st in STRUCTS:
        cv[f"{st}_2018_2023"] = np.round(curves[(st, 2018)][GRID <= 100], 5)
        cv[f"{st}_2013_2018"] = np.round(curves[(st, 2013)][GRID <= 100], 5)
        cv[f"{st}_pooled"] = np.round(curves[(st, "pooled")][GRID <= 100], 5)
    cv = cv[np.isclose(cv.age % 1, 0)].reset_index(drop=True)
    cv.to_csv(RES / "survival_curves.csv", index=False, lineterminator="\n")

    # H4：同じ築年数での残る割合（1971〜80年の住宅 対 1981〜90年の住宅）
    h4 = []
    for st in STRUCTS:
        for (ya, yb) in [(1998, 2008), (2003, 2013)]:
            a = sv[(sv.structure == st) & (sv.c_start == 1971) & (sv.y0 == ya)].iloc[0]
            b = sv[(sv.structure == st) & (sv.c_start == 1981) & (sv.y0 == yb)].iloc[0]
            h4.append(dict(structure=st, age0=round(float(a.age0), 2), old_period=f"{ya}-{ya+5}",
                           old_ratio=round(float(a.ratio), 4), new_period=f"{yb}-{yb+5}",
                           new_ratio=round(float(b.ratio), 4), diff_pt=round(float(b.ratio - a.ratio) * 100, 2)))
    h4 = pd.DataFrame(h4)
    h4.to_csv(RES / "same_age_comparison.csv", index=False, lineterminator="\n")

    # 頑健性
    rob = []
    def add(name, st, y0, svx, **kw):
        r, _ = life_table(svx, st, y0, **kw)
        ma, _ = mean_age_lost(svx, st, y0)
        rob.append(dict(check=name, structure=st, period=f"{y0}-{y0+5}", median=r["median"],
                        mean=r["mean"], mean_age_lost=round(ma, 2)))
    for st in STRUCTS:
        add("main", st, 2018, sv)
        add("unknown_reallocated", st, 2018, sv_adj)
        add("period_2013_2018", st, 2013, sv)
        add("period_2008_2013", st, 2008, sv)
        add("no_clip_negative_hazard", st, 2018, sv, clip=False)
        add("step_hazard", st, 2018, sv, step=True)
    for st in STRUCTS:
        r, _ = life_table(pooled(sv), st, 0)
        rob.append(dict(check="pooled_1998_2023", structure=st, period="1998-2023", median=r["median"],
                        mean=r["mean"], mean_age_lost=float("nan")))
    for st in STRUCTS:
        ma, _ = mean_age_lost(sv, st, 2008, use_end_age=True)
        rob.append(dict(check="mlit_age_at_end_2008_2013", structure=st, period="2008-2013",
                        median=float("nan"), mean=float("nan"), mean_age_lost=round(ma, 2)))
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False, lineterminator="\n")

    per = lt[lt.n_points < 99]
    PER = [f"{y0}-{y0+5}" for y0 in SURVEYS[:-1]]
    def col(c, pooled_row=False):
        d = {}
        for y0, key in zip(SURVEYS[:-1], PER):
            d[key] = {st: per[(per.structure == st) & (per.y0 == y0) & (per.lost_total.notna())].iloc[0][c] for st in STRUCTS}
        return d
    lt_per = lt[lt.lost_total.notna()]
    lt_pool = lt[lt.lost_total.isna()]
    def tab(c):
        return {f"{y0}-{y0+5}": {st: (None if pd.isna(v := lt_per[(lt_per.structure == st) & (lt_per.y0 == y0)].iloc[0][c]) else float(v))
                                  for st in STRUCTS} for y0 in SURVEYS[:-1]}
    def ptab(c):
        return {st: (None if pd.isna(v := lt_pool[lt_pool.structure == st].iloc[0][c]) else float(v)) for st in STRUCTS}
    m = {
        "source": "総務省「住宅・土地統計調査」1998〜2023年 住宅の種類、構造、建築の時期別住宅数－全国",
        "mlit_reference_mean_age_lost": {"1993-1998": 32.3, "1998-2003": 30.0, "2003-2008": 27.0, "2008-2013": 32.1},
        "mean_age_lost": tab("mean_age_lost"),
        "mean_age_lost_unknown_realloc": tab("mean_age_lost_unknown_realloc"),
        "lost_total": tab("lost_total"),
        "median_life": tab("median"),
        "median_life_unknown_realloc": tab("median_unknown_realloc"),
        "mean_life": tab("mean"),
        "surv30": tab("surv30"),
        "surv50": tab("surv50"),
        "pooled_1998_2023": {"median": ptab("median"), "mean": ptab("mean"), "surv30": ptab("surv30"),
                              "surv50": ptab("surv50"), "median_unknown_realloc": ptab("median_unknown_realloc"),
                              "mean_age_lost": ptab("mean_age_lost")},
        "unknown_period_dwellings": {str(y): int(stock[(stock.structure == "total") & (stock.year == y) & (stock.start < 0)].dwellings.sum()) for y in SURVEYS},
        "total_dwellings": {str(y): int(stock[(stock.structure == "total") & (stock.year == y)].dwellings.sum()) for y in SURVEYS},
        "same_age": h4.to_dict(orient="records"),
        "counterfactual": cf.to_dict(orient="records"),
        "robustness": [{k: (None if isinstance(v, float) and np.isnan(v) else v) for k, v in r.items()} for r in rob.to_dict(orient="records")],
    }
    dec = {}
    for st in STRUCTS:
        c = cf[cf.structure == st].set_index(["stock_period", "hazard_period"])["mean_age_lost"]
        a, b = "1998-2003", "2018-2023"
        stock_eff = 0.5 * ((c[(b, a)] - c[(a, a)]) + (c[(b, b)] - c[(a, b)]))
        haz_eff = 0.5 * ((c[(a, b)] - c[(a, a)]) + (c[(b, b)] - c[(b, a)]))
        dec[st] = {"from": float(c[(a, a)]), "to": float(c[(b, b)]), "change": round(float(c[(b, b)] - c[(a, a)]), 2),
                   "stock_aging_effect": round(float(stock_eff), 2), "hazard_change_effect": round(float(haz_eff), 2)}
    m["requestion_decomposition"] = dec
    med = m["median_life"]["2018-2023"]
    mal = m["mean_age_lost"]["2018-2023"]
    big = lambda v: 1e9 if v is None else v
    m["hypotheses"] = {
        "H1": {"value": m["mean_age_lost"]["2008-2013"]["total"], "ref": 32.1,
               "supported": bool(abs(m["mean_age_lost"]["2008-2013"]["total"] - 32.1) <= 3)},
        "H2": {"median": med["total"], "mean_age_lost": mal["total"], "gap": round(med["total"] - mal["total"], 2),
               "supported": bool(med["total"] - mal["total"] >= 10),
               "gap_by_period": {k: round(m["median_life"][k]["total"] - m["mean_age_lost"][k]["total"], 2) for k in PER}},
        "H3": {"wood": med["wood"], "nonwood": med["nonwood"], "supported": bool(big(med["wood"]) < big(med["nonwood"])),
               "by_period_wood_shorter": {k: bool(big(m["median_life"][k]["wood"]) < big(m["median_life"][k]["nonwood"])) for k in PER}},
        "H4": {"total_diff_pt": [r["diff_pt"] for r in m["same_age"] if r["structure"] == "total"],
               "supported": bool(all(r["diff_pt"] >= 1 for r in m["same_age"] if r["structure"] == "total"))},
    }
    (RES / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: m[k] for k in ["mean_age_lost", "mean_age_lost_unknown_realloc", "median_life", "median_life_unknown_realloc", "pooled_1998_2023", "hypotheses", "requestion_decomposition"]}, ensure_ascii=False))
    print(rob.to_string())
    print(cf[cf.structure == "total"].pivot(index="stock_period", columns="hazard_period", values="mean_age_lost"))

if __name__ == "__main__":
    main()
