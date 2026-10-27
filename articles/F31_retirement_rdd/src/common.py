"""F31 共通：パス・図の体裁・回帰不連続（年齢）の推定関数"""
from pathlib import Path
import logging, warnings
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
import statsmodels.api as sm
warnings.filterwarnings("ignore")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSans-CJK" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "sans-serif"],
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
                     "figure.dpi": 150, "savefig.bbox": "tight"})
ROOT = Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, RED = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#c43c39"
SOURCE = "出典：総務省「国勢調査」（2000〜2020年）をもとに作成者が加工して作成"
YEARS = [2000, 2005, 2010, 2015, 2020]
SEXES = ["総数", "男", "女"]
CUTOFFS = [60, 65]
H = 5          # 基本のバンド幅（境界の左右5歳ずつ）


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)


def rd(df, c, h=H, p=1, y="emp_rate", kernel="tri", weight_pop=False):
    """年齢 a（整数）を走る変数にした局所多項式の回帰不連続。
    a >= c を「境界の右」とし、左右で傾きが違う p 次の多項式を当てはめる。
    戻り値：段差（ポイント）、HC1 標準誤差、95%区間、使った年齢の数。
    年齢は1歳刻みで、境界のすぐ左は c-1 歳・すぐ右は c 歳。"""
    d = df[(df.age >= c - h) & (df.age <= c + h - 1)].copy()
    x = d.age - c
    right = (d.age >= c).astype(float)
    X = {"const": 1.0, "D": right}
    for k in range(1, p + 1):
        X[f"x{k}"] = x ** k
        X[f"Dx{k}"] = right * x ** k
    X = pd.DataFrame(X, index=d.index)
    w = np.ones(len(d))
    if kernel == "tri":
        # 右側の0歳（=c歳）と左側の-1歳（=c-1歳）が同じ重みになるよう、境界を c-0.5 に置いた三角カーネル
        w = np.clip(1 - np.abs(x + 0.5) / h, 0, None)
    if weight_pop:
        w = w * d["pop_known"] / d["pop_known"].mean()
    m = sm.WLS(d[y] * 100, X, weights=w).fit(cov_type="HC1")
    b, se = m.params["D"], m.bse["D"]
    return {"jump": b, "se": se, "lo": b - 1.96 * se, "hi": b + 1.96 * se, "n_ages": len(d), "h": h, "p": p}


def fit_line(df, c, h=H, p=1, y="emp_rate", side="left"):
    """図のための当てはめ線（左右それぞれ）"""
    if side == "left":
        d = df[(df.age >= c - h) & (df.age < c)]
    else:
        d = df[(df.age >= c) & (df.age <= c + h - 1)]
    x = d.age - c
    co = np.polyfit(x, d[y] * 100, p)
    xs = np.linspace(x.min(), x.max(), 30)
    return xs + c, np.polyval(co, xs)
