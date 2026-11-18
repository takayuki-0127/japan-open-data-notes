"""03_analysis.py：前年同期比の「とび」を、4〜6月期とほかの期で比べる。資本金の食い違いも見る。
乱数は使わない。結果は results/ に出す。"""
import json, pathlib
import numpy as np
import pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; R.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "quarterly_long.csv")
d["t"] = d["year"] * 4 + d["q"] - 1  # 連続の四半期番号

PRE = (1990, 2008)
POST = (2010, 2026)
ITEMS = ["sales", "employees", "ordinary_profit", "capex_ex_sw", "capex"]


def add_yoy(g):
    g = g.sort_values("t").copy()
    s = g.set_index("t")["value"]
    g["yoy"] = (100 * (s / s.shift(4) - 1)).reindex(g["t"]).values  # t−4 が欠けていれば NaN
    # shift は位置で動くので、t が連続していることを確かめる
    assert (np.diff(g["t"].values) == 1).all()
    g["jump"] = g["yoy"].diff()
    return g


flows = d[d["item"].isin(ITEMS)]
parts = []
for (it, ind, sz), g in flows.groupby(["item", "industry", "size"], sort=True):
    parts.append(add_yoy(g))
J = pd.concat(parts, ignore_index=True)
J["is_q2"] = J["q"] == 2
J.round(4).to_csv(R / "yoy_jumps.csv", index=False)


def ratio(sub, how="mean"):
    a = sub.loc[sub["is_q2"], "jump"].abs().dropna()
    b = sub.loc[~sub["is_q2"], "jump"].abs().dropna()
    f = np.mean if how == "mean" else np.median
    if len(a) == 0 or len(b) == 0:
        return dict(n_q2=0)
    p = stats.mannwhitneyu(a, b, alternative="greater").pvalue
    return dict(n_q2=len(a), n_other=len(b), q2=float(f(a)), other=float(f(b)), ratio=float(f(a) / f(b)), p_mw=float(p))


def window(sub, y0, y1, drop=()):
    s = sub[(sub["year"] >= y0) & (sub["year"] <= y1)]
    if drop:
        s = s[~s["year"].isin(drop)]
    return s


rows = []
for (it, ind, sz), g in J.groupby(["item", "industry", "size"], sort=True):
    for per, (y0, y1) in {"pre_1990_2008": PRE, "post_2010_2026": POST}.items():
        r = ratio(window(g, y0, y1))
        if r.get("n_q2"):
            rows.append(dict(item=it, industry=ind, size=sz, period=per, **r))
T = pd.DataFrame(rows)
T.round(4).to_csv(R / "jump_ratios.csv", index=False)


def get(it, sz, per, ind="all_ex_fin", col="ratio"):
    v = T[(T["item"] == it) & (T["size"] == sz) & (T["period"] == per) & (T["industry"] == ind)][col]
    return round(float(v.iloc[0]), 3)


# 頑健性
rob = []
def rob_add(name, it, sz, sub_fn, how="mean", ind="all_ex_fin"):
    g = J[(J["item"] == it) & (J["size"] == sz) & (J["industry"] == ind)]
    r = ratio(sub_fn(g), how)
    rob.append(dict(check=name, item=it, size=sz, industry=ind, q2=round(r["q2"], 3), other=round(r["other"], 3),
                    ratio=round(r["ratio"], 3), p_mw=round(r["p_mw"], 4), n_q2=r["n_q2"]))

for it in ["sales", "employees"]:
    for sz in ["B", "D"]:
        rob_add("本線 2010〜2026年", it, sz, lambda g: window(g, *POST))
        rob_add("2020〜2021年を除く", it, sz, lambda g: window(g, *POST, drop=(2020, 2021)))
        rob_add("2010・2011・2020・2021年を除く", it, sz, lambda g: window(g, *POST, drop=(2010, 2011, 2020, 2021)))
        rob_add("中央値で比べる", it, sz, lambda g: window(g, *POST), how="median")
        rob_add("製造業だけ", it, sz, lambda g: window(g, *POST), ind="manufacturing")
        rob_add("非製造業だけ", it, sz, lambda g: window(g, *POST), ind="non_manufacturing")
        rob_add("入れ替え前 1990〜2008年", it, sz, lambda g: window(g, *PRE))
        rob_add("入れ替え前を2000〜2008年に短く", it, sz, lambda g: window(g, 2000, 2008))
RB = pd.DataFrame(rob)
RB.to_csv(R / "robustness.csv", index=False)

# 資本金：前期末資本金（今の期の標本が答えた値）と、前の期に公表された資本金の食い違い（％）
cap = d[d["item"].isin(["capital", "capital_prev_end"])].pivot_table(index=["industry", "size", "t", "year", "q"], columns="item", values="value").reset_index()
cap = cap.sort_values(["industry", "size", "t"])
cap["cap_lag"] = cap.groupby(["industry", "size"])["capital"].shift(1)
cap["t_lag"] = cap.groupby(["industry", "size"])["t"].shift(1)
cap = cap[cap["t"] - cap["t_lag"] == 1].copy()
cap["gap_pct"] = 100 * (cap["capital_prev_end"] / cap["cap_lag"] - 1)
cap["is_q2"] = cap["q"] == 2
cap[["industry", "size", "year", "q", "capital", "capital_prev_end", "cap_lag", "gap_pct"]].round(4).to_csv(R / "capital_gap.csv", index=False)
crow = []
for sz in "ABCD":
    for per, (y0, y1) in {"pre_1990_2008": PRE, "post_2010_2026": POST}.items():
        s = cap[(cap["industry"] == "all_ex_fin") & (cap["size"] == sz) & (cap["year"] >= y0) & (cap["year"] <= y1)]
        a = s.loc[s["is_q2"], "gap_pct"].abs(); b = s.loc[~s["is_q2"], "gap_pct"].abs()
        crow.append(dict(size=sz, period=per, q2_mean_abs=round(a.mean(), 3), other_mean_abs=round(b.mean(), 3),
                         ratio=round(a.mean() / b.mean(), 3), q2_median_abs=round(a.median(), 3), other_median_abs=round(b.median(), 3),
                         q2_mean_signed=round(s.loc[s["is_q2"], "gap_pct"].mean(), 3)))
CG = pd.DataFrame(crow); CG.to_csv(R / "capital_gap_summary.csv", index=False)

# 公表の前年同期比との照合（2026年4〜6月期、全産業（金融業・保険業を除く）、全規模）
def yoy_at(it, y, q, sz="A"):
    s = J[(J["item"] == it) & (J["industry"] == "all_ex_fin") & (J["size"] == sz) & (J["year"] == y) & (J["q"] == q)]
    return round(float(s["yoy"].iloc[0]), 2)

chk = {"sales": (yoy_at("sales", 2026, 2), 5.9), "ordinary_profit": (yoy_at("ordinary_profit", 2026, 2), 24.6), "capex": (yoy_at("capex", 2026, 2), 1.6)}

# 法人数（母集団）の変わり方：D は4〜6月期だけ変わるか
corp = d[(d["item"] == "corporations") & (d["industry"] == "all_ex_fin")].sort_values(["size", "t"]).copy()
corp["chg"] = corp.groupby("size")["value"].diff()
cz = {}
for sz in "BD":
    s = corp[(corp["size"] == sz) & (corp["year"] >= 2010)]
    cz[sz] = dict(share_nonzero_q2=round(float((s.loc[s["q"] == 2, "chg"] != 0).mean()), 3),
                  share_nonzero_other=round(float((s.loc[s["q"] != 2, "chg"] != 0).mean()), 3))
    pct = 100 * corp.loc[corp["size"] == sz, "value"].pct_change()
    cz[sz]["q2_mean_pct_change_2010_2026"] = round(float(pct[(corp["size"] == sz) & (corp["year"] >= 2010) & (corp["q"] == 2)].mean()), 3)

main = {
    "published_yoy_check_2026q2": {k: {"computed": v[0], "published": v[1]} for k, v in chk.items()},
    "sales_ratio": {sz: {"post": get("sales", sz, "post_2010_2026"), "pre": get("sales", sz, "pre_1990_2008")} for sz in "ABCD"},
    "employees_ratio": {sz: {"post": get("employees", sz, "post_2010_2026"), "pre": get("employees", sz, "pre_1990_2008")} for sz in "ABCD"},
    "capex_ex_sw_ratio": {sz: {"post": get("capex_ex_sw", sz, "post_2010_2026"), "pre": get("capex_ex_sw", sz, "pre_1990_2008")} for sz in "ABCD"},
    "ordinary_profit_ratio": {sz: {"post": get("ordinary_profit", sz, "post_2010_2026"), "pre": get("ordinary_profit", sz, "pre_1990_2008")} for sz in "ABCD"},
    "D_sales_q2_mean_abs": {"post": get("sales", "D", "post_2010_2026", col="q2"), "pre": get("sales", "D", "pre_1990_2008", col="q2")},
    "D_sales_other_mean_abs": {"post": get("sales", "D", "post_2010_2026", col="other"), "pre": get("sales", "D", "pre_1990_2008", col="other")},
    "D_emp_q2_mean_abs": {"post": get("employees", "D", "post_2010_2026", col="q2"), "pre": get("employees", "D", "pre_1990_2008", col="q2")},
    "D_emp_other_mean_abs": {"post": get("employees", "D", "post_2010_2026", col="other"), "pre": get("employees", "D", "pre_1990_2008", col="other")},
    "B_sales_q2_mean_abs": {"post": get("sales", "B", "post_2010_2026", col="q2"), "pre": get("sales", "B", "pre_1990_2008", col="q2")},
    "B_sales_other_mean_abs": {"post": get("sales", "B", "post_2010_2026", col="other"), "pre": get("sales", "B", "pre_1990_2008", col="other")},
    "p_mw": {f"{it}_{sz}_post": get(it, sz, "post_2010_2026", col="p_mw") for it in ["sales", "employees"] for sz in "BD"},
    "capital_gap": CG.set_index(["size", "period"]).to_dict(orient="index").__repr__(),
    "corporations_change_share": cz,
}
main["capital_gap"] = {f"{r['size']}_{r['period']}": {k: r[k] for k in ["q2_mean_abs", "other_mean_abs", "ratio", "q2_mean_signed"]} for r in crow}
H = {}
H["H1"] = dict(value=main["sales_ratio"]["D"]["post"], rule=">=1.5", supported=main["sales_ratio"]["D"]["post"] >= 1.5)
H["H2"] = dict(value=main["sales_ratio"]["B"]["post"], rule="<1.3", supported=main["sales_ratio"]["B"]["post"] < 1.3)
H["H3"] = dict(value_pre=main["D_sales_q2_mean_abs"]["pre"], value_post=main["D_sales_q2_mean_abs"]["post"], rule="post<pre",
               supported=main["D_sales_q2_mean_abs"]["post"] < main["D_sales_q2_mean_abs"]["pre"])
H["H4"] = dict(value=main["employees_ratio"]["D"]["post"], rule=">=1.5", supported=main["employees_ratio"]["D"]["post"] >= 1.5)
main["hypotheses"] = {k: {kk: (bool(vv) if isinstance(vv, (bool, np.bool_)) else vv) for kk, vv in v.items()} for k, v in H.items()}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
print(json.dumps(main, ensure_ascii=False, indent=1))
print(RB.to_string())
