"""F109 共通：パス・図の体裁・特徴量の列（F03 と同じ特徴量）"""
from pathlib import Path
import warnings, logging
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
warnings.filterwarnings("ignore")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
DATA, FIG, RES = ROOT / "data", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#8a5cc2"
SOURCE = "出典：国土交通省「地価公示」「駅別乗降客数」（国土数値情報）、総務省「令和2年国勢調査」をもとに作成者が加工して作成"
SEED = 2026
NUM = ["dist_station", "log_acreage", "far", "coverage", "road_width", "gas", "water", "sewage",
       "frontage_ratio", "depth_ratio", "floors", "basement", "irregular", "station_square",
       "log_pass_nearest", "dist_nearest_st", "log_pass_1km", "log_pass_3km", "log_pass_10km",
       "dist_metro", "log_muni_density", "log_muni_pop", "muni_pop_change", "lat", "lon"]
CAT = ["use_district", "planning_area", "fire_area", "road_type", "land_use_class"]
STRAT_LABEL = {"random": "ランダム", "uncertainty": "不確実性（委員会の分散）",
               "diversity": "多様性（k-means）", "hybrid": "不確実性＋多様性"}
STRAT_COLOR = {"random": GRAY, "uncertainty": ORANGE, "diversity": BLUE, "hybrid": GREEN}


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)


def load():
    d = pd.read_csv(DATA / "features.csv", dtype={"code": str, "muni": str, "pref": str})
    d["y"] = np.log(d["price"])
    for c in CAT:
        d[c] = d[c].astype("category")
    return d.reset_index(drop=True)
