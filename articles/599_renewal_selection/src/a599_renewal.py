"""599 事故のあった人ほど契約を更新しないと、翌年の保有の事故率はどれだけ下がって見えるか（seed 599）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import RES, FIG, SQL, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

rng = np.random.default_rng(599)
SRC = "架空のデータ（作成者が乱数で作成、seed 599）"
N, T, MU = 300_000, 15, 0.07           # 保有30万件、15年、新しく入る人の平均の事故率7%（1年あたり件数）


def run(cv, p_no, p_acc, n=N, keep_rows=False):
    """毎年、事故のなかった人は p_no、事故のあった人は p_acc の確率で更新。やめた分は新しい人で埋める"""
    draw = (lambda k: np.full(k, MU)) if cv == 0 else (lambda k: rng.gamma(1 / cv ** 2, MU * cv ** 2, k))
    lam = draw(n); tenure = np.ones(n, dtype=int); ids = np.arange(n); nxt = n
    out, rows = [], []
    for t in range(1, T + 1):
        y = rng.poisson(lam)
        new = tenure == 1
        out.append({"year": t, "inforce_rate": y.mean(), "inforce_true": lam.mean(),
                    "new_rate": y[new].mean(), "renewed_rate": y[~new].mean() if (~new).any() else np.nan,
                    "share_new": new.mean()})
        stay = rng.random(n) < np.where(y > 0, p_acc, p_no)
        if keep_rows:
            rows.append(pd.DataFrame({"policy_id": ids, "year": t, "tenure": tenure, "claims": y, "renewed": stay.astype(int), "true_rate": lam}))
        k = int((~stay).sum())
        lam = np.where(stay, lam, 0); lam[~stay] = draw(k)
        tenure = np.where(stay, tenure + 1, 1)
        ids = ids.copy(); ids[~stay] = np.arange(nxt, nxt + k); nxt += k
    res = pd.DataFrame(out)
    if keep_rows:
        return res, pd.concat(rows, ignore_index=True), (lam, tenure)
    return res


# 1) 基本の場合（ばらつき CV 0.8、事故なし90%・事故あり70%で更新）と、更新が事故と無関係な場合
base, rows, _ = run(0.8, 0.90, 0.70, keep_rows=True)
p_avg = 0.90 * np.exp(-MU) + 0.70 * (1 - np.exp(-MU))           # 事故と無関係にしたときの更新率（同じ水準）
indep = run(0.8, p_avg, p_avg)
same = run(0.0, 0.90, 0.70)
pd.concat([base.assign(case="selection_cv0.8"), indep.assign(case="independent_cv0.8"), same.assign(case="selection_cv0")]
          ).round(6).to_csv(RES / "yearly.csv", index=False)

# 2) 保有の年数ごとの事故率（最後の5年）
rr = rows[rows.year > T - 5].copy(); rr["tenure_band"] = np.minimum(rr.tenure, 10)
ten = rr.groupby("tenure_band").agg(policy_years=("claims", "size"), claims=("claims", "sum"), true_rate=("true_rate", "mean")).reset_index()
ten["rate"] = ten.claims / ten.policy_years
ten_cv = []
for cv in [0.4, 0.8, 1.2]:
    _, r2, _ = run(cv, 0.90, 0.70, n=200_000, keep_rows=True)
    r2 = r2[r2.year > T - 5]; b = np.minimum(r2.tenure, 10)
    g = r2.groupby(b).agg(rate=("claims", "mean"), true_rate=("true_rate", "mean"))
    for k_, v in g.iterrows():
        ten_cv.append({"cv": cv, "tenure_band": int(k_), "rate": v.rate, "true_rate": v.true_rate})
ten_cv = pd.DataFrame(ten_cv); ten_cv.round(6).to_csv(RES / "rate_by_tenure.csv", index=False)

# 3) 15年目の保有の事故率と新規の差（ばらつき × 更新率の差）
grid = []
for cv in [0.0, 0.4, 0.8, 1.2]:
    for p_acc in [0.80, 0.70, 0.50]:
        r = run(cv, 0.90, p_acc, n=200_000)
        last = r[r.year > T - 3].mean()
        grid.append({"cv": cv, "p_no": 0.90, "p_acc": p_acc, "inforce_rate": last.inforce_rate, "inforce_true": last.inforce_true,
                     "new_rate": last.new_rate, "renewed_rate": last.renewed_rate,
                     "inforce_vs_new_pct": (last.inforce_true / MU - 1) * 100})
grid = pd.DataFrame(grid); grid.round(6).to_csv(RES / "steady_state_grid.csv", index=False)

# データ（2万件・最後の3年）を書き出し、SQL で保有の年数ごとの事故率を数え直す
_, ex, _ = run(0.8, 0.90, 0.70, n=20_000, keep_rows=True)
ex = ex[ex.year > T - 3].drop(columns="true_rate").reset_index(drop=True); ex.to_csv(DATA / "policy_years.csv", index=False)
con = duckdb.connect(); con.execute("SET threads TO 1"); con.register("policy_years", ex)
sq = con.execute(open(SQL / "02_tenure_duckdb.sql").read()).df().set_index("tenure_band")
py = ex.assign(b=np.minimum(ex.tenure, 10)).groupby("b").claims.mean()
mx = float((sq.claim_rate - py).abs().max())
pd.DataFrame([{"max_abs_diff": mx, "match": mx < 1e-12, "renew_rate_no_claim": float(ex[ex.claims == 0].renewed.mean()),
               "renew_rate_claim": float(ex[ex.claims > 0].renewed.mean())}]).to_csv(RES / "sql_check.csv", index=False)

# 図1 年ごとの推移
fig, ax = plt.subplots(figsize=(9.5, 4.8))
ax.plot(base.year, base.inforce_rate * 100, color=BLUE, marker="o", ms=4, label="保有全体の事故率（事故のあった人ほどやめる）")
ax.plot(base.year, base.inforce_true * 100, color=BLUE, lw=1, ls="--", label="同・保有の人の本当の事故率の平均")
ax.plot(base.year, base.new_rate * 100, color=ORANGE, marker="s", ms=4, label="その年に新しく入った人の事故率")
ax.plot(indep.year, indep.inforce_rate * 100, color=GRAY, marker="^", ms=4, label="保有全体（やめるかどうかが事故と無関係）")
ax.axhline(MU * 100, color=INK, lw=0.8, ls=":")
ax.set_xlabel("年（1年目は全員が新しく入った人）"); ax.set_ylabel("事故率（1件・1年あたりの件数、%）"); ax.set_ylim(6.0, 7.5)
ax.grid(alpha=0.3); ax.legend(fontsize=9, loc="lower left"); ax.set_xticks(range(1, T + 1))
ax.set_title("誰の事故率も変わっていないのに、保有の事故率は下がっていく（人ごとの差 CV 0.8）")
save(fig, "a599_yearly.png", "出典：" + SRC + "。事故のなかった人は90%、事故のあった人は70%の確率で更新。30万件")

# 図2 保有の年数ごとの事故率
fig, ax = plt.subplots(figsize=(9.5, 4.6))
for cv, col in zip([0.4, 0.8, 1.2], [GREEN, BLUE, ORANGE]):
    s = ten_cv[ten_cv.cv == cv]
    ax.plot(s.tenure_band, s.true_rate * 100, marker="o", color=col, label=f"人ごとの差 CV {cv}")
    ax.scatter(s.tenure_band, s.rate * 100, color=col, s=12, alpha=0.5)
ax.axhline(MU * 100, color=INK, lw=0.8, ls=":")
ax.set_xticks(range(1, 11)); ax.set_xticklabels([str(i) for i in range(1, 10)] + ["10年以上"])
ax.set_xlabel("保有の年数（何年目の契約か）"); ax.set_ylabel("事故率（%）"); ax.grid(alpha=0.3); ax.legend(fontsize=9, loc="lower left")
ax.set_title("長く続いている契約ほど事故率が低い：選ばれて残った人だから")
save(fig, "a599_tenure.png", "出典：" + SRC + "。11〜15年目の平均。線は本当の事故率の平均、点は実際の件数の率。各20万件")

# 図3 保有の本当の平均の事故率は、新規より何%低いか
fig, ax = plt.subplots(figsize=(9.5, 4.6)); xx = np.arange(4)
for j, (pa, col) in enumerate(zip([0.80, 0.70, 0.50], [GREEN, BLUE, ORANGE])):
    v = [grid[(grid.cv == cv) & (grid.p_acc == pa)].iloc[0].inforce_vs_new_pct for cv in [0.0, 0.4, 0.8, 1.2]]
    bars = ax.bar(xx + (j - 1) * 0.26, v, 0.26, color=col, label=f"事故のあった人の更新率 {int(pa * 100)}%")
    for b_, vv in zip(bars, v): ax.text(b_.get_x() + b_.get_width() / 2, vv - 1.2, f"{vv:.1f}", ha="center", fontsize=8)
ax.axhline(0, color=INK, lw=0.8); ax.set_ylim(-20.5, 1)
ax.set_xticks(xx); ax.set_xticklabels(["差なし（CV 0）", "CV 0.4", "CV 0.8", "CV 1.2"]); ax.set_xlabel("人ごとの本当の事故率の差")
ax.set_ylabel("保有の平均の事故率 − 新規（%）"); ax.grid(axis="y", alpha=0.3); ax.legend(fontsize=9, loc="lower left")
ax.set_title("人ごとの差が大きく、事故のあった人がやめやすいほど、保有の事故率は新規より低くなる")
save(fig, "a599_gap.png", "出典：" + SRC + "。事故のなかった人の更新率は90%。保有の人の本当の事故率の平均、13〜15年目。各20万件")

json.dump({"yearly_base": base.round(6).to_dict("records"), "yearly_indep": indep.round(6).to_dict("records"),
           "tenure_main": ten.round(6).to_dict("records"), "grid": grid.round(4).to_dict("records"),
           "sql": pd.read_csv(RES / "sql_check.csv").to_dict("records"), "p_avg_indep": p_avg},
          open(RES / "a599_main.json", "w"), ensure_ascii=False, indent=1)
pd.set_option("display.width", 250)
print(base.round(4).to_string()); print(indep.round(4).tail(3).to_string()); print(same.round(4).tail(3).to_string())
print(ten.round(4).to_string()); print(ten_cv.pivot(index="tenure_band", columns="cv", values="true_rate").round(4)); print(grid.round(4).to_string()); print(pd.read_csv(RES / "sql_check.csv"))
