"""共通：不動産情報ライブラリ（国土交通省）の「不動産取引価格情報」CSV を読み、分析用に整える"""
from pathlib import Path
import logging, warnings, re, zipfile, io
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
RAW, FIG, RES = ROOT / "data" / "raw", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：国土交通省 不動産情報ライブラリ（https://www.reinfolib.mlit.go.jp/）。「不動産取引価格情報」（国土交通省）をもとに作成者が加工して作成"
WARDS = ["千代田区", "中央区", "港区", "新宿区", "文京区", "台東区", "墨田区", "江東区", "品川区", "目黒区", "大田区", "世田谷区", "渋谷区", "中野区", "杉並区",
         "豊島区", "北区", "荒川区", "板橋区", "練馬区", "足立区", "葛飾区", "江戸川区"]


def read_raw(name="Tokyo_20151_20261.zip"):
    with zipfile.ZipFile(RAW / name) as z:
        f = [n for n in z.namelist() if n.endswith(".csv")][0]
        return pd.read_csv(io.BytesIO(z.read(f)), encoding="cp932", low_memory=False)


def walk_min(s):
    s = str(s)
    if s.isdigit(): return float(s)
    return {"30分～60分": 45.0}.get(s, np.nan)          # 1時間以上は除く


def load(name="Tokyo_20151_20261.zip"):
    """中古マンション等の取引から、住宅として普通の取引だけを残す。戻り値の1行＝1取引"""
    d = read_raw(name)
    n0 = len(d); log = {"raw": n0}
    d = d[d["種類"] == "中古マンション等"]
    d = d[d["取引の事情等"].isna()]; log["no_special_circumstances"] = len(d)          # 競売・関係者間取引などを除く
    d = d[d["用途"].isna() | (d["用途"] == "住宅")]; log["residential_use"] = len(d)
    d["year_q"] = d["取引時期"].str.extract(r"(\d{4})年第(\d)四半期").apply(lambda r: f"{r[0]}Q{r[1]}", axis=1)
    d["q"] = pd.PeriodIndex(d.year_q, freq="Q"); d["year"] = d.q.dt.year
    d["built"] = pd.to_numeric(d["建築年"].astype(str).str.extract(r"(\d{4})年")[0], errors="coerce")
    d["age"] = d.year - d.built
    d["area"] = pd.to_numeric(d["面積（㎡）"].astype(str).str.replace(",", ""), errors="coerce")
    d["walk"] = d["最寄駅：距離（分）"].map(walk_min)
    d["price"] = pd.to_numeric(d["取引価格（総額）"], errors="coerce")
    d["ppm2"] = d.price / d.area / 10000                                              # 1㎡あたり（万円）
    d["struct"] = d["建物の構造"].map(lambda s: "SRC" if str(s).startswith("ＳＲＣ") else ("RC" if str(s).startswith("ＲＣ") else "その他"))
    d["renov"] = (d["改装"] == "改装済み").astype(int)
    d["muni"] = d["市区町村名"]; d["ward23"] = d.muni.isin(WARDS)
    d = d.dropna(subset=["age", "area", "walk", "ppm2"]); log["complete_fields"] = len(d)
    d = d[(d.age >= 0) & (d.age <= 60) & (d.area >= 15) & (d.area <= 200)]; log["age_area_range"] = len(d)
    lo, hi = d.ppm2.quantile([0.005, 0.995]); d = d[(d.ppm2 >= lo) & (d.ppm2 <= hi)]; log["trim_ppm2_0.5pct"] = len(d)
    d["lppm2"] = np.log(d.ppm2); d["larea"] = np.log(d.area)
    return d.reset_index(drop=True), log
