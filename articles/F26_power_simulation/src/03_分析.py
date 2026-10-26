"""検出力シミュレーション（差の差のモンテカルロ）
A 実データに「でたらめな処置」を置く：処置県の数 k・期間の長さ T・効果 δ を変えて、効果を見つけられる割合（検出力）
B 標準誤差の種類と誤検出（効果0なのに有意になる割合）：OLS／HC1／県クラスター／wild cluster bootstrap
C 誤差の構造を変える：AR(1) の強さを変えた人工データ
D 乱数の種を変える
E 処置の時期がずれて効果が育つ場合：二方向固定効果（TWFE）と Callaway–Sant'Anna 型（CS）
F F14 の設定（市町村の2時点の差）：何市町村あれば何ポイントの差が見えるか
G これまでの看板記事の推定がどこにあるか（最小検出効果との比較）
"""
import json, time
import numpy as np, pandas as pd
from scipy import stats
from joblib import Parallel, delayed
from common import DATA, RES, SEED, wide, did_twfe, wild_cluster_p

t0 = time.time()
P = pd.read_csv(DATA / "panel.csv")
YEARS12 = list(range(2008, 2020))
YEARS18 = list(range(2008, 2026))
REPS = 1000
DELTAS = np.round(np.arange(0, 1.21, 0.1), 2)
KS = [3, 5, 10, 15, 23, 30, 40]
TS = [4, 6, 8, 12]
CRIT = stats.t.ppf(0.975, 46)  # 県クラスター：自由度 G-1


def placebo_draws(Y, k, T, reps, rng):
    """実データからでたらめな処置を作り、効果0のときの推定値と標準誤差を返す（効果δを足すと推定値が δ ずれるだけで、標準誤差は変わらない）"""
    N, TT = Y.shape
    res = np.empty((reps, 4))
    for r in range(reps):
        s = rng.integers(0, TT - T + 1)
        Ys = Y[:, s:s + T]
        tr = rng.choice(N, k, replace=False)
        D = np.zeros((N, T)); D[tr, T // 2:] = 1
        res[r] = did_twfe(Ys, D)
    return res


def power_from(res, delta, se_col=3, crit=CRIT):
    return float((np.abs(res[:, 0] + delta) / res[:, se_col] > crit).mean())


# ---------- A 実データのでたらめ処置 ----------
def cell(col, yrs_label, k, T, seed):
    rng = np.random.default_rng(seed)
    Y, _ = wide(P, col, YEARS12 if yrs_label == "2008-2019" else YEARS18)
    if T > Y.shape[1]:
        return []
    res = placebo_draws(Y, k, T, REPS, rng)
    out = []
    for dlt in DELTAS:
        out.append(dict(outcome=col, years=yrs_label, k=k, T=T, delta=float(dlt),
                        power_cl=power_from(res, dlt, 3), power_ols=power_from(res, dlt, 1, 1.96),
                        power_hc1=power_from(res, dlt, 2, 1.96),
                        sd_est=float(res[:, 0].std()), mean_se_cl=float(res[:, 3].mean())))
    return out

jobs = []
for col in ["emp_rate", "unemp_rate"]:
    for yl in ["2008-2019", "2008-2025"]:
        for k in KS:
            for T in TS + ([18] if yl == "2008-2025" else []):
                jobs.append((col, yl, k, T, SEED + 7 * k + T + (0 if col == "emp_rate" else 1000) + (0 if yl == "2008-2019" else 5000)))
A = Parallel(n_jobs=2)(delayed(cell)(*j) for j in jobs)
A = pd.DataFrame([r for x in A for r in x])
A.to_csv(RES / "power_grid.csv", index=False)
print("A", len(A), round(time.time() - t0, 1))

# 最小検出効果（検出力80%）：推定値のばらつきから計算
def mde_from(res, crit=CRIT):
    grid = np.arange(0, 3.0, 0.005)
    pw = np.array([power_from(res, g) for g in grid])
    i = np.argmax(pw >= 0.8)
    return float(grid[i]) if pw[i] >= 0.8 else np.nan

mde_rows = []
rng = np.random.default_rng(SEED + 1)
for col in ["emp_rate", "unemp_rate"]:
    Y, _ = wide(P, col, YEARS12)
    for k in KS:
        for T in TS:
            res = placebo_draws(Y, k, T, REPS, rng)
            mde_rows.append(dict(outcome=col, k=k, T=T, mde80=mde_from(res), fpr_cl=power_from(res, 0.0)))
MDE = pd.DataFrame(mde_rows); MDE.to_csv(RES / "mde_grid.csv", index=False)
print("MDE", round(time.time() - t0, 1))

# ---------- B 標準誤差の種類と誤検出 ----------
def fpr_cell(col, k, seed, reps=500, B=199):
    rng = np.random.default_rng(seed)
    Y, _ = wide(P, col, YEARS12)
    N, T = Y.shape
    rej = np.zeros(4)
    for r in range(reps):
        tr = rng.choice(N, k, replace=False)
        D = np.zeros((N, T)); D[tr, T // 2:] = 1
        b, so, sh, sc = did_twfe(Y, D)
        rej[0] += abs(b / so) > 1.96
        rej[1] += abs(b / sh) > 1.96
        rej[2] += abs(b / sc) > CRIT
        rej[3] += wild_cluster_p(Y, D, B, rng) < 0.05
    return [dict(outcome=col, k=k, se=s, fpr=float(v / reps)) for s, v in
            zip(["OLS（普通の標準誤差）", "HC1（不均一分散に頑健）", "県クラスター", "wild cluster bootstrap"], rej)]

B_ = Parallel(n_jobs=2)(delayed(fpr_cell)(c, k, SEED + 31 * k + (0 if c == "emp_rate" else 99))
                       for c in ["emp_rate", "unemp_rate"] for k in [2, 3, 5, 10, 23])
B_ = pd.DataFrame([r for x in B_ for r in x]); B_.to_csv(RES / "fpr_by_se.csv", index=False)
print("B", round(time.time() - t0, 1))

# ---------- C 誤差の構造を変える（人工データ） ----------
es = json.load(open(RES / "error_structure.json"))
SD = es["emp_rate|2008-2019"]["resid_sd"]
def ar_panel(N, T, rho, sd, rng, burn=20):
    u = rng.normal(0, sd * np.sqrt(1 - rho ** 2), size=(N, T + burn))
    e = np.zeros_like(u); e[:, 0] = rng.normal(0, sd, N)
    for t in range(1, T + burn):
        e[:, t] = rho * e[:, t - 1] + u[:, t]
    return e[:, burn:]

C_rows = []
rng = np.random.default_rng(SEED + 2)
for rho in [0.0, 0.3, 0.6, 0.9]:
    res = np.empty((2000, 4))
    for r in range(2000):
        Y = ar_panel(47, 12, rho, SD, rng)
        tr = rng.choice(47, 23, replace=False)
        D = np.zeros((47, 12)); D[tr, 6:] = 1
        res[r] = did_twfe(Y, D)
    for dlt in [0.0, 0.3, 0.5]:
        C_rows.append(dict(rho=rho, delta=dlt, power_cl=power_from(res, dlt, 3), power_ols=power_from(res, dlt, 1, 1.96),
                           power_hc1=power_from(res, dlt, 2, 1.96), sd_est=float(res[:, 0].std())))
C = pd.DataFrame(C_rows); C.to_csv(RES / "error_structure_sim.csv", index=False)
print("C", round(time.time() - t0, 1))

# ---------- D 乱数の種 ----------
D_rows = []
Y, _ = wide(P, "emp_rate", YEARS12)
for s in range(5):
    res = placebo_draws(Y, 23, 12, REPS, np.random.default_rng(SEED + 100 + s))
    D_rows.append(dict(seed=SEED + 100 + s, power_03=power_from(res, 0.3), power_05=power_from(res, 0.5),
                       fpr=power_from(res, 0.0), mde80=mde_from(res)))
pd.DataFrame(D_rows).to_csv(RES / "seeds.csv", index=False)
print("D", round(time.time() - t0, 1))

# ---------- E 処置の時期がずれる＋効果が育つ：TWFE と CS ----------
COH = [2012, 2014, 2016]
def cs_att(Y, cohort, years):
    """Callaway–Sant'Anna 型：まだ処置されない県ではなく「最後まで処置されない県」と比べる。基準は処置の前年。
    ATT(g,t) を処置後のセルで（コホートの県数で重みづけて）平均する"""
    yi = {y: i for i, y in enumerate(years)}
    never = cohort == 0
    num, den = 0.0, 0.0
    for g in COH:
        m = cohort == g
        if m.sum() == 0: continue
        b = yi[g - 1]
        for t in years:
            if t < g: continue
            j = yi[t]
            att = (Y[m, j] - Y[m, b]).mean() - (Y[never, j] - Y[never, b]).mean()
            num += att * m.sum(); den += m.sum()
    return num / den

def stag_rep(Y, years, delta, rng, nb=99):
    N, T = Y.shape
    perm = rng.permutation(N)
    cohort = np.zeros(N, int)
    for i, g in enumerate(COH):
        cohort[perm[i * 8:(i + 1) * 8]] = g
    D = np.zeros((N, T)); Eff = np.zeros((N, T))
    for i in range(N):
        if cohort[i]:
            for j, t in enumerate(years):
                if t >= cohort[i]:
                    D[i, j] = 1
                    Eff[i, j] = delta * min(t - cohort[i] + 1, 4) / 4   # 4年目で δ に育つ
    Yt = Y + Eff
    true_att = Eff[D == 1].mean()
    b, _, _, sc = did_twfe(Yt, D)
    cs = cs_att(Yt, cohort, years)
    # CS の標準誤差：県を単位にしたブートストラップ（処置の有無の層ごと）
    idx_t, idx_n = np.where(cohort > 0)[0], np.where(cohort == 0)[0]
    bs = []
    for _ in range(nb):
        s = np.r_[rng.choice(idx_t, len(idx_t)), rng.choice(idx_n, len(idx_n))]
        bs.append(cs_att(Yt[s], cohort[s], years))
    se_cs = np.std(bs, ddof=1)
    return true_att, b, sc, cs, se_cs

def stag_cell(delta, seed, reps=300):
    rng = np.random.default_rng(seed)
    Y, _ = wide(P, "emp_rate", YEARS12)
    out = np.array([stag_rep(Y, YEARS12, delta, rng) for _ in range(reps)])
    tr, b, sc, cs, scs = out.T
    return dict(delta=delta, true_att=float(tr.mean()), twfe_mean=float(b.mean()), cs_mean=float(cs.mean()),
                twfe_bias=float((b - tr).mean()), cs_bias=float((cs - tr).mean()),
                twfe_power=float((np.abs(b / sc) > CRIT).mean()), cs_power=float((np.abs(cs / scs) > 1.96).mean()),
                twfe_sd=float(b.std()), cs_sd=float(cs.std()))
E_ = Parallel(n_jobs=2)(delayed(stag_cell)(d, SEED + int(d * 100) + 7) for d in [0.0, 0.3, 0.6, 1.0])
pd.DataFrame(E_).to_csv(RES / "staggered_twfe_cs.csv", index=False)
print("E", round(time.time() - t0, 1))

# ---------- F F14 の設定（市町村の2時点の差） ----------
f = pd.read_csv(DATA / "f14_cross.csv")
y20, y15 = f["d_dens_2020_w"].to_numpy(), f["d_dens_2015_w"].to_numpy()
rng = np.random.default_rng(SEED + 3)
F_rows = []
for n_total in [100, 200, 400, 635]:
    for share in [0.47]:
        diffs, diffs_adj = [], []
        for r in range(2000):
            s = rng.choice(len(f), n_total, replace=False)
            nt = int(round(n_total * share))
            t = np.zeros(n_total, bool); t[rng.choice(n_total, nt, replace=False)] = True
            yy, xx = y20[s], y15[s]
            diffs.append(yy[t].mean() - yy[~t].mean())
            # 前の期間の変化をそろえる（ANCOVA）
            X = np.c_[np.ones(n_total), t, xx]
            diffs_adj.append(np.linalg.lstsq(X, yy, rcond=None)[0][1])
        sd, sda = np.std(diffs), np.std(diffs_adj)
        F_rows.append(dict(n_total=n_total, n_treat=int(round(n_total * share)), sd_diff=float(sd), mde80=float(2.8 * sd),
                           sd_diff_adj=float(sda), mde80_adj=float(2.8 * sda)))
pd.DataFrame(F_rows).to_csv(RES / "f14_mde.csv", index=False)
print("F", round(time.time() - t0, 1))

# ---------- G これまでの看板記事 ----------
G = pd.DataFrame([
    dict(key="F01 就業率", est=0.414, se=0.229, unit="%pt"),
    dict(key="F01 失業率", est=-0.190, se=0.103, unit="%pt"),
    dict(key="F14 人口集中地区の密度", est=0.22, se=(2.06 + 1.51) / (2 * 1.96), unit="%pt"),
    dict(key="F15 飲食＋小売の雇用", est=1.41, se=1.72, unit="弾力性"),
    dict(key="F16 保育所と女性の労働力率", est=0.0656, se=0.0303, unit="%pt"),
    dict(key="F17 最低賃金の平均効果", est=-0.09, se=(0.22 + 0.40) / (2 * 1.96), unit="%pt"),
])
G["mde80"] = 2.8 * G["se"]
G["ratio"] = G["est"].abs() / G["mde80"]
G.to_csv(RES / "past_flagships.csv", index=False)
print(G)
print("done", round(time.time() - t0, 1))
