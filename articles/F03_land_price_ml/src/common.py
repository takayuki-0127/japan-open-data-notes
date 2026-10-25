"""F03 共通：パス・図の体裁・特徴量の列"""
from pathlib import Path
import warnings, logging
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
# 元データ（大きいので GitHub には置かない。README の URL から取得して data/raw/ に展開）
import os
BIG = Path(os.environ.get("F03_RAW", RAW))
L01_GEOJSON = BIG / "L01-26_GML" / "L01-26.geojson"
S12_GEOJSON = BIG / "S12-25_GML" / "UTF-8" / "S12-25_NumberOfPassengers.geojson"
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a"
SOURCE = "出典：国土交通省「地価公示」「駅別乗降客数」（国土数値情報）、総務省「令和2年国勢調査」をもとに作成者が加工して作成"
SEED = 2026

NUM = ["dist_station", "log_acreage", "far", "coverage", "road_width", "gas", "water", "sewage",
       "frontage_ratio", "depth_ratio", "floors", "basement", "irregular", "station_square",
       "log_pass_nearest", "dist_nearest_st", "log_pass_1km", "log_pass_3km", "log_pass_10km",
       "dist_metro", "log_muni_density", "log_muni_pop", "muni_pop_change", "lat", "lon"]
CAT = ["use_district", "planning_area", "fire_area", "road_type", "land_use_class"]
LABEL = {"dist_station": "駅までの距離", "log_acreage": "地積", "far": "容積率", "coverage": "建ぺい率",
         "road_width": "前面道路の幅", "gas": "ガス", "water": "水道", "sewage": "下水", "frontage_ratio": "間口",
         "depth_ratio": "奥行", "floors": "建物の階数", "basement": "地下階数", "irregular": "形状（台形・不整形）",
         "station_square": "駅前広場に接する", "log_pass_nearest": "最寄駅の乗降客数", "dist_nearest_st": "最寄駅までの直線距離",
         "log_pass_1km": "1km内の乗降客数", "log_pass_3km": "3km内の乗降客数", "log_pass_10km": "10km内の乗降客数",
         "dist_metro": "三大都市の中心までの距離", "log_muni_density": "市区町村の人口密度", "log_muni_pop": "市区町村の人口",
         "muni_pop_change": "市区町村の人口増減率", "lat": "緯度", "lon": "経度", "use_district": "用途地域",
         "planning_area": "都市計画区域", "fire_area": "防火地域", "road_type": "前面道路の種類", "land_use_class": "用途（住宅地・商業地など）"}


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)


def load(year=2026):
    d = pd.read_csv(DATA / "features.csv", dtype={"code": str, "muni": str, "pref": str})
    if year == 2016:
        d = d[d["price_2016"] > 0].copy()
        d["y"] = np.log(d["price_2016"])
    else:
        d["y"] = np.log(d["price"])
    for c in CAT:
        d[c] = d[c].astype("category")
    return d
