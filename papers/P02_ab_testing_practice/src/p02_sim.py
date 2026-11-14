"""P02 A/B テストの実務を論文3本で読む：シミュレーション一式。
すべて種を固定したシミュレーション（架空のECサイト）。設定は articles/F237 に合わせた（購入率5%、1日5,000人、14日）。
使い方: cd src && python p02_sim.py
"""
import json
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm, chi2

HERE = Path(__file__).resolve().parents[1]
R = HERE / "results"; R.mkdir(exist_ok=True)
BASE, LIFT, DAILY_PER_ARM, DAYS = 0.05, 0.10, 2500, 14
main = {}

# ---------------------------------------------------------------- A. 割り付けの比率のずれ（SRM）
# 処置群だけ、一部の人の記録が落ちる（例：リダイレクトの途中で離れた人が数えられない）。
# 落ちるのは「買わない人」に偏る、とする（記録の落ち方と行動が関係する場合）。
rng = np.random.default_rng(201)
R_A = 4000
rows = []
for loss in [0.0, 0.005, 0.01, 0.02, 0.05]:
    for days in [1, 3, 7, 14]:
        n_assign = DAILY_PER_ARM * days
        nA = rng.binomial(2 * n_assign, 0.5, R_A)          # 50:50 でくじ
        nB_true = 2 * n_assign - nA
        # 処置群で、買わない人のうち loss/(1-BASE) の割合が記録から落ちる → 全体の loss が落ちる
        buyB = rng.binomial(nB_true, BASE * (1 + 0))        # 効果なし（A/A）で偏りだけを見る
        nonbuyB = nB_true - buyB
        dropped = rng.binomial(nonbuyB, min(loss / (1 - BASE), 1))
        nB = nB_true - dropped
        buyA = rng.binomial(nA, BASE)
        tot = nA + nB
        x2 = (nA - tot / 2) ** 2 / (tot / 2) + (nB - tot / 2) ** 2 / (tot / 2)
        p_srm = 1 - chi2.cdf(x2, 1)
        lift_hat = (buyB / nB) / (buyA / nA) - 1
        rows.append(dict(loss=loss, days=days, srm_detect_rate_p001=float((p_srm < 0.001).mean()),
                         mean_lift_hat=float(lift_hat.mean()), sd_lift_hat=float(lift_hat.std())))
A = pd.DataFrame(rows); A.to_csv(R / "A_srm.csv", index=False)
main["A"] = {"loss1pct_14d_detect": float(A.query("loss==0.01 and days==14").srm_detect_rate_p001.iloc[0]),
             "loss1pct_1d_detect": float(A.query("loss==0.01 and days==1").srm_detect_rate_p001.iloc[0]),
             "loss0_14d_detect": float(A.query("loss==0.0 and days==14").srm_detect_rate_p001.iloc[0]),
             "loss1pct_bias": float(A.query("loss==0.01 and days==14").mean_lift_hat.iloc[0]),
             "loss05_14d_detect": float(A.query("loss==0.005 and days==14").srm_detect_rate_p001.iloc[0]),
             "loss2pct_14d_detect": float(A.query("loss==0.02 and days==14").srm_detect_rate_p001.iloc[0]),
             "loss5pct_14d_detect": float(A.query("loss==0.05 and days==14").srm_detect_rate_p001.iloc[0]),
             "loss5pct_1d_detect": float(A.query("loss==0.05 and days==1").srm_detect_rate_p001.iloc[0]),
             "loss5pct_bias": float(A.query("loss==0.05 and days==14").mean_lift_hat.iloc[0]),
             "loss2pct_bias": float(A.query("loss==0.02 and days==14").mean_lift_hat.iloc[0])}

# ---------------------------------------------------------------- B. トレンドに見える効果（A/A）と、日数を延ばしても縮まない幅
# B1: A/A で累積の差を毎日見る。日 k の累積の推定が、14日目の 95% 区間の外にある割合。
rng = np.random.default_rng(202)
R_B = 4000
cA = rng.binomial(DAILY_PER_ARM, BASE, (R_B, DAYS)).cumsum(1)
cB = rng.binomial(DAILY_PER_ARM, BASE, (R_B, DAYS)).cumsum(1)
n = DAILY_PER_ARM * np.arange(1, DAYS + 1)
lift_path = (cB / n) / (cA / n) - 1
pf = (cA[:, -1] + cB[:, -1]) / (2 * n[-1])
se_final = np.sqrt(2 * pf * (1 - pf) / n[-1]) / pf          # 相対差の標準誤差（近似）
lo, hi = lift_path[:, -1] - 1.96 * se_final, lift_path[:, -1] + 1.96 * se_final
outside = ((lift_path < lo[:, None]) | (lift_path > hi[:, None])).mean(0)
# 4日続けて同じ向きに動いた（単調に上がるか下がる）割合
d = np.diff(lift_path[:, :4], axis=1)
mono4 = float(((d > 0).all(1) | (d < 0).all(1)).mean())
B1 = pd.DataFrame({"day": np.arange(1, DAYS + 1), "share_outside_final_ci": outside})
B1.to_csv(R / "B1_aa_trend.csv", index=False)
np.save(R / "B1_paths_sample.npy", lift_path[:30])

# B2: 1人あたりのセッション数のように、人ごとの差が大きい指標。人は日ごとに初めて来て、来た後も来続ける。
# 見る日数を延ばすと、人数は増えるが1人あたりの値のばらつきも増える → 幅（相対）が縮みにくい。
rng = np.random.default_rng(203)
N_POOL = 60_000                       # この群に来うる人
first_rate = 1 / 20                   # 毎日、まだ来ていない人の約5%が初めて来る（推測で置いた値）
lam = rng.gamma(0.6, 1 / 0.6 * 0.4, N_POOL)    # 人ごとの1日あたりの訪問の強さ（平均0.4、ばらつき大）
first_day = rng.geometric(first_rate, N_POOL)   # 初めて来る日
conv_p = 0.05
rows = []
for days in [1, 3, 7, 14, 21, 28, 35]:
    seen = first_day <= days
    exposure = np.clip(days - first_day + 1, 0, None)[seen]
    sessions = rng.poisson(lam[seen] * exposure)
    sessions = np.maximum(sessions, 1)              # 来た日に最低1回
    m, s = sessions.mean(), sessions.std()
    nseen = int(seen.sum())
    cv = s / m
    rel_ci_sessions = 1.96 * np.sqrt(2) * cv / np.sqrt(nseen)
    # 比べる指標：1人あたり「1回でも買ったか」（上限がある指標）
    buy = rng.random(nseen) < 1 - (1 - conv_p) ** np.minimum(sessions, 50)
    pb = buy.mean(); cvb = np.sqrt(pb * (1 - pb)) / pb
    rel_ci_buy = 1.96 * np.sqrt(2) * cvb / np.sqrt(nseen)
    rows.append(dict(days=days, users=nseen, sessions_mean=m, sessions_cv=cv, rel_ci_sessions=rel_ci_sessions,
                     buy_rate=pb, rel_ci_buy=rel_ci_buy))
B2 = pd.DataFrame(rows); B2.to_csv(R / "B2_ci_width.csv", index=False)
main["B"] = {"aa_day1_outside": float(outside[0]), "aa_day2_outside": float(outside[1]),
             "aa_day7_outside": float(outside[6]), "aa_mono4": mono4,
             "sess_ci_7d": float(B2.query("days==7").rel_ci_sessions.iloc[0]),
             "sess_ci_28d": float(B2.query("days==28").rel_ci_sessions.iloc[0]),
             "buy_ci_7d": float(B2.query("days==7").rel_ci_buy.iloc[0]),
             "buy_ci_28d": float(B2.query("days==28").rel_ci_buy.iloc[0]),
             "users_7d": int(B2.query("days==7").users.iloc[0]), "users_28d": int(B2.query("days==28").users.iloc[0]),
             "cv_7d": float(B2.query("days==7").sessions_cv.iloc[0]), "cv_28d": float(B2.query("days==28").sessions_cv.iloc[0])}

# ---------------------------------------------------------------- C. CUPED
# 人ごとの「来る強さ」を共通にして、テスト前 P 日の訪問数 X と、テスト中14日の訪問数 Y を作る。
rng = np.random.default_rng(204)
R_C, N_ARM = 800, 4000
TRUE_LIFT_C = 0.03                     # 処置で訪問が3%増える

def cuped_once(rng, pre_days, new_share=0.0, bad_cov=False):
    nn = 2 * N_ARM
    # 強さは週ごとに少し揺れる（期間が離れると相関が下がる）
    base = rng.gamma(0.8, 1 / 0.8 * 0.5, nn)
    drift = rng.lognormal(0, 0.35, nn)
    lam_pre, lam_exp = base, base * drift
    t = np.r_[np.zeros(N_ARM), np.ones(N_ARM)].astype(bool)
    rng.shuffle(t)
    Y = rng.poisson(lam_exp * DAYS * np.where(t, 1 + TRUE_LIFT_C, 1.0))
    X = rng.poisson(lam_pre * pre_days).astype(float)
    new = rng.random(nn) < new_share
    has = ~new
    X[new] = 0.0
    if bad_cov:
        # テスト中の値を共変量に使ってしまう（処置の影響を受ける）
        X = rng.poisson(lam_exp * 7 * np.where(t, 1 + TRUE_LIFT_C, 1.0)).astype(float)
    diff = Y[t].mean() / Y[~t].mean() - 1
    # CUPED：theta = cov(Y, X)/var(X)（新規の人がいるときは「前の値があるか」も入れた回帰で調整）
    if new_share > 0 and not bad_cov:
        Z = np.c_[X, has.astype(float)]
        Zc = Z - Z.mean(0)
        beta = np.linalg.lstsq(Zc, Y - Y.mean(), rcond=None)[0]
        Yc = Y - Zc @ beta
    else:
        theta = np.cov(Y, X)[0, 1] / X.var(ddof=1)
        Yc = Y - theta * (X - X.mean())
    adj = (Yc[t].mean() - Yc[~t].mean()) / Y[~t].mean()
    rho = np.corrcoef(Y, X)[0, 1]
    return diff, adj, rho

rows = []
for pre in [1, 3, 7, 14, 28]:
    out = np.array([cuped_once(rng, pre) for _ in range(R_C)])
    rows.append(dict(setting=f"前の期間 {pre}日", pre_days=pre, new_share=0.0, rho=out[:, 2].mean(),
                     var_ratio=out[:, 1].var() / out[:, 0].var(), mean_adj=out[:, 1].mean(), mean_raw=out[:, 0].mean()))
for ns in [0.2, 0.5]:
    out = np.array([cuped_once(rng, 14, new_share=ns) for _ in range(R_C)])
    rows.append(dict(setting=f"前の期間14日・新規 {int(ns*100)}%", pre_days=14, new_share=ns, rho=out[:, 2].mean(),
                     var_ratio=out[:, 1].var() / out[:, 0].var(), mean_adj=out[:, 1].mean(), mean_raw=out[:, 0].mean()))
out = np.array([cuped_once(rng, 14, bad_cov=True) for _ in range(R_C)])
rows.append(dict(setting="テスト中の値を共変量に（やってはいけない）", pre_days=0, new_share=0.0, rho=out[:, 2].mean(),
                 var_ratio=out[:, 1].var() / out[:, 0].var(), mean_adj=out[:, 1].mean(), mean_raw=out[:, 0].mean()))
C = pd.DataFrame(rows); C["theory_1_minus_rho2"] = 1 - C.rho ** 2
C.to_csv(R / "C_cuped.csv", index=False)
g = lambda s, c: float(C.loc[C.setting == s, c].iloc[0])
main["C"] = {"true_lift": TRUE_LIFT_C,
             "rho_14": g("前の期間 14日", "rho"), "varratio_14": g("前の期間 14日", "var_ratio"),
             "rho_1": g("前の期間 1日", "rho"), "varratio_1": g("前の期間 1日", "var_ratio"),
             "rho_28": g("前の期間 28日", "rho"), "varratio_28": g("前の期間 28日", "var_ratio"),
             "varratio_new50": g("前の期間14日・新規 50%", "var_ratio"),
             "bad_mean_adj": g("テスト中の値を共変量に（やってはいけない）", "mean_adj"),
             "bad_mean_raw": g("テスト中の値を共変量に（やってはいけない）", "mean_raw")}

# ---------------------------------------------------------------- D. mSPRT と、途中で見る誤り
rng = np.random.default_rng(205)
R_D, H = 4000, DAYS * 24
nh = np.full(H, DAILY_PER_ARM // 24); nh[: (DAILY_PER_ARM * DAYS - nh.sum()) % H] += 0
n_cum = np.cumsum(nh)

def msprt_p(cA, cB, n, tau):
    pa = cA / n; pb = cB / n
    V = (pa * (1 - pa) + pb * (1 - pb)) / n
    pp = (cA + cB) / (2 * n)
    V = np.where(V > 0, V, np.maximum(pp * (1 - pp) * 2 / n, 1e-12))
    th = pb - pa; t2 = tau ** 2
    logL = 0.5 * np.log(V / (V + t2)) + th ** 2 * t2 / (2 * V * (V + t2))
    return np.minimum.accumulate(np.minimum(1.0, np.exp(-logL)), axis=1)

def naive_p(cA, cB, n):
    pa = cA / n; pb = cB / n; pp = (cA + cB) / (2 * n)
    z = (pb - pa) / np.sqrt(np.maximum(pp * (1 - pp) * 2 / n, 1e-300))
    return 2 * (1 - norm.cdf(np.abs(z)))

rows = []
paths = {}
for label, lift in [("差なし", 0.0), ("+10%", LIFT)]:
    cA = rng.binomial(nh[None, :], BASE, (R_D, H)).cumsum(1)
    cB = rng.binomial(nh[None, :], BASE * (1 + lift), (R_D, H)).cumsum(1)
    p_naive = naive_p(cA, cB, n_cum)
    daily_idx = np.arange(23, H, 24)
    for tau_rel in [0.05, 0.10, 0.20, 0.40]:
        p_m = msprt_p(cA, cB, n_cum, BASE * tau_rel)
        rej = p_m[:, -1] < 0.05
        stop = np.where(rej, (p_m < 0.05).argmax(1) / 24, np.nan)
        rows.append(dict(truth=label, method=f"mSPRT τ=基準の{int(tau_rel*100)}%", reject=float(rej.mean()),
                         mean_stop_day=float(np.nanmean(stop)) if rej.any() else np.nan))
    rows.append(dict(truth=label, method="毎日見て p<0.05 で止める", reject=float((p_naive[:, daily_idx] < 0.05).any(1).mean()), mean_stop_day=np.nan))
    rows.append(dict(truth=label, method="1時間ごとに見て p<0.05 で止める", reject=float((p_naive < 0.05).any(1).mean()), mean_stop_day=np.nan))
    rows.append(dict(truth=label, method="14日目に1回だけ見る", reject=float((p_naive[:, -1] < 0.05).mean()), mean_stop_day=np.nan))
    if label == "差なし":
        p_m10 = msprt_p(cA, cB, n_cum, BASE * 0.10)
        pd_ = p_naive[:, daily_idx]
        cand = np.where((pd_[:, :4] >= 0.05).all(1) & (pd_[:, 4:10] < 0.05).any(1) & (pd_[:, -1] >= 0.05))[0]
        k = int(cand[0])   # 5〜10日目に一度 p<0.05 になり、最後は差なしに戻った例
        paths = {"naive": p_naive[k, daily_idx].tolist(), "msprt": p_m10[k, daily_idx].tolist()}
D = pd.DataFrame(rows); D.to_csv(R / "D_msprt.csv", index=False)
json.dump(paths, open(R / "D_path_example.json", "w"), ensure_ascii=False)
gd = lambda t, m, c: float(D.loc[(D.truth == t) & (D.method == m), c].iloc[0])
main["D"] = {"fpr_fixed": gd("差なし", "14日目に1回だけ見る", "reject"),
             "fpr_daily": gd("差なし", "毎日見て p<0.05 で止める", "reject"),
             "fpr_hourly": gd("差なし", "1時間ごとに見て p<0.05 で止める", "reject"),
             "fpr_msprt10": gd("差なし", "mSPRT τ=基準の10%", "reject"),
             "power_fixed": gd("+10%", "14日目に1回だけ見る", "reject"),
             "power_msprt05": gd("+10%", "mSPRT τ=基準の5%", "reject"),
             "power_msprt10": gd("+10%", "mSPRT τ=基準の10%", "reject"),
             "power_msprt20": gd("+10%", "mSPRT τ=基準の20%", "reject"),
             "power_msprt40": gd("+10%", "mSPRT τ=基準の40%", "reject"),
             "stop_msprt10": gd("+10%", "mSPRT τ=基準の10%", "mean_stop_day")}

json.dump(main, open(R / "main.json", "w"), ensure_ascii=False, indent=2, default=float)
print(json.dumps(main, ensure_ascii=False, indent=1, default=float))
