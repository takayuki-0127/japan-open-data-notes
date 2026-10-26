"""パイプライン全体を順に実行して、各段の結果と時間を results/run_log.txt に残す
  python src/run_pipeline.py            # Web から取得（Actions など）
  python src/run_pipeline.py --bundle f # ブラウザで取ったバンドルから
"""
import subprocess, sys, time, datetime as dt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
args = sys.argv[1:]
steps = [("01 取得", ["python", "src/01_fetch.py", *args]),
         ("02 DuckDB へ取り込み・差分", ["python", "src/02_load_duckdb.py"]),
         ("03 dbt build（加工とテスト）", ["python", "src/03_run_dbt.py"]),
         ("04 図と CSV", ["python", "src/04_figures.py"])]
log = [f"run at {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M:%S} UTC"]
ok = True
for name, cmd in steps:
    t = time.time()
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    line = f"{name:<28} {'OK ' if p.returncode == 0 else 'NG '} {time.time()-t:5.1f}s  {p.stdout.strip().splitlines()[-1][:110] if p.stdout.strip() else ''}"
    log.append(line); print(line)
    if p.returncode != 0:
        log.append(p.stderr[-800:]); ok = False; break
(ROOT / "results" / "run_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")
sys.exit(0 if ok else 1)
