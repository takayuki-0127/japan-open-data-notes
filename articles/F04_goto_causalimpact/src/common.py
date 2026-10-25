"""F04 共通：パス・図の体裁・データの読み込み"""
from pathlib import Path
import logging, warnings
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
warnings.filterwarnings("ignore")
for name in ("matplotlib.font_manager", "pymc", "pytensor"):
    logging.getLogger(name).setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a"
SOURCE = "出典：観光庁「宿泊旅行統計調査」、厚生労働省「新型コロナウイルス感染症 新規陽性者数」をもとに作成者が加工して作成"
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
         "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫",
         "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎",
         "熊本", "大分", "宮崎", "鹿児島", "沖縄"]
SEED = 20200722
GOTO = pd.date_range("2020-07-01", "2020-12-01", freq="MS")      # 7/22開始、東京は10/1から、12/28に全国停止
CORE = pd.date_range("2020-08-01", "2020-11-01", freq="MS")      # 月のすべてが期間内の4か月
# 緊急事態宣言の日数の割合（東京都の発令期間で近似）
EMERG = {"2020-04": 24 / 30, "2020-05": 25 / 31, "2021-01": 24 / 31, "2021-02": 1.0, "2021-03": 21 / 31,
         "2021-04": 6 / 30, "2021-05": 1.0, "2021-06": 20 / 30, "2021-07": 20 / 31, "2021-08": 1.0, "2021-09": 1.0}


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)


def panel():
    """data/monthly_pref.csv：都道府県（と全国）×月"""
    return pd.read_csv(DATA / "monthly_pref.csv", parse_dates=["date"])


def national():
    d = panel()
    return d[d.pref == "全国"].set_index("date").asfreq("MS")
