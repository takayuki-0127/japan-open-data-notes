"""F43 共通の設定と関数"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 43
H = 36          # 何か月先まで見るか
SHOCK = 0.25    # 金利ショックの大きさ（%ポイント、0.25＝25bp）

LABELS = {
    "ip": "鉱工業生産",
    "cpi": "消費者物価（生鮮除く）",
    "unemp": "失業率",
    "call": "短期金利（コール）",
    "long": "長期金利（10年）",
    "fx": "ドル円（上＝円安）",
    "imp": "輸入物価（契約通貨）",
}
# 消費税の引き上げ月（消費者物価の水準が段差で上がる）
TAX_MONTHS = ["1989-04-01", "1997-04-01", "2014-04-01", "2019-10-01"]

BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = ("出典：日本銀行「時系列統計データ検索サイト」、総務省「消費者物価指数」「労働力調査」、"
          "経済産業省「鉱工業指数」（内閣府「景気動向指数」の個別系列）をもとに作成者が加工して作成")


def setup_font():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for f in font_manager.findSystemFonts():
        if "NotoSansCJK" in f or "Noto Sans CJK" in f:
            font_manager.fontManager.addfont(f)
    plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "DejaVu Sans"], "axes.unicode_minus": False,
                         "axes.spines.top": False, "axes.spines.right": False, "font.size": 11,
                         "figure.dpi": 150, "savefig.bbox": "tight"})
    return plt
