"""345 店ごとの平均を平均すると、全体の平均からどれだけずれるのか"""
import numpy as np, pandas as pd, json
import matplotlib.pyplot as plt
from common import *
# ---- 1) 宿泊旅行統計：従業者数の4区分の客室稼働率
occ = pd.read_csv(DATA / "lodging_occupancy.csv"); occ = occ[occ.month == 0].set_index("year")
fac = pd.read_csv(DATA / "lodging_facilities.csv").groupby("year").mean(numeric_only=True)
S = ["s0_9", "s10_29", "s30_99", "s100"]
L = pd.DataFrame({"official": occ.total, "simple_mean_of_4": occ[S].mean(axis=1),
                  "weighted_by_facilities": (occ[S].values * fac.loc[occ.index, S].values).sum(axis=1) / fac.loc[occ.index, S].values.sum(axis=1)})
L["simple_minus_official"] = L.simple_mean_of_4 - L.official; L["facility_minus_official"] = L.weighted_by_facilities - L.official
# 公表の全体の値になる重み（客室数にあたる）を、4区分の値から逆算はできないので、差だけを示す
L.round(3).to_csv(RES / "lodging_occupancy_means.csv")
chg = lambda c: float(L.loc[2025, c] - L.loc[2019, c])
# ---- 2) 商業動態統計：6業態の前年同月比
m = pd.read_csv(DATA / "meti_sales_monthly.csv", parse_dates=["ym"]).pivot(index="ym", columns="gyotai", values="sales").dropna()
yoy_each = m.pct_change(12).dropna() * 100
yoy_total = (m.sum(axis=1).pct_change(12).dropna()) * 100
K = pd.DataFrame({"total_yoy": yoy_total, "mean_of_6_yoy": yoy_each.mean(axis=1)}); K["diff_pt"] = K.mean_of_6_yoy - K.total_yoy
w_prev = m.shift(12).div(m.shift(12).sum(axis=1), axis=0).loc[K.index]
assert np.allclose((yoy_each * w_prev).sum(axis=1), K.total_yoy)        # 前年の売上で重みをつけると全体と一致
K.round(4).to_csv(RES / "meti_yoy_means.csv")
ksign = int((np.sign(K.total_yoy) != np.sign(K.mean_of_6_yoy)).sum())
# ---- 3) 架空の店：客単価＝売上÷客数。大きさの偏りと、大きさと客単価の結びつきを変える
rng = np.random.default_rng(345)
def stores(n, sigma, rho, rng):
    z = rng.standard_normal(n); e = rng.standard_normal(n)
    cust = np.round(np.exp(7.0 + sigma * z)).astype(int) + 20                     # 月の客数（店の大きさ）
    unit = np.exp(np.log(2400) + 0.25 * (rho * z + np.sqrt(1 - rho ** 2) * e))    # 客単価（円）
    sales = cust * unit * np.exp(rng.normal(0, 0.03, n))
    return cust, sales
rows = []
for sigma in [0.0, 0.3, 0.6, 0.9, 1.2, 1.5]:
    for rho in [-0.6, -0.3, 0.0, 0.3, 0.6]:
        d = []
        for r in range(300):
            c, s = stores(200, sigma, rho, rng)
            true = s.sum() / c.sum(); mm = (s / c).mean(); med = np.median(s / c)
            d.append(((mm / true - 1) * 100, (med / true - 1) * 100, c.max() / c.sum() * 100, np.sort(c)[-20:].sum() / c.sum() * 100))
        d = np.array(d)
        rows.append({"sigma": sigma, "rho": rho, "mean_of_means_diff_pct": d[:, 0].mean(), "diff_p10": np.percentile(d[:, 0], 10),
                     "diff_p90": np.percentile(d[:, 0], 90), "median_diff_pct": d[:, 1].mean(), "top10pct_share": d[:, 3].mean()})
F = pd.DataFrame(rows); F.round(4).to_csv(RES / "fictional_sweep.csv", index=False)
# ---- 4) 率の例：成約率。店ごとの率の平均と、合計どうしの率。向きが逆になる例を数える
rng2 = np.random.default_rng(3450); flips = []; diffs = []
for r in range(2000):
    n = 30; z = rng2.standard_normal(n)
    visits0 = np.round(np.exp(6 + 1.0 * z)).astype(int) + 30
    p0 = np.clip(0.20 - 0.03 * z + rng2.normal(0, 0.02, n), 0.02, 0.6)            # 大きい店ほど率が低い
    grow = np.exp(rng2.normal(0, 0.25, n) + 0.15 * z)                              # 大きい店ほど来店が伸びる
    visits1 = np.round(visits0 * grow).astype(int); p1 = np.clip(p0 + 0.01 + rng2.normal(0, 0.01, n), 0.02, 0.6)   # どの店も率は約1ポイント上がる
    k0 = rng2.binomial(visits0, p0); k1 = rng2.binomial(visits1, p1)
    a0, a1 = (k0 / visits0).mean(), (k1 / visits1).mean(); t0, t1 = k0.sum() / visits0.sum(), k1.sum() / visits1.sum()
    flips.append(np.sign(a1 - a0) != np.sign(t1 - t0)); diffs.append(((a1 - a0) * 100, (t1 - t0) * 100, (a0 - t0) * 100))
diffs = np.array(diffs)
g = lambda s, r: float(F[(F.sigma == s) & (F.rho == r)].mean_of_means_diff_pct.iloc[0])
main = {"lodging": {"2025": {k: round(float(L.loc[2025, k]), 2) for k in ["official", "simple_mean_of_4", "weighted_by_facilities"]},
                    "simple_minus_official_range": [round(float(L.simple_minus_official.min()), 2), round(float(L.simple_minus_official.max()), 2)],
                    "facility_minus_official_range": [round(float(L.facility_minus_official.min()), 2), round(float(L.facility_minus_official.max()), 2)],
                    "change_2019_2025": {k: round(chg(k), 2) for k in ["official", "simple_mean_of_4", "weighted_by_facilities"]},
                    "small_share_of_facilities_2025": round(float(fac.loc[2025, "s0_9"] / fac.loc[2025, S].sum()), 3)},
        "meti": {"months": int(len(K)), "from": str(K.index.min().date()), "to": str(K.index.max().date()),
                 "diff_pt_mean": round(float(K.diff_pt.mean()), 3), "diff_pt_abs_mean": round(float(K.diff_pt.abs().mean()), 3),
                 "diff_pt_min": round(float(K.diff_pt.min()), 2), "diff_pt_max": round(float(K.diff_pt.max()), 2),
                 "months_abs_diff_over_1pt": int((K.diff_pt.abs() > 1).sum()), "months_sign_differs": ksign,
                 "worst_month": str(K.diff_pt.abs().idxmax().date()), "worst": {k: round(float(v), 2) for k, v in K.loc[K.diff_pt.abs().idxmax()].items()}},
        "fictional": {"sigma0_rho0": round(g(0.0, 0.0), 3), "sigma1.2_rho0": round(g(1.2, 0.0), 3), "sigma0.6_rho0.6": round(g(0.6, 0.6), 2),
                      "sigma1.2_rho0.6": round(g(1.2, 0.6), 2), "sigma1.2_rho-0.6": round(g(1.2, -0.6), 2), "sigma1.5_rho0.6": round(g(1.5, 0.6), 2),
                      "sigma0_rho0.6": round(g(0.0, 0.6), 3),
                      "top10pct_share_sigma1.2": round(float(F[(F.sigma == 1.2) & (F.rho == 0)].top10pct_share.iloc[0]), 1)},
        "rate_example": {"runs": 2000, "direction_flips": int(np.sum(flips)), "mean_change_store_avg_pt": round(float(diffs[:, 0].mean()), 3),
                         "mean_change_total_pt": round(float(diffs[:, 1].mean()), 3), "level_gap_pt": round(float(diffs[:, 2].mean()), 2)}}
json.dump(main, open(RES / "a345_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1))
# 図1
fig, ax = plt.subplots(figsize=(8, 4.4))
ax.plot(L.index, L.official, "o-", color=BLUE, lw=2.2, label="公表の全体の値")
ax.plot(L.index, L.simple_mean_of_4, "s--", color=ORANGE, lw=1.8, label="4つの区分の値を単純に平均")
ax.plot(L.index, L.weighted_by_facilities, "^--", color=GRAY, lw=1.8, label="施設の数で重みをつけて平均")
ax.set_ylabel("客室稼働率（%）"); ax.set_xticks(L.index); ax.set_ylim(15, 70)
ax.set_title("宿泊施設の客室稼働率：平均の取り方で20ポイント違う"); ax.legend(frameon=False, fontsize=9)
save(fig, "a345_lodging.png", "出典：観光庁「宿泊旅行統計調査」年の確定値（従業者数の4区分）をもとに作成")
# 図2
fig, ax = plt.subplots(figsize=(8, 4.4))
for rho, col in zip([-0.6, -0.3, 0.0, 0.3, 0.6], [ORANGE, "#f2b08f", GRAY, LIGHT, BLUE]):
    d = F[F.rho == rho]; ax.plot(d.sigma, d.mean_of_means_diff_pct, "o-", color=col, lw=2, label=f"大きさと客単価の結びつき {rho:+.1f}")
ax.axhline(0, color=INK, lw=0.6); ax.set_xlabel("店の大きさの偏り（客数の対数の標準偏差。0＝全店同じ大きさ）"); ax.set_ylabel("「店ごとの客単価の平均」− 全体の客単価（%）")
ax.set_title("架空の200店：大きさが偏り、大きさと客単価が結びつくほど、ずれが広がる"); ax.legend(frameon=False, fontsize=8.5)
save(fig, "a345_sweep.png", "架空の店のデータ（乱数で作成、seed 345）。条件ごとに300回の平均")
# 図3
fig, ax = plt.subplots(figsize=(8.2, 4.2))
ax.plot(K.index, K.total_yoy, color=BLUE, lw=1.8, label="6業態の合計の前年同月比")
ax.plot(K.index, K.mean_of_6_yoy, color=ORANGE, lw=1.4, label="6業態の前年同月比を単純に平均")
ax.axhline(0, color=INK, lw=0.6); ax.set_ylabel("前年同月比（%）"); ax.set_title("6業態の伸び率を平均しても、合計の伸び率にはならない"); ax.legend(frameon=False, fontsize=9)
save(fig, "a345_meti.png", "出典：経済産業省「商業動態統計」業態別の販売額をもとに作成")
