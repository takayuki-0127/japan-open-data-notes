from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 42
for p in (RAW, RES, FIG):
    p.mkdir(parents=True, exist_ok=True)

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

SERIES = {"power": "電力需要（東京エリア）", "inbound": "訪日外客数（総数）", "births": "出生数（1日あたり）"}
