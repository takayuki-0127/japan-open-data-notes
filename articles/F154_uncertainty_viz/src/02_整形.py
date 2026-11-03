"""3つの例の「予測のシミュレーション」をそろえる。
- 出生数：F55 の 4,000 本（年の出生数、2026〜2030年）と、2020〜25年の月の 4,000 本を年に足し上げたもの
- 平均寿命：F86 と同じ Lee–Carter（1970〜2024年で当てはめ、2段目あり、出発点は2024年の実際の死亡率、
  k はドリフトの推定誤差も入れたランダムウォーク、seed=42、男→女の順に 5,000 本）をやり直し、F86 の表と一致するか確かめる
- 電力：F92 の日ごとの予測と実績は data/raw/f92_pred_tokyo.csv をそのまま 03_分析.py で読む
"""
import numpy as np
import pandas as pd
from scipy.optimize import brentq
from common import RAW, DATA, SEED

AGE_MAX = 99


def e0_from_mx(mx):
    mx = np.asarray(mx, dtype=float); n = len(mx)
    a = np.full(n, 0.5); a[0] = 0.1
    q = np.clip(mx / (1 + (1 - a) * mx), 0, 1)
    l = np.empty(n); l[0] = 1.0
    for i in range(1, n):
        l[i] = l[i - 1] * (1 - q[i - 1])
    d = l * q; L = l - (1 - a) * d
    L[-1] = l[-1] / mx[-1] if mx[-1] > 0 else 0.0
    return L.sum() / l[0]


def lc_forecast(long, sex, rng, y0=1970, y1=2024, h_end=2070, nsim=5000):
    d = long[(long.sex == sex) & (long.year.between(y0, y1))]
    D = d.pivot(index="year", columns="age", values="deaths"); E = d.pivot(index="year", columns="age", values="exposure")
    M = (D / E).clip(lower=1e-7)
    Lm = np.log(M.values); a = Lm.mean(axis=0)
    U, s, Vt = np.linalg.svd(Lm - a, full_matrices=False)
    b = Vt[0]; k = U[:, 0] * s[0]; sc = b.sum(); b = b / sc; k = k * sc
    k2 = []
    for i in range(len(M)):
        target = e0_from_mx(M.values[i])
        k2.append(brentq(lambda kk: e0_from_mx(np.exp(a + b * kk)) - target, k[i] - 200, k[i] + 200))
    k = np.array(k2)
    T = len(k); dk = np.diff(k); drift = dk.mean(); sd = dk.std(ddof=1)
    years = np.arange(y1 + 1, h_end + 1); h = np.arange(1, len(years) + 1)
    drift_sim = rng.normal(drift, sd / np.sqrt(T - 1), nsim)
    eps = rng.normal(0, sd, (nsim, len(h))).cumsum(axis=1)
    ks = drift_sim[:, None] * h[None, :] + eps
    base = np.log(M.values[-1])
    e0 = np.empty((nsim, len(h)))
    for i in range(nsim):
        for j in range(len(h)):
            e0[i, j] = e0_from_mx(np.exp(base + b * ks[i, j]))
    return years, e0


def main():
    # 出生数
    fut = np.load(RAW / "f55_bsts_future_annual.npy").T.astype(float)      # (4000, 5) 2026..2030
    mon = np.load(RAW / "f55_bsts_2020_2025_monthly.npy").T.astype(float)  # (4000, 72) 2020-01..2025-12
    past = mon.reshape(mon.shape[0], 6, 12).sum(axis=2)                    # (4000, 6) 2020..2025
    m = pd.read_csv(RAW / "f55_monthly.csv")
    act = m.groupby("year").births.sum()
    # 平均寿命
    long = pd.read_csv(RAW / "f86_mx_long.csv")
    rng = np.random.default_rng(SEED)
    out = {}
    for sex in ["男", "女"]:
        years, e0 = lc_forecast(long, sex, rng)
        out[sex] = e0
    ref = pd.read_csv(RAW / "f86_forecast_e0.csv")
    chk = []
    for sex, key in [("男", "e0_m"), ("女", "e0_f")]:
        r = ref[ref.sex == sex].set_index("year")
        for y in [2045, 2070]:
            j = int(np.where(years == y)[0][0])
            chk.append((sex, y, round(float(np.percentile(out[sex][:, j], 50)), 3), round(float(r.loc[y, "p50"]), 3),
                        round(float(np.percentile(out[sex][:, j], 2.5)), 3), round(float(r.loc[y, "p025"]), 3)))
    print(pd.DataFrame(chk, columns=["sex", "year", "p50_here", "p50_F86", "p025_here", "p025_F86"]))
    np.savez_compressed(DATA / "samples.npz",
                        births_future=fut.astype(np.float32), births_future_years=np.arange(2026, 2031),
                        births_past=past.astype(np.float32), births_past_years=np.arange(2020, 2026),
                        births_actual_years=act.index.values, births_actual=act.values,
                        e0_years=years, e0_m=out["男"].astype(np.float32), e0_f=out["女"].astype(np.float32))
    print("births", fut.shape, past.shape, "e0", out["女"].shape)


if __name__ == "__main__":
    main()
