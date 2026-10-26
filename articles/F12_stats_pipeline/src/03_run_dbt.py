"""03 加工とテスト：dbt build（stg → mart の作成と全テスト）と dbt docs generate（系譜図の元データ）を実行する"""
import subprocess, sys, time, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DBT = ROOT / "dbt"


def run(args):
    t = time.time()
    p = subprocess.run(["dbt", *args, "--profiles-dir", "."], cwd=DBT, capture_output=True, text=True)
    return p.returncode, round(time.time() - t, 1), p.stdout


if __name__ == "__main__":
    rc, sec, out = run(["build"])
    (ROOT / "results" / "dbt_build_log.txt").write_text(out, encoding="utf-8")
    res = json.loads((DBT / "target" / "run_results.json").read_text())
    summary = {"returncode": rc, "seconds": sec,
               "results": [{"name": r["unique_id"].split(".")[-1] if r["unique_id"].startswith("model") else r["unique_id"].split(".")[2],
                            "type": r["unique_id"].split(".")[0], "status": r["status"], "sec": round(r["execution_time"], 2)} for r in res["results"]]}
    (ROOT / "results" / "dbt_results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    run(["docs", "generate"])
    print(rc, sec, sum(r["status"] == "pass" for r in summary["results"]), "tests passed")
    sys.exit(rc)
