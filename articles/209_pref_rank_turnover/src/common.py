"""共通：社会・人口統計体系「社会生活統計指標－都道府県の指標－2015」と「統計でみる都道府県のすがた2026」の指標値を読む"""
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
SOURCE = "出典：総務省統計局「社会・人口統計体系」（社会生活統計指標2015・統計でみる都道府県のすがた2026、e-Stat）をもとに作成者が加工して作成"



PREF = ["北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県","茨城県","栃木県","群馬県","埼玉県","千葉県","東京都","神奈川県","新潟県","富山県","石川県","福井県","山梨県","長野県","岐阜県","静岡県","愛知県","三重県","滋賀県","京都府","大阪府","兵庫県","奈良県","和歌山県","鳥取県","島根県","岡山県","広島県","山口県","徳島県","香川県","愛媛県","高知県","福岡県","佐賀県","長崎県","熊本県","大分県","宮崎県","鹿児島県","沖縄県"]
FIELD = {"A": "人口・世帯", "B": "自然環境", "C": "経済基盤", "D": "行政基盤", "E": "教育", "F": "労働", "G": "文化・スポーツ",
         "H": "居住", "I": "健康・医療", "J": "福祉・社会保障", "K": "安全", "L": "家計", "M": "生活時間"}
P = [f"p{i:02d}" for i in range(1, 48)]


def load():
    """long形式：code, edition(2015/2026), year, p01..p47（都道府県コード順の指標値）"""
    d = pd.read_csv(DATA / "pref_indicators_2015_2026_editions.csv", dtype={"code": str})
    n = pd.read_csv(DATA / "indicator_names_2026.tsv", sep="\t")
    n["code"] = n.code.str.lstrip("#")
    return d, n


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
