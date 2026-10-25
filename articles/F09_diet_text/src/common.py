"""共通：国会会議録検索システム API（発言数・発言の抜粋）"""
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
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE, RED = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6", "#c8423b"
SEED = 20261025
SOURCE = "出典：国立国会図書館「国会会議録検索システム」検索用API、総務省「消費者物価指数」、厚生労働省「賃金引上げ等の実態に関する調査」をもとに作成者が加工して作成"
PERIODS = [(1985, 1994, "1985〜94年"), (1995, 2004, "1995〜2004年"), (2005, 2014, "2005〜14年"), (2015, 2026, "2015〜26年")]


def period_of(y):
    for a, b, lab in PERIODS:
        if a <= y <= b:
            return lab
