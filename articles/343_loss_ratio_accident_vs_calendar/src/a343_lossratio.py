"""343 損害率は、事故が起きた年で数えるか、支払った年で数えるかで、どれだけ違うのか（架空の保険・seed 343）"""
import numpy as np, pandas as pd, duckdb, json
import matplotlib.pyplot as plt
from common import *
PAT = np.array([0.40, 0.30, 0.15, 0.10, 0.05])     # 事故の年から数えて0〜4年後に払う割合
TRUE_LR = 0.60

def simulate(growth, seed, lr=None, years=16, base_prem=10_000, sev_mu=13.0, sev_sg=1.2):
    """growth: 年ごとの保険料の伸び率（長さ years-1）。保険料の単位は百万円。事故は件数ポアソン・金額対数正規"""
    rng = np.random.default_rng(seed)
    lr = np.full(years, TRUE_LR) if lr is None else lr
    prem = base_prem * np.cumprod(np.r_[1.0, 1 + np.asarray(growth)])
    mean_sev = np.exp(sev_mu + sev_sg ** 2 / 2) / 1e6
    cl, pay = [], []; cid = 0
    for y in range(years):
        n = rng.poisson(prem[y] * lr[y] / mean_sev)
        sev = rng.lognormal(sev_mu, sev_sg, n) / 1e6
        ids = np.arange(cid, cid + n); cid += n
        cl.append(pd.DataFrame({"claim_id": ids, "acc_year": 2010 + y, "ultimate": sev}))
        # 1件ごとの払い方：PAT を中心にばらつかせる（ディリクレ）
        w = rng.dirichlet(PAT * 20, n)
        for k in range(5):
            pay.append(pd.DataFrame({"claim_id": ids, "pay_year": 2010 + y + k, "paid": sev * w[:, k]}))
    prem_df = pd.DataFrame({"year": 2010 + np.arange(years), "earned_premium": prem})
    return prem_df, pd.concat(cl, ignore_index=True), pd.concat(pay, ignore_index=True)

SQL_CAL = """SELECT p.pay_year AS year, SUM(p.paid) AS paid FROM payments p GROUP BY p.pay_year"""
SQL_ACC = """SELECT c.acc_year AS year, SUM(p.paid) AS paid_all,
                    SUM(CASE WHEN p.pay_year <= ? THEN p.paid ELSE 0 END) AS paid_to_date
             FROM claims c JOIN payments p ON p.claim_id = c.claim_id GROUP BY c.acc_year"""

def ratios(prem, claims, payments, asof_year):
    con = duckdb.connect()
    con.register("premium", prem); con.register("claims", claims); con.register("payments", payments)
    cal = con.execute(SQL_CAL).df(); acc = con.execute(SQL_ACC, [asof_year]).df()
    r = prem.merge(cal, on="year", how="left").merge(acc, on="year", how="left")
    r["lr_calendar"] = r.paid / r.earned_premium           # 支払った年で数える
    r["lr_accident"] = r.paid_all / r.earned_premium       # 事故の年で数える（払い終わったあとの値）
    r["lr_accident_to_date"] = r.paid_to_date / r.earned_premium   # 事故の年で数えるが、まだ払った分だけ
    # pandas で別に計算して照合
    chk = payments.groupby("pay_year").paid.sum().reindex(r.year).values
    assert np.allclose(np.nan_to_num(chk), np.nan_to_num(r.paid.values))
    return r

# ---- 場面1：伸びる→横ばい→縮む
g1 = [0.10] * 6 + [0.0] * 3 + [-0.10] * 6
P, C, Y = simulate(g1, 343)
r1 = ratios(P, C, Y, asof_year=2025)
r1["phase"] = ["立ち上がり"] * 4 + ["伸びる"] * 3 + ["横ばい"] * 3 + ["縮む"] * 6
r1 = r1[r1.year <= 2025]
r1.round(5).to_csv(RES / "scenario1_by_year.csv", index=False)
ph = r1[r1.year >= 2014].groupby("phase").apply(lambda d: pd.Series({
    "lr_calendar": d.paid.sum() / d.earned_premium.sum(), "lr_accident": d.paid_all.sum() / d.earned_premium.sum()}))
ph["diff_pt"] = (ph.lr_calendar - ph.lr_accident) * 100
ph.round(4).to_csv(RES / "scenario1_by_phase.csv")
# ---- 場面2：伸び率を変える（一定の伸びが続いたあとの差。式と、シミュレーション20回の平均）
sweep = []
for g in [-0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20, 0.30]:
    theory = TRUE_LR * (PAT / (1 + g) ** np.arange(5)).sum()
    sims = []
    for s in range(20):
        p_, c_, y_ = simulate([g] * 15, 1000 + s)
        rr = ratios(p_, c_, y_, 2025); rr = rr[(rr.year >= 2018) & (rr.year <= 2025)]
        sims.append(rr.paid.sum() / rr.earned_premium.sum())
    sweep.append({"growth": g, "theory_calendar_lr": theory, "sim_mean": np.mean(sims), "sim_sd": np.std(sims),
                  "diff_pt_theory": (theory - TRUE_LR) * 100, "diff_pt_sim": (np.mean(sims) - TRUE_LR) * 100})
sw = pd.DataFrame(sweep); sw.round(5).to_csv(RES / "growth_sweep.csv", index=False)
# ---- 場面3：本当の損害率が 2018 年の事故から 60%→70% に上がる（保険料は横ばい）。いつ気づけるか
lr3 = np.r_[np.full(8, 0.60), np.full(8, 0.70)]
runs = []
for s in range(200):
    p_, c_, y_ = simulate([0.0] * 15, 5000 + s, lr=lr3)
    rr = ratios(p_, c_, y_, 2025); rr = rr[(rr.year >= 2014) & (rr.year <= 2025)]
    runs.append(rr[["year", "lr_calendar", "lr_accident"]].assign(run=s))
r3 = pd.concat(runs); m3 = r3.groupby("year")[["lr_calendar", "lr_accident"]].mean()
m3["theory_calendar"] = [sum(PAT[k] * lr3[y - 2010 - k] for k in range(5)) for y in m3.index]
m3.round(5).to_csv(RES / "scenario3_shock.csv")
# 事故の年で数えるが、まだ払った分だけ（直近の年ほど低く見える）
imm = r1[r1.year >= 2021][["year", "lr_accident", "lr_accident_to_date"]]
main = {"pattern": PAT.tolist(), "true_lr": TRUE_LR, "n_claims_s1": int(len(C)),
        "phase": {k: {c: round(float(v), 4) for c, v in r.items()} for k, r in ph.iterrows()},
        "sweep": [{k: round(float(v), 4) for k, v in r.items()} for r in sw.to_dict("records")],
        "shock_mean": {int(y): {c: round(float(v), 4) for c, v in r.items()} for y, r in m3.iterrows()},
        "shock_share_of_rise": {int(y): round(float((m3.loc[y, "lr_calendar"] - 0.6) / 0.1), 3) for y in range(2018, 2023)},
        "immature_accident_year": {int(r.year): {"final": round(r.lr_accident, 4), "to_date": round(r.lr_accident_to_date, 4)} for r in imm.itertuples()},
        "s1_calendar_minmax_2014_2025": [round(float(r1[r1.year >= 2014].lr_calendar.min()), 4), round(float(r1[r1.year >= 2014].lr_calendar.max()), 4)],
        "s1_accident_minmax_2014_2025": [round(float(r1[r1.year >= 2014].lr_accident.min()), 4), round(float(r1[r1.year >= 2014].lr_accident.max()), 4)]}
json.dump(main, open(RES / "a343_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(main, ensure_ascii=False, indent=1))
SRC = "架空の保険の事故・支払データ（乱数で作成、seed 343）。本当の損害率は60%、支払いは事故の年から5年に分かれる（40・30・15・10・5%）"
# 図1
fig, ax = plt.subplots(figsize=(8.4, 4.6)); d = r1[r1.year >= 2014]
ax2 = ax.twinx(); ax2.bar(d.year, d.earned_premium / 100, color="#e8e7e2", width=0.7, zorder=0); ax2.set_ylabel("保険料（億円）", color=GRAY)
ax2.spines["right"].set_visible(True); ax2.set_ylim(0, d.earned_premium.max() / 100 * 2.2); ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)
ax.plot(d.year, d.lr_accident * 100, "o-", color=BLUE, lw=2, label="事故が起きた年で数える（払い終わった値）")
ax.plot(d.year, d.lr_calendar * 100, "s-", color=ORANGE, lw=2, label="支払った年で数える")
ax.axhline(60, color=GRAY, lw=0.8, ls="--"); ax.set_ylim(45, 75); ax.set_ylabel("損害率（%）"); ax.set_xticks(d.year)
ax.set_title("同じ会社の損害率：保険料が伸びる時期は低く、縮む時期は高く出る"); ax.legend(frameon=False, loc="upper left", fontsize=9)
save(fig, "a343_two_ratios.png", SRC)
# 図2
fig, ax = plt.subplots(figsize=(7.8, 4.2))
ax.plot(sw.growth * 100, sw.diff_pt_theory, "-", color=GRAY, lw=1.5, label="式（払い方と伸び率から）")
ax.errorbar(sw.growth * 100, sw.diff_pt_sim, yerr=sw.sim_sd * 100, fmt="o", color=BLUE, capsize=3, label="シミュレーション20回の平均（縦棒は標準偏差）")
ax.axhline(0, color=INK, lw=0.6); ax.axvline(0, color=INK, lw=0.6)
for g_, v in zip(sw.growth * 100, sw.diff_pt_sim): ax.text(g_, v + (1.0 if v >= 0 else -1.6), f"{v:+.1f}", ha="center", fontsize=8.5)
ax.set_xlabel("保険料の伸び率（年、%）"); ax.set_ylabel("支払った年の損害率 − 本当の損害率（ポイント）")
ax.set_title("伸び率が大きいほど、支払った年で数えた損害率は低く出る"); ax.legend(frameon=False, fontsize=9)
save(fig, "a343_growth.png", SRC)
# 図3
fig, ax = plt.subplots(figsize=(7.8, 4.2))
ax.plot(m3.index, m3.lr_accident * 100, "o-", color=BLUE, lw=2, label="事故が起きた年で数える（払い終わった値）")
ax.plot(m3.index, m3.lr_calendar * 100, "s-", color=ORANGE, lw=2, label="支払った年で数える")
ax.axvline(2017.5, color=GRAY, lw=0.8, ls="--"); ax.text(2017.6, 71.3, "ここから本当の損害率が70%に", fontsize=9, color=GRAY)
ax.set_ylim(56, 73); ax.set_xticks(m3.index); ax.set_ylabel("損害率（%、200回の平均）")
ax.set_title("損害率が10ポイント上がったとき、支払った年の数字は何年かけて追いつくか"); ax.legend(frameon=False, loc="lower right", fontsize=9)
save(fig, "a343_shock.png", SRC)
