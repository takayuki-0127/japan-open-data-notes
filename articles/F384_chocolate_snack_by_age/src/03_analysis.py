"""03 分析（オフライン）：年齢別の伸び（名目・実質・1人あたり）、平均の伸びの分け方（年齢の中／年齢構成）、
菓子類の伸びの品目への分け、頑健性。出力：results/main.json, growth_by_age.csv, shift_share.csv, items_contrib.csv, robustness.csv"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
AGES = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
GROUPS = ["平均"] + AGES
CPI_FOR = {"choco": "cpi_chocolate", "snack": "cpi_potato_chips", "sweets": "cpi_sweets"}


def load():
    s = pd.read_csv(DATA / "sweets.csv")
    w = s.pivot_table(index=["year", "group"], columns="item", values="amount").reset_index()
    w["choco"] = w.chocolate + w.choco_kashi
    h = pd.read_csv(DATA / "households.csv")
    c = pd.read_csv(DATA / "cpi_annual.csv")
    w = w.merge(h, on=["year", "group"]).merge(c, on="year")
    return w.sort_values(["group", "year"]).reset_index(drop=True)


def value(w, item, kind, deflator=None):
    v = w[item].astype(float)
    if kind in ("real", "real_pp"):
        v = v / (w[deflator or CPI_FOR[item]] / 100.0)
    if kind in ("pp", "real_pp"):
        v = v / w.persons
    return v


def growth(w, item, kind, start, end, deflator=None):
    d = w.assign(v=value(w, item, kind, deflator))
    a = d[d.year.isin(start)].groupby("group").v.mean()
    b = d[d.year.isin(end)].groupby("group").v.mean()
    out = pd.DataFrame({"start": a, "end": b}).reindex(GROUPS)
    out["diff"] = out.end - out.start
    out["pct"] = 100 * (out.end / out.start - 1)
    return out


def shift_share(w, item, kind, start, end):
    d = w[w.group != "平均"].assign(v=value(w[w.group != "平均"], item, kind), s=lambda x: x.weight / 10000)
    a = d[d.year.isin(start)].groupby("group")[["v", "s"]].mean().reindex(AGES)
    b = d[d.year.isin(end)].groupby("group")[["v", "s"]].mean().reindex(AGES)
    within = ((a.s + b.s) / 2 * (b.v - a.v)).sum()
    comp = ((a.v + b.v) / 2 * (b.s - a.s)).sum()
    return {"start_wavg": (a.s * a.v).sum(), "end_wavg": (b.s * b.v).sum(), "total": (b.s * b.v).sum() - (a.s * a.v).sum(),
            "within_age": within, "composition": comp, "share_start_60plus": a.s.loc[AGES[4:]].sum(), "share_end_60plus": b.s.loc[AGES[4:]].sum()}


def main():
    w = load()
    S, E = [2005, 2006, 2007], [2023, 2024, 2025]
    rows, main = [], {"period": {"start": "2005-2007平均", "end": "2023-2025平均"}}
    for item in ["choco", "snack", "sweets"]:
        for kind in ["nominal", "real", "pp", "real_pp"]:
            g = growth(w, item, kind, S, E)
            for grp, r in g.iterrows():
                rows.append({"item": item, "kind": kind, "group": grp, **{k: round(float(v), 4) for k, v in r.items()}})
    gb = pd.DataFrame(rows)
    gb.to_csv(RES / "growth_by_age.csv", index=False)
    G = lambda item, kind: gb[(gb.item == item) & (gb.kind == kind)].set_index("group")
    for item in ["choco", "snack", "sweets"]:
        main[item] = {kind: {grp: {"start": round(r.start, 1), "end": round(r.end, 1), "diff": round(r["diff"], 1), "pct": round(r.pct, 1)}
                             for grp, r in G(item, kind).iterrows()} for kind in ["nominal", "real", "pp", "real_pp"]}
    # 物価の伸び（3年平均の比）
    c = w[w.group == "平均"].set_index("year")
    main["cpi_pct"] = {k: round(100 * (c.loc[E, v].mean() / c.loc[S, v].mean() - 1), 1) for k, v in CPI_FOR.items()}
    main["facts"] = {"cpi_chocolate_2024_2025_pct": round(100 * (c.loc[2025, "cpi_chocolate"] / c.loc[2024, "cpi_chocolate"] - 1), 1),
                     "cpi_chocolate_2005_2025_ratio": round(c.loc[2025, "cpi_chocolate"] / c.loc[2005, "cpi_chocolate"], 2),
                     "choco_nominal_2024_2025_pct": round(100 * (c.loc[2025, "choco"] / c.loc[2024, "choco"] - 1), 1),
                     "snack_nominal_2019_2025_pct": round(100 * (c.loc[2025, "snack"] / c.loc[2019, "snack"] - 1), 1),
                     "choco_2025_yen": int(c.loc[2025, "choco"]), "snack_2025_yen": int(c.loc[2025, "snack"]),
                     "n_sample_u29_min": int(w[w.group == "29歳以下"].n_sample.min()), "n_sample_u29_max": int(w[w.group == "29歳以下"].n_sample.max()),
                     "n_sample_u29_2025": int(w[(w.group == "29歳以下") & (w.year == 2025)].n_sample.iloc[0]),
                     "persons_avg_start": round(c.loc[S, "persons"].mean(), 2), "persons_avg_end": round(c.loc[E, "persons"].mean(), 2)}
    # 仮説
    cn = G("choco", "nominal").pct
    sn = G("snack", "nominal").pct
    cr = G("choco", "real").pct
    h1 = min(cn["60～69歳"], cn["70歳以上"]) > max(cn["29歳以下"], cn["30～39歳"])
    h2 = cr["平均"] <= cn["平均"] / 2
    h3 = bool((sn.loc[AGES] < cn.loc[AGES]).all())
    ss = {}
    for item in ["choco", "snack", "sweets"]:
        for kind in ["nominal", "real"]:
            ss[f"{item}_{kind}"] = {k: round(float(v), 4) for k, v in shift_share(w, item, kind, S, E).items()}
    pd.DataFrame(ss).T.to_csv(RES / "shift_share.csv")
    h4 = ss["choco_nominal"]["composition"] < 0
    main["shift_share"] = ss
    main["hypotheses"] = {
        "H1": {"result": "支持" if h1 else "外れ", "choco_nominal_pct": {g: round(cn[g], 1) for g in AGES}},
        "H2": {"result": "支持" if h2 else "外れ", "nominal_pct": round(cn["平均"], 1), "real_pct": round(cr["平均"], 1)},
        "H3": {"result": "支持" if h3 else "外れ", "snack_nominal_pct": {g: round(sn[g], 1) for g in AGES}},
        "H4": {"result": "支持" if h4 else "外れ", "composition_yen": round(ss["choco_nominal"]["composition"], 1),
               "within_yen": round(ss["choco_nominal"]["within_age"], 1)}}
    # 菓子類の伸び（平均の世帯、名目）を品目に分ける
    items = ["choco", "snack", "icecream", "other", "wagashi_other", "yogashi_other", "senbei", "biscuit", "candy", "cake", "jelly",
             "pudding", "castella", "manju", "yokan"]
    a = w[(w.group == "平均") & w.year.isin(S)][items + ["sweets"]].mean()
    b = w[(w.group == "平均") & w.year.isin(E)][items + ["sweets"]].mean()
    ic = pd.DataFrame({"start": a, "end": b, "diff": b - a})
    ic["share_of_sweets_growth_pct"] = 100 * ic["diff"] / (b.sweets - a.sweets)
    ic = ic.round(2)
    ic.to_csv(RES / "items_contrib.csv")
    main["items_contrib"] = {k: {"diff": float(r["diff"]), "share_pct": float(r.share_of_sweets_growth_pct)} for k, r in ic.iterrows()}
    # 年ごとの系列（図用）
    yr = w[["year", "group", "choco", "snack", "sweets", "persons", "weight", "cpi_chocolate", "cpi_potato_chips", "cpi_sweets"]].copy()
    yr["choco_real"] = value(w, "choco", "real").round(2)
    yr["snack_real"] = value(w, "snack", "real").round(2)
    yr.to_csv(RES / "by_year.csv", index=False)
    # 頑健性
    variants = {"基準（3年平均、名目）": dict(kind="nominal", s=S, e=E),
                "端点を単年（2005→2025）": dict(kind="nominal", s=[2005], e=[2025]),
                "1人あたり（名目）": dict(kind="pp", s=S, e=E),
                "終点をコロナ前（2017〜19）": dict(kind="nominal", s=S, e=[2017, 2018, 2019]),
                "実質（品目の指数）": dict(kind="real", s=S, e=E),
                "実質（菓子類の指数）": dict(kind="real", s=S, e=E, defl="cpi_sweets"),
                "実質（品目の指数）・終点をコロナ前": dict(kind="real", s=S, e=[2017, 2018, 2019])}
    rb = []
    for name, v in variants.items():
        g = growth(w, "choco", v["kind"], v["s"], v["e"], v.get("defl")).pct
        gs = growth(w, "snack", v["kind"], v["s"], v["e"], v.get("defl")).pct
        top = g.loc[AGES].idxmax()
        rb.append({"variant": name, **{f"choco_{a}": round(g[a], 1) for a in GROUPS},
                   "choco_top_age": top, "H1_holds": bool(min(g["60～69歳"], g["70歳以上"]) > max(g["29歳以下"], g["30～39歳"])),
                   "snack_avg": round(gs["平均"], 1), "snack_below_choco_all_ages": bool((gs.loc[AGES] < g.loc[AGES]).all())})
    rb = pd.DataFrame(rb)
    rb.to_csv(RES / "robustness.csv", index=False)
    main["robustness"] = rb.set_index("variant").to_dict(orient="index")
    # 水準の年齢差（終点）
    e = G("choco", "nominal").end
    main["choco_end_level_top_age"] = e.loc[AGES].idxmax()
    (RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1, sort_keys=True, default=float) + "\n", encoding="utf-8")
    print(rb.T.to_string())


if __name__ == "__main__":
    main()
