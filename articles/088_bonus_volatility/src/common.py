"""共通：厚生労働省「毎月勤労統計調査」全国調査の実数・指数累積データ（e-Stat）を読む"""
from pathlib import Path
import logging, warnings, zipfile
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
SOURCE = "出典：厚生労働省「毎月勤労統計調査」全国調査 実数・指数累積データ（e-Stat）を加工して作成"
# 産業分類（大分類）の記号
IND = {"TL": "調査産業計", "C": "鉱業", "D": "建設業", "E": "製造業", "F": "電気・ガス", "G": "情報通信業",
       "H": "運輸業，郵便業", "I": "卸売業，小売業", "J": "金融業，保険業", "K": "不動産・物品賃貸業",
       "L": "学術研究・専門技術", "M": "宿泊業，飲食サービス業", "N": "生活関連・娯楽業", "O": "教育，学習支援業",
       "P": "医療，福祉", "Q": "複合サービス事業", "R": "その他のサービス業"}
SIZE = {"T": "5人以上", "0": "30人以上"}
FORM = {"0": "就業形態計", "1": "一般労働者", "2": "パートタイム労働者"}
SUBSET = ROOT / "data" / "maikin_subset.csv"
ZIP = ROOT / "data" / "maikin_subset.zip"
if not SUBSET.exists() and ZIP.exists():
    zipfile.ZipFile(ZIP).extractall(ROOT / "data")


def _read_raw(name):
    d = pd.read_csv(RAW / name, encoding="cp932", dtype=str)
    d.columns = [c.strip() for c in d.columns]
    for c in ["種別", "年", "月", "産業分類", "規模", "就業形態"]:
        d[c] = d[c].str.strip()
    return d


def load(cache=True):
    """元の累積 CSV（実数・指数）から、年平均（CY）は産業計と16大産業、月次は産業計だけを、
    規模5人以上・30人以上で取り出した1表（横長、元の列のまま）。種別：実数／指数／伸び率"""
    if cache and SUBSET.exists():
        return pd.read_csv(SUBSET, dtype={"月": str, "規模": str, "就業形態": str})
    out = []
    for f in ["maikin_jissu.csv", "maikin_shisu.csv"]:
        d = _read_raw(f)
        d = d[d["産業分類"].isin(IND) & d["規模"].isin(SIZE) & ((d["月"] == "CY") | (d["産業分類"] == "TL"))]
        d["種別"] = d["種別"].replace({"伸び率、日数差、ポイント差": "伸び率"})
        out.append(d)
    x = pd.concat(out, ignore_index=True)
    for c in x.columns[6:]:
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x["年"] = x["年"].astype(int)
    x.to_csv(SUBSET, index=False, encoding="utf-8")
    return x


def load_bonus():
    p = ROOT / "data" / "bonus_national.csv"
    if p.exists():
        return pd.read_csv(p, dtype={"月": str, "規模": str})
    d = _read_raw("maikin_shoyo.csv")
    d = d.drop(columns=["種別", "就業形態", "産業分類"])
    for c in d.columns[3:]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d.to_csv(p, index=False, encoding="utf-8")
    return d


def series(x, kind, item, ind="TL", size="T", form="0", month="CY"):
    s = x[(x["種別"] == kind) & (x["産業分類"] == ind) & (x["規模"] == size)
          & (x["就業形態"] == form) & (x["月"] == month)]
    return s.set_index("年")[item].sort_index()


def note(ax, text=SOURCE, y=-0.16):
    ax.text(0, y, text, transform=ax.transAxes, fontsize=7.5, color=GRAY, va="top")
