"""共通：公害苦情調査の騒音の苦情件数（発生源の産業別・主な発生原因別）を読む"""
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
SOURCE = "出典：総務省公害等調整委員会「公害苦情調査」（e-Stat）をもとに作成者が加工して作成"


GROUPS = {"建設業": ["construction"], "製造業": ["manufacturing"], "飲食店・宿泊業": ["food_lodging"],
          "卸売・小売業": ["retail"], "運輸業": ["transport"],
          "その他の会社・事業所": ["agri_forest", "fishery", "mining", "utility", "info", "finance", "realestate", "science",
                          "lifestyle", "education", "medical", "cooperative", "services", "public", "unclassified"],
          "個人": ["individual"], "その他・不明（会社・事業所以外）": ["other", "unknown"]}


def load():
    d = pd.read_csv(DATA / "noise_by_source.csv").set_index("year")
    g = pd.DataFrame({k: d[v].sum(axis=1) for k, v in GROUPS.items()})
    g["合計"] = d.total
    return d, g


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
