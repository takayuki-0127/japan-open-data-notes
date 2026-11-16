"""割合・減り方・頑健性・問い直しを計算し、results/ に書く（オフライン）。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
REGIONS = [("北海道", [1]), ("東北", range(2, 8)), ("関東", range(8, 15)), ("中部", range(15, 24)),
           ("近畿", range(24, 31)), ("中国", range(31, 36)), ("四国", range(36, 40)), ("九州・沖縄", range(40, 48))]
RNAME = [r for r, _ in REGIONS]
REG_OF = {p: r for r, ps in REGIONS for p in ps}
YEARS = [2010, 2015, 2020, 2025]


def r1(x):
    return round(float(x), 1)


def r2(x):
    return round(float(x), 2)


def by_region(df, cols, pref_col="pref"):
    d = df[df[pref_col] > 0].copy()
    d["region"] = d[pref_col].map(REG_OF)
    g = d.groupby(["year", "region"])[cols].sum().reset_index()
    nat = df[df[pref_col] == 0].assign(region="全国")[["year", "region"] + cols]
    return pd.concat([g, nat], ignore_index=True)


def spearman(a, b):
    return float(pd.Series(a).rank().corr(pd.Series(b).rank()))


def main():
    RES.mkdir(exist_ok=True)
    P = pd.read_csv(ROOT / "data" / "pref_3gen.csv")
    T = pd.read_csv(ROOT / "data" / "pref_type.csv")
    out = {}
    # 地方別の3世代世帯の割合
    R = by_region(P, ["households", "gen3", "single65", "couple65"])
    R["share"] = 100 * R.gen3 / R.households
    R["single65_share"] = 100 * R.single65 / R.households
    R["couple65_share"] = 100 * R.couple65 / R.households
    W = R.pivot(index="region", columns="year", values="share").reindex(RNAME + ["全国"])
    W.round(2).to_csv(RES / "region_share.csv")
    out["share"] = {k: {str(y): r2(W.loc[k, y]) for y in YEARS} for k in W.index}
    out["count"] = {k: {str(y): int(R[(R.region == k) & (R.year == y)].gen3.iloc[0]) for y in YEARS} for k in RNAME + ["全国"]}
    chg = (W[2025] / W[2010] - 1) * 100
    out["share_change_pct_2010_2025"] = {k: r1(v) for k, v in chg.items()}
    out["share_change_pt_2010_2025"] = {k: r2(v) for k, v in (W[2025] - W[2010]).items()}
    # 都道府県
    Pp = P[P.pref > 0].copy(); Pp["share"] = 100 * Pp.gen3 / Pp.households
    PW = Pp.pivot(index="pref", columns="year", values="share")
    PW["region"] = PW.index.map(REG_OF)
    PW.round(2).to_csv(RES / "pref_share.csv")
    rho = spearman(PW[2010], PW[2025] / PW[2010])
    rho20 = spearman(PW[2010], PW[2020] / PW[2010])
    out["pref_rho_2010_vs_ratio_2025"] = r2(rho)
    out["pref_share_2025_range"] = [r2(PW[2025].min()), r2(PW[2025].max())]
    out["pref_share_2010_range"] = [r2(PW[2010].min()), r2(PW[2010].max())]
    out["pref_all_declined_each_period"] = bool(((PW[2015] < PW[2010]) & (PW[2020] < PW[2015]) & (PW[2025] < PW[2020])).all())
    # 仮説
    nat = chg["全国"]
    every = all((W.loc[k, 2015] < W.loc[k, 2010]) and (W.loc[k, 2020] < W.loc[k, 2015]) and (W.loc[k, 2025] < W.loc[k, 2020]) for k in RNAME)
    h3 = W.loc["東北", 2025] / W.loc["関東", 2025]
    out["hypotheses"] = {
        "H1": dict(value=r1(nat), verdict="支持" if nat <= -40 else "外れ"),
        "H2": dict(value=every, verdict="支持" if every else "外れ"),
        "H3": dict(value=r2(h3), verdict="支持" if h3 >= 2 else "外れ"),
        "H4": dict(value=r2(rho), verdict="支持" if rho > 0 else "外れ"),
    }
    # 長い期間の目安（親・夫婦・子の型）
    T["typesum"] = T.type_c2p + T.type_c1p + T.type_cpo
    TR = by_region(T[T.series == "new"], ["households", "typesum"])
    TR["share"] = 100 * TR.typesum / TR.households
    TO = by_region(T[T.series == "old"], ["households", "typesum"])
    TO["share"] = 100 * TO.typesum / TO.households
    TW = TR.pivot(index="region", columns="year", values="share").reindex(RNAME + ["全国"])
    TOW = TO.pivot(index="region", columns="year", values="share").reindex(RNAME + ["全国"])
    TW.round(2).to_csv(RES / "region_typeshare_new.csv"); TOW.round(2).to_csv(RES / "region_typeshare_old.csv")
    out["typeshare_new"] = {k: {str(y): r2(TW.loc[k, y]) for y in TW.columns} for k in TW.index}
    out["typeshare_old_national"] = {str(y): r2(TOW.loc["全国", y]) for y in TOW.columns}
    out["type_vs_gen3_2025"] = r1(100 * T[(T.series == "new") & (T.year == 2025) & (T.pref == 0)].typesum.iloc[0] / P[(P.year == 2025) & (P.pref == 0)].gen3.iloc[0])
    # 頑健性
    rb = []
    rb.append(dict(check="0 主：3世代世帯の割合（2010→2025年）", result=f"全国 {W.loc['全国',2010]:.2f}%→{W.loc['全国',2025]:.2f}%（{nat:+.1f}%）、8地方すべて毎回低下={every}、東北÷関東 {h3:.2f}倍、順位相関 {rho:+.2f}"))
    every_t = all(all(TW.loc[k, y2] < TW.loc[k, y1] for y1, y2 in zip(TW.columns[:-1], TW.columns[1:])) for k in RNAME)
    rb.append(dict(check="1 親・夫婦・子の型で（1995→2025年、5年ごと）", result=f"全国 {TW.loc['全国',1995]:.2f}%→{TW.loc['全国',2025]:.2f}%（{100*(TW.loc['全国',2025]/TW.loc['全国',1995]-1):+.1f}%）、8地方すべて毎回低下={every_t}、2025年の東北÷関東 {TW.loc['東北',2025]/TW.loc['関東',2025]:.2f}倍"))
    cc = {k: 100 * (out['count'][k]['2025'] / out['count'][k]['2010'] - 1) for k in RNAME + ['全国']}
    rb.append(dict(check="2 世帯数で（2010→2025年）", result="、".join(f"{k} {v:+.1f}%" for k, v in cc.items())))
    rb.append(dict(check="3 H4 を2010→2020年で", result=f"順位相関 {rho20:+.2f}"))
    no_oki = P[(P.pref >= 40) & (P.pref <= 46)].groupby("year")[["gen3", "households"]].sum()
    med = Pp[Pp.year == 2025].assign(region=lambda d: d.pref.map(REG_OF)).groupby("region").share.median()
    rb.append(dict(check="4 地方のまとめ方（九州から沖縄を除く／都道府県の中央値）", result=f"九州（沖縄を除く）2025年 {100*no_oki.gen3[2025]/no_oki.households[2025]:.2f}%（2010年 {100*no_oki.gen3[2010]/no_oki.households[2010]:.2f}%）、中央値での東北÷関東 {med['東北']/med['関東']:.2f}倍"))
    imp = P[P.year == 2025].copy()
    ri = by_region(imp.rename(columns={"gen3": "g", "households": "h"}).assign(gen3=imp.gen3_imputed, households=imp.households_imputed), ["gen3", "households"])
    ri["share"] = 100 * ri.gen3 / ri.households
    si = ri.set_index("region").share
    rb.append(dict(check="5 2025年を不詳補完値で", result=f"全国 {si['全国']:.2f}%（2010年比 {100*(si['全国']/W.loc['全国',2010]-1):+.1f}%）、東北÷関東 {si['東北']/si['関東']:.2f}倍"))
    pd.DataFrame(rb).to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rb
    # 問い直し：高齢者の暮らし方（原数値のそろう2010→2020年）
    S = R[R.year.isin([2010, 2020])].pivot(index="region", columns="year", values=["share", "single65_share", "couple65_share"]).reindex(RNAME + ["全国"])
    S.columns = [f"{a}_{b}" for a, b in S.columns]
    S.round(2).to_csv(RES / "requestion_elderly.csv")
    out["requestion"] = {k: {c: r2(v) for c, v in S.loc[k].items()} for k in S.index}
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(W.round(2)); print(json.dumps(out["hypotheses"], ensure_ascii=False)); print(pd.DataFrame(rb).to_string()); print(S.round(2)); print(TW.round(2))


if __name__ == "__main__":
    main()
