"""共通：データの読み込み・図の設定（3本の元記事 008・019・020 の読み込みをそのまま再現）"""
from pathlib import Path
import logging, warnings
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
RAW, ORIG = ROOT / "data" / "raw", ROOT / "data" / "original"
FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
SRC_MUNI = "出典：e-Stat「社会・人口統計体系 市区町村データ」「統計でみる市区町村のすがた2026」を加工して作成"
SRC_LFS = "出典：e-Stat「労働力調査 長期時系列データ 表1 a-1」（総務省統計局）を加工して作成"
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SEED = 20261104

CONTROLS = ["log_inc", "old", "univ", "log_density", "mfg", "primary", "single"]
LABEL = {"log_inc": "所得", "old": "65歳以上の割合", "univ": "大卒の割合", "log_density": "人口密度",
         "mfg": "第2次産業の割合", "primary": "第1次産業の割合", "single": "単独世帯の割合"}


def load_muni():
    """008・019 と同じ市区町村データ（municipal_base.csv）"""
    d = pd.read_csv(RAW / "municipal_base.csv")
    d = d[(d["A1101"] > 0) & (d["C120120"] > 0) & (d["A2301"] > 0)].copy().reset_index(drop=True)
    d["inc"] = d["C120110"] / d["C120120"] * 100
    d["log_inc"] = np.log(d["inc"])
    d["old"] = d["A1303"] / d["A1101"]
    d["univ"] = d["E9106"] / d["E9101"]
    d["mfg"] = d["F2211"] / d["F1102"]
    d["primary"] = d["F2201"] / d["F1102"]
    d["single"] = d["A810105"] / d["A710101"]
    d["ward23"] = d["code"].between(13101, 13123)
    for c in CONTROLS:
        d["z_" + c] = (d[c] - d[c].mean()) / d[c].std()
    return d


def load_extra():
    d = load_muni()
    x = pd.read_csv(RAW / "municipal_extra.csv")
    return d.merge(x, on="code", how="left")


LFS_COLS = {4: "labour_force", 7: "employed", 13: "unemployed", 19: "rate"}


def _read_lfs(sheet):
    df = pd.read_excel(RAW / "lt01-a10.xlsx", sheet_name=sheet, header=None).iloc[10:]
    month = pd.to_numeric(df[1].astype(str).str.extract(r"(\d+)月")[0], errors="coerce")
    df, month = df[month.notna()], month[month.notna()].astype(int)
    first_year = int(df[0].astype(str).str.extract(r"^(\d{4})")[0].dropna().iloc[0])
    years, y = [], first_year - 1
    for m in month:
        if m == 1: y += 1
        years.append(y)
    out = df[list(LFS_COLS)].rename(columns=LFS_COLS).apply(pd.to_numeric, errors="coerce")
    out.index = pd.PeriodIndex([f"{a}-{b:02d}" for a, b in zip(years, month)], freq="M")
    return out.dropna(subset=["unemployed"])


def load_unemp():
    """020 と同じ完全失業率（完全失業者 ÷ 労働力人口、原数値、2000年1月〜）"""
    raw = _read_lfs("原数値")
    y = (raw.unemployed / raw.labour_force * 100).loc["2000-01":]
    y.index = y.index.to_timestamp()
    return y
