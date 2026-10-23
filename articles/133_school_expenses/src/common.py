"""共通：文部科学省「子供の学習費調査」（令和5年度）年次統計を読む"""
from pathlib import Path
import io, re, zipfile, logging, warnings
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
DATA, RAW, FIG, RES = ROOT / "data", ROOT / "data" / "raw", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：文部科学省「子供の学習費調査」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00400201）をもとに作成者が加工して作成"
SCHOOLS = {"y": "幼稚園", "e": "小学校", "j": "中学校", "h": "高等学校（全日制）"}
# 親の見出し（同じ名前の「その他」「月謝等」を区別するため）
CTX = {"学校教育費", "補助学習費", "家庭内学習費", "芸術文化活動", "スポーツ・レクリエーション活動", "教養・その他"}
AMBIG = {"その他", "月謝等", "図書費"}
TIDY = DATA / "learning_cost.csv"


def _extract():
    if not RAW.exists():
        RAW.mkdir(parents=True)
        with zipfile.ZipFile(DATA / "raw.zip") as z:
            z.extractall(RAW)


def _num(v):
    if v is None:
        return np.nan
    s = str(v).strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return np.nan  # 「…」「－」は空欄


def build():
    import openpyxl
    _extract()
    rows = []
    for key, school in SCHOOLS.items():
        wb = openpyxl.load_workbook(io.BytesIO((RAW / f"133_2023_{key}.xls").read_bytes()), data_only=True)
        ws = wb.worksheets[0]
        vals = [list(r) for r in ws.iter_rows(values_only=True)]
        i_kubun = next(i for i, r in enumerate(vals) if str(r[0]).strip() == "区分")
        i_year = next(i for i, r in enumerate(vals) if str(r[0]).strip() == "年度（西暦）")
        setting, cols = None, []
        for j, v in enumerate(vals[i_kubun][1:], start=1):
            if v:
                setting = "公立" if str(v).startswith("公立") else "私立"
            y = vals[i_year][j]
            if y:
                cols.append((j, setting, int(re.match(r"(\d{4})", str(y)).group(1))))
        ctx = None
        for r in vals[i_year + 1:]:
            lab = str(r[0]).strip() if r[0] else ""
            if not lab:
                continue
            lab = re.sub(r"\s", "", lab)
            if lab in CTX:
                ctx = lab
            elif lab in ("通信教育・家庭教師費", "学習塾費"):
                ctx = "補助学習費"
            item = f"{ctx}/{lab}" if lab in AMBIG else lab
            for j, st, y in cols:
                rows.append({"school": school, "setting": st, "year": y, "item": item, "yen": _num(r[j])})
    df = pd.DataFrame(rows)
    df.to_csv(TIDY, index=False, encoding="utf-8-sig")
    return df


def load():
    if not TIDY.exists():
        return build()
    return pd.read_csv(TIDY)


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
