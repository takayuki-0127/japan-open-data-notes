"""545 割引を2つ重ねるとき、「足し算」「掛け算」「適用の順番」の違いで、請求額は何件・何円違うのか

架空の注文 20,000件（%引きと円引きのクーポンを0〜2枚使う）で、重ね方を4通りにして請求額を出す。
  M1 足し算（%→円）：どの割引も元の金額から計算して合計する（%引きを先に、円引きを後に引くのと同じ）
  M2 掛け算（%→円）：%引きを順に掛け、そのあと円引きを引く
  M3 掛け算（円→%）：円引きを先に引き、そのあと%引きを順に掛ける
  M4 足し算（円→%）：円引きを先に引き、残りの金額に%引きの合計を掛ける
端数は %引きを当てるたびに1円未満を切り捨てる（比較として、最後に1回だけ切り捨てる場合も出す）。請求額は0円未満にしない。
税や会計の扱いは入れていない。数字は置いた注文とクーポンの組み合わせで決まる。
"""
import json
import math
from itertools import combinations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の注文とクーポン（作成者が乱数で作成、seed 545）"
rng = np.random.default_rng(545)
N = 20000
PCT = [5, 10, 15, 20]
YEN = [300, 500, 1000]
amount = np.round(rng.lognormal(np.log(4000), 0.6, N) / 10) * 10  # 10円単位
ncp = rng.choice([0, 1, 2], size=N, p=[0.6, 0.2, 0.2])
rows = []
for i in range(N):
    cps = []
    if ncp[i] == 1:
        cps = [("%", int(rng.choice(PCT)))] if rng.random() < 0.6 else [("円", int(rng.choice(YEN)))]
    elif ncp[i] == 2:
        u = rng.random()
        if u < 0.25:
            cps = [("%", int(rng.choice(PCT))), ("%", int(rng.choice(PCT)))]
        elif u < 0.85:
            cps = [("%", int(rng.choice(PCT))), ("円", int(rng.choice(YEN)))]
        else:
            cps = [("円", int(rng.choice(YEN))), ("円", int(rng.choice(YEN)))]
    rows.append({"order_id": i + 1, "amount": int(amount[i]), "coupons": " ".join(f"{v}{t}" for t, v in cps)})
od = pd.DataFrame(rows)
od.to_csv(DATA / "orders.csv", index=False)


def parse(s):
    return [("%" if c.endswith("%") else "円", int(c[:-1])) for c in s.split()] if s else []


def bill(amount, cps, method, step_round=True):
    pct = [v for t, v in cps if t == "%"]
    yen = sum(v for t, v in cps if t == "円")
    fl = math.floor if step_round else (lambda x: x)
    x = float(amount)
    if method == "M1":
        x = x - sum(fl(amount * p / 100) for p in pct) - yen
    elif method == "M2":
        for p in pct:
            x = x - fl(x * p / 100)
        x = x - yen
    elif method == "M3":
        x = max(x - yen, 0)
        for p in pct:
            x = x - fl(x * p / 100)
    elif method == "M4":
        x = max(x - yen, 0)
        x = x - fl(x * sum(pct) / 100)
    return max(math.floor(x), 0)


M = ["M1", "M2", "M3", "M4"]
for m in M:
    od[m] = [bill(a, parse(c), m) for a, c in zip(od.amount, od.coupons)]
    od[m + "_end"] = [bill(a, parse(c), m, step_round=False) for a, c in zip(od.amount, od.coupons)]
od["kind"] = od.coupons.map(lambda s: "なし" if not s else "+".join(sorted(t for t, _ in parse(s))).replace("%+%", "%と%").replace("%+円", "%と円").replace("円+円", "円と円") if len(parse(s)) == 2 else "1枚")
od.to_csv(RES / "bills.csv", index=False)

pairs = []
for a, b in combinations(M, 2):
    d = od[a] - od[b]
    pairs.append({"組み合わせ": f"{a}と{b}", "違う件数": int((d != 0).sum()), "違う割合%": (d != 0).mean() * 100,
                  "差の合計（円）": int(d.abs().sum()), "最大の差（円）": int(d.abs().max())})
pr = pd.DataFrame(pairs)
pr.to_csv(RES / "pair_diff.csv", index=False)
spread = od[M].max(axis=1) - od[M].min(axis=1)
bykind = od.assign(spread=spread).groupby("kind").agg(件数=("spread", "size"), 違う件数=("spread", lambda s: int((s > 0).sum())),
                                                       差の合計=("spread", "sum"), 最大の差=("spread", "max"))
bykind.to_csv(RES / "by_kind.csv")
rnd = {m: {"違う件数": int((od[m] != od[m + "_end"]).sum()), "差の合計（円）": int((od[m] - od[m + "_end"]).abs().sum()),
           "最大の差（円）": int((od[m] - od[m + "_end"]).abs().max())} for m in M}
tot = {m: int(od[m].sum()) for m in M}
stacked = od.kind.isin(["%と%", "%と円", "円と円"])
out = {"n": N, "kind_n": od.kind.value_counts().to_dict(), "stacked_n": int(stacked.sum()),
       "any_diff_n": int((spread > 0).sum()), "any_diff_share_of_stacked": float((spread > 0)[stacked].mean()),
       "spread_sum": int(spread.sum()), "spread_max": int(spread.max()), "total_bill": tot,
       "total_gap_max_min": max(tot.values()) - min(tot.values()),
       "pairs": pr.round(3).to_dict(orient="records"), "by_kind": bykind.reset_index().to_dict(orient="records"),
       "rounding": rnd,
       "example": od.loc[spread.idxmax(), ["amount", "coupons"] + M].to_dict()}
(RES / "a545_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=int))

# 図1 例：10,000円に 20%引きと 1,000円引き、20%引きと10%引き
ex = [("10,000円に「20%引き」と「1,000円引き」", 10000, [("%", 20), ("円", 1000)]),
      ("10,000円に「20%引き」と「10%引き」", 10000, [("%", 20), ("%", 10)]),
      ("3,000円に「15%引き」と「500円引き」", 3000, [("%", 15), ("円", 500)])]
LAB = {"M1": "M1 足し算（%→円）", "M2": "M2 掛け算（%→円）", "M3": "M3 掛け算（円→%）", "M4": "M4 足し算（円→%）"}
COL = {"M1": GRAY, "M2": BLUE, "M3": ORANGE, "M4": GREEN}
fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.8), sharey=False)
exv = []
for ax, (t, a, c) in zip(axes, ex):
    v = [bill(a, c, m) for m in M]
    exv.append({"例": t, **dict(zip(M, v))})
    ax.bar(range(4), v, color=[COL[m] for m in M])
    for i, vv in enumerate(v):
        ax.text(i, vv, f"{vv:,}", ha="center", va="bottom", fontsize=9.5)
    ax.set_xticks(range(4), ["M1", "M2", "M3", "M4"]); ax.set_title(t, fontsize=10)
    ax.set_ylim(min(v) * 0.85, max(v) * 1.06)
axes[0].set_ylabel("請求額（円）")
fig.legend([plt.Rectangle((0, 0), 1, 1, color=COL[m]) for m in M], [LAB[m] for m in M], ncol=4, loc="lower center",
           bbox_to_anchor=(0.5, -0.1), frameon=False, fontsize=9)
fig.suptitle("同じクーポンの組み合わせでも、重ね方で請求額が変わる", y=1.03)
save(fig, "a545_examples.png", SRC, y=-0.13)
pd.DataFrame(exv).to_csv(RES / "examples.csv", index=False)
out["examples"] = exv
(RES / "a545_main.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=int))

# 図2 組み合わせごとの違う件数
fig, ax = plt.subplots(figsize=(8.6, 4.0))
y = np.arange(len(pr))
ax.barh(y, pr["違う件数"], color=BLUE)
for yi, r in zip(y, pr.itertuples()):
    ax.text(r.違う件数 + 30, yi, f"{r.違う件数:,}件（{r._3:.1f}%）・合計{r._4:,}円・最大{r._5:,}円", va="center", fontsize=9)
ax.set_yticks(y, [f"{LAB[p[:2]].split()[0]} と {LAB[p[3:5]].split()[0]}" for p in pr.組み合わせ]); ax.invert_yaxis()
ax.set_xlim(0, pr.違う件数.max() * 2.1); ax.set_xlabel(f"請求額が違う注文の件数（{N:,}件のうち）")
ax.set_title("重ね方の組み合わせごとの、請求額が違う注文の数")
save(fig, "a545_pair_diff.png", SRC)

# 図3 クーポンの組み合わせの種類ごと
order = ["なし", "1枚", "%と%", "%と円", "円と円"]
bk = bykind.reindex(order).fillna(0)
fig, ax = plt.subplots(figsize=(8.0, 3.8))
ax.bar(range(5), bk.件数, color=LIGHT, label="注文の件数")
ax.bar(range(5), bk.違う件数, color=ORANGE, label="4通りのどれかで請求額が違う件数")
for i, (n, dn, mx) in enumerate(zip(bk.件数, bk.違う件数, bk.最大の差)):
    ax.text(i, n, f"{int(dn):,} / {int(n):,}件\n最大{int(mx):,}円", ha="center", va="bottom", fontsize=9)
ax.set_xticks(range(5), ["クーポンなし", "1枚", "%引き2枚", "%引きと円引き", "円引き2枚"])
ax.set_ylim(0, bk.件数.max() * 1.25); ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.set_title("請求額が変わるのは、%引きを含む2枚の重ねだけ")
save(fig, "a545_by_kind.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1, default=int)[:4000])
