"""552 訂正を「取消（赤）＋再登録（黒）」で入れる伝票では、件数と金額をどう数えればよいのか

架空の売上伝票（2025年、はじめの登録 20,000件）を作り、一部を赤黒で訂正する（金額の誤り・数量の誤り・取引そのものの取消）。
訂正は、もとの取引と同じ月に入るものと、翌月以降に入るものがある。訂正をさらに訂正する（2回目の赤黒）ものも少し混ぜる。
件数と金額を5通りで数え、最後に有効な伝票だけを数えた値（正しい値）と比べる。
  N1 すべての行を数える／金額はプラスの行だけ足す
  N2 赤を除いて数える（通常＋黒）／金額もプラスの行だけ
  N3 行をすべて足す（件数は 通常＋黒−赤）
  N4 最後に有効な伝票だけ（取り消されていない通常と黒）＝正しい値
月別は「入力した日の月」と「もとの取引日の月」で比べる。Python と SQL（DuckDB、1スレッド）で N4 が一致することを確かめる。
数字は、置いた訂正の起きやすさで決まる。会計処理の助言ではない。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の売上伝票（作成者が乱数で作成、seed 552）"
rng = np.random.default_rng(552)
N = 20000
days = pd.date_range("2025-01-01", "2025-12-31")
rows = []
rid = 0
def add(slip, kind, ref, entry, orig, amt):
    global rid
    rid += 1
    rows.append((rid, slip, kind, ref, entry, orig, int(amt)))

slip_no = 100000
orig_dates = np.sort(rng.choice(days, N))
P_FIX, P_CANCEL, P_LATE, P_TWICE = 0.06, 0.015, 0.35, 0.10   # 金額の訂正・取引の取消・訂正が翌月以降に入る・訂正をもう一度訂正する
for d in orig_dates:
    d = pd.Timestamp(d)
    slip_no += 1; s0 = slip_no
    amt = int(round(rng.lognormal(9.6, 0.8), -1))
    add(s0, "通常", None, d, d, amt)
    u = rng.random()
    if u < P_FIX + P_CANCEL:
        late = rng.random() < P_LATE
        lag = int(rng.integers(20, 75)) if late else int(rng.integers(0, 8))
        e = min(d + pd.Timedelta(days=lag), pd.Timestamp("2025-12-31")) if not late else d + pd.Timedelta(days=lag)
        if e.month == d.month and late:
            e = (d + pd.offsets.MonthBegin(1)) + pd.Timedelta(days=int(rng.integers(0, 20)))
        if not late and e.month != d.month:
            e = d
        add(s0, "赤", s0, e, d, -amt)
        if u < P_FIX:   # 金額の訂正：黒で入れ直す
            new = int(round(amt * rng.choice([0.5, 0.8, 0.9, 1.1, 1.2, 2.0], p=[0.1, 0.2, 0.25, 0.25, 0.1, 0.1]), -1))
            slip_no += 1; s1 = slip_no
            add(s1, "黒", s0, e, d, new)
            if rng.random() < P_TWICE:   # 黒をもう一度訂正する
                e2 = e + pd.Timedelta(days=int(rng.integers(0, 10)))
                add(s1, "赤", s1, e2, d, -new)
                new2 = int(round(new * rng.choice([0.9, 1.1]), -1))
                slip_no += 1
                add(slip_no, "黒", s1, e2, d, new2)
S = pd.DataFrame(rows, columns=["row_id", "slip_no", "kind", "ref_slip_no", "entry_date", "orig_date", "amount"])
S["ref_slip_no"] = S.ref_slip_no.astype("Int64")
S.assign(entry_date=S.entry_date.dt.strftime("%Y-%m-%d"), orig_date=S.orig_date.dt.strftime("%Y-%m-%d")).to_csv(DATA / "slips.csv", index=False)

# --- 数え方
red = S[S.kind == "赤"]
cancelled = set(red.ref_slip_no.dropna().astype(int))
valid = S[S.kind.isin(["通常", "黒"]) & ~S.slip_no.isin(cancelled)]
pos = S[S.amount > 0]
nored = S[S.kind != "赤"]
M = {"N1": (len(S), int(pos.amount.sum())),
     "N2": (len(nored), int(nored.amount.sum())),
     "N3": (int(len(nored) - len(red)), int(S.amount.sum())),
     "N4": (len(valid), int(valid.amount.sum()))}
true_n, true_a = M["N4"]
summ = {k: {"count": n, "amount": a, "count_over_pct": round(100 * (n / true_n - 1), 2), "amount_over_pct": round(100 * (a / true_a - 1), 2),
            "count_over": n - true_n, "amount_over": a - true_a} for k, (n, a) in M.items()}
pd.DataFrame(summ).T.to_csv(RES / "summary.csv")

# --- SQL（DuckDB）で N4 を出す
con = duckdb.connect(); con.execute("SET threads=1"); con.register("slips", S)
n_sql, a_sql = con.execute((SQL / "02_red_black_duckdb.sql").read_text(encoding="utf-8")).fetchone()
assert (n_sql, int(a_sql)) == M["N4"]

# --- 月別：入力日の月とともとの取引日の月（金額は全行を足す＝N3 の金額）
mon = pd.DataFrame({"entry": S.groupby(S.entry_date.dt.to_period("M")).amount.sum(),
                    "orig": S.groupby(S.orig_date.dt.to_period("M")).amount.sum()}).fillna(0)
mon["diff_pct"] = (mon.entry / mon.orig - 1) * 100
mon.round(2).to_csv(RES / "by_month.csv")
m25 = mon[mon.index.year == 2025]
spill = S[(S.kind == "赤") & (S.entry_date.dt.to_period("M") != S.orig_date.dt.to_period("M"))]
spill_next_year = S[S.entry_date.dt.year > 2025]

# 種類の内訳
kinds = S.kind.value_counts().to_dict()
n_fix = int((S.kind == "黒").sum()); n_red = int(len(red))
n_cancel_only = int(len(red) - n_fix)
chains2 = int(S[(S.kind == "赤")].ref_slip_no.isin(S[S.kind == "黒"].slip_no).sum())

out = {"rows": len(S), "kinds": kinds, "originals": N, "red": n_red, "black": n_fix, "cancel_only": n_cancel_only, "second_corrections": chains2,
       "summary": summ, "red_in_later_month": int(len(spill)), "rows_entered_2026": int(len(spill_next_year)),
       "month_diff_pct": {"min": round(float(m25.diff_pct.min()), 2), "max": round(float(m25.diff_pct.max()), 2)},
       "amount_2025_entry_basis": int(m25.entry.sum()), "amount_2025_orig_basis": int(m25.orig.sum())}
json.dump(out, open(RES / "a552_main.json", "w"), ensure_ascii=False, indent=1, default=int)

# --- 図1：件数と金額の過大
lab = {"N1": "すべての行／プラスの行の金額", "N2": "赤を除く（通常＋黒）", "N3": "全行を足す（件数は 黒−赤 も足す）", "N4": "最後に有効な伝票だけ（正しい値）"}
ks = ["N1", "N2", "N3", "N4"]
COL = {"N1": ORANGE, "N2": BLUE, "N3": LIGHT, "N4": GREEN}
fig, ax = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True, gridspec_kw={"wspace": 0.15})
for j, (col, unit) in enumerate([("count_over_pct", "件数"), ("amount_over_pct", "金額")]):
    v = [summ[k][col] for k in ks][::-1]
    ax[j].barh([lab[k] for k in ks][::-1], v, color=[COL[k] for k in ks][::-1])
    for i, x in enumerate(v):
        ax[j].text(x, i, f" {x:+.2f}%", va="center", fontsize=9)
    ax[j].axvline(0, color=GRAY, lw=0.8); ax[j].set_xlim(min(0, min(v)) - 1, max(v) * 1.45 + 0.5)
    ax[j].set_title(f"{unit}：正しい値との差")
fig.suptitle(f"正しい値：{true_n:,}件、{true_a/1e6:,.1f}百万円", fontsize=10, y=0.02)
save(fig, "a552_count_amount.png", SRC, y=-0.06)

# --- 図2：月別（入力日の月 vs もとの取引日の月）
fig, ax = plt.subplots(figsize=(8.5, 4))
x = np.arange(12)
ax.bar(x, m25.diff_pct.values, color=[ORANGE if v < 0 else BLUE for v in m25.diff_pct.values])
for i, v in enumerate(m25.diff_pct.values):
    ax.text(i, v, f"{v:+.2f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8)
ax.axhline(0, color=GRAY, lw=0.8); ax.set_xticks(x); ax.set_xticklabels([f"{i}月" for i in range(1, 13)])
ax.set_ylabel("もとの取引日の月で数えた値との差（%）")
ax.set_title("月の売上を「赤黒を入力した日の月」で数えたときの差")
save(fig, "a552_by_month.png", SRC)

# --- 図3：行の内訳
fig, ax = plt.subplots(figsize=(8, 3.8))
parts = [("取り消されていない通常", int(((S.kind == "通常") & ~S.slip_no.isin(cancelled)).sum()), GREEN),
         ("取り消された通常", int(((S.kind == "通常") & S.slip_no.isin(cancelled)).sum()), LIGHT),
         ("有効な黒（再登録）", int(((S.kind == "黒") & ~S.slip_no.isin(cancelled)).sum()), GREEN),
         ("取り消された黒", int(((S.kind == "黒") & S.slip_no.isin(cancelled)).sum()), LIGHT),
         ("赤（取消）", n_red, ORANGE)]
names = [p[0] for p in parts][::-1]; vals = [p[1] for p in parts][::-1]
ax.barh(names, vals, color=[p[2] for p in parts][::-1])
for i, v in enumerate(vals):
    ax.text(v, i, f" {v:,}", va="center", fontsize=9)
ax.set_xlim(0, max(vals) * 1.15); ax.set_xlabel("行数")
ax.set_title(f"伝票の行の内訳：{len(S):,}行のうち、最後に有効なのは緑の{true_n:,}行")
save(fig, "a552_rows.png", SRC, y=-0.08)
print(json.dumps(out, ensure_ascii=False, indent=1, default=int))
