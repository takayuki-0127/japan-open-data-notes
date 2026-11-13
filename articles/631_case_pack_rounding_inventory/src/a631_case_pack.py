"""631 発注をケース単位に切り上げると、在庫は平均で何日分多く持つことになるのか

架空の店の1品目。毎日の売れ数はポアソン（1日平均 μ = 5・20・50個）。7日ごとに発注し、2日後に届く。
発注は「次の発注の品が届くまでの需要＋安全の分（95%）」まで在庫を戻す数（発注点方式の定期発注）。
発注数の決め方：ばら（1個単位）、ケース単位に切り上げ（入数 6・12・24・48）、最低2ケース。
2年分（730日）をくり返し 20回流し、平均在庫（何日分）と欠品率（売れなかった数の割合）を出す。
発注数の切り上げは SQL（DuckDB、1スレッド）でも出し、Python と一致を確かめる。数字は置いた売れ方と発注の決まりで決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, SQL, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の店の売れ数（作成者が乱数で作成、seed 631)".replace(")", "）")
rng = np.random.default_rng(631)
DAYS, REV, LT, REPS = 730, 7, 2, 20
MUS, CASES = [5, 20, 50], [1, 6, 12, 24, 48]


def order_qty(need, case, min_cases):
    if need <= 0:
        return 0
    return int(max(np.ceil(need / case), min_cases) * case)


def simulate(mu, case, min_cases, rng, log=None):
    S = stats.poisson.ppf(0.95, mu * (REV + LT))
    on_hand, pipe = S, []          # pipe: (到着日, 数)
    inv_sum = lost = sold = 0
    for d in range(DAYS):
        on_hand += sum(q for t, q in pipe if t == d); pipe = [(t, q) for t, q in pipe if t > d]
        dem = rng.poisson(mu); s = min(dem, on_hand); on_hand -= s; sold += s; lost += dem - s
        if d % REV == 0:
            need = S - on_hand - sum(q for t, q in pipe)
            q = order_qty(need, case, min_cases)
            if log is not None:
                log.append({"day": d, "need_units": int(need), "case_size": case, "min_cases": min_cases, "order_units": q})
            if q > 0:
                pipe.append((d + LT, q))
        inv_sum += on_hand
    return inv_sum / DAYS / mu, 100 * lost / (lost + sold)


rows = []
for mu in MUS:
    for case in CASES:
        for mc in ([1] if case == 1 else [1, 2]):
            inv, so = zip(*[simulate(mu, case, mc, rng) for _ in range(REPS)])
            rows.append({"mu": mu, "case": case, "min_cases": mc, "inv_days": float(np.mean(inv)), "stockout_pct": float(np.mean(so))})
R = pd.DataFrame(rows)
base = R[R.case == 1].set_index("mu").inv_days
R["extra_days"] = R.inv_days - R.mu.map(base)
R["approx_extra_days"] = (R.case - 1) / 2 / R.mu   # 目安：切り上げで平均 (入数−1)/2 個多い
R.round(4).to_csv(RES / "summary.csv", index=False)

# SQL：μ=20、入数24・最低2ケースの発注の記録で確かめる
log = []; simulate(20, 24, 2, np.random.default_rng(6310), log)
LG = pd.DataFrame(log); LG.insert(0, "item_id", "I001")
con = duckdb.connect(); con.execute("SET threads=1"); con.register("order_need", LG.drop(columns="order_units"))
q = (SQL / "02_case_round_duckdb.sql").read_text(encoding="utf-8").split(";")[0]
sq = con.execute(q).df()
assert (sq.order_units.astype(int).to_numpy() == LG.order_units.to_numpy()).all()
LG.to_csv(RES / "order_log_mu20_case24_min2.csv", index=False)

out = {"days": DAYS, "review_days": REV, "lead_days": LT, "reps": REPS, "service_target": 0.95, "results": R.round(4).to_dict(orient="records"),
       "sql_rows_checked": int(len(LG))}
json.dump(out, open(RES / "a631_main.json", "w"), ensure_ascii=False, indent=1)

COL = {5: ORANGE, 20: BLUE, 50: GREEN}
# 図1：平均在庫（日分）
fig, ax = plt.subplots(figsize=(8.5, 4.2))
for mu in MUS:
    s = R[(R.mu == mu) & (R.min_cases == 1)]
    ax.plot(s.case, s.inv_days, marker="o", color=COL[mu], label=f"1日平均 {mu}個")
    for c, v in zip(s.case, s.inv_days):
        ax.text(c, v + 0.15, f"{v:.1f}", ha="center", fontsize=8.5, color=COL[mu])
ax.set_xticks(CASES); ax.set_xticklabels(["ばら"] + [f"{c}入" for c in CASES[1:]]); ax.set_xlabel("発注の単位")
ax.set_ylabel("平均在庫（何日分の売れ数か）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("ケース単位に切り上げると、売れ数の少ない品目ほど在庫が増える")
save(fig, "a631_inventory_days.png", SRC)

# 図2：増えた日数と目安
fig, ax = plt.subplots(figsize=(8.5, 4))
s = R[(R.min_cases == 1) & (R.case > 1)]
w = 0.25; xs = np.arange(4)
for j, mu in enumerate(MUS):
    v = s[s.mu == mu]
    ax.bar(xs + (j - 1) * w, v.extra_days, w, color=COL[mu], label=f"1日平均 {mu}個")
    ax.scatter(xs + (j - 1) * w, v.approx_extra_days, color=INK, s=12, zorder=3)
ax.set_xticks(xs); ax.set_xticklabels([f"{c}入" for c in CASES[1:]]); ax.set_ylabel("ばらより増えた在庫（日分）")
ax.set_title("増えた在庫（棒）と目安「(入数−1)÷2 個」（黒い点）"); ax.legend(frameon=False, fontsize=9)
save(fig, "a631_extra_days.png", SRC)

# 図3：最低2ケースの上乗せ（μ=5）
fig, ax = plt.subplots(figsize=(8.5, 4))
s1 = R[(R.mu == 5) & (R.case > 1) & (R.min_cases == 1)]; s2 = R[(R.mu == 5) & (R.case > 1) & (R.min_cases == 2)]
ax.bar(xs - 0.2, s1.inv_days, 0.4, color=BLUE, label="切り上げのみ")
ax.bar(xs + 0.2, s2.inv_days, 0.4, color=ORANGE, label="最低2ケース")
for x, v in zip(xs - 0.2, s1.inv_days):
    ax.text(x, v + 0.2, f"{v:.1f}", ha="center", fontsize=8.5)
for x, v in zip(xs + 0.2, s2.inv_days):
    ax.text(x, v + 0.2, f"{v:.1f}", ha="center", fontsize=8.5)
ax.axhline(base[5], color=GRAY, ls=":", label=f"ばら（{base[5]:.1f}日分）")
ax.set_xticks(xs); ax.set_xticklabels([f"{c}入" for c in CASES[1:]]); ax.set_ylabel("平均在庫（日分）")
ax.set_title("1日平均5個の品目：最低2ケースの決まりがあると"); ax.legend(frameon=False, fontsize=9)
save(fig, "a631_min_cases.png", SRC)
print(R.round(3).to_string())
