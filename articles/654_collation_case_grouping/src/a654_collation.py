"""654 大文字と小文字を区別するかしないかで、GROUP BY の件数とつながる行はどれだけ変わるのか

2つの場面を架空のデータで作る。
  (1) メールアドレス：同じ人が注文ごとに「Taro@Example.com」「taro@example.com」のように書き方を変える。
      本当は大文字小文字を区別しない値なので、区別する照合だと1人が何人にも分かれ、顧客表ともつながらない。
  (2) クーポンの番号：英大文字・小文字・数字6けた（大文字小文字に意味がある）。区別しない照合だと別の番号が1つにまとまる。
DuckDB（1スレッド）の COLLATE NOCASE と pandas の結果が一致することを確かめる。seed 654。
"""
import json, string
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN
DATA.mkdir(exist_ok=True)
SRC = "出典：架空の顧客・注文・クーポン（作成者が乱数で作成、seed 654）"
rng = np.random.default_rng(654)
N_CUST, N_ORD = 8000, 40000
first = ["taro", "hanako", "ken", "yui", "sho", "mio", "daiki", "rina", "kota", "emi", "yuto", "saki"]
doms = ["example.com", "example.jp", "mail.example.net", "sample.co.jp"]
emails = []
seen = set()
while len(emails) < N_CUST:
    e = f"{rng.choice(first)}.{rng.integers(1, 99999):05d}@{rng.choice(doms)}"
    if e not in seen:
        seen.add(e); emails.append(e)
CUST = pd.DataFrame({"customer_id": np.arange(1, N_CUST + 1), "email": emails})


def variant(e, r):
    u = r.random()
    if u < 0.80:
        return e
    loc, dom = e.split("@")
    if u < 0.90:
        return loc.capitalize() + "@" + dom          # 先頭だけ大文字
    if u < 0.95:
        return loc + "@" + dom.capitalize()          # ドメインの先頭が大文字
    return e.upper()                                  # 全部大文字


cust_of = rng.integers(0, N_CUST, N_ORD)
ORD = pd.DataFrame({"order_id": np.arange(1, N_ORD + 1), "email": [variant(emails[i], rng) for i in cust_of],
                    "amount": rng.integers(800, 20000, N_ORD) // 10 * 10, "true_cust": cust_of})
alph = np.array(list(string.ascii_letters + string.digits))
# クーポン：あえて短い番号（4けた）と6けたの2種類
def codes(n, k):
    out = set()
    while len(out) < n:
        out.add("".join(rng.choice(alph, k)))
    return sorted(out)
cp4 = codes(20000, 4); cp6 = codes(20000, 6)
COUP = pd.DataFrame({"code": cp4 + cp6, "length": [4] * len(cp4) + [6] * len(cp6)})
CUST.to_csv(DATA / "customers.csv", index=False)
ORD.drop(columns="true_cust").to_csv(DATA / "orders.csv", index=False)
COUP.to_csv(DATA / "coupons_used.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1")
con.register("customers", CUST); con.register("orders", ORD.drop(columns="true_cust")); con.register("coupons_used", COUP)
q = [x for x in (SQL / "02_collation_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
r1 = con.execute(q[0]).df().iloc[0]; r2 = con.execute(q[1]).df().iloc[0]; r3 = con.execute(q[2]).df().iloc[0]; r4 = con.execute(q[3]).df().iloc[0]
# pandas
n_cs = ORD.email.nunique(); n_ci = ORD.email.str.lower().nunique(); n_true = ORD.true_cust.nunique()
un_cs = ~ORD.email.isin(set(CUST.email)); un_ci = ~ORD.email.str.lower().isin(set(CUST.email.str.lower()))
assert r1.n_case_sensitive == n_cs and r1.n_nocase == n_ci and r1.n_lower == n_ci
assert r2.unmatched_cs == un_cs.sum() and r3.unmatched_ci == un_ci.sum()
c4 = COUP[COUP.length == 4].code; c6 = COUP[COUP.length == 6].code
assert r4.n_cs == len(COUP) and r4.n_ci == COUP.code.str.lower().nunique()
# 人ごとの分かれ方
split = ORD.groupby("true_cust").email.nunique()
merged4 = len(c4) - c4.str.lower().nunique(); merged6 = len(c6) - c6.str.lower().nunique()
# 1人あたりの購入回数・金額の見え方（区別する場合）
per_cs = ORD.groupby("email").amount.agg(["size", "sum"]); per_true = ORD.groupby("true_cust").amount.agg(["size", "sum"])
out = {"customers": N_CUST, "orders": N_ORD, "share_orders_with_case_variant_pct": round(float((ORD.email != [emails[i] for i in ORD.true_cust]).mean() * 100), 1),
       "distinct_email_case_sensitive": int(n_cs), "distinct_email_nocase": int(n_ci), "true_buyers": int(n_true),
       "overcount_people_pct": round((n_cs / n_true - 1) * 100, 1),
       "buyers_split_into_2plus_pct": round(float((split >= 2).mean() * 100), 1),
       "unmatched_orders_case_sensitive": int(un_cs.sum()), "unmatched_orders_pct": round(float(un_cs.mean() * 100), 1),
       "unmatched_amount_pct": round(float(ORD.amount[un_cs].sum() / ORD.amount.sum() * 100), 1),
       "unmatched_orders_nocase": int(un_ci.sum()),
       "orders_per_buyer_true": round(float(per_true["size"].mean()), 2), "orders_per_buyer_cs": round(float(per_cs["size"].mean()), 2),
       "repeat_rate_true_pct": round(float((per_true["size"] >= 2).mean() * 100), 1), "repeat_rate_cs_pct": round(float((per_cs["size"] >= 2).mean() * 100), 1),
       "coupon4_codes": int(len(c4)), "coupon4_merged_under_nocase": int(merged4), "coupon4_merged_pct": round(merged4 / len(c4) * 100, 2),
       "coupon6_codes": int(len(c6)), "coupon6_merged_under_nocase": int(merged6), "coupon6_merged_pct": round(merged6 / len(c6) * 100, 3)}
json.dump(out, open(RES / "a654_main.json", "w"), ensure_ascii=False, indent=1)
pd.Series(out).to_csv(RES / "summary.csv", header=["value"])

# 図1：人数
fig, ax = plt.subplots(figsize=(8, 3.4))
lab = ["本当の購入者", "区別しない（NOCASE・LOWER）", "区別する"]
val = [n_true, n_ci, n_cs]
ax.barh(lab[::-1], val[::-1], color=[ORANGE, BLUE, GRAY][::-1])
for i, v in enumerate(val[::-1]):
    ax.text(v, i, f" {v:,}人", va="center", fontsize=9)
ax.set_xlim(0, max(val) * 1.18); ax.set_xlabel("メールアドレスで数えた購入者の数")
ax.set_title(f"区別すると、同じ人が別の人に分かれて {out['overcount_people_pct']:.0f}% 多く数える")
save(fig, "a654_people.png", SRC)
# 図2：リピート率・つながらない注文
fig, axs = plt.subplots(1, 2, figsize=(9, 3.5))
axs[0].bar(["本当", "区別する"], [out["repeat_rate_true_pct"], out["repeat_rate_cs_pct"]], color=[GRAY, ORANGE])
for i, v in enumerate([out["repeat_rate_true_pct"], out["repeat_rate_cs_pct"]]):
    axs[0].text(i, v + 1, f"{v:.1f}%", ha="center", fontsize=9)
axs[0].set_ylabel("2回以上買った人の割合（%）"); axs[0].set_title("リピートの割合"); axs[0].set_ylim(0, 100)
axs[1].bar(["区別する", "区別しない"], [out["unmatched_orders_pct"], un_ci.mean() * 100], color=[ORANGE, BLUE])
axs[1].text(0, out["unmatched_orders_pct"] + 0.5, f"{out['unmatched_orders_pct']:.1f}%", ha="center", fontsize=9)
axs[1].text(1, 0.5, "0%", ha="center", fontsize=9)
axs[1].set_ylabel("顧客表とつながらない注文（%）"); axs[1].set_title("顧客表とのつながり")
fig.tight_layout(); save(fig, "a654_repeat_join.png", SRC)
# 図3：クーポン
fig, ax = plt.subplots(figsize=(8, 3.4))
ax.bar(["4けたの番号（2万個）", "6けたの番号（2万個）"], [merged4, merged6], color=[ORANGE, BLUE], width=0.5)
for i, v in enumerate([merged4, merged6]):
    ax.text(i, v + 20, f"{v:,}個", ha="center", fontsize=9)
ax.set_ylabel("区別しないと別の番号と\n1つにまとまる番号の数"); ax.set_title("大文字小文字に意味のある番号は、区別しないと重なる")
save(fig, "a654_coupons.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
