"""分析：A 出生順位別の全国の動き／B 保育の受け皿と段階別の出生（二方向固定効果）／
C 幼保無償化（2019年10月）前後のイベントスタディ／D 2040年の出生数のシナリオ。"""
import json
import numpy as np, pandas as pd
import statsmodels.formula.api as smf
from common import RAW, DATA, RES, AGES, SEED

RES.mkdir(exist_ok=True)
rng = np.random.default_rng(SEED)
P = pd.read_csv(DATA / "panel.csv")
out = {}
STG = {"r_marriages": "婚姻", "r_o1": "第1子", "r_o2": "第2子", "r_o3p": "第3子以上"}

# ---------- A 全国：出生順位別の合計特殊出生率と出生数 ----------
T = pd.read_csv(RAW / "f58_order_tfr_mab.csv").set_index("year")
T["tfr3p"] = T.tfr3 + T.tfr4 + T.tfr5p
A_rows = []
for y0, y1 in [(1995, 2005), (2005, 2015), (2015, 2023)]:
    d = {k: round(T.loc[y1, k] - T.loc[y0, k], 3) for k in ["tfr", "tfr1", "tfr2", "tfr3p"]}
    A_rows.append({"y0": y0, "y1": y1, **d})
A = pd.DataFrame(A_rows); A.to_csv(RES / "A_order_tfr_change.csv", index=False)
out["A_tfr_change"] = A.to_dict("records")
N = P.groupby("year")[["total", "o1", "o2", "o3p", "marriages"]].sum(min_count=40)
N.to_csv(RES / "A_national_counts.csv")
def pct(a, b, k): return round((N.loc[b, k] / N.loc[a, k] - 1) * 100, 1)
out["A_counts_2015_2025"] = {k: pct(2015, 2025, k) for k in ["total", "o1", "o2", "o3p"]}
out["A_counts_2015_2023"] = {k: pct(2015, 2023, k) for k in ["total", "o1", "o2", "o3p", "marriages"]}
out["A_counts_2023_2025"] = {k: pct(2023, 2025, k) for k in ["total", "o1", "o2", "o3p"]}
out["A_share_o3p"] = {int(y): round(N.loc[y, "o3p"] / N.loc[y, "total"] * 100, 2) for y in [2015, 2019, 2022, 2023, 2024, 2025]}
# 1組の結婚あたりの第1子（2〜3年のずれを無視した目安）
out["A_o1_per_marriage"] = {int(y): round(N.loc[y, "o1"] / N.loc[y, "marriages"], 3) for y in range(2012, 2024) if y in N.index and not np.isnan(N.loc[y, "marriages"])}

# ---------- B 保育の受け皿（定員、0〜5歳100人あたり）と段階別の出生 ----------
def twfe(df, y, x, extra="", cl="pref"):
    d = df.dropna(subset=[y, x]).copy()
    d["ly"] = np.log(d[y])
    m = smf.ols(f"ly ~ {x} + C(pref) + C(year){extra}", data=d).fit(cov_type="cluster", cov_kwds={"groups": d[cl]})
    b, se = m.params[x], m.bse[x]
    return {"b": b * 100, "lo": (b - 1.96 * se) * 100, "hi": (b + 1.96 * se) * 100, "p": m.pvalues[x], "n": int(m.nobs)}
B = P[(P.year >= 2012) & (P.year <= 2022)].copy()
B["cap10"] = B.D_cap / 10; B["enr10"] = B.D / 10
B = B.sort_values(["pref", "year"])
B["cap10_l1"] = B.groupby("pref").cap10.shift(1)
B.loc[B.year == 2018, "cap10_l1"] = B.loc[B.year == 2018, "pref"].map(B[B.year == 2016].set_index("pref").cap10)  # 2017年が欠けるので2016年で代用
B["t"] = B.year - 2012
rows = []
for y, nm in STG.items():
    for lab, x, extra, d in [("主（定員・二方向固定効果）", "cap10", "", B),
                             ("1年前の定員", "cap10_l1", "", B),
                             ("県ごとの傾きを入れる", "cap10", " + C(pref):t", B),
                             ("在所児（定員ではなく）", "enr10", "", B),
                             ("確定数の年だけ（2012〜16年）", "cap10", "", B[B.year <= 2016]),
                             ("分母を15〜64歳の女性に", "cap10", "", B.assign(**{y: B[y] * B.w15_49 / B.women15_64}))]:
        r = twfe(d, y, x, extra); rows.append({"stage": nm, "spec": lab, **r})
# 長い差（2012→2022）
L = B[B.year.isin([2012, 2022])].pivot(index="pref", columns="year")
for y, nm in STG.items():
    dy = np.log(L[(y, 2022)] / L[(y, 2012)]); dx = L[("cap10", 2022)] - L[("cap10", 2012)]
    m = smf.ols("dy ~ dx", data=pd.DataFrame({"dy": dy, "dx": dx})).fit(cov_type="HC1")
    rows.append({"stage": nm, "spec": "長い差（2012→2022）", "b": m.params["dx"] * 100, "lo": m.conf_int().loc["dx", 0] * 100, "hi": m.conf_int().loc["dx", 1] * 100, "p": m.pvalues["dx"], "n": int(m.nobs)})
Bt = pd.DataFrame(rows); Bt.to_csv(RES / "B_twfe.csv", index=False)
out["B_main"] = Bt[Bt.spec.str.startswith("主")].round(3).to_dict("records")
out["B_range"] = {nm: [round(Bt[Bt.stage == nm].b.min(), 2), round(Bt[Bt.stage == nm].b.max(), 2), int((Bt[Bt.stage == nm].p < 0.05).sum()), int((Bt.stage == nm).sum())] for nm in STG.values()}
out["B_dcap_growth"] = {"2012": round(B[B.year == 2012].D_cap.mean(), 1), "2022": round(B[B.year == 2022].D_cap.mean(), 1),
                        "sd_change": round((L[("cap10", 2022)] - L[("cap10", 2012)]).std() * 10, 1)}

# ---------- C 幼保無償化（2019年10月）前後：2018年の在所の多さで比べる ----------
E = P[P.year == 2018].set_index("pref").D
Ez = (E - E.mean()) / E.std()
CD = P[(P.year >= 2012)].copy()
CD["E"] = CD.pref.map(Ez)
YRS = sorted(CD.year.unique())
def es(df, y, expo):
    d = df.dropna(subset=[y]).copy(); d["ly"] = np.log(d[y]); d["E"] = d.pref.map(expo)
    terms = []
    for yy in sorted(d.year.unique()):
        if yy == 2018: continue
        d[f"e{yy}"] = (d.year == yy) * d.E; terms.append(f"e{yy}")
    m = smf.ols("ly ~ " + " + ".join(terms) + " + C(pref) + C(year)", data=d).fit(cov_type="cluster", cov_kwds={"groups": d["pref"]})
    res = {int(t[1:]): (m.params[t] * 100, m.bse[t] * 100) for t in terms}
    res[2018] = (0.0, 0.0)
    return res
crow = []
for y, nm in STG.items():
    r = es(CD, y, Ez)
    for yy, (b, se) in sorted(r.items()):
        crow.append({"stage": nm, "year": yy, "b": b, "lo": b - 1.96 * se, "hi": b + 1.96 * se})
Ce = pd.DataFrame(crow); Ce.to_csv(RES / "C_event_study.csv", index=False)
# 後（2020年以降）の平均 − 前（2012〜16年）の平均 と、在所の多さを並べ替えた分布（1,000回）
def diff_post_pre(r):
    post = [b for yy, (b, _) in r.items() if yy >= 2020]; pre = [b for yy, (b, _) in r.items() if yy <= 2016]
    return np.mean(post) - np.mean(pre)
perm = {}
for y, nm in STG.items():
    obs = diff_post_pre(es(CD, y, Ez))
    sims = []
    for _ in range(300):
        z = pd.Series(rng.permutation(Ez.values), index=Ez.index)
        sims.append(diff_post_pre(es(CD, y, z)))
    sims = np.array(sims)
    perm[nm] = {"obs": round(obs, 2), "p": round(float((np.abs(sims) >= abs(obs)).mean()), 3), "q95": round(float(np.quantile(np.abs(sims), 0.95)), 2)}
out["C_perm"] = perm
# 県ごとの「前からの傾き」を入れた確認：E×(年−2018) の直線と E×(2020年以降) を同時に入れる
def es_trend(df, y, expo):
    d = df.dropna(subset=[y]).copy(); d["ly"] = np.log(d[y]); d["E"] = d.pref.map(expo)
    d["Et"] = d.E * (d.year - 2018); d["Epost"] = d.E * (d.year >= 2020)
    m = smf.ols("ly ~ Et + Epost + C(pref) + C(year)", data=d).fit(cov_type="cluster", cov_kwds={"groups": d["pref"]})
    return {"post": m.params["Epost"] * 100, "lo": (m.params["Epost"] - 1.96 * m.bse["Epost"]) * 100, "hi": (m.params["Epost"] + 1.96 * m.bse["Epost"]) * 100,
            "p": m.pvalues["Epost"], "trend_per_year": m.params["Et"] * 100}
out["C_trend_adjusted"] = {nm: {k: round(v, 3) for k, v in es_trend(CD, y, Ez).items()} for y, nm in STG.items()}
permt = {}
for y, nm in STG.items():
    obs = es_trend(CD, y, Ez)["post"]; sims = []
    for _ in range(300):
        z = pd.Series(rng.permutation(Ez.values), index=Ez.index); sims.append(es_trend(CD, y, z)["post"])
    permt[nm] = {"obs": round(obs, 3), "p": round(float((np.abs(sims) >= abs(obs)).mean()), 3)}
out["C_trend_perm"] = permt
out["C_trend_no_tokyo"] = {nm: round(es_trend(CD[CD.pref != 13], y, Ez.drop(13))["post"], 3) for y, nm in STG.items()}
out["C_trend_until2023"] = {nm: round(es_trend(CD[CD.year <= 2023], y, Ez)["post"], 3) for y, nm in STG.items()}
# 前の期間（2012〜18年）だけで傾きを測り、2025年までのばした値と比べる
pre_fit = {}
for nm in STG.values():
    g = Ce[(Ce.stage == nm) & (Ce.year <= 2018)]
    sl, ic = np.polyfit(g.year, g.b, 1)
    post = Ce[(Ce.stage == nm) & (Ce.year >= 2020)]
    pre_fit[nm] = {"slope": round(sl, 3), "post_obs_mean": round(post.b.mean(), 2), "post_trend_mean": round(float(np.mean(ic + sl * post.year)), 2)}
out["C_pretrend_extrap"] = pre_fit
# 東京を除いた確認
r_no13 = {nm: round(diff_post_pre(es(CD[CD.pref != 13], y, Ez.drop(13))), 2) for y, nm in STG.items()}
out["C_no_tokyo"] = r_no13
out["C_E_2018"] = {"mean": round(E.mean(), 1), "sd": round(E.std(), 1), "min": round(E.min(), 1), "max": round(E.max(), 1)}

# ---------- D 2040年の出生数のシナリオ ----------
f3 = json.load(open(RAW / "f203_main.json", encoding="utf-8"))
f_m20 = pd.Series(f3["A_marital_rate_2020"])[AGES]          # 有配偶の女性1人あたりの年の出生（2020年）
m20 = pd.Series(f3["A_2025_marriage_only"]["married_2020"])[AGES]
m25 = pd.Series(f3["A_2025_marriage_only"]["married_2025"])[AGES]
Wn = pd.read_csv(RAW / "f160_women_by_age_national.csv").set_index("year")
ag = [f"a{i}" for i in range(19)]
w20, w25 = Wn.loc[2020, ag].values, Wn.loc[2025, ag].values
ratio = np.r_[w25[0] / 1, w25[1:] / w20[:-1]]        # 5年で1つ上の階級に移るときの比（死亡・移動を含む）
def project(w, steps, ratio):
    for _ in range(steps):
        w = np.r_[np.nan, w[:-1] * ratio[1:]]
    return w
w40 = project(w25.astype(float), 3, ratio)
w40_nomig = project(w25.astype(float), 3, np.ones_like(ratio))
def births(w, m, f, scale=1.0):
    return float(np.sum(w[3:10] * m.values * f.values) * scale)
calib20 = 840832 / births(w20, m20, f_m20)                    # 2020年の実際の出生数に合わせる倍率（日本人・届出の範囲の違いなど）
b25_model = births(w25, m25, f_m20, calib20)                  # 2020年の夫婦の出生率のままなら2025年は何人だったか
f25_mult = int(N.loc[2025, "total"]) / b25_model              # 2025年の実際に合わせる＝夫婦の出生率が2020→25年に何倍になったか（年齢の形は同じと仮定）
f_m = f_m20 * f25_mult                                        # シナリオの出発点：2025年の夫婦の出生率
paths = {"有配偶の割合がこの5年の勢いで下がり続ける": (m25 + 3 * (m25 - m20)).clip(lower=m25 * 0.5),
         "2025年の有配偶の割合のまま": m25,
         "2040年までに2020年の割合へ戻る": m20}
fmul = {"夫婦の出生率がさらに1割下がる": 0.9, "2025年のまま": 1.0, "1割上がる（2020年を少し上回る）": 1.1}
Drows = []
for pn, m in paths.items():
    for fn, k in fmul.items():
        Drows.append({"married": pn, "marital": fn, "births2040": births(w40, m, f_m * k, calib20),
                      "births2040_nomig": births(w40_nomig, m, f_m * k, calib20),
                      "tfr2040": float(5 * np.sum(m.values * f_m.values * k))})
Dt = pd.DataFrame(Drows); Dt.to_csv(RES / "D_scenarios_2040.csv", index=False)
# 2025年の出生数を保つのに必要な夫婦の出生率の倍率
need = {pn: births(w25, m25, f_m, calib20) / births(w40, m, f_m, calib20) for pn, m in paths.items()}
w_change = float(np.nansum(w40[3:10]) / np.sum(w25[3:10]) - 1)
out["D"] = {"calib20": round(calib20, 4), "f25_mult": round(f25_mult, 4), "b25_model": round(b25_model), "b25_actual": int(N.loc[2025, "total"]),
            "range": [round(Dt.births2040.min()), round(Dt.births2040.max())], "mid": round(Dt.loc[(Dt.married == "2025年の有配偶の割合のまま") & (Dt.marital == "2025年のまま"), "births2040"].iloc[0]),
            "range_nomig": [round(Dt.births2040_nomig.min()), round(Dt.births2040_nomig.max())],
            "women15_49_change_2025_2040_pct": round(w_change * 100, 1),
            "women15_49_2025": int(np.sum(w25[3:10])), "women15_49_2040": int(np.nansum(w40[3:10])),
            "need_mult_to_keep_2025": {k: round(v, 3) for k, v in need.items()}}
# 女性の数だけが変わったとき（2025年の率のまま）の出生数
out["D"]["women_only"] = round(births(w40, m25, f_m, calib20))
json.dump(out, open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float)[:6000])
