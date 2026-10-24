"""共通：経済構造実態調査（乙調査、2020年）の事業従事者規模別の事業所数・売上高を読む"""
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
SOURCE = "出典：総務省・経済産業省「経済構造実態調査」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00200555）をもとに作成者が加工して作成"



MID = {"４人以下": 2.5, "５人～９人": 7, "１０人～２９人": 19.5, "３０人～４９人": 39.5, "５０人～９９人": 74.5}
SHORT = {"教養・技能教授業（外国語会話教授業を除く）": "教養・技能教授業", "公園，遊園地・テーマパーク": "公園・遊園地", "インターネット附随サービス業": "ネット附随サービス業", "情報処理・提供サービス業": "情報処理・提供業", "その他のスポーツ施設提供業": "その他スポーツ施設"}


def load():
    d = pd.read_csv(DATA / "size_class_2020.csv", dtype={"code": str})
    for c in ["estab", "emp", "workers", "sales_mn"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["name"] = d.industry.map(lambda s: SHORT.get(s, s))
    tot = d[d.cls2 == "計"].copy()
    s = d[(d.cls2 != "計")].dropna(subset=["estab", "workers", "sales_mn"]).copy()
    s = s[(s.estab > 0) & (s.sales_mn > 0)]
    s["w_per"] = s.workers / s.estab
    s["sales_per"] = s.sales_mn / s.estab
    s["sales_per_w"] = s.sales_mn / s.workers * 100  # 万円/人
    return tot, s


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
