"""F91 共通：パス・図の体裁・データの読み込み"""
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
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11,
                     "axes.titlesize": 13, "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
DATA, RAW = ROOT / "data", ROOT / "data" / "raw"
FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
SEED = 2026
BLUE, ORANGE, GREEN, PURPLE, GRAY, INK = "#2a78d6", "#eb6834", "#3aa07a", "#8a5cc2", "#a3a29c", "#0b0b0b"
METHODS = ["SHAP", "並べ替え重要度", "部分依存（PDP）", "ALE"]
MCOL = {"SHAP": BLUE, "並べ替え重要度": ORANGE, "部分依存（PDP）": GREEN, "ALE": PURPLE}
SOURCE = ("出典：国土交通省「地価公示」「駅別乗降客数」、総務省「国勢調査」、東京電力パワーグリッド「エリア需給実績」、"
          "気象庁「過去の気象データ」をもとに作成者が加工して作成（F03・F22 のデータを再利用）")

# --- 地価（F03） ---
L_NUM = ["dist_station", "log_acreage", "far", "coverage", "road_width", "gas", "water", "sewage",
         "frontage_ratio", "depth_ratio", "floors", "basement", "irregular", "station_square",
         "log_pass_nearest", "dist_nearest_st", "log_pass_1km", "log_pass_3km", "log_pass_10km",
         "dist_metro", "log_muni_density", "log_muni_pop", "muni_pop_change", "lat", "lon"]
L_CAT = ["use_district", "planning_area", "fire_area", "road_type", "land_use_class"]
L_LABEL = {"dist_station": "駅までの距離", "log_acreage": "地積", "far": "容積率", "coverage": "建ぺい率",
           "road_width": "前面道路の幅", "gas": "ガス", "water": "水道", "sewage": "下水", "frontage_ratio": "間口",
           "depth_ratio": "奥行", "floors": "建物の階数", "basement": "地下階数", "irregular": "形状",
           "station_square": "駅前広場", "log_pass_nearest": "最寄駅の乗降客数", "dist_nearest_st": "最寄駅までの直線距離",
           "log_pass_1km": "1km内の乗降客数", "log_pass_3km": "3km内の乗降客数", "log_pass_10km": "10km内の乗降客数",
           "dist_metro": "三大都市の中心までの距離", "log_muni_density": "市区町村の人口密度", "log_muni_pop": "市区町村の人口",
           "muni_pop_change": "市区町村の人口増減率", "lat": "緯度", "lon": "経度", "use_district": "用途地域",
           "planning_area": "都市計画区域", "fire_area": "防火地域", "road_type": "前面道路の種類",
           "land_use_class": "用途（住宅地・商業地など）"}
L_PARAMS = dict(objective="regression", learning_rate=0.05, num_leaves=63, min_child_samples=20, subsample=0.8,
                subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, n_estimators=700, random_state=SEED,
                verbose=-1, n_jobs=2)

# --- 電力需要（F22） ---
P_LABEL = {"hour": "時刻", "dow": "曜日", "daytype": "平日・土曜・休日", "holiday": "祝日", "nenmatsu": "年末年始",
           "obon": "お盆", "gw": "大型連休", "doy_sin": "季節（sin）", "doy_cos": "季節（cos）", "month": "月",
           "year": "年（トレンド）", "temp_mean": "日平均気温", "temp_max": "日最高気温", "temp_min": "日最低気温",
           "humid_mean": "湿度", "cdd": "冷房度日", "hdd": "暖房度日", "cdd_max": "最高気温の冷房度日",
           "temp_change": "前日からの気温変化", "lag24": "24時間前の需要", "lag168": "1週間前の需要",
           "prevday_mean": "前日の平均需要", "lag24_daytype": "前日の曜日区分"}
P_PARAMS = dict(n_estimators=900, learning_rate=0.04, num_leaves=63, min_child_samples=40, subsample=0.8,
                subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, random_state=SEED, verbose=-1, n_jobs=2)
P_SPLIT = "2023-04-01"  # これより前で学習、以降（〜2026-09）で評価


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=6.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)


def load_land():
    d = pd.read_csv(RAW / "F03_features.csv", dtype={"code": str, "muni": str, "pref": str})
    d["y"] = np.log(d["price"])
    for c in L_CAT:
        d[c] = d[c].astype("category")
    return d


def load_power():
    from feat import make_features, LGB_FEATS
    d = pd.read_csv(RAW / "F22_hourly_tokyo.csv", index_col="ts", parse_dates=True)
    d = make_features(d).dropna(subset=LGB_FEATS + ["demand"])
    return d, LGB_FEATS
