"""F158 共通：パス・図の体裁・特徴量・CV の分け方"""
from pathlib import Path
import warnings, logging, os
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
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#8a5cc7"
SOURCE = "出典：国土交通省「地価公示」「駅別乗降客数」（国土数値情報）、総務省「令和2年国勢調査」をもとに作成者が加工して作成"
SEED = 2026
YEARS = list(range(2017, 2027))
NUM = ["dist_station", "log_acreage", "far", "coverage", "road_width", "gas", "water", "sewage",
       "frontage_ratio", "depth_ratio", "floors", "basement", "irregular", "station_square",
       "log_pass_nearest", "dist_nearest_st", "log_pass_1km", "log_pass_3km", "log_pass_10km",
       "dist_metro", "log_muni_density", "log_muni_pop", "muni_pop_change", "lat", "lon"]
CAT = ["use_district", "planning_area", "fire_area", "road_type", "land_use_class"]
FEAT = NUM + CAT
GROUPS = {
    "都心からの距離・位置": ["dist_metro", "lat", "lon"],
    "駅と乗降客数": ["dist_station", "station_square", "log_pass_nearest", "dist_nearest_st", "log_pass_1km", "log_pass_3km", "log_pass_10km"],
    "市区町村の人口": ["log_muni_density", "log_muni_pop", "muni_pop_change"],
    "用途地域・容積率など": ["use_district", "planning_area", "fire_area", "far", "coverage", "land_use_class"],
    "土地と建物の条件": ["log_acreage", "road_width", "road_type", "gas", "water", "sewage", "frontage_ratio", "depth_ratio", "floors", "basement", "irregular"],
}
LABEL = {"dist_station": "駅までの距離", "log_acreage": "地積", "far": "容積率", "coverage": "建ぺい率",
         "road_width": "前面道路の幅", "gas": "ガス", "water": "水道", "sewage": "下水", "frontage_ratio": "間口",
         "depth_ratio": "奥行", "floors": "建物の階数", "basement": "地下階数", "irregular": "形状",
         "station_square": "駅前広場に接する", "log_pass_nearest": "最寄駅の乗降客数", "dist_nearest_st": "最寄駅までの直線距離",
         "log_pass_1km": "1km内の乗降客数", "log_pass_3km": "3km内の乗降客数", "log_pass_10km": "10km内の乗降客数",
         "dist_metro": "三大都市の中心までの距離", "log_muni_density": "市区町村の人口密度", "log_muni_pop": "市区町村の人口",
         "muni_pop_change": "市区町村の人口増減率", "lat": "緯度", "lon": "経度", "use_district": "用途地域",
         "planning_area": "都市計画区域", "fire_area": "防火地域", "road_type": "前面道路の種類", "land_use_class": "用途（住宅地・商業地など）"}
PARAMS = dict(objective="regression", learning_rate=0.1, num_leaves=63, min_child_samples=20, max_bin=63,
              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, n_estimators=300,
              random_state=SEED, verbose=-1, n_jobs=2)


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)


def load_points():
    d = pd.read_csv(DATA / "points.csv", dtype={"code": str, "muni": str, "pref": str})
    for c in CAT:
        d[c] = d[c].astype("category")
    return d


def load_panel():
    return pd.read_csv(DATA / "panel.csv", dtype={"code": str})


def folds(points, kind="block20", k=5):
    """地点ごとに 0〜4 の分割番号。block20：20km四方のブロック単位、random：地点単位"""
    rng = np.random.default_rng(SEED)
    if kind == "random":
        return pd.Series(rng.permutation(len(points)) % k, index=points["code"].values)
    u = points["block20"].unique(); perm = dict(zip(u, rng.permutation(len(u))))
    from sklearn.model_selection import GroupKFold
    f = np.zeros(len(points), int)
    for i, (_, te) in enumerate(GroupKFold(k).split(points, groups=points["block20"].map(perm))):
        f[te] = i
    return pd.Series(f, index=points["code"].values)


def score(y, p):
    y, p = np.asarray(y), np.asarray(p)
    e = p - y
    ape = np.abs(np.exp(e) - 1)
    return dict(n=len(y), r2=1 - (e ** 2).sum() / ((y - y.mean()) ** 2).sum(), rmse_log=np.sqrt((e ** 2).mean()),
                median_ape=np.median(ape), within20=(ape <= 0.2).mean(), bias=np.median(e))
