"""748 ある日に「利用中」の会員だけに聞くと、平均の利用期間は本当の何倍に見えるのか

架空の会員。入会は2010〜2029年の20年間に一様に起き、利用期間（入会から退会まで、月）は分布から決める。
2025年1月1日に「利用中」の会員だけを見て、その人たちの利用期間（退会までの全体）の平均を、入会した人全員の平均と比べる。
長く使う人ほど、ある日に利用中である確率が高い（長さに比例して選ばれる）。
分布は4つ（平均はどれも12か月）：
  一定（全員12か月）、ガンマ（形4）、指数、対数正規（ばらつき大）
補正として、利用中の人を「利用期間の逆数」で重みづけした平均も出す。
各分布で入会20万人。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 748）"
rng = np.random.default_rng(748)
N, MEAN = 200_000, 12.0
DAY = 15 * 12.0                       # 2010年1月から数えて、2025年1月（月）
start = rng.uniform(0, 20 * 12, N)
s_ln = 1.2
dists = {
    "一定": lambda: np.full(N, MEAN),
    "ガンマ（形4）": lambda: rng.gamma(4, MEAN / 4, N),
    "指数": lambda: rng.exponential(MEAN, N),
    "対数正規（ばらつき大）": lambda: rng.lognormal(np.log(MEAN) - s_ln ** 2 / 2, s_ln, N),
}
rows = {}; keep = {}
for name, f in dists.items():
    T = f()
    act = (start <= DAY) & (start + T > DAY)
    w = 1 / T[act]
    elapsed = DAY - start[act]
    theory = np.mean(T ** 2) / np.mean(T)
    rows[name] = dict(all_mean=float(T.mean()), active_n=int(act.sum()), active_mean=float(T[act].mean()),
                      ratio=float(T[act].mean() / T.mean()), theory_ratio=float(theory / T.mean()),
                      weighted_mean=float(np.sum(T[act] * w) / np.sum(w)), elapsed_mean=float(elapsed.mean()),
                      cv=float(T.std() / T.mean()))
    keep[name] = (T, act)
S = pd.DataFrame(rows).T; S.index.name = "distribution"; S.to_csv(RES / "summary.csv")
out = {"joins": N, "survey_month": "2025-01", "true_mean_months": MEAN, "by_distribution": rows,
       "exp_ratio": rows["指数"]["ratio"], "lognormal_ratio": rows["対数正規（ばらつき大）"]["ratio"],
       "gamma_ratio": rows["ガンマ（形4）"]["ratio"], "const_ratio": rows["一定"]["ratio"],
       "exp_weighted": rows["指数"]["weighted_mean"], "lognormal_weighted": rows["対数正規（ばらつき大）"]["weighted_mean"],
       "exp_elapsed": rows["指数"]["elapsed_mean"]}
json.dump(out, open(RES / "a748_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：指数のときの分布
T, act = keep["指数"]
fig, ax = plt.subplots(figsize=(9, 4.6)); bins = np.linspace(0, 72, 49)
ax.hist(T, bins=bins, density=True, color=BLUE, alpha=.6, label=f"入会した人全員（平均 {T.mean():.1f}か月）")
ax.hist(T[act], bins=bins, density=True, color=ORANGE, alpha=.6, label=f"2025年1月に利用中の人（平均 {T[act].mean():.1f}か月）")
ax.set_xlabel("利用期間（入会から退会まで、月）"); ax.set_ylabel("割合（面積で1）"); ax.legend(frameon=False)
ax.set_title("ある日に利用中の人は、長く使う人に偏る（利用期間が指数分布のとき）")
save(fig, "a748_hist.png", SRC)

# 図2：分布ごとの倍率
fig, ax = plt.subplots(figsize=(9, 4.6)); x = np.arange(len(S))
b = ax.bar(x, S.ratio, color=ORANGE)
ax.scatter(x, S.theory_ratio, color=GRAY, zorder=3, marker="_", s=600, label="目安 E[T²]/E[T]²")
for bb, v in zip(b, S.ratio):
    ax.text(bb.get_x() + bb.get_width() / 2, v + .05, f"{v:.2f}倍", ha="center")
ax.axhline(1, color=GRAY, lw=1)
ax.set_xticks(x); ax.set_xticklabels([f"{i}\n（ばらつき係数 {c:.2f}）" for i, c in zip(S.index, S.cv)], fontsize=9)
ax.set_ylabel("利用中の人の平均 ÷ 全員の平均"); ax.legend(frameon=False, loc="upper left")
ax.set_title("利用期間のばらつきが大きいほど、利用中の人の平均は長く見える（本当の平均はどれも12か月）")
save(fig, "a748_ratio.png", SRC)

# 図3：補正
fig, ax = plt.subplots(figsize=(9, 4.6)); w = .27
for j, (c, l, colr) in enumerate([("all_mean", "全員（本当）", BLUE), ("active_mean", "利用中の人だけ", ORANGE), ("weighted_mean", "利用中の人を 1/利用期間 で重みづけ", GREEN)]):
    bb = ax.bar(x + (j - 1) * w, S[c], w, color=colr, label=l)
    for q in bb:
        ax.text(q.get_x() + w / 2, q.get_height() + .4, f"{q.get_height():.1f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(S.index, fontsize=9); ax.set_ylabel("平均の利用期間（月）")
ax.legend(frameon=False, loc="upper left"); ax.set_title("利用期間の逆数で重みづけすると、本当の平均にほぼ戻る")
save(fig, "a748_weighted.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
