"""共通：農林水産省「食料需給表」（令和6年度、e-Stat の CSV）を読む"""
from pathlib import Path
import csv, io, logging, warnings, zipfile
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
RAW, FIG, RES = ROOT / "data" / "raw", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
if not any(RAW.glob("jukyu_r6_*.csv")) and (ROOT / "data" / "jukyu_raw.zip").exists():
    RAW.mkdir(parents=True, exist_ok=True)
    zipfile.ZipFile(ROOT / "data" / "jukyu_raw.zip").extractall(RAW)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE, RED = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6", "#c8443a"
SOURCE = "出典：農林水産省「食料需給表」（e-Stat）を加工して作成"
# e-Stat のファイル（令和6年度食料需給表）
FILES = {"pop": "jukyu_r6_01.csv",        # 総人口
         "kg": "jukyu_r6_14.csv",         # 国民1人・1年当たり供給純食料（kg）
         "kcal": "jukyu_r6_16.csv",       # 国民1人・1日当たり供給熱量（kcal）
         "ssr_item": "jukyu_r6_84.csv",   # 品目別自給率（重量ベース）
         "ssr_total": "jukyu_r6_85.csv",  # 総合自給率等
         "feed": "jukyu_r6_98.csv"}       # 飼料需給表


def _num(x):
    x = str(x).replace(",", "").replace('"', "").strip()
    try:
        return float(x)
    except ValueError:
        return np.nan


def read_wide(key):
    """e-Stat の累年表（行＝項目、列＝年度）を long 形式（item, year, value）で返す"""
    text = (RAW / FILES[key]).read_bytes().decode("cp932")
    rows = list(csv.reader(io.StringIO(text)))
    h = next(i for i, r in enumerate(rows) if any(str(c).startswith("1960年度") or str(c).startswith("1965年度") for c in r))
    head = rows[h]
    ycol = {j: int(str(c)[:4]) for j, c in enumerate(head) if str(c)[:4].isdigit() and "年度" in str(c)}
    first = min(ycol)  # 最初の年度列
    out = []
    for r in rows[h + 1:]:
        if len(r) <= first or not any(r):
            continue
        item = r[first - 1].strip() if first >= 1 else ""
        for j, y in ycol.items():
            if j < len(r):
                out.append((item, y, _num(r[j])))
    return pd.DataFrame(out, columns=["item", "year", "value"])


def wide(key):
    d = read_wide(key)
    return d.pivot_table(index="year", columns="item", values="value", aggfunc="first")
