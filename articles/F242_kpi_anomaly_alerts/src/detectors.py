"""異常検知のルール（どれもその日の判定に、前日までの値だけを使う）。
入力 ly：log(KPI) の配列、sp：特別な日の種類（0=ふつう, 1=祝日, 2=年末年始・お盆, 3=予定された販促）。
戻り値は z（どれだけ外れたか）と、警報の日（True/False）。"""
import numpy as np
from statsmodels.tsa.seasonal import STL

MADK = 1.4826

def _mad(x):
    x = x[np.isfinite(x)]
    if len(x) < 5: return np.nan
    return MADK * np.median(np.abs(x - np.median(x)))

def d1_prev_day(ly, thr=np.log(1.10)):
    e = np.r_[np.nan, np.diff(ly)]
    return e, np.abs(e) > thr

def d2_moving(ly, w=28, k=3.0):
    n = len(ly); z = np.full(n, np.nan)
    for t in range(w, n):
        x = ly[t - w:t]; s = x.std(ddof=1)
        z[t] = (ly[t] - x.mean()) / s if s > 0 else np.nan
    return z, np.abs(z) > k

def d3_same_weekday(ly, k=3.5, nweeks=4, scale_days=56):
    n = len(ly); e = np.full(n, np.nan); z = np.full(n, np.nan)
    for t in range(7 * nweeks, n):
        base = np.median(ly[t - 7 * nweeks:t:7])
        e[t] = ly[t] - base
    for t in range(7 * nweeks + scale_days, n):
        s = _mad(e[t - scale_days:t])
        z[t] = e[t] / s if s and s > 0 else np.nan
    return z, np.abs(z) > k

def d4_stl(ly, k=3.5, w=84, scale_days=56):
    """STL で前の84日を傾向・曜日の形・残差に分け、今日の値を予測する。
    尺度（どれだけの外れを普通とみるか）を2通りで返す：
      a) 当てはめた84日の残差の MAD（よく使われるが、当てはめの残差は小さく出やすい）
      b) これまでの「予測の外れ」の MAD（前の56日）"""
    n = len(ly); z = np.full(n, np.nan); zb = np.full(n, np.nan); err = np.full(n, np.nan)
    for t in range(w, n):
        x = ly[t - w:t]
        r = STL(x, period=7, robust=True).fit()
        pred = r.trend[-1] + r.seasonal[-7]
        err[t] = ly[t] - pred
        s = _mad(r.resid)
        z[t] = err[t] / s if s > 0 else np.nan
        if t >= w + scale_days:
            sb = _mad(err[t - scale_days:t])
            zb[t] = err[t] / sb if sb > 0 else np.nan
    return z, np.abs(z) > k, zb, np.abs(zb) > k

def d5_calendar(ly, sp, wd, k=3.5, nweeks=4, scale_days=56, k_special=6.0):
    """同じ曜日の中央値に、暦の扱いを足したもの。
    ふつうの日：前の「ふつうの日」の同じ曜日4つの中央値と比べる。
    祝日：前の「ふつうの日曜」4つと比べる。販促の日：前の販促の日4つと比べる。
    年末年始・お盆：比べる相手がいないので、z が k_special を超えたときだけ鳴らす（前年の同じ日と比べる）。"""
    n = len(ly); e = np.full(n, np.nan); z = np.full(n, np.nan)
    hist = {}
    def key(t):
        if sp[t] == 0: return ("wd", wd[t])
        if sp[t] == 1: return ("wd", 6)       # 祝日は日曜と比べる
        if sp[t] == 3: return ("camp", 0)
        return ("yearend", 0)
    for t in range(n):
        kk = key(t)
        if sp[t] == 2:
            if t >= 364 and np.isfinite(ly[t - 364]):
                # 前年の同じ曜日の日と比べ、ふつうの日の前年比の中央値で直す
                yoy = [ly[s] - ly[s - 364] for s in range(max(364, t - 56), t) if sp[s] == 0 and sp[s - 364] == 0]
                if yoy: e[t] = ly[t] - ly[t - 364] - np.median(yoy)
        else:
            h = hist.get(kk, [])
            if len(h) >= nweeks: e[t] = ly[t] - np.median(h[-nweeks:])
        if sp[t] != 2:
            hist.setdefault(kk, []).append(ly[t])
    norm = np.array([s == 0 for s in sp])
    for t in range(scale_days, n):
        win = e[t - scale_days:t][norm[t - scale_days:t]]
        s = _mad(win)
        z[t] = e[t] / s if s and s > 0 else np.nan
    thr = np.where(np.array(sp) == 2, k_special, k)
    return z, np.abs(z) > thr

def d6_confirm(z, sp, k=3.5, k_hi=5.0, k_special=6.0):
    """D5 の z を使い、大きく外れた日（|z|>k_hi）はすぐ鳴らす。小さめの外れは2日続いたら鳴らす（2日目に鳴る）。"""
    n = len(z); a = np.zeros(n, bool)
    for t in range(1, n):
        if not np.isfinite(z[t]): continue
        if sp[t] == 2:
            a[t] = abs(z[t]) > k_special; continue
        if abs(z[t]) > k_hi: a[t] = True
        elif abs(z[t]) > k and np.isfinite(z[t - 1]) and abs(z[t - 1]) > k and np.sign(z[t]) == np.sign(z[t - 1]): a[t] = True
    return a
