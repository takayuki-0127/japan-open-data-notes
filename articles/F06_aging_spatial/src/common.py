"""F06 共通設定"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"          # e-Stat からダウンロードした zip を展開した場所
DATA = ROOT / "data"
FIG = ROOT / "figures"
RES = ROOT / "results"
SEED = 20261025

# 対象の政令市：都道府県コード, 区のコード範囲, 平面直角座標系(EPSG), 市役所の位置(経度, 緯度)
CITIES = {
    "札幌市": dict(pref="01", wards=range(101, 111), epsg=6680, center=(141.3545, 43.0618)),
    "横浜市": dict(pref="14", wards=range(101, 119), epsg=6677, center=(139.6317, 35.4513)),
    "福岡市": dict(pref="40", wards=range(131, 138), epsg=6670, center=(130.4017, 33.5902)),
}
MIN_POP = 50  # これより人口の少ない区域は除く（頑健性で 30・100 も見る）


def setup_font():
    for name in ["Noto Sans CJK JP", "Noto Sans JP", "IPAexGothic"]:
        if any(name in f.name for f in font_manager.fontManager.ttflist):
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 110
