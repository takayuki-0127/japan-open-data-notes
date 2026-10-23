"""共通：文部科学省「学校基本調査」年次統計の Excel を読む"""
from pathlib import Path
import glob, re, logging, warnings
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
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：「学校基本調査」（文部科学省）（https://www.e-stat.go.jp/stat-search/files?toukei=00400001）年次統計をもとに作成者が加工して作成"


def num(v):
    v = str(v).replace(",", "").strip()
    try:
        return float(v)
    except ValueError:
        return np.nan


def rates():
    """年次統計4：進学率（1948〜2025年）。大学（学部）・短大（本科）は過年度高卒者等を含む"""
    d = pd.read_excel(RAW / "nen004.xlsx", header=None)
    d = d[d[1].astype(str).str.fullmatch(r"\d{4}")]
    cols = {"year": 1, "hs_m": 8, "hs_f": 9, "univjc": 16, "univjc_m": 17, "univjc_f": 18,
            "univ": 19, "univ_m": 20, "univ_f": 21, "jc": 22, "jc_m": 23, "jc_f": 24}
    x = pd.DataFrame({k: d[c].map(num) for k, c in cols.items()}); x["year"] = x.year.astype(int)
    return x.reset_index(drop=True)


def schools(name):
    """年次統計（学校種ごと）：学校数・在籍者数・本務教員数（計）。k003=小学校、k004=中学校、k010=大学"""
    d = pd.read_excel(RAW / name, header=None)
    d = d[d[1].astype(str).str.fullmatch(r"\d{4}")]
    x = pd.DataFrame({"year": d[1].astype(int), "schools": d[2].map(num), "public": d[4].map(num), "private": d[5].map(num),
                      "pupils": d[6].map(num), "teachers": d[12].map(num)})
    return x.reset_index(drop=True)
