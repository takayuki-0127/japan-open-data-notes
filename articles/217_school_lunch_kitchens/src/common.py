"""共通：厚生労働省「介護保険事業状況報告（年報）」全国計の要介護（要支援）認定者数（年度末現在）"""
from pathlib import Path
import logging, warnings
import pandas as pd
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
SOURCE = "出典：文部科学省「学校給食実施状況等調査」（平成22年度・令和7年度、e-Stat）をもとに作成者が加工して作成"
# タイル地図の位置（x, y）
TILE = {"北海道": (12, 0), "青森県": (12, 1), "秋田県": (11, 2), "岩手県": (12, 2), "福井県": (6, 3), "石川県": (7, 3), "富山県": (8, 3), "新潟県": (9, 3), "山形県": (11, 3), "宮城県": (12, 3),
        "島根県": (2, 4), "鳥取県": (3, 4), "兵庫県": (4, 4), "京都府": (5, 4), "滋賀県": (6, 4), "岐阜県": (7, 4), "長野県": (8, 4), "群馬県": (9, 4), "栃木県": (10, 4), "福島県": (11, 4),
        "山口県": (1, 5), "広島県": (2, 5), "岡山県": (3, 5), "大阪府": (4, 5), "奈良県": (5, 5), "三重県": (6, 5), "愛知県": (7, 5), "山梨県": (8, 5), "埼玉県": (9, 5), "茨城県": (10, 5),
        "佐賀県": (0, 6), "福岡県": (1, 6), "愛媛県": (2, 6), "香川県": (3, 6), "徳島県": (4, 6), "和歌山県": (5, 6), "静岡県": (7, 6), "神奈川県": (8, 6), "東京都": (9, 6), "千葉県": (10, 6),
        "長崎県": (0, 7), "熊本県": (1, 7), "大分県": (2, 7), "高知県": (3, 7), "鹿児島県": (0, 8), "宮崎県": (1, 8), "沖縄県": (0, 9)}


def load():
    """公立小・中学校の調理方式別の学校数（完全給食などの実施校）。single＝単独調理場（自校）方式、joint＝共同調理場（センター）方式"""
    return pd.read_csv(DATA / "lunch_kitchen_type_pref_2010_2025.csv")
