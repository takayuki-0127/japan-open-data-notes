"""共通：総務省消防庁「熱中症による救急搬送人員」と環境省「暑さ指数（WBGT）」の過去データを読む"""
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
SOURCE = "出典：総務省消防庁「熱中症情報 過去のデータ一覧」、環境省「熱中症予防情報サイト 暑さ指数（WBGT）過去データ」をもとに作成者が加工して作成"
CITY = {"東京": 13, "大阪": 27, "名古屋": 23, "福岡": 40, "札幌": 1, "仙台": 4}
PREF = {13: "東京都", 27: "大阪府", 23: "愛知県", 40: "福岡県", 1: "北海道", 4: "宮城県"}


def fdma():
    """消防庁：日別・都道府県別の熱中症による救急搬送人員（5〜9月、2016〜2025年。2020年5月は調査なし）"""
    out = []
    for f in sorted(glob.glob(str(RAW / "heatstroke003_data_*.xlsx"))):
        x = pd.ExcelFile(f)
        for sh in x.sheet_names:
            d = x.parse(sh); d.columns = [str(c).strip() for c in d.columns]
            out.append(d)
    d = pd.concat(out, ignore_index=True)
    d["日付"] = pd.to_datetime(d["日付"]); d["pref"] = pd.to_numeric(d["都道府県コード"], errors="coerce").astype(int)
    d = d.rename(columns={"日付": "date", "搬送人員（計）": "n", "年齢区分：高齢者": "elderly", "傷病程度：死亡": "dead", "傷病程度：重症": "severe",
                          "発生場所：住居": "home"})
    return d


def wbgt():
    w = pd.read_csv(RAW / "wbgt_daily_6cities.csv"); w["date"] = pd.to_datetime(w.date); w["pref"] = w.city.map(CITY)
    return w


def population():
    d = pd.read_csv(RAW / "SSDSE-E-2026.csv", encoding="cp932", header=None, skiprows=3)
    d = d[d[0].astype(str).str.match(r"R\d{5}") & (d[0] != "R00000")]
    return pd.Series(d[2].astype(float).values, index=range(1, 48), name="pop")


def panel():
    """6都市：WBGT（日最高）と、その都道府県の搬送人員。前日・前々日の WBGT、季節の経過も付ける"""
    f = fdma(); w = wbgt(); pop = population()
    m = w.merge(f[["date", "pref", "n", "elderly", "dead", "severe", "home"]], on=["date", "pref"], how="inner").sort_values(["city", "date"])
    g = m.groupby(["city", m.date.dt.year])
    m["wbgt_l1"] = g.wbgt_max.shift(1); m["wbgt_l2"] = g.wbgt_max.shift(2)
    m["year"] = m.date.dt.year; m["month"] = m.date.dt.month; m["dow"] = m.date.dt.dayofweek
    m["doy"] = m.date.dt.dayofyear
    m["hot_days_sofar"] = g.wbgt_max.transform(lambda s: (s.shift(1) >= 28).cumsum())  # その年の前日までに WBGT28以上だった日数
    m["pop"] = m.pref.map(pop); m["rate"] = m.n / m["pop"] * 1e6
    return m.dropna(subset=["wbgt_l1", "wbgt_l2"])
