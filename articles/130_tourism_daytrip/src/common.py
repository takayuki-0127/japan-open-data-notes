"""共通：観光庁「共通基準による観光入込客統計」の都道府県別・年間値（集計表1〜3）を読む"""
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
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a"
SOURCE = "出典：観光庁「共通基準による観光入込客統計」をもとに作成者が加工して作成"
SEG = {"1": "日本人・観光目的", "2": "日本人・ビジネス目的", "3": "訪日外国人"}
TIDY = DATA / "irikomi_pref_year.csv"


def _year(fname):
    m = re.search(r"平成(\d+)", fname)
    if m: return 1988 + int(m.group(1))
    return int(re.search(r"(20\d\d)", fname).group(1))


def _rows(path):
    if open(path, "rb").read(2) == b"PK":
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        return {ws.title: [list(r) for r in ws.iter_rows(values_only=True)] for ws in wb.worksheets}
    import xlrd
    wb = xlrd.open_workbook(path)
    return {s.name: [s.row_values(i) for i in range(s.nrows)] for s in wb.sheets()}


def _num(v):
    try:
        x = float(str(v).replace(",", ""))
        return x
    except Exception:
        return np.nan


def _ensure_raw():
    """data/raw がなければ data/raw.zip を展開する"""
    if not RAW.exists() or not any(RAW.iterdir()):
        import zipfile
        RAW.mkdir(parents=True, exist_ok=True)
        zipfile.ZipFile(DATA / "raw.zip").extractall(RAW)


def build():
    """data/raw の Excel から、年×都道府県×区分×県内外×宿泊日帰り の長い表を作る"""
    _ensure_raw()
    out = []
    files = [f for f in glob.glob(str(RAW / "130_annual_*.xls*")) if "2022年" not in f]  # 2022は _new と同じ内容
    for f in sorted(files):
        y = _year(Path(f).name)
        book = _rows(f)
        for sh, seg in SEG.items():
            for r in book[sh][7:]:
                m = re.match(r"\s*(\d\d)\s*(\S+)", str(r[0]))
                if not m or int(m.group(1)) > 47: continue
                code, pref = int(m.group(1)), m.group(2)
                status = "集計中" if "集計中" in str(r[1]) else ""
                for k, (area, stay) in enumerate([("県内", "宿泊"), ("県内", "日帰り"), ("県外", "宿泊"), ("県外", "日帰り")]):
                    out.append(dict(year=y, code=code, pref=pref, segment=seg, area=area, stay=stay, status=status,
                                    visitors_k=_num(r[1 + k]), unit_yen=_num(r[5 + k]), spend_m=_num(r[9 + k])))
    df = pd.DataFrame(out)
    df.loc[df.status == "集計中", ["visitors_k", "unit_yen", "spend_m"]] = np.nan
    df.to_csv(TIDY, index=False, float_format="%.8g")
    return df


def load():
    if not TIDY.exists(): build()
    return pd.read_csv(TIDY)
