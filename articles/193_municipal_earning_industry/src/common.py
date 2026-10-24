"""共通：経済センサス‐活動調査（令和3年）市区町村別・産業大分類別の純付加価値額"""
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
SOURCE = "出典：総務省・経済産業省「令和3年経済センサス‐活動調査」（e-Stat）を加工して作成"


def load(name):
    return pd.read_csv(DATA / name)


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)

IND = {"AB": "農林漁業", "C": "鉱業", "D": "建設業", "E": "製造業", "F": "電気・ガス・水道", "G": "情報通信業", "H": "運輸業・郵便業",
       "I": "卸売業・小売業", "J": "金融業・保険業", "K": "不動産・物品賃貸", "L": "学術研究・専門サービス", "M": "宿泊・飲食サービス",
       "N": "生活関連・娯楽", "O": "教育・学習支援", "P": "医療・福祉", "Q": "複合サービス", "R": "その他のサービス"}
