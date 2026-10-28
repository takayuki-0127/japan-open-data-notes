"""共通：パス・乱数の種・設定"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 20261028
AGES = ["20-24", "25-29", "30-34", "35-39", "40-44", "45-49"]   # 本体の年齢
PERIODS = [1960, 1970, 1980, 1990, 2000, 2010, 2020]       # 本体の時代（10年おき）
