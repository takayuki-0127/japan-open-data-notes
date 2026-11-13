"""572 同じ時刻の行が並ぶとき、ROW_NUMBERで「最新の1行」を選ぶと、実行のたびに何件入れ替わるのか（架空の更新ログ、seed 572）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

rng = np.random.default_rng(572)
SRC = "架空の会員の状態の更新ログ（作成者が乱数で作成、seed 572）"
STAT = ["有効", "休止", "解約"]
FEE = {"有効": 1980, "休止": 300, "解約": 0}
# --- 架空の更新ログ：会員2万人。秒単位の時刻。夜間の一括処理と二重の書き込みで、同じ秒の行ができる
N = 20000
rows = []
for cid in range(1, N + 1):
    k = rng.integers(1, 7)
    t = pd.Timestamp("2025-01-01") + pd.to_timedelta(np.sort(rng.integers(0, 365 * 86400, k)), "s")
    st = ["有効"] + list(rng.choice(STAT, k - 1, p=[.45, .3, .25]))
    ts = list(t)
    # 夜間の一括処理：最後の更新の 6% は、同じ秒に「もう1行」（状態を上書き）が入る
    if rng.random() < .06:
        ts.append(ts[-1]); st.append(rng.choice(STAT, p=[.4, .25, .35]))
    # 画面からの二重送信：2% は同じ秒に同じ状態がもう1行
    if rng.random() < .02:
        ts.append(ts[-1]); st.append(st[-1])
    for j, (a, b) in enumerate(zip(ts, st)):
        rows.append((cid, a, b))
log = pd.DataFrame(rows, columns=["member_id", "updated_at", "status"])
log["status"] = [str(s) for s in log["status"]]
log["seq"] = np.arange(1, len(log) + 1)          # 書き込まれた順の連番（正しい順番）
log.to_csv(DATA / "status_log.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")

# 正解：時刻＋連番で最後の行
truth = log.sort_values(["member_id", "updated_at", "seq"]).groupby("member_id").tail(1).set_index("member_id")["status"]
last_t = log.groupby("member_id")["updated_at"].transform("max")
tie_n = log[log.updated_at == last_t].groupby("member_id").size()
tied = int((tie_n > 1).sum())
tied_diff = int(log[log.updated_at == last_t].groupby("member_id")["status"].nunique().gt(1).sum())

con = duckdb.connect(); con.execute("SET threads=1")
Q_TIME = (SQL / "02_latest_duckdb.sql").read_text().split(";")[0]
Q_SEQ = Q_TIME.replace("ORDER BY updated_at DESC", "ORDER BY updated_at DESC, seq DESC")
Q_NAME = Q_TIME.replace("ORDER BY updated_at DESC", "ORDER BY updated_at DESC, status DESC")
Q_MAX = """SELECT l.member_id, l.status FROM status_log l
JOIN (SELECT member_id, MAX(updated_at) AS mt FROM status_log GROUP BY member_id) m
  ON l.member_id = m.member_id AND l.updated_at = m.mt"""

def run(df, q):
    con.register("src", df); con.execute("CREATE OR REPLACE TABLE status_log AS SELECT * FROM src")
    return con.execute(q).df()

R = 100
runs = []
prev = None
for r in range(R):
    df = log.sample(frac=1, random_state=10000 + r).reset_index(drop=True)   # 行の物理的な並びだけを変える
    a = run(df, Q_TIME).set_index("member_id")["status"].sort_index()
    b = run(df, Q_SEQ).set_index("member_id")["status"].sort_index()
    wrong = int((a != truth).sum()); changed = int((a != prev).sum()) if prev is not None else None
    runs.append({"run": r + 1, "wrong_vs_truth": wrong, "changed_vs_prev": changed,
                 "cancel": int((a == "解約").sum()), "fee": int(a.map(FEE).sum()),
                 "seq_wrong": int((b != truth).sum())})
    prev = a
RU = pd.DataFrame(runs); RU.to_csv(RES / "runs.csv", index=False)
mx = run(log, Q_MAX); nm = run(log, Q_NAME).set_index("member_id")["status"].sort_index()
dup_rows = len(mx) - N
nm_wrong = int((nm != truth).sum())
cancel_true = int((truth == "解約").sum()); fee_true = int(truth.map(FEE).sum())
mx_cancel = int((mx.status == "解約").sum())
chg = RU.changed_vs_prev.dropna()
res = {"members": N, "log_rows": len(log), "tied_members": tied, "tied_share_pct": round(tied / N * 100, 2),
       "tied_with_diff_status": tied_diff,
       "time_only_wrong_mean": round(RU.wrong_vs_truth.mean(), 1), "time_only_wrong_min": int(RU.wrong_vs_truth.min()), "time_only_wrong_max": int(RU.wrong_vs_truth.max()),
       "changed_vs_prev_mean": round(float(chg.mean()), 1), "changed_vs_prev_min": int(chg.min()), "changed_vs_prev_max": int(chg.max()),
       "cancel_true": cancel_true, "cancel_min": int(RU.cancel.min()), "cancel_max": int(RU.cancel.max()),
       "fee_true": fee_true, "fee_min": int(RU.fee.min()), "fee_max": int(RU.fee.max()),
       "time_seq_wrong_max": int(RU.seq_wrong.max()),
       "max_join_rows": len(mx), "max_join_dup_rows": dup_rows, "max_join_cancel": mx_cancel,
       "time_name_wrong": nm_wrong}
json.dump(res, open(RES / "a572_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False))
pd.DataFrame([["時刻のみ（ROW_NUMBER）", res["time_only_wrong_mean"], f'{res["time_only_wrong_min"]}〜{res["time_only_wrong_max"]}（実行ごとに変わる）'],
              ["時刻＋状態名（ROW_NUMBER）", nm_wrong, "毎回同じ"], ["MAX(時刻)で結合", dup_rows, "行が増える（同じ会員が2行）"],
              ["時刻＋連番（ROW_NUMBER）", res["time_seq_wrong_max"], "毎回同じ・正しい"]],
             columns=["並びの決め方", "正解と違う件数（重複行）", "備考"]).to_csv(RES / "methods.csv", index=False)

# --- 図1：実行ごとに、前回と選ばれた行が変わる会員の数
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(RU.run, RU.changed_vs_prev, color=ORANGE, marker="o", ms=3, lw=1, label="前回の実行と違う行を選んだ会員")
ax.plot(RU.run, RU.wrong_vs_truth, color=BLUE, lw=1, label="正解（時刻＋連番）と違う会員")
ax.plot(RU.run, RU.seq_wrong, color=INK, lw=1.5, label="時刻＋連番で並べた場合（0件）")
ax.set_xlabel("実行の回数（行の並びだけを変えて100回）"); ax.set_ylabel("会員数"); ax.set_ylim(bottom=-20); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"時刻だけで並べると、毎回 {chg.min():.0f}〜{chg.max():.0f}人の「最新の1行」が入れ替わる")
save(fig, "a572_changed.png", "出典：" + SRC)
# --- 図2：解約の人数（100回）
fig, ax = plt.subplots(figsize=(8, 4))
ax.hist(RU.cancel, bins=20, color=LIGHT, edgecolor=BLUE)
ax.axvline(cancel_true, color=INK, lw=2, label=f"正解 {cancel_true:,}人")
ax.set_xlabel("「解約」の会員数"); ax.set_ylabel("実行の回数"); ax.legend(frameon=False)
ax.set_title(f"時刻だけで並べた「解約」の人数：{RU.cancel.min():,}〜{RU.cancel.max():,}人（100回）")
save(fig, "a572_cancel.png", "出典：" + SRC)
# --- 図3：並びの決め方の比較
fig, ax = plt.subplots(figsize=(8, 4))
lab = ["時刻のみ\n（100回の平均）", "時刻＋状態名", "MAX(時刻)で結合\n（増えた行）", "時刻＋連番"]
val = [res["time_only_wrong_mean"], nm_wrong, dup_rows, res["time_seq_wrong_max"]]
b = ax.bar(lab, val, color=[ORANGE, GRAY, BLUE, GREEN])
for x, v in zip(b, val): ax.text(x.get_x() + x.get_width() / 2, v, f"{v:,.0f}", ha="center", va="bottom")
ax.set_ylabel("正解と違う会員数（結合は増えた行数）")
ax.set_title("同じ時刻の行の並びを決めないと、どの書き方でもずれる")
save(fig, "a572_methods.png", "出典：" + SRC + "。時刻＋状態名は毎回同じ結果だが、正しい順番ではない")
