"""F29 共通：パス・図の体裁・対照県の定義・推定の関数（SCM・SDID・ASCM）"""
from pathlib import Path
import logging, warnings
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
from scipy.optimize import minimize
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
SOURCE = "出典：観光庁「宿泊旅行統計調査」をもとに作成者が加工して作成"
SEED = 20150314
OPEN = pd.Timestamp("2015-03-01")            # 北陸新幹線 長野―金沢 開業 2015-03-14
PRE0, POST1 = pd.Timestamp("2012-01-01"), pd.Timestamp("2019-12-01")   # 基本：2012/1〜2015/2 が事前、2015/3〜2019/12 が事後
TREATED = ["石川", "富山"]
# 対照から外す県
EXCL_LINE = ["新潟", "長野"]                 # 同じ北陸新幹線の駅がある（上越妙高・糸魚川・飯山は2015年開業）
EXCL_HOKKAIDO = ["北海道", "青森"]            # 2016年3月 北海道新幹線
EXCL_KYUSHU = ["福岡", "佐賀", "熊本", "鹿児島"]  # 2011年3月 九州新幹線全線開業
EXCL_NEIGHBOR = ["福井"]                     # 金沢から特急で接続（波及のおそれ）
EXCL_QUAKE = ["岩手", "宮城", "福島"]         # 東日本大震災で事前期間が大きく乱れる
BASE_EXCL = EXCL_LINE + EXCL_HOKKAIDO + EXCL_KYUSHU + EXCL_NEIGHBOR + EXCL_QUAKE


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)


def load_panel(col="japanese"):
    d = pd.read_csv(DATA / "monthly_pref.csv", parse_dates=["date"])
    return d.pivot(index="date", columns="pref", values=col)


def prep(wide, pre0=PRE0, post1=POST1, open_=OPEN):
    """対数をとり、事前期間の同じ月の平均を引いて季節をならす（県ごと）"""
    y = np.log(wide.loc[pre0:post1])
    pre = y.loc[:open_ - pd.offsets.MonthBegin(1)]
    mmean = pre.groupby(pre.index.month).mean()
    return y - mmean.loc[y.index.month].values


def _simplex(obj, n, x0=None):
    x0 = np.full(n, 1 / n) if x0 is None else x0
    r = minimize(obj, x0, method="SLSQP", bounds=[(0, 1)] * n,
                 constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}], options={"maxiter": 500, "ftol": 1e-12})
    w = np.clip(r.x, 0, None); return w / w.sum()


def scm(y, tr, donors, open_=OPEN):
    """古典的な合成コントロール：事前の差の二乗和を最小にする非負・合計1の重み"""
    pre = y.index < open_
    X0, x1 = y.loc[pre, donors].values, y.loc[pre, tr].values
    w = _simplex(lambda w: ((x1 - X0 @ w) ** 2).sum(), len(donors))
    synth = y[donors].values @ w
    gap = y[tr].values - synth
    return dict(w=pd.Series(w, donors), synth=pd.Series(synth, y.index), gap=pd.Series(gap, y.index),
                att=gap[~pre].mean(), pre_rmse=np.sqrt((gap[pre] ** 2).mean()), post_rmse=np.sqrt((gap[~pre] ** 2).mean()))


def sdid(y, trs, donors, open_=OPEN):
    """Synthetic DID（Arkhangelsky ほか 2021）。単位の重み（切片つき・リッジ）と時点の重みを推定して重みつき差の差"""
    pre = y.index < open_
    Y0 = y[donors].values; Y1 = y[trs].values.mean(axis=1) if isinstance(trs, list) else y[trs].values
    T0, T1 = pre.sum(), (~pre).sum(); N0 = len(donors); Ntr = len(trs) if isinstance(trs, list) else 1
    d = np.diff(Y0[pre], axis=0); sigma = d.std(ddof=1)
    zeta = (Ntr * T1) ** 0.25 * sigma
    A, b = Y0[pre], Y1[pre]
    def obj_w(p):
        w0, w = p[0], p[1:]
        return ((w0 + A @ w - b) ** 2).sum() + zeta ** 2 * T0 * (w ** 2).sum()
    p0 = np.r_[0, np.full(N0, 1 / N0)]
    r = minimize(obj_w, p0, method="SLSQP", bounds=[(None, None)] + [(0, 1)] * N0,
                 constraints=[{"type": "eq", "fun": lambda p: p[1:].sum() - 1}], options={"maxiter": 1000, "ftol": 1e-14})
    w = np.clip(r.x[1:], 0, None); w /= w.sum()
    B, c = Y0[pre].T, Y0[~pre].mean(axis=0)          # 時点の重み：対照県の事後平均を事前の時点で再現
    def obj_l(p):
        l0, l = p[0], p[1:]
        return ((l0 + B @ l - c) ** 2).sum() + 1e-6 * sigma ** 2 * N0 * (l ** 2).sum()
    q0 = np.r_[0, np.full(T0, 1 / T0)]
    r2 = minimize(obj_l, q0, method="SLSQP", bounds=[(None, None)] + [(0, 1)] * T0,
                  constraints=[{"type": "eq", "fun": lambda p: p[1:].sum() - 1}], options={"maxiter": 1000, "ftol": 1e-14})
    lam = np.clip(r2.x[1:], 0, None); lam /= lam.sum()
    tr_diff = Y1[~pre].mean() - lam @ Y1[pre]
    co_diff = (Y0[~pre].mean(axis=0) - lam @ Y0[pre]) @ w
    att = tr_diff - co_diff
    # 図用：事前の水準をそろえた合成系列
    synth = Y0 @ w + (lam @ Y1[pre] - lam @ (Y0[pre] @ w))
    return dict(w=pd.Series(w, donors), lam=pd.Series(lam, y.index[pre]), att=att,
                synth=pd.Series(synth, y.index), gap=pd.Series(Y1 - synth, y.index))


def ascm(y, tr, donors, open_=OPEN, alpha=None):
    """Augmented SCM（Ben-Michael ほか 2021、リッジ版）：SCM の事前のずれをリッジ回帰で補正"""
    s = scm(y, tr, donors, open_)
    pre = y.index < open_
    X0 = y.loc[pre, donors].values.T; x1 = y.loc[pre, tr].values
    Yp0 = y.loc[~pre, donors].values.T
    mu = X0.mean(axis=0)
    Xc = X0 - mu
    if alpha is None:   # 対照県の一つ抜きで事後の当てはまりが最もよい罰則を選ぶ
        grid = np.logspace(-3, 2, 26); best = None
        for a in grid:
            err = 0
            for j in range(len(donors)):
                m = np.ones(len(donors), bool); m[j] = False
                Xm = X0[m]; mm = Xm.mean(axis=0); Xmc = Xm - mm
                B = np.linalg.solve(Xmc.T @ Xmc + a * np.eye(Xmc.shape[1]), Xmc.T @ (Yp0[m] - Yp0[m].mean(axis=0)))
                pred = Yp0[m].mean(axis=0) + (X0[j] - mm) @ B
                err += ((Yp0[j] - pred) ** 2).mean()
            if best is None or err < best[0]: best = (err, a)
        alpha = best[1]
    B = np.linalg.solve(Xc.T @ Xc + alpha * np.eye(Xc.shape[1]), Xc.T @ (Yp0 - Yp0.mean(axis=0)))
    w = s["w"].values
    adj_post = (x1 - X0.T @ w) @ B
    synth = s["synth"].copy()
    synth[~pre] = synth[~pre].values + adj_post
    gap = y[tr] - synth
    return dict(w=s["w"], synth=synth, gap=gap, att=gap[~pre].mean(), alpha=alpha,
                pre_rmse=s["pre_rmse"])


def did(y, tr, donors, open_=OPEN):
    pre = y.index < open_
    g = y[tr] - y[donors].mean(axis=1)
    return dict(att=g[~pre].mean() - g[pre].mean(), gap=g - g[pre].mean())
