"""F118 共通：パス・図の設定"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PRIOR = ROOT / "data" / "prior"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
for p in (RES, FIG):
    p.mkdir(exist_ok=True)

for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if Path(f).exists():
        font_manager.fontManager.addfont(f)
plt.rcParams.update({
    "font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
    "savefig.dpi": 150, "savefig.bbox": "tight", "axes.titlesize": 12, "axes.titleweight": "bold",
})
INK, GRAY, BLUE, ORANGE, GREEN, PURPLE = "#2b2a28", "#9a9893", "#2f6db5", "#d9822b", "#3c8d5a", "#7b5ea7"
SRC = "出典：統計センター SSDSE-B-2026、総務省統計局「社会・人口統計体系」、厚生労働省「人口動態保健所・市区町村別統計」をもとに作成（F16・F20・F51・F81・F100・022 の結果を再集計）"

UNIT = "在所児＋10人（0〜5歳100人あたり）で、合計特殊出生率がいくつ違うか"


def jload(p):
    return json.load(open(p, encoding="utf-8"))


def jdump(obj, p):
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
