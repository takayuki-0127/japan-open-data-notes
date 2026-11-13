"""635 ROLLUP の小計の行と、もともと区分が空の行を取り違えると、合計はどれだけずれるのか

架空の売上明細（6店×5区分、区分が空＝NULL の行を一定の割合で含む）を作り、
店×区分の ROLLUP を DuckDB（1スレッド）で出す。結果の表から「小計」を取り出す4通りの読み方を比べる。
  R0 正しい：GROUPING(category)=1 の行を小計とみなす
  R1 category IS NULL の行を小計とみなす（未分類の行も小計に見える）
  R2 category IS NULL の行を捨ててから区分の行を足して小計を作る（未分類の売上が落ちる）
  R3 COALESCE(category,'小計') で埋めてから、店ごとに '小計' の最初の行を使う（並び次第でどちらかを拾う）
未分類の割合を 0〜20% で動かして、全体の合計のずれも数える。数字は置いた割合で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の売上明細（作成者が乱数で作成、seed 635）"
DATA.mkdir(exist_ok=True)
STORES = [f"S{i}" for i in range(1, 7)]
CATS = ["食品", "飲料", "日用品", "衣料", "雑貨"]


def make(rng, n, p_null):
    store = rng.choice(STORES, n, p=[0.25, 0.2, 0.18, 0.15, 0.12, 0.10])
    cat = rng.choice(CATS, n, p=[0.35, 0.2, 0.2, 0.15, 0.1]).astype(object)
    cat[rng.random(n) < p_null] = None
    amount = np.round(rng.lognormal(7.3, 0.7, n), -1).astype(int)
    return pd.DataFrame({"line_id": np.arange(1, n + 1), "store": store, "category": cat, "amount": amount})


def rollup(df):
    con = duckdb.connect(); con.execute("SET threads=1"); con.register("sales", df)
    q = (SQL / "02_rollup_duckdb.sql").read_text(encoding="utf-8")
    r = con.execute(q).df()
    con.close()
    return r


def readings(r, df):
    """店ごとの小計と全体の合計を、4つの読み方で取り出す"""
    st = r[r.g_store == 0]
    truth = df.groupby("store").amount.sum()
    out = {}
    out["R0"] = st[st.g_cat == 1].set_index("store").amount
    out["R1"] = st[st.category.isna()].groupby("store").amount.sum()        # 小計＋未分類が足し合わさる
    out["R2"] = st[st.category.notna()].groupby("store").amount.sum()       # 未分類が落ちる
    # R3：埋めたあと店ごとに最初の '小計' を使う。並びは「区分の名前順で NULL が最後」の素朴な ORDER BY
    f = st.assign(category=st.category.fillna("小計")).sort_values(["store", "category"], kind="stable")
    out["R3"] = f[f.category == "小計"].groupby("store").amount.first()
    grand = {k: int(v.reindex(STORES).fillna(0).sum()) for k, v in out.items()}
    gtrue = int(df.amount.sum())
    store_err = {k: float(((v.reindex(STORES).fillna(0) - truth) / truth * 100).abs().max()) for k, v in out.items()}
    return out, grand, gtrue, store_err, truth


rng = np.random.default_rng(635)
df = make(rng, 20000, 0.08)
df.to_csv(DATA / "sales.csv", index=False)
r = rollup(df)
# Python での正解と、DuckDB の R0 が一致すること
out, grand, gtrue, store_err, truth = readings(r, df)
assert (out["R0"].reindex(STORES) == truth.reindex(STORES)).all()
assert int(r[(r.g_store == 1)].amount.iloc[0]) == gtrue
null_rows = int(r.category.isna().sum()); sub_rows = int((r.g_cat == 1).sum())
r.to_csv(RES / "rollup_result.csv", index=False)
uncls = df[df.category.isna()].groupby("store").amount.sum()

per_store = pd.DataFrame({"truth": truth, **{k: v for k, v in out.items()}, "unclassified": uncls}).reindex(STORES)
per_store.to_csv(RES / "per_store.csv")

# 未分類の割合を動かす（各 200 回）
rows = []
for p in [0, 0.01, 0.02, 0.05, 0.08, 0.1, 0.15, 0.2]:
    errs = {k: [] for k in ["R1", "R2", "R3"]}
    for rep in range(200):
        d = make(rng, 5000, p)
        rr = rollup(d)
        _, g, gt, _, _ = readings(rr, d)
        for k in errs:
            errs[k].append((g[k] - gt) / gt * 100)
    rows.append({"p_null": p, **{k: round(float(np.mean(v)), 3) for k, v in errs.items()}})
sens = pd.DataFrame(rows); sens.to_csv(RES / "by_null_share.csv", index=False)

summ = pd.DataFrame({"grand": grand, "diff_pct": {k: round((g - gtrue) / gtrue * 100, 2) for k, g in grand.items()},
                     "max_store_err_pct": {k: round(v, 2) for k, v in store_err.items()}})
summ.to_csv(RES / "summary.csv")
out_json = {"lines": len(df), "null_share_lines": round(float(df.category.isna().mean() * 100), 2),
            "null_share_amount": round(float(df[df.category.isna()].amount.sum() / gtrue * 100), 2),
            "rollup_rows": int(len(r)), "rows_with_null_category": null_rows, "subtotal_rows": sub_rows,
            "grand_true": gtrue, "summary": summ.reset_index().rename(columns={"index": "reading"}).to_dict(orient="records"),
            "by_null_share": rows}
json.dump(out_json, open(RES / "a635_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：4つの読み方の全体の合計のずれ
lab = {"R0": "GROUPING で小計を見分ける", "R1": "区分が NULL の行を小計とみなす", "R2": "NULL の行を捨てて区分を足す", "R3": "NULL を「小計」で埋め、最初の行を使う"}
ks = ["R0", "R1", "R2", "R3"]; col = [GREEN, ORANGE, BLUE, LIGHT]
fig, ax = plt.subplots(figsize=(8.5, 3.6))
v = [summ.loc[k, "diff_pct"] for k in ks]
ax.barh([lab[k] for k in ks][::-1], v[::-1], color=col[::-1])
for i, x in enumerate(v[::-1]):
    ax.text(x, i, f" {x:+.2f}%", va="center", ha="left" if x >= 0 else "right", fontsize=9)
ax.axvline(0, color=GRAY, lw=0.8); ax.set_xlim(min(v) * 1.25, max(v) * 3 + 3)
ax.set_title(f"店の小計を足した全体の合計の、正しい値とのずれ（未分類は売上の{out_json['null_share_amount']}%）")
save(fig, "a635_methods.png", SRC, y=-0.04)

# 図2：店ごとの小計（正しい値・R1・R2）
fig, ax = plt.subplots(figsize=(8.5, 4))
x = np.arange(len(STORES)); w = 0.26
ax.bar(x - w, per_store.truth / 1e6, w, color=GREEN, label="正しい小計")
ax.bar(x, per_store.R1 / 1e6, w, color=ORANGE, label="NULL の行を小計とみなす")
ax.bar(x + w, per_store.R2 / 1e6, w, color=BLUE, label="NULL の行を捨てて足す")
ax.set_xticks(x); ax.set_xticklabels(STORES); ax.set_ylabel("売上（百万円）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("店ごとの小計：NULL の行を小計とみなすと未分類の分だけ多く、捨てると少なく出る")
save(fig, "a635_by_store.png", SRC)

# 図3：未分類の割合とずれ
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(sens.p_null * 100, sens.R1, marker="o", color=ORANGE, label="NULL の行を小計とみなす")
ax.plot(sens.p_null * 100, sens.R2, marker="s", color=BLUE, label="NULL の行を捨てて足す")
ax.axhline(0, color=GRAY, lw=0.8); ax.set_xlabel("区分が空（NULL）の明細の割合（%）"); ax.set_ylabel("全体の合計のずれ（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("未分類が多いほど、取り違えたときのずれは大きくなる（各200回の平均）")
save(fig, "a635_by_share.png", SRC)
print(json.dumps(out_json, ensure_ascii=False, indent=1))
