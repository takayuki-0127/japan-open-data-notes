"""05 頑健性と問い直し。
頑健性：店の数 6・24、乱数の種20通り（丸めの食い違い）、丸めの単位。
問い直し（結果を見た後に追加）：経営向けに絞ったとき、入れておいた本当の動きは何か月で例外の欄に出たか、
入れていない動き（空振り）はどれだけ出たか。"""
import sys, os, json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from zz_f287_common import gen, kpis, month_view, events, FY25, DEPTS
import importlib
m03 = importlib.import_module("zz_f287_03_レポートと測定")
HERE = os.path.dirname(__file__); OUT = os.path.join(HERE, "..", "results")
BANDS = json.load(open(os.path.join(OUT, "bands.json")))
rows = []
# 1) 店の数
for n in [6, 12, 24]:
    M = m03.measure(gen(287, n), n)
    lin = M[M["mode"] == "linear"]
    ex = lin[lin.reader == "経営"].groupby("report"); st = lin[lin.reader == "店長"].dropna(subset=["cost"]).groupby("report")
    stall = lin[lin.reader == "店長"].groupby("report")
    rows.append(dict(cond=f"店の数{n}", exec_ratio=ex.cost.median()["C"] / ex.cost.median()["E"],
                     store_ratio=st.cost.median()["C"] / st.cost.median()["S"],
                     store_ans1500_C=stall.ans1500.mean()["C"] / 8, store_ans1500_S=stall.ans1500.mean()["S"] / 8,
                     exec_noise_C=ex.noise.mean()["C"], exec_noise_E=ex.noise.mean()["E"],
                     C_chars=lin[lin.report == "C"].total.median()))
# 2) 乱数の種20通り：丸めの食い違いの月の数
rd = []
for sd in range(20):
    R = m03.rounding(gen(5000 + sd, 12), 12)
    rd.append(dict(seed=5000 + sd, any=int(R["any"].sum()), lr=int(R["lr_any"].sum()),
                   dept=int(R.dept_oku.sum()), store=int(R.store_mil.sum()), share=int(R.share_pct.sum())))
rd = pd.DataFrame(rd); rd.to_csv(os.path.join(OUT, "C_rounding_seeds.csv"), index=False)


# 3) 丸めの単位を変える
def rounding_units(df, step_dept_oku, store_mult, step_share):
    """部門は億円で step_dept_oku 刻み、店は（百万円×store_mult）の整数、構成比は step_share %刻みで丸める。"""
    g = kpis(df); cnt = 0
    r = lambda x, st: np.round(np.asarray(x) / st) * st
    for m in FY25:
        ms = str(m); tot = g["co"].loc[ms, "sales"]
        dep = np.array([g["dept"].loc[(d, ms)].sales for d in DEPTS]) / 100
        sto = np.array([g["store"].loc[(s, ms)].sales for s in g["size"].index]) * store_mult
        shr = dep / dep.sum() * 100
        t1 = abs(r(tot / 100, step_dept_oku) - r(dep, step_dept_oku).sum()) > 1e-9
        t2 = abs(r(tot * store_mult, 1) - r(sto, 1).sum()) > 1e-9
        t3 = abs(100 - r(shr, step_share).sum()) > 1e-9
        cnt += int(t1 or t2 or t3)
    return cnt


df12 = gen(287, 12)
units = {"基本（億円0.1・百万円1・%1）": rounding_units(df12, 0.1, 1, 1),
         "細かく（億円0.01・千円1・%0.1）": rounding_units(df12, 0.01, 1000, 0.1),
         "粗く（億円1・億円0.1・%5）": rounding_units(df12, 1.0, 0.1, 5)}
# 4) 問い直し：経営向けの例外の欄に、本当の動きが出たか（動きの後の月で、その店・部門が幅の外と判定された割合）
rq = []
for sd in range(20):
    seed = 7000 + sd
    g = kpis(gen(seed, 12)); ev = events(12)
    s_drop, m_drop, _ = ev["cust_drop"]; s_cafe, m_cafe, _ = ev["cafe_up"]; d_mg, m_mg, _ = ev["zakka_margin"]
    hit = {"客数の落ち込み": [], "雑貨の粗利率": [], "カフェの伸び（店）": [], "カフェの伸び（部門）": []}
    first = {"客数の落ち込み": None, "雑貨の粗利率": None}
    null_flags = []; null_dept = []
    for m in FY25:
        v = month_view(g, m, BANDS["12"])
        outs = {s for s in v["store"] if v["store"][s]["out"]}
        od = {d for d in DEPTS if v["dept"][d]["out"]}
        if m >= m_drop:
            hit["客数の落ち込み"].append(s_drop in outs)
            if s_drop in outs and first["客数の落ち込み"] is None:
                first["客数の落ち込み"] = (m - m_drop).n
        if m >= m_mg:
            hit["雑貨の粗利率"].append(d_mg in od)
            if d_mg in od and first["雑貨の粗利率"] is None:
                first["雑貨の粗利率"] = (m - m_mg).n
        if m >= m_cafe:
            hit["カフェの伸び（店）"].append(s_cafe in outs)
            hit["カフェの伸び（部門）"].append("カフェ" in od)
        # 動きを入れていない店（落ち込み・カフェの店以外）の判定＝空振り
        null_flags += [s in outs for s in v["store"] if s not in (s_drop, s_cafe)]
        null_dept += [d in od for d in ["文具", "書籍"]]  # 動きを入れていない部門
    rq.append(dict(seed=seed, **{f"hit_{k}": float(np.mean(x)) for k, x in hit.items()},
                   **{f"lag_{k}": x for k, x in first.items()}, null_flag_rate=float(np.mean(null_flags)),
                   null_dept_rate=float(np.mean(null_dept))))
rq = pd.DataFrame(rq); rq.to_csv(os.path.join(OUT, "D_reask_seeds.csv"), index=False)
res = dict(by_nstores=rows, rounding_seeds=dict(any_median=float(rd["any"].median()), any_min=int(rd["any"].min()),
                                                any_max=int(rd["any"].max()), share_ge30=float((rd["any"] >= 4).mean()),
                                                lr_max=int(rd.lr.max())),
           rounding_units=units,
           reask=dict(hit_rate={c[4:]: float(rq[c].mean()) for c in rq.columns if c.startswith("hit_")},
                      lag_median={c[4:]: float(rq[c].median()) for c in rq.columns if c.startswith("lag_")},
                      lag_max={c[4:]: float(rq[c].max()) for c in rq.columns if c.startswith("lag_")},
                      hit_range={c[4:]: [float(rq[c].min()), float(rq[c].max())] for c in rq.columns if c.startswith("hit_")},
                      null_flag_rate=float(rq.null_flag_rate.mean()),
                      null_flag_range=[float(rq.null_flag_rate.min()), float(rq.null_flag_rate.max())],
                      null_dept_rate=float(rq.null_dept_rate.mean()),
                      null_dept_range=[float(rq.null_dept_rate.min()), float(rq.null_dept_rate.max())]))
pd.DataFrame(rows).to_csv(os.path.join(OUT, "E_robust_nstores.csv"), index=False)
json.dump(res, open(os.path.join(OUT, "robust_reask.json"), "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(res, ensure_ascii=False, indent=1, default=float))
