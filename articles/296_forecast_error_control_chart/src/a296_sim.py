"""需要予測の当たり外れを毎週見張る：誤差の管理図と、作り直しの決まり。
架空の日別需要（曜日の形＋ばらつき）。予測は「学習期間の曜日ごとの平均」を固定で使う（表計算でできる程度のもの）。
学習：1〜52週、管理限界を決める期間：53〜78週、80週目から需要の水準が s% 変わる（s=0 は変化なし＝空振りを数える）。seed 296"""
import json, numpy as np, pandas as pd
from common import RES, DATA
WD = np.array([0.9, 0.9, 0.95, 1.0, 1.1, 1.35, 1.3])  # 月〜日
W_TRAIN, W_BASE, W_BREAK, W_END = 52, 78, 80, 156

def demand(rng, shift, noise=0.08, annual=0.0):
    w = np.arange(W_END * 7) // 7; d = np.arange(W_END * 7)
    level = 1000 * (1 + annual * np.sin(2 * np.pi * d / 364)) * np.where(w >= W_BREAK - 1, 1 + shift, 1.0)
    return level * WD[d % 7] * np.exp(rng.normal(0, noise, len(d)))

def weekly_bias(y, fc):
    a = y.reshape(-1, 7).sum(1); f = fc.reshape(-1, 7).sum(1)
    return (a - f) / f  # 週の誤差（+ は実績が予測より多い）

def fit(y, w_from, w_to):  # 曜日ごとの平均
    seg = y[(w_from - 1) * 7:w_to * 7].reshape(-1, 7)
    return seg.mean(0)

def rules(z):
    """z：管理限界の期間の平均と標準偏差でそろえた週の誤差。週ごとに鳴ったかを返す"""
    n = len(z); r1 = np.abs(z) > 3
    r2 = np.zeros(n, bool); r3 = np.zeros(n, bool); cu = np.zeros(n, bool); cp = cn = 0.0
    for t in range(n):
        if t >= 2:
            w = z[t - 2:t + 1]; r2[t] = (w > 2).sum() >= 2 or (w < -2).sum() >= 2
        if t >= 3:
            w = z[t - 3:t + 1]; r3[t] = (w > 1).all() or (w < -1).all()
        cp = max(0, cp + z[t] - 0.5); cn = max(0, cn - z[t] - 0.5); cu[t] = cp > 4 or cn > 4
        if cu[t]: cp = cn = 0.0
    return {"R1 3σを1回": r1, "R2 2σを3週中2回": r2, "R3 1σを4週続けて": r3, "R1〜R3のどれか": r1 | r2 | r3, "CUSUM（k=0.5, h=4）": cu}

def one_run(rng, shift, annual=0.0):
    y = demand(rng, shift, annual=annual)
    fc = np.tile(fit(y, 1, W_TRAIN), W_END)
    b = weekly_bias(y, fc)
    base = b[W_TRAIN:W_BASE]; mu, sd = base.mean(), base.std(ddof=1)
    z = (b - mu) / sd
    mon = slice(W_BASE, W_END)  # 79週目から見張る
    return rules(z[mon]), b

def detect_stats(shift, n=2000, annual=0.0, seed=296):
    rng = np.random.default_rng(seed + int(shift * 1000) + int(annual * 100))
    out = {}
    for _ in range(n):
        rs, _ = one_run(rng, shift, annual)
        for k, v in rs.items():
            idx = np.arange(W_BASE + 1, W_END + 1)
            if shift == 0:
                out.setdefault(k, []).append(v.sum() / (len(v) / 52))  # 1年あたりの空振り
            else:
                pre = v[idx < W_BREAK]; post = np.where(v & (idx >= W_BREAK))[0]
                delay = (idx[post[0]] - W_BREAK + 1) if len(post) else np.nan
                out.setdefault(k, []).append(delay)
    res = {}
    for k, v in out.items():
        v = np.array(v, float)
        if shift == 0: res[k] = {"false_alarms_per_year": round(float(v.mean()), 2), "share_years_with_alarm": round(float((v > 0).mean()), 3)}
        else: res[k] = {"median_delay_weeks": float(np.nanmedian(v)), "p90_delay_weeks": float(np.nanpercentile(v, 90)), "detected_within_8w": round(float(np.mean(v <= 8)), 3)}
    return res

if __name__ == "__main__":
    out = {"main": {}, "annual5": {}}
    for s in [0.0, 0.05, 0.10, 0.20, -0.10]:
        out["main"][f"{s:+.0%}"] = detect_stats(s)
    for s in [0.0, 0.10]:
        out["annual5"][f"{s:+.0%}"] = detect_stats(s, annual=0.05)
    json.dump(out, open(RES / "detection.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
