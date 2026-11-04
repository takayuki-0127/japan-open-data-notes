"""03 分析：子どもの平均身長の伸びは、いつ止まったのか（変化点）

主の方法（M1）：折れ線（連続な2本の直線、hinge）を年齢×性ごとに当てはめ、
  残差平方和が最小になる折れ目の年を「伸びが変わった年」とする。
  期間は1948〜2019年度（2020〜2023年度はコロナで測定時期がずれたので除く）。
  折れ目の95%区間は、残差の移動ブロック・ブートストラップ（ブロック長5、999回）。
別の方法：
  M1b：折れ目のあとは傾き0（伸びて、ある年から止まる）とする折れ線
  M2 ：毎年の伸び（前年差）の平均が1回だけ変わる点（ruptures Binseg, l2）
  M3 ：5年移動平均が、その年齢の最高値−0.3cm に初めて届いた年
  M4 ：折れ目2つの折れ線の、あとの折れ目
時代か世代か：
  折れ目の年（M1）を年齢で回帰する。時代（その年に全年齢で止まる）なら傾き0、
  世代（ある生まれ年から止まる）なら傾き+1になる。
"""
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
import ruptures as rpt

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
RES.mkdir(exist_ok=True)
rng = np.random.default_rng(187)

d = pd.read_csv(RES / "height_panel.csv")
AGES = list(range(5, 18))
SEXES = ["M", "F"]
GRID_MIN, GRID_MAX = 1953, 2014   # 折れ目の候補（両端5年は残す）
B = 999
BLOCK = 5


def series(sex, age, y0=1948, y1=2019, drop_covid=True):
    s = d[(d.sex == sex) & (d.age == age) & (d.year >= y0) & (d.year <= y1)]
    if drop_covid:
        s = s[s.flag_covid == 0]
    return s.year.to_numpy(float), s.height.to_numpy(float)


def hinge_design(x, b, plateau=False):
    if plateau:
        return np.column_stack([np.ones_like(x), np.minimum(x, b)])
    return np.column_stack([np.ones_like(x), x - 1948, np.maximum(x - b, 0)])


def resid_maker(x, grid, plateau=False):
    """各折れ目候補の残差化行列 M_b = I - P_b を作る"""
    Ms = []
    for b in grid:
        X = hinge_design(x, b, plateau)
        P = X @ np.linalg.pinv(X)
        Ms.append(np.eye(len(x)) - P)
    return np.stack(Ms)


def hinge_fit(x, y, plateau=False, grid=None):
    grid = np.arange(GRID_MIN, GRID_MAX + 1) if grid is None else grid
    Ms = resid_maker(x, grid, plateau)
    sse = np.einsum("i,bij,j->b", y, Ms, y)
    k = int(np.argmin(sse))
    b = grid[k]
    X = hinge_design(x, b, plateau)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    fit = X @ coef
    if plateau:
        s1, s2 = coef[1], 0.0
    else:
        s1, s2 = coef[1], coef[1] + coef[2]
    return dict(b=int(b), s1=s1 * 10, s2=s2 * 10, sse=sse[k], fit=fit,
                Ms=Ms, grid=grid)


def block_boot_breaks(x, y, fitres, plateau=False):
    """残差の移動ブロック・ブートストラップで折れ目の分布を作る"""
    e = y - fitres["fit"]
    n = len(e)
    nb = int(np.ceil(n / BLOCK))
    starts = rng.integers(0, n - BLOCK + 1, size=(B, nb))
    idx = (starts[:, :, None] + np.arange(BLOCK)[None, None, :]).reshape(B, -1)[:, :n]
    Y = fitres["fit"][None, :] + e[idx]
    Ms = fitres["Ms"]
    sse = np.einsum("ri,bij,rj->rb", Y, Ms, Y)
    return fitres["grid"][np.argmin(sse, axis=1)]


def m2_mean_shift(x, y):
    """毎年の伸び（前年差）の平均が1回変わる点。隣り合う年度だけで差をとる"""
    xs, ys = x[1:], np.diff(y)
    ok = np.diff(x) == 1
    xs, ys = xs[ok], ys[ok]
    algo = rpt.Binseg(model="l2", min_size=5).fit(ys.reshape(-1, 1))
    bk = algo.predict(n_bkps=1)[0]
    return int(xs[bk]) if bk < len(xs) else np.nan, ys[:bk].mean() * 10, ys[bk:].mean() * 10


def m3_threshold(x, y, tol=0.3):
    s = pd.Series(y, index=x.astype(int)).reindex(range(int(x.min()), int(x.max()) + 1))
    ma = s.rolling(5, center=True, min_periods=3).mean()
    top = ma.max()
    hit = ma[ma >= top - tol]
    return int(hit.index.min()) if len(hit) else np.nan


def m4_two_breaks(x, y, gap=8):
    best = (np.inf, None, None)
    for b1 in range(GRID_MIN, GRID_MAX + 1):
        for b2 in range(b1 + gap, GRID_MAX + 1):
            X = np.column_stack([np.ones_like(x), x - 1948, np.maximum(x - b1, 0), np.maximum(x - b2, 0)])
            coef, *_ = np.linalg.lstsq(X, y, rcond=None)
            sse = ((y - X @ coef) ** 2).sum()
            if sse < best[0]:
                best = (sse, b1, b2, coef)
    _, b1, b2, coef = best
    s3 = (coef[1] + coef[2] + coef[3]) * 10
    return b1, b2, s3


# ---------- 1. 年齢×性ごとの変化点 ----------
rows, boot_store = [], {}
for sex in SEXES:
    for age in AGES:
        x, y = series(sex, age)
        f1 = hinge_fit(x, y)
        bb = block_boot_breaks(x, y, f1)
        boot_store[(sex, age)] = bb
        f1b = hinge_fit(x, y, plateau=True)
        m2b, m2pre, m2post = m2_mean_shift(x, y)
        m3b = m3_threshold(x, y)
        b41, b42, s43 = m4_two_breaks(x, y)
        mx = d[(d.sex == sex) & (d.age == age) & (d.year <= 2019) & (d.year >= 1948)]
        peak = mx.loc[mx.height.idxmax()]
        rows.append(dict(sex=sex, age=age,
                         M1_break=f1["b"], M1_lo=int(np.percentile(bb, 2.5)), M1_hi=int(np.percentile(bb, 97.5)),
                         M1_slope_before_cm10y=round(f1["s1"], 2), M1_slope_after_cm10y=round(f1["s2"], 2),
                         M1b_plateau_break=f1b["b"], M2_meanshift=m2b,
                         M2_gain_before_cm10y=round(m2pre, 2), M2_gain_after_cm10y=round(m2post, 2),
                         M3_reach_max=m3b, M4_break1=b41, M4_break2=b42, M4_slope_last_cm10y=round(s43, 2),
                         peak_year=int(peak.year), peak_height=peak.height,
                         h1948=float(mx[mx.year == 1948].height.iloc[0]),
                         h2019=float(mx[mx.year == 2019].height.iloc[0])))
br = pd.DataFrame(rows)
br["M1_cohort"] = br["M1_break"] - br["age"]
br.to_csv(RES / "breaks_by_age.csv", index=False)
print(br[["sex", "age", "M1_break", "M1_lo", "M1_hi", "M1_slope_before_cm10y", "M1_slope_after_cm10y",
          "M1b_plateau_break", "M2_meanshift", "M3_reach_max", "M4_break2", "peak_year"]].to_string())

# ---------- 2. 時代か世代か：折れ目の年を年齢で回帰 ----------
pc_rows = []
for sex in SEXES:
    for lo_age in (5, 11):   # 全年齢と、思春期以降（11〜17歳）
        ages = [a for a in AGES if a >= lo_age]
        sub = br[(br.sex == sex) & (br.age.isin(ages))]
        slope = np.polyfit(sub.age, sub.M1_break, 1)[0]
        bs = np.array([[boot_store[(sex, a)][r] for a in ages] for r in range(B)])
        boot_slopes = np.array([np.polyfit(ages, bs[r], 1)[0] for r in range(B)])
        for meth in ["M1_break", "M1b_plateau_break", "M2_meanshift", "M3_reach_max", "M4_break2"]:
            ss = sub.dropna(subset=[meth])
            sl = np.polyfit(ss.age, ss[meth], 1)[0]
            pc_rows.append(dict(sex=sex, ages=f"{ages[0]}-{ages[-1]}", method=meth, slope=round(sl, 2),
                                lo=round(np.percentile(boot_slopes, 2.5), 2) if meth == "M1_break" else np.nan,
                                hi=round(np.percentile(boot_slopes, 97.5), 2) if meth == "M1_break" else np.nan))
pc = pd.DataFrame(pc_rows)
pc.to_csv(RES / "period_vs_cohort.csv", index=False)
print(pc.to_string())

# ---------- 3. 止まってからの傾き（1994〜2019年度, HAC）と2024・2025年度 ----------
post = []
for sex in SEXES:
    for age in AGES:
        x, y = series(sex, age, 1994, 2019)
        X = sm.add_constant(x - 1994)
        r = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
        late = d[(d.sex == sex) & (d.age == age) & (d.year.isin([2024, 2025]))].height.mean()
        pre = d[(d.sex == sex) & (d.age == age) & (d.year.between(2015, 2019))].height.mean()
        post.append(dict(sex=sex, age=age, slope_cm10y=round(r.params[1] * 10, 3),
                         lo=round((r.params[1] - 1.96 * r.bse[1]) * 10, 3),
                         hi=round((r.params[1] + 1.96 * r.bse[1]) * 10, 3), p=round(r.pvalues[1], 4),
                         mean_2015_19=round(pre, 2), mean_2024_25=round(late, 2),
                         diff_2024_25=round(late - pre, 2)))
post = pd.DataFrame(post)
post.to_csv(RES / "post_plateau_slope.csv", index=False)
print(post.to_string())

# ---------- 4. 世代でみる：11歳と17歳の身長、その差 ----------
w = d[(d.year >= 1948) & (d.flag_covid == 0)].pivot_table(index=["sex", "cohort"], columns="age", values="height")
coh = w[[11, 13, 14, 17]].dropna().reset_index()
coh["gain_11_17"] = coh[17] - coh[11]
coh.to_csv(RES / "cohort_heights.csv", index=False)
crow = []
for sex in SEXES:
    c = coh[coh.sex == sex]
    x = c.cohort.to_numpy(float)
    for col in [17, 11, "gain_11_17"]:
        y = c[col].to_numpy(float)
        grid = np.arange(int(x.min()) + 5, int(x.max()) - 4)
        Ms = resid_maker(x, grid)
        sse = np.einsum("i,bij,j->b", y, Ms, y)
        bc = grid[np.argmin(sse)]
        top = c.loc[c[col].idxmax()]
        crow.append(dict(sex=sex, series=str(col), cohort_break=int(bc), max_cohort=int(top.cohort),
                         max_value=round(top[col], 2),
                         first=round(c[col].iloc[0], 2), last=round(c[col].iloc[-1], 2),
                         first_cohort=int(c.cohort.iloc[0]), last_cohort=int(c.cohort.iloc[-1])))
cb = pd.DataFrame(crow)
cb.to_csv(RES / "cohort_breaks.csv", index=False)
print(cb.to_string())

# ---------- 5. 頑健性：期間・方法・年齢（17・13・11歳） ----------
rob = []
windows = {"1948-2019（主）": (1948, 2019, True), "1955-2019": (1955, 2019, True),
           "1960-2019": (1960, 2019, True), "1948-2025（コロナ期を除く）": (1948, 2025, True),
           "1948-2025（コロナ期を含む）": (1948, 2025, False), "1948-2009": (1948, 2009, True)}
for sex in SEXES:
    for age in [11, 13, 14, 17]:
        for wn, (a, b_, dc) in windows.items():
            x, y = series(sex, age, a, b_, dc)
            g = np.arange(max(GRID_MIN, a + 5), min(GRID_MAX, b_ - 5) + 1)
            f1 = hinge_fit(x, y, grid=g)
            f1b = hinge_fit(x, y, plateau=True, grid=g)
            rob.append(dict(sex=sex, age=age, window=wn, M1=f1["b"], M1b=f1b["b"],
                            M2=m2_mean_shift(x, y)[0], M3=m3_threshold(x, y),
                            slope_after=round(f1["s2"], 2)))
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness_windows.csv", index=False)
print(rob.to_string())

# ---------- 6. 戦前との比較（17歳・11歳の10年あたりの伸び） ----------
dec = []
for sex in SEXES:
    for age in [11, 17]:
        s = d[(d.sex == sex) & (d.age == age)].set_index("year").height
        for (a, b_) in [(1900, 1939), (1948, 1970), (1970, 1994), (1994, 2019)]:
            ss = s.loc[a:b_]
            sl = np.polyfit(ss.index, ss.values, 1)[0] * 10
            dec.append(dict(sex=sex, age=age, period=f"{a}-{b_}", gain_cm10y=round(sl, 2)))
dec = pd.DataFrame(dec)
dec.to_csv(RES / "gain_by_era.csv", index=False)
print(dec.to_string())

# ---------- 7. 擬似データでの確認：方法ごとの外れ方 ----------
# 1948〜2019年、1985年までは年0.1cm伸び、そのあと0。ノイズは実データの残差の大きさ（17歳男子）。
x, y = series("M", 17)
f = hinge_fit(x, y)
sd = np.std(y - f["fit"], ddof=3)
sim = []
for true_b in [1975, 1985, 1995]:
    for r in range(300):
        yy = 160 + 0.1 * (np.minimum(x, true_b) - 1948) + rng.normal(0, sd, len(x))
        sim.append(dict(true=true_b, M1=hinge_fit(x, yy)["b"], M1b=hinge_fit(x, yy, plateau=True)["b"],
                        M2=m2_mean_shift(x, yy)[0], M3=m3_threshold(x, yy)))
sim = pd.DataFrame(sim)
simsum = sim.groupby("true").agg(
    **{f"{m}_med": (m, "median") for m in ["M1", "M1b", "M2", "M3"]},
    **{f"{m}_q10": (m, lambda v: np.nanpercentile(v, 10)) for m in ["M1", "M1b", "M2", "M3"]},
    **{f"{m}_q90": (m, lambda v: np.nanpercentile(v, 90)) for m in ["M1", "M1b", "M2", "M3"]}).round(1)
simsum["resid_sd_cm"] = round(sd, 3)
simsum.to_csv(RES / "simulation_methods.csv")
print(simsum.T.to_string())
