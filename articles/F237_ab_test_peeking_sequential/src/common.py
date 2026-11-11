"""F237 共通：A/B テストのシミュレーションと、途中で見るときの判定ルール。
テストのデータはすべてシミュレーション（架空のECサイト「みどりモール」を想定）。"""
import numpy as np
from scipy.stats import norm

ALPHA = 0.05
BASE = 0.05          # いまの購入率（F236 と同じ）
LIFT = 0.10          # 見つけたい差（相対 +10%、F236 と同じ）
DAILY_PER_ARM = 2500 # 1日の訪問者 5,000人（2群合計）→ 1群 2,500人（F236 の表の行）
FIX_DAYS = 14        # F236 の計算で +10% を見つけるのに要る日数（週単位に切り上げ）
MAX_DAYS = 28        # 連続で見る方法の上限
HOURS = 24

def hourly_n(daily=DAILY_PER_ARM, hours=HOURS):
    base = daily // hours
    n = np.full(hours, base)
    n[: daily - base * hours] += 1
    return n  # 合計 = daily

def sim_cum(R, days, pA, pB, seed, daily=DAILY_PER_ARM, wk=None, chunk=None):
    """1時間ごとの購入数をシミュレーションし、累積の購入数（R×時間）と累積の人数（時間）を返す。
    wk：曜日パターン（7要素、訪問者の倍率, 購入率の倍率）。None なら毎日同じ。"""
    rng = np.random.default_rng(seed)
    H = days * HOURS
    nh = []
    ph_scale = []
    for d in range(days):
        if wk is None:
            tm, cm = 1.0, 1.0
        else:
            tm, cm = wk[d % 7]
        nh.append(hourly_n(int(round(daily * tm))))
        ph_scale.append(np.full(HOURS, cm))
    nh = np.concatenate(nh)
    sc = np.concatenate(ph_scale)
    cA = rng.binomial(nh[None, :], np.clip(pA * sc, 0, 1)[None, :], size=(R, H)).astype(np.int32)
    cB = rng.binomial(nh[None, :], np.clip(pB * sc, 0, 1)[None, :], size=(R, H)).astype(np.int32)
    return np.cumsum(cA, axis=1), np.cumsum(cB, axis=1), np.cumsum(nh)

def zstat(cA, cB, n):
    """2つの割合の差の z（併合した割合で標準誤差）。n は1群の人数。"""
    pa = cA / n; pb = cB / n; pp = (cA + cB) / (2 * n)
    se = np.sqrt(np.maximum(pp * (1 - pp) * 2 / n, 1e-300))
    return (pb - pa) / se

def calibrate_bounds(tk, spend, alpha=ALPHA, M=400_000, seed=11):
    """情報の割合 tk（増えていく）での両側の境界を、α 消費関数 spend(t) に合わせてブラウン運動の
    シミュレーションで決める（Lan-DeMets の方法）。"""
    rng = np.random.default_rng(seed)
    tk = np.asarray(tk, float)
    dt = np.diff(np.concatenate([[0.0], tk]))
    W = np.cumsum(rng.standard_normal((M, len(tk))) * np.sqrt(dt)[None, :], axis=1)
    Z = W / np.sqrt(tk)[None, :]
    alive = np.ones(M, bool)
    bounds = []
    prev = 0.0
    for k in range(len(tk)):
        target = spend(tk[k], alpha) - prev   # この回に使う α
        a = np.abs(Z[alive, k])
        need = target * M                     # この回に新しく越える本数
        if need < 200:
            # 使う α がごく小さい回は、シミュレーションの本数が足りないので正規分布の式で決める
            # （それより前に越えた分はほぼ 0 なので、この近似の誤差は無視できる）
            c = float(norm.ppf(1 - max(target, 1e-15) / 2))
        elif len(a) == 0:
            c = np.inf
        else:
            q = 1 - need / len(a)
            c = np.inf if q >= 1 else float(np.quantile(a, max(q, 0)))
        bounds.append(c)
        cross = alive.copy(); cross[alive] = np.abs(Z[alive, k]) >= c
        alive &= ~cross
        prev = max(prev + max(target, 0), 1 - alive.mean()) if need < 200 else 1 - alive.mean()
    return np.array(bounds)

def obf_spend(t, a=ALPHA):
    return 2 - 2 * norm.cdf(norm.ppf(1 - a / 2) / np.sqrt(t))

def pocock_spend(t, a=ALPHA):
    return a * np.log(1 + (np.e - 1) * t)

def first_cross(stat_at_looks, bound):
    """各回の |z| が境界を越えた最初の回の番号（越えなければ -1）。"""
    hit = np.abs(stat_at_looks) >= np.asarray(bound)[None, :]
    any_ = hit.any(axis=1)
    idx = np.where(any_, hit.argmax(axis=1), -1)
    return idx

def msprt_pvalues(cA, cB, n, tau):
    """mSPRT（正規分布の混合）の、いつ見てもよい p 値（各時点）。差 θ = pB − pA の正規近似。"""
    pa = cA / n; pb = cB / n
    V = (pa * (1 - pa) + pb * (1 - pb)) / n
    pp = (cA + cB) / (2 * n)
    V = np.where(V > 0, V, np.maximum(pp * (1 - pp) * 2 / n, 1e-12))
    th = pb - pa
    t2 = tau ** 2
    logL = 0.5 * np.log(V / (V + t2)) + th ** 2 * t2 / (2 * V * (V + t2))
    p = np.minimum(1.0, np.exp(-logL))
    return np.minimum.accumulate(p, axis=1)
