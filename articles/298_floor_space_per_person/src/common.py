"""共通：令和5年住宅・土地統計調査 時系列統計表（e-Stat、閲覧用 Excel を CSV 文字列にした JSON）の読み込み"""
import json, csv, io, re, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw", "hlts_ts_subset.json")
FIG = os.path.join(ROOT, "figures")
RES = os.path.join(ROOT, "results")
DATA = os.path.join(ROOT, "data")
for p in (FIG, RES):
    os.makedirs(p, exist_ok=True)

def setup_font():
    for f in font_manager.findSystemFonts():
        if "NotoSansCJK-Regular" in f or "NotoSansCJKjp-Regular" in f:
            font_manager.fontManager.addfont(f)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name()
            break
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["savefig.dpi"] = 150
    plt.rcParams["svg.hashsalt"] = "hlts"

def load():
    return json.load(open(RAW, encoding="utf-8"))

def rows(sheet_csv):
    return [[c.strip() for c in r] for r in csv.reader(io.StringIO(sheet_csv))]

def num(s):
    s = s.replace(",", "").strip()
    if s in ("", "*", "-", "…", "x", "X"):
        return None
    try:
        return float(s)
    except ValueError:
        return None

WAREKI = {"昭和": 1925, "平成": 1988, "令和": 2018}
def year_from_label(s):
    """'令和５年' 'その８． 令和５年' などから西暦を返す"""
    s = s.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    m = re.search(r"(昭和|平成|令和)\s*(\d+)年", s)
    return WAREKI[m.group(1)] + int(m.group(2)) if m else None

def save_json(name, obj):
    with open(os.path.join(RES, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=True)

def savefig(fig, name):
    fig.savefig(os.path.join(FIG, name), bbox_inches="tight", metadata={"Software": None})
    plt.close(fig)
