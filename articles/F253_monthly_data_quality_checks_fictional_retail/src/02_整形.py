"""02 整形：速報（締めの時点）の mart を作る。

F247 の build_mart_pd(raw, close_day=k) で「営業日の翌月 k 日の24時までに届いた POS だけ」で作った店×日・店×日×部門を、
FY2025 の12か月について data/versions/ に書き出す（k = 1, 3, 5, 10）。F248 の「速報・確定」と同じ作り方。
確定は F247 の mart（data/in/）。
※ F247 のフォルダ（../F247_data_mart_fictional_retail）で F247 の 01〜02 を先に流しておく（data/truth・data/raw_synth が要る）。
会社・数字はすべて架空（合成データ）。
"""
import importlib.util, pathlib, warnings
import pandas as pd
warnings.filterwarnings("ignore")

ROOT = pathlib.Path(__file__).resolve().parents[1]
F247 = ROOT.parent / "F247_data_mart_fictional_retail"
OUT = ROOT / "data" / "versions"; OUT.mkdir(parents=True, exist_ok=True)

s = importlib.util.spec_from_file_location("f247", F247 / "src" / "03_整える.py")
M = importlib.util.module_from_spec(s); s.loader.exec_module(M)
raw = M.load_raw()
for cd in (1, 3, 5, 10):
    m = M.build_mart_pd(raw, close_day=cd)
    f = m["mart_fact_store_day"]; c = m["mart_fact_store_day_dept"]
    f = f[f.biz_date >= "2025-04-01"].drop(columns=["dept_sales"], errors="ignore")
    c = c[c.biz_date >= "2025-04-01"]
    f.to_csv(OUT / f"fact_store_day_d{cd}.csv.gz", index=False)
    c.to_csv(OUT / f"fact_store_day_category_d{cd}.csv.gz", index=False)
    print("close day", cd, len(f), len(c))
