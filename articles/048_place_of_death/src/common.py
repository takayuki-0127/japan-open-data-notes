"""共通：厚生労働省「人口動態統計」（確定数）の CSV を読む"""
from pathlib import Path
import io, re, logging, warnings
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
SOURCE = "出典：「人口動態統計」（厚生労働省）（https://www.e-stat.go.jp/stat-search/files?toukei=00450011）確定数 2025年 上巻 第5.4表・第5.5表をもとに作成者が加工して作成"


def read_csv(name):
    """CP932 の CSV を文字列の表として読む"""
    txt = (RAW / name).read_bytes().decode("cp932")
    rows = [r.split(",") for r in txt.splitlines()]
    w = max(len(r) for r in rows)
    return pd.DataFrame([r + [""] * (w - len(r)) for r in rows])


def num(v):
    v = str(v).replace(",", "").strip()
    try:
        return float(v)
    except ValueError:
        return np.nan


def monthly_deaths():
    """第5.4表：死亡月別にみた年次別死亡数。2005年以降は毎年。long 形式（year, month, deaths, days）"""
    d = read_csv("mc040000.csv")
    start = d.index[d[0] == "死亡数"][0]; end = d.index[d[0] == "死亡率"][0]
    rows = []
    for i in range(start, end):
        y = int(d.iloc[i, 1])
        for m in range(1, 13):
            rows.append(dict(year=y, month=m, deaths=num(d.iloc[i, 2 + m])))
    x = pd.DataFrame(rows)
    x["date"] = pd.to_datetime(dict(year=x.year, month=x.month, day=1))
    x["days"] = x.date.dt.days_in_month
    return x


def place_of_death():
    """第5.5表：死亡の場所別にみた年次別死亡数（1951〜2025年）"""
    d = read_csv("mc050000.csv")
    cols = ["year", "total", "inst_total", "hospital", "clinic", "roken", "iryoin", "midwife", "nursing_home", "out_total", "home", "other"]
    x = d[d[0].str.fullmatch(r"\d{4}")].iloc[:, :12].copy(); x.columns = cols
    x = x.apply(lambda c: c.map(num)); x["year"] = x.year.astype(int)
    return x.reset_index(drop=True)
