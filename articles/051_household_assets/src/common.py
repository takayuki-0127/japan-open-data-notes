"""共通：日本銀行「資金循環統計」（家計の金融資産、ストックとフロー）を読む"""
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
SOURCE = "出典：日本銀行「資金循環統計」（時系列統計データ検索サイト）をもとに作成者が加工して作成"
API_CREDIT = "このサービスは、日本銀行時系列統計データ検索サイトの API 機能を使用しています。サービスの内容は日本銀行によって保証されたものではありません。"
ITEMS = {"A100": "現金・預金", "A110": "現金", "A140": "流動性預金", "A150": "定期性預金", "A170": "外貨預金", "A300": "債務証券", "A311": "国債・財投債",
         "A330": "株式等", "A331": "上場株式", "A332": "非上場株式", "A318": "投資信託", "A400": "保険・年金・定型保証", "A900": "金融資産合計"}


def load():
    """四半期のストック（期末残高）とフロー（期中の取引）を横持ちで返す。単位は兆円。
    調整（≒時価の変動など）＝ 残高の前期差 − フロー"""
    d = pd.read_csv(RAW / "boj_fof_household.csv", dtype={"date": str})
    d["kind"] = d.series_code.str[4:8].map({"FFAS": "stock", "FFAF": "flow"})
    d["item"] = d.series_code.str[-4:]
    d = d[d.item.isin(ITEMS)]
    d["q"] = pd.PeriodIndex([f"{x[:4]}Q{int(x[4:])}" for x in d.date], freq="Q")
    w = d.pivot_table(index="q", columns=["kind", "item"], values="value") / 1e4
    st, fl = w["stock"], w["flow"]
    adj = st.diff() - fl
    return st, fl, adj
