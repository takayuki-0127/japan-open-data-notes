"""共通：内閣府「消費動向調査」長期時系列表1-3（主要耐久消費財の普及率、二人以上の世帯）を読む"""
from pathlib import Path
import re, logging, warnings
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
RAW, DATA, FIG, RES = ROOT / "data" / "raw", ROOT / "data", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
if not RAW.exists() or not any(RAW.glob("*.xlsx")):   # 初回は data/raw.zip を展開する
    import zipfile
    RAW.mkdir(parents=True, exist_ok=True); zipfile.ZipFile(DATA / "raw.zip").extractall(RAW)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：内閣府「消費動向調査」（e-Stat）を加工して作成"
ERA = {"昭和": 1925, "平成": 1988, "令和": 2018}
SIZES = ["計", "5,000人以上", "1,000～4,999人", "300～999人", "100～299人"]



def load():
    """各年3月末（1976年までは2月末）の普及率（％）。行＝年、列＝品目"""
    import openpyxl
    rows = list(openpyxl.load_workbook(RAW / "142_fukyuritsu_1-3.xlsx", read_only=True, data_only=True)
                .worksheets[0].iter_rows(values_only=True))
    hdr = rows[2]; out = []
    for r in rows[4:]:
        if not isinstance(r[0], (int, float)): continue
        rec = {"year": int(str(int(r[0]))[:4])}
        for j in range(3, 34):
            if hdr[j]: rec[hdr[j]] = float(r[j]) if isinstance(r[j], (int, float)) else np.nan
        out.append(rec)
    return pd.DataFrame(out).set_index("year")


def logistic(t, K, r, t0):
    return K / (1 + np.exp(-r * (t - t0)))
