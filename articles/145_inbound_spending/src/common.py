"""共通：観光庁「インバウンド消費動向調査」の国籍・地域別 費目別1人当たり旅行支出を読む"""
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
DATA = ROOT / "data"; FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：観光庁「インバウンド消費動向調査」（https://www.mlit.go.jp/kankocho/tokei_hakusyo/gaikokujinshohidoko.html）をもとに作成者が加工して作成"
ITEMS = ["宿泊費", "飲食費", "交通費", "娯楽等サービス費", "買物代"]


def load():
    """年×費目×国籍・地域の1人1回当たり旅行支出（円、一般客・全目的、パッケージツアー参加費の内訳を含む）"""
    d = pd.read_csv(DATA / "spending_by_item.csv")
    long = d.melt(id_vars=["year", "item"], var_name="nat", value_name="yen")
    shop = pd.read_csv(DATA / "shopping_items_2025.csv").set_index("item")
    return long, shop


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
