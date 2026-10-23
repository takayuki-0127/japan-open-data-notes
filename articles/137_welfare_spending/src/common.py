"""共通：地方財政状況調査（市町村分）から作った市区町村×年度の歳出表を読む"""
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
SOURCE = "出典：総務省「地方財政状況調査」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00200251）をもとに作成者が加工して作成"
# 団体区分のコード → 記事で使うまとまり
GROUP = {1: "政令指定都市", 8: "中核市", 2: "東京23区", 9: "その他の市", 3: "その他の市", 4: "その他の市", 5: "町村"}
ITEMS = {"民生費・児童福祉費": "児童福祉費", "民生費・老人福祉費": "老人福祉費",
         "民生費・社会福祉費": "社会福祉費", "民生費・生活保護費": "生活保護費"}


def load():
    p = DATA / "municipal_expenditure.csv"
    if not p.exists():
        from build_data import main
        main()
    d = pd.read_csv(p, dtype={"code": str})
    d["group"] = d.kubun.map(GROUP)
    d["share"] = d["民生費・総額"] / d["歳出合計"]
    return d


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
