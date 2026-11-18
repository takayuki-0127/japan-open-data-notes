"""電気の推移、用途別の変化、世帯人数の構成の分解、家電の使用年数の分解、頑健性。"""
import pathlib, json
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
RES.mkdir(exist_ok=True)
KWH = 1e6 / 3600  # 1 GJ = 277.78 kWh
OLD = ["1995年以前", "1996年～2000年", "2001年～2005年", "2006年～2010年", "2011年～2015年", "2016年以降"]
NEW = ["2000年以前", "2001年～2005年", "2006年～2010年", "2011年～2015年", "2016年～2020年", "2021年以降"]
AGE_17_22 = ["22年以上", "17〜21年", "12〜16年", "7〜11年", "2〜6年", "0〜1年"]
AGE_18_23 = ["23年以上", "18〜22年", "13〜17年", "8〜12年", "3〜7年", "0〜2年"]


def r(x, k=3):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), k)


def shift_share(s0, e0, s1, e1):
    """平均＝Σ s e。対称な分解：構成＝Σ Δs·ē、区分の中＝Σ s̄·Δe。s は合計1に直した割合。"""
    s0, s1 = s0 / s0.sum(), s1 / s1.sum()
    m0, m1 = (s0 * e0).sum(), (s1 * e1).sum()
    comp = ((s1 - s0) * (e0 + e1) / 2).sum()
    within = ((s0 + s1) / 2 * (e1 - e0)).sum()
    return {"mean0": m0, "mean1": m1, "diff": m1 - m0, "composition": comp, "within": within,
            "composition_share": comp / (m1 - m0) if m1 != m0 else np.nan}


def vintage(t, group, y0, y1, ages):
    a = t[(t.group == group) & (t.fy == y0) & (t.cat1.isin(OLD))].set_index("cat1").loc[OLD]
    b = t[(t.group == group) & (t.fy == y1) & (t.cat1.isin(NEW))].set_index("cat1").loc[NEW]
    df = pd.DataFrame({"age": ages, "label0": OLD, "label1": NEW, "w0": a.w.values, "w1": b.w.values,
                       "share0": a.w.values / a.w.sum() * 100, "share1": b.w.values / b.w.sum() * 100,
                       "elec0": a["mean"].values, "elec1": b["mean"].values, "n0": a.n.values, "n1": b.n.values})
    ss = shift_share(df.w0.values, df.elec0.values, df.w1.values, df.elec1.values)
    unk0 = t[(t.group == group) & (t.fy == y0) & (t.cat1 == "不明")].w.iloc[0] / t[(t.group == group) & (t.fy == y0)].w.sum() * 100
    unk1 = t[(t.group == group) & (t.fy == y1) & (t.cat1 == "不明")].w.iloc[0] / t[(t.group == group) & (t.fy == y1)].w.sum() * 100
    ss.update({"unknown_share0_pct": unk0, "unknown_share1_pct": unk1})
    # 平均の使用年数（区分の中央の値で近似。最も古い区分は下限+2年）
    mid = np.array([24, 19, 14, 9, 4, 0.5]) if ages is AGE_17_22 else np.array([25, 20, 15, 10, 5, 1])
    ss["mean_age0"] = float((df.share0 * mid).sum() / 100); ss["mean_age1"] = float((df.share1 * mid).sum() / 100)
    ss["share_le6_0"] = float(df.share0.iloc[4:].sum()); ss["share_le6_1"] = float(df.share1.iloc[4:].sum())
    ss["share_ge12_0"] = float(df.share0.iloc[:3].sum()); ss["share_ge12_1"] = float(df.share1.iloc[:3].sum())
    return df, ss


def main():
    ts = pd.read_csv(DATA / "ts2_long.csv")
    t622 = pd.read_csv(DATA / "t622_long.csv")
    t711 = pd.read_csv(DATA / "t711_long.csv")
    sk = pd.read_csv(DATA / "sokuhou_trend.csv")
    main = {"note": "値は年度。電気の GJ/世帯・年は調査の表のとおり。1 GJ＝277.78 kWh で換算。"}

    # 1. 推移
    nat = ts[(ts.group == "全国") & (ts.kind == "電気")].set_index("fy")["mean"]
    tr = sk.copy(); tr["elec_kwh"] = tr.elec_gj * KWH
    tr.to_csv(RES / "trend_national.csv", index=False, float_format="%.3f")
    main["elec_gj"] = {int(k): r(v, 2) for k, v in tr.set_index("fy").elec_gj.dropna().items()}
    main["elec_kwh"] = {int(k): r(v, 0) for k, v in tr.set_index("fy").elec_kwh.dropna().items()}
    main["check_ts2_vs_sokuhou_maxdiff"] = r((tr.set_index("fy").elec_gj.loc[2017:2023] - nat).abs().max(), 4)
    g = lambda a, b: (nat[b] / nat[a] - 1) * 100
    main["elec_change_pct"] = {"2017_2023": r(g(2017, 2023), 2), "2019_2023": r(g(2019, 2023), 2), "2017_2022": r(g(2017, 2022), 2),
                               "2018_2023": r(g(2018, 2023), 2),
                               "2017_2025": r((tr.set_index("fy").elec_gj[2025] / nat[2017] - 1) * 100, 2)}
    main["elec_diff_gj_2017_2023"] = r(nat[2023] - nat[2017], 3)
    main["elec_diff_kwh_2017_2023"] = r((nat[2023] - nat[2017]) * KWH, 1)

    # 2. 用途別（全エネルギー）
    u = t711[t711.group == "全国"].pivot(index="fy", columns="kind", values="mean")
    uses = ["暖房", "冷房", "給湯", "台所用コンロ", "照明・家電製品等"]
    u = u[uses]; u["5用途の合計"] = u.sum(axis=1)
    u.to_csv(RES / "uses_by_fy.csv", float_format="%.3f")
    d = u.loc[2023] - u.loc[2017]
    main["uses_2017"] = {k: r(v, 2) for k, v in u.loc[2017].items()}
    main["uses_2023"] = {k: r(v, 2) for k, v in u.loc[2023].items()}
    main["uses_diff_2017_2023"] = {k: r(v, 3) for k, v in d.items()}
    main["lighting_appliances_share_of_decline_pct"] = r(d["照明・家電製品等"] / d["5用途の合計"] * 100, 2)
    main["heating_share_of_decline_pct"] = r(d["暖房"] / d["5用途の合計"] * 100, 2)
    main["hotwater_share_of_decline_pct"] = r(d["給湯"] / d["5用途の合計"] * 100, 2)
    main["lighting_appliances_change_pct"] = r((u.loc[2023, "照明・家電製品等"] / u.loc[2017, "照明・家電製品等"] - 1) * 100, 2)

    # 3. 世帯人数の構成
    def size_decomp(group, y0, y1):
        s = ts[(ts.group == group) & (ts.kind == "電気") & (ts.cat != "不明")]
        a = s[s.fy == y0].set_index("cat"); b = s[s.fy == y1].set_index("cat").loc[a.index]
        dd = shift_share(a.w.values, a["mean"].values, b.w.values, b["mean"].values)
        tab = pd.DataFrame({"cat": a.index, "share0": a.w.values / a.w.sum() * 100, "share1": b.w.values / b.w.sum() * 100,
                            "elec0": a["mean"].values, "elec1": b["mean"].values})
        return dd, tab
    hs, hs_tab = size_decomp("世帯人数別（6区分）", 2017, 2023)
    hs_tab.to_csv(RES / "household_size_2017_2023.csv", index=False, float_format="%.3f")
    main["household_size_2017_2023"] = {k: r(v, 4) for k, v in hs.items()}
    main["household_size_shares"] = {row.cat: {"2017": r(row.share0, 2), "2023": r(row.share1, 2), "elec2017": r(row.elec0, 2), "elec2023": r(row.elec1, 2)} for row in hs_tab.itertuples()}

    # 4. 家電の使用年数
    vt = []
    res_v = {}
    for grp, key in [("冷蔵庫（1台目）の製造時期別", "fridge"), ("エアコン（1台目）の製造時期別", "aircon"), ("テレビ（1台目）の製造時期別", "tv")]:
        for (y0, y1, ages) in [(2017, 2022, AGE_17_22), (2018, 2023, AGE_18_23)]:
            df, ss = vintage(t622, grp, y0, y1, ages)
            df.insert(0, "pair", f"{y0}→{y1}"); df.insert(0, "appliance", key)
            vt.append(df)
            ss["national_diff"] = float(nat[y1] - nat[y0])
            ss["composition_share_of_national"] = ss["composition"] / ss["national_diff"]
            res_v[f"{key}_{y0}_{y1}"] = {k: r(v, 4) for k, v in ss.items()}
    pd.concat(vt).to_csv(RES / "vintage_age_tables.csv", index=False, float_format="%.3f")
    main["vintage"] = res_v

    # 5. 断面：2022年度、単身・2人以上ごとに冷蔵庫の年数別の電気
    cs = t622[(t622.group == "世帯類型別・冷蔵庫（1台目）の製造時期別") & (t622.fy.isin([2022, 2023])) & (t622.cat2.isin(NEW))].copy()
    cs["age_rank"] = cs.cat2.map({k: i for i, k in enumerate(NEW)})
    cs = cs.sort_values(["fy", "cat1", "age_rank"])
    cs[["fy", "cat1", "cat2", "w", "n", "mean"]].to_csv(RES / "cross_section_fridge_by_hhtype.csv", index=False)
    cross = {}
    for (fy, h), s in cs.groupby(["fy", "cat1"], sort=True):
        new = s[s.age_rank >= 4]; old = s[s.age_rank <= 2]
        en = (new.w * new["mean"]).sum() / new.w.sum(); eo = (old.w * old["mean"]).sum() / old.w.sum()
        cross[f"{fy}_{h}"] = {"new_le6_or_7": r(en, 3), "old_ge12_or_13": r(eo, 3), "diff_pct": r((en / eo - 1) * 100, 2)}
    allc = t622[(t622.group == "冷蔵庫（1台目）の製造時期別") & (t622.fy == 2022) & (t622.cat1.isin(NEW))].set_index("cat1").loc[NEW]
    en = (allc.w.iloc[4:] * allc["mean"].iloc[4:]).sum() / allc.w.iloc[4:].sum(); eo = (allc.w.iloc[:3] * allc["mean"].iloc[:3]).sum() / allc.w.iloc[:3].sum()
    cross["2022_全体"] = {"new_le6_or_7": r(en, 3), "old_ge12_or_13": r(eo, 3), "diff_pct": r((en / eo - 1) * 100, 2)}
    main["cross_section_fridge"] = cross

    # 頑健性
    rob = []
    v = res_v
    rob.append({"check": "基本：冷蔵庫、2017→2022年度", "composition_gj": v["fridge_2017_2022"]["composition"], "diff_gj": v["fridge_2017_2022"]["diff"], "share": v["fridge_2017_2022"]["composition_share"]})
    rob.append({"check": "年の組：冷蔵庫、2018→2023年度", "composition_gj": v["fridge_2018_2023"]["composition"], "diff_gj": v["fridge_2018_2023"]["diff"], "share": v["fridge_2018_2023"]["composition_share"]})
    for k, nm in [("aircon", "エアコン"), ("tv", "テレビ")]:
        for p in ["2017_2022", "2018_2023"]:
            rob.append({"check": f"機器：{nm}、{p.replace('_', '→')}年度", "composition_gj": v[f"{k}_{p}"]["composition"], "diff_gj": v[f"{k}_{p}"]["diff"], "share": v[f"{k}_{p}"]["composition_share"]})
    ht, _ = size_decomp("世帯類型別（8区分）", 2017, 2023)
    rob.append({"check": "構成の区分：世帯類型（8区分）、2017→2023年度", "composition_gj": ht["composition"], "diff_gj": ht["diff"], "share": ht["composition_share"]})
    h19, _ = size_decomp("世帯人数別（6区分）", 2019, 2023)
    rob.append({"check": "期間：世帯人数、2019→2023年度", "composition_gj": h19["composition"], "diff_gj": h19["diff"], "share": h19["composition_share"]})
    h17_20, _ = size_decomp("世帯人数別（6区分）", 2017, 2020)
    rob.append({"check": "期間：世帯人数、2017→2020年度（重みの基準が同じ）", "composition_gj": h17_20["composition"], "diff_gj": h17_20["diff"], "share": h17_20["composition_share"]})
    h20_21, _ = size_decomp("世帯人数別（6区分）", 2020, 2021)
    rob.append({"check": "期間：世帯人数、2020→2021年度（世帯数分布の重みが替わる年）", "composition_gj": h20_21["composition"], "diff_gj": h20_21["diff"], "share": h20_21["composition_share"]})
    h21_23, _ = size_decomp("世帯人数別（6区分）", 2021, 2023)
    rob.append({"check": "期間：世帯人数、2021→2023年度（重みの基準が同じ）", "composition_gj": h21_23["composition"], "diff_gj": h21_23["diff"], "share": h21_23["composition_share"]})
    rb = pd.DataFrame(rob); rb.to_csv(RES / "robustness.csv", index=False, float_format="%.4f")
    main["robustness"] = [{k: (r(x, 4) if isinstance(x, float) else x) for k, x in row.items()} for row in rob]
    (RES / "main.json").write_text(json.dumps(main, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: main[k] for k in ["elec_gj", "elec_change_pct", "uses_diff_2017_2023", "lighting_appliances_share_of_decline_pct", "household_size_2017_2023", "cross_section_fridge"]}, ensure_ascii=False, indent=1))
    print(json.dumps(res_v["fridge_2017_2022"], ensure_ascii=False)); print(rb.to_string())


if __name__ == "__main__":
    main()
