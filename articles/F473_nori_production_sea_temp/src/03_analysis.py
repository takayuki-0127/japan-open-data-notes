"""主な分析：H1〜H4 と頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "data"; R = ROOT / "results"
S = pd.read_csv(D / "nori_by_pref_season.csv")
SST = pd.read_csv(D / "jma_sst_area_anomaly.csv")
ST = pd.read_csv(D / "jma_station_monthly_temp.csv")
LG = pd.read_csv(D / "nori_national_long.csv")
MAJOR = ["宮城", "千葉", "愛知", "三重", "兵庫", "岡山", "香川", "福岡", "佐賀", "熊本"]
COMPLETE5 = ["兵庫", "岡山", "香川", "佐賀", "熊本"]
GROUP = {"宮城": "東北", "千葉": "東京湾", "愛知": "伊勢・三河湾", "三重": "伊勢・三河湾", "兵庫": "瀬戸内海", "岡山": "瀬戸内海",
         "香川": "瀬戸内海", "福岡": "有明海", "佐賀": "有明海", "熊本": "有明海"}
G_ORDER = ["東北", "東京湾", "伊勢・三河湾", "瀬戸内海", "有明海"]
AREA = {"宮城": "K", "千葉": "M", "愛知": "N", "三重": "N", "兵庫": "N", "岡山": "N", "香川": "N", "福岡": "C", "佐賀": "C", "熊本": "C"}
STATION = {"宮城": "仙台", "千葉": "千葉", "愛知": "名古屋", "三重": "名古屋", "兵庫": "高松", "岡山": "高松", "香川": "高松",
           "福岡": "佐賀", "佐賀": "佐賀", "熊本": "佐賀"}
E0, E1 = list(range(2004, 2009)), list(range(2019, 2024))
M = {}

# 欠けた値（秘匿）を埋める
P = S[S.pref.isin(MAJOR)].copy().sort_values(["pref", "season"]).reset_index(drop=True)
P["imputed"] = ""
for p, d in P.groupby("pref"):
    ratio = (d.season_t / d.ita_season).where(d.season_t.notna() & (d.ita_season > 0))
    for i in d.index[d.season_t.isna()]:
        s = P.loc[i, "season"]
        near = ratio.dropna(); near = near[(P.loc[near.index, "season"] - s).abs() <= 2]
        if pd.notna(P.loc[i, "ita_season"]) and len(near):
            P.loc[i, "season_t"] = P.loc[i, "ita_season"] * near.mean(); P.loc[i, "imputed"] = "枚数×比"
    d = P[P.pref == p]
    if d.season_t.isna().any():
        filled = d.set_index("season").season_t.interpolate(method="index")
        for i in d.index[d.season_t.isna()]:
            P.loc[i, "season_t"] = filled.loc[P.loc[i, "season"]]; P.loc[i, "imputed"] = "直線"
assert P.season_t.notna().all()
P[P.imputed != ""][["pref", "season", "season_t", "imputed"]].to_csv(R / "imputed.csv", index=False, float_format="%.1f")
P["group"] = P.pref.map(GROUP)

# 海面水温（秋）と気温（10〜11月）の平年差
sst = SST.pivot(index="year", columns="area", values="autumn")
P["sst"] = [sst.loc[s, AREA[p]] for p, s in zip(P.pref, P.season)]
on = ST[ST.month.isin([10, 11])].groupby(["station", "year"]).temp.mean().unstack(0)
on_norm = on.loc[1991:2020].mean()
P["air"] = [on.loc[s, STATION[p]] - on_norm[STATION[p]] for p, s in zip(P.pref, P.season)]
P["logt"] = np.log(P.season_t)
P.to_csv(R / "panel_major.csv", index=False, float_format="%.5f")

# H1：全国
nat = S[S.pref == "全国"].set_index("season").season_t
a0, a1 = nat.loc[E0].mean(), nat.loc[E1].mean()
M["H1"] = {"avg_2004_08": float(a0), "avg_2019_23": float(a1), "change_pct": float(100 * (a1 / a0 - 1)),
           "s2004": float(nat.loc[2004]), "s2022": float(nat.loc[2022]), "s2023": float(nat.loc[2023]), "min_season": int(nat.idxmin())}
M["H1_verdict"] = "支持" if M["H1"]["change_pct"] <= -30 else "外れ"
lg = LG.set_index("year").nori_t
M["long"] = {"peak_year": int(lg.idxmax()), "peak_t": float(lg.max()), "y1956": float(lg.loc[1956]), "y2024": float(lg.loc[2024]),
             "y2004": float(lg.loc[2004]), "last_year_at_or_below_2024_level": int(lg[(lg <= lg.loc[2024]) & (lg.index < 2024)].index.max())}

# H2：産地のまとまり
gs = P.groupby(["group", "season"]).season_t.sum().unstack(0)[G_ORDER]
gs["その他（全国−5産地）"] = nat - gs.sum(axis=1)
gs.to_csv(R / "groups_season.csv", float_format="%.1f")
rows = []
dn = a1 - a0
for g in gs.columns:
    b0, b1 = gs.loc[E0, g].mean(), gs.loc[E1, g].mean()
    rows.append(dict(group=g, avg_2004_08=b0, avg_2019_23=b1, change_t=b1 - b0, change_pct=100 * (b1 / b0 - 1), share_of_national_drop=100 * (b1 - b0) / dn,
                     share_2004_08=100 * b0 / a0, share_2019_23=100 * b1 / a1))
G = pd.DataFrame(rows); G.to_csv(R / "h2_groups.csv", index=False, float_format="%.3f")
M["H2"] = G.set_index("group").to_dict("index")
M["H2_verdict"] = "支持" if M["H2"]["瀬戸内海"]["change_pct"] < M["H2"]["有明海"]["change_pct"] else "外れ"


# H3・H4：パネル
def fit(d, x=("sst",), trend="common"):
    d = d.reset_index(drop=True)
    X = pd.DataFrame({c: d[c] for c in x})
    F = pd.get_dummies(d.pref, prefix="p", dtype=float)
    if trend == "common":
        X["t"] = d.season - 2013.5
    elif trend == "pref":
        for p in sorted(d.pref.unique()):
            X[f"t_{p}"] = (d.season - 2013.5) * (d.pref == p)
    X = pd.concat([X, F], axis=1)
    r = sm.OLS(d["logt"], X).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.season, sort=True)[0]})
    return r


def co(r, n):
    ci = r.conf_int().loc[n]
    return dict(b=float(r.params[n]), lo=float(ci[0]), hi=float(ci[1]), pct=float(100 * (np.exp(r.params[n]) - 1)), n=int(r.nobs))


r_main = fit(P); r_tonly = fit(P, x=())
M["H3"] = co(r_main, "sst")
M["H3_verdict"] = "支持" if M["H3"]["hi"] < 0 else "外れ"
t0, t1 = co(r_tonly, "t"), co(r_main, "t")
M["H4"] = {"trend_without_sst": t0, "trend_with_sst": t1, "remaining_share": t1["b"] / t0["b"]}
M["H4_verdict"] = "支持" if t1["b"] / t0["b"] >= 0.5 else "外れ"
M["sst_trend_per_year"] = {a: float(np.polyfit(range(2004, 2024), sst.loc[2004:2023, a].values, 1)[0]) for a in ["C", "N", "M", "K"]}

rob = [dict(name="主（10県、秋の海面水温、共通の年の直線）", **co(r_main, "sst"))]
rob.append(dict(name="10〜11月の気温（近くの気象台）", **co(fit(P, x=("air",)), "air")))
rob.append(dict(name="埋めた値を使わない5県", **co(fit(P[P.pref.isin(COMPLETE5)]), "sst")))
rob.append(dict(name="2022・2023年の期を除く", **co(fit(P[P.season <= 2021]), "sst")))
rob.append(dict(name="県ごとの年の直線", **co(fit(P, trend="pref"), "sst")))
rob = pd.DataFrame(rob); rob.to_csv(R / "robustness.csv", index=False, float_format="%.4f")
M["robustness"] = rob.to_dict("records")
# 頑健性の H4（2022・2023を除く）
M["H4_excl_2223"] = fit(P[P.season <= 2021])["t"] if False else co(fit(P[P.season <= 2021]), "t")["b"] / co(fit(P[P.season <= 2021], x=()), "t")["b"]
# レビューで足した確かめ：気温（10〜11月）を入れたとき、年の直線がどれだけ残るか。気温そのものの上がり方
r_air = fit(P, x=("air",))
_pa = P.groupby("season").air.mean()
M["review_air"] = {"trend_with_air": co(r_air, "t"), "remaining_share_air": co(r_air, "t")["b"] / t0["b"],
                   "air_trend_per_year_mean10": float(np.polyfit(_pa.index.values, _pa.values, 1)[0])}
M["national_season"] = {int(k): float(v) for k, v in nat.items()}
json.dump(M, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps({k: M[k] for k in ["H1", "H1_verdict", "H2_verdict", "H3", "H3_verdict", "H4", "H4_verdict", "long", "sst_trend_per_year", "H4_excl_2223"]}, ensure_ascii=False, indent=0))
print(G.round(1).to_string()); print(rob.round(3).to_string()); print(pd.read_csv(R / "imputed.csv").to_string())
