"""共通の設定（パス・フォント・対象の国・季節の形の作り方）"""
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RES = ROOT / "results"
FIG = ROOT / "figures"
SEED = 68

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "Noto Sans CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 110

# 2003年からそろっている個別の国・地域（「計」「その他」「総数」、2019年以降に分けられた地域は除く）
MARKETS = [
    "韓国", "中国", "台湾", "香港", "タイ", "シンガポール", "マレーシア", "インドネシア",
    "フィリピン", "ベトナム", "インド", "イスラエル", "トルコ",
    "英国", "フランス", "ドイツ", "イタリア", "スペイン", "ロシア", "スウェーデン", "デンマーク",
    "ノルウェー", "フィンランド", "オランダ", "スイス", "ベルギー", "ポーランド", "オーストリア",
    "ポルトガル", "アイルランド",
    "米国", "カナダ", "メキシコ", "ブラジル", "豪州", "ニュージーランド",
]
REGION = {
    **{m: "東アジア" for m in ["韓国", "中国", "台湾", "香港"]},
    **{m: "東南・南アジア" for m in ["タイ", "シンガポール", "マレーシア", "インドネシア", "フィリピン", "ベトナム", "インド"]},
    **{m: "中東" for m in ["イスラエル", "トルコ"]},
    **{m: "欧州" for m in ["英国", "フランス", "ドイツ", "イタリア", "スペイン", "ロシア", "スウェーデン", "デンマーク",
                          "ノルウェー", "フィンランド", "オランダ", "スイス", "ベルギー", "ポーランド", "オーストリア",
                          "ポルトガル", "アイルランド"]},
    **{m: "北米・中南米" for m in ["米国", "カナダ", "メキシコ", "ブラジル"]},
    **{m: "オセアニア" for m in ["豪州", "ニュージーランド"]},
}
MONTHS = [f"{m}月" for m in range(1, 13)]
BASE_YEARS = [2015, 2016, 2017, 2018, 2019]   # 本体：コロナ前の5年
POST_YEARS = [2023, 2024, 2025]               # コロナ後
DAYS = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])


def load_long():
    d = pd.read_csv(RAW / "jnto_monthly_2003_2026.csv")
    return d[["year", "market", "month", "visitors"]]


def panel(d, markets=MARKETS):
    """market × (year, month) の人数の表"""
    p = d[d.market.isin(markets)].pivot_table(index="market", columns=["year", "month"], values="visitors", aggfunc="sum")
    return p.reindex(markets)


def profile(p, years, per_day=False):
    """各年の月の割合×12 を年で平均した「季節の形」（平均が1）"""
    out = []
    for y in years:
        m = p[y].astype(float).values           # market × 12
        if per_day:
            m = m / DAYS
        out.append(m / m.sum(axis=1, keepdims=True) * 12)
    prof = np.mean(out, axis=0)
    return pd.DataFrame(prof, index=p.index, columns=MONTHS)
