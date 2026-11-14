"""735 ユニークな人数を近似の関数で数えると、件数の少ない区分でどれだけずれるのか

架空のアクセスログ。区分（ページの種類など）は40個で、区分ごとのユニークな人数は 3人〜40,000人と大きく違う。
1人あたりのアクセス回数は1〜20回。
DuckDB の COUNT(DISTINCT) と approx_count_distinct（HyperLogLog という近似）を区分ごとに比べる。
あわせて、HyperLogLog の考え方を Python で小さく作り、レジスタの数 m を変えたときの誤差を2,000回の試行で数える。
DuckDB は1スレッド。結果は DuckDB の版で変わることがある。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空のアクセスログ（作成者が乱数で作成、seed 735）"
rng = np.random.default_rng(735)
K = 40
sizes = np.unique(np.round(np.geomspace(3, 40000, K)).astype(int))
while len(sizes) < K:
    sizes = np.unique(np.append(sizes, sizes.max() + len(sizes)))
rows_seg, rows_user = [], []
uid0 = 1
for k, s in enumerate(sizes):
    users = rng.choice(np.arange(1, 300001), size=s, replace=False)    # 区分をまたいで同じ人がいる
    visits = rng.integers(1, 21, size=s)
    rows_seg.append(np.repeat(k + 1, visits.sum())); rows_user.append(np.repeat(users, visits))
L = pd.DataFrame({"segment": np.concatenate(rows_seg), "user_id": np.concatenate(rows_user)})
L = L.sample(frac=1, random_state=735).reset_index(drop=True)
DATA.mkdir(exist_ok=True)
L.head(20000).to_csv(DATA / "access_log_head.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("access_log", L)
qs = [q for q in ("\n".join(l for l in (SQL / "02_approx_duckdb.sql").read_text(encoding="utf-8").splitlines()
                            if not l.strip().startswith("--"))).split(";") if q.strip()]
S = con.execute(qs[0]).df()
tot_exact, tot_approx = con.execute(qs[1]).fetchone()
ex_py = L.groupby("segment").user_id.nunique()
assert (S.set_index("segment").exact_users == ex_py).all() and tot_exact == L.user_id.nunique()
S["rel_err"] = S.approx_users / S.exact_users - 1
S["abs_err"] = S.approx_users - S.exact_users
S.to_csv(RES / "by_segment.csv", index=False)

small = S[S.exact_users < 100]; big = S[S.exact_users >= 10000]


# HyperLogLog の考え方（Python の小さな実装）
def hll(ids, p, salt):
    m = 1 << p
    h = (ids.astype(np.uint64) * np.uint64(0x9E3779B97F4A7C15) + np.uint64(salt)) & np.uint64(0xFFFFFFFFFFFFFFFF)
    h ^= h >> np.uint64(33); h *= np.uint64(0xff51afd7ed558ccd); h ^= h >> np.uint64(33)
    idx = (h >> np.uint64(64 - p)).astype(np.int64)
    w = (h << np.uint64(p)) | np.uint64(1 << (p - 1))
    rho = np.zeros(len(w), dtype=np.int64)
    ww = w.copy()
    lz = np.zeros(len(w), dtype=np.int64)
    for b in range(63, -1, -1):
        bit = (ww >> np.uint64(b)) & np.uint64(1)
        lz += np.where((rho == 0) & (bit == 0), 1, 0)
        rho = np.where((rho == 0) & (bit == 1), 1, rho)
    reg = np.zeros(m, dtype=np.int64); np.maximum.at(reg, idx, lz + 1)
    alpha = 0.7213 / (1 + 1.079 / m)
    E = alpha * m * m / np.sum(2.0 ** -reg)
    V = np.sum(reg == 0)
    if E <= 2.5 * m and V > 0:
        E = m * np.log(m / V)          # 少ないときの補正
    return E


trials = []
for p in [4, 6, 8, 10, 12]:
    for n in [30, 1000, 30000]:
        errs = []
        for t in range(200):
            ids = rng.choice(10 ** 9, size=n, replace=False)
            errs.append(hll(ids, p, t) / n - 1)
        errs = np.array(errs)
        trials.append(dict(p=p, m=1 << p, n=n, rmse=float(np.sqrt(np.mean(errs ** 2))), theory=1.04 / np.sqrt(1 << p),
                           p90_abs=float(np.quantile(np.abs(errs), .9))))
T = pd.DataFrame(trials); T.to_csv(RES / "hll_trials.csv", index=False)

out = {"segments": int(K), "rows": int(len(L)), "users_min": int(S.exact_users.min()), "users_max": int(S.exact_users.max()),
       "total_exact": int(tot_exact), "total_approx": int(tot_approx), "total_rel_err": float(tot_approx / tot_exact - 1),
       "sum_seg_exact": int(S.exact_users.sum()), "sum_seg_approx": int(S.approx_users.sum()),
       "max_abs_rel_err": float(S.rel_err.abs().max()),
       "max_abs_rel_err_segment_users": int(S.loc[S.rel_err.abs().idxmax(), "exact_users"]),
       "small_lt100_n": int(len(small)), "small_lt100_max_abs_err_people": int(small.abs_err.abs().max()),
       "small_lt100_max_abs_rel_err": float(small.rel_err.abs().max()), "small_lt100_exact_hits": int((small.abs_err == 0).sum()),
       "big_ge10000_n": int(len(big)), "big_ge10000_max_abs_rel_err": float(big.rel_err.abs().max()),
       "big_ge10000_max_abs_err_people": int(big.abs_err.abs().max()),
       "median_abs_rel_err": float(S.rel_err.abs().median()),
       "hll_trials": trials, "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a735_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：区分の人数と相対誤差
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.scatter(S.exact_users, S.rel_err * 100, color=BLUE, s=28, zorder=3)
ax.axhline(0, color=GRAY, lw=1)
ax.set_xscale("log"); ax.set_xlabel("区分の本当のユニーク人数（対数の目盛り）"); ax.set_ylabel("近似のずれ（%）")
ax.set_title(f"近似のずれは、%で見ると区分の大きさによらず数%以内（{K}区分）")
save(fig, "a735_rel_err.png", SRC)

# 図2：人数で見たずれ
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.bar(np.arange(len(S)), S.abs_err, color=np.where(S.abs_err >= 0, ORANGE, BLUE))
ax.axhline(0, color=GRAY, lw=1)
ax.set_xticks(np.arange(0, len(S), 5)); ax.set_xticklabels([f"{v:,}" for v in S.exact_users.iloc[::5]], fontsize=8)
ax.set_xlabel("区分（本当のユニーク人数の小さい順）"); ax.set_ylabel("近似 − 正確（人）")
ax.set_yscale("symlog", linthresh=1)
ax.set_title("人数で見ると、小さな区分は0〜数人、大きな区分は数百〜千人あまりずれる")
save(fig, "a735_abs_err.png", SRC)

# 図3：HyperLogLog の誤差とレジスタの数
fig, ax = plt.subplots(figsize=(9, 4.6))
for n, c in zip([30, 1000, 30000], [LIGHT, BLUE, ORANGE]):
    d = T[T.n == n]; ax.plot(d.m, d.rmse * 100, "o-", color=c, label=f"本当の人数 {n:,}人")
ax.plot(T[T.n == 30].m, T[T.n == 30].theory * 100, "--", color=GRAY, label="目安 1.04/√m")
ax.set_xscale("log", base=2); ax.set_xlabel("レジスタの数 m（メモリの大きさ）"); ax.set_ylabel("誤差の大きさ（RMSE、%）")
ax.legend(frameon=False); ax.set_title("自作の HyperLogLog：m を4倍にすると誤差はおよそ半分（各200回）")
save(fig, "a735_hll_m.png", SRC)
print(json.dumps({k: v for k, v in out.items() if k != "hll_trials"}, ensure_ascii=False, indent=1))
print(T)
