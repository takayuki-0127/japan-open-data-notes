"""F01 共通：パス・図の体裁・回帰（県と年の固定効果、県クラスター標準誤差、wild cluster bootstrap）"""
from pathlib import Path
import logging, warnings
import numpy as np, pandas as pd
import statsmodels.api as sm
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
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
FIG, RES = ROOT / "figures", ROOT / "results"
FIG.mkdir(exist_ok=True); RES.mkdir(exist_ok=True)
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a"
SOURCE = ("出典：総務省「労働力調査（都道府県別モデル推計値）」、厚生労働省「地域別最低賃金の全国一覧」「賃金構造基本統計調査（2015年）」"
          "「職業安定業務統計」（いずれも e-Stat ほか）をもとに作成者が加工して作成")
PREFS = ["北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
         "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫",
         "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎",
         "熊本", "大分", "宮崎", "鹿児島", "沖縄"]


def panel():
    return pd.read_csv(DATA / "panel.csv")


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7, color=GRAY, ha="left", va="top", wrap=True)
    fig.savefig(FIG / name)
    plt.close(fig)


def design(df, regs, trends=False):
    """説明変数 + 県ダミー + 年ダミー（+ 県別線形トレンド）"""
    X = df[regs].astype(float).copy()
    X = X.join(pd.get_dummies(df["pref"], prefix="p", drop_first=True, dtype=float))
    X = X.join(pd.get_dummies(df["year"], prefix="y", drop_first=True, dtype=float))
    if trends:
        t = df["year"] - df["year"].mean()
        for p in df["pref"].unique()[1:]:
            X["tr_" + p] = (df["pref"] == p) * t
    return sm.add_constant(X)


def fe_ols(df, y, regs, trends=False):
    d = df.dropna(subset=[y] + regs).reset_index(drop=True)
    X = design(d, regs, trends)
    m = sm.OLS(d[y].astype(float), X).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d["pref"])[0]})
    return m, d, X


def wild_cluster_p(df, y, reg, regs, trends=False, B=999, seed=1):
    """帰無仮説（係数=0）を課した wild cluster bootstrap（Rademacher）の p 値"""
    rng = np.random.default_rng(seed)
    m, d, X = fe_ols(df, y, regs, trends)
    t0 = m.tvalues[reg]
    Xr = X.drop(columns=[reg])
    mr = sm.OLS(d[y].astype(float), Xr).fit()
    fit, u = mr.fittedvalues.values, mr.resid.values
    g = pd.factorize(d["pref"])[0]; G = g.max() + 1
    cnt = 0
    for _ in range(B):
        w = rng.choice([-1.0, 1.0], G)[g]
        yb = fit + w * u
        mb = sm.OLS(yb, X).fit(cov_type="cluster", cov_kwds={"groups": g})
        cnt += abs(mb.tvalues[reg]) >= abs(t0)
    return (cnt + 1) / (B + 1)
