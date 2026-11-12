"""464 短くしたハッシュをキーにすると、何行から衝突が起き、何行がまちがってつながるのか（架空のキー、seed 464）

ハッシュは SHA-256（hashlib）。16進の先頭から 8桁（32ビット）・12桁（48ビット）・16桁（64ビット）を切り出して使う。
"""
import hashlib
import json
import math
import duckdb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, BLUE, ORANGE, GRAY, LIGHT, GREEN, save

SRC = "架空のキー（作成者が乱数で作成、seed 464）。ハッシュは SHA-256 の先頭を切り出したもの"


def keys(n, seed=464):
    """架空の顧客キー（文字列）。支店コード＋通し番号＋チェック用の文字"""
    rng = np.random.default_rng(seed)
    br = rng.integers(1, 400, n)
    return [f"BR{b:03d}-C{i:09d}" for b, i in zip(br, range(1, n + 1))]


def sha_trunc(ks, bits):
    """SHA-256 の先頭 bits ビットを整数にする"""
    h = np.fromiter((int.from_bytes(hashlib.sha256(k.encode()).digest()[:8], "big") for k in ks), dtype=np.uint64, count=len(ks))
    return h >> np.uint64(64 - bits) if bits < 64 else h


def n_collisions(h):
    """衝突の数：ほかのキーと同じハッシュになったキーの数（行の数 − 違うハッシュの数）と、同じハッシュの組の数"""
    u, c = np.unique(h, return_counts=True)
    return int(len(h) - len(u)), int((c * (c - 1) // 2).sum())


def expected_pairs(n, bits):
    return n * (n - 1) / 2 / 2.0 ** bits


def p_any(n, bits):
    return 1 - math.exp(-expected_pairs(n, bits))


def main():
    res = {}
    rng = np.random.default_rng(464)

    # ---- A. 本物の SHA-256 で数える（1,000万キー。64ビットを1回作り、上のビットを切る） ----
    N = 10_000_000
    ks = keys(N)
    h64 = sha_trunc(ks, 64)
    rows = []
    for bits in [24, 32, 40, 48, 64]:
        h = h64 >> np.uint64(64 - bits) if bits < 64 else h64
        for n in [10_000, 100_000, 1_000_000, 10_000_000]:
            extra, pairs = n_collisions(h[:n])
            rows.append({"ビット": bits, "キーの数": n, "同じハッシュの組（実際）": pairs, "同じハッシュの組（式）": expected_pairs(n, bits),
                         "衝突が1件以上起きる確率（式）%": p_any(n, bits) * 100, "ほかと重なったキー": extra})
    real = pd.DataFrame(rows); real.to_csv(RES / "collisions_sha256.csv", index=False)
    res["sha256"] = {f"{int(r['ビット'])}bit_{int(r['キーの数']):,}": {"実際": int(r["同じハッシュの組（実際）"]), "式": round(r["同じハッシュの組（式）"], 2)}
                     for _, r in real.iterrows() if r["ビット"] in (32, 48, 64)}

    # ---- B. 何行から衝突が起きるか（式）：確率が1%・50%・99%になる行数 ----
    thr = []
    for bits in [32, 48, 64]:
        row = {"ビット": bits}
        for p in [0.01, 0.5, 0.99]:
            row[f"{int(p*100)}%"] = math.sqrt(2 * 2.0 ** bits * -math.log(1 - p))
        thr.append(row)
    thr = pd.DataFrame(thr); thr.to_csv(RES / "rows_until_collision.csv", index=False)
    res["rows_until_collision"] = {str(int(r["ビット"])): {k: float(f"{r[k]:.3g}") for k in ["1%", "50%", "99%"]} for _, r in thr.iterrows()}

    # ---- C. 32ビット：最初の衝突が起きた行数（本物の SHA-256 で、キーの並びを変えて300回） ----
    first = []
    M = 400_000
    for rep in range(300):
        idx = rng.choice(N, M, replace=False)
        h = (h64[idx] >> np.uint64(32))
        # 最初に「前に出たハッシュ」が出た位置
        _, firstpos = np.unique(h, return_index=True)
        dup_mask = np.ones(M, bool); dup_mask[firstpos] = False
        pos = np.flatnonzero(dup_mask)
        first.append(int(pos[0]) + 1 if len(pos) else np.nan)
    first = pd.Series(first)
    first.to_csv(RES / "first_collision_32bit.csv", index=False, header=["最初の衝突が起きた行"])
    res["first_collision_32bit"] = {"中央値": int(first.median()), "10%点": int(first.quantile(0.1)), "90%点": int(first.quantile(0.9)),
                                    "最小": int(first.min()), "式の中央値": round(math.sqrt(2 * 2.0 ** 32 * math.log(2))),
                                    "10万行までに起きた割合%": round(float((first <= 100_000).mean() * 100), 1),
                                    "式：10万行までの確率%": round(p_any(100_000, 32) * 100, 1)}

    # ---- D. 結合：顧客マスタ（ハッシュがキー）と取引の表をつなぐ ----
    con = duckdb.connect(); con.execute("PRAGMA threads=2")
    join_rows = []
    for nk in [100_000, 1_000_000, 5_000_000]:
        key = np.arange(nk)
        h32 = (h64[:nk] >> np.uint64(32)).astype(np.int64); h48 = (h64[:nk] >> np.uint64(16)).astype(np.int64)
        nfact = nk * 3
        fk = rng.integers(0, nk, nfact)
        amount = np.round(rng.lognormal(np.log(3000), 0.8, nfact)).astype(np.int64)
        dim = pd.DataFrame({"cust": key, "h32": h32, "h48": h48})
        fact = pd.DataFrame({"cust": fk, "h32": h32[fk], "h48": h48[fk], "amount": amount})
        con.register("dim", dim); con.register("fact", fact)
        true_rows, true_sum = nfact, int(amount.sum())
        for col, bits in [("h32", 32), ("h48", 48)]:
            r = con.execute(f"""SELECT COUNT(*), SUM(f.amount), SUM(CASE WHEN f.cust <> d.cust THEN 1 ELSE 0 END),
                                       COUNT(DISTINCT CASE WHEN f.cust <> d.cust THEN f.cust END)
                                FROM fact f JOIN dim d ON f.{col} = d.{col}""").fetchone()
            ndim_dup = int(con.execute(f"SELECT COUNT(*) FROM (SELECT {col} FROM dim GROUP BY {col} HAVING COUNT(*) > 1)").fetchone()[0])
            join_rows.append({"マスタのキーの数": nk, "取引の行": nfact, "ビット": bits, "同じハッシュになったキーの組": ndim_dup,
                              "つないだあとの行": int(r[0]), "余分な行": int(r[0]) - true_rows, "別の顧客につながった行": int(r[2]),
                              "金額の合計のずれ%": (int(r[1]) / true_sum - 1) * 100, "まちがってつながった顧客の数": int(r[3])})
        con.unregister("dim"); con.unregister("fact")
    jn = pd.DataFrame(join_rows); jn.to_csv(RES / "join_extra_rows.csv", index=False)
    res["join"] = {f"{int(r['ビット'])}bit_{int(r['マスタのキーの数']):,}": {"組": int(r["同じハッシュになったキーの組"]), "余分な行": int(r["余分な行"]),
                                                             "金額のずれ%": round(r["金額の合計のずれ%"], 4), "顧客": int(r["まちがってつながった顧客の数"])}
                   for _, r in jn.iterrows()}
    # 照合で気づけるか（マスタ500万・32ビット）
    j = jn[(jn["マスタのキーの数"] == 5_000_000) & (jn["ビット"] == 32)].iloc[0]
    res["checks"] = {"行数をぴったり比べる": bool(j["余分な行"] != 0), "金額の合計を0.5%以内で比べる": bool(abs(j["金額の合計のずれ%"]) > 0.5),
                     "マスタのキーが重なっていないかを見る": bool(j["同じハッシュになったキーの組"] > 0),
                     "余分な行の割合%": round(j["余分な行"] / j["取引の行"] * 100, 4)}

    # ---- E. 式の確かめ：一様な乱数のハッシュで、衝突の組の数を200回ずつ ----
    sim = []
    for bits, n in [(32, 100_000), (32, 1_000_000), (32, 5_000_000), (48, 5_000_000)]:
        got = []
        for _ in range(100 if n >= 5_000_000 else 200):
            h = rng.integers(0, 2 ** bits, n, dtype=np.int64)
            got.append(n_collisions(h)[1])
        sim.append({"ビット": bits, "キーの数": n, "組の数の平均（乱数）": float(np.mean(got)), "式": expected_pairs(n, bits),
                    "0件だった回の割合%": float(np.mean(np.array(got) == 0) * 100), "式：0件の確率%": math.exp(-expected_pairs(n, bits)) * 100})
    sim = pd.DataFrame(sim); sim.to_csv(RES / "formula_vs_random.csv", index=False)
    res["formula_vs_random"] = sim.round(3).to_dict("records")
    json.dump(res, open(RES / "a464_main.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))

    # ---- 図 ----
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    ns = np.logspace(3, 10, 200)
    for bits, col in [(32, ORANGE), (48, BLUE), (64, GREEN)]:
        ax.plot(ns, [expected_pairs(n, bits) for n in ns], color=col, label=f"{bits}ビット（式）")
        d = real[(real["ビット"] == bits) & (real["同じハッシュの組（実際）"] > 0)]
        ax.scatter(d["キーの数"], d["同じハッシュの組（実際）"], color=col, zorder=3, s=40, label=f"{bits}ビット（SHA-256 で数えた値）" if len(d) else None)
    ax.axhline(1, color=GRAY, lw=1, ls="--"); ax.text(1.2e3, 1.4, "同じハッシュの組が1つ", fontsize=8.5, color=GRAY)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_ylim(1e-6, 1e8)
    ax.set_xlabel("キーの数（行）"); ax.set_ylabel("同じハッシュになったキーの組の数")
    ax.set_title("キーの数と、同じハッシュになる組の数"); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    save(fig, "a464_pairs_by_rows.png", SRC)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4))
    ax = axes[0]
    ax.hist(first.dropna() / 1000, bins=30, color=BLUE)
    ax.axvline(first.median() / 1000, color=ORANGE); ax.text(first.median() / 1000 + 3, ax.get_ylim()[1] * 0.9, f"中央値 {first.median()/1000:.0f}千行", color=ORANGE, fontsize=9)
    ax.set_xlabel("最初の衝突が起きた行（千行）"); ax.set_ylabel("回数（300回のうち）"); ax.set_title("32ビット：最初の衝突はいつ起きたか")
    ax = axes[1]
    for bits, col in [(32, ORANGE), (48, BLUE), (64, GREEN)]:
        ax.plot(ns, [p_any(n, bits) * 100 for n in ns], color=col, label=f"{bits}ビット")
    ax.set_xscale("log"); ax.set_xlabel("キーの数（行）"); ax.set_ylabel("衝突が1件以上ある確率（%）")
    ax.set_title("衝突が1件以上起きる確率（式）"); ax.legend(frameon=False, loc=(0.02, 0.4))
    save(fig, "a464_first_collision.png", SRC)

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4))
    ax = axes[0]
    d32 = jn[jn["ビット"] == 32]; d48 = jn[jn["ビット"] == 48]
    x = np.arange(len(d32))
    ax.bar(x - 0.2, d32["余分な行"], 0.38, color=ORANGE, label="32ビット"); ax.bar(x + 0.2, d48["余分な行"], 0.38, color=BLUE, label="48ビット")
    for i, (a, b) in enumerate(zip(d32["余分な行"], d48["余分な行"])):
        ax.text(i - 0.2, a + max(d32["余分な行"]) * 0.02, f"{a:,}", ha="center", fontsize=9); ax.text(i + 0.2, b + max(d32["余分な行"]) * 0.02, f"{b:,}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([f"マスタ{n//10000:,}万キー\n取引{m//10000:,}万行" for n, m in zip(d32["マスタのキーの数"], d32["取引の行"])], fontsize=8.5)
    ax.set_ylabel("つないだあとに増えた行"); ax.set_title("ハッシュでつないだとき、余分にできた行"); ax.legend(frameon=False)
    ax = axes[1]
    ax.bar(x, d32["金額の合計のずれ%"], 0.5, color=ORANGE)
    for i, v in enumerate(d32["金額の合計のずれ%"]):
        ax.text(i, v + d32["金額の合計のずれ%"].max() * 0.03, f"+{v:.4f}%", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([f"マスタ{n//10000:,}万キー" for n in d32["マスタのキーの数"]], fontsize=8.5)
    ax.set_ylabel("金額の合計のずれ（%）"); ax.set_title("32ビット：金額の合計は何%増えたか")
    save(fig, "a464_join_extra.png", SRC)


if __name__ == "__main__":
    main()
