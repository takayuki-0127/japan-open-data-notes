"""共通：警察庁「犯罪統計資料」（各年1〜12月確定値）の第1表（罪種別）と第2表（窃盗手口別）の認知件数を読む"""
from pathlib import Path
import logging, re, warnings
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
warnings.filterwarnings("ignore")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
logging.getLogger("pdfminer").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
RAW, FIG, RES, DATA = ROOT / "data" / "raw", ROOT / "figures", ROOT / "results", ROOT / "data"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE, RED = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6", "#c8433a"
SOURCE = "出典：警察庁「犯罪統計資料」（e-Stat）を加工して作成"

# 第1表で使う行（罪種）。第2表は手口すべて
GROUPS2 = ("侵入盗", "乗り物盗", "非侵入盗")


def _n(s):
    s = str(s).strip().replace(",", "")
    if s in ("", "-", "－", "―", "…"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return np.nan


def _norm(lab):
    lab = re.sub(r"\s+", "", lab).replace("（", "(").replace("）", ")")
    return lab.replace("うち)", "うち)")


# ---- PDF（2008〜2019年分） ----
NUM = re.compile(r"^-?[\d,]+(\.\d+)?$|^-$")


def _pdf_lines(path, title):
    import pdfplumber
    with pdfplumber.open(path) as p:
        for pg in p.pages[3:25]:
            t = pg.extract_text() or ""
            head = re.sub(r"\s+", "", t[:40])
            if head.startswith(title):
                return t.splitlines()
    raise RuntimeError(f"{title} not found in {path}")


def _parse_lines(lines):
    """行ごとに（ラベル, 今年の認知件数, 前年の認知件数）を返す。ラベルは数字の前までの文字"""
    out = []
    for ln in lines:
        toks = ln.split()
        k = next((i for i, x in enumerate(toks) if NUM.match(x)), None)
        if k is None or k == 0:
            continue
        lab = _norm("".join(toks[:k]))
        nums = toks[k:]
        if len(nums) < 2:
            continue
        out.append((lab, _n(nums[0]), _n(nums[1])))
    return out


def _with_group(rows, table):
    """第2表は手口の上に「侵入盗」「乗り物盗」「非侵入盗」の計の行がある。グループを付ける"""
    res, g = [], ""
    for lab, a, b in rows:
        if table == 2:
            if lab in ("窃盗総数",):
                g, item = "窃盗総数", "計"
            elif lab in GROUPS2:
                g, item = lab, "計"
            else:
                item = lab
            res.append((g, item, a, b))
        else:
            res.append(("", lab, a, b))
    return res


def read_pdf(path, year):
    rows = []
    for table, title in ((1, "第１表"), (2, "第２表")):
        rs = _with_group(_parse_lines(_pdf_lines(path, title)), table)
        for g, item, a, b in rs:
            rows.append(dict(year=year, table=table, group=g, item=item, count=a, prev=b))
    return rows


# ---- CSV（2020年分〜） ----
def read_csv(path, year):
    txt = path.read_bytes().decode("cp932", errors="replace").splitlines()
    import csv
    rows, table, g = [], None, ""
    for r in csv.reader(txt):
        if not r:
            continue
        if r[0].startswith("第１表"):
            table = 1; continue
        if r[0].startswith("第２表"):
            table = 2; continue
        if r[0].startswith("第") and r[0].endswith("表"):
            table = None; continue
        if table is None or len(r) < 4:
            continue
        a, b = _n(r[2]), _n(r[3])
        if np.isnan(a):
            continue
        c0, c1 = _norm(r[0]), _norm(r[1])
        if table == 1:
            if c0 == "刑法犯総数":
                item = "刑法犯総数"
            elif c1 == "計":
                item = c0
            else:
                item = c1
            rows.append(dict(year=year, table=1, group="", item=item, count=a, prev=b))
        else:
            if c0 == "窃盗総数":
                grp, item = "窃盗総数", "計"
            else:
                grp, item = c0, c1
            rows.append(dict(year=year, table=2, group=grp, item=item, count=a, prev=b))
    return rows


# CSV の罪名の改正などで名前が変わった行をそろえる
RENAME = {"不同意性交等": "強制性交等(不同意性交等)", "強制性交等": "強制性交等(不同意性交等)", "強姦": "強制性交等(不同意性交等)",
          "うち)不同意わいせつ": "うち)強制わいせつ(不同意わいせつ)", "うち)強制わいせつ": "うち)強制わいせつ(不同意わいせつ)",
          "凶悪犯": "凶悪犯", "窃盗犯": "窃盗犯"}


def load_counts():
    """年×表×グループ×項目の認知件数（各年の資料の当年値）。2007年は2008年分の前年値"""
    f = DATA / "crime_counts.csv"
    if f.exists():
        return pd.read_csv(f)
    raise FileNotFoundError("先に python build.py を実行してください")
