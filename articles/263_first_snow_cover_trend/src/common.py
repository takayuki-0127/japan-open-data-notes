"""262〜266 共通：気象庁「過去の気象データ検索」日ごとの値（daily_s1, view=p1）14地点 1931〜2025年"""
from pathlib import Path
import re
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"; RES = ROOT / "results"; FIG = ROOT / "figures"
for p in (RES, FIG): p.mkdir(parents=True, exist_ok=True)
# 名前, 府県番号, 地点番号。網走〜宮崎の13地点は気象庁が「都市化の影響が比較的少ない」とする15地点から
# 亜熱帯の名瀬・石垣島を除いたもの。東京は大都市の比較用
STATIONS = [("網走",17,47409),("根室",18,47420),("寿都",16,47421),("山形",35,47588),("石巻",34,47592),
            ("伏木",55,47606),("飯田",48,47637),("銚子",45,47648),("境",69,47742),("浜田",68,47755),
            ("彦根",60,47761),("多度津",72,47890),("宮崎",87,47830),("東京",44,47662)]
NAMES = [s[0] for s in STATIONS]; RURAL = NAMES[:-1]
COLS = ["station","year","month","day","prec","tmean","tmax","tmin","snowfall","snowdepth","wx_day","wx_night"]

def num(s):
    """値の印：')' 準正常値→使う、']' 資料不足値・'×' 欠測・'#' 疑問・'///' 観測なし→欠測、'--' 現象なし→0"""
    if s is None or (isinstance(s, float) and np.isnan(s)): return np.nan
    s = str(s).strip()
    if s == "": return np.nan
    if s == "--": return 0.0
    if any(c in s for c in "]×#/"): return np.nan
    s = s.replace(")", "").strip()
    try: return float(s)
    except ValueError: return np.nan

def load():
    df = pd.read_csv(DATA / "jma_daily_14st_1931_2025.tsv.gz", sep="\t", names=COLS, dtype=str, keep_default_na=False)
    for c in ["year","month","day"]: df[c] = df[c].astype(int)
    for c in ["prec","tmean","tmax","tmin","snowfall","snowdepth"]:
        df[c + "_raw"] = df[c]; df[c] = df[c].map(num)
    df["date"] = pd.to_datetime(dict(year=df.year, month=df.month, day=df.day))
    return df

def ols_trend(x, y):
    """傾きと HC1 標準誤差"""
    import statsmodels.api as sm
    m = ~(np.isnan(x) | np.isnan(y))
    if m.sum() < 10: return np.nan, np.nan, int(m.sum())
    X = sm.add_constant(np.asarray(x)[m]); f = sm.OLS(np.asarray(y)[m], X).fit(cov_type="HC1")
    return f.params[1], f.bse[1], int(m.sum())

def theil_sen(x, y):
    from scipy.stats import theilslopes
    m = ~(np.isnan(x) | np.isnan(y))
    if m.sum() < 10: return np.nan
    return theilslopes(np.asarray(y)[m], np.asarray(x)[m])[0]

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "Noto Sans CJK JP"; plt.rcParams["figure.dpi"] = 110

def doy_from(dates, start_month):
    """start_month の1日を1日目とした通し日（寒候年は8月1日起点など）"""
    y = dates.dt.year - (dates.dt.month < start_month).astype(int)
    base = pd.to_datetime(dict(year=y, month=start_month, day=1))
    return (dates - base).dt.days + 1, y

def md_label(doy, start_month, ref_year=2001):
    """通し日を「11月3日」の形に（ref_year は閏年でない年）"""
    d = pd.Timestamp(year=ref_year, month=start_month, day=1) + pd.Timedelta(days=float(doy) - 1)
    return f"{d.month}月{d.day}日"

def complete_years(df, col, min_days=360, key="year"):
    c = df.groupby(["station", key])[col].apply(lambda s: s.notna().sum())
    return c[c >= min_days].index

PERIODS = [(1931, 1960), (1961, 1990), (1996, 2025)]
