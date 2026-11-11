"""04 確かめ（頑健性）：引き継ぎ資料の決めごとが、本当に効いているか。

    python src/04_確かめ.py <run_all で作った work/repo> <最新版の venv の python> <作業用の空きフォルダ>

1. DuckDB の並列（T3）：F247 の 03_整える.py を、そのまま5回・1本で足す設定（launch.py）で5回流し、
   mart/store_month.csv が1回目・元のファイルと何セル違うかを数える → results/D_duckdb_threads.csv
2. 版の固定（T1）：最新版の venv（pandas 3.1.1 ほか）で run_all.py を流し、基準（requirements.lock で作った md5）と
   いくつ合うかを数える → results/D_latest_vs_baseline.json
"""
import io, json, pathlib, shutil, subprocess, sys, time
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
HO = ROOT / "handover"
sys.path.insert(0, str(HO))
from samplemart.verify import _close_csv, content_md5  # noqa: E402

repo, py_latest = pathlib.Path(sys.argv[1]), sys.argv[2]
RES = ROOT / "results"
A = repo / "articles" / "F247_data_mart_fictional_retail"
SM = A / "mart" / "store_month.csv"
pub = subprocess.run(["git", "show", "HEAD:articles/F247_data_mart_fictional_retail/mart/store_month.csv"],
                     cwd=repo, capture_output=True).stdout


def cells(a, b):
    ok, n = _close_csv(a, b)
    return n if ok else -1


rows = []
for mode in ["そのまま（並列）", "1本で足す（launch.py）"]:
    first = None
    for i in range(5):
        cmd = [sys.executable, "src/03_整える.py"] if mode.startswith("そのまま") else \
              [sys.executable, str(HO / "samplemart" / "launch.py"), "src/03_整える.py"]
        t0 = time.time()
        p = subprocess.run(["nice", "-n", "10", *cmd], cwd=A, capture_output=True, text=True)
        b = SM.read_bytes(); first = first or b
        rows.append({"流し方": mode, "回目": i + 1, "rc": p.returncode, "秒": round(time.time() - t0, 1),
                     "1回目と違うセル": cells(b, first), "元のファイルと違うセル": cells(b, pub),
                     "md5": content_md5(b, SM.name)[:10]})
        print(rows[-1], flush=True)
D = pd.DataFrame(rows)
D.to_csv(RES / "D_duckdb_threads.csv", index=False, encoding="utf-8-sig")
# 最後は launch.py の状態に戻しておく（後の照合のため）
subprocess.run([sys.executable, str(HO / "samplemart" / "launch.py"), "src/03_整える.py"], cwd=A, capture_output=True)

# 2. 最新版の venv で run_all.py（report）
work = pathlib.Path(sys.argv[3])
if work.exists():
    shutil.rmtree(work)
t0 = time.time()
p = subprocess.run(["nice", "-n", "10", py_latest, str(HO / "run_all.py"), "--work", str(work)], capture_output=True, text=True)
out = p.stdout.strip().splitlines()
v = pd.read_csv(work / "verify.csv")
num = v[v.種類 == "数字"]
res = {"rc": p.returncode, "sec": round(time.time() - t0, 1),
       "versions": subprocess.run([py_latest, "-c", "import pandas,numpy,duckdb,scipy,matplotlib;print(pandas.__version__,numpy.__version__,duckdb.__version__,scipy.__version__,matplotlib.__version__)"],
                                  capture_output=True, text=True).stdout.strip(),
       "baseline_files": int((num.基準と != "—").sum()), "same_as_baseline": int((num.基準と == "同じ").sum()),
       "diff_from_baseline": int((num.基準と == "違う").sum()),
       "vs_published": num.元のファイルと.str.replace(r"（.*", "", regex=True).value_counts().to_dict(),
       "diff_files": num[num.基準と == "違う"].ファイル.tolist()[:40], "tail": out[-4:]}
(RES / "D_latest_vs_baseline.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
shutil.copyfile(work / "verify.csv", RES / "D_latest_verify.csv")
shutil.rmtree(work)
print(json.dumps(res, ensure_ascii=False, indent=1))
