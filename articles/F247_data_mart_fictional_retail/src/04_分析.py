"""04 分析：手当てを1つずつ抜いたら KPI がどれだけ狂うか、テストで見つかるか（サンプルマート（架空）、合成データ）

B：シナリオ別の KPI（FY2025）と正解（F246 のデータ）とのずれ
C：シナリオ × テストの表（どのテストがどの汚れを見つけるか）
D：月次の締めの日（3日・5日・10日）と、締めの数字があとでどれだけ直るか
E：頑健性：乱数の種 0〜19、汚れの割合 ×0.5・×2、人時の埋め方
"""
import importlib.util, json, pathlib, sys
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"


def _load(name):
    spec = importlib.util.spec_from_file_location(name.split("_")[0] + "m", ROOT / "src" / name)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


G = _load("02_整形.py")
M = _load("03_整える.py")
ST, CA, DD = M.load_dims()
SUMS = ["sales", "receipts", "items", "gross_profit_before_waste", "waste", "gross_profit", "labor_hours", "labor_cost", "other_cost"]


def truth_mart():
    t = G.load_truth()
    fsd = t["fsd"].rename(columns={"date": "biz_date"})
    fsd["labor_imputed"] = 0
    acct = pd.read_csv(ROOT / "data" / "raw_synth" / "acct_store_month.csv")
    sm = M.store_month(fsd.drop(columns=["other_cost"]), acct, ST, DD)
    dept = t["fsdc"].rename(columns={"date": "biz_date"})
    return {"mart_fact_store_day": fsd, "mart_fact_store_day_dept": dept, "mart_store_month": sm}


def comparable(sm):
    """FY2025 の各月で既存店の店×月と、その前年同月（F246 と同じ決めごと）"""
    cur = sm[(sm.is_existing == 1) & (sm.fy == 2025)][["store_id", "ym"]].copy()
    cur["ym0"] = (pd.PeriodIndex(cur.ym, freq="M") - 12).strftime("%Y-%m")
    a = sm.merge(cur[["store_id", "ym"]], on=["store_id", "ym"])
    b = sm.merge(cur[["store_id", "ym0"]].rename(columns={"ym0": "ym"}), on=["store_id", "ym"])
    return a, b, cur


def kpi(mart):
    sm = mart["mart_store_month"]
    a, b, cur = comparable(sm)
    A, B = a[SUMS].sum(), b[SUMS].sum()
    op1 = A.gross_profit - A.labor_cost - A.other_cost
    op0 = B.gross_profit - B.labor_cost - B.other_cost
    d = mart["mart_fact_store_day_dept"].copy()
    d["ym"] = pd.to_datetime(d.biz_date).dt.strftime("%Y-%m")
    d4 = d[d.category_id == 4].groupby(["store_id", "ym"]).sales.sum()
    s4a = d4.reindex(pd.MultiIndex.from_frame(cur[["store_id", "ym"]])).sum()
    s4b = d4.reindex(pd.MultiIndex.from_frame(cur[["store_id", "ym0"]])).sum()
    al = sm[sm.fy == 2025][SUMS].sum()
    return {
        "既存店売上_FY2025": A.sales, "既存店売上の前年比": A.sales / B.sales - 1,
        "既存店営業利益_FY2025": op1, "既存店営業利益の前年比": op1 / op0 - 1,
        "全店売上_FY2025": al.sales, "既存店廃棄率_FY2025": A.waste / A.sales,
        "既存店人時売上_FY2025": A.sales / A.labor_hours, "既存店惣菜売上の前年比": s4a / s4b - 1,
    }


NAIVE = dict(dedupe=False, store_map="fanout", fixes=False, dept_map=False, hr="zero", waste_fix=False, close_day=5)
SCEN = [
    ("正しく整えたもの", {}, None),
    ("再送を除かない", dict(dedupe=False), None),
    ("締め5日の時点の数字（遅れて届く分が抜ける）", dict(close_day=5), None),
    ("店コードを期間を見ずに結合（行が増える）", dict(store_map="fanout"), None),
    ("店コードを古い対応表だけで結合", dict(store_map="oldmaster"), None),
    ("16店の新コードを補わない", dict(s16_fix=False), "s16"),
    ("トレーニング用コード9999を除かない", {}, "9999"),
    ("部門の付け替えを戻さない", dict(dept_map=False), None),
    ("空の人時を0のままにする", dict(hr="zero"), None),
    ("廃棄の単位（千円）を直さない", dict(waste_fix=False), None),
    ("すべて素朴に（上の手当てをどれもしない）", NAIVE, "9999"),
]


def build(raw, opt, special):
    m = M.build_mart_pd(raw, **opt)
    if special == "9999":   # 9999 を店の1つとして残す（全店の売上に入る）
        ps = raw["pos_store_day"]; ps = ps[ps["店コード"] == "9999"]
        if opt.get("dedupe", True):
            ps = ps.drop_duplicates(["店コード", "営業日"], keep="last")
        x = ps.rename(columns={"営業日": "biz_date", "レシート枚数": "receipts", "会員レシート枚数": "member_receipts", "点数": "items", "売上金額": "sales"})
        x = x.assign(store_id=99, gross_profit_before_waste=x.sales * 0.25, waste=0.0, gross_profit=x.sales * 0.25,
                     labor_hours=np.nan, labor_cost=0.0, labor_imputed=0, dept_sales=x.sales)[m["mart_fact_store_day"].columns]
        fsd = pd.concat([m["mart_fact_store_day"], x], ignore_index=True)
        sm = M.store_month(fsd, raw["acct_store_month"], ST, DD)
        m = {**m, "mart_fact_store_day": fsd, "mart_store_month": sm}
    return m


def fix_store_for(special, opt):
    if not opt.get("fixes", True):
        return M.EMPTY_FIX_STORE
    f = M.REF_FIX_STORE_CODE
    if special == "s16" or opt.get("s16_fix") is False:
        f = f[f["店コード"] != "1020"]
    if special == "9999":
        f = f[f["店コード"] != "9999"]
    return f


def main():
    RES.mkdir(exist_ok=True)
    raw = M.load_raw()
    tm = truth_mart()
    T = kpi(tm)
    out = {"truth": T}
    # F246 の数字と一致するか
    f246 = {"既存店売上_FY2025": 25817692839.08783, "既存店営業利益の前年比": -0.03197244824323453, "全店売上_FY2025": 27038278996.381542}
    out["truth_vs_F246"] = {k: T[k] - v for k, v in f246.items()}

    # ---- B と C ----
    rowsB, rowsC = [], []
    for name, opt, sp in SCEN:
        m = build(raw, opt, sp)
        K = kpi(m)
        r = {"シナリオ": name}
        for k, v in K.items():
            r[k] = v
            r[k + "_正解とのずれ"] = (v - T[k]) if ("比" in k or "率" in k) else (v / T[k] - 1)
        rowsB.append(r)
        t = M.tests_on_pd(m, raw, fix_store=fix_store_for(sp, opt))
        rowsC.append({"シナリオ": name, **t})
        print(name, {k: round(r[k + "_正解とのずれ"] * 100, 2) for k in K}, sum(v > 0 for v in t.values()))
    B = pd.DataFrame(rowsB); B.to_csv(RES / "B_scenario_kpi.csv", index=False, encoding="utf-8-sig")
    C = pd.DataFrame(rowsC); C.to_csv(RES / "C_scenario_tests.csv", index=False, encoding="utf-8-sig")
    out["B"] = B.set_index("シナリオ").to_dict(orient="index")
    out["C"] = C.set_index("シナリオ").to_dict(orient="index")

    # ---- D：締めの日 ----
    sm_t = tm["mart_store_month"]
    def monthly_yoy(sm, sm_prev=None):
        """当月は sm（締めの時点）、前年同月は sm_prev（確定済み）から"""
        a, _, cur = comparable(sm)
        _, b, _ = comparable(sm) if sm_prev is None else (None, sm_prev.merge(cur[["store_id", "ym0"]].rename(columns={"ym0": "ym"}), on=["store_id", "ym"]), None)
        a["k"] = a.ym; b["k"] = (pd.PeriodIndex(b.ym, freq="M") + 12).strftime("%Y-%m")
        return a.groupby("k").sales.sum() / b.groupby("k").sales.sum() - 1
    yt = monthly_yoy(sm_t)
    sm_final = M.build_mart_pd(raw)["mart_store_month"]
    final = monthly_yoy(sm_final)
    rowsD = []
    for cd in (1, 3, 5, 10, 20):
        mm = M.build_mart_pd(raw, close_day=cd)
        y = monthly_yoy(mm["mart_store_month"], sm_final)
        sm = mm["mart_store_month"]; s25 = sm[sm.fy == 2025].groupby("ym").sales.sum()
        acct = raw["acct_store_month"].groupby("年月")["売上高"].sum().reindex(s25.index)
        for ym in y.index:
            rowsD.append({"締めの日": cd, "ym": ym, "既存店前年比_締め": y[ym], "既存店前年比_確定": final[ym],
                          "直り幅_pt": (final[ym] - y[ym]) * 100, "売上の届いた割合": float(s25[ym] / acct[ym])})
    D = pd.DataFrame(rowsD); D.to_csv(RES / "D_close_day_revision.csv", index=False, encoding="utf-8-sig")
    Ds = D.groupby("締めの日").agg(直り幅の絶対値_平均pt=("直り幅_pt", lambda x: x.abs().mean()), 直り幅の絶対値_最大pt=("直り幅_pt", lambda x: x.abs().max()),
                               売上の届いた割合_最小=("売上の届いた割合", "min"), 売上の届いた割合_平均=("売上の届いた割合", "mean"))
    Ds.to_csv(RES / "D_close_day_summary.csv", encoding="utf-8-sig"); print(Ds)
    out["D"] = Ds.to_dict(orient="index")
    out["final_vs_truth_monthly_yoy_maxpt"] = float((final - yt).abs().max() * 100)

    # ---- E1：人時の埋め方 ----
    t_fsd = tm["mart_fact_store_day"].set_index(["biz_date", "store_id"])
    rowsE = []
    for hr in ("mean", "median", "zero", "dropday"):
        m = M.build_mart_pd(raw, hr=hr)
        f = m["mart_fact_store_day"]
        imp = f[f.labor_imputed == 1].set_index(["biz_date", "store_id"])
        K = kpi(m)
        e = (imp.labor_hours - t_fsd.labor_hours.reindex(imp.index)) if len(imp) else pd.Series(dtype=float)
        rowsE.append({"埋め方": hr, "埋めた店×日": int(len(imp)), "埋めた日の人時の誤差_平均絶対%": float((e.abs() / t_fsd.labor_hours.reindex(imp.index)).mean() * 100) if len(imp) else np.nan,
                      "既存店人時売上_ずれ%": (K["既存店人時売上_FY2025"] / T["既存店人時売上_FY2025"] - 1) * 100,
                      "既存店営業利益の前年比_ずれpt": (K["既存店営業利益の前年比"] - T["既存店営業利益の前年比"]) * 100,
                      "既存店売上_ずれ%": (K["既存店売上_FY2025"] / T["既存店売上_FY2025"] - 1) * 100})
    E1 = pd.DataFrame(rowsE); E1.to_csv(RES / "E_hr_impute_methods.csv", index=False, encoding="utf-8-sig"); print(E1)
    out["E_hr"] = E1.to_dict(orient="records")

    # ---- E2：乱数の種と汚れの割合 ----
    t = G.load_truth()
    rowsS = []
    keyk = ["既存店売上の前年比", "既存店営業利益の前年比", "全店売上_FY2025", "既存店廃棄率_FY2025"]
    for mult in (0.5, 1.0, 2.0):
        seeds = range(20) if mult == 1.0 else range(5)
        for sd in seeds:
            rr, _ = G.make_raw(t, seed=sd, rates={k: v * mult for k, v in G.RATES.items()})
            rr = M.normalize_raw(rr)
            for nm, opt, sp in (SCEN[0], SCEN[-1]):
                m = build(rr, opt, sp)
                K = kpi(m)
                tt = M.tests_on_pd(m, rr, fix_store=fix_store_for(sp, opt))
                row = {"倍率": mult, "seed": sd, "シナリオ": nm, "不合格のテスト数": sum(v > 0 for v in tt.values())}
                for k in keyk:
                    row[k + "_ずれ"] = (K[k] - T[k]) if ("比" in k or "率" in k) else (K[k] / T[k] - 1)
                rowsS.append(row)
        print("mult", mult, "done")
    S = pd.DataFrame(rowsS); S.to_csv(RES / "E_seeds_rates.csv", index=False, encoding="utf-8-sig")
    Ss = S.groupby(["倍率", "シナリオ"]).agg(n=("seed", "size"), 不合格テスト数_最小=("不合格のテスト数", "min"), 不合格テスト数_最大=("不合格のテスト数", "max"),
                                         **{k + "_最大絶対": (k + "_ずれ", lambda x: x.abs().max()) for k in keyk},
                                         **{k + "_平均": (k + "_ずれ", "mean") for k in keyk})
    Ss.to_csv(RES / "E_seeds_rates_summary.csv", encoding="utf-8-sig"); print(Ss.T)
    out["E_seeds"] = {f"{a}|{b}": v for (a, b), v in Ss.to_dict(orient="index").items()}

    # ---- E3：SQL 版で seed 1〜4 も同じテストが通るか ----
    rowsQ = []
    for sd in range(1, 5):
        rr, _ = G.make_raw(t, seed=sd); rr = M.normalize_raw(rr)
        for fx in (False, True):
            con = M.sql_build(rr, fixes=fx)
            res = M.run_tests(con)
            rowsQ.append({"seed": sd, "補正表": fx, **res})
    Q = pd.DataFrame(rowsQ); Q.to_csv(RES / "E_sql_tests_seeds.csv", index=False, encoding="utf-8-sig"); print(Q)
    out["E_sql_seeds"] = Q.to_dict(orient="records")
    json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)


if __name__ == "__main__":
    main()
