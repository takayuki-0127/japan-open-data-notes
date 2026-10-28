"""F108 共通：パス・図の体裁・乱数の種・グループの定義"""
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
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "sans-serif"], "axes.unicode_minus": False,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
DATA, RAW, RES, FIG = ROOT / "data", ROOT / "data" / "raw", ROOT / "results", ROOT / "figures"
for p in (RAW, RES, FIG):
    p.mkdir(parents=True, exist_ok=True)
SEED = 2026
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a"
SRC_LAND = "出典：国土交通省「地価公示」「駅別乗降客数」（国土数値情報）、総務省「令和2年国勢調査」をもとに作成者が加工して作成（F03 のデータ）"
SRC_POWER = "出典：東京電力パワーグリッド「エリア需給実績」、気象庁「過去の気象データ」をもとに作成者が加工して作成（F92 の予測）"

# F03 と同じ特徴量・同じ設定（F03 の src/common.py・03_lgbm_cv.py と同じ）
NUM = ["dist_station", "log_acreage", "far", "coverage", "road_width", "gas", "water", "sewage",
       "frontage_ratio", "depth_ratio", "floors", "basement", "irregular", "station_square",
       "log_pass_nearest", "dist_nearest_st", "log_pass_1km", "log_pass_3km", "log_pass_10km",
       "dist_metro", "log_muni_density", "log_muni_pop", "muni_pop_change", "lat", "lon"]
CAT = ["use_district", "planning_area", "fire_area", "road_type", "land_use_class"]
PARAMS = dict(objective="regression", learning_rate=0.03, num_leaves=63, min_child_samples=20,
              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, n_estimators=1500,
              random_state=SEED, verbose=-1, n_jobs=2)

# グループの定義（都道府県コードで近似。地価公示の「三大都市圏」は市区町村単位の定義なので、ここでは近似）
KEN = {**{p: "東京圏" for p in ("11", "12", "13", "14")}, **{p: "大阪圏" for p in ("26", "27", "28", "29")},
       **{p: "名古屋圏" for p in ("23", "24")}}
def block(p):
    p = int(p)
    if p == 1: return "北海道"
    if p <= 7: return "東北"
    if p <= 14: return "関東"
    if p <= 23: return "中部"
    if p <= 30: return "近畿"
    if p <= 35: return "中国"
    if p <= 39: return "四国"
    return "九州・沖縄"
BLOCKS = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]
KENS = ["東京圏", "大阪圏", "名古屋圏", "地方圏"]
DENS = ["密度1（低い）", "密度2", "密度3", "密度4", "密度5（高い）"]
USES = ["住宅地", "商業地", "工業地", "その他"]


def save(fig, name, src, y=-0.02):
    fig.text(0.01, y, src, fontsize=7, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
