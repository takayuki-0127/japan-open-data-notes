"""359 累計を出すウィンドウ関数は、同じ日付の行があると何がずれるのか（架空の入出金明細）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import SQL, RES, save, BLUE, ORANGE, GRAY, GREEN, INK, LIGHT

SEED = 359
SRC = "架空の入出金明細（作成者が乱数で作成、seed 359）"
rng = np.random.default_rng(SEED)
N_ACCT, N_DAY = 2000, 90
days = pd.date_range("2026-01-01", periods=N_DAY)

# ---------- 架空の入出金明細：口座2,000・90日。1日に0〜数行。繰越残高は期間の前の日に1行 ----------
rows = []
for a in range(1, N_ACCT + 1):
    rate = rng.gamma(2.0, 0.35)                           # 口座ごとの1日の明細の数の平均
    open_bal = int(rng.lognormal(np.log(60000), 0.9))
    rows.append((a, days[0] - pd.Timedelta(days=1), 0, open_bal))            # 繰越残高は前の日の日付（1行だけ）
    k = rng.poisson(rate, N_DAY)
    for di, n in enumerate(k):
        for j in range(n):
            if rng.random() < 0.28:                       # 入金（まとまった額）
                amt = int(rng.lognormal(np.log(60000), 0.8))
            else:                                         # 出金
                amt = -int(rng.lognormal(np.log(9000), 1.0))
            rows.append((a, days[di], j + 1, amt))
tx = pd.DataFrame(rows, columns=["acct", "d", "seq", "amount"])
tx["n_day"] = tx.groupby(["acct", "d"])["seq"].transform("size")

Q = (SQL / "01_running_total_duckdb.sql").read_text(encoding="utf-8")
Q2 = (SQL / "02_rows_date_only_duckdb.sql").read_text(encoding="utf-8")


def run(df, threads=1, q=Q):
    con = duckdb.connect(); con.execute(f"SET threads={threads}")
    con.register("t_df", df[["acct", "d", "seq", "amount"]])
    con.execute("CREATE TABLE tx AS SELECT acct, CAST(d AS DATE) d, seq, amount FROM t_df")
    out = con.execute(q).df(); con.close()
    return out.sort_values(["acct", "d", "seq"]).reset_index(drop=True)


base = run(tx.sort_values(["acct", "d", "seq"]))
base["n_day"] = tx.sort_values(["acct", "d", "seq"])["n_day"].values
base["last_of_day"] = base["seq"] == base.groupby(["acct", "d"])["seq"].transform("max")

# pandas で正しい累計を別に計算して確かめる
ref = tx.sort_values(["acct", "d", "seq"]).groupby("acct")["amount"].cumsum().values
assert (base["bal_rows_unique"].values == ref).all()
eod = base.groupby(["acct", "d"])["bal_rows_unique"].transform("last")
assert (base["bal_range"].values == eod.values).all()            # RANGE は「その日の最後の残高」と同じ

# ---------- ① 枠を書かない（RANGE）と、行ごとの正しい累計との違い ----------
base["range_differs"] = base["bal_range"] != base["bal_rows_unique"]
multi = base["n_day"] >= 2
r1 = {"rows": int(len(base)), "rows_on_multi_days_pct": float(multi.mean() * 100),
      "range_differs_pct": float(base["range_differs"].mean() * 100),
      "range_differs_pct_on_multi_days": float(base.loc[multi, "range_differs"].mean() * 100),
      "last_row_of_day_equal_pct": float((~base.loc[base["last_of_day"], "range_differs"]).mean() * 100)}
byn = base.assign(n=base["n_day"].clip(upper=5)).groupby("n").agg(行数=("amount", "size"), 違う行の割合=("range_differs", lambda s: s.mean() * 100)).reset_index()
byn["n"] = byn["n"].map({1: "1行", 2: "2行", 3: "3行", 4: "4行", 5: "5行以上"})
byn.round(2).to_csv(RES / "range_vs_rows_by_rows_per_day.csv", index=False)

# ---------- ② ROWS＋日付だけで並べる：表に入っている順を変えて20回 ----------
runs = []
for i in range(20):
    sh = tx.sample(frac=1, random_state=SEED + i)                 # 行の入っている順だけを変える
    runs.append(run(sh, threads=1 if i < 10 else 2, q=Q2)["bal_rows_date_only"].values)
runs = np.array(runs)
varies = (runs != runs[0]).any(axis=0)
wrong_each = (runs != base["bal_rows_unique"].values).mean(axis=1) * 100
eod_idx = base["last_of_day"].values
r2 = {"runs": 20, "rows_value_changes_between_runs_pct": float(varies.mean() * 100),
      "rows_value_changes_on_multi_days_pct": float(varies[multi.values].mean() * 100),
      "wrong_vs_unique_pct_mean": float(wrong_each.mean()), "wrong_vs_unique_pct_min": float(wrong_each.min()), "wrong_vs_unique_pct_max": float(wrong_each.max()),
      "same_select_equals_unique_pct": float((base["bal_rows_date_only"] == base["bal_rows_unique"]).mean() * 100),
      "alone_sorted_input_equals_unique_pct": float((run(tx.sort_values(["acct", "d", "seq"]), q=Q2)["bal_rows_date_only"].values == base["bal_rows_unique"].values).mean() * 100)}

# ---------- ③ 下流への影響：「残高がマイナスになった口座」を数える ----------
def neg_accounts(order_cols, asc):
    s = tx.sort_values(["acct", "d"] + order_cols, ascending=[True, True] + asc)
    bal = s.groupby("acct")["amount"].cumsum()
    g = pd.DataFrame({"acct": s["acct"].values, "bal": bal.values})
    return g.groupby("acct")["bal"].min()

mins = {"正しい順（日付＋その日の順番）": neg_accounts(["seq"], [True]),
        "同じ日は出金を先に": neg_accounts(["amount"], [True]),
        "同じ日は入金を先に": neg_accounts(["amount"], [False])}
mins["枠を書かない（その日の最後の残高だけ）"] = base.groupby("acct")["bal_range"].min()
neg = pd.DataFrame({k: (v < 0) for k, v in mins.items()})
truth = neg["正しい順（日付＋その日の順番）"]
r3 = []
for k in neg:
    r3.append({"数え方": k, "マイナスになった口座": int(neg[k].sum()), "正しい順との差": int(neg[k].sum() - truth.sum()),
               "見逃した口座": int((truth & ~neg[k]).sum()), "余分に数えた口座": int((~truth & neg[k]).sum()),
               "最低残高が正しい順と違う口座の割合": float((mins[k].values != mins["正しい順（日付＋その日の順番）"].values).mean() * 100)})
r3 = pd.DataFrame(r3); r3.round(2).to_csv(RES / "negative_balance_accounts.csv", index=False)
# 20回の実行（ROWS＋日付だけ）でのマイナス口座の数
neg_runs = [int((pd.Series(runs[i]).groupby(base["acct"].values).min() < 0).sum()) for i in range(20)]
r2["negative_accounts_min"], r2["negative_accounts_max"] = min(neg_runs), max(neg_runs)

# ---------- 例：1つの口座の1日 ----------
cand = base[(base["n_day"] == 4)].groupby(["acct", "d"]).filter(lambda g: (g["amount"] > 0).sum() == 1 and g["bal_rows_unique"].min() < 0 and g["bal_range"].iloc[0] > 0)
key = cand[["acct", "d"]].iloc[0]
exm = base[(base["acct"] == key["acct"]) & (base["d"] == key["d"])][["seq", "amount", "bal_range", "bal_rows_unique"]].copy()
prev = base[(base["acct"] == key["acct"]) & (base["d"] < key["d"])]["bal_rows_unique"].iloc[-1]
s2 = exm.sort_values("amount", ascending=False); exm["bal_deposit_first"] = (prev + s2["amount"].cumsum()).reindex(exm.index)
exm.to_csv(RES / "example_one_day.csv", index=False)

# ---------- 図 ----------
fig, ax = plt.subplots(figsize=(9, 3.2)); ax.axis("off")
cells = [[f"{int(r.seq)}", f"{int(r.amount):+,}", f"{int(r.bal_range):,}", f"{int(r.bal_rows_unique):,}", f"{int(r.bal_deposit_first):,}"] for r in exm.itertuples()]
tb = ax.table(cellText=cells, colLabels=["その日の\n順番", "入出金（円）", "① 枠を書かない\n（RANGE）", "③ ROWS＋一意な並び\n（正しい残高）", "② ROWS＋日付だけ\n（入金が先に並んだ場合）"],
              loc="center", cellLoc="right", colWidths=[0.1, 0.16, 0.2, 0.24, 0.3])
tb.auto_set_font_size(False); tb.set_fontsize(10.5); tb.scale(1, 2.0)
for (i, j), c in tb.get_celld().items():
    c.set_edgecolor("#d0d0d0")
    if i == 0: c.set_facecolor("#f0f0f0"); c.set_height(c.get_height() * 1.25)
    elif j == 3 and cells[i - 1][3].startswith("-"): c.set_facecolor("#fde3d8")
ax.set_title(f"同じ日に4行ある口座の例（前の日の残高 {int(prev):,}円）", pad=14)
save(fig, "a359_example_one_day.png", "色のついたセルは、残高がマイナスになった行。" + SRC, y=0.02)

fig, ax = plt.subplots(figsize=(9, 4.0))
ax.bar(byn["n"], byn["違う行の割合"], color=ORANGE)
for x, v, n in zip(byn["n"], byn["違う行の割合"], byn["行数"]): ax.text(x, v + 1.2, f"{v:.0f}%\n（{n:,}行）", ha="center", fontsize=9.5)
ax.set_ylim(0, 100); ax.set_xlabel("同じ口座・同じ日の明細の数"); ax.set_ylabel("累計が正しい残高と違う行の割合（%）")
ax.set_title("枠を書かないと、同じ日の最後の行以外は累計がずれる")
save(fig, "a359_range_differs_by_rows.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.0))
order = ["正しい順（日付＋その日の順番）", "同じ日は出金を先に", "同じ日は入金を先に", "枠を書かない（その日の最後の残高だけ）"]
v = [int(r3.loc[r3["数え方"] == k, "マイナスになった口座"].iloc[0]) for k in order]
ax.bar(range(4), v, color=[BLUE, ORANGE, ORANGE, GRAY])
for x, y in enumerate(v): ax.text(x, y + 8, f"{y:,}口座", ha="center", fontsize=10.5)
ax.set_xticks(range(4)); ax.set_xticklabels(["正しい順\n（日付＋その日の順番）", "同じ日は\n出金を先に", "同じ日は\n入金を先に", "枠を書かない\n（その日の最後の残高だけ）"])
ax.set_ylabel(f"残高がマイナスになった口座の数（{N_ACCT:,}口座中）"); ax.set_title("同じ日の中の並び方で、「残高がマイナスになった口座」の数が変わる")
save(fig, "a359_negative_accounts.png", SRC)

main = {"range": r1, "negative": r3.round(3).to_dict("records"), "by_rows_per_day": byn.round(3).to_dict("records"),
        "accounts": N_ACCT, "days": N_DAY,
        "rows_date_only_fixed": {k: r2[k] for k in ("runs", "rows_value_changes_on_multi_days_pct", "same_select_equals_unique_pct", "alone_sorted_input_equals_unique_pct")}}
json.dump(main, open(RES / "a359_main.json", "w"), ensure_ascii=False, indent=1)
# ②（ROWS＋日付だけ）の20回の結果は、同点の並びが実行のたびに変わるので、流し直すと数字が少し変わる。別のファイルに分ける
json.dump({"rows_date_only": r2, "neg_runs": neg_runs}, open(RES / "a359_runs_vary_each_time.json", "w"), ensure_ascii=False, indent=1)
print(r1); print(r2); print(r3.round(2).to_string()); print(byn.round(1).to_string()); print(exm.to_string(), prev); print(neg_runs)
