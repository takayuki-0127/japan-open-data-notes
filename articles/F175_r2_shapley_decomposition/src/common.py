"""F175 共通：パス・図の体裁・データ・特徴量のまとまり（グループ）"""
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
for p in (RAW, FIG, RES):  # git は空のフォルダを保存しないので、ここで作る
    p.mkdir(parents=True, exist_ok=True)
SEED = 2026
BLUE, ORANGE, GREEN, PURPLE, GRAY, INK, RED = "#2a78d6", "#eb6834", "#3aa07a", "#8a5cc2", "#a3a29c", "#0b0b0b", "#c8414b"
SOURCE = ("出典：国土交通省「地価公示」「駅別乗降客数」、総務省「国勢調査」、東京電力パワーグリッド「エリア需給実績」、"
          "気象庁「過去の気象データ」をもとに作成者が加工して作成（F03・F22 のデータを再利用）")

# --- 地価（F03）：30変数 ---
L_NUM = ["dist_station", "log_acreage", "far", "coverage", "road_width", "gas", "water", "sewage",
         "frontage_ratio", "depth_ratio", "floors", "basement", "irregular", "station_square",
         "log_pass_nearest", "dist_nearest_st", "log_pass_1km", "log_pass_3km", "log_pass_10km",
         "dist_metro", "log_muni_density", "log_muni_pop", "muni_pop_change", "lat", "lon"]
L_CAT = ["use_district", "planning_area", "fire_area", "road_type", "land_use_class"]
L_FEATS = L_NUM + L_CAT
# 基本の7グループ
L_GROUPS = {
    "駅の近さ": ["dist_station", "dist_nearest_st", "station_square"],
    "周りの乗降客数": ["log_pass_nearest", "log_pass_1km", "log_pass_3km", "log_pass_10km"],
    "位置（緯度経度・大都市までの距離）": ["lat", "lon", "dist_metro"],
    "市区町村の人口": ["log_muni_density", "log_muni_pop", "muni_pop_change"],
    "用途・規制": ["far", "coverage", "use_district", "planning_area", "fire_area", "land_use_class"],
    "土地と建物": ["log_acreage", "frontage_ratio", "depth_ratio", "floors", "basement", "irregular"],
    "道路・設備": ["road_width", "road_type", "gas", "water", "sewage"],
}
# 粗い4グループ（頑健性）
L_GROUPS4 = {
    "駅と乗降客数": L_GROUPS["駅の近さ"] + L_GROUPS["周りの乗降客数"],
    "位置と市区町村": L_GROUPS["位置（緯度経度・大都市までの距離）"] + L_GROUPS["市区町村の人口"],
    "用途・規制": L_GROUPS["用途・規制"],
    "土地・建物・道路": L_GROUPS["土地と建物"] + L_GROUPS["道路・設備"],
}

# --- 電力需要（F22）：23変数 ---
P_GROUPS = {
    "時刻": ["hour"],
    "曜日・祝日・連休": ["dow", "daytype", "holiday", "nenmatsu", "obon", "gw", "lag24_daytype"],
    "季節": ["doy_sin", "doy_cos", "month"],
    "年（トレンド）": ["year"],
    "気温・湿度": ["temp_mean", "temp_max", "temp_min", "humid_mean", "cdd", "hdd", "cdd_max", "temp_change"],
    "過去の需要": ["lag24", "lag168", "prevday_mean"],
}
P_GROUPS4 = {
    "時刻と暦": P_GROUPS["時刻"] + P_GROUPS["曜日・祝日・連休"],
    "季節と年": P_GROUPS["季節"] + P_GROUPS["年（トレンド）"],
    "気温・湿度": P_GROUPS["気温・湿度"],
    "過去の需要": P_GROUPS["過去の需要"],
}
# 細かい7グループ（過去の需要を「前日」と「1週間前」に分ける）
P_GROUPS7 = dict(P_GROUPS)
P_GROUPS7.pop("過去の需要")
P_GROUPS7["前日の需要"] = ["lag24", "prevday_mean"]
P_GROUPS7["1週間前の需要"] = ["lag168"]

# 学び直し（refit）用の軽い設定：128通り×学習するため、F91 より木を減らす
FAST = dict(objective="regression", learning_rate=0.1, num_leaves=63, min_child_samples=20, subsample=0.8,
            subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, n_estimators=300, random_state=SEED,
            verbose=-1, n_jobs=2)
P_SPLIT = "2023-04-01"


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=6.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)


def r2(y, p):
    return float(1 - np.sum((y - p) ** 2) / np.sum((y - np.mean(y)) ** 2))


def data_land(seed=SEED):
    d = pd.read_csv(RAW / "F03_features.csv", dtype={"code": str, "muni": str, "pref": str})
    d["y"] = np.log(d["price"])
    for c in L_CAT:
        d[c] = d[c].astype("category")
    rng = np.random.default_rng(seed)
    te = rng.random(len(d)) < 0.2
    X, y = d[L_FEATS], d["y"].values
    return X[~te].reset_index(drop=True), y[~te], X[te].reset_index(drop=True), y[te], d.loc[te, "pref"].values


def data_power():
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from feat import make_features, LGB_FEATS
    d = pd.read_csv(RAW / "F22_hourly_tokyo.csv", index_col="ts", parse_dates=True)
    d = make_features(d).dropna(subset=LGB_FEATS + ["demand"])
    tr, te = d.index < P_SPLIT, d.index >= P_SPLIT
    Xte = d.loc[te, LGB_FEATS].sample(20000, random_state=SEED).sort_index()
    return (d.loc[tr, LGB_FEATS].reset_index(drop=True), d.loc[tr, "demand"].values,
            Xte.reset_index(drop=True), d.loc[Xte.index, "demand"].values, Xte.index)
