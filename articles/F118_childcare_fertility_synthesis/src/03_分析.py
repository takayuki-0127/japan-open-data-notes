"""03 分析：①022 を共通の単位で再推定（都道府県×年）②これまでの記事の推定値を同じ単位で並べる③頑健性"""
from common import *
import statsmodels.formula.api as smf

out = {}
P = pd.read_csv(DATA / "pref_panel.csv", dtype={"pc": str})
P = P[P.year <= 2022].copy()   # 022 と同じく、定義が変わった可能性のある2023年を除く


def fit(f, d, x, k=10):
    r = smf.ols(f, d).fit(cov_type="cluster", cov_kwds={"groups": d["pc"]})
    lo, hi = r.conf_int().loc[x]
    return {"coef": r.params[x] * k, "lo": lo * k, "hi": hi * k, "se": r.bse[x] * k, "n": int(r.nobs)}


def fit_hc(f, d, x, k=10):
    r = smf.ols(f, d).fit(cov_type="HC1")
    lo, hi = r.conf_int().loc[x]
    return {"coef": r.params[x] * k, "lo": lo * k, "hi": hi * k, "se": r.bse[x] * k, "n": int(r.nobs)}


# ---------- ① 022 の再推定 ----------
specs = {"そのまま（県×年をプール）": "tfr ~ {x}", "＋県の固定効果": "tfr ~ {x} + C(pc)", "＋県と年の固定効果（二方向）": "tfr ~ {x} + C(pc) + C(year)"}
pref = {}
for name, f in specs.items():
    pref[name] = fit(f.format(x="D"), P, "D")
# 022 のもとの単位（15歳未満100人あたりの定員、+10人）を再現できるか
orig = {name: fit(f.format(x="cap_u15"), P, "cap_u15") for name, f in specs.items()}
# 県の間（2022年の断面）
pref["県どうし（2022年の断面）"] = fit_hc("tfr ~ D", P[P.year == 2022], "D")
# 長い差（県ごとの変化どうし）
w = P.pivot(index="pc", columns="year", values=["tfr", "D"])
for a, b in [(2012, 2019), (2012, 2022), (2015, 2020)]:
    dd = pd.DataFrame({"dY": w.tfr[b] - w.tfr[a], "dD": w.D[b] - w.D[a]}).reset_index()
    pref[f"長い差 {a}→{b}"] = fit_hc("dY ~ dD", dd, "dD")
out["pref_main"] = pref
out["pref_orig_unit"] = orig

# ---------- ③ 頑健性（二方向固定効果を中心に） ----------
rob = {}
tw = "tfr ~ {x} + C(pc) + C(year)"
rob["基本（在所児・0〜5歳を国勢調査で補間）"] = pref["＋県と年の固定効果（二方向）"]
rob["0〜5歳の割合を全国一律（2015年）に"] = fit(tw.format(x="D_const"), P, "D_const")
Pb = P[P.year >= 2017]
rob["0〜5歳を直近6年の出生数で近似（2017〜22年）"] = fit(tw.format(x="D_births"), Pb, "D_births")
rob["同じ期間（2017〜22年）で基本の換算"] = fit(tw.format(x="D"), Pb, "D")
rob["処置を定員に（0〜5歳100人あたり）"] = fit(tw.format(x="D_cap"), P, "D_cap")
rob["2012〜19年だけ（コロナの年を除く）"] = fit(tw.format(x="D"), P[P.year <= 2019], "D")
rob["有効求人倍率をそろえる"] = fit("tfr ~ D + job + C(pc) + C(year)", P, "D")
rob["1年前の在所児で（tfr_t ~ D_{t-1}）"] = None
P = P.sort_values(["pc", "year"]); P["D_lag"] = P.groupby("pc").D.shift(1)
rob["1年前の在所児で（tfr_t ~ D_{t-1}）"] = fit(tw.format(x="D_lag"), P.dropna(subset=["D_lag"]), "D_lag")
P["w"] = P.groupby("pc").A4101.transform("mean")
r = smf.wls("tfr ~ D + C(pc) + C(year)", P, weights=P.w).fit(cov_type="cluster", cov_kwds={"groups": P["pc"]})
rob["出生数で重み付け"] = {"coef": r.params["D"] * 10, "lo": r.conf_int().loc["D", 0] * 10, "hi": r.conf_int().loc["D", 1] * 10, "se": r.bse["D"] * 10, "n": int(r.nobs)}
# 県を1つずつ抜く
loo = []
for p in sorted(P.pc.unique()):
    loo.append(fit(tw.format(x="D"), P[P.pc != p], "D")["coef"])
rob["県を1つずつ抜く（47回の範囲）"] = {"coef": float(np.median(loo)), "lo": float(min(loo)), "hi": float(max(loo)), "se": None, "n": 46 * 11, "note": "lo/hi は47回の推定値の最小・最大"}
out["pref_robust"] = rob

# ---------- ② これまでの記事の推定値を並べる ----------
rows = []
def add(study, level, design, method, e, note=""):
    rows.append({"study": study, "level": level, "design": design, "method": method, "coef": e["coef"], "lo": e["lo"], "hi": e["hi"], "n": e.get("n"), "note": note})

add("022（再推定）", "都道府県", "県どうしの差（水準）", "単純な回帰（2022年）", pref["県どうし（2022年の断面）"])
add("022（再推定）", "都道府県", "県どうしの差（水準）", "プールした回帰", pref["そのまま（県×年をプール）"])
add("022（再推定）", "都道府県", "県の中の年ごとの動き", "県の固定効果", pref["＋県の固定効果"])
add("022（再推定）", "都道府県", "県の中の年ごとの動き", "二方向固定効果", pref["＋県と年の固定効果（二方向）"])
add("022（再推定）", "都道府県", "県の変化どうし", "長い差 2012→22", pref["長い差 2012→2022"])

f100 = jload(PRIOR / "F100_results.json")
add("F100", "市区町村", "町どうしの差（水準）", "単純な回帰", f100["naive"]["q1_level"], "条件なし")
add("F100", "市区町村", "町の変化どうし", "単純な回帰", f100["naive"]["q1_change"], "条件なし")
sp = pd.read_csv(PRIOR / "F100_specifications.csv")
sp = sp[(sp.q == "q1") & (sp.pref == True) & (sp["sample"] == "all")]
for _, s in sp.iterrows():
    dz = "町どうしの差（水準）" if s.design == "level" else "町の変化どうし"
    add("F100", "市区町村", dz, s.method + "（県ダミーあり）", {"coef": s.coef, "lo": s.lo, "hi": s.hi, "n": int(s.n)})
f51 = jload(PRIOR / "F51_results.json")["main"]
add("F51", "市区町村", "町の変化どうし", "媒介分析：総合効果", {"coef": f51["c"], "lo": f51["ci"]["c"][0], "hi": f51["ci"]["c"][1], "n": f51["n"]})
add("F51", "市区町村", "町の変化どうし", "媒介分析：女性の就業を通る分", {"coef": f51["ab"], "lo": f51["ci"]["ab"][0], "hi": f51["ci"]["ab"][1], "n": f51["n"]})
add("F51", "市区町村", "町の変化どうし", "媒介分析：通らない分", {"coef": f51["cp"], "lo": f51["ci"]["cp"][0], "hi": f51["ci"]["cp"][1], "n": f51["n"]})
E = pd.DataFrame(rows)
E["sig"] = np.where(E.lo > 0, "プラス", np.where(E.hi < 0, "マイナス", "0をまたぐ"))
E["halfwidth"] = (E.hi - E.lo) / 2
E.to_csv(RES / "estimates_common_unit.csv", index=False, encoding="utf-8-sig")

# 単位をそろえられない推定（施設数で見たもの）
f20 = pd.read_csv(PRIOR / "F20_coefficients.csv")
f20n = f20[(f20.run == "main") & (f20.x == "nursery")]
out["not_comparable"] = {
    "F20（保育所等の数、0〜5歳千人あたり・1SD=7.7か所、2018〜22年の出生率、市区町村の断面）": {m: {"beta": float(b), "se": float(s_)} for m, b, s_ in zip(f20n.model, f20n.beta, f20n.se)},
    "F100 頑健性（処置を保育所等の数・1SDあたり）": "水準 −0.010〜−0.053（すべてマイナス）、変化 −0.003〜+0.003（すべて0をまたぐ）",
    "F81（通勤の割合が処置。保育所数は条件の1つで、出生率への保育所の効果は推定していない）": "対象外",
}

# 比べ方ごとのまとめ
g = E[E.study.ne("F51") | E.method.str.contains("総合")].groupby("design").agg(n_est=("coef", "size"), min=("coef", "min"), max=("coef", "max"), med=("coef", "median"),
      n_pos=("sig", lambda s: (s == "プラス").sum()), n_neg=("sig", lambda s: (s == "マイナス").sum()), n_zero=("sig", lambda s: (s == "0をまたぐ").sum()),
      med_halfwidth=("halfwidth", "median"))
g.to_csv(RES / "by_design.csv", encoding="utf-8-sig")
out["by_design"] = g.reset_index().to_dict(orient="records")

# ---------- 大きさの目安 ----------
nat = P.groupby("year").agg(J2506=("J2506", "sum"), age05=("age05", "sum"), tfr=("tfr", "mean"))
nat["D"] = nat.J2506 / nat.age05 * 100
dD = float(nat.D.loc[2022] - nat.D.loc[2012])
out["scale"] = {"D_2012": float(nat.D.loc[2012]), "D_2022": float(nat.D.loc[2022]), "D_change": dD,
                "tfr_pref_mean_2012": float(nat.tfr.loc[2012]), "tfr_pref_mean_2022": float(nat.tfr.loc[2022]), "tfr_change": float(nat.tfr.loc[2022] - nat.tfr.loc[2012]),
                "note": "D は全国の在所児÷全国の0〜5歳（推計）×100、tfr は47都道府県の単純平均"}
# 各推定値を「全国で実際に増えた分」に当てはめると出生率はいくつ違うか
E2 = E.copy(); k = dD / 10
E2["implied"] = E2.coef * k; E2["implied_lo"] = E2.lo * k; E2["implied_hi"] = E2.hi * k
E2.to_csv(RES / "estimates_implied_2012_22.csv", index=False, encoding="utf-8-sig")

# ---------- 女性の就業（問い2）の並べ比べ ----------
f16 = jload(PRIOR / "F16_results.json")
q2 = []
for key, lab in [("ols_naive", "単純な回帰"), ("ols_ctrl", "重回帰（80列）"), ("dml_lasso", "DML（Lasso）"), ("dml_rf", "DML（RF）"), ("dml_lgbm", "DML（LightGBM）")]:
    e = f16[key]; q2.append({"study": "F16", "design": "町の変化どうし", "method": lab, "coef": e["coef"], "lo": e["lo"], "hi": e["hi"]})
q2.append({"study": "F51", "design": "町の変化どうし", "method": "媒介分析の a", "coef": f51["a"], "lo": f51["ci"]["a"][0], "hi": f51["ci"]["a"][1]})
sp2 = pd.read_csv(PRIOR / "F100_specifications.csv")
sp2 = sp2[(sp2.q == "q2") & (sp2.pref == True) & (sp2["sample"] == "all")]
for _, s in sp2.iterrows():
    q2.append({"study": "F100", "design": "町どうしの差（水準）" if s.design == "level" else "町の変化どうし", "method": s.method, "coef": s.coef, "lo": s.lo, "hi": s.hi})
Q2 = pd.DataFrame(q2); Q2.to_csv(RES / "estimates_q2_labor.csv", index=False, encoding="utf-8-sig")

# F100 のばらつきの分解（再掲）
out["f100_variance_share"] = jload(PRIOR / "F100_variance_share.json")

jdump(out, RES / "results.json")
pd.set_option("display.width", 200)
print(pd.DataFrame(pref).T.round(4)); print(pd.DataFrame(orig).T.round(4)); print(pd.DataFrame({k_: v for k_, v in rob.items()}).T[["coef", "lo", "hi", "n"]].round(4))
print(g.round(4)); print(out["scale"]); print(Q2.round(3))
