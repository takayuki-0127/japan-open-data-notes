"""共通：日銀の時系列（data/raw）を読む・図の設定"""
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
SOURCE = "出典：日本銀行「時系列統計データ検索サイト」（https://www.stat-search.boj.or.jp/）のデータをもとに作成者が加工して作成"


def monthly(fname="boj_prices_fx.csv"):
    """月次：列＝系列コード、行＝月（PeriodIndex）"""
    d = pd.read_csv(RAW / fname)
    d["month"] = pd.PeriodIndex(d.date.astype(str).str[:4] + "-" + d.date.astype(str).str[4:], freq="M")
    return d.pivot(index="month", columns="series_code", values="value").sort_index()


def quarterly(fname="boj_tankan_di.csv"):
    """四半期：date は YYYYQQ（例 202603 = 2026年7〜9月期）"""
    d = pd.read_csv(RAW / fname)
    s = d.date.astype(str)
    d["q"] = pd.PeriodIndex(s.str[:4] + "Q" + s.str[4:].astype(int).astype(str), freq="Q")
    return d.pivot(index="q", columns="series_code", values="value").sort_index()
API_CREDIT = "このサービスは、日本銀行時系列統計データ検索サイトの API 機能を使用しています。サービスの内容は日本銀行によって保証されたものではありません。"
