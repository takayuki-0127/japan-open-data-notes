"""F75 共通：パス・図の体裁・地域・座標の変換（データは F03 の特徴量を使う）"""
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
DATA, FIG, RES = ROOT / "data", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a"
SOURCE = "出典：国土交通省「地価公示」「駅別乗降客数」（国土数値情報）、総務省「令和2年国勢調査」をもとに作成者が加工して作成"
SEED = 2026

# 3つの大都市圏（都道府県コード）
AREAS = {"首都圏": ["11", "12", "13", "14"], "関西圏": ["26", "27", "28", "29"], "中京圏": ["23"]}
# 各地域の座標の原点（km に変換するときの基準）
ORIGIN = {"首都圏": (35.68, 139.77), "関西圏": (34.70, 135.50), "中京圏": (35.17, 136.91)}

# 共変量（回帰クリギングの平均と、ARD のガウス過程・LightGBM で使う）
COV = ["log_pass_3km", "log_pass_1km", "log_pass_nearest", "dist_station", "dist_metro",
       "far", "coverage", "road_width", "log_acreage", "log_muni_density", "muni_pop_change"]
NUM_LGB = ["dist_station", "log_acreage", "far", "coverage", "road_width", "gas", "water", "sewage",
           "frontage_ratio", "depth_ratio", "floors", "basement", "irregular", "station_square",
           "log_pass_nearest", "dist_nearest_st", "log_pass_1km", "log_pass_3km", "log_pass_10km",
           "dist_metro", "log_muni_density", "log_muni_pop", "muni_pop_change", "lat", "lon"]
CAT_LGB = ["use_district", "planning_area", "fire_area", "road_type"]
LGB_PARAMS = dict(learning_rate=0.08, num_leaves=31, min_child_samples=20, subsample=0.8, subsample_freq=1,
                  colsample_bytree=0.8, reg_lambda=1.0, n_estimators=400, random_state=SEED, verbose=-1,
                  n_jobs=1, max_bin=127)


def to_km(lat, lon, area):
    la0, lo0 = ORIGIN[area]
    return (lon - lo0) * 111.32 * np.cos(np.radians(la0)), (lat - la0) * 110.57


def load(use="住宅地"):
    d = pd.read_csv(DATA / "features_metro.csv", dtype={"code": str, "muni": str, "pref": str})
    if use is not None:
        d = d[d["land_use_class"] == use]
    d["y"] = np.log(d["price"])
    return d.reset_index(drop=True)


def score(y, p, sd=None, level=0.90):
    e = p - y
    ape = np.abs(np.exp(p - y) - 1)
    out = dict(n=len(y), r2=1 - (e ** 2).sum() / ((y - y.mean()) ** 2).sum(), rmse_log=np.sqrt((e ** 2).mean()),
               median_ape=np.median(ape), within20=(ape <= 0.2).mean())
    if sd is not None:
        from scipy.stats import norm
        z = norm.ppf(0.5 + level / 2)
        out["cover90"] = (np.abs(e) <= z * sd).mean()
        out["width90"] = np.median(np.exp(2 * z * sd))  # 上限÷下限（倍）
    return out


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
