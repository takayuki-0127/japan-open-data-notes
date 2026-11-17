"""用途の割合の推移、ブロック別、都道府県の相関、頑健性、問い直し。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
BLOCKS = ["北海道", "東北", "関東", "北陸", "東山", "東海", "近畿", "中国", "四国", "九州", "沖縄"]
SPANS = {"前（2010〜12年）": (2010, 2012), "中（2015〜19年）": (2015, 2019), "後（2021〜23年）": (2021, 2023)}
GROUPS = ["housing", "public", "factory", "commerce", "agri_facility", "parking", "quarry", "renew_etc", "forest", "unknown"]
GJ = {"housing": "住宅用地", "public": "公的施設用地", "factory": "工場用地", "commerce": "商業サービス等用地", "agri_facility": "農林漁業用施設",
      "parking": "駐車場・資材置場", "quarry": "土石等採取用地", "renew_etc": "再エネ等（再エネ発電設備＋その他）", "forest": "植林", "unknown": "分類不能・不明"}


def r(x, k=2):
    return None if x is None or pd.isna(x) else round(float(x), k)


def wide(df):
    w = df.pivot_table(index=["year", "level", "region"], columns="use", values="ha", aggfunc="first").reset_index()
    w["renewable"] = w["renewable"].fillna(0) if "renewable" in w else 0
    w["renew_etc"] = w["renewable"] + w["ob_other"]
    for g in GROUPS:
        w["s_" + g] = 100 * w[g] / w["total"]
    w["s_renewable"] = 100 * w["renewable"] / w["total"]
    return w


def span_mean(w, span, level, region=None, col="s_renew_etc", by_area=False):
    s = w[(w.level == level) & w.year.between(*span)]
    if region is not None:
        s = s[s.region == region]
    if by_area:  # 面積の合計から割合を出す
        return s.groupby("region")[[c.replace("s_", "") for c in [col]] + ["total"]].sum()
    return s.groupby("region")[col].mean()


def main():
    df = pd.read_csv(DATA / "conversion_long.csv")
    w = wide(df)
    w.round(4).to_csv(RES / "wide_table.csv", index=False)
    N = w[w.level == "national"].set_index("year")
    out = {}
    out["national_by_year"] = {int(y): dict(total=r(x.total, 1), housing=r(x.housing, 1), renewable=r(x.renewable, 1), renew_etc=r(x.renew_etc, 1),
                                            s_housing=r(x.s_housing, 1), s_renew_etc=r(x.s_renew_etc, 1), s_renewable=r(x.s_renewable, 1),
                                            s_parking=r(x.s_parking, 1)) for y, x in N.iterrows()}
    # 期間ごとの全国の割合（面積を足してから割る）
    shares = {}
    for sn, sp in SPANS.items():
        s = N.loc[sp[0]:sp[1]]
        shares[sn] = {GJ[g]: r(100 * s[g].sum() / s.total.sum(), 2) for g in GROUPS}
        shares[sn]["総数（年平均ha）"] = r(s.total.mean(), 1)
    out["national_span_shares"] = shares
    pd.DataFrame(shares).to_csv(RES / "national_span_shares.csv")

    # 合計の確かめ：都道府県の和と全国
    P = w[w.level == "pref"]
    chk = (P.groupby("year").total.sum() / N.total - 1) * 100
    out["pref_sum_vs_national_pct"] = dict(max_abs=r(chk.abs().max(), 3))

    # ブロック
    B = w[w.level == "block"]
    bt = []
    for b in BLOCKS:
        row = dict(block=b)
        for sn, sp in SPANS.items():
            s = B[(B.region == b) & B.year.between(*sp)]
            row[sn + "_renew_etc"] = 100 * s.renew_etc.sum() / s.total.sum()
            row[sn + "_housing"] = 100 * s.housing.sum() / s.total.sum()
            row[sn + "_total"] = s.total.mean()
        bt.append(row)
    bt = pd.DataFrame(bt)
    bt.round(3).to_csv(RES / "block_shares.csv", index=False)
    k0, k1 = "前（2010〜12年）_renew_etc", "中（2015〜19年）_renew_etc"
    n_up = int((bt[k1] > bt[k0]).sum())
    out["blocks"] = {x.block: {"前": r(x[k0], 1), "中": r(x[k1], 1), "後": r(x["後（2021〜23年）_renew_etc"], 1),
                               "住宅_前": r(x["前（2010〜12年）_housing"], 1), "住宅_後": r(x["後（2021〜23年）_housing"], 1)} for _, x in bt.iterrows()}

    # 都道府県の相関（中の期間）
    pm = P[P.year.between(*SPANS["中（2015〜19年）"])].groupby("region")[["renew_etc", "housing", "total"]].sum()
    pm["s_renew"] = 100 * pm.renew_etc / pm.total; pm["s_housing"] = 100 * pm.housing / pm.total
    pm.round(3).to_csv(RES / "pref_mid_period.csv")
    c, p = stats.pearsonr(pm.s_renew, pm.s_housing)
    cs, ps = stats.spearmanr(pm.s_renew, pm.s_housing)
    out["pref_corr_mid"] = dict(pearson=r(c, 3), p=r(p, 5), spearman=r(cs, 3), p_s=r(ps, 5), n=len(pm),
                                renew_min=r(pm.s_renew.min(), 1), renew_max=r(pm.s_renew.max(), 1))

    # 頑健性
    rob = []
    for y0, y1, y2 in [(2011, 2017, 2023)]:
        rob.append(dict(check="1 単年（2011・2017・2023年）", renew_etc=f"{N.loc[y0,'s_renew_etc']:.1f}→{N.loc[y1,'s_renew_etc']:.1f}→{N.loc[y2,'s_renew_etc']:.1f}",
                        housing=f"{N.loc[y0,'s_housing']:.1f}→{N.loc[y2,'s_housing']:.1f}",
                        blocks_up=int(sum(B[(B.region == b) & (B.year == y1)].s_renew_etc.iloc[0] > B[(B.region == b) & (B.year == y0)].s_renew_etc.iloc[0] for b in BLOCKS))))
    mid = N.loc[2015:2019]; late = N.loc[2021:2023]
    rob.append(dict(check="2 再エネ発電設備だけ（中→後、%）", renew_etc=f"{100*mid.renewable.sum()/mid.total.sum():.1f}→{100*late.renewable.sum()/late.total.sum():.1f}", housing="—", blocks_up=None))
    e = N.loc[2010:2012]
    rob.append(dict(check="3 面積（年平均ha、前→中→後）", renew_etc=f"{e.renew_etc.mean():.0f}→{mid.renew_etc.mean():.0f}→{late.renew_etc.mean():.0f}",
                    housing=f"{e.housing.mean():.0f}→{late.housing.mean():.0f}", blocks_up=int((B[B.year.between(2015, 2019)].groupby('region').renew_etc.mean() > B[B.year.between(2010, 2012)].groupby('region').renew_etc.mean()).sum())))
    rob.append(dict(check="4 H4 をスピアマンで", renew_etc=f"ρ = {cs:.2f}", housing="—", blocks_up=None))
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)
    out["robustness"] = rob.astype(object).where(rob.notna(), None).to_dict(orient="records")

    # 問い直し：前→中で、どの用途の割合が下がったか（割合の差、ポイント）
    d = {GJ[g]: r(shares["中（2015〜19年）"][GJ[g]] - shares["前（2010〜12年）"][GJ[g]], 2) for g in GROUPS}
    d2 = {GJ[g]: r(shares["後（2021〜23年）"][GJ[g]] - shares["中（2015〜19年）"][GJ[g]], 2) for g in GROUPS}
    out["requestion_share_change"] = {"前→中": d, "中→後": d2}
    # 面積の差（ha/年）
    GJ2 = {**GJ, "total": "総数"}
    out["requestion_area_change"] = {GJ2[g]: dict(early=r(e[g].mean(), 0), mid=r(mid[g].mean(), 0), late=r(late[g].mean(), 0)) for g in GROUPS + ["total"] if g in N}
    pd.DataFrame({"前→中": d, "中→後": d2}).to_csv(RES / "requestion_share_change.csv")

    S = shares
    out["hypotheses"] = {
        "H1": dict(value=[S["前（2010〜12年）"][GJ["renew_etc"]], S["中（2015〜19年）"][GJ["renew_etc"]]],
                   verdict="支持" if S["中（2015〜19年）"][GJ["renew_etc"]] - S["前（2010〜12年）"][GJ["renew_etc"]] >= 10 else "外れ"),
        "H2": dict(value=[S["前（2010〜12年）"][GJ["housing"]], S["後（2021〜23年）"][GJ["housing"]]],
                   verdict="支持" if S["後（2021〜23年）"][GJ["housing"]] < S["前（2010〜12年）"][GJ["housing"]] else "外れ"),
        "H3": dict(value=n_up, verdict="支持" if n_up >= 9 else "外れ"),
        "H4": dict(value=r(c, 3), verdict="支持" if c < -0.3 else "外れ"),
    }
    (RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "national_by_year"}, ensure_ascii=False, indent=0))
    print(N[["total", "housing", "renewable", "ob_other", "renew_etc", "s_renew_etc", "s_housing"]].round(1).to_string())


if __name__ == "__main__":
    main()
