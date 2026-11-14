"""P03 前半：コンフォーマル予測（Angelopoulos & Bates）を、東京の1時間ごとの電力需要の予測で試す。
入力：data/f157_pred_tokyo_2024_25.csv.gz（較正用の1年）、data/f157_pred_tokyo_2025_26.csv.gz（試す1年）
出力：results/a_*.csv・a_main.json、figures/p03_01・02・03
"""
import json
import numpy as np, pandas as pd
from scipy.stats import beta, norm
from common import DATA, RES, BLUE, ORANGE, GRAY, GREEN, PURPLE, RED, SEED, conformal_q, save, plt

SRC = "出典：東京電力パワーグリッド「エリア需給実績データ」と japan-open-data-notes F157 の予測をもとに作成"
ALPHA = 0.10
cal = pd.read_csv(DATA / "f157_pred_tokyo_2024_25.csv.gz", parse_dates=["ts"])
tst = pd.read_csv(DATA / "f157_pred_tokyo_2025_26.csv.gz", parse_dates=["ts"])
r_cal = (cal.actual - cal["毎月"]).values                 # 較正：実測の気温で出した予測の誤差
out = {}

# ---------- 1. 入れかえ可能なとき：較正の点数が少ないと、当たり方がどれだけ揺れるか ----------
rng = np.random.default_rng(SEED)
r_all = (tst.actual - tst["毎月"]).values
rows = []
for n in (20, 100, 1000):
    cov_c, cov_g = [], []
    for _ in range(2000):
        idx = rng.permutation(len(r_all))
        c, t = r_all[idx[:n]], r_all[idx[n:]]
        q = conformal_q(np.abs(c), ALPHA)
        cov_c.append(np.mean(np.abs(t) <= q))
        z = norm.ppf(1 - ALPHA / 2)
        cov_g.append(np.mean(np.abs(t - c.mean()) <= z * c.std(ddof=1)))
    cov_c, cov_g = np.array(cov_c), np.array(cov_g)
    l = int(np.floor((n + 1) * ALPHA))
    th = beta(n + 1 - l, l)
    rows.append({"n_cal": n, "conformal_mean": cov_c.mean(), "conformal_p05": np.quantile(cov_c, .05),
                 "conformal_p95": np.quantile(cov_c, .95), "theory_mean": th.mean(), "theory_p05": th.ppf(.05),
                 "theory_p95": th.ppf(.95), "gauss_mean": cov_g.mean(), "gauss_p05": np.quantile(cov_g, .05),
                 "gauss_p95": np.quantile(cov_g, .95), "conformal_below_85": np.mean(cov_c < .85)})
    out[f"exch_{n}"] = cov_c
ex = pd.DataFrame(rows)
ex.round(4).to_csv(RES / "a_exchangeable.csv", index=False, encoding="utf-8")

fig, axs = plt.subplots(1, 3, figsize=(11, 3.6), sharey=False)
for ax, n in zip(axs, (20, 100, 1000)):
    cv = out[f"exch_{n}"]
    ax.hist(cv, bins=40, density=True, color=BLUE, alpha=.55, label="2,000回の分割")
    l = int(np.floor((n + 1) * ALPHA)); th = beta(n + 1 - l, l)
    x = np.linspace(max(.6, cv.min() - .02), 1, 400)
    ax.plot(x, th.pdf(x), color=ORANGE, lw=2, label="理論（ベータ分布）")
    ax.axvline(.9, color=GRAY, ls="--", lw=1)
    ax.set_title(f"較正に使う点が {n} 個", fontsize=11)
    ax.set_xlabel("新しい点が区間に入った割合"); ax.set_yticks([])
axs[0].legend(fontsize=8, loc="upper left")
fig.suptitle("平均はどれも90%前後。ただし較正の点が少ないと、1回ごとの当たり方は大きく揺れる", fontsize=12)
fig.tight_layout()
save(fig, "p03_01_finite_sample.png", SRC)


# ---------- 2. 時間の順に使うとき：固定の区間・ローリング・適応（ACI） ----------
def run(test_resid, cal_resid, ts, gamma=0.05, window_days=28):
    days = pd.DatetimeIndex(ts).normalize()
    ud = days.unique()
    z = norm.ppf(1 - ALPHA / 2)
    width = {"正規分布を仮定（固定）": np.full(len(ts), 2 * z * cal_resid.std(ddof=1)),
             "分割コンフォーマル（固定）": np.full(len(ts), 2 * conformal_q(np.abs(cal_resid), ALPHA))}
    center = {"正規分布を仮定（固定）": cal_resid.mean()}
    roll_w, aci_w = np.zeros(len(ts)), np.zeros(len(ts))
    hist = list(np.abs(cal_resid[-24 * window_days:]))     # 初めの窓は較正の年の最後の28日
    a_t, alphas = ALPHA, []
    for d in ud:
        m = days == d
        win = np.array(hist[-24 * window_days:])
        roll_w[m] = 2 * conformal_q(win, ALPHA)
        qa = conformal_q(win, min(max(a_t, 1e-4), .999)) if a_t > 0 else np.inf
        if not np.isfinite(qa):
            qa = win.max()
        aci_w[m] = 2 * qa
        err = np.mean(np.abs(test_resid[m]) > qa)            # その日が終わってから分かる外れの割合
        a_t = a_t + gamma * (ALPHA - err)
        alphas.append(a_t)
        hist.extend(np.abs(test_resid[m]))
    width["ローリング（直近28日）"] = roll_w
    width["適応（ACI）"] = aci_w
    res = {}
    for k, w in width.items():
        c = center.get(k, 0.0)
        res[k] = np.abs(test_resid - c) <= w / 2
    return width, res, np.array(alphas)


cases = {
    "A 実測の気温で予測（ずれなし）": ((tst.actual - tst["毎月"]).values, r_cal),
    "B 予報の気温で予測（較正は実測の気温）": ((tst.actual - tst["毎月（気温に誤差）"]).values, r_cal),
    "C 3年前に学習したままのモデル": ((tst.actual - tst["固定・3年前に学習したまま"]).values,
                                    (cal.actual - cal["固定・3年前に学習したまま"]).values),
}
month = tst.ts.dt.to_period("M").astype(str).values
summ, monthly, alpha_paths = [], [], {}
for case, (rt, rc) in cases.items():
    width, hit, alphas = run(rt, rc, tst.ts)
    alpha_paths[case] = alphas
    for k in width:
        mc = pd.Series(hit[k]).groupby(month).mean()
        summ.append({"case": case, "method": k, "coverage": hit[k].mean(), "month_min": mc.min(),
                     "month_max": mc.max(), "months_below_85": int((mc < .85).sum()),
                     "mean_width_mw": width[k].mean()})
        for mm, v in mc.items():
            monthly.append({"case": case, "method": k, "month": mm, "coverage": v})
S = pd.DataFrame(summ); M = pd.DataFrame(monthly)
S.round(4).to_csv(RES / "a_time_order_summary.csv", index=False, encoding="utf-8")
M.round(4).to_csv(RES / "a_time_order_monthly.csv", index=False, encoding="utf-8")

cols = {"正規分布を仮定（固定）": GRAY, "分割コンフォーマル（固定）": BLUE, "ローリング（直近28日）": GREEN, "適応（ACI）": ORANGE}
fig, axs = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
for ax, case in zip(axs, list(cases)[:2]):
    mm = M[M.case == case]
    for k, c in cols.items():
        d = mm[mm.method == k]
        ax.plot(range(len(d)), d.coverage * 100, marker="o", ms=3.5, color=c, label=k, lw=1.6)
    ax.axhline(90, color="#555", ls="--", lw=1)
    ax.set_xticks(range(12), [m[2:4] + "/" + m[5:] for m in d.month], fontsize=8)
    ax.set_title(case, fontsize=11); ax.set_xlabel("月（年/月）")
axs[0].set_ylabel("区間に入った割合（%）、目標90%")
axs[0].legend(fontsize=8, loc="lower left")
fig.suptitle("較正したときと条件が変わると、固定の区間は外れが増える。直近の誤差で作り直す方法は目標の近くに戻る", fontsize=12)
fig.tight_layout()
save(fig, "p03_02_monthly_coverage.png", SRC)

# 幅と当たり方の関係（ケース B）
sb = S[S.case == list(cases)[1]].set_index("method")
fig, ax = plt.subplots(figsize=(7.5, 4.2))
for k, c in cols.items():
    ax.scatter(sb.loc[k, "mean_width_mw"], sb.loc[k, "coverage"] * 100, s=90, color=c, zorder=3)
    ax.annotate(f"{k}\n最も悪い月 {sb.loc[k, 'month_min'] * 100:.0f}%", (sb.loc[k, "mean_width_mw"], sb.loc[k, "coverage"] * 100),
                textcoords="offset points", xytext=(8, -4), fontsize=8.5)
ax.axhline(90, color="#555", ls="--", lw=1)
ax.set_xlabel("区間の平均の幅（MW）"); ax.set_ylabel("1年で区間に入った割合（%）")
ax.set_title("予報の気温で予測した1年：当たり方を戻すには、幅を広げるしかない", fontsize=11)
x0, x1 = ax.get_xlim(); ax.set_xlim(x0, x1 + (x1 - x0) * 0.45)
fig.tight_layout()
save(fig, "p03_03_width_vs_coverage.png", SRC)

g = lambda case, k, c: float(S[(S.case == case) & (S.method == k)][c].iloc[0])
A, B, C = list(cases)
main = {
    "exch_n20_mean": float(ex.loc[0, "conformal_mean"]), "exch_n20_p05": float(ex.loc[0, "conformal_p05"]),
    "exch_n20_p95": float(ex.loc[0, "conformal_p95"]), "exch_n20_below85": float(ex.loc[0, "conformal_below_85"]),
    "exch_n1000_p05": float(ex.loc[2, "conformal_p05"]), "exch_n1000_p95": float(ex.loc[2, "conformal_p95"]),
    "exch_theory_n20_p05": float(ex.loc[0, "theory_p05"]), "exch_theory_n20_p95": float(ex.loc[0, "theory_p95"]),
    "gauss_n1000_mean": float(ex.loc[2, "gauss_mean"]),
    "cal_resid_sd": float(r_cal.std(ddof=1)), "cal_q90": float(conformal_q(np.abs(r_cal), ALPHA)),
}
for case, tag in ((A, "A"), (B, "B"), (C, "C")):
    for k, kk in (("正規分布を仮定（固定）", "gauss"), ("分割コンフォーマル（固定）", "split"),
                  ("ローリング（直近28日）", "roll"), ("適応（ACI）", "aci")):
        for c in ("coverage", "month_min", "mean_width_mw", "months_below_85"):
            main[f"{tag}_{kk}_{c}"] = g(case, k, c)
main["B_resid_sd"] = float(cases[B][0].std(ddof=1))
main["B_aci_alpha_min"] = float(alpha_paths[B].min()); main["B_aci_alpha_end"] = float(alpha_paths[B][-1])
json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()},
          open(RES / "a_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(S.round(3).to_string()); print(ex.round(3).to_string())
