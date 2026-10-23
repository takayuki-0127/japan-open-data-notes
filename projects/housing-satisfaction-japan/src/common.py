"""共通：国土交通省「住生活総合調査」表4（住宅及び居住環境の総合満足度 × 各要素の満足度）を読む"""
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
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a"
SOURCE = "出典：国土交通省「住生活総合調査」（e-Stat）をもとに作成者が加工して作成"
YEARS = [2013, 2018, 2023]
LEVELS = ["満足", "まあ満足", "多少不満", "非常に不満", "不明"]
COLS = ["総計", "総合_満足", "総合_まあ満足", "総合_多少不満", "総合_非常に不満", "総合_不明"]
TIDY = DATA / "satisfaction_t4.csv"


def _rows(path):
    if open(path, "rb").read(2) == b"PK":
        import openpyxl
        import io; ws = openpyxl.load_workbook(io.BytesIO(open(path, "rb").read()), read_only=True, data_only=True).worksheets[0]
        return [list(r) for r in ws.iter_rows(values_only=True)]
    import xlrd
    s = xlrd.open_workbook(path).sheet_by_index(0)
    return [s.row_values(i) for i in range(s.nrows)]


def _num(v):
    try:
        return float(str(v).replace(",", ""))
    except Exception:
        return np.nan


def _ensure_raw():
    """data/raw がなければ data/raw.zip を展開する"""
    if not RAW.exists() or not any(RAW.iterdir()):
        import zipfile
        RAW.mkdir(parents=True, exist_ok=True)
        zipfile.ZipFile(DATA / "raw.zip").extractall(RAW)


def build():
    """表4を、年 × 区分（住宅／居住環境／属性） × 項目 × 回答 の長い表にする（単位：千世帯）"""
    _ensure_raw()
    out = []
    for y in YEARS:
        rows = _rows(RAW / f"129_{y}_t4.xls")
        group, item = None, None
        for r in rows[9:]:
            a = str(r[0]).strip() if r[0] not in (None, "None") else ""
            if not a: continue
            if a == "総計":
                out.append(dict(year=y, group="総計", item="総計", answer="総計", **dict(zip(COLS, map(_num, r[1:7])))))
            elif a.endswith("各要素の満足度"):
                group = "住宅" if a.startswith("住宅") else "居住環境"
            elif a.startswith("属性"):
                group = "属性：" + re.sub(r"）?（\d+区分）", "", a.replace("属性", "")).strip("（）")
            elif re.match(r"^[①-⑳]", a):
                item = re.sub(r"（\d区分）$", "", a)
            elif a in LEVELS and group in ("住宅", "居住環境"):
                out.append(dict(year=y, group=group, item=item, answer=a, **dict(zip(COLS, map(_num, r[1:7])))))
            elif group and group.startswith("属性"):
                out.append(dict(year=y, group=group, item=a.replace("　", "　"), answer="計", **dict(zip(COLS, map(_num, r[1:7])))))
    df = pd.DataFrame(out)
    df.to_csv(TIDY, index=False)
    return df


def load():
    return pd.read_csv(TIDY) if TIDY.exists() else build()
