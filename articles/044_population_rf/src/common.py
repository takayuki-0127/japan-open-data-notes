"""共通：国立社会保障・人口問題研究所「日本の地域別将来推計人口（令和5年推計）」の結果表を読む"""
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
RAW, FIG, RES = ROOT / "data" / "raw", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：国立社会保障・人口問題研究所「日本の地域別将来推計人口（令和5（2023）年推計）」をもとに作成者が加工して作成"
YRS = [2020, 2025, 2030, 2035, 2040, 2045, 2050]


def read_pop(name):
    """総人口の表（結果表1・封鎖人口）：1行＝地域、列＝2020〜2050年の人口"""
    d = pd.read_excel(RAW / name, header=None, skiprows=5)
    d = d.iloc[:, :11]; d.columns = ["code", "kind", "pref", "muni"] + YRS
    d = d[d.code.notna()].copy(); d["code"] = d.code.astype(int).astype(str).str.zfill(5); d["kind"] = d.kind.astype(str)
    for y in YRS: d[y] = pd.to_numeric(d[y], errors="coerce")
    return d


def munis(d):
    """市町村の単位：政令市は市全体、東京23区は区ごと、ほかの市・町村。都道府県・政令市の区（23区以外）・浜通り地域は除く"""
    return d[d.kind.isin(["1", "2", "3"]) | ((d.kind == "0") & d.code.str.startswith("131"))].copy()
