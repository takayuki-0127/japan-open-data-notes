"""F110 共通：パス・図の体裁・データの読み込み・目的関数（LightGBM の検証誤差）"""
from pathlib import Path
import warnings, logging, time
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import lightgbm as lgb
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
SOURCE = "出典：国土交通省「地価公示」、東京電力パワーグリッド「エリア需給実績」、気象庁「過去の気象データ」をもとに作成者が加工して作成"
SEED = 2026
METHOD_LABEL = {"grid": "グリッド", "random": "ランダム", "tpe": "ベイズ最適化（TPE）", "gp": "ベイズ最適化（ガウス過程）"}
METHOD_COLOR = {"grid": PURPLE, "random": GRAY, "tpe": ORANGE, "gp": BLUE}
METHODS = ["grid", "random", "tpe", "gp"]

LAND_NUM = ["dist_station", "log_acreage", "far", "coverage", "road_width", "gas", "water", "sewage",
            "frontage_ratio", "depth_ratio", "floors", "basement", "irregular", "station_square",
            "log_pass_nearest", "dist_nearest_st", "log_pass_1km", "log_pass_3km", "log_pass_10km",
            "dist_metro", "log_muni_density", "log_muni_pop", "muni_pop_change", "lat", "lon"]
LAND_CAT = ["use_district", "planning_area", "fire_area", "road_type", "land_use_class"]
POWER_X = ["temp_mean", "temp_max", "temp_min", "humid", "precip", "holiday", "dow", "month", "obon",
           "nenmatsu", "gw", "offday", "covid", "temp_lag1", "t_index"]


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)


def load_land(seed=SEED):
    """地価：20km 四方のブロック単位で 学習60%・検証20%・テスト20% に分ける"""
    d = pd.read_csv(DATA / "land_features.csv", dtype={"code": str, "muni": str, "pref": str})
    d["y"] = np.log(d["price"])
    for c in LAND_CAT:
        d[c] = d[c].astype("category")
    rng = np.random.default_rng(seed)
    blocks = d["block20"].unique(); rng.shuffle(blocks)
    cum = d.groupby("block20").size().loc[blocks].cumsum() / len(d)
    part = pd.Series(np.where(cum <= 0.6, "train", np.where(cum <= 0.8, "valid", "test")), index=blocks)
    d["part"] = d["block20"].map(part)
    X = d[LAND_NUM + LAND_CAT]
    return {k: (X[d.part == k], d.loc[d.part == k, "y"].values) for k in ("train", "valid", "test")}


def load_power():
    """電力：東京の日次需要（対数）。学習 2016/4〜2022/3、検証 2022/4〜2024/3、テスト 2024/4〜"""
    d = pd.read_csv(DATA / "power_daily_tokyo.csv", parse_dates=["date"])
    d["t_index"] = (d["date"] - d["date"].min()).dt.days
    d = d.dropna(subset=POWER_X + ["log_d"])
    X = d[POWER_X]; y = d["log_d"].values
    tr = d.date < "2022-04-01"; va = (d.date >= "2022-04-01") & (d.date < "2024-04-01"); te = d.date >= "2024-04-01"
    return {"train": (X[tr], y[tr]), "valid": (X[va], y[va]), "test": (X[te], y[te])}


def fit_eval(data, p, max_rounds=1000, seed=0):
    """設定 p で学習し、検証 RMSE（早期打ち切りに使う）とテスト RMSE を返す"""
    params = dict(objective="regression", verbose=-1, num_threads=1, seed=seed,
                  learning_rate=p["learning_rate"], num_leaves=int(p["num_leaves"]),
                  min_child_samples=int(p["min_child_samples"]), feature_fraction=p["feature_fraction"],
                  bagging_fraction=p["bagging_fraction"], bagging_freq=1, lambda_l2=p["lambda_l2"])
    Xtr, ytr = data["train"]; Xva, yva = data["valid"]; Xte, yte = data["test"]
    t0 = time.time()
    m = lgb.train(params, lgb.Dataset(Xtr, ytr), max_rounds, valid_sets=[lgb.Dataset(Xva, yva)],
                  callbacks=[lgb.early_stopping(50, verbose=False)])
    pv = m.predict(Xva, num_iteration=m.best_iteration); pt = m.predict(Xte, num_iteration=m.best_iteration)
    return (float(np.sqrt(np.mean((pv - yva) ** 2))), float(np.sqrt(np.mean((pt - yte) ** 2))),
            int(m.best_iteration), time.time() - t0)


DEFAULT = dict(learning_rate=0.1, num_leaves=31, min_child_samples=20, feature_fraction=1.0,
               bagging_fraction=1.0, lambda_l2=0.0)
