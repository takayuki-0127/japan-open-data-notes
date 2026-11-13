"""553 売掛金の滞留を、請求日から数えるか支払期日から数えるかで、区分ごとの金額はどれだけ動くのか

架空の取引先200社への請求（2024年7月〜2025年12月、約9,600件。支払条件は 30・60・90日の3通り）と入金を作り、
基準日 2025-12-31 で未入金の請求を、起算日を変えた2通りの年齢区分に分ける。
  請求日から：30日以内・31〜60日・61〜90日・90日超
  支払期日から：期日前・30日以内・31〜60日・61〜90日・90日超
区分ごとの金額、同じ請求がどの区分に移るか（対応表）、月末ごとの「90日超」の金額を比べる。
Python と SQL（DuckDB、1スレッド）で区分ごとの金額が一致することを確かめる。
数字は、置いた支払条件と入金の遅れ方で決まる。会計・与信の助言ではない。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の請求と入金（作成者が乱数で作成、seed 553）"
rng = np.random.default_rng(553)
ASOF = pd.Timestamp("2025-12-31")
NC = 200
terms = rng.choice([30, 60, 90], NC, p=[0.45, 0.35, 0.20])
size = rng.lognormal(12.3, 0.9, NC)
late_type = rng.choice(["期日どおり", "少し遅れる", "遅れがち"], NC, p=[0.70, 0.22, 0.08])
rows = []
iid = 0
for c in range(NC):
    k = int(rng.integers(2, 6))  # 月に何回請求するか（目安）
    dates = np.sort(rng.choice(pd.date_range("2024-07-01", "2025-12-31"), int(k * 18 * rng.uniform(0.6, 1.0)), replace=False))
    for d in dates:
        iid += 1
        d = pd.Timestamp(d)
        due = d + pd.Timedelta(days=int(terms[c]))
        amt = int(round(size[c] * rng.lognormal(0, 0.5), -2))
        lt = late_type[c]
        u = rng.random()
        if lt == "期日どおり":
            lag = int(rng.integers(-5, 3)) if u < 0.96 else int(rng.integers(5, 40))
        elif lt == "少し遅れる":
            lag = int(rng.integers(0, 25)) if u < 0.85 else int(rng.integers(25, 90))
        else:
            lag = int(rng.integers(10, 80)) if u < 0.80 else int(rng.integers(80, 260))
        paid = due + pd.Timedelta(days=lag)
        if rng.random() < 0.004:
            paid = pd.NaT   # 入金がないまま
        rows.append((iid, f"C{c+1:03d}", d, due, amt, paid, int(terms[c])))
I = pd.DataFrame(rows, columns=["invoice_id", "customer_id", "invoice_date", "due_date", "amount", "paid_date", "terms_days"])
I.assign(**{c: I[c].dt.strftime("%Y-%m-%d") for c in ["invoice_date", "due_date", "paid_date"]}).to_csv(DATA / "invoices.csv", index=False)

BI = ["1_30日以内", "2_31〜60日", "3_61〜90日", "4_90日超"]
BD = ["0_期日前"] + BI
def aging(asof):
    o = I[(I.invoice_date <= asof) & (I.paid_date.isna() | (I.paid_date > asof))].copy()
    o["dfi"] = (asof - o.invoice_date).dt.days
    o["dpd"] = (asof - o.due_date).dt.days
    o["b_inv"] = pd.cut(o.dfi, [-1, 30, 60, 90, 10**6], labels=BI).astype(str)
    o["b_due"] = np.where(o.dpd <= 0, "0_期日前", pd.cut(o.dpd, [-10**6, 30, 60, 90, 10**6], labels=BI).astype(str))
    return o

O = aging(ASOF)
tab = O.pivot_table(index="b_inv", columns="b_due", values="amount", aggfunc="sum", fill_value=0).reindex(index=BI, columns=BD, fill_value=0)
tabn = O.pivot_table(index="b_inv", columns="b_due", values="amount", aggfunc="size", fill_value=0).reindex(index=BI, columns=BD, fill_value=0)
tab.to_csv(RES / "crosstab_amount.csv"); tabn.to_csv(RES / "crosstab_count.csv")

# SQL（DuckDB）で突き合わせ
con = duckdb.connect(); con.execute("SET threads=1"); con.register("invoices", I)
q = (SQL / "02_aging_duckdb.sql").read_text(encoding="utf-8").replace("$asof", "DATE '2025-12-31'")
sq = con.execute(q).df()
chk = sq.pivot_table(index="bucket_invoice", columns="bucket_due", values="amount", aggfunc="sum", fill_value=0).reindex(index=BI, columns=BD, fill_value=0)
assert (chk.astype(int).values == tab.astype(int).values).all()

tot = int(O.amount.sum())
by_inv = tab.sum(axis=1); by_due = tab.sum(axis=0)
summ = {"open_invoices": int(len(O)), "open_amount": tot,
        "by_invoice_basis": {k: int(v) for k, v in by_inv.items()},
        "by_due_basis": {k: int(v) for k, v in by_due.items()},
        "share_invoice_basis": {k: round(100 * v / tot, 1) for k, v in by_inv.items()},
        "share_due_basis": {k: round(100 * v / tot, 1) for k, v in by_due.items()}}
over90_inv, over90_due = int(by_inv["4_90日超"]), int(by_due["4_90日超"])
summ["over90_ratio"] = round(over90_inv / over90_due, 2)
# 請求日から61〜90日のうち、期日前のもの
summ["inv61_90_not_due_amount"] = int(tab.loc["3_61〜90日", "0_期日前"])
summ["inv61_90_not_due_share"] = round(100 * tab.loc["3_61〜90日", "0_期日前"] / by_inv["3_61〜90日"], 1)
summ["inv_over90_not_due_amount"] = int(tab.loc["4_90日超", "0_期日前"])
summ["inv_over90_not_due_share"] = round(100 * tab.loc["4_90日超", "0_期日前"] / by_inv["4_90日超"], 1)
summ["over30_invoice_basis_pct"] = round(100 * (tot - by_inv["1_30日以内"]) / tot, 1)
summ["past_due_pct"] = round(100 * (tot - by_due["0_期日前"]) / tot, 1)
# 支払条件ごとの「90日超」
tt = O.assign(o90i=(O.b_inv == "4_90日超") * O.amount, o90d=(O.b_due == "4_90日超") * O.amount).groupby("terms_days")[["amount", "o90i", "o90d"]].sum()
tt.to_csv(RES / "over90_by_terms.csv")
summ["over90_by_terms"] = {int(k): {"invoice": int(r.o90i), "due": int(r.o90d)} for k, r in tt.iterrows()}

# 月末ごとの「90日超」
me = pd.date_range("2025-04-30", "2025-12-31", freq="ME")
ser = []
for d in me:
    o = aging(d)
    ser.append((d.strftime("%Y-%m"), int(o.amount.sum()), int(o[o.b_inv == "4_90日超"].amount.sum()), int(o[o.b_due == "4_90日超"].amount.sum())))
S = pd.DataFrame(ser, columns=["month_end", "open", "over90_invoice", "over90_due"])
S.to_csv(RES / "over90_by_month_end.csv", index=False)
summ["over90_month_end"] = S.to_dict(orient="records")
summ["customers"] = NC; summ["invoices"] = int(len(I))
json.dump(summ, open(RES / "a553_main.json", "w"), ensure_ascii=False, indent=1)

# --- 図1：区分ごとの金額
lab = {"0_期日前": "期日前", "1_30日以内": "30日以内", "2_31〜60日": "31〜60日", "3_61〜90日": "61〜90日", "4_90日超": "90日超"}
fig, ax = plt.subplots(figsize=(9, 4))
x = np.arange(len(BD)); w = 0.38
vi = [0] + [by_inv[b] / 1e6 for b in BI]; vd = [by_due[b] / 1e6 for b in BD]
ax.bar(x - w / 2, vi, w, color=BLUE, label="請求日から数える")
ax.bar(x + w / 2, vd, w, color=ORANGE, label="支払期日から数える")
for i in range(len(BD)):
    if i > 0: ax.text(i - w / 2, vi[i], f"{vi[i]:.1f}", ha="center", va="bottom", fontsize=8.5)
    ax.text(i + w / 2, vd[i], f"{vd[i]:.1f}", ha="center", va="bottom", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([lab[b] for b in BD]); ax.set_ylabel("未入金の金額（百万円）")
ax.legend(frameon=False); ax.set_title(f"2025年12月末の未入金 {tot/1e6:.1f}百万円を、起算日を変えて区分に分ける")
save(fig, "a553_buckets.png", SRC)

# --- 図2：対応表（金額）
fig, ax = plt.subplots(figsize=(8.5, 4))
M = tab.values / 1e6
ax.imshow(M, cmap="Blues", aspect="auto")
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        if M[i, j] > 0:
            ax.text(j, i, f"{M[i, j]:.1f}\n（{tabn.values[i, j]}件）", ha="center", va="center", fontsize=8.5, color="white" if M[i, j] > M.max() * 0.55 else INK)
ax.set_xticks(range(len(BD))); ax.set_xticklabels([lab[b] for b in BD]); ax.set_yticks(range(len(BI))); ax.set_yticklabels([lab[b] for b in BI])
ax.set_xlabel("支払期日から数えた区分"); ax.set_ylabel("請求日から数えた区分")
ax.set_title("同じ請求が、起算日を変えるとどの区分に入るか（百万円）")
for s in ax.spines.values(): s.set_visible(False)
save(fig, "a553_crosstab.png", SRC, y=-0.06)

# --- 図3：月末ごとの「90日超」
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.plot(S.month_end, S.over90_invoice / 1e6, marker="o", color=BLUE, label="請求日から90日超")
ax.plot(S.month_end, S.over90_due / 1e6, marker="s", color=ORANGE, label="支払期日から90日超")
ax.set_ylabel("金額（百万円）"); ax.legend(frameon=False); ax.set_ylim(0, None)
ax.set_xticks(range(len(S))); ax.set_xticklabels([str(int(m[5:])) + "月末" for m in S.month_end])
ax.set_title("月末ごとの「90日超」の金額")
save(fig, "a553_over90_month.png", SRC)
print(json.dumps({k: v for k, v in summ.items() if k != "over90_month_end"}, ensure_ascii=False, indent=1)); print(S)
