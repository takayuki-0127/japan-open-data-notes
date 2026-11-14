"""dbt build と、pandas で別に計算した答えとの突き合わせをまとめて回し、results/check_result.json に書く。
使い方: python3 tools/check.py
  1. データを作る（data/ になければ）と、答え合わせの期待値（seeds/expected_*）を作る
  2. 既定の定義・答え合わせ用データで dbt build（テストを全部通す）
  3. 8つの変更依頼（vars を1つ変える）ごとに、全レポートを pandas の答えと比べる。
     あわせて、期待値を既定のままにしたテスト（force_golden）が落ちることを確かめる
  4. 本番の大きさのデータ（13店・2年）で、既定の定義の全レポートを pandas の答えと比べる
  5. 増分モデル（fct_daily_store_sales）を2回に分けて積んだ結果が、作り直した結果と一致するか
"""
import json, os, subprocess, sys
import duckdb, numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from spec import load, reports

DB = os.path.join(ROOT, "target", "retail_mart.duckdb")
ENV = {**os.environ, "DBT_PROFILES_DIR": ROOT}
BASE_P = dict(mon="cal", st="cancel", test=False, tax=False, ret="return", grp="old", gap=13, cust="receipt")
CR = {  # 変更依頼：dbt の vars と、pandas の答えの引数
    "CR1 返品を元の売上日に計上": ({"return_date_basis": "sale"}, {"ret": "sale"}),
    "CR2 既存店を12か月以上に": ({"comp_store_min_months": 12}, {"gap": 12}),
    "CR3 21日締めの会計月": ({"month_basis": "fis"}, {"mon": "fis"}),
    "CR4 税抜き": ({"amount_basis": "excl"}, {"tax": True}),
    "CR5 テスト店を除外": ({"exclude_test_store": True}, {"test": True}),
    "CR6 void も除外": ({"bad_status": ["cancel", "void"]}, {"st": "cancel_void"}),
    "CR7 部門のまとめ方": ({"dept_group_version": "new"}, {"grp": "new"}),
    "CR8 客数を日ごとの会員に": ({"customer_key": "member_day"}, {"cust": "member"}),
}
REPORTS = {"R1": "rpt_r1_monthly_sales", "R2": "rpt_r2_store_monthly_sales", "R3": "rpt_r3_dept_group_monthly_sales",
           "R4": "rpt_r4_comp_store_yoy", "R5": "rpt_r5_customers_ticket", "R6": "rpt_r6_store_dept_group_monthly_sales",
           "R7": "rpt_r7_kpi_summary", "R8": "rpt_r8_latest_month_daily"}
KEYS = {"R1": ["ym"], "R2": ["ym", "store_id"], "R3": ["ym", "grp"], "R4": ["ym"], "R5": ["ym"],
        "R6": ["ym", "store_id", "grp"], "R7": ["ym"], "R8": ["date_key"]}


def dbt(*args, vars_=None):
    cmd = ["dbt", "--no-use-colors", "--log-format", "json", *args]
    if vars_:
        cmd += ["--vars", json.dumps(vars_, ensure_ascii=False)]
    p = subprocess.run(cmd, cwd=ROOT, env=ENV, capture_output=True, text=True)
    res = {"pass": 0, "fail": 0, "error": 0, "success": 0}
    for line in p.stdout.splitlines():
        try:
            d = json.loads(line)["data"]
        except Exception:
            continue
        st = (d.get("node_info") or {}).get("node_status")
        if d.get("status") and "node_info" in d and json.loads(line)["info"]["name"] in ("LogTestResult", "LogModelResult", "LogSeedResult"):
            s = str(d["status"]).lower()
            if s in ("pass", "success"): res["pass"] += 1
            elif s == "fail": res["fail"] += 1
            elif s == "error": res["error"] += 1
    res["returncode"] = p.returncode
    return res


def read(table):
    with duckdb.connect(DB, read_only=True) as c:
        return c.execute(f"select * from main.{table}").df()


def compare(model_df, exp_df, keys, tol=1e-9):
    """キーで突き合わせ、値の列のどれかが許容を超えてずれた行と、片方にしかない行を数える"""
    vals = [c for c in exp_df.columns if c not in keys]
    m = model_df[keys + vals].merge(exp_df[keys + vals], on=keys, how="outer", suffixes=("_m", "_e"), indicator=True)
    bad = m["_merge"] != "both"
    for c in vals:
        a, b = m[c + "_m"].astype(float), m[c + "_e"].astype(float)
        both_na = a.isna() & b.isna()
        diff = (a - b).abs() > tol * np.maximum(1.0, b.abs())
        bad |= ~both_na & (diff | a.isna() ^ b.isna())
    return int(bad.sum()), int(len(m))


def compare_all(P, data_dir):
    exp = reports(load(os.path.join(ROOT, "data", data_dir)), P)
    out = {}
    for k, t in REPORTS.items():
        df = read(t)
        if "customers" in df: df["customers"] = df["customers"].astype("int64")
        out[k] = compare(df, exp[k], KEYS[k])
    return out


def main():
    if not os.path.exists(os.path.join(ROOT, "data", "main_2751", "sales_line.csv.gz")):
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "generate_data.py")], check=True, cwd=ROOT)
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "make_expected.py")], check=True, cwd=ROOT,
                   capture_output=True)
    result = {}
    b = dbt("build", "--full-refresh")
    result["base_build"] = {**b, "reports_vs_pandas": compare_all(BASE_P, "fixture_2751")}
    print("base", result["base_build"])

    result["change_requests"] = {}
    for name, (v, p) in CR.items():
        bb = dbt("build", "--full-refresh", "--exclude", "test_name:matches_expected", vars_=v)
        cmp_ = compare_all({**BASE_P, **p}, "fixture_2751")
        g = dbt("test", "--select", "test_name:matches_expected", vars_={**v, "force_golden": True})
        changed = [k for k, t in REPORTS.items()]
        result["change_requests"][name] = {
            "vars": v, "build_returncode": bb["returncode"], "build_fail": bb["fail"] + bb["error"],
            "reports_mismatch_vs_pandas": sum(x[0] for x in cmp_.values()),
            "rows_compared": sum(x[1] for x in cmp_.values()),
            "golden_tests_failed_when_expectation_not_updated": g["fail"],
        }
        print(name, result["change_requests"][name])

    mb = dbt("build", "--full-refresh", vars_={"dataset": "main_2751"})
    result["main_data"] = {**mb, "reports_vs_pandas": compare_all(BASE_P, "main_2751")}
    print("main", result["main_data"])

    inc = {}
    sel = ["--select", "+fct_daily_store_sales"]
    for label, extra in [("返品は返品日（既定）", {}), ("返品は元の売上日（CR1）", {"return_date_basis": "sale"}),
                         ("CR1・読み直しなし（対照）", {"return_date_basis": "sale", "incremental_lookback_days": 0})]:
        v0 = {"dataset": "main_2751", **extra}
        dbt("run", *sel, "--full-refresh", vars_={**v0, "load_until": 20260331})
        full = read("fct_daily_store_sales").sort_values(["date_key", "store_id"]).reset_index(drop=True)
        dbt("run", *sel, "--full-refresh", vars_={**v0, "load_until": 20260228})
        r2 = dbt("run", *sel, vars_={**v0, "load_until": 20260331})
        incr = read("fct_daily_store_sales").sort_values(["date_key", "store_id"]).reset_index(drop=True)
        n_bad, n = compare(incr[["date_key", "store_id", "sales"]], full[["date_key", "store_id", "sales"]],
                           ["date_key", "store_id"])
        inc[label] = {"rows": n, "rows_differ_from_full_refresh": n_bad,
                      "total_diff": round(float(incr.sales.sum() - full.sales.sum()), 6)}
        print(label, inc[label])
    result["incremental"] = inc
    dbt("build", "--full-refresh")  # 最後に既定の状態に戻す

    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    json.dump(result, open(os.path.join(ROOT, "results", "check_result.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    ok = (result["base_build"]["returncode"] == 0 and result["main_data"]["returncode"] == 0
          and all(x["reports_mismatch_vs_pandas"] == 0 and x["build_returncode"] == 0 for x in result["change_requests"].values())
          and inc["返品は返品日（既定）"]["rows_differ_from_full_refresh"] == 0
          and inc["返品は元の売上日（CR1）"]["rows_differ_from_full_refresh"] == 0)
    print("ALL OK" if ok else "NG")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
