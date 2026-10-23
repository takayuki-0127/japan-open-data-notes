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
RAW, FIG, RES = ROOT / "data" / "raw", ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：総務省統計局「住宅・土地統計調査」（e-Stat）を加工して作成"

# 地域識別コード：a＝全国・都道府県、1＝政令指定都市と東京都特別区部、0＝政令市の区と東京都の特別区、2＝市、3＝町村
LEVEL = {"a": "全国・都道府県", "1": "政令市・特別区部", "0": "政令市の区・特別区", "2": "市", "3": "町村"}


def num(x):
    try:
        if x in (None, "", "-", "…", "***", "X"): return np.nan
        return float(x)
    except Exception: return np.nan


def _rows(path):
    import openpyxl
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    return [list(r) for r in ws.iter_rows(values_only=True)]


def _area(s):
    m = re.match(r"(\d{5})_(.+)", str(s))
    return (m.group(1), m.group(2).replace("　", " ")) if m else (None, None)


# 第1-2表（居住世帯の有無別住宅数）の列：2023年と2018年で「空き家」の内訳の並びが違う
COLS_12 = {2023: dict(lev=0, area=1, v=2, cols=["houses", "occupied", "_a", "_b", "unocc", "temp", "vacant", "other", "rent", "sale", "second", "constr"]),
           2018: dict(lev=4, area=5, v=6, cols=["houses", "occupied", "_a", "_b", "unocc", "temp", "vacant", "second", "rent", "sale", "other", "constr"])}
# 第34-2表（2023）／第35-2表（2018）：空き家の種類×腐朽・破損の有無×建て方×構造
COLS_ROT = {2023: dict(area=1, rot=2, tate=3, kozo=4, v=5, cols=["vacant", "other", "rent", "sale", "second"]),
            2018: dict(area=5, rot=7, tate=9, kozo=11, v=12, cols=["vacant", "second", "rent", "sale", "other"])}
FILES = {2023: ("j2023_1-2.xlsx", "j2023_34-2.xlsx"), 2018: ("j2018_1-2.xlsx", "j2018_35-2.xlsx")}


def _load_year(y):
    c = COLS_12[y]; out = {}
    for r in _rows(RAW / FILES[y][0]):
        code, name = _area(r[c["area"]] if len(r) > c["area"] else None)
        if code is None: continue
        d = {"year": y, "code": code, "name": name, "level": str(r[c["lev"]]).strip()}
        for k, v in zip(c["cols"], r[c["v"]:c["v"] + len(c["cols"])]):
            if not k.startswith("_"): d[k] = num(v)
        out[code] = d
    c = COLS_ROT[y]
    for r in _rows(RAW / FILES[y][1]):
        code, _ = _area(r[c["area"]] if len(r) > c["area"] else None)
        if code not in out: continue
        rot, tate, kozo = (str(r[c[k]]) for k in ("rot", "tate", "kozo"))
        if not kozo.startswith("0_"): continue
        vals = dict(zip(c["cols"], (num(v) for v in r[c["v"]:c["v"] + 5])))
        if rot.startswith("1_") and tate.startswith(("0_", "00_")):
            for k in ("vacant", "other", "rent"): out[code][f"rot_{k}"] = vals[k]
        if rot.startswith("0_") and "一戸建" in tate:
            out[code]["det_vacant"] = vals["vacant"]; out[code]["det_other"] = vals["other"]
    return pd.DataFrame(out.values())


def load_muni(cache=True):
    """全国・都道府県・市区町村×2018/2023年の住宅数と空き家の種類（戸）。'-' は0として扱う"""
    p = ROOT / "data" / "muni_2018_2023.csv"
    if cache and p.exists(): return pd.read_csv(p, dtype={"code": str, "level": str})
    x = pd.concat([_load_year(2018), _load_year(2023)], ignore_index=True)
    num_cols = [k for k in x.columns if k not in ("year", "code", "name", "level")]
    x[num_cols] = x[num_cols].fillna(0)
    x.to_csv(p, index=False, encoding="utf-8-sig")
    return x


def load_national(cache=True):
    """全国の住宅数と空き家の種類（1958〜2023年）。時系列第1-1表と第4表から"""
    p = ROOT / "data" / "national_series.csv"
    if cache and p.exists(): return pd.read_csv(p)
    rows = _rows(RAW / "jts_00.xlsx")
    out = {}
    for r in rows:
        m = re.search(r"Oct\.1,(\d{4})", str(r[2]))
        if m is None or not isinstance(r[4], (int, float)) or r[4] < 1000: continue
        y = int(m.group(1))
        if y in out: continue  # 1973年は沖縄県を含まない行と含む行がある。前（含まない）を使い1978年以降は1行
        out[y] = {"year": y, "houses": r[4], "occupied": r[5], "vacant": num(r[10])}
    # 1973年は沖縄県を含む値に置き換え（第4表の内訳と合わせる）
    seen = 0
    for r in rows:
        if "Oct.1,1973" in str(r[2]) and isinstance(r[4], (int, float)):
            seen += 1
            if seen == 2: out[1973].update(houses=r[4], occupied=r[5], vacant=num(r[10]))
            if seen == 2: break
    x = pd.DataFrame(out.values()).set_index("year")
    t = _rows(RAW / "jts_05.xlsx")
    head8, years = t[8], t[12]
    kind, cur = [], None
    for j in range(len(years)):
        h = str(head8[j] or "")
        if "賃貸・売却用及び二次的住宅を除く" in h: cur = "other"
        elif h.startswith("賃貸用"): cur = "rent"
        elif h.startswith("売却用"): cur = "sale"
        elif h.startswith("二次的"): cur = "second"
        elif h == "総数": cur = "total"
        kind.append(cur)
    jp = [r for r in t if len(r) > 2 and r[2] == "全国" and r[4] is None][0]
    for j, (k, y) in enumerate(zip(kind, years)):
        if k in ("other", "rent", "sale", "second") and isinstance(y, int):
            x.loc[y, k] = num(jp[j])
    x = x[x.index >= 1958].reset_index().sort_values("year")
    x.to_csv(p, index=False, encoding="utf-8-sig")
    return x


def munis(x):
    """市区町村の分析単位：市、町村、政令市の区と特別区（政令市と特別区部の合計は重ねて数えないよう除く）"""
    return x[x.level.isin(["0", "2", "3"])].copy()


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
