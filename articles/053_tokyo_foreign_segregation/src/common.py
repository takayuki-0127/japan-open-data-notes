"""共通：東京都総務局「東京都の外国人人口」（東京都オープンデータカタログ、CC BY 4.0）を読む"""
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
SOURCE = "出典：東京都総務局「東京都の外国人人口」（東京都オープンデータカタログ、CC BY 4.0）をもとに作成者が加工して作成"
ERA = {"昭和": 1925, "平成": 1988, "令和": 2018}
# 年をまたいで同じ範囲になるようにまとめた国籍・地域
MERGE = {"中国（平成28年まで）": "中国・台湾", "中国（平成29年から）": "中国・台湾", "台湾（平成29年から）": "中国・台湾",
         "韓国・朝鮮（平成28年まで）": "韓国・朝鮮", "韓国（平成29年から）": "韓国・朝鮮", "朝鮮（平成29年から）": "韓国・朝鮮",
         "東ドイツ": "ドイツ", "西ドイツ": "ドイツ"}


def year_of(c):
    m = re.match(r"(昭和|平成|令和)(\d+)年", c)
    return ERA[m.group(1)] + int(m.group(2)) if m else None


def load(level="4"):
    """時系列表（各年1月1日現在、1979〜2026年）を long 形式で返す。level 4 = 区市町村、0 = 東京都総数"""
    d = pd.read_csv(RAW / "ga000v0001.csv", dtype=str)
    d = d[d["地域階層"] == level]
    ycols = [c for c in d.columns if year_of(c)]
    x = d.melt(id_vars=["国・地域", "地域コード", "国・地域(人)"], value_vars=ycols, var_name="y", value_name="n")
    x["year"] = x.y.map(year_of); x["n"] = pd.to_numeric(x.n.str.replace(",", ""), errors="coerce")
    x["nat"] = x["国・地域"].replace(MERGE); x = x.rename(columns={"国・地域(人)": "area", "地域コード": "code"})
    x = x.groupby(["nat", "code", "area", "year"], as_index=False).n.sum(min_count=1)
    return x


CONT = ["アジア", "ヨーロッパ", "アフリカ", "北米", "南米", "オセアニア"]


def detail2026():
    """第3表（2026年1月1日）：区市町村×国籍・地域（全国籍）。大陸の小計列は除く"""
    d = pd.read_csv(RAW / "ga26ev0300.csv", dtype=str)
    d = d[d["地域階層"] == "4"].set_index("国・地域(人)")
    cols = [c for c in d.columns[6:] if c not in CONT]
    return d[cols].apply(lambda s: pd.to_numeric(s.str.strip().replace("", "0"), errors="coerce")).fillna(0)


def dissimilarity(m):
    """非類似度指数：各グループの区市町村分布と、それ以外の外国人の分布の差（0〜1）。m は 区市町村×グループ"""
    tot = m.sum(axis=1)
    out = {}
    for g in m.columns:
        a = m[g]; b = tot - a
        if a.sum() == 0: continue
        out[g] = 0.5 * (a / a.sum() - b / b.sum()).abs().sum()
    return pd.Series(out)
