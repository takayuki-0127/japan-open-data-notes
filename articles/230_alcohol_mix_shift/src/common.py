"""共通の設定（パス・フォント・データの読み込み）"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
for p in (DATA, RES, FIG):
    p.mkdir(exist_ok=True)

AGES = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]


def setup_font():
    for f in font_manager.findSystemFonts():
        if "NotoSansCJK" in f or "Noto Sans CJK" in f:
            font_manager.fontManager.addfont(f)
    plt.rcParams["font.family"] = "Noto Sans CJK JP"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 110
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False


def annual():
    """品目×年の1世帯当たり年間支出金額（円）。2015〜2024年は年の表、2025年は月の表の12か月の合計"""
    a = pd.read_csv(DATA / "kakei_annual.csv")
    # 2025年改定で「発泡酒・ビール風アルコール飲料」が「発泡酒」に名前が変わった
    a["item"] = a["item"].replace({"発泡酒": "発泡酒・ビール風アルコール飲料"})
    return a.pivot_table(index="year", columns="item", values="value")


def monthly():
    m = pd.read_csv(DATA / "kakei_monthly.csv")
    m["item"] = m["item"].replace({"発泡酒": "発泡酒・ビール風アルコール飲料"})
    return m


def detail():
    """年報の詳細結果表（第4-6表 世帯主の年齢階級別、第4-1表 都市別）の長い形"""
    return pd.read_csv(DATA / "kakei_detail.csv")


def cpi():
    c = pd.read_csv(DATA / "cpi_annual.csv").set_index("year")
    c.columns = [x.split("|")[0] for x in c.columns]
    return c
