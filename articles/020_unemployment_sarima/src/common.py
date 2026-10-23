"""共通：労働力調査 長期時系列（表1 a-1）の読み込みと図の設定"""
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
FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
SOURCE = "出典：政府統計の総合窓口(e-Stat)「労働力調査 長期時系列データ 表1 a-1」（総務省統計局）をもとに作成者が加工して作成"
BLUE, ORANGE, GRAY, INK, LIGHT = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef"
COLS = {4: "labour_force", 7: "employed", 13: "unemployed", 19: "rate"}   # 男女計の列


def read(sheet):
    df = pd.read_excel(ROOT / "data" / "raw" / "lt01-a10.xlsx", sheet_name=sheet, header=None).iloc[10:]
    month = pd.to_numeric(df[1].astype(str).str.extract(r"(\d+)月")[0], errors="coerce")
    df, month = df[month.notna()], month[month.notna()].astype(int)
    first_year = int(df[0].astype(str).str.extract(r"^(\d{4})")[0].dropna().iloc[0])   # 西暦は元号の次の行にある
    years, y = [], first_year - 1
    for m in month:                       # 1月が来るたびに1年進める
        if m == 1: y += 1
        years.append(y)
    out = df[list(COLS)].rename(columns=COLS).apply(pd.to_numeric, errors="coerce")
    out.index = pd.PeriodIndex([f"{a}-{b:02d}" for a, b in zip(years, month)], freq="M")
    return out.dropna(subset=["unemployed"])


def load():
    raw, sa = read("原数値"), read("季節調整値")
    raw["rate_calc"] = raw.unemployed / raw.labour_force * 100     # 公表値は小数1桁なので、人数から計算し直す
    sa["rate_calc"] = sa.unemployed / sa.labour_force * 100
    return raw, sa
