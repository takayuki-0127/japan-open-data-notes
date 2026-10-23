"""共通：スポーツ庁「体力・運動能力調査」の表23「体力・運動能力の推移」を読む"""
from pathlib import Path
import re, zipfile, logging, warnings
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
SOURCE = "出典：スポーツ庁「体力・運動能力調査」（e-Stat）を加工して作成"
XLSX = RAW / "tairyoku_23_suii.xlsx"
TIDY = ROOT / "data" / "suii_long.csv"
ERA = {"S": 1925, "H": 1988, "R": 2018}
TABLE = {"表１": "青少年", "表２": "成年", "表３": "高齢者"}
Z2H = str.maketrans("０１２３４５６７８９ｍ", "0123456789m")


def _years(row):
    """見出し行（S40, 45, …, H元, 5, 10, …, R元, 2, …）を西暦の年度に直す"""
    out, era = {}, None
    for j, v in enumerate(row):
        if j < 2 or v is None or (isinstance(v, float) and np.isnan(v)):
            continue
        s = str(v).strip()
        m = re.match(r"^([SHR])(元|\d+)$", s)
        if m:
            era = m.group(1); n = 1 if m.group(2) == "元" else int(m.group(2))
        else:
            n = int(float(s))
        out[j] = ERA[era] + n
    return out


def _parse(path):
    d = pd.read_excel(path, header=None)
    rows, table, item, years = [], None, None, None
    for i in range(len(d)):
        a, b = d.iat[i, 0], d.iat[i, 1]
        a = a.strip() if isinstance(a, str) else None
        if a and a[:2] in TABLE:
            table = TABLE[a[:2]]; continue
        if a and "歳" not in a:                      # 種目名の行
            item = re.sub(r"\s+", "", a.translate(Z2H)).split("（")[0]; years = None; continue
        if a is None and years is None and isinstance(d.iat[i, 2], (str, int, float)) and str(d.iat[i, 2]).strip()[:1] in "SHR":
            years = _years(d.iloc[i].tolist()); continue
        if a and "歳" in a and years and b in ("男子", "女子"):
            age = a.translate(Z2H).replace("～", "-").replace("歳", "")
            for j, y in years.items():
                v = pd.to_numeric(d.iat[i, j], errors="coerce")
                if pd.notna(v):
                    rows.append((table, item, age, "男" if b == "男子" else "女", y, float(v)))
    df = pd.DataFrame(rows, columns=["group", "item", "age", "sex", "year", "value"])
    df["item"] = df["item"].replace({"新体力テストの合計点": "合計点", "持久走": "持久走"})
    return df


def load():
    """表23を縦長（区分・種目・年齢・男女・年度・値）にして返す。CSVがあればそれを使う"""
    if TIDY.exists():
        return pd.read_csv(TIDY, dtype={"age": str})
    if not XLSX.exists() and (ROOT / "data" / "tairyoku_raw.zip").exists():
        RAW.mkdir(parents=True, exist_ok=True)
        zipfile.ZipFile(ROOT / "data" / "tairyoku_raw.zip").extractall(RAW)
    df = _parse(XLSX)
    df.to_csv(TIDY, index=False, encoding="utf-8")
    return df


def note(fig, extra=""):
    fig.text(0.0, -0.02, SOURCE + (("。" + extra) if extra else ""), fontsize=8, color=GRAY, ha="left", va="top")


if __name__ == "__main__":
    df = load()
    print(df.groupby(["group", "item"]).agg(n=("value", "size"), y0=("year", "min"), y1=("year", "max")))
