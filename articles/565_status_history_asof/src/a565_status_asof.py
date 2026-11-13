"""565 状態が何度も変わる申込みで、過去のある日の状態を履歴からどう戻すのか。今の状態で数えると何件ずれるか

架空の申込み（2024年1月〜2025年12月、15,000件）と、状態の変わった履歴。
状態：受付 → 審査中 →（保留 ⇄ 審査中）→ 承認・否認・取下げ。承認のあと解約になることもある。
履歴の一部は、あとから入力される（有効日より3〜30日遅れて記録される）。
各月末の「状態ごとの件数」を3通りで出して比べる：
  正 有効日で戻す：その月末に有効だった状態（valid_from ≦ 月末 < valid_to）。あとから入力された分も入れる
  当 記録日で戻す：その月末までに記録されていた履歴だけで戻す（その時点で見えていた数）
  今 今の状態で数える：その月末までに受けた申込みを、いま（2025年末）の状態で数える
Python と SQL（DuckDB、1スレッド）で「正」の月末件数が一致することを確かめる。数字は置いた仮定で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の申込みと状態の履歴（作成者が乱数で作成、seed 565）"
rng = np.random.default_rng(565)
N = 15000
start = pd.Timestamp("2024-01-01")
END = pd.Timestamp("2025-12-31")
STATUSES = ["受付", "審査中", "保留", "承認", "否認", "取下げ", "解約"]
hist = []
for i in range(N):
    aid = 300000 + i
    t = start + pd.Timedelta(days=int(rng.integers(0, 731)))
    seq = [("受付", t)]
    t = t + pd.Timedelta(days=int(rng.integers(1, 6)))
    seq.append(("審査中", t))
    while rng.random() < 0.3:                    # 保留に回る
        t = t + pd.Timedelta(days=int(rng.integers(2, 15))); seq.append(("保留", t))
        t = t + pd.Timedelta(days=int(rng.integers(5, 40))); seq.append(("審査中", t))
    t = t + pd.Timedelta(days=int(rng.integers(3, 30)))
    u = rng.random()
    fin = "承認" if u < 0.6 else ("否認" if u < 0.85 else "取下げ")
    seq.append((fin, t))
    if fin == "承認" and rng.random() < 0.12:
        t = t + pd.Timedelta(days=int(rng.integers(30, 300))); seq.append(("解約", t))
    for k, (s, vf) in enumerate(seq):
        if vf > END:
            break
        late = int(rng.integers(3, 31)) if (k > 0 and rng.random() < 0.08) else 0
        hist.append((aid, k + 1, s, vf.date(), (vf + pd.Timedelta(days=late)).date()))
H = pd.DataFrame(hist, columns=["app_id", "seq", "status", "valid_from", "recorded_on"])
H.to_csv(DATA / "status_history.csv", index=False)
H["valid_from"] = pd.to_datetime(H.valid_from)
H["recorded_on"] = pd.to_datetime(H.recorded_on)


def asof_counts(asof, by="valid"):
    """asof の日の終わり時点の状態ごとの件数"""
    h = H[H.valid_from <= asof]
    if by == "recorded":
        h = h[h.recorded_on <= asof]
    last = h.sort_values(["app_id", "valid_from", "seq"]).groupby("app_id").tail(1)
    return last.status.value_counts().reindex(STATUSES, fill_value=0)


cur = H.sort_values(["app_id", "valid_from", "seq"]).groupby("app_id").tail(1).set_index("app_id").status
recv = H[H.seq == 1].set_index("app_id").valid_from

month_ends = pd.date_range("2024-01-31", "2025-12-31", freq="ME")
rows = []
for me in month_ends:
    a = asof_counts(me, "valid"); b = asof_counts(me, "recorded")
    c = cur[recv[recv <= me].index].value_counts().reindex(STATUSES, fill_value=0)
    for s in STATUSES:
        rows.append({"month_end": me.strftime("%Y-%m"), "status": s, "valid": int(a[s]), "recorded": int(b[s]), "current": int(c[s])})
C = pd.DataFrame(rows)
C.to_csv(RES / "month_end_counts.csv", index=False)

# SQL（DuckDB）で「正」を出して突き合わせ
con = duckdb.connect()
con.execute("SET threads=1")
con.execute(f"CREATE TABLE status_history AS SELECT * FROM read_csv_auto('{DATA / 'status_history.csv'}')")
sql = (SQL / "02_asof_duckdb.sql").read_text()
for me in month_ends:
    q = con.execute(sql.replace(":asof", me.strftime("%Y-%m-%d"))).df().set_index("status").n
    py = C[C.month_end == me.strftime("%Y-%m")].set_index("status").valid
    assert all(int(q.get(s, 0)) == int(py[s]) for s in STATUSES), me

# 比べる
P = C.pivot(index="month_end", columns="status", values=["valid", "recorded", "current"])
inrev = lambda k: P[k]["審査中"] + P[k]["保留"]
summ = {}
for k in ["recorded", "current"]:
    d_rev = inrev(k) - inrev("valid")
    d_app = P[k]["承認"] - P["valid"]["承認"]
    summ[k] = {"in_review_diff_mean": round(float(d_rev.mean()), 1), "in_review_diff_min": int(d_rev.min()), "in_review_diff_max": int(d_rev.max()),
               "in_review_diff_pct_mean": round(float((100 * d_rev / inrev("valid")).mean()), 1),
               "approved_diff_mean": round(float(d_app.mean()), 1), "approved_diff_max_abs": int(d_app.abs().max())}
# 1つの月末で見た状態ごとの差（2024年12月末）
ex = C[C.month_end == "2024-12"].set_index("status")[["valid", "recorded", "current"]]
# 1つの月末で、状態が「正」と違う申込みの数
def mismatch(me, by):
    a_last = H[H.valid_from <= me].sort_values(["app_id", "valid_from", "seq"]).groupby("app_id").tail(1).set_index("app_id").status
    if by == "recorded":
        h = H[(H.valid_from <= me) & (H.recorded_on <= me)]
        b = h.sort_values(["app_id", "valid_from", "seq"]).groupby("app_id").tail(1).set_index("app_id").status.reindex(a_last.index)
    else:
        b = cur.reindex(a_last.index)
    return int((a_last != b).sum()), len(a_last)


mm = {me.strftime("%Y-%m"): {"recorded": mismatch(me, "recorded")[0], "current": mismatch(me, "current")[0], "apps": mismatch(me, "current")[1]} for me in month_ends}
pd.DataFrame(mm).T.to_csv(RES / "mismatch_by_month.csv")
late = H[H.recorded_on > H.valid_from]
summary = {"applications": N, "history_rows": len(H), "late_rows": len(late), "late_rows_pct": round(100 * len(late) / len(H), 2),
           "final_status_now": cur.value_counts().to_dict(), "diff_vs_valid": summ,
           "example_2024_12": ex.to_dict(orient="index"),
           "mismatch_apps_mean_pct": {k: round(float(np.mean([100 * v[k] / v["apps"] for v in mm.values()])), 1) for k in ["recorded", "current"]},
           "mismatch_2024_12": mm["2024-12"], "sql_python_match": True}
json.dump(summary, open(RES / "a565_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))

COL = {"valid": INK, "recorded": BLUE, "current": ORANGE}
LAB = {"valid": "正 有効日で戻す", "recorded": "当 記録日で戻す（当時見えていた数）", "current": "今 今の状態で数える"}
x = np.arange(len(month_ends)); xl = [m.strftime("%y/%m") for m in month_ends]
# 図1：審査中（保留を含む）の月末件数
fig, ax = plt.subplots(figsize=(9, 4.2))
for k in ["valid", "recorded", "current"]:
    ax.plot(x, inrev(k).values, marker="o", ms=3, color=COL[k], lw=1.6 if k == "valid" else 1.3, label=LAB[k])
ax.set_xticks(x[::3], xl[::3])
ax.set_ylabel("件数")
ax.set_title("月末に「審査中・保留」だった申込みの数", loc="left")
ax.legend(frameon=False, fontsize=9)
save(fig, "a565_in_review.png", SRC)

# 図2：2024年12月末の状態ごとの件数
fig, ax = plt.subplots(figsize=(9, 4))
xs = np.arange(len(STATUSES))
for j, k in enumerate(["valid", "recorded", "current"]):
    v = ex[k].reindex(STATUSES).values
    ax.bar(xs + (j - 1) * 0.27, v, 0.27, color=COL[k], label=LAB[k])
ax.set_xticks(xs, STATUSES)
ax.set_ylabel("件数")
ax.set_title("2024年12月末の状態ごとの件数（3通りの数え方）", loc="left")
ax.legend(frameon=False, fontsize=9)
save(fig, "a565_by_status.png", SRC)

# 図3：状態が「正」と違う申込みの割合
fig, ax = plt.subplots(figsize=(9, 3.8))
for k in ["recorded", "current"]:
    ax.plot(x, [100 * mm[m.strftime("%Y-%m")][k] / mm[m.strftime("%Y-%m")]["apps"] for m in month_ends], marker="o", ms=3, color=COL[k], label=LAB[k])
ax.set_xticks(x[::3], xl[::3])
ax.set_ylabel("「正」と状態が違う申込みの割合（%）")
ax.set_title("月末時点の状態が、有効日で戻した状態と違う申込みの割合", loc="left", fontsize=12)
ax.legend(frameon=False, fontsize=9)
save(fig, "a565_mismatch.png", SRC)
