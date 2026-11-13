"""638 主成分の数を「固有値1以上」「累積80%」「並行分析」で選ぶと、本当の数を何%で当てるのか

本当の因子の数 k（1〜6）が分かっている架空のデータ（変数20個、件数300）を作り、相関行列の固有値から
  K1 固有値1以上の数（カイザー基準）
  C80 累積寄与率が80%に届くまでの数
  PA 並行分析（同じ大きさの乱数データ50組の固有値の95%点を超える数）
で主成分の数を選び、本当の k と一致する割合を数える。各条件200回。
因子の効き（負荷量）を 0.4・0.6・0.8 に変える。各変数は1つの因子だけに載る（20個を k 個に均等に割り振る）。
数字は置いた因子の数・負荷量・件数で決まる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 638）"
rng = np.random.default_rng(638)
P, N, REPS, NPA = 20, 300, 200, 50


def draw(k, lam, n=N):
    F = rng.standard_normal((n, k))
    grp = np.arange(P) % k
    X = F[:, grp] * lam + rng.standard_normal((n, P)) * np.sqrt(1 - lam ** 2)
    return X


def eig_desc(X):
    return np.sort(np.linalg.eigvalsh(np.corrcoef(X, rowvar=False)))[::-1]


# 並行分析の基準（件数・変数の数が同じなので、乱数データの固有値の95%点は共通に作っておく）
rand = np.array([eig_desc(rng.standard_normal((N, P))) for _ in range(NPA * 20)])
pa95 = np.quantile(rand, 0.95, axis=0)


def choose(ev):
    k1 = int((ev > 1).sum())
    c80 = int(np.searchsorted(np.cumsum(ev) / ev.sum(), 0.8) + 1)
    pa = 0
    for i in range(P):
        if ev[i] > pa95[i]:
            pa += 1
        else:
            break
    return {"K1": k1, "C80": c80, "PA": pa}


rows = []
for lam in [0.4, 0.6, 0.8]:
    for k in range(1, 7):
        for r in range(REPS):
            c = choose(eig_desc(draw(k, lam)))
            rows.append({"lam": lam, "k": k, "rep": r, **c})
D = pd.DataFrame(rows)
D.to_csv(RES / "choices.csv", index=False)
M = ["K1", "C80", "PA"]
hit = D.groupby(["lam", "k"]).apply(lambda g: pd.Series({m: (g[m] == g.k).mean() * 100 for m in M})).round(1)
over = D.groupby(["lam", "k"]).apply(lambda g: pd.Series({m: (g[m] > g.k).mean() * 100 for m in M})).round(1)
under = D.groupby(["lam", "k"]).apply(lambda g: pd.Series({m: (g[m] < g.k).mean() * 100 for m in M})).round(1)
med = D.groupby(["lam", "k"])[M].median()
hit.to_csv(RES / "hit_rate.csv"); over.to_csv(RES / "over_rate.csv"); under.to_csv(RES / "under_rate.csv"); med.to_csv(RES / "median_choice.csv")
avg = D.assign(**{f"hit_{m}": D[m] == D.k for m in M}).groupby("lam")[[f"hit_{m}" for m in M]].mean().mul(100).round(1)
avg.to_csv(RES / "hit_rate_by_loading.csv")
out = {"p": P, "n": N, "reps": REPS, "pa_random_sets": NPA * 20,
       "pa95_first3": [round(float(x), 3) for x in pa95[:3]],
       "hit_by_loading": avg.to_dict(orient="index"),
       "hit_lam06": hit.loc[0.6].to_dict(orient="index"),
       "median_choice_lam06": med.loc[0.6].to_dict(orient="index"),
       "hit_lam04": hit.loc[0.4].to_dict(orient="index"),
       "median_choice_lam04": med.loc[0.4].to_dict(orient="index"),
       "hit_lam08": hit.loc[0.8].to_dict(orient="index")}
json.dump(out, open(RES / "a638_main.json", "w"), ensure_ascii=False, indent=1, default=float)

lab = {"K1": "固有値1以上", "C80": "累積80%", "PA": "並行分析"}
col = {"K1": ORANGE, "C80": GRAY, "PA": BLUE}
# 図1：負荷量0.6で本当の数ごとの当たる割合
fig, ax = plt.subplots(figsize=(8.5, 4))
x = np.arange(1, 7); w = 0.26
for i, m in enumerate(M):
    v = hit.loc[0.6][m].values
    ax.bar(x + (i - 1) * w, v, w, color=col[m], label=lab[m])
ax.set_xticks(x); ax.set_xticklabels([f"{k}個" for k in x]); ax.set_xlabel("本当の因子の数")
ax.set_ylabel("本当の数を当てた割合（%）"); ax.set_ylim(0, 105); ax.legend(frameon=False, ncol=3, fontsize=9)
ax.set_title("負荷量0.6：並行分析はほぼ当て、累積80%は大きく外す（変数20・300件、各200回）")
save(fig, "a638_hit_by_k.png", SRC)

# 図2：選んだ数の中央値（負荷量 0.4・0.6・0.8）
fig, ax = plt.subplots(1, 3, figsize=(11, 3.7), sharey=True, gridspec_kw={"wspace": 0.12})
for a_, lam in zip(ax, [0.4, 0.6, 0.8]):
    for m in M:
        a_.plot(x, med.loc[lam][m].values, marker="o", color=col[m], label=lab[m])
    a_.plot([1, 6], [1, 6], color=INK, lw=0.8, ls="--")
    a_.set_title(f"負荷量 {lam}", fontsize=11); a_.set_xlabel("本当の因子の数"); a_.set_xticks(x)
ax[0].set_ylabel("選んだ数（中央値）"); ax[0].legend(frameon=False, fontsize=8)
save(fig, "a638_median_choice.png", SRC, y=-0.06)

# 図3：例の1回の固有値と並行分析の線（k=3, 負荷量0.6）
ev = eig_desc(draw(3, 0.6))
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(range(1, P + 1), ev, marker="o", color=INK, label="データの固有値")
ax.plot(range(1, P + 1), pa95, color=BLUE, ls="--", label="乱数データの固有値の95%点（並行分析）")
ax.axhline(1, color=ORANGE, lw=1, label="固有値1")
c = choose(ev)
ax.set_xticks(range(1, P + 1)); ax.set_xlabel("主成分の番号"); ax.set_ylabel("固有値"); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"例（本当は3個・負荷量0.6）：固有値1以上は{c['K1']}個、累積80%は{c['C80']}個、並行分析は{c['PA']}個")
save(fig, "a638_scree_example.png", SRC)
out["example"] = c
json.dump(out, open(RES / "a638_main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(out, ensure_ascii=False, indent=1, default=float))
