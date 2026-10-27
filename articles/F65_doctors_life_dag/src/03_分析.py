"""DAG で調整する変数を選び、選び方で答えがどう変わるかを比べる。

X = 人口10万人当たり医師数（2010年）, Y = 平均寿命（0歳、2015年）, n = 47都道府県。
係数は「医師が人口10万人当たり50人多い」ときの平均寿命の差（年）。標準誤差は HC3。
"""
import itertools, json
import numpy as np
import pandas as pd
import networkx as nx
import statsmodels.api as sm
from common import DATA, RES, SEED

rng = np.random.default_rng(SEED)
d = pd.read_csv(DATA / "pref_panel.csv", index_col="pref_code")
SCALE = 50.0

# ---------- DAG（仮定）----------
BASE_EDGES = [("did", "doctors"), ("did", "e0"), ("did", "income"), ("did", "univ_grad"),
              ("did", "universities"), ("did", "aged65"), ("did", "unemp"),
              ("income", "doctors"), ("income", "e0"),
              ("univ_grad", "doctors"), ("univ_grad", "e0"),
              ("universities", "doctors"),
              ("aged65", "doctors"), ("aged65", "e0"),
              ("temp", "e0"), ("unemp", "e0"),
              ("doctors", "e0"), ("e0", "std_mort")]
DAGS = {"A_病床は中間": BASE_EDGES + [("doctors", "beds"), ("beds", "e0")],
        "B_病床は共通原因": BASE_EDGES + [("beds", "doctors"), ("beds", "e0")]}
OBS = ["did", "income", "univ_grad", "aged65", "temp", "unemp", "beds", "universities", "std_mort"]

def is_dsep(G, x, y, z):
    f = getattr(nx, "is_d_separator", None) or nx.d_separated
    return f(G, {x}, {y}, set(z))

def backdoor_ok(edges, Z, x="doctors", y="e0"):
    G = nx.DiGraph(edges)
    if set(Z) & nx.descendants(G, x):
        return False
    H = G.copy(); H.remove_edges_from([(x, c) for c in list(G.successors(x))])
    return is_dsep(H, x, y, Z)

dag_out = {}
for name, E in DAGS.items():
    valid = [list(z) for k in range(len(OBS) + 1) for z in itertools.combinations(OBS, k) if backdoor_ok(E, z)]
    mins = [z for z in valid if not any(set(w) < set(z) for w in valid)]
    dag_out[name] = {"n_valid": len(valid), "minimal": mins}
    print(name, "有効な調整セット", len(valid), "最小", mins)
json.dump(dag_out, open(RES / "dag_adjustment_sets.json", "w"), ensure_ascii=False, indent=1)

# ---------- 回帰 ----------
def fit(df, y, x, Z):
    X = sm.add_constant(df[[x] + list(Z)])
    m = sm.OLS(df[y], X).fit(cov_type="HC3")
    b, se = m.params[x] * SCALE, m.bse[x] * SCALE
    return {"coef": b, "lo": b - 1.96 * se, "hi": b + 1.96 * se, "se": se, "p": m.pvalues[x], "r2": m.rsquared, "k": len(Z)}

MIN = ["did", "income", "univ_grad", "aged65"]
SETS = {
    "調整なし": [],
    "DAGの最小セット（都市化・所得・大卒・高齢化）": MIN,
    "最小セット＋結果だけに効く変数（気温・失業）": MIN + ["temp", "unemp"],
    "＋病床数（Aなら過剰調整、Bなら必要）": MIN + ["temp", "unemp", "beds"],
    "＋大学数（医師数にだけ効く変数）": MIN + ["temp", "unemp", "universities"],
    "高齢化を外す": ["did", "income", "univ_grad", "temp", "unemp"],
    "＋標準化死亡率（結果そのものを調整）": MIN + ["temp", "unemp", "std_mort"],
    "全部入れる": OBS,
}
rows = []
for sex in ("m", "f"):
    y = f"e0_{sex}_2015"
    for lab, Z in SETS.items():
        r = fit(d, y, "doctors", Z); r.update(sex=sex, set=lab, vars="+".join(Z))
        r["valid_A"] = backdoor_ok(DAGS["A_病床は中間"], Z); r["valid_B"] = backdoor_ok(DAGS["B_病床は共通原因"], Z)
        rows.append(r)
main = pd.DataFrame(rows); main.to_csv(RES / "coef_by_adjustment_set.csv", index=False)
print(main[["sex", "set", "coef", "lo", "hi", "p", "r2", "valid_A", "valid_B"]].round(3).to_string())

# ---------- 全部の組み合わせ（std_mort を除く8変数 → 256通り）----------
POOL = [v for v in OBS if v != "std_mort"]
spec = []
for sex in ("m", "f"):
    y = f"e0_{sex}_2015"
    for k in range(len(POOL) + 1):
        for Z in itertools.combinations(POOL, k):
            r = fit(d, y, "doctors", Z)
            r.update(sex=sex, vars="+".join(Z), valid_A=backdoor_ok(DAGS["A_病床は中間"], Z),
                     valid_B=backdoor_ok(DAGS["B_病床は共通原因"], Z),
                     has_aged=("aged65" in Z), has_did=("did" in Z))
            spec.append(r)
spec = pd.DataFrame(spec); spec.to_csv(RES / "specification_curve.csv", index=False)
summ = spec.groupby(["sex", "valid_A"]).coef.describe()[["count", "min", "50%", "max"]]
print(summ.round(3)); summ.to_csv(RES / "spec_summary.csv")
sign = spec.groupby("sex").apply(lambda g: pd.Series({"pos": (g.coef > 0).mean(), "sig_pos": ((g.lo > 0)).mean(), "sig_neg": (g.hi < 0).mean()}))
print(sign.round(3)); sign.to_csv(RES / "spec_sign_share.csv")
# どの変数を入れると係数が動くか（入れる／入れないの平均の差）
eff = []
for sex in ("m", "f"):
    g = spec[spec.sex == sex]
    for v in POOL:
        inc = g.vars.str.split("+").apply(lambda s: v in s)
        eff.append({"sex": sex, "var": v, "with": g[inc].coef.mean(), "without": g[~inc].coef.mean(), "diff": g[inc].coef.mean() - g[~inc].coef.mean()})
eff = pd.DataFrame(eff); eff.to_csv(RES / "variable_inclusion_effect.csv", index=False)
print(eff.round(3).to_string())

# ---------- 相関（変数どうし）----------
cols = ["doctors", "e0_m_2015", "e0_f_2015"] + OBS
d[cols].corr().round(3).to_csv(RES / "correlations.csv")
print(d[cols].corr().round(2).loc[["doctors", "e0_m_2015", "e0_f_2015"]].to_string())

# ---------- 頑健性 ----------
REC = MIN + ["temp", "unemp"]
rob = []
def add(lab, sex, r): r.update(check=lab, sex=sex); rob.append(r)
REGION = {1: 1, **{i: 2 for i in range(2, 8)}, **{i: 3 for i in range(8, 15)}, **{i: 4 for i in range(15, 24)},
          **{i: 5 for i in range(24, 31)}, **{i: 6 for i in range(31, 40)}, **{i: 7 for i in range(40, 47)}, 47: 8}
dd = d.copy(); dd["region"] = dd.index.map(REGION)
rd = pd.get_dummies(dd["region"], prefix="r", drop_first=True).astype(float); dd = pd.concat([dd, rd], axis=1)
for sex in ("m", "f"):
    for lab, Z in (("調整なし", []), ("推奨セット", REC)):
        add(f"基本（医師2010→寿命2015）・{lab}", sex, fit(d, f"e0_{sex}_2015", "doctors", Z))
        new = d.copy()
        for v in OBS + ["doctors"]: new[v] = d[f"{v}_new"]
        add(f"新しい年（医師2022→寿命2020）・{lab}", sex, fit(new, f"e0_{sex}_2020", "doctors", Z))
        add(f"同じ年（医師2010→寿命2010）・{lab}", sex, fit(d, f"e0_{sex}_2010", "doctors", Z))
        add(f"65歳の平均余命・{lab}", sex, fit(d, f"e65_{sex}_2015", "doctors", Z))
        sub = d.drop(index=[13, 47])
        add(f"東京・沖縄を除く・{lab}", sex, fit(sub, f"e0_{sex}_2015", "doctors", Z))
        add(f"地方ブロックの違いを入れる・{lab}", sex, fit(dd, f"e0_{sex}_2015", "doctors", Z + list(rd.columns)))
        # 変化どうし：医師2010→2022 と 寿命2010→2020
        ch = pd.DataFrame({"dy": d[f"e0_{sex}_2020"] - d[f"e0_{sex}_2010"], "dx": d["doctors_new"] - d["doctors"],
                           "did": d["did_new"] - d["did"], "income": np.log(d["income_new"]) - np.log(d["income"]),
                           "aged65": d["aged65_new"] - d["aged65"], "univ_grad": d["univ_grad_new"] - d["univ_grad"],
                           "temp": d["temp"], "unemp": d["unemp"]})
        Zc = [] if lab == "調整なし" else ["did", "income", "univ_grad", "aged65", "temp", "unemp"]
        add(f"変化どうし（医師の増加→寿命の伸び）・{lab}", sex, fit(ch, "dy", "dx", Zc))
    # 1県ずつ除いたときの幅（推奨セット）
    loo = [fit(d.drop(index=i), f"e0_{sex}_2015", "doctors", REC)["coef"] for i in d.index]
    print(sex, "1県ずつ除く 推奨セットの係数", round(min(loo), 3), round(max(loo), 3))
    rob.append({"check": "1県ずつ除く（推奨セット）・最小〜最大", "sex": sex, "coef": float(np.median(loo)), "lo": min(loo), "hi": max(loo)})
rob = pd.DataFrame(rob); rob.to_csv(RES / "robustness.csv", index=False)
print(rob[["sex", "check", "coef", "lo", "hi", "p"]].round(3).to_string())
