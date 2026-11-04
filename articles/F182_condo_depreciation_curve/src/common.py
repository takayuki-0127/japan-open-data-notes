"""共通：不動産情報ライブラリ（国土交通省）の不動産取引価格情報（中古マンション等・全国）を読み、分析用に整える"""
from pathlib import Path
import logging, warnings, zipfile, io
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
DATA, RAW, FIG, RES = ROOT / "data", ROOT / "data" / "raw", ROOT / "figures", ROOT / "results"
for p in (RAW, FIG, RES):
    p.mkdir(parents=True, exist_ok=True)          # 空のフォルダは git に残らないので、ここで作る
BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, PURPLE = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b", "#a9c9ef", "#3aa07a", "#7a5bd6"
SOURCE = "出典：国土交通省 不動産情報ライブラリ「不動産取引価格情報」（中古マンション等、全国、2015年第1四半期〜2025年第4四半期）をもとに作成者が加工して作成"
RAW_ZIP = "All_20151_20254.zip"
CLEAN = DATA / "condo_clean.csv.gz"
REGION = {}
for p in ["東京都", "神奈川県", "埼玉県", "千葉県"]: REGION[p] = "東京圏"
for p in ["大阪府", "京都府", "兵庫県", "奈良県"]: REGION[p] = "大阪圏"
for p in ["愛知県", "岐阜県", "三重県"]: REGION[p] = "名古屋圏"
for p in ["北海道", "宮城県", "広島県", "福岡県"]: REGION[p] = "地方の中心4道県"
REG_ORDER = ["東京圏", "大阪圏", "名古屋圏", "地方の中心4道県", "その他"]
MAXAGE = 50


def walk_min(s):
    s = str(s)
    if s.isdigit(): return float(s)
    return {"30分～60分": 45.0}.get(s, np.nan)          # 1時間以上は除く


def load_clean():
    d = pd.read_csv(CLEAN, dtype={"muni": str})
    d["lppm2"] = np.log(d.ppm2); d["larea"] = np.log(d.area)
    d["region"] = d.pref.map(REGION).fillna("その他")
    d["cell"] = d.muni + "_" + d.yq
    return d


def within(d, cols, key="cell"):
    """市区町村×四半期の平均を引く（固定効果を吸収する）"""
    g = d.groupby(key)
    return d[cols].astype("float64") - g[cols].transform("mean")


def age_curve(d, ages=range(0, MAXAGE + 1), ref=1, controls=True, key="cell"):
    """log㎡単価を、築年数の1年ごとのダミー＋物件の特徴＋市区町村×四半期の固定効果で回帰。築ref年との差（log）を返す"""
    d = d[d.age.between(min(ages), max(ages))].copy()
    A = pd.get_dummies(d.age.astype(int), prefix="a").astype(float)
    A = A.drop(columns=[f"a_{ref}"])
    X = A.copy()
    if controls:
        X["larea"] = d.larea
        for lo, hi in [(6, 10), (11, 15), (16, 20), (21, 30), (31, 99)]:
            X[f"w{lo}"] = d.walk.between(lo, hi).astype(float)
        X["src"] = (d.struct == "SRC").astype(float)
        X["oth"] = (d.struct == "その他").astype(float)
        X["renov"] = d.renov.astype(float)
    cols = list(X.columns)
    X[key] = d[key].values; X["y"] = d.lppm2.values
    W = within(X, cols + ["y"], key)
    keep = X.groupby(key)[key].transform("size") > 1
    W = W[keep.values]
    Xm, y = W[cols].values, W["y"].values
    beta, *_ = np.linalg.lstsq(Xm, y, rcond=None)
    # 市区町村でクラスタした標準誤差（築年数の係数だけ）
    e = y - Xm @ beta
    XtXi = np.linalg.pinv(Xm.T @ Xm)
    cl = d.loc[keep.values, "muni"].values
    S = pd.DataFrame(Xm * e[:, None]).groupby(cl).sum().values
    V = XtXi @ (S.T @ S) @ XtXi
    G = len(np.unique(cl)); n, k = Xm.shape
    V *= G / (G - 1)
    se = np.sqrt(np.diag(V))
    out = []
    for a in ages:
        if a == ref: out.append((a, 0.0, 0.0)); continue
        c = f"a_{a}"
        if c in cols:
            i = cols.index(c); out.append((a, beta[i], se[i]))
    r = pd.DataFrame(out, columns=["age", "b", "se"])
    r["rel"] = np.exp(r.b); r["lo"] = np.exp(r.b - 1.96 * r.se); r["hi"] = np.exp(r.b + 1.96 * r.se)
    r.attrs["n"] = int(keep.sum())
    r.attrs["coef"] = dict(zip(cols, beta))
    return r


def half_age(r, level=0.5):
    """相対価格が level を下回る最初の築年数（線形補間）"""
    r = r.sort_values("age"); r = r[r.age >= 1]
    v, a = r.rel.values, r.age.values
    for i in range(1, len(v)):
        if v[i] <= level < v[i - 1]:
            return a[i - 1] + (v[i - 1] - level) / (v[i - 1] - v[i])
    return np.nan


def summarize(r, label):
    g = r.set_index("age").rel
    def pct(a): return (g.get(a, np.nan) - 1) * 100
    slope = lambda a0, a1: (np.log(g[a1]) - np.log(g[a0])) / (a1 - a0) * 100 if (a0 in g.index and a1 in g.index) else np.nan
    return {"spec": label, "n": r.attrs.get("n"), "築0年": pct(0), "築10年": pct(10), "築20年": pct(20), "築30年": pct(30), "築40年": pct(40),
            "築0→3年の下がり": (g.get(3, np.nan) / g.get(0, np.nan) - 1) * 100,
            "築3〜20年の年率": slope(3, 20),
            "築0→3年は築3〜20年の何年分": (np.log(g.get(0, np.nan)) - np.log(g.get(3, np.nan))) / (-slope(3, 20) / 100) if 3 in g.index else np.nan,
            "半値の築年数": half_age(r), "年率1-10": slope(1, 10), "年率10-20": slope(10, 20), "年率20-30": slope(20, 30), "年率30-45": slope(30, 45)}
