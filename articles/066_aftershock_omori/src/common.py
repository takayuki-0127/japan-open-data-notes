"""共通：気象庁「地震月報（カタログ編）」の震源データ（1919〜2024年）を読む"""
from pathlib import Path
import glob, logging, warnings
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
SOURCE = "出典：気象庁「地震月報（カタログ編）」震源データ（https://www.data.jma.go.jp/eqev/data/bulletin/hypo.html）をもとに作成者が加工して作成"
NEG = {"-": -0.0, "A": -1.0, "B": -2.0, "C": -3.0}


def _mag(s):
    """2桁の固定長マグニチュード（F2.1）。先頭が - / A / B / C は負の値"""
    s = s.strip()
    if not s: return np.nan
    if s[0] in NEG and len(s) == 2:
        return NEG[s[0]] - int(s[1]) / 10
    try: return int(s) / 10
    except ValueError: return np.nan


def _f(s, dec):
    """固定長の数値。小数部が空白のときは整数として読む"""
    t = s.strip()
    if not t: return np.nan
    if s[-dec:].strip() == "":
        return float(s[:-dec])
    return float(s) / 10 ** dec


def parse(path):
    rows = []
    for l in open(path, encoding="latin1"):
        if l[0] != "J" or len(l) < 92: continue
        m = _mag(l[52:54])
        try:
            rows.append((int(l[1:5]), int(l[5:7]), int(l[7:9]), int(l[9:11]), int(l[11:13]), _f(l[13:17], 2),
                         int(l[21:24]) + _f(l[24:28], 2) / 60, int(l[32:36]) + _f(l[36:40], 2) / 60,
                         _f(l[44:49], 2), m, l[54], l[61], l[68:92].strip()))
        except ValueError:
            continue
    return rows


def load(cache=True):
    p = ROOT / "data" / "catalog.pkl"
    if cache and p.exists(): return pd.read_pickle(p)
    rows = []
    for f in sorted(glob.glob(str(RAW / "h*"))):
        if f.endswith(".zip"): continue
        rows += parse(f)
    d = pd.DataFrame(rows, columns=["y", "mo", "d", "h", "mi", "s", "lat", "lon", "depth", "mag", "mtype", "inten", "region"])
    d["s"] = d.s.fillna(0).clip(0, 59.99)
    d["time"] = pd.to_datetime(dict(year=d.y, month=d.mo, day=d.d, hour=d.h, minute=d.mi), errors="coerce") + pd.to_timedelta(d.s, unit="s")
    d = d.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)
    d.to_pickle(p)
    return d


def haversine(lat1, lon1, lat2, lon2):
    r = np.radians
    a = np.sin((r(lat2) - r(lat1)) / 2) ** 2 + np.cos(r(lat1)) * np.cos(r(lat2)) * np.sin((r(lon2) - r(lon1)) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(a))


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
