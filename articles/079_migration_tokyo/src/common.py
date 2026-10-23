"""共通：総務省「住民基本台帳人口移動報告」長期時系列表（1954〜2025年、日本人移動者）を読む"""
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
RAW, FIG, RES = ROOT / "data" / "raw", ROOT / "figures", ROOT / "results"
# 元の Excel（66本）は GitHub では data/idou_raw.zip にまとめて置いている。初回に展開する
if not any(RAW.glob("*.xls*")) and (ROOT / "data" / "idou_raw.zip").exists():
    import zipfile
    RAW.mkdir(parents=True, exist_ok=True)
    zipfile.ZipFile(ROOT / "data" / "idou_raw.zip").extractall(RAW)
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：総務省「住民基本台帳人口移動報告」長期時系列表（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00200523）をもとに作成者が加工して作成"
PREF = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
        "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
        "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
        "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]
TOKYO_AREA = [11, 12, 13, 14]; NAGOYA_AREA = [21, 23, 24]; OSAKA_AREA = [26, 27, 28, 29]
# 都道府県庁所在地の緯度経度（概数）
CAP = {1: (43.06, 141.35), 2: (40.82, 140.74), 3: (39.70, 141.15), 4: (38.27, 140.87), 5: (39.72, 140.10), 6: (38.24, 140.36),
       7: (37.75, 140.47), 8: (36.34, 140.45), 9: (36.57, 139.88), 10: (36.39, 139.06), 11: (35.86, 139.65), 12: (35.61, 140.12),
       13: (35.69, 139.69), 14: (35.45, 139.64), 15: (37.90, 139.02), 16: (36.70, 137.21), 17: (36.59, 136.63), 18: (36.07, 136.22),
       19: (35.66, 138.57), 20: (36.65, 138.18), 21: (35.39, 136.72), 22: (34.98, 138.38), 23: (35.18, 136.91), 24: (34.73, 136.51),
       25: (35.00, 135.87), 26: (35.02, 135.76), 27: (34.69, 135.52), 28: (34.69, 135.18), 29: (34.69, 135.83), 30: (34.23, 135.17),
       31: (35.50, 134.24), 32: (35.47, 133.05), 33: (34.66, 133.93), 34: (34.40, 132.46), 35: (34.19, 131.47), 36: (34.07, 134.56),
       37: (34.34, 134.04), 38: (33.84, 132.77), 39: (33.56, 133.53), 40: (33.61, 130.42), 41: (33.25, 130.30), 42: (32.74, 129.87),
       43: (32.79, 130.74), 44: (33.24, 131.61), 45: (31.91, 131.42), 46: (31.56, 130.56), 47: (26.21, 127.68)}


def read_xl(f, **kw):
    """拡張子が .xls でも中身が xlsx のファイルがあるので、先頭の数バイトで読み方を決める"""
    eng = "openpyxl" if open(f, "rb").read(2) == b"PK" else "xlrd"
    return pd.read_excel(f, engine=eng, **kw)


def num(v):
    if isinstance(v, (int, float, np.integer, np.floating)): return float(v)
    s = str(v).strip().replace(",", "")
    if s in ("－", "-", "―", "…", "", "nan", "x", "X"): return 0.0
    try: return float(s)
    except ValueError: return np.nan


def era_year(s):
    s = str(s); m = re.search(r"(昭和|平成|令和)(\d+|元)年", s)
    if not m: return None
    n = 1 if m.group(2) == "元" else int(m.group(2))
    return {"昭和": 1925, "平成": 1988, "令和": 2018}[m.group(1)] + n


def code(v):
    try:
        c = int(str(v).strip())
        return c if 1 <= c <= 47 and len(str(v).strip()) <= 2 else None
    except ValueError: return None


def parse_od(df):
    """移動前（行）×移動後（列）の47×47行列"""
    hdr = df.iloc[4].tolist()
    cols = {}
    for j, h in enumerate(hdr):
        c = code(h)
        if c and c not in cols: cols[c] = j
    M = np.zeros((47, 47))
    for i in range(df.shape[0]):
        r = code(df.iat[i, 0])
        if not r: continue
        for c, j in cols.items(): M[r - 1, c - 1] = num(df.iat[i, j])
    return M


def load_od(cache=True):
    p = ROOT / "data" / "od.npz"
    if cache and p.exists():
        z = np.load(p); return {int(y): z[y] for y in z.files}
    od = {}
    for f in sorted(glob.glob(str(RAW / "*.xls*"))):
        name = Path(f).name
        if name.startswith("0000404308"): continue
        try:
            df = read_xl(f, header=None)
        except Exception as e:  # 1989年（平成元年）のファイルは壊れていて読めない
            print("読めないファイル:", name, e); continue
        y = era_year(df.iat[1, 1])
        if y: od[y] = parse_od(df)
    xl = read_xl(RAW / "000040430819_平成24年.xls", sheet_name=None, header=None)
    for k, df in xl.items(): od[int(k)] = parse_od(df)
    np.savez(p, **{str(y): m for y, m in od.items()})
    return od


def series_table(fname, sheet=0):
    """第2〜5表：都道府県×年"""
    df = read_xl(RAW / fname, sheet_name=sheet, header=None)
    years = [int(v) if str(v).strip().isdigit() else None for v in df.iloc[6].tolist()]
    rows = {}
    for i in range(df.shape[0]):
        c = str(df.iat[i, 0]).strip()
        if re.fullmatch(r"\d{2}", c):
            rows[int(c)] = [num(df.iat[i, j]) if years[j] else None for j in range(df.shape[1])]
    out = pd.DataFrame({c: [v for v, y in zip(vals, years) if y] for c, vals in rows.items()}, index=[y for y in years if y])
    return out  # index=年, columns=0(全国),1..47


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
