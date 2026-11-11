"""共通：厚生労働省「賃金引上げ等の実態に関する調査」（令和7年）時系列表を読む"""
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
SOURCE = "出典：厚生労働省「賃金引上げ等の実態に関する調査」（e-Stat）を加工して作成"
ERA = {"昭和": 1925, "平成": 1988, "令和": 2018}
SIZES = ["計", "5,000人以上", "1,000～4,999人", "300～999人", "100～299人"]


def _rows(name):
    import openpyxl
    ws = openpyxl.load_workbook(RAW / f"{name}.xlsx", read_only=True, data_only=True).worksheets[0]
    return [list(r) for r in ws.iter_rows(values_only=True)]


def num(v):
    if v is None: return np.nan
    if isinstance(v, (int, float)): return float(v)
    s = str(v).replace(",", "").replace("(", "").replace(")", "").strip()
    try: return float(s)
    except ValueError: return np.nan


class YearParser:
    """「昭和44年」「　　45」「平成元年」「    ９１）」などを西暦に直す"""
    def __init__(self): self.era = None
    def __call__(self, s):
        if s is None: return None
        s = str(s).translate(str.maketrans("０１２３４５６７８９", "0123456789")).replace("　", " ").strip()
        m = re.match(r"(昭和|平成|令和)?\s*(元|\d+)", s)
        if not m: return None
        if m.group(1): self.era = m.group(1)
        if self.era is None: return None
        n = 1 if m.group(2) == "元" else int(m.group(2))
        return ERA[self.era] + n


def _clean_year_label(s):
    s = str(s).translate(str.maketrans("０１２３４５６７８９", "0123456789")).replace("　", " ").strip()
    # 末尾の注番号（例 "9１）" → "9"）を落とす
    return re.sub(r"\d）$", "", s)


def table1():
    """第1表：企業規模別 1人平均賃金の改定額（円）・改定率（％）。1975年以降（規模区分がそろう）"""
    rows = _rows("141_t1"); yp = YearParser(); out = []
    for r in rows[6:64]:
        lab = r[1]
        if lab is None: continue
        y = yp(_clean_year_label(lab))
        if y is None or y < 1975: continue
        amt = [num(v) for v in r[2:7]]; rate = [num(v) for v in r[7:12]]
        for s, a, p in zip(SIZES, amt, rate):
            out.append({"year": y, "size": s, "amount_yen": a, "rate_pct": p})
    return pd.DataFrame(out)


def sectioned(name, cols, start):
    """第4・6表：企業規模ごとのブロックを縦につないで long 形式にする"""
    rows = _rows(name); yp = None; sec = None; out = []
    for r in rows[start:]:
        a = r[0]
        if a not in (None, "") and (str(a).startswith(("第", "企業規模、年")) or "単位" in str(a)):
            continue
        if a not in (None, "") and not str(a).strip().startswith("注"):
            sec = str(a).replace("\n", "").replace(" ", "").strip(); yp = YearParser(); continue
        if sec is None or r[1] is None: continue
        y = yp(_clean_year_label(r[1]))
        if y is None: continue
        rec = {"size": sec, "year": y}
        for k, j in cols.items(): rec[k] = num(r[j])
        out.append(rec)
    return pd.DataFrame(out)


SIZE_NORM = {"企業規模計": "計", "5,000人以上": "5,000人以上", "1,000人～4,999人": "1,000～4,999人",
             "1,000～4,999人": "1,000～4,999人", "300～999人": "300～999人", "100～299人": "100～299人"}


def table4():
    """第4表：賃金の改定を実施した又は予定（col3）、1人平均賃金を引き上げた・引き上げる（col5）"""
    d = sectioned("141_t4", {"implemented": 3, "raised": 5, "cut": 6, "unchanged": 7}, 0)
    d["size"] = d["size"].map(SIZE_NORM); return d.dropna(subset=["size"])


T6 = {"業績": 3, "世間相場": 4, "雇用の維持": 5, "労働力の確保・定着": 6, "消費者物価": 7, "労使関係": 8,
      "親会社等": 9, "前年度の実績": 10, "最低賃金": 11}


def table6():
    """第6表：賃金の改定の決定に当たり最も重視した要素（単数回答のブロックのみ）"""
    d = sectioned("141_t6", T6, 0)
    d = d[~d["size"].str.contains("複数回答")]
    d["size"] = d["size"].map(SIZE_NORM); return d.dropna(subset=["size"])
