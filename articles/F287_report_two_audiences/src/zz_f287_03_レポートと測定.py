"""03 レポートと測定：FY2025 の12か月で C（共通）・E（経営向け）・S（現場向け）を作り、
読む量・1枚で答えられる問い・要らない数字の割合・丸めの食い違いを測る。"""
import sys, os, json
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from zz_f287_common import (gen, kpis, month_view, report_C, report_E, report_S, Q_EXEC, q_store,
                            read_cost, answered_within, noise_share, text_of, FY25, DEPTS)
HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "results"); REP = os.path.join(HERE, "..", "reports")
os.makedirs(OUT, exist_ok=True); os.makedirs(REP, exist_ok=True)
BANDS = json.load(open(os.path.join(OUT, "bands.json")))


def measure(df, n, caps=(1000, 1500, 2500), save=False):
    g = kpis(df)
    b = BANDS[str(n)]
    rows = []
    for m in FY25:
        v = month_view(g, m, b)
        C = report_C(v, str(m)); E = report_E(v, str(m))
        if save and str(m) == "2025-10":
            open(os.path.join(REP, "C_共通版_2025-10.md"), "w").write(text_of(C))
            open(os.path.join(REP, "E_経営向け_2025-10.md"), "w").write(text_of(E))
            for s in ["S01", "S07"]:
                open(os.path.join(REP, f"S_現場向け_{s}_2025-10.md"), "w").write(text_of(report_S(v, str(m), s)))
        for mode in ["linear", "jump"]:
            rows.append(dict(month=str(m), reader="経営", report="C", mode=mode, cost=read_cost(C, Q_EXEC, mode),
                             noise=noise_share(C, Q_EXEC), total=sum(x["chars"] for x in C),
                             **{f"ans{c}": answered_within(C, Q_EXEC, c) for c in caps}))
            rows.append(dict(month=str(m), reader="経営", report="E", mode=mode, cost=read_cost(E, Q_EXEC, mode),
                             noise=noise_share(E, Q_EXEC), total=sum(x["chars"] for x in E),
                             **{f"ans{c}": answered_within(E, Q_EXEC, c) for c in caps}))
            for s in v["store"]:
                Q = q_store(s); S = report_S(v, str(m), s)
                rows.append(dict(month=str(m), reader="店長", store=s, report="C", mode=mode, cost=read_cost(C, Q, mode),
                                 noise=noise_share(C, Q), total=sum(x["chars"] for x in C),
                                 **{f"ans{c}": answered_within(C, Q, c) for c in caps}))
                rows.append(dict(month=str(m), reader="店長", store=s, report="S", mode=mode, cost=read_cost(S, Q, mode),
                                 noise=noise_share(S, Q), total=sum(x["chars"] for x in S),
                                 **{f"ans{c}": answered_within(S, Q, c) for c in caps}))
                rows.append(dict(month=str(m), reader="店長", store=s, report="E", mode=mode, cost=read_cost(E, Q, mode),
                                 noise=noise_share(E, Q), total=sum(x["chars"] for x in E),
                                 **{f"ans{c}": answered_within(E, Q, c) for c in caps}))
    return pd.DataFrame(rows)


def lr_round(vals, total_rounded, step):
    """最大剰余法：部分の丸めの合計が、丸めた合計と一致するように丸める。"""
    q = np.array(vals) / step
    fl = np.floor(q); rem = q - fl
    k = int(round(total_rounded / step - fl.sum()))
    idx = np.argsort(-rem)[:max(k, 0)]
    fl[idx] += 1
    return fl * step


def rounding(df, n):
    g = kpis(df); rows = []
    for m in FY25:
        ms = str(m)
        tot = g["co"].loc[ms, "sales"]
        dep = np.array([g["dept"].loc[(d, ms)].sales for d in DEPTS]) / 100  # 億円
        sto = np.array([g["store"].loc[(s, ms)].sales for s in g["size"].index])  # 百万円
        shr = dep / dep.sum() * 100
        # 別々に丸める
        t1 = round(round(tot / 100, 1) - np.round(dep, 1).sum(), 2) != 0
        t2 = round(np.round(tot, 0) - np.round(sto, 0).sum(), 2) != 0
        t3 = round(100 - np.round(shr, 0).sum(), 2) != 0
        # 最大剰余法
        l1 = abs(round(tot / 100, 1) - lr_round(dep, round(tot / 100, 1), 0.1).sum()) > 1e-9
        l2 = abs(np.round(tot, 0) - lr_round(sto, np.round(tot, 0), 1).sum()) > 1e-9
        l3 = abs(100 - lr_round(shr, 100, 1).sum()) > 1e-9
        rows.append(dict(month=ms, dept_oku=t1, store_mil=t2, share_pct=t3, any=(t1 or t2 or t3),
                         lr_any=(l1 or l2 or l3),
                         dept_gap=round(round(tot / 100, 1) - np.round(dep, 1).sum(), 2),
                         store_gap=round(np.round(tot, 0) - np.round(sto, 0).sum(), 2),
                         share_gap=round(100 - np.round(shr, 0).sum(), 2)))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = pd.read_csv(os.path.join(HERE, "..", "data", "midorido_monthly.csv"))
    M = measure(df, 12, save=True)
    M.to_csv(os.path.join(OUT, "A_measure.csv"), index=False)
    R = rounding(df, 12)
    R.to_csv(os.path.join(OUT, "B_rounding.csv"), index=False)
    lin = M[M["mode"] == "linear"]
    ex = lin[lin.reader == "経営"]; st = lin[lin.reader == "店長"]
    res = {}
    res["exec_cost_median"] = ex.groupby("report").cost.median().to_dict()
    res["exec_cost_ratio_C_over_E"] = res["exec_cost_median"]["C"] / res["exec_cost_median"]["E"]
    res["store_cost_median"] = st.dropna(subset=["cost"]).groupby("report").cost.median().to_dict()
    res["store_cost_ratio_C_over_S"] = res["store_cost_median"]["C"] / res["store_cost_median"]["S"]
    res["store_E_answerable_mean"] = float(st[st.report == "E"].ans1500.mean())
    for c in [1000, 1500, 2500]:
        res[f"exec_ans{c}"] = (ex.groupby("report")[f"ans{c}"].mean() / 8).to_dict()
        res[f"store_ans{c}"] = (st.groupby("report")[f"ans{c}"].mean() / 8).to_dict()
        res[f"store_ans{c}_C_by_store"] = (st[st.report == "C"].groupby("store")[f"ans{c}"].mean() / 8).to_dict()
    res["exec_noise"] = ex.groupby("report").noise.mean().to_dict()
    res["store_noise"] = st.groupby("report").noise.mean().to_dict()
    res["total_chars"] = lin.groupby("report").total.median().to_dict()
    jm = M[M["mode"] == "jump"]
    res["jump_exec_cost_median"] = jm[jm.reader == "経営"].groupby("report").cost.median().to_dict()
    res["jump_exec_ratio"] = res["jump_exec_cost_median"]["C"] / res["jump_exec_cost_median"]["E"]
    res["jump_store_cost_median"] = jm[jm.reader == "店長"].dropna(subset=["cost"]).groupby("report").cost.median().to_dict()
    res["jump_store_ratio"] = res["jump_store_cost_median"]["C"] / res["jump_store_cost_median"]["S"]
    res["rounding_months_any"] = int(R["any"].sum()); res["rounding_months_lr"] = int(R["lr_any"].sum())
    res["rounding_by_table"] = {k: int(R[k].sum()) for k in ["dept_oku", "store_mil", "share_pct"]}
    # 仮説の判定
    res["H1"] = res["exec_cost_ratio_C_over_E"] >= 3
    res["H2"] = (res["store_ans1500"]["C"] < 0.5) and (res["store_ans1500"]["S"] == 1.0)
    res["H3"] = (res["rounding_months_any"] / 12 >= 0.3) and (res["rounding_months_lr"] == 0)
    res["H4"] = (res["exec_noise"]["C"] >= 0.7) and (res["exec_noise"]["E"] < 0.3)
    json.dump(res, open(os.path.join(OUT, "main.json"), "w"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=float))
