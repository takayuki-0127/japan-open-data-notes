"""03b 問い直し（結果を見てから足した）：
ペットフードは、2019→2025年に買う回数が増えたのに、1回あたりの実質の額（物価で割った額）が2割減った。
これはコロナ前からの流れか、値上がりの時期に重なる動きか。年ごとの変化で、物価の伸びと1回あたりの実質の額の伸びを並べる。
出力：results/requestion.json、results/food_yearly_changes.csv"""
import json, pathlib
import numpy as np, pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
f = pd.read_csv(RES / "food_freq.csv").set_index("year")
t = pd.read_csv(RES / "total_by_year.csv").set_index("year")
r = lambda x: float(round(x, 4))
c = pd.DataFrame({"dlog_price": np.log(t.cpi_food).diff(), "dlog_real_per_purchase": np.log(f.food_per_purchase_real).diff(),
                  "dlog_freq": np.log(f.food_freq_per100).diff()}).dropna()
c.round(5).to_csv(RES / "food_yearly_changes.csv")
Q = {}
def cagr(s, a, b):
    return float((s[b] / s[a]) ** (1 / (b - a)) - 1)
Q["real_per_purchase_cagr_2005_2019"] = r(cagr(f.food_per_purchase_real, 2005, 2019))
Q["real_per_purchase_cagr_2019_2025"] = r(cagr(f.food_per_purchase_real, 2019, 2025))
Q["freq_cagr_2005_2019"] = r(cagr(f.food_freq_per100, 2005, 2019)); Q["freq_cagr_2019_2025"] = r(cagr(f.food_freq_per100, 2019, 2025))
Q["price_cagr_2005_2019"] = r(cagr(t.cpi_food, 2005, 2019)); Q["price_cagr_2019_2025"] = r(cagr(t.cpi_food, 2019, 2025))
sl = stats.linregress(c.dlog_price, c.dlog_real_per_purchase)
Q["slope_real_per_purchase_on_price"] = r(sl.slope); Q["slope_se"] = r(sl.stderr)
Q["slope_ci95"] = [r(sl.slope - 1.96 * sl.stderr), r(sl.slope + 1.96 * sl.stderr)]
# 実質＝名目÷物価 なので、上の傾き＋1 が「名目の1回あたりの額が、物価の伸び1に対してどれだけ伸びたか」
Q["slope_nominal_per_purchase_on_price"] = r(1 + sl.slope); Q["slope_nominal_ci95"] = [r(1 + sl.slope - 1.96 * sl.stderr), r(1 + sl.slope + 1.96 * sl.stderr)]
Q["n_years"] = int(len(c)); Q["corr"] = r(sl.rvalue)
hi = c[c.dlog_price > 0.05]
Q["years_price_up_gt5pct"] = [int(y) for y in hi.index]
Q["mean_dlog_real_pp_when_price_up_gt5pct"] = r(hi.dlog_real_per_purchase.mean())
Q["mean_dlog_real_pp_other_years"] = r(c[c.dlog_price <= 0.05].dlog_real_per_purchase.mean())
(RES / "requestion.json").write_text(json.dumps(Q, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(Q, ensure_ascii=False, indent=1)); print(c.round(3).to_string())
