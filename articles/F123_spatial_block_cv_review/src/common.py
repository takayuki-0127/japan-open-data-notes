"""F123 共通：パス・図の体裁・3つのデータの読み込み・分け方"""
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
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "sans-serif"], "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13, "figure.dpi": 150,
                     "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
DATA, FIG, RES = ROOT / "data", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#3aa07a", "#8a5cc2"
SOURCE = ("出典：国土交通省「地価公示」（国土数値情報）、総務省「国勢調査」・厚生労働省「人口動態保健所・市区町村別統計」、"
          "気象庁「平年値」をもとに作成者が加工して作成（F03・F107・F74 の data を再利用）")
SEED = 2026

def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=6.5, color=GRAY, ha="left", va="top", wrap=True)
    fig.savefig(FIG / name); plt.close(fig)

def to_km(lat, lon, lat0=36.0):
    """緯度経度を、日本付近で使う近似の平面座標（km）に"""
    x = (lon - 137.0) * 111.32 * np.cos(np.radians(lat0))
    y = (lat - lat0) * 110.57
    return np.asarray(x), np.asarray(y)

# --- 3つのデータ（被説明変数 y、特徴量 X、座標 x,y km、都道府県 pref）
LAND_NUM = ["dist_station", "log_acreage", "far", "coverage", "road_width", "gas", "water", "sewage",
            "frontage_ratio", "depth_ratio", "floors", "basement", "irregular", "station_square",
            "log_pass_nearest", "dist_nearest_st", "log_pass_1km", "log_pass_3km", "log_pass_10km",
            "dist_metro", "log_muni_density", "log_muni_pop", "muni_pop_change"]
LAND_CAT = ["use_district", "planning_area", "fire_area", "road_type", "land_use_class"]
TFR_FEAT = ["young_f", "income", "commute_out", "nursery", "tertiary", "density", "unmarried", "aged",
            "owner", "floor", "pop"]
TEMP_FEAT = ["alt"]

def load(name):
    if name == "地価":
        d = pd.read_csv(DATA / "land_price_features.csv", dtype={"code": str, "muni": str, "pref": str})
        d["y"] = np.log(d["price"])
        for c in LAND_CAT:
            d[c] = d[c].astype("category").cat.codes
        x, y = to_km(d["lat"], d["lon"])
        feats = LAND_NUM + LAND_CAT
    elif name == "出生率":
        d = pd.read_csv(DATA / "municipal_tfr.csv", dtype={"code": str, "pref": str})
        d = d.dropna(subset=["tfr"]).copy()
        d["y"] = d["tfr"]; d["pop"] = np.log(d["pop"])
        x, y = d["x_km"].values, d["y_km"].values
        feats = TFR_FEAT
    elif name == "気温":
        d = pd.read_csv(DATA / "amedas_normals.csv", dtype={"id": str})
        d = d.dropna(subset=["annual", "lat", "lon", "alt"]).copy()
        d["y"] = d["annual"]; d["pref"] = d["area"].astype(str)
        x, y = to_km(d["lat"], d["lon"])
        feats = TEMP_FEAT
    d = d.reset_index(drop=True)
    d["xk"], d["yk"] = np.asarray(x, float), np.asarray(y, float)
    return d, feats

# --- 分け方
def folds(d, kind, k=5, seed=SEED, size=None):
    """各行の fold 番号を返す。random：地点ごと／block：size km 四方のマスごと／pref：都道府県（気温は予報区）ごと"""
    rng = np.random.default_rng(seed)
    n = len(d)
    if kind == "random":
        f = np.arange(n) % k
        rng.shuffle(f); return f
    if kind == "block":
        g = (np.floor(d["xk"] / size).astype(int).astype(str) + "_" + np.floor(d["yk"] / size).astype(int).astype(str)).values
    elif kind == "pref":
        g = d["pref"].astype(str).values
    u = np.unique(g); rng.shuffle(u)
    # 地点数がそろうように、大きいグループから順に一番少ない fold に入れる
    cnt = pd.Series(g).value_counts().reindex(u)
    order = cnt.sort_values(ascending=False, kind="stable").index
    load_, gf = np.zeros(k), {}
    for gg in order:
        j = int(np.argmin(load_)); gf[gg] = j; load_[j] += cnt[gg]
    return np.array([gf[gg] for gg in g])
