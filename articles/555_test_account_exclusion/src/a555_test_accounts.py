"""555 社内のテスト用アカウントの行を外す条件を変えると、利用者数と売上はどれだけ動くのか

架空のサービス（2025年10〜12月、利用者 20,000人）の利用ログと注文に、社内のテスト用アカウント 240件の行を混ぜる。
テスト用アカウントには3つの目印があるが、どれも全部には付いていない：
  E メールの末尾が社内のもの（@corp.example、架空）
  I ID がテスト用の範囲（900000〜900999）
  F テスト用フラグ（is_test_flag = 1）
外す条件を7通り（なし・E・I・F・E か I・E か F・3つのどれか）で比べ、利用者数・購入者数・売上・購入した人の割合（転換率）と、
外し漏れ・外しすぎの件数を数える。正しい値は、作成者が付けた「本当にテスト用か」で出す。
Python と SQL（DuckDB、1スレッド）で「3つのどれか」の値が一致することを確かめる。数字は置いた仮定で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空のサービスの利用ログと注文（作成者が乱数で作成、seed 555）"
rng = np.random.default_rng(555)
NU, NT = 20000, 240
# 一般の利用者
u = pd.DataFrame({"user_id": rng.choice(np.arange(100000, 899999), NU, replace=False)})
dom = rng.choice(["mail-a.example", "mail-b.example", "mail-c.example", "corp.example"], NU, p=[0.5, 0.3, 0.1996, 0.0004])
u["email"] = [f"u{i}@{d}" for i, d in zip(u.user_id, dom)]   # 社員が一般の利用者として使う例（ごく少数）
u["is_test_flag"] = 0; u["true_test"] = 0
# テスト用アカウント：目印の付き方を置く
t = pd.DataFrame({"user_id": np.r_[rng.choice(np.arange(900000, 901000), 150, replace=False), rng.choice(np.setdiff1d(np.arange(100000, 899999), u.user_id), NT - 150, replace=False)]})
t["email"] = [f"qa{i}@{'corp.example' if rng.random() < 0.6 else rng.choice(['mail-a.example', 'mail-b.example'])}" for i in t.user_id]
t["is_test_flag"] = (rng.random(NT) < 0.55).astype(int)
t["true_test"] = 1
U = pd.concat([u, t], ignore_index=True).sample(frac=1, random_state=555).reset_index(drop=True)
# 一般の利用者にも、ID 範囲のまちがった割り当て（移行で入った一般利用者）を少し置く
mig = rng.choice(np.setdiff1d(np.arange(900000, 901000), t.user_id), 30, replace=False)
U.loc[U[U.true_test == 0].sample(30, random_state=1).index, "user_id"] = mig

# セッションと注文
sess, orders = [], []
sid = oid = 0
for r in U.itertuples():
    if r.true_test:
        ns = int(rng.integers(5, 120)); p_buy = 0.65; nb = int(rng.integers(1, 8)); amt = lambda: int(rng.choice([1, 1, 100, 1980, 4980]))
    else:
        ns = int(rng.poisson(3)); p_buy = 0.06; nb = int(rng.integers(1, 3)); amt = lambda: int(round(rng.lognormal(8.2, 0.6), -1))
    for _ in range(ns):
        sid += 1; sess.append((sid, r.user_id))
    if ns > 0 and rng.random() < p_buy:
        for _ in range(nb):
            oid += 1; orders.append((oid, r.user_id, amt()))
S = pd.DataFrame(sess, columns=["session_id", "user_id"])
O = pd.DataFrame(orders, columns=["order_id", "user_id", "amount"])
U[["user_id", "email", "is_test_flag"]].to_csv(DATA / "users.csv", index=False)
U[["user_id", "true_test"]].to_csv(DATA / "users_true_label.csv", index=False)
S.to_csv(DATA / "sessions.csv", index=False); O.to_csv(DATA / "orders.csv", index=False)

E_ = U.email.str.endswith("@corp.example"); I_ = U.user_id.between(900000, 900999); F_ = U.is_test_flag == 1
conds = {"外さない": pd.Series(False, index=U.index), "E メール末尾": E_, "I ID の範囲": I_, "F フラグ": F_,
         "E か I": E_ | I_, "E か F": E_ | F_, "3つのどれか": E_ | I_ | F_, "正しい値": U.true_test == 1}
def metrics(excl):
    ex_ids = set(U.user_id[excl])
    s = S[~S.user_id.isin(ex_ids)]; o = O[~O.user_id.isin(ex_ids)]
    act = s.user_id.nunique(); buyers = o.user_id.nunique()
    return {"active_users": int(act), "buyers": int(buyers), "sales": int(o.amount.sum()), "orders": int(len(o)),
            "conversion_pct": round(100 * buyers / act, 2)}
rows = {}
active_ids = set(S.user_id)
for k, m in conds.items():
    r = metrics(m)
    tt = U.true_test == 1
    r["missed_test"] = int((tt & ~m & U.user_id.isin(active_ids)).sum())
    r["wrongly_excluded"] = int((~tt & m & U.user_id.isin(active_ids)).sum())
    rows[k] = r
R = pd.DataFrame(rows).T
truth = R.loc["正しい値"]
for c in ["active_users", "buyers", "sales", "orders"]:
    R[c + "_diff_pct"] = (R[c] / truth[c] - 1) * 100
R["conversion_diff_pt"] = R.conversion_pct - truth.conversion_pct
R.round(2).to_csv(RES / "by_condition.csv")

con = duckdb.connect(); con.execute("SET threads=1")
con.register("users", U[["user_id", "email", "is_test_flag"]]); con.register("sessions", S); con.register("orders", O)
a, b, s_, c = con.execute((SQL / "02_exclude_duckdb.sql").read_text(encoding="utf-8")).fetchone()
r3 = rows["3つのどれか"]
assert (a, b, int(s_)) == (r3["active_users"], r3["buyers"], r3["sales"]) and abs(c - r3["conversion_pct"]) < 0.01

marks = pd.DataFrame({"E": E_[U.true_test == 1], "I": I_[U.true_test == 1], "F": F_[U.true_test == 1]})
mark_count = marks.sum(axis=1).value_counts().sort_index().to_dict()
out = {"users": int(len(U)), "true_test": NT, "test_marks": {k: int(v) for k, v in marks.sum().items()},
       "test_by_number_of_marks": {int(k): int(v) for k, v in mark_count.items()},
       "test_sessions_share_pct": round(100 * S.user_id.isin(set(U.user_id[U.true_test == 1])).mean(), 1),
       "test_sales_share_pct": round(100 * O[O.user_id.isin(set(U.user_id[U.true_test == 1]))].amount.sum() / O.amount.sum(), 1),
       "by_condition": R.round(2).to_dict(orient="index")}
json.dump(out, open(RES / "a555_main.json", "w"), ensure_ascii=False, indent=1, default=float)

order = ["外さない", "E メール末尾", "I ID の範囲", "F フラグ", "E か I", "E か F", "3つのどれか", "正しい値"]
# --- 図1：利用者数・売上・転換率の差
fig, ax = plt.subplots(1, 3, figsize=(12, 4), sharey=True, gridspec_kw={"wspace": 0.12})
for j, (col, t_) in enumerate([("active_users_diff_pct", "利用者数（%）"), ("sales_diff_pct", "売上（%）"), ("conversion_diff_pt", "購入した人の割合（ポイント）")]):
    v = R.loc[order, col].values[::-1]
    ax[j].barh(order[::-1], v, color=[GREEN if k == "正しい値" else (BLUE if k == "3つのどれか" else LIGHT) for k in order[::-1]])
    for i, x in enumerate(v):
        ax[j].text(x, i, f" {x:+.2f}", va="center", fontsize=8.5)
    ax[j].axvline(0, color=GRAY, lw=0.8); ax[j].set_title("正しい値との差：" + t_, fontsize=11)
    ax[j].set_xlim(min(0, v.min()) * 2.5, max(v.max() * 1.4, 0.5))
save(fig, "a555_metrics.png", SRC, y=-0.03)

# --- 図2：外し漏れ・外しすぎ
fig, ax = plt.subplots(figsize=(8.5, 4))
o2 = [k for k in order if k not in ("外さない", "正しい値")]
x = np.arange(len(o2)); w = 0.38
ax.bar(x - w / 2, R.loc[o2, "missed_test"], w, color=ORANGE, label="外し漏れ（テスト用なのに残った）")
ax.bar(x + w / 2, R.loc[o2, "wrongly_excluded"], w, color=BLUE, label="外しすぎ（一般の利用者を外した）")
for i, k in enumerate(o2):
    ax.text(i - w / 2, R.loc[k, "missed_test"], f"{int(R.loc[k, 'missed_test'])}", ha="center", va="bottom", fontsize=8.5)
    ax.text(i + w / 2, R.loc[k, "wrongly_excluded"], f"{int(R.loc[k, 'wrongly_excluded'])}", ha="center", va="bottom", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels(o2); ax.set_ylabel("アカウント数"); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"テスト用アカウント{NT}件に対する、外し漏れと外しすぎ")
save(fig, "a555_miss.png", SRC)

# --- 図3：目印の付き方
fig, ax = plt.subplots(figsize=(8, 3.6))
combos = marks.astype(int).astype(str).agg("".join, axis=1).value_counts()
lab = {"100": "E だけ", "010": "I だけ", "001": "F だけ", "110": "E と I", "101": "E と F", "011": "I と F", "111": "3つとも", "000": "目印なし"}
keys = ["111", "110", "101", "011", "100", "010", "001", "000"]
vals = [int(combos.get(k, 0)) for k in keys]
ax.barh([lab[k] for k in keys][::-1], vals[::-1], color=[ORANGE if k == "000" else BLUE for k in keys][::-1])
for i, v in enumerate(vals[::-1]):
    ax.text(v, i, f" {v}", va="center", fontsize=9)
ax.set_xlabel("アカウント数"); ax.set_title(f"テスト用アカウント{NT}件に付いている目印（E メール末尾・I ID の範囲・F フラグ）")
save(fig, "a555_marks.png", SRC, y=-0.08)
print(json.dumps({k: v for k, v in out.items() if k != "by_condition"}, ensure_ascii=False, indent=1)); print(R[["active_users", "buyers", "sales", "conversion_pct", "missed_test", "wrongly_excluded", "sales_diff_pct", "conversion_diff_pt"]].round(2))
