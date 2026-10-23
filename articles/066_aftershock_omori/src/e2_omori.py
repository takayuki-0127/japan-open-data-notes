"""余震の減り方：改良大森公式（大森・宇津）を最尤法で当てはめ、p値・c値・K値を比べる。最大余震とのM差（バートの法則）"""
import numpy as np, pandas as pd
from scipy.optimize import minimize
import matplotlib.pyplot as plt
from common import *

d = load(); d = d[d.mag.notna()].copy()
EQ = {  # 名前: (本震の時刻, 範囲の半径km, 深さの上限km, 余震に使う下限M)
    "東北地方太平洋沖地震（2011年3月11日、M9.0）": ("2011-03-11 14:46:18", 350, 100, 4.5),
    "熊本地震（2016年4月16日、M7.3）": ("2016-04-16 01:25:05", 50, 30, 2.5),
    "能登半島地震（2024年1月1日、M7.6）": ("2024-01-01 16:10:22", 100, 30, 2.5),
}
SHORT = {k: k.split("（")[0] for k in EQ}
COL = dict(zip(EQ, [BLUE, ORANGE, GREEN]))
T, S = 365.0, 0.01  # 本震から1年間、最初の約15分は検知が追いつかないので除く


def nll(th, t):
    lk, lc, p = th; K, c = np.exp(lk), np.exp(lc)
    if abs(p - 1) < 1e-6: I = K * (np.log(T + c) - np.log(S + c))
    else: I = K * ((T + c) ** (1 - p) - (S + c) ** (1 - p)) / (1 - p)
    return -(np.sum(np.log(K) - p * np.log(t + c)) - I)


rows, series, mags = [], {}, {}
for name, (t0, R, zmax, mmin) in EQ.items():
    t0 = pd.Timestamp(t0)
    ms = d[(d.time - t0).abs() < pd.Timedelta(seconds=3)].sort_values("mag").iloc[-1]
    dist = haversine(ms.lat, ms.lon, d.lat.values, d.lon.values)
    sel = d[(dist <= R) & (d.depth <= zmax) & (d.time > ms.time) & (d.time <= ms.time + pd.Timedelta(days=T))].copy()
    sel["t"] = (sel.time - ms.time).dt.total_seconds() / 86400
    mags[name] = sel[["t", "mag"]]
    a = sel[(sel.mag >= mmin) & (sel.t >= S)].t.values
    best = None
    for p0 in (0.9, 1.1, 1.3):
        for c0 in (0.01, 0.1):
            r = minimize(nll, [np.log(len(a) / 10), np.log(c0), p0], args=(a,), method="Nelder-Mead", options={"maxiter": 5000, "xatol": 1e-6, "fatol": 1e-6})
            if best is None or r.fun < best.fun: best = r
    lk, lc, p = best.x
    # ブートストラップ（余震の時刻をリサンプル）で p の95%区間
    rng = np.random.default_rng(1); ps = []
    for _ in range(200):
        bb = np.sort(rng.choice(a, len(a)))
        rr = minimize(nll, best.x, args=(bb,), method="Nelder-Mead", options={"maxiter": 3000})
        ps.append(rr.x[2])
    big = sel[sel.t > 0].sort_values("mag").iloc[-1]
    big30 = sel[(sel.t > 0) & (sel.t <= 30)].sort_values("mag").iloc[-1]
    n1 = (a < 1).sum(); n_last = ((a >= 335) & (a < 365)).sum()
    rows.append({"eq": SHORT[name], "main_M": ms.mag, "radius_km": R, "depth_max": zmax, "m_min": mmin, "n_aftershocks": len(a),
                 "K": np.exp(lk), "c_day": np.exp(lc), "p": p, "p_lo": np.percentile(ps, 2.5), "p_hi": np.percentile(ps, 97.5),
                 "largest_aftershock_M": big.mag, "largest_aftershock_days": big.t, "bath_dM": ms.mag - big.mag, "largest_30d_M": big30.mag, "largest_30d_days": big30.t, "bath_dM_30d": ms.mag - big30.mag, "largest_time": str(big.time),
                 "n_first_day": n1, "n_last_30days": n_last})
    edges = np.logspace(np.log10(S), np.log10(T), 30); cnt, _ = np.histogram(a, edges); w = np.diff(edges)
    series[name] = (np.sqrt(edges[1:] * edges[:-1]), cnt / w, edges, lk, lc, p)
    print(rows[-1])
R_ = pd.DataFrame(rows); R_.to_csv(RES / "e2_omori.csv", index=False, encoding="utf-8-sig")

# 下限Mを変えたときの p の頑健性
rob = []
for name, (t0, R, zmax, mmin) in EQ.items():
    sel = mags[name]
    for dm in (0, 0.5, 1.0):
        a = sel[(sel.mag >= mmin + dm) & (sel.t >= S)].t.values
        if len(a) < 50: continue
        best = min((minimize(nll, [np.log(len(a) / 10), np.log(c0), p0], args=(a,), method="Nelder-Mead", options={"maxiter": 5000}) for p0 in (0.9, 1.1, 1.3) for c0 in (0.01, 0.1)), key=lambda r: r.fun)
        rob.append({"eq": SHORT[name], "m_min": round(mmin + dm, 1), "n": len(a), "p": best.x[2], "c_day": np.exp(best.x[1])})
RB = pd.DataFrame(rob); RB.to_csv(RES / "e2_robust.csv", index=False, encoding="utf-8-sig"); print(RB.round(3))

# 図1：1日あたりの余震の数（両対数）
fig, ax = plt.subplots(figsize=(8, 5))
for name, (x, y, e, lk, lc, p) in series.items():
    ok = y > 0
    ax.loglog(x[ok], y[ok], "o", color=COL[name], ms=4.5, label=f"{SHORT[name]}（M{EQ[name][3]}以上）")
    tt = np.logspace(np.log10(S), np.log10(T), 200); ax.loglog(tt, np.exp(lk) / (tt + np.exp(lc)) ** p, "-", color=COL[name], lw=1.4, label=f"  当てはめ p={p:.2f}")
ax.set_xlabel("本震からの経過日数（対数目盛）"); ax.set_ylabel("1日あたりの余震の数（対数目盛）")
ax.legend(frameon=False, fontsize=8.8); ax.set_title("余震は「時間に反比例」に近い形で減っていく", loc="left")
note(ax, SOURCE + "\n改良大森公式 n(t)=K/(t+c)^p を最尤法で当てはめ。本震から0.01日〜365日", -0.12)
fig.savefig(FIG / "e2_decay.png"); plt.close(fig)

# 図2：時間と規模（M−t図）
fig, axes = plt.subplots(3, 1, figsize=(8.4, 7.2), sharex=True)
for ax, (name, sel) in zip(axes, mags.items()):
    s_ = sel[sel.mag >= EQ[name][3] - 0.5]
    ax.scatter(s_.t.clip(lower=1e-3), s_.mag, s=3, color=COL[name], alpha=.4, lw=0)
    r_ = R_[R_["eq"] == SHORT[name]].iloc[0]
    ax.axhline(r_.main_M, color=INK, lw=.8, ls=":"); ax.text(1.2e-3, r_.main_M - .35, f"本震 M{r_.main_M}", fontsize=8.5, va="top")
    ax.plot(r_.largest_aftershock_days, r_.largest_aftershock_M, "*", color=INK, ms=11)
    late = r_.largest_aftershock_days > 10
    ax.text(r_.largest_aftershock_days * (0.7 if late else 1.4), r_.largest_aftershock_M, f"最大余震 M{r_.largest_aftershock_M}（差{r_.bath_dM:.1f}）", fontsize=8.5, va="center", ha="right" if late else "left")
    ax.set_xscale("log"); ax.set_ylabel("M"); ax.set_title(SHORT[name], loc="left", fontsize=11); ax.set_ylim(EQ[name][3] - 0.6, r_.main_M + 0.4)
axes[-1].set_xlabel("本震からの経過日数（対数目盛）")
note(axes[-1], SOURCE, -0.45)
fig.savefig(FIG / "e2_mt.png"); plt.close(fig)

# 図3：p値の比較
fig, ax = plt.subplots(figsize=(7, 3.4))
for i, r_ in enumerate(R_.itertuples()):
    ax.errorbar(r_.p, i, xerr=[[r_.p - r_.p_lo], [r_.p_hi - r_.p]], fmt="o", color=list(COL.values())[i], capsize=4, ms=7)
    ax.text(r_.p_hi + .01, i, f"p={r_.p:.2f}", va="center", fontsize=9)
ax.axvline(1, color=GRAY, ls=":", lw=1); ax.set_xlim(0.98, 1.14); ax.set_ylim(len(R_) - .4, -.6); ax.set_yticks(range(len(R_))); ax.set_yticklabels(R_["eq"])
ax.set_xlabel("p値（大きいほど早く減る。ひげは95%区間）"); ax.set_title("余震の減り方の速さ（p値）", loc="left", fontsize=12)
note(ax, SOURCE, -0.25)
fig.savefig(FIG / "e2_p.png"); plt.close(fig)
