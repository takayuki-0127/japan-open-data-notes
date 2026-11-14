"""677 多腕バンディットと固定の A/B テストでは、失う申込みの数と、正しい案を選ぶ割合はどう違うのか

架空の申込みページの案。来訪は合計 20,000人で、100人ずつ順に来る（200回）。
案の数は 2 と 4。基準の申込み率は 5%。いちばん良い案は 5%×(1+伸び)、伸びは 5%・10%・20%。
  2案：[5%, 5%×(1+伸び)]
  4案：[5%, 5%, 5%×(1+伸び/2), 5%×(1+伸び)]
方法は3つ：
  A/B：最初の 10,000人を案に均等に分け、残り 10,000人は申込み率がいちばん高かった案に出す
  トンプソン抽出：各案の申込み率に Beta(1,1) を置き、来訪者ごとに事後分布から1つずつ引いて、いちばん大きい案に出す（事後は100人ごとに更新）
  ε-greedy：100人のうち 10% は案に均等、90% はその時点で申込み率がいちばん高い案に出す
失った申込み＝「全員にいちばん良い案を出した場合」との申込み率の差の合計（期待値）。
正しく選んだ割合＝最後に選んだ案（A/B は残りに出した案、ほかは最後の時点で申込み率の推定がいちばん高い案）がいちばん良い案だった割合。
各設定 400 回。数字は置いた申込み率で決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の申込みページの案（作成者が乱数で作成、seed 677）"
rng = np.random.default_rng(677)
P0, TOTAL, BATCH, REPS, EPS = 0.05, 20_000, 100, 400, 0.10
NB = TOTAL // BATCH
LIFTS, KS = [0.05, 0.10, 0.20], [2, 4]
METHODS = ["A/B", "トンプソン抽出", "ε-greedy"]
COL = {"A/B": GRAY, "トンプソン抽出": BLUE, "ε-greedy": ORANGE}


def arms(k, lift):
    return np.array([P0, P0 * (1 + lift)]) if k == 2 else np.array([P0, P0, P0 * (1 + lift / 2), P0 * (1 + lift)])


def run(method, p, track=False):
    k = len(p); n = np.zeros((REPS, k)); s = np.zeros((REPS, k))
    share_best = []
    for b in range(NB):
        if method == "A/B":
            if b < NB // 2:
                alloc = np.full((REPS, k), BATCH / k)
            else:
                if b == NB // 2:
                    choice = np.argmax(s / n, axis=1)
                alloc = np.zeros((REPS, k)); alloc[np.arange(REPS), choice] = BATCH
        elif method == "トンプソン抽出":
            draws = rng.beta(1 + s[:, None, :], 1 + n[:, None, :] - s[:, None, :], (REPS, BATCH, k))
            pick = draws.argmax(axis=2)
            alloc = np.stack([(pick == j).sum(axis=1) for j in range(k)], axis=1).astype(float)
        else:
            if b == 0:
                alloc = np.full((REPS, k), BATCH / k)
            else:
                rate = s / np.maximum(n, 1)
                best = np.argmax(rate + rng.random((REPS, k)) * 1e-9, axis=1)
                alloc = np.full((REPS, k), BATCH * EPS / k); alloc[np.arange(REPS), best] += BATCH * (1 - EPS)
        alloc_i = alloc.astype(int)
        conv = rng.binomial(alloc_i, p[None, :])
        n += alloc_i; s += conv
        if track:
            share_best.append(alloc_i[:, -1].mean() / BATCH)
    lost = ((p.max() - p)[None, :] * n).sum(axis=1)
    final = choice if method == "A/B" else np.argmax((1 + s) / (2 + n), axis=1)
    correct = final == k - 1
    return lost, correct, n, np.array(share_best)


rows = []; tracks = {}
for k in KS:
    for lift in LIFTS:
        p = arms(k, lift)
        for m in METHODS:
            track = (k == 4 and lift == 0.10)
            lost, correct, n, sb = run(m, p, track)
            if track:
                tracks[m] = sb
            rows.append(dict(k=k, lift=lift, method=m, lost_mean=lost.mean(), lost_p90=np.percentile(lost, 90),
                             correct_pct=100 * correct.mean(), best_share_pct=100 * (n[:, -1] / TOTAL).mean(),
                             max_lost=(p.max() - p.min()) * TOTAL))
S = pd.DataFrame(rows)
S.round(3).to_csv(RES / "summary.csv", index=False)


def g(k, lift, m, col, nd=1):
    return round(float(S[(S.k == k) & (S.lift == lift) & (S.method == m)][col].iloc[0]), nd)


out = {"total": TOTAL, "batch": BATCH, "reps": REPS, "eps": EPS,
       "lost": {f"{k}案_{int(l * 100)}%": {m: g(k, l, m, "lost_mean") for m in METHODS} for k in KS for l in LIFTS},
       "correct_pct": {f"{k}案_{int(l * 100)}%": {m: g(k, l, m, "correct_pct") for m in METHODS} for k in KS for l in LIFTS},
       "best_share_pct": {f"{k}案_{int(l * 100)}%": {m: g(k, l, m, "best_share_pct") for m in METHODS} for k in KS for l in LIFTS},
       "track_4arms_10pct_last_batch_best_share": {m: round(float(tracks[m][-1]) * 100, 1) for m in METHODS},
       "track_4arms_10pct_mid_best_share": {m: round(float(tracks[m][NB // 2 - 1]) * 100, 1) for m in METHODS}}
json.dump(out, open(RES / "a677_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：4案・伸び10%で、いちばん良い案に出した人の割合の推移
fig, ax = plt.subplots(figsize=(9, 4.6))
xs = (np.arange(NB) + 1) * BATCH
for m in METHODS:
    ax.plot(xs, 100 * tracks[m], color=COL[m], lw=2, label=m)
ax.axhline(25, color=GRAY, lw=.8, ls=":"); ax.text(20000, 21, "均等（25%）", ha="right", fontsize=9, color=GRAY)
ax.set_xlabel("来訪者の累計（人）"); ax.set_ylabel("いちばん良い案に出した割合（%、400回の平均）")
ax.set_ylim(0, 100); ax.legend(frameon=False, loc="upper left")
ax.set_title("4案・いちばん良い案は+10%：バンディットは途中から良い案に寄せる")
save(fig, "a677_allocation.png", SRC)

# 図2：失った申込み
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
x = np.arange(len(LIFTS)); w = .26
for ax, k in zip(axes, KS):
    for i, m in enumerate(METHODS):
        vals = [g(k, l, m, "lost_mean") for l in LIFTS]
        bars = ax.bar(x + (i - 1) * w, vals, w, color=COL[m], label=m)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.0f}", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels([f"+{int(l * 100)}%" for l in LIFTS])
    ax.set_xlabel("いちばん良い案の伸び"); ax.set_title(f"{k}案", fontsize=11)
axes[0].set_ylabel("失った申込み（件、2万人あたり・期待値）")
axes[0].legend(frameon=False, loc="upper left", fontsize=9)
fig.suptitle("失う申込みは、差が大きいほどバンディットの方が少ない", fontsize=12)
save(fig, "a677_lost.png", SRC)

# 図3：正しく選んだ割合
fig, axes = plt.subplots(1, 2, figsize=(10, 4.4), sharey=True)
for ax, k in zip(axes, KS):
    for i, m in enumerate(METHODS):
        vals = [g(k, l, m, "correct_pct") for l in LIFTS]
        bars = ax.bar(x + (i - 1) * w, vals, w, color=COL[m], label=m)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.0f}", ha="center", fontsize=8.5)
    ax.axhline(100 / k, color=INK, lw=.8, ls=":")
    ax.set_xticks(x); ax.set_xticklabels([f"+{int(l * 100)}%" for l in LIFTS])
    ax.set_xlabel("いちばん良い案の伸び"); ax.set_title(f"{k}案（点線はあてずっぽう {100 // k}%）", fontsize=11)
axes[0].set_ylabel("最後にいちばん良い案を選んだ割合（%）"); axes[0].set_ylim(0, 118)
axes[1].legend(frameon=False, loc="upper left", fontsize=9, ncol=3)
fig.suptitle("正しい案を選ぶ割合", fontsize=12)
save(fig, "a677_correct.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
