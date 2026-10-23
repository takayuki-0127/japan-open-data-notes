"""共通：気象庁「海洋の健康診断表」の海面水位・海面水温のデータを読む"""
from pathlib import Path
import logging, warnings, zipfile
import numpy as np, pandas as pd
import statsmodels.api as sm
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
if not (RAW / "sst_areaall.txt").exists() and (ROOT / "data" / "sst_area_txt.zip").exists():
    zipfile.ZipFile(ROOT / "data" / "sst_area_txt.zip").extractall(RAW)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SRC_SL = "出典：気象庁「海洋の健康診断表」日本沿岸の海面水位の長期変化傾向 を加工して作成"
SRC_SST = "出典：気象庁「海洋の健康診断表」海面水温の長期変化傾向（日本近海・全球平均）を加工して作成"

STATIONS = {"Wakkanai": "稚内", "Abashiri": "網走", "Kushiro": "釧路", "Hakodate": "函館", "Oofunato": "大船渡",
            "Mera": "布良", "Chichijima": "父島", "Kushimoto": "串本", "Aburatu": "油津", "Naha": "那覇",
            "Nagasaki": "長崎", "Hamada": "浜田", "Toyama": "富山"}
AREAS = {"A": "先島諸島周辺", "B": "東シナ海南部", "C": "東シナ海北部", "D": "黄海", "E": "日本海南西部", "F": "日本海中部",
         "G": "日本海北東部", "I": "網走沖", "J": "釧路沖", "K": "三陸沖", "L": "関東の東", "M": "関東の南",
         "N": "四国・東海沖", "O": "沖縄の東", "all": "日本近海（13海域平均）"}
SEASONS = {"Annual": "年", "Winter": "冬(1-3月)", "Spring": "春(4-6月)", "Summer": "夏(7-9月)", "Autumn": "秋(10-12月)"}


def load_sl():
    d = pd.read_csv(RAW / "sl.csv", encoding="utf-8-sig", comment="注")
    d.columns = ["year", "pt4", "pt4_ma5", "area4", "area4_ma5"]
    d = d[pd.to_numeric(d["year"], errors="coerce").notna()].astype(float)
    d["year"] = d["year"].astype(int)
    return d.set_index("year")


def load_tide(org=False):
    d = pd.read_csv(RAW / ("13tideorg.csv" if org else "13tide.csv"))
    d = d.rename(columns={"Aburatsu": "Aburatu"})  # 補正前のファイルだけ綴りが違う
    return d.set_index("Year")


def load_sst(area="all"):
    lines = open(RAW / f"sst_area{area}.txt").read().splitlines()
    head = {}
    for ln in lines[2:7]:
        p = [x.strip() for x in ln.split(",")]
        if p[0] in ("Normal", "Slope", "95%lim"):
            head[p[0]] = p[1:]
    i = [k for k, ln in enumerate(lines) if ln.startswith("Year")][0]
    cols = [x.strip() for x in lines[i].split(",")][1:]
    rows = []
    for ln in lines[i + 1:]:
        p = [x.strip() for x in ln.split(",")]
        if len(p) < 2 or not p[0].isdigit():
            continue
        rows.append([int(p[0])] + [np.nan if v in ("NoData", "") else float(v) for v in p[1:]])
    d = pd.DataFrame(rows, columns=["year"] + cols).set_index("year")
    meta = pd.DataFrame(head, index=cols).T if head else None
    return d, meta


def load_global():
    rows = []
    for ln in open(RAW / "sst_global.txt"):
        p = ln.split()
        if len(p) == 2 and p[0].isdigit():
            rows.append((int(p[0]), float(p[1])))
    return pd.DataFrame(rows, columns=["year", "anom"]).set_index("year")["anom"]


def trend(s, y0=None, y1=None, level=0.90, lags=None):
    """OLS の傾き（1年あたり）と、Newey-West（HAC）で求めた信頼区間。"""
    s = s.dropna()
    if y0: s = s[s.index >= y0]
    if y1: s = s[s.index <= y1]
    X = sm.add_constant(np.asarray(s.index, float))
    n = len(s)
    L = lags if lags is not None else int(np.floor(4 * (n / 100) ** (2 / 9)))
    ols = sm.OLS(s.values, X).fit()
    hac = sm.OLS(s.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": L})
    from scipy import stats
    z = stats.t.ppf(0.5 + level / 2, n - 2)
    b, se_o, se_h = ols.params[1], ols.bse[1], hac.bse[1]
    r = np.corrcoef(ols.resid[:-1], ols.resid[1:])[0, 1]
    neff = n * (1 - r) / (1 + r) if r > 0 else n
    se_ar = se_o * np.sqrt((n - 2) / max(neff - 2, 1)) if r > 0 else se_o
    return dict(start=int(s.index.min()), end=int(s.index.max()), n=n, slope=b, se_ols=se_o, se_hac=se_h,
                lo_ols=b - z * se_o, hi_ols=b + z * se_o, lo_hac=b - z * se_h, hi_hac=b + z * se_h,
                ar1=r, lo_ar1=b - z * se_ar, hi_ar1=b + z * se_ar, level=level)


def save(fig, name):
    fig.savefig(FIG / name); plt.close(fig)
