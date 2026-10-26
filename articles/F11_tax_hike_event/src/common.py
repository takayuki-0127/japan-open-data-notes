"""共通の設定（パス・フォント・イベントの月）"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
for p in (DATA, RES, FIG):
    p.mkdir(exist_ok=True)

# 増税の月（税率が上がった月を 0 とする）
EVENTS = {"2014": "2014-04", "2019": "2019-10"}

STAT_IDS = {
    "amount": "000040270646",   # 品目分類（小分類まで）支出金額（月）2000年1月〜
    "nominal": "000040270647",  # 名目増減率（月）
    "real": "000040270648",     # 実質増減率（月）
    "items2015": "000040270649",  # 全品目（2015年改定）支出金額（月）2015〜2019
    "items2020": "000040270650",  # 全品目（2020年改定）支出金額（月）2020〜2024
}


def setup_font():
    for f in font_manager.findSystemFonts():
        if "NotoSansCJK" in f or "Noto Sans CJK" in f:
            font_manager.fontManager.addfont(f)
    plt.rcParams["font.family"] = "Noto Sans CJK JP"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 110
