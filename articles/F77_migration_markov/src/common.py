"""F77 共通の設定。"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
for p in (DATA, RES, FIG):
    p.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False

TOKYO_AREA = ["埼玉県", "千葉県", "東京都", "神奈川県"]
SEED = 77
