"""共通：総務省「小売物価統計調査（構造編）」10大費目別消費者物価地域差指数（都道府県）を読む"""
from pathlib import Path
import re, io, logging, warnings, unicodedata
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
BLUE, ORANGE, GRAY, INK, LIGHT = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef"
SOURCE = "出典：総務省「小売物価統計調査（構造編）」消費者物価地域差指数（e-Stat）をもとに作成者が加工して作成"
PREF = ("北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 "
        "石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 "
        "岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県").split()
ITEMS = {"食料": "食料", "住居": "住居", "光熱": "光熱・水道", "家具": "家具・家事用品", "被服": "被服及び履物",
         "保健": "保健医療", "交通": "交通・通信", "教育": "教育", "教養": "教養娯楽", "諸雑費": "諸雑費"}
TIDY = DATA / "regional_price_index.csv"


def _norm(s):
    return re.sub(r"\s|　", "", unicodedata.normalize("NFKC", str(s)))


def _rows(p):
    b = open(p, "rb").read()
    if b[:2] == b"PK":
        import openpyxl
        ws = openpyxl.load_workbook(io.BytesIO(b), read_only=True, data_only=True).worksheets[0]
        return [["" if v is None else v for v in r] for r in ws.iter_rows(values_only=True)]
    import xlrd
    s = xlrd.open_workbook(file_contents=b).sheet_by_index(0)
    return [s.row_values(i) for i in range(s.nrows)]


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan


def parse_year(p, year):
    """1年分の表1から、都道府県×費目の指数を取り出す。
    「総合」は「家賃を除く総合」の左の列。2013〜2017年は持家の帰属家賃を除く総合（住居も同様）、2018年以降は帰属家賃を含む。"""
    R = _rows(p)
    fi = next(i for i, r in enumerate(R) if any(_norm(v) == "北海道" for v in r))
    H = {}
    for r in R[:fi]:
        for j, v in enumerate(r):
            if re.search(r"[぀-ヿ一-鿿]", str(v)):
                H[j] = H.get(j, "") + _norm(v)
    col = {}
    for j, h in H.items():
        if h.endswith("家賃を除く総合"):
            col["家賃を除く総合"] = j; col["総合"] = j - 1
        for k, name in ITEMS.items():
            if h.endswith(name) or (k in h and len(h) < 30 and not h.startswith("10大")):
                col.setdefault(name, j)
    out = []
    for r in R[fi:]:
        names = [_norm(v) for v in r]
        hit = [n for n in names if n in PREF]
        if not hit:
            continue
        pref = hit[0]
        for name, j in col.items():
            out.append((year, pref, name, _num(r[j])))
    df = pd.DataFrame(out, columns=["year", "pref", "item", "index"]).drop_duplicates(["year", "pref", "item"])
    return df


def load():
    if TIDY.exists():
        return pd.read_csv(TIDY)
    dfs = [parse_year(RAW / f"127_{y}.xls", y) for y in range(2013, 2026)]
    df = pd.concat(dfs, ignore_index=True)
    df["imputed_rent_included"] = (df["year"] >= 2018) & df["item"].isin(["総合", "住居"])
    df.to_csv(TIDY, index=False)
    return df
