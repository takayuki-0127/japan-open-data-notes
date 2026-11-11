"""共通の設定（パス・フォント）"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RES = ROOT / "results"
FIG = ROOT / "figures"
for p in (RES, FIG):
    p.mkdir(exist_ok=True)


def setup_font():
    for f in font_manager.findSystemFonts():
        if "NotoSansCJK" in f or "Noto Sans CJK" in f:
            font_manager.fontManager.addfont(f)
    plt.rcParams["font.family"] = "Noto Sans CJK JP"
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 110
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["svg.hashsalt"] = "fixed"


import pandas as pd


def to_period(ym):
    s = str(int(ym))
    return pd.Period(f"{s[:4]}-{s[4:6]}", "M")


def splice(old, new, cut=202301):
    """接続指数（〜2022年）と2020年基準の指数（2018年〜）をつなぐ。2023年1月から後は2020年基準を使う"""
    old = old.dropna()
    keep_new = (new.index >= cut) | (~new.index.isin(old.index))   # 接続指数がない月は2020年基準で埋める
    s = pd.concat([old[old.index < cut], new[keep_new]]).dropna()
    s = s[~s.index.duplicated(keep="first")]
    s.index = pd.PeriodIndex([to_period(i) for i in s.index])
    return s.sort_index()
