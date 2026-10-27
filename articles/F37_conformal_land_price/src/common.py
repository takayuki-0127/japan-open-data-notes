"""F37 共通：パス・図の体裁・特徴量の列（F03 と同じ特徴量を使う）"""
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

NUM = ["dist_station", "log_acreage", "far", "coverage", "road_width", "gas", "water", "sewage",
       "frontage_ratio", "depth_ratio", "floors", "basement", "irregular", "station_square",
       "log_pass_nearest", "dist_nearest_st", "log_pass_1km", "log_pass_3km", "log_pass_10km",
       "dist_metro", "log_muni_density", "log_muni_pop", "muni_pop_change", "lat", "lon"]
CAT = ["use_district", "planning_area", "fire_area", "road_type", "land_use_class"]
FEAT = NUM + CAT

# F03 より木の数を減らし学習率を上げた（計算を軽くするため。F03 との精度の差は README に記載）
PARAMS = dict(learning_rate=0.08, num_leaves=63, min_child_samples=20, subsample=0.8, subsample_freq=1,
              colsample_bytree=0.8, reg_lambda=1.0, n_estimators=400, random_state=SEED, verbose=-1, n_jobs=2, max_bin=127)


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


REGION = {**{p: "北海道・東北" for p in ["01", "02", "03", "04", "05", "06", "07"]},
          **{p: "関東" for p in ["08", "09", "10", "11", "12", "13", "14"]},
          **{p: "中部" for p in ["15", "16", "17", "18", "19", "20", "21", "22", "23"]},
          **{p: "近畿" for p in ["24", "25", "26", "27", "28", "29", "30"]},
          **{p: "中国・四国" for p in ["31", "32", "33", "34", "35", "36", "37", "38", "39"]},
          **{p: "九州・沖縄" for p in ["40", "41", "42", "43", "44", "45", "46", "47"]}}
