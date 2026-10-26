"""F17 共通：パス・図の体裁"""
from pathlib import Path
import logging, warnings
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
warnings.filterwarnings("ignore")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a"
SEED = 20261026
SOURCE = ("出典：総務省「労働力調査（都道府県別モデル推計値）」、厚生労働省「地域別最低賃金の全国一覧」「賃金構造基本統計調査（2015年）」"
          "「職業安定業務統計」、統計センター「SSDSE-A-2021」「SSDSE-B-2026」をもとに作成者が加工して作成")

# 効果の違いを説明する特徴（すべて2015〜16年＝引き上げが続く前の値）
X_COLS = ["bite", "wage15", "emp15", "unemp15", "jor15", "logpop15", "age65", "sh_manu", "sh_retail", "sh_food", "sh_welfare", "sh_constr"]
X_JA = {"bite": "最低賃金÷平均時給（2015）", "wage15": "短時間労働者の平均時給（2015）", "emp15": "就業率（2015）",
        "unemp15": "完全失業率（2015）", "jor15": "有効求人倍率（2015）", "logpop15": "15歳以上人口（log, 2015）",
        "age65": "65歳以上の割合（2015）", "sh_manu": "製造業の従業者の割合（2016）", "sh_retail": "卸売・小売業の割合（2016）",
        "sh_food": "宿泊・飲食業の割合（2016）", "sh_welfare": "医療・福祉の割合（2016）", "sh_constr": "建設業の割合（2016）"}


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7, color=GRAY, ha="left", va="top", wrap=True)
    fig.savefig(FIG / name)
    plt.close(fig)
