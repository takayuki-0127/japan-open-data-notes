"""共通：国土交通省「不動産情報ライブラリ」不動産価格（取引価格・成約価格）情報 全国CSVを読む"""
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
SOURCE = "出典：国土交通省「不動産情報ライブラリ」（https://www.reinfolib.mlit.go.jp/）の不動産価格（取引価格・成約価格）情報をもとに作成者が加工して作成"
REGIONS = ["東京圏", "大阪圏", "名古屋圏", "地方4市", "その他"]
RCOL = {"東京圏": BLUE, "大阪圏": ORANGE, "名古屋圏": GREEN, "地方4市": PURPLE, "その他": GRAY}


def region(pref, city):
    if pref in ("埼玉県", "千葉県", "東京都", "神奈川県"): return "東京圏"
    if pref in ("京都府", "大阪府", "兵庫県", "奈良県"): return "大阪圏"
    if pref in ("愛知県", "岐阜県", "三重県"): return "名古屋圏"
    if str(city).startswith(("札幌市", "仙台市", "広島市", "福岡市")): return "地方4市"
    return "その他"


def walk(v):
    """最寄駅：距離（分）。区間表記は中央値に置き換える"""
    m = {"30分～60分": 45, "1H～1H30": 75, "1H30～2H": 105, "2H～": 120}
    if pd.isna(v): return np.nan
    if v in m: return m[v]
    try: return float(v)
    except ValueError: return np.nan


def num(v):
    return pd.to_numeric(pd.Series(v).astype(str).str.replace(",", "").str.replace("㎡以上", "").str.replace("m^2以上", ""), errors="coerce").values


def load(cache=True):
    p = ROOT / "data" / "work.pkl"
    if cache and p.exists(): return pd.read_pickle(p)
    fs = sorted(glob.glob(str(RAW / "*_20211_20254.csv")))
    use = ["種類", "価格情報区分", "市区町村コード", "都道府県名", "市区町村名", "最寄駅：距離（分）", "取引価格（総額）", "間取り",
           "面積（㎡）", "延床面積（㎡）", "建築年", "建物の構造", "取引時期", "改装", "取引の事情等", "今後の利用目的", "用途"]
    d = pd.concat([pd.read_csv(f, encoding="cp932", dtype=str, usecols=use) for f in fs], ignore_index=True)
    d = d[d["種類"].isin(["中古マンション等", "宅地(土地と建物)"])].copy()
    q = d["取引時期"].str.extract(r"(\d{4})年第(\d)四半期").astype(int)
    x = pd.DataFrame({
        "kind": d["種類"].map({"中古マンション等": "マンション", "宅地(土地と建物)": "戸建て"}),
        "src": d["価格情報区分"].map({"不動産取引価格情報": "取引", "成約価格情報": "成約"}),
        "muni": d["市区町村コード"].astype(str), "pref": d["都道府県名"], "city": d["市区町村名"],
        "year": q[0].values, "qtr": q[1].values,
        "price": num(d["取引価格（総額）"]), "area": num(d["面積（㎡）"]), "floor": num(d["延床面積（㎡）"]),
        "walk": d["最寄駅：距離（分）"].map(walk),
        "built": pd.to_numeric(d["建築年"].str.replace("年", ""), errors="coerce").values,
        "struct": d["建物の構造"].fillna("不明").str.split("、").str[0],
        "layout": d["間取り"].fillna("不明"),
        "renov": d["改装"].fillna("不明"),
        "special": d["取引の事情等"].notna().astype(int).values,
    })
    x["t"] = (x["year"] - 2021) * 4 + x["qtr"] - 1
    x["tlab"] = x["year"].astype(str) + "Q" + x["qtr"].astype(str)
    x["age"] = (x["year"] - x["built"]).clip(lower=0)
    x["region"] = [region(p_, c_) for p_, c_ in zip(x["pref"], x["city"])]
    x.to_pickle(p)
    return x


def demean(df, cols, g):
    """市区町村固定効果を除く（グループ内平均を引く）"""
    return df[cols] - df.groupby(g)[cols].transform("mean")


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
