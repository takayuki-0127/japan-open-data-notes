"""共通：気象庁「生物季節観測」累年値ファイル（種目ごとのCSV、地点×年の観測日）を読む"""
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
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：気象庁「生物季節観測の情報」生物季節観測累年値（https://www.data.jma.go.jp/sakura/data/download_ruinenchi.html）をもとに作成者が加工して作成"

# 地点のおおよその緯度（気象台・測候所の所在地、小数1桁）
LAT = {"401": 45.4, "406": 43.9, "407": 43.8, "409": 44.0, "412": 43.1, "413": 43.2, "417": 42.9, "418": 43.0, "420": 43.3,
       "423": 42.3, "426": 42.2, "428": 41.9, "430": 41.8, "433": 42.9, "435": 44.4, "440": 42.3, "520": 38.8, "575": 40.8,
       "581": 40.5, "582": 39.7, "584": 39.7, "585": 39.6, "587": 38.9, "588": 38.3, "590": 38.3, "595": 37.8, "597": 37.1,
       "598": 36.9, "600": 37.4, "602": 38.0, "604": 37.9, "605": 36.6, "607": 36.7, "610": 36.7, "612": 37.1, "615": 36.5,
       "616": 36.1, "617": 36.2, "618": 36.2, "624": 36.4, "626": 36.2, "629": 36.4, "631": 35.7, "632": 35.4, "636": 35.2,
       "637": 35.5, "638": 35.7, "648": 35.7, "651": 34.7, "654": 34.7, "656": 35.0, "662": 35.7, "663": 34.1, "670": 35.4,
       "672": 35.0, "675": 34.8, "677": 34.1, "678": 33.1, "740": 36.2, "741": 35.5, "744": 35.4, "746": 35.5, "747": 35.5,
       "750": 35.5, "755": 34.9, "759": 35.0, "761": 35.3, "762": 34.0, "765": 34.4, "768": 34.7, "770": 34.7, "772": 34.7,
       "776": 34.3, "777": 34.2, "778": 33.5, "780": 34.7, "800": 34.2, "807": 33.6, "813": 33.3, "815": 33.2, "817": 32.7,
       "819": 32.8, "822": 32.6, "827": 31.6, "830": 31.9, "836": 30.4, "837": 30.7, "843": 32.7, "887": 33.8, "891": 34.3,
       "892": 33.2, "893": 33.6, "895": 34.1, "909": 28.4, "912": 24.5, "917": 24.4, "918": 24.3, "927": 24.8, "929": 26.3,
       "936": 26.2, "940": 26.6, "945": 25.8}


def load():
    """全種目を縦長に。値0（観測なし）は落とす。doy＝1月1日を1とする通日"""
    p = ROOT / "data" / "long.pkl"
    if p.exists(): return pd.read_pickle(p)
    rows = []
    for f in sorted(glob.glob(str(RAW / "[0-9][0-9][0-9].csv"))):
        code = Path(f).stem
        L = open(f, encoding="cp932").read().split("\n")
        name = L[0].split(",")[1]
        hdr = L[1].split(",")
        for l in L[2:]:
            c = l.split(",")
            if len(c) < 10 or not c[0].strip().isdigit(): continue
            st, sn = c[0].strip(), c[1].replace("　", "").strip()
            for j, h in enumerate(hdr):
                if h.isdigit() and 1953 <= int(h) <= 2026 and j + 1 < len(c):
                    v, rm = c[j].strip(), c[j + 1].strip()
                    rows.append((code, name, st, sn, int(h), int(v) if v.isdigit() else 0, rm))
    d = pd.DataFrame(rows, columns=["code", "name", "st", "stname", "year", "mmdd", "rm"])
    d["obs"] = (d.mmdd > 0).astype(int)
    m, dd = d.mmdd // 100, d.mmdd % 100
    ok = d.obs == 1
    dt = pd.to_datetime(dict(year=d.year.where(ok, 2001), month=m.where(ok, 1).clip(1, 12), day=dd.where(ok, 1).clip(1, 31)), errors="coerce")
    d["doy"] = np.where(ok, dt.dt.dayofyear, np.nan)
    # 種目ごとの「ふつうの時期」（観測日の月の中央値）で、年をまたいだ日付を前後の年に寄せる
    med = d[ok].assign(m=m[ok]).groupby("code").m.median()
    cm = d.code.map(med)
    d.loc[ok & (cm >= 8) & (m <= 3), "doy"] += 365    # 秋〜冬の現象が翌年1〜3月にずれ込んだ場合
    d.loc[ok & (cm <= 5) & (m >= 10), "doy"] -= 365   # 冬〜春の現象が前年10〜12月に起きた場合
    d["lat"] = d.st.map(LAT)
    d.to_pickle(p)
    return d


def jpn_temp():
    """日本の月平均気温偏差（1991〜2020年平均との差、15地点平均）"""
    t = pd.read_csv(RAW / "mon_jpn.csv", encoding="cp932")
    t.columns = ["year"] + list(range(1, 13))
    return t.set_index("year").apply(pd.to_numeric, errors="coerce")


def theil(y, x):
    from scipy.stats import theilslopes
    s, _, lo, hi = theilslopes(y, x)
    return s, lo, hi


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
