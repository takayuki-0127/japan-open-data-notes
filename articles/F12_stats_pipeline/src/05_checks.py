"""05 頑健性チェック：パイプラインが「失敗に気づけるか」を3つの試験で確かめる

1. 取得の再試行：2回失敗してから成功する偽の通信 → 3回目で取れるか。ずっと失敗する通信 → キャッシュで続行するか
2. 前回との差分：先月時点（--as-of 2026-07）と最新の取り込みを比べ、増えた月・改定された値を数える（02 が出力）
3. 壊れたデータ：DB のコピーに失業率 25% の行と重複した月を入れ、dbt のテストが失敗として止めるか
"""
import importlib.util, io, json, shutil, subprocess
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fetch", ROOT / "src" / "01_fetch.py")
fetch = importlib.util.module_from_spec(spec); spec.loader.exec_module(fetch)
out = {}

# 1. 再試行
class FakeResp(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *a): pass
calls = {"n": 0}
def flaky(url, timeout=60):
    calls["n"] += 1
    if calls["n"] < 3:
        raise ConnectionError("503 Service Unavailable (simulated)")
    return FakeResp(b"x" * 5000)
waits = []
data, tries = fetch.http_get("https://example.invalid", opener=flaky, sleep=waits.append)
out["retry_success"] = {"tries": tries, "waits_sec": waits, "bytes": len(data)}
def down(url, timeout=60): raise ConnectionError("e-Stat down (simulated)")
try:
    fetch.http_get("https://example.invalid", opener=down, sleep=lambda s: None)
    out["retry_all_fail"] = "unexpected success"
except RuntimeError as e:
    out["retry_all_fail"] = {"raised": str(e)[:80], "fallback": "キャッシュ（前回の data/raw）で続行。--strict なら失敗で止める"}

# 2. 差分（02 の出力を読む）
diffs = sorted((ROOT / "results").glob("diff_load*_vs_*.csv"))
if diffs:
    import pandas as pd
    nonempty = [f for f in diffs if len(pd.read_csv(f))]
    if nonempty:  # 先月時点（--as-of）と比べた差分
        d = pd.read_csv(nonempty[-1])
        out["diff"] = {"file": nonempty[-1].name, "by_table_status": {f"{k[0]}:{k[1]}": int(v) for k, v in d.groupby(["tbl", "status"]).size().items()}}
    out["diff_latest_rerun"] = {"file": diffs[-1].name, "changed_rows": int(len(pd.read_csv(diffs[-1])))}  # 同じデータでもう一度流したとき

# 3. 壊れたデータで dbt のテストが落ちるか
bad = ROOT / "data" / "stats_bad.duckdb"
shutil.copy(ROOT / "data" / "stats.duckdb", bad)
con = duckdb.connect(str(bad))
con.execute("insert into raw_lfs values (date '2026-09-01', 'unemp_rate_sa', 25.0)")
con.execute("insert into raw_jobs select month + interval 0 day, series, value from raw_jobs where month = date '2026-08-01'")  # 同じ月を二重に
con.execute("delete from raw_cpi where month = date '2026-09-01' and series = 'cpi_all'")
con.close()
prof = (ROOT / "dbt" / "profiles.yml").read_text().replace("../data/stats.duckdb", "../data/stats_bad.duckdb")
(ROOT / "dbt" / "profiles_bad").mkdir(exist_ok=True)
(ROOT / "dbt" / "profiles_bad" / "profiles.yml").write_text(prof)
p = subprocess.run(["dbt", "build", "--profiles-dir", "profiles_bad", "--target-path", "target_bad"], cwd=ROOT / "dbt", capture_output=True, text=True)
res = json.loads((ROOT / "dbt" / "target_bad" / "run_results.json").read_text())
failed = [r["unique_id"].split(".")[2] for r in res["results"] if r["status"] in ("fail", "error")]
skipped = [r["unique_id"].split(".")[2] for r in res["results"] if r["status"] == "skipped"]
out["bad_data"] = {"returncode": p.returncode, "failed_tests": failed, "skipped": skipped}
bad.unlink(); shutil.rmtree(ROOT / "dbt" / "profiles_bad"); shutil.rmtree(ROOT / "dbt" / "target_bad", ignore_errors=True)
(ROOT / "results" / "robustness.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))
