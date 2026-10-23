"""共通：農林水産省「作物統計調査」茶の累年統計（全国・主産県）と全国の荒茶生産量（茶種別）を読む"""
from pathlib import Path
import logging, warnings, re, zipfile
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
DATA = ROOT / "data"; RAW = DATA / "raw"; FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：農林水産省「作物統計調査」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00500215）をもとに作成者が加工して作成"


def _raw():
    if not (RAW / "zenkoku.xls").exists():
        with zipfile.ZipFile(DATA / "raw.zip") as z:
            z.extractall(RAW)


def _num(v):
    return float(v) if isinstance(v, (int, float)) else np.nan


def _year(s):
    m = re.search(r"\((\d{4})\)", str(s))
    return int(m.group(1)) if m else None


def _ruinen(name):
    import xlrd
    s = xlrd.open_workbook(RAW / name).sheet_by_index(0)
    rows = []
    for i in range(6, s.nrows):
        r = s.row_values(i); y = _year(r[0])
        if y:
            rows.append({"year": y, "area_ha": _num(r[1]), "plucked_area_ha": _num(r[2]),
                         "leaf_t": _num(r[3]), "aracha_t": _num(r[4])})
    return pd.DataFrame(rows)


def _aracha():
    """全国累年の荒茶生産量（茶種別、t）。和暦の行を西暦にする"""
    import xlrd
    s = xlrd.open_workbook(RAW / "aracha.xls").sheet_by_index(0)
    era, rows = None, []
    for i in range(10, s.nrows):
        r = s.row_values(i); lab = str(r[0]).strip()
        if lab.startswith("昭和"): era, lab = 1925, lab.replace("昭和", "").replace("年産", "")
        elif lab.startswith("平成"): era, lab = 1988, lab.replace("平成", "")
        elif lab.startswith("令和"): era, lab = 2018, lab.replace("令和", "")
        lab = lab.strip().replace("元", "1")
        if era is None or not lab.isdigit():
            continue
        v = [_num(x) if x not in ("-",) else 0.0 for x in r[1:10]]
        rows.append(dict(zip(["year", "total", "gyokuro", "kabuse", "tencha", "sencha", "tamaryokucha", "bancha", "other", "black"],
                             [era + int(lab)] + v)))
    d = pd.DataFrame(rows)
    # 2009〜2016年産は玉露・かぶせ茶・てん茶を「おおい茶」として一括で表章（かぶせ茶の列に入っている）
    d["ooi"] = d[["gyokuro", "kabuse", "tencha"]].sum(axis=1, min_count=1)
    m = d.year.between(2009, 2016)
    d.loc[m, "ooi"] = d.loc[m, "kabuse"]
    d.loc[m, ["gyokuro", "kabuse", "tencha"]] = np.nan
    return d


def load():
    p1, p2, p3 = DATA / "national.csv", DATA / "main_prefs_total.csv", DATA / "aracha_by_type.csv"
    if not (p1.exists() and p2.exists() and p3.exists()):
        _raw()
        _ruinen("zenkoku.xls").to_csv(p1, index=False)
        _ruinen("shusanken.xls").to_csv(p2, index=False)
        _aracha().to_csv(p3, index=False)
    return pd.read_csv(p1), pd.read_csv(p2), pd.read_csv(p3)


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
