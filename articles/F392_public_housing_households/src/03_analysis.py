"""公営の借家の推移、地方別の割合、年齢別の利用率と分解、頑健性、問い直し（家賃）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
REGIONS = [("北海道", [1]), ("東北", range(2, 8)), ("関東", range(8, 15)), ("中部", range(15, 24)),
           ("近畿", range(24, 31)), ("中国", range(31, 36)), ("四国", range(36, 40)), ("九州・沖縄", range(40, 48))]
# 2003年と2023年に共通する年齢区分 → まとめ方
COARSE = {"25歳未満": "〜29歳", "25～29歳": "〜29歳", "30～34歳": "30〜39歳", "35～39歳": "30〜39歳", "40～44歳": "40〜49歳",
          "45～49歳": "40〜49歳", "50～54歳": "50〜59歳", "55～59歳": "50〜59歳", "60～64歳": "60〜64歳", "65～69歳": "65〜74歳",
          "70～74歳": "65〜74歳", "75歳以上": "75歳以上", "75～79歳": "75歳以上", "80～84歳": "75歳以上", "85歳以上": "75歳以上"}
FINE = {k: k for k in COARSE}
FINE.update({"75～79歳": "75歳以上", "80～84歳": "75歳以上", "85歳以上": "75歳以上"})
ORDER = ["〜29歳", "30〜39歳", "40〜49歳", "50〜59歳", "60〜64歳", "65〜74歳", "75歳以上"]


def r(x, k=2):
    return None if x is None or pd.isna(x) else round(float(x), k)


def age_table(ag, y, mapping):
    s = ag[(ag.year == y) & ag.age.isin(mapping.keys())].copy()
    s["g"] = s.age.map(mapping)
    return s.groupby("g", sort=False)[["total", "public"]].sum()


def decompose(ag, y0, y1, mapping):
    a, b = age_table(ag, y0, mapping), age_table(ag, y1, mapping)
    a, b = a.align(b, join="outer", fill_value=0)
    ra, rb = a.public / a.total, b.public / b.total
    comp = ((b.total - a.total) * ra).sum()          # 年齢の世帯数の変化（利用率は y0 のまま）
    rate = (b.total * (rb - ra)).sum()                # 利用率の変化（y1 の世帯数で重み）
    return dict(change=float(b.public.sum() - a.public.sum()), composition=float(comp), rate=float(rate),
                rates0=ra, rates1=rb)


def main():
    jp = pd.read_csv(DATA / "tenure_japan.csv")
    pr = pd.read_csv(DATA / "tenure_pref.csv")
    ag = pd.read_csv(DATA / "tenure_age.csv")
    rent = pd.read_csv(DATA / "rent.csv")
    out = {}

    jp["public_share"] = 100 * jp.public / jp.total
    jp["public_share_rented"] = 100 * jp.public / jp.rented
    jp.round(4).to_csv(RES / "japan_trend.csv", index=False)
    J = jp.set_index("year")
    out["japan"] = {int(y): dict(public=r(x.public, 0), share=r(x.public_share), share_rented=r(x.public_share_rented)) for y, x in J.iterrows()}
    peak = int(J.public.idxmax())
    out["peak_year"] = peak
    out["change_2003_2023_pct"] = r(100 * (J.loc[2023, "public"] / J.loc[2003, "public"] - 1), 1)
    out["change_2018_2023_pct"] = r(100 * (J.loc[2023, "public"] / J.loc[2018, "public"] - 1), 1)

    # 地方別
    reg = []
    for name, nos in REGIONS:
        for y in sorted(pr.year.unique()):
            s = pr[(pr.year == y) & pr.pref.isin(list(nos))]
            reg.append(dict(area=name, year=int(y), total=s.total.sum(), rented=s.rented.sum(), public=s.public.sum()))
    reg = pd.DataFrame(reg)
    reg["share"] = 100 * reg.public / reg.total
    reg["share_rented"] = 100 * reg.public / reg.rented
    reg.round(4).to_csv(RES / "region_trend.csv", index=False)
    R = reg.pivot(index="area", columns="year", values="share").loc[[n for n, _ in REGIONS]]
    RR = reg.pivot(index="area", columns="year", values="share_rented").loc[[n for n, _ in REGIONS]]
    RP = reg.pivot(index="area", columns="year", values="public").loc[[n for n, _ in REGIONS]]
    out["regions"] = {a: dict(share_1983=r(R.loc[a, 1983]), share_2003=r(R.loc[a, 2003]), share_2023=r(R.loc[a, 2023]),
                              public_2003=r(RP.loc[a, 2003], 0), public_2023=r(RP.loc[a, 2023], 0),
                              change_pct=r(100 * (RP.loc[a, 2023] / RP.loc[a, 2003] - 1), 1)) for a in R.index}
    n_down = int((R[2023] < R[2003]).sum())
    P = pr.pivot(index="pref", columns="year", values="public") / pr.pivot(index="pref", columns="year", values="total")
    n_pref_down = int((P[2023] < P[2003]).sum())

    # 年齢
    d = decompose(ag, 2003, 2023, COARSE)
    rates = pd.DataFrame({"rate_2003": 100 * d["rates0"], "rate_2023": 100 * d["rates1"]}).loc[ORDER]
    t03, t23 = age_table(ag, 2003, COARSE), age_table(ag, 2023, COARSE)
    rates["public_2003"] = t03.public; rates["public_2023"] = t23.public
    rates["households_2003"] = t03.total; rates["households_2023"] = t23.total
    rates.round(4).to_csv(RES / "age_rates.csv")
    out["age_rates"] = {a: dict(rate_2003=r(x.rate_2003), rate_2023=r(x.rate_2023), public_2003=r(x.public_2003, 0), public_2023=r(x.public_2023, 0)) for a, x in rates.iterrows()}
    under65 = rates.loc[["〜29歳", "30〜39歳", "40〜49歳", "50〜59歳", "60〜64歳"]]
    out["decomposition_2003_2023"] = dict(change=r(d["change"], 0), composition=r(d["composition"], 0), rate=r(d["rate"], 0))
    # 65歳以上の割合（公営と全体）
    old = {}
    for y in (1983, 1993, 2003, 2013, 2023):
        s = ag[ag.year == y]
        tot = s[s.age == "総数"].iloc[0]
        o = s[s.age.str.contains("65|75|80|85") & ~s.age.str.contains("～64")]
        old[y] = dict(public=r(100 * o.public.sum() / tot.public, 1), all=r(100 * o.total.sum() / tot.total, 1))
    out["share65plus"] = old

    # 頑健性
    rob = []
    for (y0, y1) in [(1993, 2023), (2013, 2023)]:
        dd = decompose(ag, y0, y1, COARSE)
        rob.append(dict(check=f"1 期間 {y0}→{y1}年", change_pct=r(100 * (J.loc[y1, "public"] / J.loc[y0, "public"] - 1), 1),
                        regions_down=int((R[y1] < R[y0]).sum()), composition=r(dd["composition"], 0), rate=r(dd["rate"], 0)))
    rob.append(dict(check="2 分母を借家の総数に（2003→2023年）", change_pct=r(J.loc[2023, "public_share_rented"] - J.loc[2003, "public_share_rented"], 2),
                    regions_down=int((RR[2023] < RR[2003]).sum()), composition=None, rate=None))
    df = decompose(ag, 2003, 2023, FINE)
    rob.append(dict(check="3 分解の年齢区分を細かく（2003→2023年）", change_pct=None, regions_down=None,
                    composition=r(df["composition"], 0), rate=r(df["rate"], 0)))
    rob.append(dict(check="4 都道府県で数える（2003→2023年、割合が下がった県の数／47）", change_pct=None, regions_down=n_pref_down, composition=None, rate=None))
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rob.astype(object).where(rob.notna(), None).to_dict(orient="records")

    # 問い直し：家賃
    rt = rent.pivot(index="year", columns="kind", values=["all", "public"])
    rq = pd.DataFrame({"monthly_ratio": 100 * rt[("public", "monthly")] / rt[("all", "monthly")],
                       "tatami_ratio": 100 * rt[("public", "per_tatami")] / rt[("all", "per_tatami")],
                       "public_monthly": rt[("public", "monthly")], "all_monthly": rt[("all", "monthly")]})
    rq.round(3).to_csv(RES / "requestion_rent.csv")
    out["rent"] = {int(y): dict(monthly_ratio=r(x.monthly_ratio, 1), tatami_ratio=r(x.tatami_ratio, 1), public_monthly=r(x.public_monthly, 0), all_monthly=r(x.all_monthly, 0)) for y, x in rq.iterrows()}

    out["hypotheses"] = {
        "H1": dict(value=out["change_2003_2023_pct"], verdict="支持" if out["change_2003_2023_pct"] <= -15 else "外れ"),
        "H2": dict(value=n_down, verdict="支持" if n_down == 8 else "外れ"),
        "H3": dict(value={a: [r(x.rate_2003), r(x.rate_2023)] for a, x in under65.iterrows()},
                   verdict="支持" if (under65.rate_2023 < under65.rate_2003).all() else "外れ"),
        "H4": dict(value=[r(d["composition"], 0), r(d["rate"], 0)], verdict="支持" if abs(d["rate"]) > abs(d["composition"]) and d["rate"] < 0 else "外れ"),
    }
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in out if k not in ("japan",)}, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
