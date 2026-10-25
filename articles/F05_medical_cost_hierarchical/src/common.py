"""共通：医療費の地域差分析（市町村国保・後期高齢者医療、市区町村別、令和3〜5年度）"""
from pathlib import Path
import logging, warnings
import matplotlib
matplotlib.use("Agg")
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
DATA, RAW = ROOT / "data", ROOT / "data" / "raw"
FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SEED = 20261025
SOURCE = "出典：厚生労働省「医療費の地域差分析」（令和3〜5年度 基礎データ）、総務省「令和2年国勢調査」「人口推計」、厚生労働省「医療施設調査」をもとに作成者が加工して作成"
YEARS = {"r03": 2021, "r04": 2022, "r05": 2023}
TILE = {"北海道": (12, 0), "青森県": (12, 1), "秋田県": (11, 2), "岩手県": (12, 2), "福井県": (6, 3), "石川県": (7, 3), "富山県": (8, 3), "新潟県": (9, 3), "山形県": (11, 3), "宮城県": (12, 3),
        "島根県": (2, 4), "鳥取県": (3, 4), "兵庫県": (4, 4), "京都府": (5, 4), "滋賀県": (6, 4), "岐阜県": (7, 4), "長野県": (8, 4), "群馬県": (9, 4), "栃木県": (10, 4), "福島県": (11, 4),
        "山口県": (1, 5), "広島県": (2, 5), "岡山県": (3, 5), "大阪府": (4, 5), "奈良県": (5, 5), "三重県": (6, 5), "愛知県": (7, 5), "山梨県": (8, 5), "埼玉県": (9, 5), "茨城県": (10, 5),
        "佐賀県": (0, 6), "福岡県": (1, 6), "愛媛県": (2, 6), "香川県": (3, 6), "徳島県": (4, 6), "和歌山県": (5, 6), "静岡県": (7, 6), "神奈川県": (8, 6), "東京都": (9, 6), "千葉県": (10, 6),
        "長崎県": (0, 7), "熊本県": (1, 7), "大分県": (2, 7), "高知県": (3, 7), "鹿児島県": (0, 8), "宮崎県": (1, 8), "沖縄県": (0, 9)}


def short(p):
    return p if p == "北海道" else p[:-1]
