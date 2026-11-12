"""454 2つの処理が同時に同じ行を書き換えると、何件の更新が消えるのか
架空の在庫の表で、処理の重なりを乱数で作るシミュレーション（seed 454）。
あわせて、SQLite の2つの接続で「読む→読む→書く→書く」の順を実際に流して確かめる。"""
import json, sqlite3, heapq
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, GREEN, save

SEED = 454


def simulate(method, n_tx, n_rows, rate, mean_dur, seed, skew=1.0):
    """n_tx 件の更新を流す。到着は毎秒 rate 件のポアソン、読んでから書くまでの時間は平均 mean_dur 秒の指数分布。
    行は skew が大きいほど一部に集まる（ジップ分布）。返り値：消えた更新の数、最後の残高のずれ、やり直しの数。"""
    rng = np.random.default_rng(seed)
    t_read = np.cumsum(rng.exponential(1 / rate, n_tx))
    dur = rng.exponential(mean_dur, n_tx)
    p = 1 / np.arange(1, n_rows + 1) ** skew; p /= p.sum()
    row = rng.choice(n_rows, n_tx, p=p)
    delta = rng.integers(1, 10, n_tx) * rng.choice([-1, 1], n_tx)
    bal = np.zeros(n_rows, dtype=np.int64); ver = np.zeros(n_rows, dtype=np.int64)
    cnt = np.zeros(n_rows, dtype=np.int64)                   # いまの値に入っている更新の数
    last_writer = np.full(n_rows, -1)
    lost = 0; retries = 0; overlapped = 0
    # 出来事：(時刻, 種類, 取引)。種類 0＝読む、1＝書く
    ev = [(t_read[i], 0, i) for i in range(n_tx)]
    heapq.heapify(ev)
    seen_bal = np.zeros(n_tx, dtype=np.int64); seen_ver = np.zeros(n_tx, dtype=np.int64); seen_cnt = np.zeros(n_tx, dtype=np.int64)
    while ev:
        t, kind, i = heapq.heappop(ev)
        r = row[i]
        if kind == 0:
            seen_bal[i] = bal[r]; seen_ver[i] = ver[r]; seen_cnt[i] = cnt[r]
            heapq.heappush(ev, (t + dur[i], 1, i))
        else:
            changed = ver[r] != seen_ver[i]                 # 読んでから書くまでの間に、ほかの処理が書いた
            overlapped += changed
            if method == "read_then_write":                 # 読んだ値に足して、そのまま書く
                bal[r] = seen_bal[i] + delta[i]; ver[r] += 1   # 間に入った更新は上書きされて消える
                cnt[r] = seen_cnt[i] + 1
            elif method == "single_update":                 # UPDATE ... SET qty = qty + ? の1文
                bal[r] += delta[i]; ver[r] += 1; cnt[r] += 1
            elif method == "version_check":                 # 版が読んだときと同じなら書く。違えば読み直してやり直す
                if changed:
                    retries += 1
                    seen_bal[i] = bal[r]; seen_ver[i] = ver[r]; seen_cnt[i] = cnt[r]
                    heapq.heappush(ev, (t + rng.exponential(mean_dur), 1, i))
                else:
                    bal[r] = seen_bal[i] + delta[i]; ver[r] += 1; cnt[r] = seen_cnt[i] + 1
    lost = n_tx - int(cnt.sum())                             # 最後の値に入っていない更新の数
    truth = np.bincount(row, weights=delta, minlength=n_rows).astype(np.int64)
    wrong_rows = int((bal != truth).sum())
    return {"lost": int(lost), "lost_pct": round(100 * lost / n_tx, 2), "overlapped_pct": round(100 * overlapped / n_tx, 2),
            "wrong_rows": wrong_rows, "wrong_rows_pct": round(100 * wrong_rows / n_rows, 1),
            "abs_error_sum": int(np.abs(bal - truth).sum()), "retries": int(retries), "retries_per_tx": round(retries / n_tx, 3)}


N_TX, N_ROWS, REPS = 20000, 500, 20
BASE = dict(n_tx=N_TX, n_rows=N_ROWS, rate=50.0, mean_dur=0.05, skew=1.0)     # 同時に動いている処理は平均 2.5 本


def run(method, **kw):
    cfg = {**BASE, **kw}
    out = [simulate(method, seed=SEED + 1000 * k, **cfg) for k in range(REPS)]
    d = pd.DataFrame(out)
    return {c: round(float(d[c].mean()), 3) for c in d.columns} | {"lost_pct_min": float(d.lost_pct.min()), "lost_pct_max": float(d.lost_pct.max())}


# ---------- 基本の場面：3つの書き方 ----------
base = []
for m, lab in (("read_then_write", "読んでから書く"), ("single_update", "1文の UPDATE で足し引きする"), ("version_check", "版番号を確かめてから書く")):
    base.append({"method": lab, **run(m)})
base = pd.DataFrame(base); base.to_csv(RES / "base_three_methods.csv", index=False)

# ---------- 同時に動く数を変える（到着の速さ） ----------
conc = []
for rate in (2, 10, 20, 50, 100, 200, 400):
    r1 = run("read_then_write", rate=float(rate)); r3 = run("version_check", rate=float(rate))
    conc.append({"in_flight": rate * BASE["mean_dur"], "rate_per_sec": rate, "lost_pct": r1["lost_pct"], "wrong_rows_pct": r1["wrong_rows_pct"],
                 "abs_error_sum": r1["abs_error_sum"], "retries_per_tx": r3["retries_per_tx"]})
conc = pd.DataFrame(conc); conc.to_csv(RES / "by_concurrency.csv", index=False)

# ---------- 処理の時間を変える ----------
durs = []
for d in (0.005, 0.02, 0.05, 0.2, 1.0):
    r1 = run("read_then_write", mean_dur=d); r3 = run("version_check", mean_dur=d)
    durs.append({"mean_dur_sec": d, "in_flight": BASE["rate"] * d, "lost_pct": r1["lost_pct"], "wrong_rows_pct": r1["wrong_rows_pct"], "retries_per_tx": r3["retries_per_tx"]})
durs = pd.DataFrame(durs); durs.to_csv(RES / "by_duration.csv", index=False)

# ---------- 行の数と集まり方を変える ----------
hot = []
for n_rows in (50, 500, 5000, 50000):
    for skew in (0.0, 1.0):
        r1 = run("read_then_write", n_rows=n_rows, skew=skew)
        hot.append({"rows": n_rows, "spread": "一部の行に集まる" if skew else "どの行も同じ", "lost_pct": r1["lost_pct"], "wrong_rows_pct": r1["wrong_rows_pct"]})
hot = pd.DataFrame(hot); hot.to_csv(RES / "by_rows_and_skew.csv", index=False)

# ---------- SQLite で実際に流す（2つの接続、順番を決めて流す） ----------
import os, tempfile
tmp = os.path.join(tempfile.mkdtemp(), "stock.db")
a = sqlite3.connect(tmp, isolation_level=None); b = sqlite3.connect(tmp, isolation_level=None)
a.execute("CREATE TABLE stock(item_id INTEGER PRIMARY KEY, qty INTEGER, ver INTEGER)")
a.execute("INSERT INTO stock VALUES (1, 100, 0), (2, 100, 0), (3, 100, 0)")
# ① 読んでから書く：A が読む → B が読む → A が書く（−3）→ B が書く（−5）
qa = a.execute("SELECT qty FROM stock WHERE item_id = 1").fetchone()[0]
qb = b.execute("SELECT qty FROM stock WHERE item_id = 1").fetchone()[0]
a.execute("UPDATE stock SET qty = ? WHERE item_id = 1", (qa - 3,))
b.execute("UPDATE stock SET qty = ? WHERE item_id = 1", (qb - 5,))
# ② 1文で足し引きする
a.execute("UPDATE stock SET qty = qty - 3 WHERE item_id = 2")
b.execute("UPDATE stock SET qty = qty - 5 WHERE item_id = 2")
# ③ 版番号を確かめてから書く
qa, va = a.execute("SELECT qty, ver FROM stock WHERE item_id = 3").fetchone()
qb, vb = b.execute("SELECT qty, ver FROM stock WHERE item_id = 3").fetchone()
na = a.execute("UPDATE stock SET qty = ?, ver = ver + 1 WHERE item_id = 3 AND ver = ?", (qa - 3, va)).rowcount
nb = b.execute("UPDATE stock SET qty = ?, ver = ver + 1 WHERE item_id = 3 AND ver = ?", (qb - 5, vb)).rowcount     # 0行：版が変わっている
retried = 0
if nb == 0:
    qb, vb = b.execute("SELECT qty, ver FROM stock WHERE item_id = 3").fetchone()
    retried = b.execute("UPDATE stock SET qty = ?, ver = ver + 1 WHERE item_id = 3 AND ver = ?", (qb - 5, vb)).rowcount
res = a.execute("SELECT item_id, qty, ver FROM stock ORDER BY item_id").fetchall()
a.close(); b.close()
demo = pd.DataFrame({"item_id": [r[0] for r in res], "method": ["読んでから書く", "1文の UPDATE で足し引きする", "版番号を確かめてから書く"],
                     "expected_qty": [92, 92, 92], "actual_qty": [r[1] for r in res],
                     "note": ["A の −3 が消えた", "", f"B の1回目は {nb} 行（版が変わっていた）。読み直して {retried} 行"]})
demo.to_csv(RES / "sqlite_demo.csv", index=False)
assert demo.actual_qty.tolist() == [95, 92, 92]

main = {"seed": SEED, "n_tx": N_TX, "n_rows": N_ROWS, "reps": REPS, "base_config": BASE, "base": base.to_dict(orient="records"),
        "by_concurrency": conc.to_dict(orient="records"), "by_duration": durs.to_dict(orient="records"), "by_rows_and_skew": hot.to_dict(orient="records"),
        "sqlite_demo": demo.to_dict(orient="records"), "sqlite_version": sqlite3.sqlite_version}
json.dump(main, open(RES / "a454_main.json", "w"), ensure_ascii=False, indent=1)

# ---------- 図 ----------
SRC = "架空のデータ（処理の重なりを乱数で作るシミュレーション、seed 454。20回の平均）"
fig, ax = plt.subplots(figsize=(8.6, 4.0))
ax.plot(conc.in_flight, conc.lost_pct, marker="o", color=ORANGE, label="読んでから書く：消えた更新（%）")
ax.plot(conc.in_flight, 100 * conc.retries_per_tx, marker="s", color=BLUE, label="版番号を確かめる：やり直し（更新100件あたりの回数）")
ax.set_xscale("log"); ax.set_xticks(conc.in_flight); ax.set_xticklabels([f"{v:g}" for v in conc.in_flight])
ax.set_xlabel("同時に動いている処理の数（平均）"); ax.set_ylabel("更新100件あたり"); ax.legend(frameon=False, fontsize=9)
ax.set_title("同時に動く処理が多いほど、消える更新は増える")
save(fig, "a454_by_concurrency.png", SRC)

fig, ax = plt.subplots(figsize=(8.6, 4.0))
x = np.arange(4); wd = 0.38
for i, (sk, c) in enumerate((("どの行も同じ", GRAY), ("一部の行に集まる", ORANGE))):
    t = hot[hot.spread == sk]
    ax.bar(x + (i - 0.5) * wd, t.lost_pct, wd, color=c, label=sk)
    for j, v in enumerate(t.lost_pct):
        ax.text(j + (i - 0.5) * wd, v + 0.3, f"{v:.1f}%" if v >= 0.05 else f"{v:.2f}%", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels([f"{n:,}行" for n in (50, 500, 5000, 50000)]); ax.set_xlabel("表の行の数"); ax.set_ylabel("消えた更新（%）")
ax.legend(frameon=False, fontsize=9, title="更新の集まり方"); ax.set_title("行が少ないほど、一部の行に集まるほど、更新は消える")
save(fig, "a454_by_rows.png", SRC)

fig, ax = plt.subplots(figsize=(8.6, 3.6))
b3 = base.iloc[::-1]
ax.barh(b3.method, b3.wrong_rows_pct, color=[BLUE, BLUE, ORANGE])
for i, (v, l, rt) in enumerate(zip(b3.wrong_rows_pct, b3.lost_pct, b3.retries_per_tx)):
    ax.text(v + 1, i, f"{v:.1f}%（消えた更新 {l:.2f}%、やり直し 更新1件あたり {rt:.3f} 回）", va="center", fontsize=9)
ax.set_xlim(0, 100); ax.set_xlabel("最後の在庫が合わなかった行の割合（%）"); ax.set_title("3つの書き方の結果（更新2万件・500行・同時に平均2.5本）")
save(fig, "a454_three_methods.png", SRC)
print(base.to_string()); print(conc.to_string()); print(durs.to_string()); print(hot.to_string()); print(demo.to_string())
