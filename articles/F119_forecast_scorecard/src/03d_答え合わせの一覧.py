"""出生数（F55）と平均寿命（F86）の答え合わせ、まだ答えが出ていない予測（F13・F18・F55 の年間）の一覧

出生数：F55 の予測は「確定数」ベース。2026年はまだ「概数」しかないので、2025年の確定数÷概数の比で確定数ベースに直す。
直し方を3通り（月ごとの比／1〜5月合計の比／直さない）で比べる。
"""
import json
import numpy as np, pandas as pd
from f119common import ART, ROOT

RES = ROOT / "results"; RAW = ROOT / "data" / "raw"
z = np.load(RES / "births_2026_sims.npz")
g = pd.read_csv(RAW / "births_geppo_gaisu_2026.csv")
m55 = pd.read_csv(ART / "F55_births_bsts" / "data" / "monthly.csv", parse_dates=["date"]).set_index("date")
k25 = m55.loc["2025-01":"2025-05", "births"].values           # 2025年1〜5月の確定数
k25_year = m55.loc["2025", "births"].sum()
ratio_m = k25 / g.births_2025_gaisu.values                     # 月ごとの 確定÷概数
ratio_c = k25.sum() / g.births_2025_gaisu.sum()
variants = {"月ごとの比で直す": g.births_2026_gaisu.values * ratio_m,
            "1〜5月合計の比で直す（基本）": g.births_2026_gaisu.values * ratio_c,
            "直さない（概数のまま）": g.births_2026_gaisu.values.astype(float)}
rows = []
for mname in ("bsts", "sarima"):
    s = z[mname][:5]                                           # 2026年1〜5月 × 4000本
    tot = s.sum(0)
    for vname, act in variants.items():
        A = act.sum()
        rows.append({"model": mname.upper(), "直し方": vname, "実績(1〜5月)": A, "予測の中央値": np.median(tot),
                     "95%下": np.quantile(tot, .025), "95%上": np.quantile(tot, .975),
                     "80%下": np.quantile(tot, .1), "80%上": np.quantile(tot, .9),
                     "誤差(%)": 100 * (np.median(tot) - A) / A, "実績の分位(%)": 100 * (tot < A).mean(),
                     "予測の前年比(%)": 100 * (np.median(tot) / k25.sum() - 1),
                     "実績の前年比(%)": 100 * (A / k25.sum() - 1)})
B = pd.DataFrame(rows)
B.to_csv(RES / "births_jan_may_2026.csv", index=False)
print(B.round(2).to_string())
# 月ごと（基本の直し方）
mm = []
act = variants["1〜5月合計の比で直す（基本）"]
for i, mon in enumerate(g.month):
    for mname in ("bsts", "sarima"):
        s = z[mname][i]
        mm.append({"month": mon, "model": mname.upper(), "実績(確定ベースに直した値)": act[i], "中央値": np.median(s),
                   "95%下": np.quantile(s, .025), "95%上": np.quantile(s, .975), "実績の分位(%)": 100 * (s < act[i]).mean(),
                   "月ごとの比で直した実績": variants["月ごとの比で直す"][i]})
pd.DataFrame(mm).to_csv(RES / "births_monthly_2026.csv", index=False)
# 参考：F55 の年間予測と2025年の確定数
c55 = pd.read_csv(ART / "F55_births_bsts" / "results" / "C_future_annual.csv")

# 平均寿命
lt = pd.read_csv(RAW / "life_table_2025.csv")
fc = pd.read_csv(ART / "F86_lee_carter_e0" / "results" / "forecast_e0.csv")
jmd = pd.read_csv(ART / "F86_lee_carter_e0" / "data" / "e0_jmd.csv").set_index("year")
er = []
for _, r in lt.iterrows():
    f = fc[(fc.sex == r.sex) & (fc.year == 2025)].iloc[0]
    j24, j14 = jmd.loc[2024, r.sex], jmd.loc[2014, r.sex]
    trend = j24 + (j24 - j14) / 10
    er.append({"sex": r.sex, "実績2025（簡易生命表）": r.e0_2025, "Lee–Carter 中央": f.p50, "95%下": f.p025, "95%上": f.p975,
               "80%下": f.p10, "80%上": f.p90, "誤差_LC": f.p50 - r.e0_2025,
               "前年のまま": j24, "誤差_前年のまま": j24 - r.e0_2025,
               "過去10年の伸びを延ばす": trend, "誤差_10年の伸び": trend - r.e0_2025,
               "JMDと簡易生命表の差（2024年）": j24 - r.e0_2024,
               "65歳 実績": r.e65_2025, "65歳 LC": f.e65_center})
E = pd.DataFrame(er)
E.to_csv(RES / "e0_2025_check.csv", index=False)
print(E.round(2).T)

# まだ答えが出ていない予測
f13 = pd.read_csv(ART / "F13_unemployment_forecast" / "results" / "forecasts.csv")
f13 = f13[f13.label == "base"].set_index("origin")
f18 = pd.read_csv(ART / "F18_nowcast_dfm" / "results" / "nowcast_2026Q3.csv")
pend = [
    {"記事": "F13 失業率", "予測": "2026年9月の完全失業率（6月起点の3か月先、4モデルの平均）",
     "値": round(f13.loc["2026-06-01", "u_T"] + f13.loc["2026-06-01", "ENS_3"], 2), "単位": "%",
     "答えが出る時期": "2026年10月末（労働力調査 9月分）"},
    {"記事": "F13 失業率", "予測": "2026年10月の完全失業率（7月起点の3か月先）",
     "値": round(f13.loc["2026-07-01", "u_T"] + f13.loc["2026-07-01", "ENS_3"], 2), "単位": "%",
     "答えが出る時期": "2026年11月末（同 10月分）"},
    {"記事": "F18 ナウキャスト", "予測": "2026年7-9月期の実質GDP前期比（8月末時点、DFM）",
     "値": float(f18.iloc[-1]["DFM"]), "単位": "%", "答えが出る時期": "2026年11月中旬（1次速報）"},
    {"記事": "F55 出生数", "予測": "2026年の出生数（BSTS の中央値、確定数ベース）",
     "値": round(float(c55[(c55.model == "BSTS") & (c55.year == 2026)]["median"].iloc[0])), "単位": "人",
     "答えが出る時期": "2027年6月ごろ（概数）・9月ごろ（確定数）"},
    {"記事": "F86 平均寿命", "予測": "2026年の平均寿命（男・女、Lee–Carter の中央）",
     "値": f"{fc[(fc.sex=='男')&(fc.year==2026)].p50.iloc[0]:.2f}・{fc[(fc.sex=='女')&(fc.year==2026)].p50.iloc[0]:.2f}",
     "単位": "年", "答えが出る時期": "2027年7月ごろ（簡易生命表）"},
]
pd.DataFrame(pend).to_csv(RES / "pending_forecasts.csv", index=False)
print(pd.DataFrame(pend).to_string())
json.dump({"k25_jan_may": int(k25.sum()), "k25_year": int(k25_year), "ratio_c": ratio_c,
           "ratio_m": ratio_m.round(4).tolist(), "rhat": float(z["rhat"])}, open(RES / "summary.json", "w"),
          ensure_ascii=False, indent=1)
