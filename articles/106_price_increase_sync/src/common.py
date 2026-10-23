"""共通：総務省「小売物価統計調査」表1（調査品目の月別価格及び年平均価格、都道府県庁所在市及び人口15万以上の市）を読む"""
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
RAW, DATA, FIG, RES = ROOT / "data" / "raw", ROOT / "data", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：総務省「小売物価統計調査」（e-Stat）をもとに作成者が加工して作成"
MONTHS = [f"m{i:02d}" for i in range(1, 13)]

def _num(v):
    """'198', 198.0, '205 a)', 'a) 205', '-', '…' → (値, 代替銘柄フラグ)"""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return np.nan, False
    if isinstance(v, (int, float, np.integer, np.floating)):
        return float(v), False
    s = str(v).strip().replace(",", "")
    m = re.search(r"\d+(\.\d+)?", s)
    if not m:
        return np.nan, False
    return float(m.group()), bool(re.search(r"[a-z]\)", s))


def _str(v):
    return "" if v is None or (isinstance(v, float) and np.isnan(v)) else str(v).strip()


def parse_sheet(df, year):
    """1シートを (year, code, item, brand, unit, city, avg, m01..m12, flag) の行に。旧様式（2010〜2016、品目が縦に並ぶ）と新様式（1品目1シート）の両方に対応"""
    out, item, brand, unit = [], "", "", ""
    for r in df.itertuples(index=False):
        r = list(r) + [None] * (24 - len(r))
        c7 = _str(r[7])
        if c7.startswith("品目"):
            if c7 == "品目：":               # 2020年以降
                item = _str(r[8])
            else:                             # 2019年以前
                item = _str(r[10]); brand = _str(r[16]); unit = _str(r[22])
            continue
        if c7 == "銘柄：":
            brand = _str(r[8]); continue
        if c7 == "単位：":
            unit = _str(r[8]); continue
        if not re.fullmatch(r"1\d\d(\.0)?", _str(r[0])) or _str(r[1]) == "" or _str(r[2]) == "":
            continue
        code = str(int(float(r[2])))
        city = re.sub(r"市$", "", _str(r[8]).replace(" ", "").replace("　", ""))
        vals = [_num(x) for x in r[10:23]]
        subst = int(bool(re.search(r"[a-z]\)", _str(r[9]))) or any(f for _, f in vals))  # a)～z)：代替銘柄
        out.append([year, code, re.sub(r"\s+", "", item), brand, unit, city, vals[0][0]] +
                   [v for v, _ in vals[1:]] + [subst])
    return out


def parse_file(path):
    year = int(re.search(r"kouri_(\d{4})_", str(path)).group(1))
    rows = []
    for name, df in pd.read_excel(path, sheet_name=None, header=None).items():
        rows += parse_sheet(df, year)
    return rows


def parse_all(raw=RAW):
    rows = []
    for p in sorted(glob.glob(str(Path(raw) / "kouri_*.xls*"))):
        rows += parse_file(p)
    return pd.DataFrame(rows, columns=["year", "code", "item", "brand", "unit", "city", "avg"] + MONTHS + ["subst"])


def load_prices():
    """data/prices_*.csv（横持ち：品目×都市×年、月別12列）を読む"""
    fs = sorted(DATA.glob("prices_*.csv"))
    d = pd.concat([pd.read_csv(f, dtype={"code": str}) for f in fs], ignore_index=True)
    return d


def long_monthly(d):
    """横持ち → 縦持ち（年月ごとの1行）"""
    m = d.melt(id_vars=["key", "year", "city"], value_vars=MONTHS, var_name="m", value_name="price")
    m["month"] = m["m"].str[1:].astype(int)
    m["t"] = pd.PeriodIndex(year=m["year"], month=m["month"], freq="M")
    return m.drop(columns="m").sort_values(["key", "city", "t"]).reset_index(drop=True)


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=8, color=GRAY, ha="left", va="top")
