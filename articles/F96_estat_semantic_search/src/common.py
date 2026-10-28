"""F96 共通の設定（パス・フォント・色・モデル）"""
from pathlib import Path
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RES = ROOT / "results"
CACHE = ROOT / "cache"  # 埋め込みのキャッシュ（大きいので GitHub には置かない）
FIG = ROOT / "figures"
for p in (DATA, RAW, RES, FIG, CACHE):
    p.mkdir(parents=True, exist_ok=True)

# 埋め込みモデル（どちらも Apache-2.0）。ネットにつながらない環境では環境変数で手元のフォルダを指定
MODELS = {
    "ruri-v3-30m": os.environ.get("RURI30_PATH", "cl-nagoya/ruri-v3-30m"),
    "ruri-v3-70m": os.environ.get("RURI70_PATH", "cl-nagoya/ruri-v3-70m"),
}
SEED = 96

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10.5,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 110, "savefig.dpi": 150, "savefig.bbox": "tight"})
BLUE, ORANGE, GREEN, RED, GRAY, PURPLE = "#2f6db5", "#e08a2e", "#3a9a5b", "#c8443c", "#8a8a8a", "#7a5aa6"
