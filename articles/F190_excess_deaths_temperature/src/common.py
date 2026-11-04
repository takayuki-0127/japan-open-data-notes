from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"; DATA = ROOT / "data"; RES = ROOT / "results"; FIG = ROOT / "figures"
for p in (RAW, RES, FIG):
    p.mkdir(parents=True, exist_ok=True)
SEED = 190
SUMMER = [6, 7, 8, 9]
WINTER = [12, 1, 2, 3]
