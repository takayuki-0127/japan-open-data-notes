"""625 データの先頭1,000行だけで中身を確かめると、後ろにある異常は何%見つかるのか

架空の100万行のファイル（日付順に1年分、1日約2,740行）に、異常な行（列のずれ・空の値など）を1,000行（0.1%）入れる。
異常の入り方は3通り：
  S1 全体にばらばら、S2 最後の1日に固まる（途中で仕様が変わった）、S3 200日目の1日に固まる（一時的な不具合）
確かめ方：先頭 n 行、無作為に n 行、等間隔に n 行（始まりは無作為）、100の区間から n/100 行ずつ無作為に。
n = 1,000〜20,000 で、異常を1行でも見つける確率を出す（無作為は超幾何分布で正確に、等間隔と区間ごとは 2,000回のくり返し、先頭は0か1）。
SQL（DuckDB、1スレッド）で先頭・無作為・区間ごとの取り方を書き、先頭の結果が Python と一致することを確かめる。
数字は置いた異常の入り方で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, SQL, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の100万行のファイル（作成者が乱数で作成、seed 625）"
rng = np.random.default_rng(625)
N, NBAD = 1_000_000, 1_000
PERDAY = N / 365
day_lo = lambda d: int(round((d - 1) * PERDAY)); day_hi = lambda d: int(round(d * PERDAY))
SC = {"S1": rng.choice(N, NBAD, replace=False),
      "S2": day_lo(365) + rng.choice(day_hi(365) - day_lo(365), NBAD, replace=False),
      "S3": day_lo(200) + rng.choice(day_hi(200) - day_lo(200), NBAD, replace=False)}
SCL = {"S1": "全体にばらばら", "S2": "最後の1日に固まる", "S3": "200日目の1日に固まる"}
NS = [1_000, 2_000, 5_000, 10_000, 20_000]
REPS = 2000
METH = ["head", "random", "systematic", "blocks"]
MLAB = {"head": "先頭の n 行", "random": "無作為に n 行", "systematic": "等間隔に n 行", "blocks": "100の区間から同じ数ずつ"}


def found(bad_mask, m, n, rng):
    if m == "head":
        return bool(bad_mask[:n].any())
    if m == "systematic":
        step = N // n
        return bool(bad_mask[rng.integers(0, step) + step * np.arange(n)].any())
    k = n // 100
    idx = (np.arange(100)[:, None] * (N // 100) + rng.integers(0, N // 100, (100, k))).ravel()  # 区間内は重複ありで近似
    return bool(bad_mask[idx].any())


rows = []
for s, pos in SC.items():
    mask = np.zeros(N, bool); mask[pos] = True
    for n in NS:
        for m in METH:
            if m == "random":  # 無作為は超幾何分布で正確に出す
                rows.append({"scenario": s, "n": n, "method": m, "found_pct": 100 * float(stats.hypergeom(N, NBAD, n).sf(0))})
                continue
            reps = 1 if m == "head" else REPS
            hit = sum(found(mask, m, n, rng) for _ in range(reps))
            rows.append({"scenario": s, "n": n, "method": m, "found_pct": 100 * hit / reps})
R = pd.DataFrame(rows)
R.to_csv(RES / "summary.csv", index=False)
# 理論値（無作為）：1 - (1 - 0.001)^n
theory = {n: round(100 * (1 - (1 - NBAD / N) ** n), 2) for n in NS}
need95 = int(np.ceil(np.log(0.05) / np.log(1 - NBAD / N)))

# SQL
mask = np.zeros(N, np.int8); mask[SC["S2"]] = 1
L = pd.DataFrame({"row_no": np.arange(1, N + 1), "bad": mask})
con = duckdb.connect(); con.execute("SET threads=1"); con.register("lines", L)
qs = [q.strip() for q in (SQL / "02_sample_check_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in q]
sqlv = [con.execute(q[q.index("SELECT"):]).fetchone()[0] for q in qs]
assert sqlv[0] == int(mask[:5000].sum())
pd.DataFrame({"method": ["先頭5,000行", "無作為5,000行（SAMPLE）", "区間ごと50行×100"], "bad_found_S2": sqlv}).to_csv(RES / "sql_example_S2.csv", index=False)

out = {"rows": N, "bad_rows": NBAD, "scenarios": SCL, "reps": REPS, "results": R.to_dict(orient="records"),
       "random_theory_pct": theory, "random_n_for_95pct": need95, "sql_S2_n5000": dict(zip(["head", "sample", "blocks"], [int(v) for v in sqlv]))}
json.dump(out, open(RES / "a625_main.json", "w"), ensure_ascii=False, indent=1)

COL = {"head": ORANGE, "random": BLUE, "systematic": LIGHT, "blocks": GREEN}
# 図1：異常の位置
fig, ax = plt.subplots(3, 1, figsize=(9, 3.6), sharex=True, gridspec_kw={"hspace": 0.6})
for i, s in enumerate(SC):
    ax[i].vlines(SC[s] / 1e4, 0, 1, color=INK, lw=0.3)
    ax[i].axvspan(0, 0.1, color=ORANGE, alpha=0.6)
    ax[i].set_yticks([]); ax[i].set_title(f"{s} {SCL[s]}", fontsize=10, loc="left"); ax[i].set_xlim(0, 100)
ax[2].set_xlabel("ファイルの中の位置（万行目）。橙は先頭1,000行")
save(fig, "a625_positions.png", SRC, y=-0.06)

# 図2：n=5,000 での見つかる確率
fig, ax = plt.subplots(figsize=(9, 4))
w = 0.2; xs = np.arange(3)
for j, m in enumerate(METH):
    v = [R[(R.scenario == s) & (R.n == 1000) & (R.method == m)].found_pct.iloc[0] for s in SC]
    ax.bar(xs + (j - 1.5) * w, v, w, color=COL[m], label=MLAB[m])
    for x, vv in zip(xs + (j - 1.5) * w, v):
        ax.text(x, vv + 1, f"{vv:.0f}", ha="center", fontsize=8)
ax.set_xticks(xs); ax.set_xticklabels([f"{s} {SCL[s]}" for s in SC]); ax.set_ylabel("異常を1行でも見つける確率（%）")
ax.set_ylim(0, 125); ax.legend(frameon=False, fontsize=9, ncol=4, loc="upper center")
ax.set_title("1,000行（0.1%）だけ確かめたとき、異常（全体の0.1%）が見つかる確率")
save(fig, "a625_found_n1000.png", SRC)

# 図3：n ごと（S1 と S3）
fig, ax = plt.subplots(1, 2, figsize=(11, 4), gridspec_kw={"wspace": 0.25})
for i, s in enumerate(["S1", "S3"]):
    for m in METH:
        v = R[(R.scenario == s) & (R.method == m)]
        ax[i].plot(v.n, v.found_pct, marker="o", color=COL[m], label=MLAB[m])
    ax[i].set_xscale("log"); ax[i].set_title(f"{s} {SCL[s]}"); ax[i].set_xlabel("確かめる行数（対数目盛）"); ax[i].set_ylim(-3, 103)
ax[0].set_ylabel("異常を1行でも見つける確率（%）"); ax[1].legend(frameon=False, fontsize=9)
save(fig, "a625_by_n.png", SRC, y=-0.04)
print(R.pivot_table(index=["scenario", "n"], columns="method", values="found_pct")); print(theory, need95, sqlv)
