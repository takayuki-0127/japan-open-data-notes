"""04 分析：レポートの「型」と決まりを確かめる（頑健性）。

A 偶然の幅：この回で測り直した幅を、F246 の幅と比べる
B 店の例外の決まり：乱数の種を20通り変えて、決まりごとに「毎月何行載るか」「載った行のうち、本当に差がある店の割合」を比べる
  （本当に差がある＝20通りの平均でも、真ん中の店との差が 1σ を超える店×月×KPI。地方の廃棄・地域の客数の流れ・新しく既存店に入った店など、設定で置いた差）
C 全社の KPI の判定：前年比そのまま／曜日補正／市場との差、KPI ツリーでまとめるかどうかで、毎月いくつ「説明すること」が出るか（20通り）
D 締めの日：1・3・5・10日の速報で、保留・境目の予告と、予告なしに判定が変わる数
E SQL と pandas：KPI 表（12か月 × 11行）を SQL（SQL Server 互換の書き方、DuckDB で実行）でも計算して照合
F 計画の置き方：計画の売上の伸びを +2%・+4% にしたとき、計画の判定がいくつ変わるか
会社・数字はすべて架空（合成データ）。
"""
import importlib.util, json, pathlib
import numpy as np
import pandas as pd
import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; DATA = ROOT / "data"


def mod(name, file):
    s = importlib.util.spec_from_file_location(name, ROOT / "src" / file)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


M = mod("rep", "03_レポート.py"); P = mod("prep", "02_整形.py")
out = {}

# ---- A
W, comp, stor, sms = M.noise_widths()
f246 = pd.read_csv(DATA / "in" / "C_noise_by_grain.csv")
f246 = f246[(f246.grain == "月")]
name_map = {"K10": ("全社", "売上"), "K02": ("全社", "客数"), "K03": ("全社", "買上点数"), "K04": ("全社", "一品単価"),
            "K06": ("全社", "粗利率（廃棄後）"), "K07": ("全社", "廃棄率"), "K08": ("全社", "人時粗利"), "K09": ("全社", "人件費率"),
            "K00": ("全社", "営業利益"), "S_sales": ("1店", "売上"), "S_rcpt": ("1店", "客数"), "S_waste": ("1店", "廃棄率"), "S_lp": ("1店", "人時粗利")}
W["F246_width"] = [float(f246[(f246.level == name_map[i][0]) & (f246.KPI == name_map[i][1])]["偶然の幅（±1.96σ）"].iloc[0]) if i in name_map else np.nan for i in W.id]
W.to_csv(RES / "A_noise_widths_vs_F246.csv", index=False, encoding="utf-8-sig"); print(W.round(3))
out["A"] = W.set_index("id")[["sigma", "width_1.96", "F246_width"]].to_dict(orient="index")
sig = dict(zip(W.id, W.sigma))

# ---- B 店の例外の決まり（20通り）
st = pd.read_csv(DATA / "in" / "dim_store.csv", parse_dates=["open_date", "close_date"])
FY = M.MONTHS
devs_by_seed = {}
for seed, (sm, fmm) in sms.items():
    d = stor[stor.seed == seed]
    devs_by_seed[seed] = {ym: g.set_index("store_id")[[k for k, _, _ in M.SKPIS]] for ym, g in d.groupby("ym")}
mu = stor[stor.ym.isin(FY)].groupby(["ym", "store_id"])[[k for k, _, _ in M.SKPIS]].mean()
real = set()
for (ym, sid), r in mu.iterrows():
    for k in r.index:
        if abs(r[k]) > sig[k]:
            real.add((ym, sid, k))
RULES = {"今月 1.96σ 超え": dict(store_now=1.96, store_run=99, run_len=99),
         "今月 3σ 超え": dict(store_now=3.0, store_run=99, run_len=99),
         "3か月続けて 1σ 超え": dict(store_now=99, store_run=1.0, run_len=3),
         "採用：今月 3σ か 3か月続けて 1σ": dict(store_now=3.0, store_run=1.0, run_len=3)}
rowsB = []
for name, rr in RULES.items():
    for seed in sms:
        n, hit = 0, 0
        for ym in FY:
            items = M.store_exceptions(devs_by_seed[seed], ym, sig, st, rule=rr)
            n += len(items); hit += sum((ym, it["store_id"], it["kpi"]) in real for it in items)
        rowsB.append({"決まり": name, "seed": seed, "1か月の行数": n / len(FY), "本当に差がある割合": hit / n if n else np.nan,
                      "見つけた割合": hit / len(real)})
    print(name, pd.DataFrame(rowsB)[lambda x: x["決まり"] == name].mean(numeric_only=True).round(3).to_dict())
# よくあるやり方：店ごとに売上の前年比の上下5店を毎月載せる
for seed in sms:
    n, hit = 0, 0
    for ym in FY:
        d = devs_by_seed[seed][ym]["S_sales"].dropna().sort_values()
        pick = list(d.index[:5]) + list(d.index[-5:])
        n += len(pick); hit += sum((ym, s, "S_sales") in real for s in pick)
    rowsB.append({"決まり": "売上の前年比の上下5店（順位）", "seed": seed, "1か月の行数": n / len(FY), "本当に差がある割合": hit / n,
                  "見つけた割合": np.nan})
B = pd.DataFrame(rowsB); B.to_csv(RES / "B_store_rule_seeds.csv", index=False, encoding="utf-8-sig")
Bs = B.groupby("決まり", sort=False).agg(行数_平均=("1か月の行数", "mean"), 本当に差がある割合=("本当に差がある割合", "mean"),
                                       本当に差がある割合_最小=("本当に差がある割合", "min"), 見つけた割合=("見つけた割合", "mean"))
Bs.to_csv(RES / "B_store_rule_summary.csv", encoding="utf-8-sig"); print(Bs.round(3))
out["B"] = Bs.to_dict(orient="index"); out["B_real_cells_FY2025"] = len(real)
out["B_real_by_kpi"] = pd.Series([k for _, _, k in real]).value_counts().to_dict()

# ---- C 全社の KPI の判定（20通り）
mkt = pd.read_csv(DATA / "in" / "market_super_monthly.csv").set_index("ym")["前年比_%"]
cal = pd.read_csv(DATA / "in" / "D_calendar_adjust.csv").set_index("ym")["曜日の並びの効果"]
VAR = {"前年比そのまま": ((), ()), "曜日補正（客数・既存店売上）": ((), ("K01", "K02")), "採用：市場との差（客数・既存店売上）": (("K01", "K02"), ())}
rowsC = []
import copy
for vname, (mk, ca) in VAR.items():
    M.MKT_ADJ = mk
    for seed, (sm, fmm) in sms.items():
        Ks = {ym: M.company_kpi(sm, sm, fmm, ym, None, cal, mkt) for ym in pd.period_range("2025-01", "2026-03", freq="M").strftime("%Y-%m")}
        if ca:   # 曜日・祝日の並びを補正した前年比で判定
            Ks = {ym: copy.deepcopy(K) for ym, K in Ks.items()}
            for ym, K in Ks.items():
                for k in ca:
                    K["yoy"][k] = ((1 + K["yoy"][k] / 100) / (1 + cal[ym]) - 1) * 100
        for ym in FY:
            K = Ks[ym]; hist = [Ks[M._ym(ym, -i)] for i in (3, 2, 1)]
            J, _ = M.judge_company(K, hist, sig)
            flagged = [k for k in J if J[k]["flag"] != 0]
            roots = [k for k in flagged if not J[k]["explained_by"]]
            rowsC.append({"判定のしかた": vname, "seed": seed, "ym": ym, "流れが変わった": len(flagged), "説明すること（ツリーでまとめた後）": len(roots),
                          "flags": ",".join(flagged)})
M.MKT_ADJ = ("K01", "K02")
C = pd.DataFrame(rowsC); C.to_csv(RES / "C_company_judgment_seeds.csv", index=False, encoding="utf-8-sig")
Cs = C.groupby("判定のしかた", sort=False)[["流れが変わった", "説明すること（ツリーでまとめた後）"]].mean()
# 同じ月・同じ KPI が20通りのうち何通りで流れが変わったとされたか（再現する＝設定や市場から来る動き、しない＝偶然）
rep = []
for vname, g in C.groupby("判定のしかた", sort=False):
    cnt = {}
    for _, r in g.iterrows():
        for k in filter(None, str(r["flags"]).replace("nan", "").split(",")):
            cnt[(r.ym, k)] = cnt.get((r.ym, k), 0) + 1
    v = np.array(list(cnt.values())) if cnt else np.array([0])
    rep.append({"判定のしかた": vname, "16通り以上で出る（月×KPI）": int((v >= 16).sum()), "4通り以下でしか出ない（月×KPI）": int((v <= 4).sum())})
Cs = Cs.join(pd.DataFrame(rep).set_index("判定のしかた"))
Cs.to_csv(RES / "C_company_judgment_summary.csv", encoding="utf-8-sig"); print(Cs.round(2))
out["C"] = Cs.to_dict(orient="index")

# ---- D 締めの日
I = M.load_inputs()
rowsD = []
for cd in (1, 3, 5, 10):
    for ym in FY:
        R1 = M.build_report(I, ym, "v1", cd, sig, sig, None)
        R2 = M.build_report(I, ym, "v2", None, sig, sig, None)
        ch, num, naive = M.diff_versions(R1, R2)
        rowsD.append({"締めの日": cd, "ym": ym, "届いた割合": R1["arrived"], "保留した店": len(R1["held"]), "境目と予告": len(R1["unsure"]),
                      "予告なしに変わった判定": len(ch), "予告がない場合に変わって見える判定": len(naive),
                      "既存店売上の前年比の動き_pt": num["K01"], "営業利益の前年比の動き_pt": num["K00"]})
D = pd.DataFrame(rowsD); D.to_csv(RES / "D_close_day_versions.csv", index=False, encoding="utf-8-sig")
Ds = D.groupby("締めの日").agg(届いた割合_平均=("届いた割合", "mean"), 保留した店_平均=("保留した店", "mean"), 境目と予告_合計=("境目と予告", "sum"),
                             予告なし_合計=("予告なしに変わった判定", "sum"), 予告がない場合_合計=("予告がない場合に変わって見える判定", "sum"),
                             予告がない場合_月数=("予告がない場合に変わって見える判定", lambda x: int((x > 0).sum())),
                             営業利益の前年比の動き_最大pt=("営業利益の前年比の動き_pt", lambda x: x.abs().max()))
Ds.to_csv(RES / "D_close_day_summary.csv", encoding="utf-8-sig"); print(Ds.round(3))
out["D"] = Ds.to_dict(orient="index")

# ---- E SQL と pandas
con = duckdb.connect()
con.register("v_sm", I["final"]); con.execute("CREATE TABLE store_month AS SELECT * FROM v_sm")
con.register("v_fm", I["fm"]); con.execute("CREATE TABLE fact_member_month AS SELECT * FROM v_fm")
sql = (ROOT / "sql" / "monthly_report_kpi.sql").read_text(encoding="utf-8")
Q = con.execute(sql).df()
rowsE = []
for ym in FY:
    K = M.company_kpi(I["final"], I["final"], I["fm"], ym)
    q = Q[Q.ym == ym].iloc[0]
    for k, n, t in M.KPIS:
        rowsE.append({"ym": ym, "id": k, "KPI": n, "pandas": K["yoy"][k], "SQL": float(q[k]), "差": float(q[k]) - K["yoy"][k]})
E = pd.DataFrame(rowsE); E.to_csv(RES / "E_sql_vs_pandas.csv", index=False, encoding="utf-8-sig")
out["E_max_abs_diff"] = float(E["差"].abs().max()); out["E_cells"] = len(E); print("SQL vs pandas max diff", out["E_max_abs_diff"])

# ---- F 計画の置き方
rowsF = []
base = {ym: M.build_report(I, ym, "v2", None, sig, sig, None)["PJ"] for ym in FY}
for g in (0.02, 0.04):
    I2 = dict(I); I2["plan"] = P.make_plan(I["final"], I["st"], dict(P.PLAN_G, sales=g))
    for ym in FY:
        pj = M.build_report(I2, ym, "v2", None, sig, sig, None)["PJ"]
        for k in pj:
            rowsF.append({"計画の売上の伸び": g, "ym": ym, "id": k, "採用(+3%)の判定": base[ym][k]["flag"], "この計画の判定": pj[k]["flag"]})
F = pd.DataFrame(rowsF); F.to_csv(RES / "F_plan_assumption.csv", index=False, encoding="utf-8-sig")
Fs = F.assign(changed=F["採用(+3%)の判定"] != F["この計画の判定"]).groupby(["計画の売上の伸び", "id"]).changed.sum()
print(Fs); out["F"] = {f"{a}_{b}": int(v) for (a, b), v in Fs.items()}
out["F_base_flags"] = {k: [base[ym][k]["flag"] for ym in FY] for k in ("K10", "K00")}

(RES / "main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
