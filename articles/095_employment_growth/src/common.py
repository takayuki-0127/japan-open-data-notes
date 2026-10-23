"""共通：総務省統計局「労働力調査」長期時系列表（基本集計 表3-1・3-3、詳細集計 表10-2）を読む"""
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
DATA = ROOT / "data"
RAW, FIG, RES = DATA / "raw", ROOT / "figures", ROOT / "results"
# 元の Excel 3本は data/rodo_raw.zip にまとめて置いている。初回に展開する
if not any(RAW.glob("*.xlsx")) and (DATA / "rodo_raw.zip").exists():
    import zipfile
    RAW.mkdir(parents=True, exist_ok=True)
    zipfile.ZipFile(DATA / "rodo_raw.zip").extractall(RAW)
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：総務省統計局「労働力調査」長期時系列データ（e-Stat）を加工して作成"
SEXES = {"総数": "男女計", "男": "男", "女": "女"}
AGE5 = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75+"]


def _rows(path, sheet):
    import openpyxl
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True)[sheet]
    return [list(r) for r in ws.iter_rows(values_only=True)]


def _num(v):
    if v is None or isinstance(v, str):
        try:
            return float(str(v).replace(",", ""))
        except Exception:
            return np.nan
    return float(v)


def _basic(path, value):
    """表3-1（人口）・3-3（就業者）：年×男女×5歳階級。1973年は沖縄を含む2行目を使う"""
    out = []
    for sheet, sex in SEXES.items():
        for r in _rows(path, sheet):
            y = r[1]
            if not isinstance(y, (int, float)) or not 1968 <= y <= 2100:
                continue
            vals = [_num(v) for v in r[3:17]]   # 15-19 … 60-64, 65+, 65-69, 70-74, 75+
            d = dict(zip(AGE5[:10], vals[:10]))
            d.update({"65-69": vals[11], "70-74": vals[12], "75+": vals[13], "65+": vals[10]})
            for a, v in d.items():
                out.append({"year": int(y), "sex": sex, "age": a, value: v})
    df = pd.DataFrame(out)
    return df.drop_duplicates(["year", "sex", "age"], keep="last")   # 1973年：沖縄を含む値を残す


def load_emp_pop():
    """年×男女×5歳階級の15歳以上人口と就業者（万人）"""
    f = DATA / "emp_pop_5yr.csv"
    if f.exists():
        return pd.read_csv(f)
    pop = _basic(RAW / "kihon_3-1_pop5.xlsx", "pop")
    emp = _basic(RAW / "kihon_3-3_emp5.xlsx", "emp")
    df = pop.merge(emp, on=["year", "sex", "age"])
    df.to_csv(f, index=False)
    return df


def load_type():
    """年×男女×5歳階級の就業者・雇用者・役員を除く雇用者・正規・非正規（万人、詳細集計、2002年〜）"""
    f = DATA / "emptype_5yr.csv"
    if f.exists():
        return pd.read_csv(f)
    path = RAW / "shosai_10-2_type5.xlsx"
    blocks = {2: "総数", 9: "15-19", 23: "20-24", 37: "25-29", 44: "30-34", 51: "35-39", 58: "40-44", 65: "45-49",
              72: "50-54", 79: "55-59", 86: "60-64", 93: "65-69", 100: "70-74", 107: "75+"}
    out = []
    for sheet, sex in {"男女計": "男女計", "男": "男", "女": "女"}.items():
        for r in _rows(path, sheet):
            m = re.match(r"(\d{4}) Yearly", str(r[1] or ""))
            if not m:
                continue
            for c, a in blocks.items():
                v = [_num(x) for x in r[c:c + 5]]
                out.append({"year": int(m.group(1)), "sex": sex, "age": a, "emp": v[0], "employee": v[1],
                            "employee_ex": v[2], "regular": v[3], "nonregular": v[4]})
    df = pd.DataFrame(out)
    df.to_csv(f, index=False)
    return df


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=8, color=GRAY)
    fig.savefig(FIG / name)
    plt.close(fig)
