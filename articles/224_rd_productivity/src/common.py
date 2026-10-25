"""共通：経済産業省企業活動基本調査（2025年確報、2020〜2024年度実績）の産業別集計を読む"""
from pathlib import Path
import logging, warnings
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
DATA = ROOT / "data"; FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：経済産業省「経済産業省企業活動基本調査」をもとに作成者が加工して作成"
SECTION = {"C": "鉱業", "E": "製造業", "F": "電気・ガス業", "G": "情報通信業", "I1": "卸売業", "I2": "小売業", "J1": "クレジットカード業等",
           "K1": "物品賃貸業", "L": "学術研究・専門技術サービス業", "M": "飲食サービス業", "N": "生活関連・娯楽業", "O": "個人教授所",
           "R1": "サービス業（その他）"}


def _num(s):
    return pd.to_numeric(s.replace({"X": None, "-": None, "…": None}), errors="coerce")


def load():
    """産業（3桁の細分類、親を除く）× 年度のパネル。生産性＝付加価値額÷従業者数（万円/人）"""
    t1 = pd.read_csv(DATA / "t1_raw.csv", dtype=str)
    t10 = pd.read_csv(DATA / "t10_raw.csv", dtype=str)
    t1["year"] = t1.year.astype(int); t10["year"] = t10.year.astype(int)
    # 大分類を表の並び順で割り当てる
    order = t1.drop_duplicates("code")[["code", "name"]].reset_index(drop=True)
    sec, cur = {}, None
    for c in order.code:
        if c in SECTION: cur = c
        sec[c] = cur
    codes = [c for c in order.code if c.isdigit() and c != "000"]
    leaf = [c for c in codes if not (c.endswith("0") and any(o != c and o[:2] == c[:2] for o in codes))]
    d = t1[t1.code.isin(leaf)].merge(t10[["code", "year", "rd_firms", "rd_sales", "rd_total"]], on=["code", "year"], how="left")
    for k in ["firms", "employees", "sales", "value_added", "ordinary_profit", "rd_firms", "rd_sales", "rd_total"]:
        d[k] = _num(d[k])
    d["section"] = d.code.map(sec).map(SECTION)
    d["mfg"] = (d.section == "製造業").astype(int)
    d["rd_firms"] = d.rd_firms.fillna(0); d["rd_total"] = d.rd_total.fillna(0)
    d["prod"] = d.value_added / d.employees * 100          # 万円/人
    d["rd_int"] = d.rd_total / d.sales * 100               # 研究開発費÷売上高（%、産業の全企業の売上高）
    d["rd_share"] = d.rd_firms / d.firms * 100             # 研究開発をした企業の割合（%）
    d["size"] = d.employees / d.firms                      # 1社あたり従業者数
    return d


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7.5, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)
