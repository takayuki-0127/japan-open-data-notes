"""F25 共通の設定（パス・フォント・色）"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RES = ROOT / "results"
FIG = ROOT / "figures"
for p in (DATA, RAW, RES, FIG):
    p.mkdir(parents=True, exist_ok=True)

# 埋め込みモデル（Apache-2.0）。ローカルに置いたパスか、Hugging Face のID
MODEL = "cl-nagoya/ruri-v3-30m"
SEED = 42

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10.5,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 110, "savefig.dpi": 150, "savefig.bbox": "tight"})
BLUE, ORANGE, GREEN, RED, GRAY = "#2f6db5", "#e08a2e", "#3a9a5b", "#c8443c", "#8a8a8a"
