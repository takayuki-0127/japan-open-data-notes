"""652 採番の連番の最大値で件数を見ると、欠番のせいで何%多く数えるのか

架空の申込みシステム（2025年）。申込みが来るたびに連番（IDENTITY のような採番）を1つ使う。欠番ができる理由を3つ置く。
  E1 登録の途中で失敗して取り消された（番号だけ使われる）
  E2 取消になった申込みを物理削除した
  E3 サーバーの再起動で、先読みしていた番号（1,000件分）が飛ぶ
件数を COUNT(*) と「MAX(ID) − MIN(ID) + 1」で数え、月ごと・累計でどれだけ違うかを見る。
DuckDB（1スレッド）と pandas の一致を確かめる。seed 652。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の申込みデータ（作成者が乱数で作成、seed 652）"
rng = np.random.default_rng(652)
P_FAIL, P_DELETE, CACHE = 0.015, 0.04, 1000
days = pd.date_range("2025-01-01", "2025-12-31")
restart_days = set(pd.to_datetime(["2025-02-17", "2025-05-08", "2025-08-21", "2025-08-22", "2025-11-04"]))
rows = []; next_id = 1; used = {"fail": 0, "restart": 0}
for d in days:
    if d in restart_days:
        jump = CACHE - ((next_id - 1) % CACHE) if (next_id - 1) % CACHE else CACHE
        used["restart"] += jump; next_id += jump
    lam = 180 * (1.25 if d.dayofweek < 5 else 0.6) * (1 + 0.15 * np.sin(2 * np.pi * d.dayofyear / 365))
    n = rng.poisson(lam)
    secs = np.sort(rng.integers(0, 86400, n))
    for s in secs:
        if rng.random() < P_FAIL:
            used["fail"] += 1; next_id += 1; continue
        rows.append((next_id, d + pd.Timedelta(seconds=int(s)), rng.random() < P_DELETE)); next_id += 1
A = pd.DataFrame(rows, columns=["app_id", "created_at", "deleted"])
n_deleted = int(A.deleted.sum())
A = A[~A.deleted].drop(columns="deleted").reset_index(drop=True)
A.assign(created_at=A.created_at.dt.strftime("%Y-%m-%d %H:%M:%S")).to_csv(DATA / "applications.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("applications", A)
q = [x for x in (SQL / "02_id_gaps_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
m = con.execute(q[0]).df().set_index("ym")
gaps = con.execute(q[1]).df()
A["ym"] = A.created_at.dt.strftime("%Y-%m")
g = A.groupby("ym").app_id
assert (m.n_rows == g.size()).all() and (m.n_by_id_range == g.max() - g.min() + 1).all()
assert int(gaps.missing.sum()) == int(A.app_id.max() - A.app_id.min() + 1 - len(A))
m["over_pct"] = (m.n_by_id_range / m.n_rows - 1) * 100
m.round(2).to_csv(RES / "monthly.csv")
gaps.head(30).to_csv(RES / "largest_gaps.csv", index=False)
total_rows = len(A); max_id = int(A.app_id.max())
gap_sizes = gaps.missing.values
out = {"rows_kept": total_rows, "max_id": max_id, "overcount_pct_total": round((max_id / total_rows - 1) * 100, 2),
       "ids_used_by_failed_inserts": used["fail"], "ids_used_by_deleted_rows": n_deleted, "ids_skipped_by_restarts": int(used["restart"]),
       "share_of_missing_ids": {"failed": round(used["fail"] / (max_id - total_rows) * 100, 1),
                                "deleted": round(n_deleted / (max_id - total_rows) * 100, 1),
                                "restart": round(used["restart"] / (max_id - total_rows) * 100, 1)},
       "gap_count": int(len(gaps)), "gaps_of_1": int((gap_sizes == 1).sum()), "gaps_over_100": int((gap_sizes > 100).sum()),
       "monthly_over_pct": {k: round(float(v), 1) for k, v in m.over_pct.items()},
       "monthly_over_pct_min": round(float(m.over_pct.min()), 1), "monthly_over_pct_max": round(float(m.over_pct.max()), 1),
       "monthly_over_pct_median": round(float(m.over_pct.median()), 1),
       "aug_by_id": int(m.loc["2025-08", "n_by_id_range"]), "aug_rows": int(m.loc["2025-08", "n_rows"]),
       "jul_by_id": int(m.loc["2025-07", "n_by_id_range"]), "jul_rows": int(m.loc["2025-07", "n_rows"])}
json.dump(out, open(RES / "a652_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：月ごとの件数
fig, ax = plt.subplots(figsize=(8.5, 3.8))
x = np.arange(len(m)); w = 0.4
ax.bar(x - w / 2, m.n_rows, w, color=BLUE, label="COUNT(*)（残っている件数）")
ax.bar(x + w / 2, m.n_by_id_range, w, color=ORANGE, label="MAX(ID) − MIN(ID) + 1")
ax.set_xticks(x); ax.set_xticklabels([s[5:] + "月" for s in m.index], fontsize=9); ax.set_ylabel("件数")
ax.legend(frameon=False, fontsize=9, loc="upper left"); ax.set_title("番号の幅で数えると毎月多く出て、再起動のあった月は跳ねる")
save(fig, "a652_monthly.png", SRC)
# 図2：多く出た割合
fig, ax = plt.subplots(figsize=(8.5, 3.6))
cols = [ORANGE if v > 10 else BLUE for v in m.over_pct]
ax.bar(x, m.over_pct, color=cols)
for i, v in enumerate(m.over_pct):
    ax.text(i, v + 0.5, f"{v:.1f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([s[5:] + "月" for s in m.index], fontsize=9); ax.set_ylabel("COUNT(*) より多い割合（%）")
ax.set_title("ふだんの月は約6%多い。再起動で番号が大きく飛んだ月は11〜36%多い")
save(fig, "a652_over_pct.png", SRC)
# 図3：欠番の内訳
fig, ax = plt.subplots(figsize=(8, 3.4))
lab = ["登録の途中で失敗", "取消で削除", "再起動で飛んだ番号"]
val = [used["fail"], n_deleted, used["restart"]]
ax.barh(lab[::-1], val[::-1], color=[GRAY, BLUE, ORANGE][::-1])
for i, v in enumerate(val[::-1]):
    ax.text(v, i, f" {v:,}", va="center", fontsize=9)
ax.set_xlabel("使われなかった番号の数"); ax.set_title(f"欠番 {max_id - total_rows:,} 個の内訳（残っている件数 {total_rows:,}）")
save(fig, "a652_gap_breakdown.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
