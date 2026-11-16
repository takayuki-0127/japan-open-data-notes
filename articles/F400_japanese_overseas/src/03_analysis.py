"""増減・寄与・頑健性・問い直しを計算し、results/ に書く（オフライン）。"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
REGIONS = ["アジア", "大洋州", "北米", "中米", "南米", "西欧", "東欧・旧ソ連", "中東", "アフリカ", "南極"]
SUPPRESSED = ["ウクライナ", "アフガニスタン", "シリア"]


def r1(x):
    return round(float(x), 1)


def contrib(a, b, key, col):
    """a→b の col の差を key ごとに出し、全体の差に対する割合（%）をつける。"""
    m = a.groupby(key)[col].sum().to_frame("a").join(b.groupby(key)[col].sum().to_frame("b"), how="outer").fillna(0)
    m["diff"] = m.b - m.a
    m["share_of_change"] = 100 * m["diff"] / m["diff"].sum()
    return m


def main():
    RES.mkdir(exist_ok=True)
    N = pd.read_csv(ROOT / "data" / "national.csv").set_index("year")
    N["perm_share"] = 100 * N.perm / N.total
    N["female_share"] = 100 * N.total_f / N.total
    N["female_share_long"] = 100 * N.long_f / N.long
    N["female_share_perm"] = 100 * N.perm_f / N.perm
    N.round(2).to_csv(RES / "national.csv")
    C = pd.read_csv(ROOT / "data" / "country.csv")
    chk = pd.read_csv(ROOT / "data" / "check_region_sums.csv")
    a, b = C[C.year == 2019], C[C.year == 2025]
    out = {}
    pk = int(N.total.idxmax())
    out["peak_year"] = pk
    out["levels"] = {str(y): dict(total=int(N.total[y]), long=int(N.long[y]), perm=int(N.perm[y]), perm_share=r1(N.perm_share[y]),
                                  female_share=r1(N.female_share[y]), female_share_long=r1(N.female_share_long[y]) if pd.notna(N.female_share_long[y]) else None,
                                  female_share_perm=r1(N.female_share_perm[y]) if pd.notna(N.female_share_perm[y]) else None)
                     for y in (1991, 2000, 2006, 2015, 2018, 2019, 2020, 2022, 2024, 2025)}
    out["chg_2019_2025"] = {k: r1(100 * (N[k][2025] / N[k][2019] - 1)) for k in ("total", "long", "perm")}
    out["perm_up_every_year_since_2003"] = bool((N.perm.loc[2003:].diff().dropna() > 0).all())
    out["long_peak_year"] = int(N.long.idxmax())
    # 地域別
    rows = []
    for col in ("long", "perm", "total"):
        m = contrib(a, b, "region", col).reindex(REGIONS)
        for reg, r in m.iterrows():
            rows.append(dict(kind=col, region=reg, n2019=r.a, n2025=r.b, diff=r["diff"], share_of_change=round(r.share_of_change, 1)))
    R = pd.DataFrame(rows)
    R.to_csv(RES / "region_2019_2025.csv", index=False, float_format="%.1f")
    rl = R[R.kind == "long"].set_index("region"); rp = R[R.kind == "perm"].set_index("region")
    out["region_long"] = {k: dict(n2019=int(v.n2019), n2025=int(v.n2025), diff=int(v["diff"]), share=v.share_of_change) for k, v in rl.iterrows()}
    out["region_perm"] = {k: dict(n2019=int(v.n2019), n2025=int(v.n2025), diff=int(v["diff"]), share=v.share_of_change) for k, v in rp.iterrows()}
    # 国別（長期滞在者の減少への寄与）
    names19, names25 = set(a.country), set(b.country)
    out["unmatched_2019"] = sorted(names19 - names25); out["unmatched_2025"] = sorted(names25 - names19)
    cl = contrib(a, b, "country", "long").sort_values("diff")
    reg_of = pd.concat([a, b]).drop_duplicates("country", keep="last").set_index("country").region
    cl["region"] = reg_of.reindex(cl.index)
    cl.round(1).to_csv(RES / "country_long_2019_2025.csv", float_format="%.1f")
    out["country_long_top"] = [dict(country=k, region=v.region, n2019=int(v.a), n2025=int(v.b), diff=int(v["diff"]), share=r1(v.share_of_change)) for k, v in cl.head(10).iterrows()]
    out["country_long_increase"] = [dict(country=k, diff=int(v["diff"])) for k, v in cl.tail(5)[::-1].iterrows()]
    cp = contrib(a, b, "country", "perm").sort_values("diff", ascending=False)
    out["country_perm_top"] = [dict(country=k, n2019=int(v.a), n2025=int(v.b), diff=int(v["diff"]), share=r1(v.share_of_change)) for k, v in cp.head(6).iterrows()]
    china = r1(cl.loc["中国", "share_of_change"])
    asia = rl.loc["アジア", "share_of_change"]
    h4 = r1(rp.loc[["北米", "大洋州", "西欧"], "share_of_change"].sum())
    drop = 100 * (1 - N.total[2025] / N.total[pk])
    out["hypotheses"] = {
        "H1": dict(value=[pk, r1(-drop)], verdict="支持" if pk == 2019 and drop >= 5 else "外れ"),
        "H2": dict(value=asia, verdict="支持" if asia >= 50 else "外れ"),
        "H3": dict(value=china, verdict="支持" if china >= 30 else "外れ"),
        "H4": dict(value=h4, verdict="支持" if h4 >= 70 else "外れ"),
    }
    # 頑健性
    rb = [dict(check="0 主（2019→2025年）", asia_share_long=asia, china_share_long=china, n3_share_perm=h4, note="")]
    a2 = a[~a.country.isin(SUPPRESSED)]
    l2 = contrib(a2, b, "region", "long"); c2 = contrib(a2, b, "country", "long"); p2 = contrib(a2, b, "region", "perm")
    rb.append(dict(check="1 2025年に非公表の3か国を2019年からも除く", asia_share_long=r1(l2.share_of_change["アジア"]), china_share_long=r1(c2.share_of_change["中国"]),
                   n3_share_perm=r1(p2.share_of_change[["北米", "大洋州", "西欧"]].sum()), note=f"除いた2019年の人数 {int(a.total.sum() - a2.total.sum())}人"))
    pk2 = 100 * (N.total[2024] / N.total[2018] - 1)
    rb.append(dict(check="2 総数を2018→2024年で", asia_share_long=None, china_share_long=None, n3_share_perm=None,
                   note=f"総数 {pk2:+.1f}%、長期滞在者 {100*(N.long[2024]/N.long[2018]-1):+.1f}%、永住者 {100*(N.perm[2024]/N.perm[2018]-1):+.1f}%"))
    ok = all((chk.table_total == chk.sum_total) & (chk.table_long == chk.sum_long) & (chk.table_perm == chk.sum_perm))
    rb.append(dict(check="3 国の合計と表の地域別総数", asia_share_long=None, china_share_long=None, n3_share_perm=None, note="すべて一致" if ok else "不一致あり"))
    G = pd.read_csv(ROOT / "data" / "region_2006_2015.csv")
    g15 = G[G.year == 2015].pivot(index="region", columns="kind", values="n").reindex(REGIONS)
    g25 = b.groupby("region")[["long", "perm"]].sum().reindex(REGIONS)
    dl = g25.long - g15.long; dp = g25.perm - g15.perm
    rb.append(dict(check="4 2015→2025年で（地域別）", asia_share_long=r1(100 * dl["アジア"] / dl.sum()), china_share_long=None,
                   n3_share_perm=r1(100 * dp[["北米", "大洋州", "西欧"]].sum() / dp.sum()),
                   note=f"長期滞在者 {int(g15.long.sum())}→{int(g25.long.sum())}、永住者 {int(g15.perm.sum())}→{int(g25.perm.sum())}"))
    pd.DataFrame(rb).to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rb
    out["region_2015_2025"] = {reg: dict(long2015=int(g15.long[reg]), long2025=int(g25.long[reg]), perm2015=int(g15.perm[reg]), perm2025=int(g25.perm[reg])) for reg in REGIONS}
    # 問い直し：女性の割合
    out["requestion"] = {str(y): dict(all=r1(N.female_share[y]), long=r1(N.female_share_long[y]) if pd.notna(N.female_share_long[y]) else None,
                                      perm=r1(N.female_share_perm[y])) for y in (1991, 2000, 2010, 2019, 2025)}
    w19 = N.long[2019] / N.total[2019]
    fixed = w19 * N.female_share_long[2025] + (1 - w19) * N.female_share_perm[2025]
    out["requestion_mix"] = dict(actual_2019=r1(N.female_share[2019]), actual_2025=r1(N.female_share[2025]), fixed_mix_2025=r1(fixed),
                                 within_pt=r1(fixed - N.female_share[2019]), mix_pt=r1(N.female_share[2025] - fixed))
    out["female_perm_2025"] = int(N.perm_f[2025]); out["female_total_2025"] = int(N.total_f[2025])
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("peak_year", "chg_2019_2025", "hypotheses", "unmatched_2019", "unmatched_2025", "long_peak_year", "perm_up_every_year_since_2003")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
