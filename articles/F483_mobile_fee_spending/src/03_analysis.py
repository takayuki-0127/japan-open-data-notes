"""携帯電話通信料の推移、年齢別、分解、物価との回帰、仮説、頑健性。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
age = pd.read_csv(ROOT / "data" / "kakei_age.csv")
cpi = pd.read_csv(ROOT / "data" / "cpi.csv").set_index("year")
lt = pd.read_csv(ROOT / "data" / "kakei_long_comm.csv")
AGES = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]

M = age[age.item == "mobile"].pivot(index="year", columns="age", values="value")[["平均"] + AGES]
D = age[age.item == "dist"].pivot(index="year", columns="age", values="value")[AGES]
D = D.div(D.sum(axis=1), axis=0)  # 年齢の構成比（合計1）
CONS = age[age.item == "consumption"].pivot(index="year", columns="age", values="value")[["平均"] + AGES]
FIX = age[age.item == "fixed"].pivot(index="year", columns="age", values="value")[["平均"] + AGES]

t = pd.DataFrame({"mobile_yen": M["平均"], "fixed_yen": FIX["平均"], "consumption_yen": CONS["平均"]})
t["mobile_share_pct"] = t.mobile_yen / t.consumption_yen * 100
t["cpi_mobile"] = cpi.cpi_mobile.reindex(t.index)
t["cpi_all"] = cpi.cpi_all.reindex(t.index)
t["mobile_real_2025yen"] = t.mobile_yen / t.cpi_mobile * 100
t.round(4).to_csv(R / "national.csv")
M.to_csv(R / "mobile_by_age.csv")
real_age = M.div(cpi.cpi_mobile.reindex(M.index), axis=0) * 100
real_age.round(1).to_csv(R / "mobile_real_by_age.csv")


def shift_share(a, b, Ma=None, Mb=None, Da=None, Db=None):
    Ma = M.loc[a, AGES] if Ma is None else Ma; Mb = M.loc[b, AGES] if Mb is None else Mb
    Da = D.loc[a] if Da is None else Da; Db = D.loc[b] if Db is None else Db
    within = float(((Mb - Ma) * (Da + Db) / 2).sum())
    comp = float(((Db - Da) * (Ma + Mb) / 2).sum())
    return within, comp, float((Mb * Db).sum() - (Ma * Da).sum())


w, c, tot = shift_share(2019, 2025)
h1 = w / tot * 100


def reg(y, trend=True, rel=False):
    yy = np.log(t.mobile_yen.loc[2015:2025])
    px = t.cpi_mobile / (t.cpi_all if rel else 1)
    X = pd.DataFrame({"log_p": np.log(px.loc[2015:2025])})
    if trend:
        X["trend"] = np.arange(len(X), dtype=float)
    X = sm.add_constant(X)
    f = sm.OLS(yy, X).fit(cov_type="HC1")
    return float(f.params["log_p"]), float(f.bse["log_p"]), float(f.rsquared)


b, se, r2 = reg(None)

# 年齢別の変化（2019→2025）
chg = pd.DataFrame({"yen_2019": M.loc[2019], "yen_2025": M.loc[2025]})
chg["change_pct"] = (chg.yen_2025 / chg.yen_2019 - 1) * 100
chg["real_change_pct"] = (real_age.loc[2025] / real_age.loc[2019] - 1) * 100
chg["share_of_consumption_2019_pct"] = M.loc[2019] / CONS.loc[2019] * 100
chg["share_of_consumption_2025_pct"] = M.loc[2025] / CONS.loc[2025] * 100
chg["households_share_2019_pct"] = pd.concat([pd.Series({"平均": 1.0}), D.loc[2019]]) * 100
chg["households_share_2025_pct"] = pd.concat([pd.Series({"平均": 1.0}), D.loc[2025]]) * 100
chg.round(2).to_csv(R / "change_by_age_2019_2025.csv")

# 長期時系列の「通信」（二人以上・単身）
L = lt.pivot_table(index="year", columns=["household", "item"], values="yen")
comm = pd.DataFrame({h: L[(h, "通信")] for h in ["二人以上の世帯", "単身世帯"]})
comm.to_csv(R / "comm_long.csv")

# ---- 頑健性 -------------------------------------------------------------------------------
rob = []
avg = lambda s, ys: s.loc[ys].mean()
for name, a, bb in [("本線：2019→2025年", [2019], [2025]), ("3年平均：2017〜19年→2023〜25年", [2017, 2018, 2019], [2023, 2024, 2025]),
                    ("起点を2020年に：2020→2025年", [2020], [2025])]:
    Ma, Mb = M.loc[a, AGES].mean(), M.loc[bb, AGES].mean()
    Da, Db = D.loc[a].mean(), D.loc[bb].mean()
    ww, cc, tt = shift_share(None, None, Ma, Mb, Da, Db)
    rob.append({"check": name, "national_change_pct": round(float((avg(M["平均"], bb) / avg(M["平均"], a) - 1) * 100), 1),
                "within_share_pct": round(ww / tt * 100, 1),
                "change_29_39_pct": round(float(((Mb["29歳以下"] + Mb["30～39歳"]) / (Ma["29歳以下"] + Ma["30～39歳"]) - 1) * 100), 1),
                "change_70plus_pct": round(float((Mb["70歳以上"] / Ma["70歳以上"] - 1) * 100), 1),
                "comm_two_plus_pct": round(float((avg(comm["二人以上の世帯"], bb) / avg(comm["二人以上の世帯"], a) - 1) * 100), 1),
                "comm_single_pct": round(float((avg(comm["単身世帯"], bb) / avg(comm["単身世帯"], a) - 1) * 100), 1)})
rob = pd.DataFrame(rob)
rob.to_csv(R / "robustness.csv", index=False)
regs = []
for name, tr, rel in [("本線：物価＋時間の傾き", True, False), ("時間の傾きなし", False, False), ("相対価格（携帯÷総合）＋傾き", True, True)]:
    bb_, ss_, rr_ = reg(None, tr, rel)
    regs.append({"model": name, "coef_log_price": round(bb_, 3), "se": round(ss_, 3), "r2": round(rr_, 3)})
pd.DataFrame(regs).to_csv(R / "regression.csv", index=False)

main = {
    "mobile_2015": float(t.mobile_yen.loc[2015]), "mobile_2019": float(t.mobile_yen.loc[2019]), "mobile_2020": float(t.mobile_yen.loc[2020]),
    "mobile_2025": float(t.mobile_yen.loc[2025]),
    "mobile_change_2019_2025_pct": round(float((t.mobile_yen.loc[2025] / t.mobile_yen.loc[2019] - 1) * 100), 1),
    "mobile_change_2019_2025_yen": float(t.mobile_yen.loc[2025] - t.mobile_yen.loc[2019]),
    "fixed_2019": float(t.fixed_yen.loc[2019]), "fixed_2025": float(t.fixed_yen.loc[2025]),
    "share_2019_pct": round(float(t.mobile_share_pct.loc[2019]), 2), "share_2025_pct": round(float(t.mobile_share_pct.loc[2025]), 2),
    "cpi_mobile_2019": float(t.cpi_mobile.loc[2019]), "cpi_mobile_2021": float(cpi.cpi_mobile.loc[2021]), "cpi_mobile_2025": float(t.cpi_mobile.loc[2025]),
    "cpi_mobile_change_2019_2025_pct": round(float((t.cpi_mobile.loc[2025] / t.cpi_mobile.loc[2019] - 1) * 100), 1),
    "real_change_2019_2025_pct": round(float((t.mobile_real_2025yen.loc[2025] / t.mobile_real_2025yen.loc[2019] - 1) * 100), 1),
    "by_age_change_pct": {k: round(float(v), 1) for k, v in chg.change_pct.items()},
    "by_age_yen_2019": {k: float(v) for k, v in chg.yen_2019.items()}, "by_age_yen_2025": {k: float(v) for k, v in chg.yen_2025.items()},
    "share70_2019_pct": round(float(D.loc[2019, "70歳以上"] * 100), 1), "share70_2025_pct": round(float(D.loc[2025, "70歳以上"] * 100), 1),
    "shift_share_yen": {"within": round(w, 0), "composition": round(c, 0), "total": round(tot, 0)},
    "reg_coef": round(b, 3), "reg_se": round(se, 3), "reg_r2": round(r2, 3),
    "hypotheses": {
        "H1_within_ge_80": {"value": round(h1, 1), "result": "支持" if h1 >= 80 else "外れ"},
        "H2_0_lt_coef_lt_1": {"value": round(b, 3), "se": round(se, 3), "result": "支持" if 0 < b < 1 else "外れ"},
    },
}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(rob.to_string()); print(pd.DataFrame(regs).to_string()); print(chg.round(1).to_string())
