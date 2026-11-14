"""743 退会した会員の番号を新しい会員に使い回すと、何人の新しい会員に前の人の購入がつくのか

架空の会員。2021〜2025年の5年間。番号は 1〜4,000。
最初の4,000人が2021年1月〜2022年12月に入会し、一部が退会する。退会した番号は、退会の30〜400日後に新しい人へ使い回す。
購入は在籍中だけに起きる（1人の月あたりの購入回数は人ごとに違う）。
購入表には会員の番号しか入っていない。
  番号だけでつなぐ：使い回された番号の新しい人に、前の人の購入もつく
  番号と在籍期間でつなぐ：入会日以上・退会日より前の購入だけ
新しい人（2人目）について、まちがってついた購入の数、初回購入月のずれ、「入会前から買っていた」ように見える人を数える。
DuckDB（1スレッド）の結果と pandas の結果の一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空の会員と購入（作成者が乱数で作成、seed 743）"
rng = np.random.default_rng(743)
START, END = pd.Timestamp("2021-01-01"), pd.Timestamp("2025-12-31")
NNO = 4000
rows = []; pid = 0
for no in range(1, NNO + 1):
    j = START + pd.Timedelta(days=int(rng.integers(0, 730)))
    while j <= END:
        pid += 1
        stay = rng.exponential(1800)
        l = j + pd.Timedelta(days=int(stay) + 1)
        rows.append((pid, no, j, l if l <= END else pd.NaT))
        if l > END:
            break
        j = l + pd.Timedelta(days=int(rng.integers(30, 401)))
M = pd.DataFrame(rows, columns=["person_id", "member_no", "joined_on", "left_on"])
M["generation"] = M.groupby("member_no").cumcount() + 1

prs = []
for r in M.itertuples():
    end = r.left_on if pd.notna(r.left_on) else END + pd.Timedelta(days=1)
    days = (end - r.joined_on).days
    rate = rng.gamma(1.5, 0.3) / 30                   # 1日あたり
    n = rng.poisson(rate * days)
    if n:
        d = r.joined_on + pd.to_timedelta(np.sort(rng.integers(0, days, n)), unit="D")
        prs.append(pd.DataFrame({"member_no": r.member_no, "purchased_on": d, "true_person": r.person_id}))
P = pd.concat(prs, ignore_index=True).sort_values(["purchased_on", "member_no"], kind="stable").reset_index(drop=True)
P.insert(0, "purchase_id", np.arange(1, len(P) + 1))
P["amount"] = rng.integers(500, 15000, len(P))
DATA.mkdir(exist_ok=True)
M[["person_id", "member_no", "joined_on", "left_on"]].to_csv(DATA / "members.csv", index=False, date_format="%Y-%m-%d")
P[["purchase_id", "member_no", "purchased_on", "amount"]].to_csv(DATA / "purchases.csv", index=False, date_format="%Y-%m-%d")

con = duckdb.connect(); con.execute("SET threads=1")
con.register("members", M[["person_id", "member_no", "joined_on", "left_on"]]); con.register("purchases", P[["purchase_id", "member_no", "purchased_on", "amount"]])
sql = (SQL / "02_join_duckdb.sql").read_text(encoding="utf-8")
for s in [x for x in ("\n".join(l for l in sql.splitlines() if not l.strip().startswith("--"))).split(";") if x.strip()][:-1]:
    con.execute(s)
Jn = con.execute("SELECT person_id, purchase_id, purchased_on FROM j_no").df()
Jp = con.execute("SELECT person_id, purchase_id, purchased_on FROM j_period").df()
# 正しいつなぎ方は、購入の本当の持ち主と一致する
chk = Jp.merge(P[["purchase_id", "true_person"]], on="purchase_id")
assert len(Jp) == len(P) and (chk.person_id == chk.true_person).all()
assert len(Jn) == P.merge(M, on="member_no").shape[0]

new = M[M.generation >= 2]
wrong = Jn.merge(M[["person_id", "joined_on", "left_on", "generation"]], on="person_id")
wrong = wrong[(wrong.purchased_on < wrong.joined_on) | (wrong.left_on.notna() & (wrong.purchased_on >= wrong.left_on))]
w_before = wrong[wrong.purchased_on < wrong.joined_on]
new_with_wrong = w_before[w_before.generation >= 2].person_id.nunique()
w_after = wrong[wrong.left_on.notna() & (wrong.purchased_on >= wrong.left_on)]
prev_after = w_after.person_id.nunique(); left_reused = int(M[M.left_on.notna() & M.member_no.isin(new.member_no)].shape[0])
first_no = Jn.groupby("person_id").purchased_on.min(); first_ok = Jp.groupby("person_id").purchased_on.min()
F = pd.DataFrame({"no": first_no, "ok": first_ok}).join(M.set_index("person_id")[["joined_on", "generation"]])
Fn = F[F.generation >= 2]
shift_m = ((Fn.ok.dt.year - Fn.no.dt.year) * 12 + (Fn.ok.dt.month - Fn.no.dt.month)).fillna(np.nan)
before_join = int((Fn.no < Fn.joined_on).sum())
amt_no = Jn.merge(P[["purchase_id", "amount"]], on="purchase_id").groupby("person_id").amount.sum()
amt_ok = Jp.merge(P[["purchase_id", "amount"]], on="purchase_id").groupby("person_id").amount.sum()
A = pd.DataFrame({"no": amt_no, "ok": amt_ok}).fillna(0).join(M.set_index("person_id")["generation"])
An = A[A.generation >= 2]
# 年ごとの「その年に買った人」の数（番号だけ・期間つき）
yr = lambda J: J.assign(y=J.purchased_on.dt.year).groupby("y").person_id.nunique()
Y = pd.DataFrame({"no": yr(Jn), "ok": yr(Jp)}); Y.to_csv(RES / "buyers_by_year.csv")
out = {"member_numbers": NNO, "persons": int(len(M)), "reused_persons": int(len(new)), "purchases": int(len(P)),
       "rows_no_join": int(len(Jn)), "rows_period_join": int(len(Jp)), "extra_rows": int(len(Jn) - len(Jp)),
       "new_with_wrong_purchases": int(new_with_wrong), "new_with_wrong_share": new_with_wrong / len(new),
       "new_first_purchase_before_join": before_join,
       "prev_with_purchases_after_leaving": int(prev_after), "left_and_reused_persons": left_reused,
       "new_first_month_shift_median": float(shift_m[shift_m > 0].median()),
       "new_amount_no": int(An.no.sum()), "new_amount_ok": int(An.ok.sum()), "new_amount_ratio": float(An.no.sum() / An.ok.sum()),
       "buyers_by_year": {int(k): {"no": int(v.no), "ok": int(v.ok)} for k, v in Y.iterrows()},
       "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a743_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：2人目以降の会員の購入額
fig, ax = plt.subplots(figsize=(9, 4.6))
s = An.sort_values("ok").reset_index(drop=True)
ax.scatter(s.ok / 1e4, s.no / 1e4, s=6, color=ORANGE, alpha=.5)
mx = s.no.max() / 1e4; ax.plot([0, mx], [0, mx], color=GRAY, lw=1)
ax.set_xlabel("正しい購入額（万円、番号と在籍期間でつなぐ）"); ax.set_ylabel("番号だけでつないだ購入額（万円）")
ax.set_title(f"使い回された番号の会員{len(new):,}人：線より上は前の人の購入がついた人")
save(fig, "a743_amount.png", SRC)

# 図2：初回購入月のずれ
fig, ax = plt.subplots(figsize=(9, 4.6))
sm = shift_m.dropna(); sm = sm[sm > 0]
ax.hist(sm, bins=np.arange(0, sm.max() + 3, 3), color=ORANGE)
ax.set_xlabel("初回購入月が早く見えた月数"); ax.set_ylabel("人数")
ax.set_title(f"{before_join:,}人が「入会前から買っていた」ように見えた（中央値 {np.median(sm):.0f}か月早い）")
save(fig, "a743_first_month.png", SRC)

# 図3：年ごとの購入者数
fig, ax = plt.subplots(figsize=(9, 4.6)); x = np.arange(len(Y))
ax.bar(x - .2, Y.ok, .4, color=BLUE, label="番号と在籍期間でつなぐ")
ax.bar(x + .2, Y.no, .4, color=ORANGE, label="番号だけでつなぐ")
ax.set_xticks(x); ax.set_xticklabels([f"{k}年" for k in Y.index]); ax.set_ylabel("その年に買った人の数（人）"); ax.legend(frameon=False)
ax.set_title("番号だけでつなぐと、1つの購入が今の人と前の人の両方に数えられる")
save(fig, "a743_buyers_year.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
