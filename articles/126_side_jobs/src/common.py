"""共通：令和4年就業構造基本調査（全国結果）の統計表を縦長の表に直す"""
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
RAW, FIG, RES, DATA = ROOT / "data" / "raw", ROOT / "figures", ROOT / "results", ROOT / "data"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a"
SOURCE = "出典：総務省「令和4年就業構造基本調査」（e-Stat）をもとに作成者が加工して作成"


def strip(s):
    """'221_正規の職員・従業員' → '正規の職員・従業員'、'02_Ｂ専門的…' → '専門的…'"""
    s = re.sub(r"^[0-9A-Z]+_", "", str(s))
    return re.sub(r"^[Ａ-Ｚ]", "", s)


def read_table(fname, dims, colname, keep=None):
    """e-Stat の統計表 Excel を縦長に。dims は 2,4,6,… 列目の見出し名（階層レベルの右の列）"""
    out = DATA / (Path(fname).stem + ".csv")
    if out.exists():
        return pd.read_csv(out)
    import openpyxl
    rows = list(openpyxl.load_workbook(RAW / fname, read_only=True, data_only=True).worksheets[0].iter_rows(values_only=True))
    items = [strip(v) for v in rows[6][10:] if v]
    recs = []
    for r in rows[9:]:
        if not r or r[1] is None: continue
        key = {d: strip(r[1 + 2 * i]) for i, d in enumerate(dims)}
        for j, it in enumerate(items):
            v = r[10 + j]
            key2 = dict(key); key2[colname] = it
            key2["n"] = float(v) if isinstance(v, (int, float)) else (0.0 if v == "-" else np.nan)
            recs.append(key2)
    x = pd.DataFrame(recs).drop(columns=["地域"])
    if keep is not None:
        x = keep(x)
    x = x[x.n.notna()]
    x.to_csv(out, index=False, encoding="utf-8-sig")
    return x


def t206():
    return read_table("126_r4_206.xlsx", ["地域", "男女", "副業", "育児", "本業の地位"], "本業の所得")


def t084():
    # 副業の地位は「総数」だけ、本業の地位は主な区分だけ残す
    k = lambda x: x[(x["副業の地位"] == "総数") & x["本業の地位"].isin(["総数", "うち雇用者", "正規の職員・従業員", "非正規の職員・従業員", "うち自営業主"])]
    return read_table("126_r4_084.xlsx", ["地域", "男女", "本業の地位", "本業の職業", "副業の地位"], "副業の職業", k)


def t076():
    k = lambda x: x[x["本業の就業日数・時間"].isin(["総数", "200日未満", "200日以上"])]
    return read_table("126_r4_076.xlsx", ["地域", "男女", "副業", "本業の地位", "本業の職業"], "本業の就業日数・時間", k)


def note(ax, text=SOURCE, y=-0.14):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
