"""03_analysis.py : 勤労者世帯の「こづかい（使途不明）」の減り方（実質・割合・年齢・共働き）、構成の分解、頑健性（オフライン）。
出力：results/series.csv, results/by_group.csv, results/shift_share.csv, results/robustness.csv, results/main.json
"""
import json
import pathlib

import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RES = ROOT / "results"
RES.mkdir(exist_ok=True)

P0 = (2000, 2002)
P1 = (2023, 2025)
AGES = ["age_u29", "age_30s", "age_40s", "age_50s", "age_60s"]
POCKET = "こづかい(使途不明)"


def r0(x):
    return int(round(float(x)))


def r1(x):
    return round(float(x), 1)


def load():
    df = pd.read_csv(DATA / "kakei_pocket_long.csv")
    cpi = pd.read_csv(DATA / "cpi_annual.csv")
    w = df.pivot_table(index=["group", "year"], columns="item", values="value").reset_index()
    w = w.merge(cpi[["year", "deflator_to_2025"]], on="year", how="left")
    w["pocket_real"] = w[POCKET] * w["deflator_to_2025"]
    w["kosai_real"] = w["交際費"] * w["deflator_to_2025"]
    w["cons_real"] = w["消費支出"] * w["deflator_to_2025"]
    w["pocket_share_cons"] = w[POCKET] / w["消費支出"] * 100
    w["kosai_share_cons"] = w["交際費"] / w["消費支出"] * 100
    w["pocket_share_dispo"] = w[POCKET] / w["可処分所得"] * 100
    w["pocket_real_per_person"] = w["pocket_real"] / w["世帯人員"]
    w["pocket_real_per_earner"] = w["pocket_real"] / w["有業人員"]
    return w.sort_values(["group", "year"]).reset_index(drop=True)


def pmean(s, col, p):
    return float(s[(s["year"] >= p[0]) & (s["year"] <= p[1])][col].mean())


def pchange(s, col, p0=P0, p1=P1):
    a, b = pmean(s, col, p0), pmean(s, col, p1)
    return a, b, (b / a - 1) * 100


def shift_share(w, groups, col, p0=P0, p1=P1):
    """平均の変化 ＝ 中の変化（重みを最初の期に固定）＋ 構成の変化（中身を最後の期で評価）"""
    x0 = np.array([pmean(w[w.group == g], col, p0) for g in groups])
    x1 = np.array([pmean(w[w.group == g], col, p1) for g in groups])
    n0 = np.array([pmean(w[w.group == g], "世帯数分布(抽出率調整)", p0) for g in groups])
    n1 = np.array([pmean(w[w.group == g], "世帯数分布(抽出率調整)", p1) for g in groups])
    s0, s1 = n0 / n0.sum(), n1 / n1.sum()
    a, b = float((s0 * x0).sum()), float((s1 * x1).sum())
    within = float((s0 * (x1 - x0)).sum())
    comp = float(((s1 - s0) * x1).sum())
    return {"weighted_p0": a, "weighted_p1": b, "change": b - a, "within": within, "composition": comp,
            "within_share_pct": within / (b - a) * 100 if b != a else float("nan"),
            "weights_p0": dict(zip(groups, s0.round(4).tolist())), "weights_p1": dict(zip(groups, s1.round(4).tolist())),
            "x0": dict(zip(groups, x0.round(1).tolist())), "x1": dict(zip(groups, x1.round(1).tolist()))}


def trend_pct(s, col, drop=()):
    t = s[~s["year"].isin(drop)]
    b = np.polyfit(t["year"].to_numpy(dtype=float), np.log(t[col].to_numpy(dtype=float)), 1)[0]
    return (np.exp(b) - 1) * 100


def main():
    w = load()
    wa = w[w.group == "workers_all"].copy()
    keep = ["year", "集計世帯数", "世帯主の年齢", "世帯人員", "有業人員", "可処分所得", "消費支出", POCKET, "交際費",
            "pocket_real", "kosai_real", "pocket_share_cons", "kosai_share_cons", "pocket_share_dispo"]
    wa[keep].to_csv(RES / "series.csv", index=False, float_format="%.2f")
    w[["group", "year", "集計世帯数", "世帯主の年齢", "世帯数分布(抽出率調整)", POCKET, "交際費", "消費支出",
       "pocket_real", "kosai_real", "pocket_share_cons"]].to_csv(RES / "by_group.csv", index=False, float_format="%.2f")

    y = wa.set_index("year")
    m = {"group": "二人以上の世帯のうち勤労者世帯", "periods": {"p0": "2000-2002", "p1": "2023-2025"}}
    for yr in (2000, 2005, 2010, 2015, 2017, 2018, 2020, 2025):
        m[f"pocket_{yr}"] = r0(y.loc[yr, POCKET])
        m[f"kosai_{yr}"] = r0(y.loc[yr, "交際費"])
    m["pocket_2000_real2025"] = r0(y.loc[2000, "pocket_real"])
    m["pocket_share_cons_2000"] = r1(y.loc[2000, "pocket_share_cons"])
    m["pocket_share_cons_2025"] = r1(y.loc[2025, "pocket_share_cons"])
    m["pocket_share_dispo_2000"] = r1(y.loc[2000, "pocket_share_dispo"])
    m["pocket_share_dispo_2025"] = r1(y.loc[2025, "pocket_share_dispo"])
    m["consumption_2000"] = r0(y.loc[2000, "消費支出"])
    m["consumption_2025"] = r0(y.loc[2025, "消費支出"])
    m["head_age_2000"] = r1(y.loc[2000, "世帯主の年齢"])
    m["head_age_2025"] = r1(y.loc[2025, "世帯主の年齢"])
    m["sample_range"] = [r0(y["集計世帯数"].min()), r0(y["集計世帯数"].max())]
    m["pocket_nominal_max"] = {"year": int(y[POCKET].idxmax()), "value": r0(y[POCKET].max())}
    m["pocket_nominal_min"] = {"year": int(y[POCKET].idxmin()), "value": r0(y[POCKET].min())}

    # H1
    a, b, c = pchange(wa, "pocket_real")
    an, bn, cn = pchange(wa, POCKET)
    m["H1"] = {"pocket_real_p0": r0(a), "pocket_real_p1": r0(b), "change_pct": r1(c),
               "pocket_nominal_p0": r0(an), "pocket_nominal_p1": r0(bn), "change_nominal_pct": r1(cn)}
    m["H1"]["verdict"] = "支持" if c <= -30 else "外れ"
    # H2
    ka, kb, kc = pchange(wa, "kosai_real")
    m["H2"] = {"kosai_real_p0": r0(ka), "kosai_real_p1": r0(kb), "kosai_change_pct": r1(kc), "pocket_change_pct": r1(c)}
    m["H2"]["verdict"] = "支持" if c < kc else "外れ"
    ca, cb, cc = pchange(wa, "cons_real")
    m["consumption_real_change_pct"] = r1(cc)
    # H3
    h3 = {}
    for g in AGES:
        s = w[w.group == g]
        a3, b3, c3 = pchange(s, "pocket_real")
        h3[g] = {"p0": r0(a3), "p1": r1(b3) if False else r0(b3), "change_pct": r1(c3),
                 "n_p1": r0(pmean(s, "集計世帯数", P1))}
    m["H3"] = {"by_age": h3, "max_change_pct": max(v["change_pct"] for v in h3.values()),
               "min_change_pct": min(v["change_pct"] for v in h3.values())}
    m["H3"]["verdict"] = "支持" if all(v["change_pct"] <= -20 for v in h3.values()) else "外れ"
    # H4 シフト・シェア（年齢）
    ss = shift_share(w, AGES, "pocket_real")
    m["H4"] = {k: (r1(v) if isinstance(v, float) else v) for k, v in ss.items()}
    m["H4"]["verdict"] = "支持" if ss["within_share_pct"] >= 80 else "外れ"
    m["H4"]["age60s_weight_pct_p0"] = r1(ss["weights_p0"]["age_60s"] * 100)
    m["H4"]["age60s_weight_pct_p1"] = r1(ss["weights_p1"]["age_60s"] * 100)
    # 共働き・夫のみ有業
    dd = {}
    for g in ("dual", "husband_only"):
        s = w[w.group == g]
        a4, b4, c4 = pchange(s, "pocket_real")
        dd[g] = {"p0": r0(a4), "p1": r0(b4), "change_pct": r1(c4),
                 "head_age_p0": r1(pmean(s, "世帯主の年齢", P0)), "head_age_p1": r1(pmean(s, "世帯主の年齢", P1))}
    ss2 = shift_share(w, ["dual", "husband_only"], "pocket_real")
    dd["shift_share"] = {k: (r1(v) if isinstance(v, float) else v) for k, v in ss2.items()}
    m["dual_vs_husband_only"] = dd
    rows = []
    for name, sres in (("age5", ss), ("dual_husband", ss2)):
        rows.append((name, sres["weighted_p0"], sres["weighted_p1"], sres["change"], sres["within"],
                     sres["composition"], sres["within_share_pct"]))
    pd.DataFrame(rows, columns=["decomposition", "weighted_p0", "weighted_p1", "change", "within", "composition",
                                "within_share_pct"]).to_csv(RES / "shift_share.csv", index=False, float_format="%.2f")

    # 頑健性
    rob = [("基本", "勤労者世帯・実質・2000〜02→2023〜25", r1(c), r1(kc))]
    rob.append(("R1", "名目", r1(cn), r1(pchange(wa, "交際費")[2])))
    rob.append(("R2", "消費支出に占める割合（%ポイントではなく変化率）", r1(pchange(wa, "pocket_share_cons")[2]),
                r1(pchange(wa, "kosai_share_cons")[2])))
    rob.append(("R3a", "1人あたり（世帯人員で割る）・実質", r1(pchange(wa, "pocket_real_per_person")[2]), None))
    rob.append(("R3b", "有業人員1人あたり・実質", r1(pchange(wa, "pocket_real_per_earner")[2]), None))
    rob.append(("R4a", "比べる期間 2005〜07→2023〜25", r1(pchange(wa, "pocket_real", (2005, 2007))[2]),
                r1(pchange(wa, "kosai_real", (2005, 2007))[2])))
    rob.append(("R4b", "比べる期間 2015〜17→2023〜25", r1(pchange(wa, "pocket_real", (2015, 2017))[2]),
                r1(pchange(wa, "kosai_real", (2015, 2017))[2])))
    rob.append(("R5", "2018年の家計簿の改正をまたがない 2000〜02→2015〜17", r1(pchange(wa, "pocket_real", P0, (2015, 2017))[2]),
                r1(pchange(wa, "kosai_real", P0, (2015, 2017))[2])))
    t1 = trend_pct(wa, "pocket_real", drop=(2020, 2021))
    t2 = trend_pct(wa, "kosai_real", drop=(2020, 2021))
    rob.append(("R6", "対数の直線の傾き（年率%）×25年、2020〜21年を除く", r1((np.exp(np.log(1 + t1 / 100) * 25) - 1) * 100),
                r1((np.exp(np.log(1 + t2 / 100) * 25) - 1) * 100)))
    tp = w[w.group == "twoplus_all"]
    rob.append(("R7", "二人以上の世帯（全体）", r1(pchange(tp, "pocket_real")[2]), r1(pchange(tp, "kosai_real")[2])))
    rb = pd.DataFrame(rob, columns=["id", "condition", "pocket_change_pct", "kosai_change_pct"])
    rb["H1_verdict"] = np.where(rb["pocket_change_pct"] <= -30, "支持", "外れ")
    rb["H2_verdict"] = [("" if pd.isna(k) else ("支持" if p < k else "外れ")) for p, k in
                        zip(rb["pocket_change_pct"], rb["kosai_change_pct"])]
    rb.to_csv(RES / "robustness.csv", index=False)
    m["robustness"] = rb.where(pd.notna(rb), None).to_dict(orient="records")
    m["trend_pocket_real_pct_per_year"] = round(float(t1), 2)
    m["trend_kosai_real_pct_per_year"] = round(float(t2), 2)

    # 2018年の段差：前年比（対数、%）の分布
    lg = np.log(y["pocket_real"]).diff() * 100
    other = lg.drop([2018]).dropna()
    m["break2018"] = {"yoy_2018_pct": r1(lg.loc[2018]), "yoy_other_mean": r1(other.mean()), "yoy_other_sd": r1(other.std(ddof=1)),
                      "z": round(float((lg.loc[2018] - other.mean()) / other.std(ddof=1)), 2),
                      "yoy_2019_pct": r1(lg.loc[2019])}

    (RES / "main.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(m, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
