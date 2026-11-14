"""744 会員番号の偶数と奇数で2群に分けると、番号の振り方によって群の間にどれだけ差が出るのか

架空の会員。番号は2台の受付の仕組みで振る：1台目は奇数、2台目は偶数（交互に振る設定）。
1台目は店頭の受付を80%、2台目はWebの受付を80%受け持つ。店頭で入った会員は、月の購入額の平均が5,000円、Webは4,200円（標準偏差はどちらも3,000円）。
施策はしていない（A/A の比較）。2群の分け方は3つ：
  偶数と奇数
  ハッシュ（番号に実験の名前をつけた文字列のハッシュ）
  無作為
1か月の新しい会員20,000人で、2群の平均の差と t 検定の p 値を出す。これを1,000か月分くり返し、「差あり」（p<0.05）の割合を数える。
比べとして、1台だけで連番を振る場合も同じことをする。
1か月分は DuckDB（1スレッド）でも集計し、偶数・奇数の平均が pandas と一致することを確かめる。
"""
import json
import hashlib
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空の会員（作成者が乱数で作成、seed 744）"
rng = np.random.default_rng(744)
N, R = 20000, 1000


def month(two_servers=True):
    store = rng.random(N) < .5                          # 店頭 or Web
    if two_servers:
        server1 = np.where(store, rng.random(N) < .8, rng.random(N) < .2)
        ids = np.empty(N, dtype=np.int64)
        n1 = server1.sum(); ids[server1] = 2 * np.arange(n1) + 1; ids[~server1] = 2 * np.arange(N - n1) + 2
    else:
        ids = np.arange(1, N + 1)
    spend = np.where(store, 5000, 4200) + rng.standard_normal(N) * 3000
    return ids, store, spend


salt = np.int64(744_000_001)


def hash_grp(ids):
    """番号のハッシュ（splitmix64 の混ぜ方）の最下位ビット"""
    h = (ids.astype(np.uint64) + np.uint64(salt)) * np.uint64(0x9E3779B97F4A7C15)
    h ^= h >> np.uint64(31); h *= np.uint64(0xBF58476D1CE4E5B9); h ^= h >> np.uint64(29)
    return (h & np.uint64(1)).astype(int)


def test(g, y):
    a, b = y[g == 0], y[g == 1]
    return b.mean() - a.mean(), stats.ttest_ind(a, b, equal_var=False).pvalue


rows = []
for two in [True, False]:
    res = {"parity": [], "hash": [], "random": []}
    for r in range(R):
        ids, store, spend = month(two)
        for k, g in [("parity", ids % 2), ("hash", hash_grp(ids)), ("random", rng.integers(0, 2, N))]:
            res[k].append(test(g, spend))
    for k, v in res.items():
        v = np.array(v)
        rows.append(dict(servers=2 if two else 1, method=k, mean_diff=v[:, 0].mean(), sd_diff=v[:, 0].std(),
                         false_positive=(v[:, 1] < .05).mean()))
        if two and k == "parity":
            diffs_parity = v[:, 0]
        if two and k == "hash":
            diffs_hash = v[:, 0]
S = pd.DataFrame(rows); S.to_csv(RES / "summary.csv", index=False)

# 1か月分を CSV に残し、DuckDB で集計
ids, store, spend = month(True)
Mb = pd.DataFrame({"member_id": ids, "channel": np.where(store, "店頭", "Web"), "spend": np.round(spend).astype(int)}).sort_values("member_id").reset_index(drop=True)
DATA.mkdir(exist_ok=True); Mb.to_csv(DATA / "members_one_month.csv", index=False)
con = duckdb.connect(); con.execute("SET threads=1"); con.register("members", Mb)
q = "\n".join(l for l in (SQL / "02_split_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
Q = con.execute(q).df()
pm = Mb.groupby(Mb.member_id % 2).spend.mean()
qp = Q[Q.method == "parity"].set_index("grp").mean_spend
assert np.allclose(qp.sort_index().to_numpy(), pm.sort_index().to_numpy())
Q.to_csv(RES / "one_month_duckdb.csv", index=False)
ch = pd.crosstab(Mb.member_id % 2, Mb.channel, normalize="index")
g = lambda s, m, c: float(S[(S.servers == s) & (S.method == m)][c].iloc[0])
out = {"members_per_month": N, "months": R,
       "two_servers": {m: {"mean_diff": round(g(2, m, "mean_diff"), 1), "false_positive": g(2, m, "false_positive")} for m in ["parity", "hash", "random"]},
       "one_server": {m: {"mean_diff": round(g(1, m, "mean_diff"), 1), "false_positive": g(1, m, "false_positive")} for m in ["parity", "hash", "random"]},
       "one_month_odd_store_share": float(ch.loc[1, "店頭"]), "one_month_even_store_share": float(ch.loc[0, "店頭"]),
       "one_month_parity_diff": float(pm[1] - pm[0]),
       "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a744_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：番号の偶奇と受付の経路
fig, ax = plt.subplots(figsize=(9, 4.4))
x = np.arange(2)
ax.bar(x, [ch.loc[1, "店頭"] * 100, ch.loc[0, "店頭"] * 100], color=ORANGE, label="店頭で入った会員")
ax.bar(x, [ch.loc[1, "Web"] * 100, ch.loc[0, "Web"] * 100], bottom=[ch.loc[1, "店頭"] * 100, ch.loc[0, "店頭"] * 100], color=BLUE, label="Web で入った会員")
for i, v in enumerate([ch.loc[1, "店頭"], ch.loc[0, "店頭"]]):
    ax.text(i, v * 50, f"{v * 100:.0f}%", ha="center", color="white", fontsize=12)
ax.set_xticks(x); ax.set_xticklabels(["奇数の番号（1台目）", "偶数の番号（2台目）"]); ax.set_ylabel("割合（%）")
ax.legend(frameon=False, loc="upper right", bbox_to_anchor=(1.0, 1.15), ncol=2)
ax.set_title("番号の偶奇が、受付の経路とつながっている（1か月分）", pad=28)
save(fig, "a744_channel_mix.png", SRC)

# 図2：差の分布
fig, ax = plt.subplots(figsize=(9, 4.6))
bins = np.linspace(-200, 700, 61)
ax.hist(diffs_hash, bins=bins, color=BLUE, alpha=.7, label="ハッシュで分ける")
ax.hist(diffs_parity, bins=bins, color=ORANGE, alpha=.7, label="偶数と奇数で分ける")
ax.axvline(0, color=GRAY, ls="--")
ax.set_xlabel("2群の平均の差（円、奇数−偶数、施策なし）"); ax.set_ylabel("月の数"); ax.legend(frameon=False)
ax.set_title(f"施策をしていないのに、偶数と奇数では平均{g(2, 'parity', 'mean_diff'):.0f}円の差が出る（1,000か月）")
save(fig, "a744_diff_hist.png", SRC)

# 図3：「差あり」の割合
fig, ax = plt.subplots(figsize=(9, 4.6))
labs = {"parity": "偶数と奇数", "hash": "ハッシュ", "random": "無作為"}
x = np.arange(3); w = .38
for j, (sv, l, c) in enumerate([(2, "受付2台で交互に番号", ORANGE), (1, "1台で連番", BLUE)]):
    v = [g(sv, m, "false_positive") * 100 for m in labs]
    b = ax.bar(x + (j - .5) * w, v, w, color=c, label=l)
    for bb in b:
        ax.text(bb.get_x() + w / 2, bb.get_height() + 1.5, f"{bb.get_height():.1f}%", ha="center", fontsize=9)
ax.axhline(5, color=GRAY, ls="--", lw=1)
ax.set_xticks(x); ax.set_xticklabels(list(labs.values())); ax.set_ylabel("「差あり」（p<0.05）の割合（%）"); ax.set_ylim(0, 115)
ax.legend(frameon=False, loc="upper right"); ax.set_title("番号の振り方しだいで、偶奇の分け方は毎月「差あり」になる")
save(fig, "a744_false_positive.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
