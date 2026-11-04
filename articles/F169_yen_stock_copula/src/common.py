from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"; DATA = ROOT / "data"; RES = ROOT / "results"; FIG = ROOT / "figures"
for p in (RAW, RES, FIG): p.mkdir(parents=True, exist_ok=True)
SEED = 169
START, END = "1998-01-05", "2026-10-30"
# 期間の区切り（頑健性チェック用）
PERIODS = [("1998-2006", "1998-01-01", "2006-12-31"), ("2007-2012", "2007-01-01", "2012-12-31"),
           ("2013-2019", "2013-01-01", "2019-12-31"), ("2020-2026", "2020-01-01", "2026-12-31")]
QS = [0.90, 0.95, 0.975, 0.99]
