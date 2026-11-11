"""03 分析：21個の「よくある誤り」を DuckDB と SQLite で流し、ずれの大きさと、7種類のテストのどれで見つかるかを数える。"""
import os, json, re
import numpy as np, pandas as pd
import lib

ROOT = lib.ROOT; RES = os.path.join(ROOT, "results")
retail, dim, hol = lib.load_retail()

def build(sim_kw, fix_kw=lib.FIXTURE_EDGE):
    sim = lib.simulate(**sim_kw)
    fix = lib.simulate(**fix_kw)
    rfix = lib.retail_fixture(retail)
    dbs = lib.make_dbs(dict(retail=retail, item_dim=dim, holidays=hol, **sim))
    dbf = lib.make_dbs(dict(retail=rfix, item_dim=dim, holidays=hol, **fix))
    Tp, Cp = lib.truths_public(retail, dim, hol); Ts, Cs = lib.truths_sim(sim)
    Tpf, _ = lib.truths_public(rfix, dim, hol); Tsf, _ = lib.truths_sim(fix)
    return dbs, dbf, {**Tp, **Ts}, {**Cp, **Cs}, {**Tpf, **Tsf}

def evaluate(dbs, dbf, T, C, TF, primary="sqlite"):
    other = "duckdb" if primary == "sqlite" else "sqlite"
    rows, mags = [], []
    for sp in lib.SPECS:
        k = sp["id"]
        for which in ["bad", "good"]:
            out = lib.run(dbs, sp[which], primary)
            oth = lib.run(dbs, sp[which], other)
            fx = lib.run(dbf, sp[which], primary)
            r = lib.run_tests(sp, out, oth, fx, T[k], TF[k], C)
            rows.append(dict(id=k, which=which, **r))
            if which == "bad":
                good = lib.run(dbs, sp["good"], primary)
                gs, bs = good.v.astype(float).sum(), out.v.astype(float).sum()
                tr = T[k].copy(); tr.index = tr.index.astype(str)
                a = out.drop_duplicates("k").set_index("k").v.astype(float)
                common = tr.index.intersection(a.index)
                wrong = (~np.isclose(a.reindex(common).values, tr.reindex(common).astype(float).values, rtol=1e-9, atol=1e-9)).sum()
                n_keys = len(tr)
                mags.append(dict(id=k, part=sp["part"], cat=sp["cat"], title=sp["title"], kind=sp["kind"],
                                 bad_rows=len(out), good_rows=len(good), bad_total=bs, good_total=gs,
                                 total_err_pct=(bs / gs - 1) * 100 if gs else np.nan,
                                 keys_wrong_or_missing_pct=(wrong + (n_keys - len(common))) / n_keys * 100,
                                 extra_keys=len(set(a.index) - set(tr.index))))
    return pd.DataFrame(rows), pd.DataFrame(mags)

def catch_table(tr):
    bad = tr[tr.which == "bad"].set_index("id")[lib.TESTS]
    good = tr[tr.which == "good"].set_index("id")[lib.TESTS]
    return bad, good

# ---------------- 本番（seed=1、SQLite を主にする：整数の割り算が SQL Server と同じ動き）
dbs, dbf, T, C, TF = build(dict(seed=1))
tr, mag = evaluate(dbs, dbf, T, C, TF, "sqlite")
bad, good = catch_table(tr)
false_alarm = good.apply(lambda c: c.fillna(False).astype(bool)).sum().to_dict()
bad.to_csv(os.path.join(RES, "A_catch_matrix_sqlite.csv"))
good.to_csv(os.path.join(RES, "A_good_queries_test_result_sqlite.csv"))
mag.to_csv(os.path.join(RES, "B_error_magnitude.csv"), index=False)

def summarize(bad):
    b = bad.apply(lambda c: c.map(lambda x: bool(x) if x is not None and not (isinstance(x, float) and np.isnan(x)) else False))
    any_ = b.any(axis=1)
    return dict(n_bugs=len(b), caught_any=int(any_.sum()), per_test={t: int(b[t].sum()) for t in lib.TESTS},
                only_T5=[i for i in b.index if b.loc[i].sum() == 1 and b.loc[i, lib.TESTS[4]]],
                missed=[i for i in b.index if not any_[i]],
                without_T5=int(b.drop(columns=[lib.TESTS[4]]).any(axis=1).sum()),
                T1_applicable=int(bad[lib.TESTS[0]].notna().sum()))
S_main = summarize(bad)

# ---------------- 頑健性1：エンジンを DuckDB にしたら
tr_d, mag_d = evaluate(dbs, dbf, T, C, TF, "duckdb")
bad_d, good_d = catch_table(tr_d)
bad_d.to_csv(os.path.join(RES, "C_catch_matrix_duckdb.csv"))
S_duck = summarize(bad_d)
# 誤り版の結果がエンジンで違うもの
eng_diff = []
for sp in lib.SPECS:
    a = lib.run(dbs, sp["bad"], "sqlite"); a = a.assign(v=a.v.astype(float)).sort_values(["k", "v"]); b = lib.run(dbs, sp["bad"], "duckdb"); b = b.assign(v=b.v.astype(float)).sort_values(["k", "v"])
    same = len(a) == len(b) and np.allclose(a.v.astype(float).values, b.v.astype(float).values, rtol=1e-9)
    if not same:
        eng_diff.append(dict(id=sp["id"], sqlite_total=a.v.astype(float).sum(), duckdb_total=b.v.astype(float).sum()))
pd.DataFrame(eng_diff).to_csv(os.path.join(RES, "C_bad_query_engine_difference.csv"), index=False)

# ---------------- 頑健性2：答え合わせ用のデータに境目のケースがないと
dbs2, dbf2, T2, C2, TF2 = build(dict(seed=1), lib.FIXTURE_PLAIN)
tr_p, _ = evaluate(dbs2, dbf2, T2, C2, TF2, "sqlite")
bad_p, _ = catch_table(tr_p)
bad_p.to_csv(os.path.join(RES, "D_catch_matrix_plain_fixture.csv"))
S_plain = summarize(bad_p)

# ---------------- 頑健性3：乱数の種を変える（3通り）
seed_rows = []
for sd in [1, 2, 3]:
    d_, f_, T_, C_, TF_ = build(dict(seed=sd), dict(lib.FIXTURE_EDGE, seed=90 + sd))
    t_, m_ = evaluate(d_, f_, T_, C_, TF_, "sqlite")
    b_, _ = catch_table(t_)
    s_ = summarize(b_)
    for _, r in m_.iterrows():
        seed_rows.append(dict(seed=sd, id=r.id, total_err_pct=r.total_err_pct, keys_wrong_pct=r.keys_wrong_or_missing_pct))
    seed_rows.append(dict(seed=sd, id="__caught_any", total_err_pct=s_["caught_any"], keys_wrong_pct=np.nan))
seed_df = pd.DataFrame(seed_rows); seed_df.to_csv(os.path.join(RES, "E_seeds.csv"), index=False)

# ---------------- 頑健性4：分割払いの割合・クーポンの割合を変える
par = []
for ps in [0.0, 0.05, 0.12, 0.30]:
    sim = lib.simulate(seed=1, p_split=ps)
    d_ = lib.make_dbs(dict(retail=retail, item_dim=dim, holidays=hol, **sim)); T_, C_ = lib.truths_sim(sim)
    b = lib.run(d_, lib.SPECS[[s["id"] for s in lib.SPECS].index("B1")]["bad"], "sqlite")
    err = (b.v.sum() / T_["B1"].sum() - 1) * 100
    t1 = not np.isclose(b.v.sum(), C_["B1"], rtol=1e-9)
    par.append(dict(param="p_split", value=ps, bug="B1", total_err_pct=err, T1_catches=t1))
for pc in [0.1, 0.3, 0.6, 0.9]:
    sim = lib.simulate(seed=1, p_coupon=pc)
    d_ = lib.make_dbs(dict(retail=retail, item_dim=dim, holidays=hol, **sim)); T_, C_ = lib.truths_sim(sim)
    b = lib.run(d_, lib.SPECS[[s["id"] for s in lib.SPECS].index("B3")]["bad"], "sqlite")
    err = (b.v.sum() / T_["B3"].sum() - 1) * 100
    par.append(dict(param="p_coupon", value=pc, bug="B3", total_err_pct=err, T1_catches=not np.isclose(b.v.sum(), C_["B3"], rtol=1e-9)))
par = pd.DataFrame(par); par.to_csv(os.path.join(RES, "F_parameters.csv"), index=False)

# ---------------- 描画用の系列
a2 = pd.DataFrame({"naive": lib.run(dbs, lib.SPECS[1]["bad"], "sqlite").set_index("k").v, "correct": lib.run(dbs, lib.SPECS[1]["good"], "sqlite").set_index("k").v})
pub_tot = retail.merge(dim, on=["gyotai", "item"]); pub_tot = pub_tot[(pub_tot.is_total == 1) & (pub_tot.gyotai == "家電大型専門店")].set_index("ym").sales
a2["published_total"] = pub_tot
a2.to_csv(os.path.join(RES, "G_A2_appliance_series.csv"))
spec_id = {s["id"]: s for s in lib.SPECS}
b8 = pd.DataFrame({"utc": lib.run(dbs, spec_id["B8"]["bad"], "sqlite").set_index("k").v, "jst": lib.run(dbs, spec_id["B8"]["good"], "sqlite").set_index("k").v})
b8.to_csv(os.path.join(RES, "G_B8_month_utc_vs_jst.csv"))
b11 = pd.DataFrame({"rows_based": lib.run(dbs, spec_id["B11"]["bad"], "sqlite").set_index("k").v, "calendar_based": lib.run(dbs, spec_id["B11"]["good"], "sqlite").set_index("k").v})
b11.to_csv(os.path.join(RES, "G_B11_moving_average.csv"))
b9 = dict(bad=float(lib.run(dbs, spec_id["B9"]["bad"], "sqlite").v.iloc[0]), good=float(lib.run(dbs, spec_id["B9"]["good"], "sqlite").v.iloc[0]))

# ---------------- SQL を書き出す（DuckDB・SQLite は実行したもの、SQL Server は自動変換で未実行）
def tsql(q):
    q = re.sub(r"JST\(([^()]*)\)", r"CONVERT(varchar(19), DATEADD(hour, 9, CAST(\1 AS datetime2)), 120)", q)
    q = re.sub(r"FLOAT\(([^()]*(?:\([^()]*\)[^()]*)*)\)", r"CAST(\1 AS float)", q)
    q = re.sub(r"DAYS\(([^()]*)\)", r"DATEDIFF(day, '2025-01-01', CAST(\1 AS date))", q)
    q = q.replace("substr(", "SUBSTRING(")
    return q
os.makedirs(os.path.join(ROOT, "sql"), exist_ok=True)
for eng in ["duckdb", "sqlite", "sqlserver"]:
    with open(os.path.join(ROOT, "sql", f"queries_{eng}.sql"), "w", encoding="utf-8") as f:
        f.write(f"-- F244 集計 SQL の誤り版と正しい版（{eng}）\n")
        if eng == "sqlserver":
            f.write("-- 注意：DuckDB・SQLite 用の SQL を機械的に書き換えたもの。SQL Server では実行していない。\n-- 整数どうしの割り算は SQL Server でも切り捨てになる（SQLite と同じ）。\n")
        for sp in lib.SPECS:
            for which in ["bad", "good"]:
                q = tsql(sp[which]) if eng == "sqlserver" else lib.render(sp[which], eng)
                f.write(f"\n-- {sp['id']} [{which}] {sp['cat']}：{sp['title']}\n{q};\n")

summary = dict(main=S_main, duckdb=S_duck, plain_fixture=S_plain, false_alarm_on_good=false_alarm,
               engine_diff=[e["id"] for e in eng_diff], b9=b9,
               rows=dict(orders=int(lib.simulate(seed=1)["orders"].shape[0])),
               seeds_caught_any=seed_df[seed_df.id == "__caught_any"].total_err_pct.tolist())
json.dump(summary, open(os.path.join(RES, "summary.json"), "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(summary, ensure_ascii=False, indent=1, default=str))
print(mag[["id", "total_err_pct", "keys_wrong_or_missing_pct", "bad_rows", "good_rows"]].round(2).to_string())
print(par.round(2).to_string())
print(bad.to_string())
