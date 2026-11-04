from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"; DATA = ROOT / "data"; RES = ROOT / "results"; FIG = ROOT / "figures"
for p in (RAW, RES, FIG):
    p.mkdir(parents=True, exist_ok=True)
SEED = 193
XLSX = RAW / "gt010108.xlsx"
URL = "https://www.soumu.go.jp/johotsusintokei/field/data/gt010108.xlsx"
