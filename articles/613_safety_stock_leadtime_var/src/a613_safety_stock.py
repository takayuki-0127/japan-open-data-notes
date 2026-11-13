"""613 安全在庫を需要のばらつきだけで決めると、届くまでの日数がばらつくとき欠品は何%になるのか

架空の1品目：1日の需要は平均100個・標準偏差30個（正規、負は0）。発注は在庫（発注済みを含む）が発注点を下回ったら700個（7日分）。
届くまでの日数（リードタイム）は平均7日で、標準偏差を0〜3日に変える（整数、1日以上）。
  S1 需要のばらつきだけの式：発注点 = 100×7 + z×30×√7
  S2 リードタイムのばらつきも入れた式：発注点 = 100×7 + z×√(7×30² + 100²×σ_L²)
z=1.645（入荷までに欠品しない回を95%にするつもり）。発注1回ごとに「届くまでの需要」を20万回作り、
入荷までに欠品が起きた回の割合・欠品した個数の割合（発注量に対する）・平均在庫の目安を数える。seed 613。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 613）"
rng = np.random.default_rng(613)
MU, SD, MUL, Q = 100.0, 30.0, 7.0, 700
Z = stats.norm.ppf(0.95)


NCYC = 200000


def simulate(rop, sdl, seed):
    """発注してから届くまでの需要 D_L を1回の発注ごとに作り、発注点を下回るか（欠品）を数える"""
    rs = np.random.default_rng(seed)
    L = np.maximum(1, np.round(rs.normal(MUL, sdl, NCYC))).astype(int) if sdl > 0 else np.full(NCYC, int(MUL))
    d = np.maximum(0, rs.normal(MU, SD, (NCYC, L.max())))
    mask = np.arange(L.max())[None, :] < L[:, None]
    DL = (d * mask).sum(axis=1)
    short = np.maximum(DL - rop, 0)
    left = np.maximum(rop - DL, 0)
    # 平均在庫の目安：入荷の直前に残る在庫の平均 ＋ 発注量の半分
    return float((DL > rop).mean()), float(short.mean() / Q), float(left.mean() + Q / 2), NCYC, float(DL.std())


rows = []
for sdl in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
    rops = {"S1": MU * MUL + Z * SD * np.sqrt(MUL), "S2": MU * MUL + Z * np.sqrt(MUL * SD ** 2 + MU ** 2 * sdl ** 2)}
    for k, rop in rops.items():
        r = simulate(rop, sdl, 613_000 + int(10 * sdl))
        rows.append({"sd_leadtime": sdl, "formula": k, "rop": round(rop, 1), "safety_stock": round(rop - MU * MUL, 1),
                     "stockout_cycle_pct": round(100 * r[0], 2), "unfilled_pct": round(100 * r[1], 3),
                     "avg_inventory": round(r[2], 1), "avg_inventory_days": round(r[2] / MU, 2), "cycles": r[3],
                     "sd_leadtime_demand_sim": round(r[4], 1),
                     "sd_leadtime_demand_formula": round(float(np.sqrt(MUL * SD ** 2 + MU ** 2 * sdl ** 2)), 1)})
df = pd.DataFrame(rows); df.to_csv(RES / "summary.csv", index=False)
out = {"demand_mean": MU, "demand_sd": SD, "leadtime_mean": MUL, "order_qty": Q, "z": round(Z, 3), "cycles_per_case": NCYC,
       "rows": rows}
json.dump(out, open(RES / "a613_main.json", "w"), ensure_ascii=False, indent=1)

s1, s2 = df[df.formula == "S1"], df[df.formula == "S2"]
# 図1：欠品の起きた回の割合
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(s1.sd_leadtime, s1.stockout_cycle_pct, marker="o", color=ORANGE, label="需要のばらつきだけの式")
ax.plot(s2.sd_leadtime, s2.stockout_cycle_pct, marker="s", color=GREEN, label="リードタイムのばらつきも入れた式")
ax.axhline(5, color=GRAY, ls=":", lw=1)
ax.set_xlabel("届くまでの日数の標準偏差（日、平均7日）"); ax.set_ylabel("入荷までに欠品した回の割合（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("目標は5%（点線）：日数がばらつくと、需要だけの式では欠品が増える")
save(fig, "a613_stockout_cycles.png", SRC)
# 図2：安全在庫と平均在庫
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(s1.sd_leadtime, s1.avg_inventory_days, marker="o", color=ORANGE, label="平均在庫（需要だけの式）")
ax.plot(s2.sd_leadtime, s2.avg_inventory_days, marker="s", color=GREEN, label="平均在庫（ばらつきも入れた式）")
ax.plot(s2.sd_leadtime, s2.safety_stock / MU, color=GREEN, ls="--", lw=1, label="安全在庫（ばらつきも入れた式）")
ax.plot(s1.sd_leadtime, s1.safety_stock / MU, color=ORANGE, ls="--", lw=1, label="安全在庫（需要だけの式）")
ax.set_xlabel("届くまでの日数の標準偏差（日）"); ax.set_ylabel("日数分（1日の平均需要＝1）")
ax.legend(frameon=False, fontsize=8, ncol=2); ax.set_title("欠品を目標に保つには、在庫を何日分多く持つことになるか")
save(fig, "a613_inventory.png", SRC)
# 図3：欠品した個数の割合
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.plot(s1.sd_leadtime, s1.unfilled_pct, marker="o", color=ORANGE, label="需要だけの式")
ax.plot(s2.sd_leadtime, s2.unfilled_pct, marker="s", color=GREEN, label="ばらつきも入れた式")
ax.set_xlabel("届くまでの日数の標準偏差（日）"); ax.set_ylabel("発注量に対する欠品の個数（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("1回の発注あたり、欠品で売れなかった個数（発注量700個に対する割合）")
save(fig, "a613_unfilled.png", SRC)
print(df.to_string())
