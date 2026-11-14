"""675 DISTINCT で重複を消すと、本当に2回あった同じ内容の取引は何件消えるのか

架空の10店・60日の売上明細（1取引1品目）を作る。品目は30。安い品ほど、同じ人が続けてもう一度買いやすい（90秒以内）。
明細には2種類の「同じ内容の行」がある：
  本当にあった取引：同じ店・同じ時刻（分）・同じ品目・同じ数量・同じ金額の取引が2回あった（取引番号は別）。
    続けて買った場合と、たまたま別の人が同じ分に同じものを買った場合がある
  取り込みの重複：同じ取引が2回取り込まれた行（取引番号も同じ）。取引の2%
重複の消し方を3通りで比べる：
  D1 DISTINCT（店・日・時刻（分）・品目・数量・金額）
  D2 DISTINCT（店・日・時刻（秒）・品目・数量・金額）
  T  取引番号で重複を消す
本当の売上（取り込みの重複だけを除いたもの）と比べ、消えた行の内訳と金額の差を数える。
3通りの件数と金額は SQL（DuckDB、1スレッド）でも出し、Python と一致を確かめる。数字は置いた買い方で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の店の売上明細（作成者が乱数で作成、seed 675）"
rng = np.random.default_rng(675)
NI = 30
price = np.sort(np.round(rng.lognormal(np.log(450), .8, NI), -1)).astype(int)
price = np.maximum(price, 100)
pop = rng.dirichlet(np.ones(NI) * 2)
rep_p = np.clip(0.18 * (300 / price) ** 0.9, 0.003, 0.25)       # 安い品ほど同じ日にもう一度買われやすい
rows = []
tid = 0
for s in range(10):
    for d in range(60):
        n = rng.poisson(80)
        items = rng.choice(NI, n, p=pop)
        qty = np.where(rng.random(n) < .85, 1, rng.integers(2, 4, n))
        sec = np.sort(rng.integers(8 * 3600, 21 * 3600, n))
        for it, q, t in zip(items, qty, sec):
            tid += 1
            rows.append((tid, s + 1, d, t, it, q, q * price[it], 0))
            if rng.random() < rep_p[it]:            # 同じ人が続けてもう一度買った（90秒以内）
                tid += 1
                rows.append((tid, s + 1, d, int(t + rng.integers(1, 91)), it, q, q * price[it], 1))
T0 = pd.DataFrame(rows, columns=["txn_id", "store", "day", "sec", "item", "qty", "amount", "is_repeat"])
dup = T0.sample(frac=.02, random_state=675).assign(is_load_dup=1)
T = pd.concat([T0.assign(is_load_dup=0), dup]).sort_values(["txn_id", "is_load_dup"]).reset_index(drop=True)
T["date"] = pd.Timestamp("2025-01-01") + pd.to_timedelta(T.day, "D")
T["time"] = T.sec.map(lambda x: f"{x // 3600:02d}:{x % 3600 // 60:02d}:{x % 60:02d}")
T["minute"] = T.time.str[:5]
T["item_name"] = T.item.map(lambda i: f"品目{i + 1:02d}")
out_cols = ["txn_id", "store", "date", "minute", "time", "item_name", "qty", "amount"]
DATA.mkdir(exist_ok=True)
T[out_cols].to_csv(DATA / "sales_lines.csv", index=False)

true_rows, true_amt = len(T0), int(T0.amount.sum())
k1 = ["store", "date", "minute", "item_name", "qty", "amount"]; k2 = ["store", "date", "time", "item_name", "qty", "amount"]
D1 = T.drop_duplicates(k1); D2 = T.drop_duplicates(k2); DT = T.drop_duplicates("txn_id")
res = {}
for name, D in [("none", T), ("D1", D1), ("D2", D2), ("T", DT)]:
    kept = set(D.txn_id)
    lost_genuine = int((~T0.txn_id.isin(kept)).sum())
    res[name] = {"rows": int(len(D)), "amount": int(D.amount.sum()), "rows_vs_true": int(len(D) - true_rows),
                 "amount_vs_true_pct": round(100 * (D.amount.sum() / true_amt - 1), 3), "genuine_lost": lost_genuine,
                 "load_dups_left": int(len(D) - len(D.drop_duplicates("txn_id")))}
con = duckdb.connect(); con.execute("SET threads=1"); con.register("sales_lines", T[out_cols])
q = (SQL / "02_distinct_duckdb.sql").read_text(encoding="utf-8").split(";")[0]
sq = con.execute(q).df().set_index("method")
for m in ["D1", "D2", "T"]:
    assert int(sq.loc[m, "n_rows"]) == res[m]["rows"] and int(sq.loc[m, "amount"]) == res[m]["amount"]
# 品目ごと（価格帯）
band = pd.cut(price, [0, 300, 600, 1200, 10**6], labels=["300円以下", "301〜600円", "601〜1,200円", "1,201円以上"])
lost = T0[~T0.txn_id.isin(D1.txn_id)]
B = pd.DataFrame({"band": band[T0.item], "amount": T0.amount}).groupby("band", observed=False).amount.sum().to_frame("true_amount")
B["lost_amount"] = pd.DataFrame({"band": band[lost.item], "amount": lost.amount}).groupby("band", observed=False).amount.sum()
B["lost_pct"] = 100 * B.lost_amount / B.true_amount
B["items"] = pd.Series(band).value_counts().reindex(B.index)
B.round(3).to_csv(RES / "by_price_band.csv")
pd.DataFrame(res).T.to_csv(RES / "summary.csv")
out = {"stores": 10, "days": 60, "items": NI, "true_rows": true_rows, "true_amount": true_amt,
       "genuine_repeats": int(T0.is_repeat.sum()), "genuine_repeat_pct": round(100 * T0.is_repeat.mean(), 2),
       "load_dups": int(len(dup)), "methods": res,
       "by_band_lost_pct": {str(k): round(float(v), 2) for k, v in B.lost_pct.items()},
       "D1_lost_repeat": int(((T0.is_repeat == 1) & ~T0.txn_id.isin(D1.txn_id)).sum()),
       "D1_lost_coincidence": int(((T0.is_repeat == 0) & ~T0.txn_id.isin(D1.txn_id)).sum()),
       "repeats_same_minute_pct": round(100 * float(((T0.is_repeat == 1) & ~T0.txn_id.isin(D1.txn_id)).sum() / T0.is_repeat.sum()), 1)}
json.dump(out, open(RES / "a675_main.json", "w"), ensure_ascii=False, indent=1)

LAB = {"D1": "DISTINCT（時刻は分まで）", "D2": "DISTINCT（時刻は秒まで）", "T": "取引番号で消す"}
# 図1：消えた行の内訳
fig, ax = plt.subplots(figsize=(8.5, 4))
ms = ["D1", "D2", "T"]
rem_load = [len(dup) - res[m]["load_dups_left"] for m in ms]
lost_g = [res[m]["genuine_lost"] for m in ms]
y = np.arange(3)[::-1]
ax.barh(y, rem_load, color=BLUE, label="取り込みの重複（消すべき行）")
ax.barh(y, lost_g, left=rem_load, color=ORANGE, label="本当にあった取引（消してはいけない行）")
for yy, a, b in zip(y, rem_load, lost_g): ax.text(a + b, yy, f" 本当の取引 {b:,}件", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels([LAB[m] for m in ms]); ax.set_xlabel("消えた行の数")
ax.set_xlim(0, (max(rem_load) + max(lost_g)) * 1.35); ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.set_title(f"分までの DISTINCT は、取り込みの重複 {len(dup):,}行と一緒に本当の取引も消す")
save(fig, "a675_removed.png", SRC)
# 図2：金額の差
fig, ax = plt.subplots(figsize=(8.5, 3.8))
v = [res[m]["amount_vs_true_pct"] for m in ["none"] + ms]
labs = ["重複を消さない"] + [LAB[m] for m in ms]
ax.barh(labs[::-1], v[::-1], color=[BLUE, GREEN, ORANGE, GRAY][::-1])
for i, vv in enumerate(v[::-1]): ax.text(vv, i, f" {vv:+.2f}%", va="center", ha="left" if vv >= 0 else "right", fontsize=9)
ax.axvline(0, color=INK, lw=.8); ax.set_xlabel("本当の売上との差（%）"); ax.set_xlim(min(v) * 1.6, max(v) * 1.6)
ax.set_title("売上の合計は、消さなくても、消しすぎてもずれる")
save(fig, "a675_amount.png", SRC)
# 図3：価格帯ごと
fig, ax = plt.subplots(figsize=(8.5, 3.8))
ax.bar(B.index.astype(str), B.lost_pct, color=ORANGE)
for i, vv in enumerate(B.lost_pct): ax.text(i, vv + .1, f"{vv:.1f}%", ha="center", fontsize=9)
ax.set_ylabel("分までの DISTINCT で消えた売上（%）"); ax.set_xlabel("品目の価格帯")
ax.set_title("安い品ほど、本当に2回買われた取引が消える")
save(fig, "a675_by_band.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
