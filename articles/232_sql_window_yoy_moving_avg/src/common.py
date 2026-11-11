"""共通：フォント・保存先・T-SQL を DuckDB で試すための最小の書き換え"""
from pathlib import Path
import logging, re, warnings
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
DATA, SQL, FIG, RES = ROOT / "data", ROOT / "sql", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a"
SOURCE = "出典：経済産業省「商業動態統計」業態別販売額をもとに作成者が加工して作成"


def tsql_to_duckdb(q: str) -> str:
    """T-SQL の文を DuckDB で動かすための書き換え（この記事で使う範囲だけ）"""
    q = re.sub(r"DATEADD\(month,\s*(-?\d+),\s*([\w.]+)\)", lambda m: f"({m.group(2)} + INTERVAL ({m.group(1)}) MONTH)", q)
    q = re.sub(r"DATEDIFF\(month,\s*([\w.]+),\s*([\w.]+)\)", r"date_diff('month', \1, \2)", q)
    q = q.replace("AS FLOAT", "AS DOUBLE")  # T-SQL の FLOAT は8バイト。DuckDB の FLOAT は4バイトなので DOUBLE に
    return q


def save(fig, name, y=-0.02, source=SOURCE):
    fig.text(0.01, y, source, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
