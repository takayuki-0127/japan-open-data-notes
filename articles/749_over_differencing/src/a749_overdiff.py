"""749 もともと定常な系列を差分にしてから予測すると、予測の誤差はどれだけ悪くなるのか

架空の月次の系列 120か月で学習し、その先 1〜12か月を予測する。
系列は4通り：AR(1) で φ＝0.5・0.8・0.95（定常、平均に戻る）、ランダムウォーク（差分が要る）。
予測は3通り。どれも AR(1)（1つ前の値で当てる式）を最小二乗で当てはめる：
  差分なし：値そのものに AR(1)
  1回の差分：前月との差に AR(1) を当て、足し戻す
  2回の差分：差の差に AR(1) を当て、2回足し戻す
各1,000回、予測の誤差（RMSE）を比べる。差分にした系列の1か月ずらしの自己相関も見る（−0.5 に近いと差分のしすぎの目印）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 749）"
rng = np.random.default_rng(749)
NT, H, R = 120, 12, 1000


def gen(kind, n):
    e = rng.standard_normal(n + 200)
    if kind == "rw":
        return np.cumsum(e)[200:]
    x = np.zeros(n + 200)
    for t in range(1, n + 200):
        x[t] = kind * x[t - 1] + e[t]
    return x[200:]


def ar1_fc(z, h):
    a, b = np.polyfit(z[:-1], z[1:], 1)            # z_t = a z_{t-1} + b
    f = []; last = z[-1]
    for _ in range(h):
        last = a * last + b; f.append(last)
    return np.array(f)


def forecast(x, d, h):
    if d == 0:
        return ar1_fc(x, h)
    if d == 1:
        return x[-1] + np.cumsum(ar1_fc(np.diff(x), h))
    dd = ar1_fc(np.diff(x, 2), h)
    d1 = (x[-1] - x[-2]) + np.cumsum(dd)
    return x[-1] + np.cumsum(d1)


def acf1(z):
    z = z - z.mean(); return float(np.sum(z[1:] * z[:-1]) / np.sum(z * z))


KINDS = [(0.5, "AR φ=0.5"), (0.8, "AR φ=0.8"), (0.95, "AR φ=0.95"), ("rw", "ランダムウォーク")]
rows = []; acfs = []
for k, lab in KINDS:
    err = {d: np.zeros((R, H)) for d in [0, 1, 2]}; ac = {d: [] for d in [0, 1, 2]}
    for r in range(R):
        x = gen(k, NT + H); tr, te = x[:NT], x[NT:]
        for d in [0, 1, 2]:
            err[d][r] = forecast(tr, d, H) - te
            ac[d].append(acf1(np.diff(tr, d) if d else tr))
    for d in [0, 1, 2]:
        rm = np.sqrt((err[d] ** 2).mean(0))
        rows.append(dict(series=lab, diff=d, **{f"h{h + 1}": float(rm[h]) for h in range(H)}, rmse_all=float(np.sqrt((err[d] ** 2).mean()))))
        acfs.append(dict(series=lab, diff=d, acf1=float(np.mean(ac[d]))))
S = pd.DataFrame(rows); S.to_csv(RES / "rmse.csv", index=False)
A = pd.DataFrame(acfs); A.to_csv(RES / "acf1.csv", index=False)
g = lambda s, d, c: float(S[(S.series == s) & (S["diff"] == d)][c].iloc[0])
out = {"train": NT, "horizon": H, "reps": R,
       "rmse_h12": {s: {f"d{d}": round(g(s, d, "h12"), 3) for d in [0, 1, 2]} for _, s in KINDS},
       "rmse_h1": {s: {f"d{d}": round(g(s, d, "h1"), 3) for d in [0, 1, 2]} for _, s in KINDS},
       "rmse_all": {s: {f"d{d}": round(g(s, d, "rmse_all"), 3) for d in [0, 1, 2]} for _, s in KINDS},
       "acf1": {s: {f"d{d}": round(float(A[(A.series == s) & (A['diff'] == d)].acf1.iloc[0]), 3) for d in [0, 1, 2]} for _, s in KINDS},
       "ar05_h12_ratio_d1": g("AR φ=0.5", 1, "h12") / g("AR φ=0.5", 0, "h12"),
       "ar05_h12_ratio_d2": g("AR φ=0.5", 2, "h12") / g("AR φ=0.5", 0, "h12"),
       "ar08_h12_ratio_d1": g("AR φ=0.8", 1, "h12") / g("AR φ=0.8", 0, "h12"),
       "ar095_h12_ratio_d1": g("AR φ=0.95", 1, "h12") / g("AR φ=0.95", 0, "h12"),
       "rw_h12_ratio_d0": g("ランダムウォーク", 0, "h12") / g("ランダムウォーク", 1, "h12"),
       "rw_h12_ratio_d2": g("ランダムウォーク", 2, "h12") / g("ランダムウォーク", 1, "h12")}
json.dump(out, open(RES / "a749_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：φ=0.5 の例と予測
x = gen(0.5, NT + H); tr, te = x[:NT], x[NT:]
fig, ax = plt.subplots(figsize=(9, 4.6)); t = np.arange(NT + H)
ax.plot(t[60:NT], tr[60:], color=GRAY, label="学習に使った系列（後半）"); ax.plot(t[NT:], te, color=GRAY, ls=":", label="その先（本当）")
for d, c, l in [(0, BLUE, "差分なし"), (1, ORANGE, "1回の差分"), (2, GREEN, "2回の差分")]:
    ax.plot(t[NT:], forecast(tr, d, H), color=c, lw=2, label=f"予測：{l}")
ax.set_xlabel("月"); ax.set_ylabel("値"); ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper left")
ax.set_title("平均に戻る系列（φ=0.5）：差分にすると、最後の値や傾きを先へ伸ばしてしまう")
save(fig, "a749_example.png", SRC)

# 図2：先の長さと RMSE
fig, axs = plt.subplots(1, 4, figsize=(11, 3.8), sharey=False)
for ax, (_, s) in zip(axs, KINDS):
    for d, c, l in [(0, BLUE, "差分なし"), (1, ORANGE, "1回"), (2, GREEN, "2回")]:
        ax.plot(range(1, H + 1), [g(s, d, f"h{h}") for h in range(1, H + 1)], color=c, label=l)
    ax.set_title(s, fontsize=10); ax.set_xlabel("何か月先"); ax.set_yscale("log")
axs[0].set_ylabel("予測の誤差（RMSE、対数の目盛り）"); axs[0].legend(frameon=False, fontsize=8, title="差分", title_fontsize=8)
fig.suptitle("定常な系列では差分なしがいちばん良く、2回の差分は先ほど大きく外れる（各1,000回）", y=1.04)
save(fig, "a749_rmse.png", SRC, y=-0.06)

# 図3：差分した系列の1か月ずらしの自己相関
fig, ax = plt.subplots(figsize=(9, 4.6)); xx = np.arange(len(KINDS)); w = .27
for j, (d, c, l) in enumerate([(0, BLUE, "差分なし"), (1, ORANGE, "1回の差分"), (2, GREEN, "2回の差分")]):
    v = [float(A[(A.series == s) & (A["diff"] == d)].acf1.iloc[0]) for _, s in KINDS]
    b = ax.bar(xx + (j - 1) * w, v, w, color=c, label=l)
    for bb, vv in zip(b, v):
        ax.text(bb.get_x() + w / 2, vv + (.03 if vv >= 0 else -.08), f"{vv:.2f}", ha="center", fontsize=8)
ax.axhline(0, color=GRAY, lw=1); ax.axhline(-.5, color=GRAY, ls=":", lw=1); ax.text(3.45, -.47, "−0.5", color=GRAY, fontsize=9)
ax.set_xticks(xx); ax.set_xticklabels([s for _, s in KINDS]); ax.set_ylabel("1か月ずらしの自己相関（平均）")
ax.legend(frameon=False, loc="lower left"); ax.set_title("差分しすぎた系列は、1か月ずらしの自己相関が −0.5 に近づく")
save(fig, "a749_acf.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
