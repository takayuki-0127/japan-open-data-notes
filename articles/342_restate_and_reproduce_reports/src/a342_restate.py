"""342 締めたあとに訂正されたデータで、先月のレポートの数字を再現できるか（架空の取引・seed 342）"""
import numpy as np, pandas as pd, duckdb, json
import matplotlib.pyplot as plt
from common import *
rng = np.random.default_rng(342)
months = pd.period_range("2025-01", "2025-12", freq="M")
TODAY = pd.Timestamp("2026-03-31")
# ---- できごとの記録（正解）：取引ごとに「登録・訂正・取消」がいつ起きたか
ev = []; tid = 0
for m in months:
    days = pd.date_range(m.start_time, m.end_time, freq="D")
    n = rng.poisson(4000)
    for _ in range(n):
        tid += 1
        d = days[rng.integers(len(days))]
        amt = float(np.round(rng.lognormal(9.2, 0.9)))
        late = rng.random() < 0.04                              # 4% は遅れて登録される
        reg = d + pd.Timedelta(days=int(np.ceil(rng.lognormal(2.6, 0.7))) if late else int(rng.integers(0, 2)))
        ev.append((tid, str(m), d, "登録", reg, amt))
        u = rng.random()
        if u < 0.05:                                            # 5% は金額の訂正（1回、たまに2回）
            t1 = reg + pd.Timedelta(days=int(np.ceil(rng.lognormal(2.8, 0.8))))
            a1 = float(np.round(amt * rng.choice([0.5, 0.8, 0.9, 1.1, 1.2, 2.0, 10.0], p=[.1, .2, .25, .25, .12, .06, .02])))
            ev.append((tid, str(m), d, "訂正", t1, a1))
            if rng.random() < 0.15:
                ev.append((tid, str(m), d, "訂正", t1 + pd.Timedelta(days=int(rng.integers(1, 30))), amt))  # 元に戻す
        elif u < 0.065:                                         # 1.5% は取消
            ev.append((tid, str(m), d, "取消", reg + pd.Timedelta(days=int(np.ceil(rng.lognormal(2.5, 0.8)))), 0.0))
E = pd.DataFrame(ev, columns=["id", "ym", "tx_date", "kind", "at", "amt"]).sort_values(["id", "at"]).reset_index(drop=True)
E = E[E["at"] <= TODAY]
# レポートを出した時点：翌月の第5営業日の終わり
asof = {str(m): pd.Timestamp(np.busday_offset(np.datetime64((m + 1).start_time.date()), 4, roll="forward")) + pd.Timedelta(hours=23) for m in months}
# ---- 3つの持ち方を作る
# C：いつからいつまでその値だったかを持つ表（登録・訂正・取消のたびに行を閉じて足す）
E["to"] = E.groupby("id")["at"].shift(-1)
C = E.rename(columns={"at": "rec_from", "to": "rec_to"})[["id", "ym", "tx_date", "kind", "amt", "rec_from", "rec_to"]]
# A：上書き（今の値だけ。取消は行を消す）
A = C[C.rec_to.isna() & (C.kind != "取消")][["id", "ym", "tx_date", "amt"]]
# B：今の表＋「更新の履歴」（訂正の前の値と訂正した時刻だけ。登録した時刻と、取り消した行は残らない）
Bcur = A.copy()
Eprev = E.assign(old=E.groupby("id")["amt"].shift(1))
Bhist = Eprev[Eprev.kind == "訂正"][["id", "at", "old", "amt"]].rename(columns={"at": "changed_at", "amt": "new"})
con = duckdb.connect()
for n_, d_ in [("A", A), ("C", C), ("Bcur", Bcur), ("Bhist", Bhist)]: con.register(n_, d_)
out = []
for ym, t in asof.items():
    con.execute("CREATE OR REPLACE TEMP TABLE p AS SELECT ?::VARCHAR AS ym, ?::TIMESTAMP AS t", [ym, t])
    # 正解＝その時点で出したレポートの数字（できごとの記録から）
    truth = E[(E.ym == ym) & (E["at"] <= t)].groupby("id").tail(1).pipe(lambda d: d[d.kind != "取消"].amt.sum())
    a = con.execute("SELECT COALESCE(SUM(amt),0) FROM A, p WHERE A.ym = p.ym").fetchone()[0]
    # B：今の値から、レポートのあとに起きた訂正を巻き戻す（いちばん古い「あとの訂正」の前の値に戻す）
    b = con.execute("""
        WITH firstafter AS (SELECT h.id, h.old, ROW_NUMBER() OVER (PARTITION BY h.id ORDER BY h.changed_at) AS rn
                            FROM Bhist h, p WHERE h.changed_at > p.t)
        SELECT COALESCE(SUM(COALESCE(f.old, c.amt)),0) FROM Bcur c JOIN p ON c.ym = p.ym
        LEFT JOIN firstafter f ON f.id = c.id AND f.rn = 1""").fetchone()[0]
    # C：その時点で有効だった行を引く
    c = con.execute("""SELECT COALESCE(SUM(amt),0) FROM C, p WHERE C.ym = p.ym AND C.kind <> '取消'
                       AND C.rec_from <= p.t AND (C.rec_to > p.t OR C.rec_to IS NULL)""").fetchone()[0]
    # 動いた分の内訳（レポートのあと）
    e = E[E.ym == ym]
    before = e[e["at"] <= t].groupby("id").tail(1).set_index("id"); now = e.groupby("id").tail(1).set_index("id")
    bamt = before[before.kind != "取消"].amt.reindex(now.index).fillna(0.0)
    namt = now.amt.where(now.kind != "取消", 0.0)
    newid = ~now.index.isin(before.index)
    canc = (now.kind == "取消") & ~newid & (bamt > 0)
    corr = ~newid & ~canc & (namt != bamt)
    out.append({"ym": ym, "reported": truth, "A_overwrite": a, "B_update_log": b, "C_asof": c, "now": float(namt.sum()),
                "late_rows": int(newid.sum()), "late_amt": float(namt[newid].sum()),
                "cancel_rows": int(canc.sum()), "cancel_amt": float(-bamt[canc].sum()),
                "corr_rows": int(corr.sum()), "corr_amt": float((namt - bamt)[corr].sum()),
                "gross_moved": float(namt[newid].abs().sum() + bamt[canc].abs().sum() + (namt - bamt)[corr].abs().sum())})
R = pd.DataFrame(out)
for k in ["A_overwrite", "B_update_log", "C_asof", "now"]:
    R[k + "_diff_pct"] = (R[k] / R.reported - 1) * 100
R["gross_moved_pct"] = R.gross_moved / R.reported * 100
R.round(4).to_csv(RES / "reproduce_by_month.csv", index=False)
exact = lambda col: int((R[col] - R.reported).abs().lt(0.5).sum())
within = lambda col, p: int((R[col + "_diff_pct"].abs() <= p).sum())
main = {"n_tx": int(E.id.nunique()), "n_events": int(len(E)), "today": str(TODAY.date()),
        "share_corrected": round(float((E.kind == "訂正").groupby(E.id).any().mean()), 4),
        "share_cancelled": round(float((E.kind == "取消").groupby(E.id).any().mean()), 4),
        "months_exact": {k: exact(k) for k in ["A_overwrite", "B_update_log", "C_asof"]},
        "months_within_0.1pct": {k: within(k, 0.1) for k in ["A_overwrite", "B_update_log", "C_asof"]},
        "abs_diff_pct_mean": {k: round(float(R[k + "_diff_pct"].abs().mean()), 3) for k in ["A_overwrite", "B_update_log", "C_asof"]},
        "abs_diff_pct_max": {k: round(float(R[k + "_diff_pct"].abs().max()), 3) for k in ["A_overwrite", "B_update_log", "C_asof"]},
        "net_move_pct_mean": round(float(R.now_diff_pct.mean()), 3), "gross_moved_pct_mean": round(float(R.gross_moved_pct.mean()), 3),
        "moved_rows_mean": {"late": float(R.late_rows.mean()), "cancel": float(R.cancel_rows.mean()), "corr": float(R.corr_rows.mean())},
        "moved_amt_share": {k: round(float(R[k + "_amt"].abs().sum() / (R.late_amt.abs().sum() + R.cancel_amt.abs().sum() + R.corr_amt.abs().sum())), 3) for k in ["late", "cancel", "corr"]},
        "rows_C_over_A": round(len(C) / len(A), 3)}
# B に「登録した時刻」と「取消の記録」を足すと再現できるか（B+）
con.register("Ereg", E[E.kind == "登録"][["id", "at"]].rename(columns={"at": "reg_at"}))
con.register("Bdel", Eprev[Eprev.kind == "取消"][["id", "ym", "at", "old"]].rename(columns={"at": "deleted_at"}))
bp = []
for ym, t in asof.items():
    con.execute("CREATE OR REPLACE TEMP TABLE p AS SELECT ?::VARCHAR AS ym, ?::TIMESTAMP AS t", [ym, t])
    v = con.execute("""
        WITH firstafter AS (SELECT h.id, h.old, ROW_NUMBER() OVER (PARTITION BY h.id ORDER BY h.changed_at) AS rn FROM Bhist h, p WHERE h.changed_at > p.t),
        alive AS (SELECT c.id, c.amt FROM Bcur c JOIN p ON c.ym = p.ym
                  UNION ALL SELECT d.id, d.old FROM Bdel d JOIN p ON d.ym = p.ym WHERE d.deleted_at > p.t)
        SELECT COALESCE(SUM(COALESCE(f.old, a.amt)),0) FROM alive a JOIN Ereg r ON r.id = a.id CROSS JOIN p
        LEFT JOIN firstafter f ON f.id = a.id AND f.rn = 1 WHERE r.reg_at <= p.t""").fetchone()[0]
    bp.append(v)
R["Bplus"] = bp; main["months_exact"]["Bplus_with_insert_time_and_deletes"] = int((R.Bplus - R.reported).abs().lt(0.5).sum())
R.round(4).to_csv(RES / "reproduce_by_month.csv", index=False)
json.dump(main, open(RES / "a342_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(R[["ym", "A_overwrite_diff_pct", "B_update_log_diff_pct", "C_asof_diff_pct", "gross_moved_pct"]].round(3))
SRC = "架空の取引（乱数で作成、seed 342）。レポートは翌月の第5営業日に出したとし、2026-03-31 に再現を試した"
# 図1：月ごとの再現のずれ
fig, ax = plt.subplots(figsize=(8.2, 4.4)); x = np.arange(12); w = 0.27
for j, (c, lab, col) in enumerate([("A_overwrite", "A 上書き（今の値だけ）", GRAY), ("B_update_log", "B 今の値＋更新の履歴", ORANGE), ("C_asof", "C いつ時点の値かを持つ", BLUE)]):
    ax.bar(x + (j - 1) * w, R[c + "_diff_pct"], w, color=col, label=lab)
ax.axhline(0, color=INK, lw=0.6); ax.set_xticks(x); ax.set_xticklabels([f"{i+1}月" for i in range(12)])
ax.set_ylabel("当時のレポートの数字とのずれ（%）"); ax.set_title("過去12か月のレポートを、いま作り直すとどれだけずれるか"); ax.legend(frameon=False, fontsize=9)
save(fig, "a342_diff.png", SRC)
# 図2：再現できた月数
fig, ax = plt.subplots(figsize=(7.6, 3.8))
labs = ["A 上書き", "B 今の値＋\n更新の履歴", "B＋ 登録時刻と\n取消の記録を足す", "C いつ時点の\n値かを持つ"]
vals = [main["months_exact"]["A_overwrite"], main["months_exact"]["B_update_log"], main["months_exact"]["Bplus_with_insert_time_and_deletes"], main["months_exact"]["C_asof"]]
b = ax.bar(labs, vals, color=[GRAY, ORANGE, LIGHT, BLUE]); ax.set_ylim(0, 13.5); ax.set_ylabel("同じ数字を再現できた月数（12か月中）")
for r_, v in zip(b, vals): ax.text(r_.get_x() + r_.get_width() / 2, v + 0.3, str(v), ha="center", fontsize=12)
ax.set_title("当時と同じ数字を再現できたのは、12か月のうち何か月か")
save(fig, "a342_months.png", SRC)
# 図3：レポートのあとに動いた分の内訳
fig, ax = plt.subplots(figsize=(8.2, 4.2))
ax.bar(x, R.late_amt / R.reported * 100, color=BLUE, label="遅れて登録された行")
ax.bar(x, R.corr_amt.clip(lower=0) / R.reported * 100, bottom=R.late_amt / R.reported * 100, color=GREEN, label="訂正（増えた分）")
ax.bar(x, R.corr_amt.clip(upper=0) / R.reported * 100, color=ORANGE, label="訂正（減った分）")
ax.bar(x, R.cancel_amt / R.reported * 100, bottom=R.corr_amt.clip(upper=0) / R.reported * 100, color=GRAY, label="取消")
ax.plot(x, R.now_diff_pct, "o-", color=INK, lw=1, ms=4, label="差し引き")
ax.axhline(0, color=INK, lw=0.6); ax.set_xticks(x); ax.set_xticklabels([f"{i+1}月" for i in range(12)])
ax.set_ylabel("当時のレポートの数字に対する割合（%）"); ax.set_title("レポートを出したあとに、月の数字はどれだけ動いたか"); ax.legend(frameon=False, fontsize=8, ncol=3)
save(fig, "a342_moved.png", SRC)
