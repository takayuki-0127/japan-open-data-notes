"""偶数月（年金の支給月）の上乗せを、対照の世帯との対数の差で測る。結果は results/ に書く。乱数は使わない。"""
import json, pathlib
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "monthly_groups.csv")
W = d.pivot_table(index=["year", "month"], columns=["group", "item"], values="value").sort_index()
# 食料（外食を除く）を足す
for g in sorted({g for g, _ in W.columns}):
    if (g, "食料") in W.columns and (g, "外食") in W.columns:
        W[(g, "食料（外食を除く）")] = W[(g, "食料")] - W[(g, "外食")]
W = W.sort_index(axis=1)
idx = W.index.to_frame(index=False)
EVEN = (idx.month % 2 == 0).to_numpy()

ITEMS = ["食料（外食を除く）", "外食", "住居", "光熱・水道", "家具・家事用品", "被服及び履物", "交通・通信", "教養娯楽",
         "交際費", "その他の消費支出"]
DISC = ["教養娯楽", "交際費", "外食", "被服及び履物"]      # 後回しにできる支出（H3）
BASIC = ["食料（外食を除く）", "光熱・水道"]               # 毎月ほぼ決まった支出（H3）


def series(target, control, item, keep=None):
    s = pd.DataFrame({"year": idx.year, "month": idx.month,
                      "d": np.log(W[(target, item)].to_numpy()) - np.log(W[(control, item)].to_numpy())})
    s["even"] = (s.month % 2 == 0).astype(int)
    s["t"] = np.arange(len(s))
    if keep is not None:
        s = s[keep(s)].reset_index(drop=True)
    return s


def reg(s):
    """d = a + b*偶数月 + 年の固定効果。Newey-West（ラグ3）。b×100 を % とする。"""
    m = smf.ols("d ~ even + C(year)", data=s).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    b, se = m.params["even"], m.bse["even"]
    return {"pct": 100 * b, "lo": 100 * (b - 1.96 * se), "hi": 100 * (b + 1.96 * se), "n": int(m.nobs)}


def local(s):
    """偶数月の d と、すぐ前後の奇数月の d の平均との差（前後がそろう偶数月だけ）。"""
    full = s.set_index("t").d
    vals = [full[t] - (full[t - 1] + full[t + 1]) / 2 for t, e in zip(s.t, s.even)
            if e == 1 and (t - 1) in full.index and (t + 1) in full.index]
    v = np.array(vals)
    se = v.std(ddof=1) / np.sqrt(len(v))
    return {"pct": 100 * v.mean(), "lo": 100 * (v.mean() - 1.96 * se), "hi": 100 * (v.mean() + 1.96 * se), "n": len(v)}


T, CTRL = "m65_nowork", "u65_worker"
out = {"period": "2015年1月〜2026年9月", "months": int(len(W)), "target": T, "control": CTRL}

# H1：年金の入り方（暦年で12か月そろう2015〜2025年）
pen = W[(T, "公的年金給付")].reset_index(name="pension")
pen = pen[pen.year <= 2025]
share = pen.assign(even=pen.month % 2 == 0).groupby("year").apply(
    lambda g: g.loc[g.even, "pension"].sum() / g.pension.sum(), include_groups=False)
share = share.rename("even_share").reset_index()
share.to_csv(RES / "pension_even_share_by_year.csv", index=False, float_format="%.5f")
out["H1"] = {"even_share_min": float(share.even_share.min()), "even_share_mean": float(share.even_share.mean()),
             "pension_even_mean_yen": float(pen[pen.month % 2 == 0].pension.mean()),
             "pension_odd_mean_yen": float(pen[pen.month % 2 == 1].pension.mean())}
out["H1"]["verdict"] = "支持" if out["H1"]["even_share_min"] >= 0.90 else "外れ"

# H2：消費支出
s = series(T, CTRL, "消費支出")
out["H2"] = {"reg": reg(s), "local": local(s)}
r = out["H2"]["reg"]
out["H2"]["verdict"] = "支持" if (r["pct"] >= 1 and r["lo"] > 0) else "外れ"
# 参考：対照なしで、年金の世帯だけの偶数月と奇数月の差（季節がまざる）
raw = pd.DataFrame({"year": idx.year, "month": idx.month, "d": np.log(W[(T, "消費支出")].to_numpy())})
raw["even"] = (raw.month % 2 == 0).astype(int)
raw["t"] = np.arange(len(raw))
out["H2"]["target_only_reg"] = reg(raw)
for g in [T, CTRL]:
    lv = pd.DataFrame({"month": idx.month, "v": W[(g, "消費支出")].to_numpy()})
    out[f"cons_by_calmonth_{g}"] = {int(k): float(v) for k, v in lv.groupby("month").v.mean().items()}

# 月ごとの差（図用）
s_out = s.copy()
s_out["d_pct"] = 100 * (s_out.d - s_out.d.mean())
s_out[["year", "month", "even", "d_pct"]].to_csv(RES / "monthly_logdiff_consumption.csv", index=False, float_format="%.4f")
cal = s.assign(dd=100 * (s.d - s.groupby("year").d.transform("mean"))).groupby("month").dd.agg(["mean", "std", "count"])
cal.reset_index().to_csv(RES / "calmonth_logdiff_consumption.csv", index=False, float_format="%.4f")

# H3：費目
rows = []
for it in ITEMS:
    s_i = series(T, CTRL, it)
    a, b = reg(s_i), local(s_i)
    rows.append({"item": it, "group": "後回しにできる" if it in DISC else ("毎月ほぼ決まった" if it in BASIC else "その他"),
                 "pct": a["pct"], "lo": a["lo"], "hi": a["hi"], "local_pct": b["pct"],
                 "target_mean_yen": float(W[(T, it)].mean())})
items = pd.DataFrame(rows)
items.to_csv(RES / "item_effects.csv", index=False, float_format="%.4f")
disc = items[items.item.isin(DISC)].pct.mean()
basic = items[items.item.isin(BASIC)].pct.mean()
# 金額で重みをつけた平均も
wdisc = np.average(items[items.item.isin(DISC)].pct, weights=items[items.item.isin(DISC)].target_mean_yen)
wbasic = np.average(items[items.item.isin(BASIC)].pct, weights=items[items.item.isin(BASIC)].target_mean_yen)
out["H3"] = {"disc_mean_pct": float(disc), "basic_mean_pct": float(basic), "disc_wmean_pct": float(wdisc),
             "basic_wmean_pct": float(wbasic), "diff_pt": float(disc - basic),
             "verdict_rule": "支持" if disc > basic else "外れ",
             "verdict": "判定できず（基準の上では支持だが差は0.01ポイント未満。金額の重みでは逆転）"
             if (disc > basic and abs(disc - basic) < 0.01 and wdisc < wbasic) else ("支持" if disc > basic else "外れ")}

# H4：大きさ（円）
cons_mean = float(W[(T, "消費支出")].mean())
extra_cons = cons_mean * (np.exp(r["pct"] / 100) - 1)
extra_pen = out["H1"]["pension_even_mean_yen"] - out["H1"]["pension_odd_mean_yen"]
out["H4"] = {"cons_mean_yen": cons_mean, "extra_cons_yen": float(extra_cons), "extra_pension_yen": float(extra_pen),
             "ratio": float(extra_cons / extra_pen)}
out["H4"]["verdict"] = "支持" if out["H4"]["ratio"] < 0.10 else "外れ"
# 2か月を1組にした見方：受け取りの月の上乗せは、2か月の消費の合計の何%か
out["H4"]["extra_share_of_2month_cons_pct"] = float(100 * extra_cons / (2 * cons_mean))

# 頑健性
rob = []
def add(name, s_):
    a, b = reg(s_), local(s_)
    rob.append({"check": name, "pct": a["pct"], "lo": a["lo"], "hi": a["hi"], "n": a["n"], "local_pct": b["pct"],
                "local_lo": b["lo"], "local_hi": b["hi"]})
add("本線：65歳以上・無職 − 65歳未満・勤労者", series(T, CTRL, "消費支出"))
add("対照を二人以上の世帯全体に", series(T, "all_2plus", "消費支出"))
add("対照を65歳以上・勤労者世帯に", series(T, "m65_worker", "消費支出"))
add("1・6・7・12月を除く", series(T, CTRL, "消費支出", keep=lambda x: ~x.month.isin([1, 6, 7, 12])))
add("2020・2021年を除く", series(T, CTRL, "消費支出", keep=lambda x: ~x.year.isin([2020, 2021])))
add("調べる世帯を高齢夫婦の無職世帯に", series("couple_nowork", CTRL, "消費支出"))
add("2015〜2019年だけ", series(T, CTRL, "消費支出", keep=lambda x: x.year <= 2019))
add("2022〜2026年だけ", series(T, CTRL, "消費支出", keep=lambda x: x.year >= 2022))
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False, float_format="%.4f")
out["robustness"] = rob.to_dict(orient="records")

# 問い直し1：預貯金の出し入れ（年金の世帯の中で、偶数月と奇数月の差。円）
dep = []
for it in ["預貯金", "預貯金引出", "実収入", "公的年金給付", "消費支出"]:
    v = pd.DataFrame({"year": idx.year, "month": idx.month, "v": W[(T, it)].to_numpy()})
    v["even"] = v.month % 2 == 0
    m = smf.ols("v ~ even + C(year)", data=v.assign(even=v.even.astype(int))).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    dep.append({"item": it, "even_mean_yen": float(v[v.even].v.mean()), "odd_mean_yen": float(v[~v.even].v.mean()),
                "even_minus_odd_yen": float(m.params["even"]), "lo": float(m.params["even"] - 1.96 * m.bse["even"]),
                "hi": float(m.params["even"] + 1.96 * m.bse["even"])})
dep = pd.DataFrame(dep)
dep.to_csv(RES / "requestion_deposits.csv", index=False, float_format="%.1f")
out["requestion_deposits"] = dep.to_dict(orient="records")
dd = dep.set_index("item").even_minus_odd_yen
out["requestion_deposits_summary"] = {
    "net_deposit_even_minus_odd_yen": float(dd["預貯金"] - dd["預貯金引出"]),
    "net_deposit_share_of_extra_pension": float((dd["預貯金"] - dd["預貯金引出"]) / dd["公的年金給付"])}

# 問い直し2：年間収入の3区分
inc = []
for g, lab in [("eld_nowork_inc1", "250万円未満"), ("eld_nowork_inc2", "250〜349万円"), ("eld_nowork_inc3", "350万円以上"),
               ("eld_nowork", "高齢者のみの無職世帯（計）")]:
    a = reg(series(g, CTRL, "消費支出"))
    inc.append({"group": lab, **a, "households_mean": float(W[(g, "集計世帯数")].mean()),
                "pension_share_of_income": float(W[(g, "公的年金給付")].sum() / W[(g, "実収入")].sum())})
inc = pd.DataFrame(inc)
inc.to_csv(RES / "requestion_income.csv", index=False, float_format="%.4f")
out["requestion_income"] = inc.to_dict(orient="records")

out["households_mean"] = {g: float(W[(g, "集計世帯数")].mean()) for g in [T, CTRL, "m65_worker", "couple_nowork"]}
out["head_age_mean"] = {g: float(W[(g, "世帯主の年齢")].mean()) for g in [T, CTRL]}
out["pension_share_of_income_target"] = float(W[(T, "公的年金給付")].sum() / W[(T, "実収入")].sum())


def rnd(o):
    if isinstance(o, float):
        return round(o, 6)
    if isinstance(o, dict):
        return {k: rnd(v) for k, v in o.items()}
    if isinstance(o, list):
        return [rnd(v) for v in o]
    return o


(RES / "main.json").write_text(json.dumps(rnd(out), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(json.dumps(rnd({k: out[k] for k in ["H1", "H2", "H3", "H4"]}), ensure_ascii=False, indent=1))
print(rob.round(2).to_string())
print(items.round(2).to_string())
print(dep.round(0).to_string())
print(inc.round(2).to_string())
