"""職業別の50歳前後の未婚割合、分解、男女の比較、頑健性、問い直し。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
OCCJ = {"A": "管理的職業", "B": "専門的・技術的職業", "C": "事務", "D": "販売", "E": "サービス職業", "F": "保安職業",
        "G": "農林漁業", "H": "生産工程", "I": "輸送・機械運転", "J": "建設・採掘", "K": "運搬・清掃・包装等"}
OCC = list(OCCJ)
AGES50 = ["45～49歳", "50～54歳"]


def r(x, k=2):
    return None if x is None or pd.isna(x) else round(float(x), k)


def rates(df, year, sex, ages=AGES50, nat="総数", simple_mean=False):
    s = df[(df.year == year) & (df.sex == sex) & (df.nationality == nat) & df.age.isin(ages)]
    p = s.pivot_table(index=["occ", "age"], columns="marital", values="n", aggfunc="sum")
    p["den"] = p["未婚"] + p["有配偶"] + p["死別・離別"]
    if simple_mean:
        p["rate"] = p["未婚"] / p["den"]
        return 100 * p.groupby("occ").rate.mean(), p.groupby("occ").den.sum()
    g = p.groupby("occ")[["未婚", "den"]].sum()
    return 100 * g["未婚"] / g.den, g.den


def decompose(df, y0, y1, sex, ages=AGES50):
    r0, n0 = rates(df, y0, sex, ages); r1, n1 = rates(df, y1, sex, ages)
    w0 = n0[OCC] / n0[OCC].sum(); w1 = n1[OCC] / n1[OCC].sum()
    comp = ((w1 - w0) * r0[OCC]).sum(); within = (w1 * (r1[OCC] - r0[OCC])).sum()
    return dict(total=float(comp + within), composition=float(comp), within=float(within),
                share_within=float(within / (comp + within)) if comp + within != 0 else np.nan)


def main():
    df = pd.read_csv(DATA / "national_long.csv")
    out = {"overall": {}, "by_occ": {}}
    tab = []
    for y in (2010, 2015, 2020):
        for sex in ("男", "女"):
            rr, nn = rates(df, y, sex)
            out["overall"].setdefault(sex, {})[y] = r(rr["総数"])
            for o in OCC:
                tab.append(dict(year=y, sex=sex, occ=OCCJ[o], rate=rr[o], employed=nn[o]))
    tab = pd.DataFrame(tab)
    tab.round(4).to_csv(RES / "rates_by_occupation.csv", index=False)
    for sex in ("男", "女"):
        t = tab[tab.sex == sex].pivot(index="occ", columns="year", values="rate").loc[[OCCJ[o] for o in OCC]]
        out["by_occ"][sex] = {o: {int(y): r(v) for y, v in row.items()} for o, row in t.iterrows()}
    dm = decompose(df, 2010, 2020, "男"); dw = decompose(df, 2010, 2020, "女")
    out["decomposition_2010_2020"] = {"男": {k: r(v, 3) for k, v in dm.items()}, "女": {k: r(v, 3) for k, v in dw.items()}}
    m20 = tab[(tab.sex == "男") & (tab.year == 2020)].set_index("occ").rate
    w20 = tab[(tab.sex == "女") & (tab.year == 2020)].set_index("occ").rate
    m10 = tab[(tab.sex == "男") & (tab.year == 2010)].set_index("occ").rate
    rho_mw, p_mw = stats.spearmanr(m20, w20[m20.index])
    rho_t, p_t = stats.spearmanr(m10, m20[m10.index])
    out["spearman_men_women_2020"] = dict(rho=r(rho_mw, 3), p=r(p_mw, 4))
    out["spearman_men_2010_2020"] = dict(rho=r(rho_t, 3), p=r(p_t, 5))
    out["range_2020"] = {"男": [r(m20.min()), r(m20.max())], "女": [r(w20.min()), r(w20.max())]}
    out["n_occ_up_2010_2020"] = {sex: int((tab[(tab.sex == sex) & (tab.year == 2020)].set_index("occ").rate >
                                          tab[(tab.sex == sex) & (tab.year == 2010)].set_index("occ").rate).sum()) for sex in ("男", "女")}

    # 頑健性（男性）
    rob = []
    def rowfor(name, y0, y1, ages=AGES50, simple=False):
        a, _ = rates(df, y0, "男", ages, simple_mean=simple); b, _ = rates(df, y1, "男", ages, simple_mean=simple)
        d = decompose(df, y0, y1, "男", ages)
        bw, _ = rates(df, y1, "女", ages, simple_mean=simple)
        rho, _ = stats.spearmanr(b[OCC], bw[OCC])
        rob.append(dict(check=name, men_change=r(b["総数"] - a["総数"]), within_share=None if simple else r(d["share_within"], 3),
                        composition=None if simple else r(d["composition"], 3), rho_men_women=r(rho, 3), rho_men_y0_y1=r(stats.spearmanr(a[OCC], b[OCC])[0], 3)))
    rowfor("0 主（2010→2020年、45〜54歳の合計）", 2010, 2020)
    rowfor("1 45〜49歳と50〜54歳の割合の単純平均", 2010, 2020, simple=True)
    rowfor("2 期間 2015→2020年", 2015, 2020)
    rowfor("3 年齢 40〜49歳", 2010, 2020, ages=["40～44歳", "45～49歳"])
    j, _ = rates(df, 2020, "男", nat="日本人"); jw, _ = rates(df, 2020, "女", nat="日本人")
    rob.append(dict(check="4 日本人だけ（2020年の水準）", men_change=None, within_share=None, composition=None,
                    rho_men_women=r(stats.spearmanr(j[OCC], jw[OCC])[0], 3), rho_men_y0_y1=None,
                    note=f"男 総数 {j['総数']:.2f}（国籍総数 {m20.get('総数', np.nan) if False else rates(df, 2020, '男')[0]['総数']:.2f}）"))
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rob.astype(object).where(rob.notna(), None).to_dict(orient="records")

    # 問い直し：35〜44歳
    rq = []
    for y in (2010, 2020):
        for sex in ("男", "女"):
            rr, _ = rates(df, y, sex, ages=["35～39歳", "40～44歳"])
            for o in ["総数"] + OCC:
                rq.append(dict(year=y, sex=sex, occ="総数" if o == "総数" else OCCJ[o], rate=rr[o]))
    rq = pd.DataFrame(rq)
    rq.round(4).to_csv(RES / "requestion_35_44.csv", index=False)
    m3 = rq[(rq.sex == "男") & (rq.year == 2020) & (rq.occ != "総数")].set_index("occ").rate
    out["requestion"] = {"overall": {sex: {y: r(rq[(rq.sex == sex) & (rq.year == y) & (rq.occ == "総数")].rate.iloc[0]) for y in (2010, 2020)} for sex in ("男", "女")},
                         "rho_men_35_44_vs_45_54_2020": r(stats.spearmanr(m3, m20[m3.index])[0], 3),
                         "men_2020": {o: r(v) for o, v in m3.items()}}

    H = out
    out["hypotheses"] = {
        "H1": dict(value=r(H["overall"]["男"][2020] - H["overall"]["男"][2010]), verdict="支持" if H["overall"]["男"][2020] - H["overall"]["男"][2010] >= 3 else "外れ"),
        "H2": dict(value=r(dm["share_within"], 3), verdict="支持" if dm["share_within"] >= 0.8 else "外れ"),
        "H3": dict(value=r(rho_mw, 3), verdict="支持" if rho_mw < 0 else "外れ"),
        "H4": dict(value=r(rho_t, 3), verdict="支持" if rho_t >= 0.8 else "外れ"),
    }
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
