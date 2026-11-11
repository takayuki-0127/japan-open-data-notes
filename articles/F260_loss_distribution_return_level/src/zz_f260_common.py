"""共通：損害額のものさし（2025年度の建設費と住宅数に直した億円）と、5つの分布。"""
import pathlib
import numpy as np, pandas as pd
from scipy import stats, optimize, special

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, P, R = ROOT / "data" / "raw", ROOT / "data" / "processed", ROOT / "results"
pr = pd.read_csv(RAW / "f256_deflator.csv").set_index("fy")
dw = pd.read_csv(RAW / "f256_dwellings.csv")
T_SURVEY = dw.year.values + 0.75            # 調査は各年10月1日
D_SURVEY = dw.dwellings.values.astype(float)
SLOPE_LAST = (D_SURVEY[-1] - D_SURVEY[-2]) / 5.0

def tdate(ym):
    y, m = int(ym[:4]), int(ym[5:7]); return y + (m - 0.5) / 12

def dwell(t):  # F256 と同じ：直線補間、2023年10月より後は2018→2023年の増え方で延ばす
    if t > T_SURVEY[-1]:
        return D_SURVEY[-1] + SLOPE_LAST * (t - T_SURVEY[-1])
    return float(np.interp(t, T_SURVEY, D_SURVEY))

T_NOW = 2025.75  # 2025年10月1日（2025年度の真ん中）
def to_2025(nom_yen, fy, ym, deflator="defl_house"):
    """名目の保険金 → 住宅1戸あたり実質（発生年度の物価、発生時点の住宅数） → 2025年度の物価・住宅数に戻した億円"""
    per = nom_yen * 100.0 / pr.loc[fy, deflator] / dwell(tdate(ym))
    return per * dwell(T_NOW) * pr.loc[2025, deflator] / 100.0 / 1e8, per

def cutoff(deflator="defl_house"):
    """F256 の「取りこぼしのない足切り」（住宅1戸あたり実質）。上位10表の10位（名目1,642億円）にどの月でも届く最小の大きさ。"""
    need = []
    for y in range(1991, 2027):
        for m in range(1, 13):
            fy = y - (m <= 3)
            if fy < 1991 or fy > 2025: continue
            need.append(1642e8 / (pr.loc[fy, deflator] / 100.0 * dwell(y + (m - 0.5) / 12)))
    return max(need)

# ---------------- 分布（しきい値 u を超えた事故の損害 x > u に当てはめる） ----------------
MODELS = ["指数", "ワイブル", "対数正規", "パレート", "GPD"]
NPAR = {"指数": 1, "ワイブル": 2, "対数正規": 2, "パレート": 1, "GPD": 2}

def fit(name, x, u):
    """最尤法。戻り値：(パラメータ, 対数尤度)。どれも「x>u の条件付き」の密度なので AIC を比べられる。"""
    x = np.asarray(x, float); y = x - u
    if name == "指数":
        m = y.mean(); return (m,), float(np.sum(-np.log(m) - y / m))
    if name == "パレート":
        a = len(x) / np.sum(np.log(x / u)); return (a,), float(np.sum(np.log(a) + a * np.log(u) - (a + 1) * np.log(x)))
    if name == "GPD":
        best = None
        for xi0 in (-0.3, 0.1, 0.5, 1.0):
            def nll(t):
                xi, ls = t; s = np.exp(ls)
                z = 1 + xi * y / s
                if np.any(z <= 0): return 1e10
                if abs(xi) < 1e-8: return float(np.sum(np.log(s) + y / s))
                return float(np.sum(np.log(s) + (1 + 1 / xi) * np.log(z)))
            r = optimize.minimize(nll, [xi0, np.log(y.mean())], method="Nelder-Mead", options=dict(xatol=1e-9, fatol=1e-10, maxiter=4000))
            if best is None or r.fun < best.fun: best = r
        xi, ls = best.x; return (xi, float(np.exp(ls))), -float(best.fun)
    if name == "ワイブル":
        lx, lu = np.log(x), np.log(u)
        def nll(t):
            k, ls = np.exp(t[0]), t[1]          # 形 k, 尺度 exp(ls)
            zx, zu = np.exp(k * (lx - ls)), np.exp(k * (lu - ls))
            return -float(np.sum(np.log(k) - ls + (k - 1) * (lx - ls) - zx + zu))
        best = None
        for k0 in (0.2, 0.5, 1.0):
            for s0 in (np.log(u), np.log(x.mean())):
                r = optimize.minimize(nll, [np.log(k0), s0], method="Nelder-Mead", options=dict(xatol=1e-9, fatol=1e-10, maxiter=6000))
                if best is None or r.fun < best.fun: best = r
        return (float(np.exp(best.x[0])), float(best.x[1])), -float(best.fun)   # (形 k, 尺度の対数)
    if name == "対数正規":
        lx, lu = np.log(x), np.log(u)
        def nll(t):
            mu, sg = t[0], np.exp(t[1]); z = (lx - mu) / sg
            # 対数正規の密度（x>u で切断）。scipy.stats を毎回呼ぶと遅いので式で書く
            return -float(np.sum(-0.5 * z * z - np.log(sg) - 0.9189385332046727 - lx) - len(x) * special.log_ndtr(-(lu - mu) / sg))
        best = None
        for mu0 in (lu - 3, lu, lx.mean()):
            for s0 in (0.5, 1.5, 3.0):
                r = optimize.minimize(nll, [mu0, np.log(s0)], method="Nelder-Mead", options=dict(xatol=1e-9, fatol=1e-10, maxiter=6000))
                if best is None or r.fun < best.fun: best = r
        return (float(best.x[0]), float(np.exp(best.x[1]))), -float(best.fun)
    raise ValueError(name)

def isf(name, par, u, p):
    """条件付きの上側確率 P(X>x | X>u) = p となる x（p は配列可）"""
    p = np.asarray(p, float)
    if name == "指数": return u - par[0] * np.log(p)
    if name == "パレート": return u * p ** (-1 / par[0])
    if name == "GPD":
        xi, s = par
        return u + (s * (-np.log(p)) if abs(xi) < 1e-8 else s / xi * (p ** (-xi) - 1))
    if name == "ワイブル":
        k, ls = par  # S(x)=exp(-(x/s)^k) → 条件付き：exp(-(x/s)^k + (u/s)^k) = p。尺度 s は対数で持つ（ブートストラップで s が極端に小さくなるため）
        return np.exp(ls + np.log(np.exp(k * (np.log(u) - ls)) - np.log(p)) / k)
    if name == "対数正規":
        mu, sg = par
        lsu = stats.norm.logsf(np.log(u), mu, sg)
        return np.exp(mu + sg * stats.norm.isf(np.exp(lsu + np.log(p))))
    raise ValueError(name)

def sf(name, par, u, x):
    """条件付きの上側確率 P(X>x | X>u)"""
    x = np.asarray(x, float)
    if name == "指数": return np.exp(-(x - u) / par[0])
    if name == "パレート": return (x / u) ** (-par[0])
    if name == "GPD":
        xi, s = par; z = np.maximum(1 + xi * (x - u) / s, 0)
        return np.exp(-(x - u) / s) if abs(xi) < 1e-8 else np.where(z > 0, z ** (-1 / xi), 0.0)
    if name == "ワイブル":
        k, ls = par; return np.exp(-np.exp(k * (np.log(x) - ls)) + np.exp(k * (np.log(u) - ls)))
    if name == "対数正規":
        mu, sg = par; return np.exp(stats.norm.logsf(np.log(x), mu, sg) - stats.norm.logsf(np.log(u), mu, sg))

def return_level(name, par, u, lam, T):
    """λ×P(X>x|X>u) = 1/T となる x。λ<1/T（その大きさの事故が T 年に1回も起きない）なら u を返さず nan。"""
    p = 1.0 / (T * lam)
    return float(isf(name, par, u, p)) if p < 1 else np.nan

def aggregate_q(name, par, u, lam, qs=(0.99, 0.995), n_years=100_000, seed=0):
    """複合ポアソン：年の件数 N~Poisson(λ)、1件の損害は当てはめた分布。年間合計の分位点。u 以下の事故は入れない。"""
    rng = np.random.default_rng(seed)
    n = rng.poisson(lam, n_years)
    sev = isf(name, par, u, 1 - rng.random(n.sum()))   # 1-U は (0,1]
    tot = np.zeros(n_years); np.add.at(tot, np.repeat(np.arange(n_years), n), sev)
    return [float(np.quantile(tot, q)) for q in qs], float(tot.mean())
