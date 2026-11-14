"""699 構造変化の時点をグラフを見てから決めて検定すると、変化がなくても何%で「変化あり」になるのか

架空の月次の系列（変化なし）：y_t = 100 + e_t。e は独立な正規（標準偏差5）か、AR(1)（係数0.5）。
水準が1回だけ変わるかを Chow 検定（F、5%）で調べる。時点の決め方を3通り比べる。
1. 前もって決めた時点（真ん中）で Chow 検定
2. グラフを見て「いちばん変わって見える時点」を選ぶ：端15%を除いた全時点で F が最大の時点を選び、ふつうの F の基準で判定
3. sup F：2と同じ最大の F を、「最大を選んだ」ことを考えた基準（変化なしの系列で作った95%点）で判定
長さ T＝60・120・240、各5,000回。seed 699。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の月次の系列（作成者が乱数で作成、seed 699）"
rng = np.random.default_rng(699)
TS = [60, 120, 240]
REPS = 5000
TRIM = 0.15


def gen(T, phi, reps):
    e = rng.normal(0, 5, (reps, T))
    if phi:
        for t in range(1, T): e[:, t] += phi * e[:, t - 1]
    return 100 + e


def fprofile(Y):
    """各時点 k（k 以降で水準が変わる）の Chow の F。端 TRIM を除く"""
    reps, T = Y.shape
    lo, hi = int(np.ceil(TRIM * T)), int(np.floor((1 - TRIM) * T))
    ks = np.arange(lo, hi + 1)
    cs = np.cumsum(Y, 1); tot = cs[:, -1:]; ss = (Y ** 2).sum(1, keepdims=True)
    rss0 = ss[:, 0] - tot[:, 0] ** 2 / T
    s1 = cs[:, ks - 1]; n1 = ks; s2 = tot - s1; n2 = T - ks
    rss1 = ss - s1 ** 2 / n1 - s2 ** 2 / n2
    F = (rss0[:, None] - rss1) / (rss1 / (T - 2))
    return ks, F


crit_F = {T: stats.f.ppf(0.95, 1, T - 2) for T in TS}
crit_sup = {}
for T in TS:  # 変化なし・独立な誤差で sup F の95%点を作る
    _, F0 = fprofile(gen(T, 0, 20000)); crit_sup[T] = float(np.quantile(F0.max(1), 0.95))

rows = []
for phi in [0, 0.5]:
    for T in TS:
        Y = gen(T, phi, REPS); ks, F = fprofile(Y)
        mid = np.where(ks == T // 2)[0][0]
        rows.append({"phi": phi, "T": T,
                     "pre": (F[:, mid] > crit_F[T]).mean() * 100,
                     "post_hoc": (F.max(1) > crit_F[T]).mean() * 100,
                     "supF": (F.max(1) > crit_sup[T]).mean() * 100,
                     "crit_F": crit_F[T], "crit_sup": crit_sup[T]})
S = pd.DataFrame(rows); S.round(3).to_csv(RES / "summary.csv", index=False)


def g(phi, T, c):
    return round(float(S[(S.phi == phi) & (S["T"] == T)][c].iloc[0]), 1)


out = {"reps": REPS, "trim": TRIM, "crit_F": {str(T): round(crit_F[T], 2) for T in TS}, "crit_sup": {str(T): round(crit_sup[T], 2) for T in TS},
       "iid": {str(T): {"pre": g(0, T, "pre"), "post_hoc": g(0, T, "post_hoc"), "supF": g(0, T, "supF")} for T in TS},
       "ar05": {str(T): {"pre": g(0.5, T, "pre"), "post_hoc": g(0.5, T, "post_hoc"), "supF": g(0.5, T, "supF")} for T in TS}}

# 図1：1本の例
T = 120
Yex = gen(T, 0, 200); ks, Fex = fprofile(Yex)
ix = int(np.where((Fex.max(1) > crit_F[T]) & (Fex.max(1) < crit_sup[T]))[0][0])  # ふつうの基準は超え、sup F の基準は超えない最初の1本
y = Yex[ix]; F = Fex[ix]; kb = ks[F.argmax()]
out["example"] = {"index": ix, "k": int(kb), "F": round(float(F.max()), 2), "p_naive": round(float(stats.f.sf(F.max(), 1, T - 2)), 4),
                  "mean_before": round(float(y[:kb].mean()), 2), "mean_after": round(float(y[kb:].mean()), 2)}
json.dump(out, open(RES / "a699_main.json", "w"), ensure_ascii=False, indent=1)
fig, axes = plt.subplots(2, 1, figsize=(9, 5.4), sharex=True, gridspec_kw={"height_ratios": [1.3, 1]})
axes[0].plot(np.arange(T), y, color=GRAY, lw=1)
axes[0].hlines([y[:kb].mean(), y[kb:].mean()], [0, kb], [kb, T - 1], color=ORANGE, lw=2)
axes[0].axvline(kb, color=ORANGE, ls=":"); axes[0].set_ylabel("値")
axes[0].set_title(f"変化のない系列でも、{kb}か月目で「変わって見える」（前 {y[:kb].mean():.1f} → 後 {y[kb:].mean():.1f}）")
axes[1].plot(ks, F, color=BLUE); axes[1].axhline(crit_F[T], color=INK, ls="--", lw=0.8, label=f"ふつうの F の基準 {crit_F[T]:.2f}")
axes[1].axhline(crit_sup[T], color=GREEN, ls="--", lw=0.8, label=f"sup F の基準 {crit_sup[T]:.2f}")
axes[1].set_ylabel("Chow の F"); axes[1].set_xlabel("変化の時点（か月目）"); axes[1].legend(frameon=False, fontsize=9)
save(fig, "a699_example.png", SRC)

# 図2：決め方ごとの「変化あり」の割合（T=120）
fig, ax = plt.subplots(figsize=(8.5, 3.8)); x = np.arange(3); w = 0.38
labs = ["前もって決めた時点", "いちばん変わって見える\n時点を選ぶ", "sup F（選んだことを\n考えた基準）"]
for k, (phi, c, nm) in enumerate([(0, BLUE, "誤差が独立"), (0.5, ORANGE, "誤差が前の月に引きずられる（AR 0.5）")]):
    v = [g(phi, 120, c_) for c_ in ["pre", "post_hoc", "supF"]]
    ax.bar(x + (k - 0.5) * w, v, w, color=c, label=nm)
    for i in range(3): ax.text(x[i] + (k - 0.5) * w, v[i] + 1, f"{v[i]:.1f}%", ha="center", fontsize=9)
ax.axhline(5, color=INK, ls=":", lw=0.8); ax.set_xticks(x); ax.set_xticklabels(labs); ax.set_ylabel("「変化あり」の割合（%）")
ax.set_title("変化のない120か月の系列で、「変化あり」と言った割合"); ax.legend(frameon=False, fontsize=9)
save(fig, "a699_false_rate.png", SRC)

# 図3：長さごと（誤差が独立）
fig, ax = plt.subplots(figsize=(8, 3.6))
for c_, col, nm in [("pre", BLUE, "前もって決めた時点"), ("post_hoc", ORANGE, "いちばん変わって見える時点を選ぶ"), ("supF", GREEN, "sup F")]:
    v = [g(0, T, c_) for T in TS]; ax.plot(TS, v, marker="o", color=col, label=nm)
    for T_, vv in zip(TS, v): ax.text(T_, vv + 1.2, f"{vv:.1f}", ha="center", fontsize=8.5, color=col)
ax.axhline(5, color=INK, ls=":", lw=0.8); ax.set_xticks(TS); ax.set_xlabel("系列の長さ（か月）"); ax.set_ylabel("「変化あり」の割合（%）")
ax.set_ylim(0, max(S.post_hoc) * 1.2); ax.legend(frameon=False, fontsize=9)
ax.set_title("長さを変えても、選んだ時点で検定すると3割以上が「変化あり」（誤差が独立）")
save(fig, "a699_by_length.png", SRC)
print(json.dumps(out, ensure_ascii=False))
