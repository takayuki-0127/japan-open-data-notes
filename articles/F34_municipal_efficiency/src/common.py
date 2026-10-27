"""F34 共通：パス・図の体裁・DEA と SFA の推定関数"""
from pathlib import Path
import logging, warnings
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
from scipy.optimize import linprog, minimize
from scipy.stats import norm
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
GCOL = ["#a9c9ef", "#6fa6e6", "#2a78d6", "#1b4f99", "#0b2a57"]
SOURCE = "出典：統計センター「SSDSE-A-2026」、総務省「統計でみる市区町村のすがた」（e-Stat 社会・人口統計体系）をもとに作成者が加工して作成"

# 人口規模のグループ（2020年国勢調査の総人口）
GROUPS = [(0, 1e4, "1万人未満"), (1e4, 3e4, "1万〜3万人"), (3e4, 1e5, "3万〜10万人"),
          (1e5, 3e5, "10万〜30万人"), (3e5, 1e9, "30万人以上")]
GLAB = [g[2] for g in GROUPS]


def group_of(pop):
    for lo, hi, lab in GROUPS:
        if lo <= pop < hi:
            return lab
    return GLAB[-1]


def save(fig, name):
    fig.text(0.01, -0.02, SOURCE, fontsize=7, color=GRAY, ha="left", va="top")
    fig.savefig(FIG / name)
    plt.close(fig)


def dea_input(X, Y, vrs=True, super_eff=False):
    """入力指向の DEA（CCR: vrs=False、BCC: vrs=True）。
    X: (n, m) 入力、Y: (n, s) 出力。各 DMU o について
      min θ  s.t.  Σλ_j x_ij ≤ θ x_io,  Σλ_j y_rj ≥ y_ro,  λ ≥ 0,（BCC なら Σλ=1）
    super_eff=True なら o 自身を参照集合から外す（スーパー効率。1を超えうる。解なしは NaN）。"""
    X, Y = np.asarray(X, float), np.asarray(Y, float)
    n, m = X.shape
    s = Y.shape[1]
    out = np.full(n, np.nan)
    for o in range(n):
        idx = np.arange(n) if not super_eff else np.delete(np.arange(n), o)
        k = len(idx)
        c = np.r_[1.0, np.zeros(k)]                       # 変数：θ, λ_1..λ_k
        A_in = np.c_[-X[o][:, None], X[idx].T]            # Σλx − θx_o ≤ 0
        A_out = np.c_[np.zeros((s, 1)), -Y[idx].T]        # −Σλy ≤ −y_o
        A_ub = np.r_[A_in, A_out]
        b_ub = np.r_[np.zeros(m), -Y[o]]
        A_eq = b_eq = None
        if vrs:
            A_eq = np.r_[0.0, np.ones(k)][None, :]
            b_eq = [1.0]
        r = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                    bounds=[(0, None)] * (k + 1), method="highs")
        if r.status == 0:
            out[o] = r.x[0]
    return out


def sfa_cost(y, X, names=None):
    """費用フロンティア（正規・半正規）の最尤推定。
    ln C = Xβ + v + u,  v ~ N(0, σv²),  u ~ |N(0, σu²)|（u ≥ 0 が非効率で費用を押し上げる）。
    戻り値：係数、σu、σv、λ、対数尤度、各 DMU の費用効率 E[exp(−u)|ε]（Battese–Coelli）。"""
    y, X = np.asarray(y, float), np.asarray(X, float)
    n, k = X.shape
    b0 = np.linalg.lstsq(X, y, rcond=None)[0]
    e0 = y - X @ b0
    s0 = np.log(np.std(e0))

    def nll(p):
        b, lsu, lsv = p[:k], p[k], p[k + 1]
        su, sv = np.exp(lsu), np.exp(lsv)
        sig = np.sqrt(su ** 2 + sv ** 2)
        lam = su / sv
        e = y - X @ b
        # 費用関数：ε = v + u なので +λε/σ
        ll = np.log(2) - np.log(sig) + norm.logpdf(e / sig) + norm.logcdf(lam * e / sig)
        return -ll.sum()

    p0 = np.r_[b0, s0 - 0.3, s0 - 0.3]
    r = minimize(nll, p0, method="L-BFGS-B")
    r = minimize(nll, r.x, method="BFGS")
    # BFGS は最後に精度の警告を出すことがあるので、最適値から Powell でもう一度探し、改善が 1e-4 未満なら収束とみなす
    r2 = minimize(nll, r.x, method="Powell", options={"maxiter": 20000, "xtol": 1e-8, "ftol": 1e-10})
    if r2.fun < r.fun:
        r2.hess_inv = getattr(r, "hess_inv", None)
        improve, r = r.fun - r2.fun, r2
    else:
        improve = 0.0
    r.success = improve < 1e-4
    b = r.x[:k]
    su, sv = np.exp(r.x[k]), np.exp(r.x[k + 1])
    e = y - X @ b
    sig2 = su ** 2 + sv ** 2
    mu_star = e * su ** 2 / sig2
    s_star = su * sv / np.sqrt(sig2)
    z = mu_star / s_star
    # E[exp(−u) | ε]（u|ε ~ N+(μ*, σ*²)）
    te = np.exp(-mu_star + 0.5 * s_star ** 2) * norm.cdf(z - s_star) / norm.cdf(z)
    try:
        cov = r.hess_inv
        se = np.sqrt(np.diag(cov))[:k]
    except Exception:
        se = np.full(k, np.nan)
    return {"beta": pd.Series(b, index=names), "se": pd.Series(se, index=names), "sigma_u": su, "sigma_v": sv,
            "lambda": su / sv, "loglik": -r.fun, "eff": te, "converged": r.success}
