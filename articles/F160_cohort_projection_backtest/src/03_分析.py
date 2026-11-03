"""F160 自作のコーホート要因法（市区町村）を、基準年・移動率の仮定・子ども女性比の仮定を変えて作り、
2015・2020・2025年の実績と社人研の3つの推計（2013・2018・2023年）と比べる。

配列は (単位, 男女, 年齢19) で持ち、全単位をまとめて計算する。結果は results/ に出す。
"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, NA, F1549, F2044

rng = np.random.default_rng(160)
pop = pd.read_csv(DATA / "pop_units.csv")
surv = pd.read_csv(DATA / "surv_units.csv")
info = pd.read_csv(DATA / "units.csv").set_index("code")
codes = np.array(sorted(info.index))
U = len(codes)
idx = {c: i for i, c in enumerate(codes)}
A = [f"a{i}" for i in range(NA)]
R = [f"r{i}" for i in range(NA - 1)]

POP = {}
for (src, y), g in pop.groupby(["src", "year"]):
    arr = np.zeros((U, 2, NA))
    for sx, j in (("M", 0), ("F", 1)):
        h = g[g.sex == sx].set_index("code").loc[codes, A].to_numpy(float)
        arr[:, j, :] = h
    POP[(src, y)] = arr
SURV = {}
for (v, per), g in surv.groupby(["vintage", "period"]):
    arr = np.zeros((U, 2, NA - 1))
    for sx, j in (("M", 0), ("F", 1)):
        arr[:, j, :] = g[g.sex == sx].set_index("code").loc[codes, R].to_numpy(float)
    SURV[(v, per)] = arr
act = {y: POP[("act", y)] for y in (2010, 2015, 2020, 2025)}
pref = np.array([c // 1000 for c in codes])
prefs = np.unique(pref)
tot = lambda a: a.sum(axis=(1, 2))
base_pop = {y: tot(act[y]) for y in act}


def per(a, b):
    return f"{a}→{b}"


def surv_for(vint, a, b):
    return SURV[(vint, per(a, b))]


# ---------------------------------------------------------------- エンジン（全単位まとめて）
def step(p, s, m, cwr, sr, fidx=F1549):
    q = np.zeros_like(p)
    q[:, :, 1:NA - 1] = p[:, :, :NA - 2] * (s[:, :, :NA - 2] + m[:, :, :NA - 2])
    q[:, :, NA - 1] = (p[:, :, NA - 2] + p[:, :, NA - 1]) * (s[:, :, NA - 2] + m[:, :, NA - 2])
    q = np.clip(q, 0, None)
    b = cwr * q[:, 1, fidx].sum(axis=1)
    q[:, 0, 0] = b * sr / (100 + sr)
    q[:, 1, 0] = b * 100 / (100 + sr)
    return q


def resid(p0, p1, s):
    m = np.zeros(p0.shape[:2] + (NA - 1,))
    with np.errstate(divide="ignore", invalid="ignore"):
        den = p0[:, :, :NA - 2]
        m[:, :, :NA - 2] = np.where(den > 0, p1[:, :, 1:NA - 1] / den - s[:, :, :NA - 2], 0.0)
        d2 = p0[:, :, NA - 2] + p0[:, :, NA - 1]
        m[:, :, NA - 2] = np.where(d2 > 0, p1[:, :, NA - 1] / d2 - s[:, :, NA - 2], 0.0)
    return m


def cwr_obs(p, fidx=F1549):
    f = p[:, 1, fidx].sum(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        c = np.where(f > 0, p[:, :, 0].sum(axis=1) / f, 0.0)
    return c


def agg_pref(x):
    """単位 → 都道府県の合計（同じ形で各単位に戻す）。"""
    out = np.zeros_like(x)
    for k in prefs:
        sel = pref == k
        out[sel] = x[sel].sum(axis=0)
    return out


# 期間ごとの実績の純移動率（市区町村・都道府県）と、そのとき使った生残率
MIG_SURV = {(2010, 2015): "ipss13", (2015, 2020): "ipss18", (2020, 2025): "ipss23"}


def mig_rates(a, b):
    s = surv_for(MIG_SURV[(a, b)], a, b)
    p0, p1 = act[a], act[b]
    m_u = resid(p0, p1, s)
    # 都道府県：人口の合計と、期首人口で加重した生残率から
    P0 = agg_pref(p0); P1 = agg_pref(p1)
    w = np.zeros_like(s)
    w[:, :, :NA - 2] = p0[:, :, :NA - 2]; w[:, :, NA - 2] = p0[:, :, NA - 2] + p0[:, :, NA - 1]
    with np.errstate(divide="ignore", invalid="ignore"):
        S_p = np.where(agg_pref(w) > 0, agg_pref(s * w) / agg_pref(w), s)
    m_p = resid(P0, P1, S_p)
    return m_u, m_p, w


def shrink(m_u, m_p, n, k):
    if k == 0:
        return m_u
    if np.isinf(k):
        return m_p
    wt = n / (n + k)
    return wt * m_u + (1 - wt) * m_p


NATIONAL_SR = None


def own_projection(base, target, mig="last", cwr_mode="last", k=0.0, surv_v=None, fidx=F1549, mig_scale=1.0,
                   start=None, combine_sex=False):
    """自作の推計。base 年の実績から target 年まで5年ずつ進める。"""
    p = act[base].copy() if start is None else start.copy()
    years = list(range(base, target + 1, 5))
    if mig == "zero":
        m = np.zeros(p.shape[:2] + (NA - 1,))
    else:
        mu, mp, n = mig_rates(base - 5, base)
        if mig == "avg2":
            mu2, mp2, n2 = mig_rates(base - 10, base - 5)
            mu, mp, n = (mu + mu2) / 2, (mp + mp2) / 2, (n + n2) / 2
        if combine_sex:
            nn = n.sum(axis=1, keepdims=True)
            with np.errstate(divide="ignore", invalid="ignore"):
                mu = np.where(nn > 0, (mu * n).sum(axis=1, keepdims=True) / nn, 0.0) * np.ones_like(mu)
        m = shrink(mu, mp, n, k) * mig_scale
    c_u = cwr_obs(act[base], fidx)
    if cwr_mode in ("pref", "trend_pref"):
        fw = act[base][:, 1, fidx].sum(axis=1)
        c_p = cwr_obs(agg_pref(act[base]), fidx)
        wt = fw / (fw + 2000.0)
        c = wt * c_u + (1 - wt) * c_p
    else:
        c = c_u
    trend = 1.0
    if cwr_mode in ("trend", "trend_pref"):
        nat0 = act[base - 5].sum(axis=0, keepdims=True); nat1 = act[base].sum(axis=0, keepdims=True)
        trend = float(cwr_obs(nat1, fidx)[0] / cwr_obs(nat0, fidx)[0])
    sr = np.full(U, float(act[base][:, 0, 0].sum() / act[base][:, 1, 0].sum() * 100))
    sv = surv_v or {2015: "ipss18", 2020: "ipss23", 2025: "ipss23"}[base]
    out = {base: p}
    cc = c.copy()
    for a, b in zip(years[:-1], years[1:]):
        if cwr_mode in ("trend", "trend_pref"):
            cc = cc * trend
        p = step(p, surv_for(sv, a, b), m, cc, sr, fidx)
        out[b] = p
    return out


def err_stats(proj, actual, mask=None):
    e = proj / actual - 1
    if mask is not None:
        e = e[mask]
    return dict(n=int(len(e)), mape=float(np.mean(np.abs(e)) * 100), mdape=float(np.median(np.abs(e)) * 100),
                bias=float(np.mean(e) * 100), p90=float(np.quantile(np.abs(e), 0.9) * 100),
                total_err=float(proj[mask].sum() / actual[mask].sum() * 100 - 100) if mask is not None else float(proj.sum() / actual.sum() * 100 - 100))


summary = {"n_units": U, "pop2020": float(base_pop[2020].sum())}
size20 = pd.cut(base_pop[2020], [0, 5000, 20000, 100000, 1e9], labels=["5千人未満", "5千～2万人", "2万～10万人", "10万人以上"])
size15 = pd.cut(base_pop[2015], [0, 5000, 20000, 100000, 1e9], labels=["5千人未満", "5千～2万人", "2万～10万人", "10万人以上"])

# ---------------------------------------------------------------- 1. 移動率の縮め方 k を、2015年基準→2020年で選び、2020年基準→2025年で確かめる
KS = [0, 25, 50, 100, 200, 400, 800, 1600, 3200, 6400, np.inf]
rows = []
for k in KS:
    p1520 = own_projection(2015, 2020, k=k)[2020]
    p2025 = own_projection(2020, 2025, k=k)[2025]
    p1525 = own_projection(2015, 2025, k=k)[2025]
    rows.append(dict(k=("pref" if np.isinf(k) else k),
                     tune_2015_2020=err_stats(tot(p1520), base_pop[2020])["mape"],
                     test_2020_2025=err_stats(tot(p2025), base_pop[2025])["mape"],
                     test_2015_2025=err_stats(tot(p1525), base_pop[2025])["mape"]))
kg = pd.DataFrame(rows)
kg.to_csv(RES / "r1_shrink_grid.csv", index=False)
kbest = KS[int(np.argmin(kg.tune_2015_2020))]
summary["k_best"] = float(kbest)
summary["shrink_grid"] = kg.round(3).to_dict("records")
print(kg.round(3))

# ---------------------------------------------------------------- 2. 基準年×先の年×仮定：自作と社人研の当たり方
cases = [(2015, 2020), (2015, 2025), (2020, 2025)]
ipss_of = {2015: "ipss18", 2020: "ipss23"}
variants = {
    "そのまま（人口が変わらない）": None,
    "移動ゼロ": dict(mig="zero"),
    "直近5年の移動率": dict(mig="last"),
    "直近10年の平均": dict(mig="avg2"),
    "移動率を県へ縮める": dict(mig="last", k=kbest),
    "移動率を半分": dict(mig="last", mig_scale=0.5),
    "縮める＋子ども女性比も県へ": dict(mig="last", k=kbest, cwr_mode="pref"),
    "縮める＋子ども女性比に全国の傾き": dict(mig="last", k=kbest, cwr_mode="trend"),
}
rows, store = [], {}
for b, t in cases:
    actual = base_pop[t]
    for name, kw in variants.items():
        if kw is None:
            proj = base_pop[b]
        else:
            if kw.get("mig") == "avg2" and b == 2015:
                continue
            proj = tot(own_projection(b, t, **kw)[t])
        store[(b, t, name)] = proj
        rows.append(dict(base=b, target=t, horizon=t - b, method=name, **err_stats(proj, actual)))
    ip = tot(POP[(ipss_of[b], t)])
    store[(b, t, "社人研")] = ip
    rows.append(dict(base=b, target=t, horizon=t - b, method="社人研", **err_stats(ip, actual)))
    own = store[(b, t, "移動率を県へ縮める")]
    comb = (own + ip) / 2
    store[(b, t, "自作と社人研の平均")] = comb
    rows.append(dict(base=b, target=t, horizon=t - b, method="自作と社人研の平均", **err_stats(comb, actual)))
# 社人研2013年推計（2010年基準）の5・10・15年先も参考に
for t in (2015, 2020, 2025):
    ip = tot(POP[("ipss13", t)])
    rows.append(dict(base=2010, target=t, horizon=t - 2010, method="社人研", **err_stats(ip, base_pop[t])))
    rows.append(dict(base=2010, target=t, horizon=t - 2010, method="そのまま（人口が変わらない）", **err_stats(base_pop[2010], base_pop[t])))
bt = pd.DataFrame(rows)
bt.to_csv(RES / "r2_backtest_methods.csv", index=False)
print(bt.round(3).to_string())
summary["backtest"] = {f"{r.base}→{r.target}|{r.method}": dict(mape=round(r.mape, 3), mdape=round(r.mdape, 3), bias=round(r.bias, 3),
                                                             p90=round(r.p90, 3), total_err=round(r.total_err, 3)) for r in bt.itertuples()}

# 自作が社人研より当たった市区町村の割合、誤差の相関
cmp = {}
for b, t in cases:
    eo = store[(b, t, "移動率を県へ縮める")] / base_pop[t] - 1
    ei = store[(b, t, "社人研")] / base_pop[t] - 1
    e1 = store[(b, t, "直近5年の移動率")] / base_pop[t] - 1
    cmp[f"{b}→{t}"] = dict(own_better_share=float(np.mean(np.abs(eo) < np.abs(ei))),
                          corr_err=float(np.corrcoef(eo, ei)[0, 1]),
                          raw_better_share=float(np.mean(np.abs(e1) < np.abs(ei))),
                          same_sign_share=float(np.mean(np.sign(eo) == np.sign(ei))))
summary["own_vs_ipss"] = cmp
print(cmp)

# 規模別（2020年基準→2025年、2015年基準→2025年）
rows = []
for (b, t), sz in (((2020, 2025), size20), ((2015, 2025), size15)):
    for name in ["直近5年の移動率", "移動率を県へ縮める", "社人研", "自作と社人研の平均"]:
        e = store[(b, t, name)] / base_pop[t] - 1
        for s in sz.categories:
            sel = np.asarray(sz == s)
            rows.append(dict(base=b, target=t, method=name, size=s, n=int(sel.sum()),
                             mape=float(np.mean(np.abs(e[sel])) * 100), bias=float(np.mean(e[sel]) * 100)))
bs = pd.DataFrame(rows)
bs.to_csv(RES / "r3_by_size.csv", index=False)
summary["by_size"] = bs.round(3).to_dict("records")

# ---------------------------------------------------------------- 3. 外れの出どころ：移動率・子ども女性比を「答え」に差し替える（2020年基準→2025年）
mu_true, _, _ = mig_rates(2020, 2025)
c_true = cwr_obs(act[2025])


def proj_with(m, c):
    sr = np.full(U, float(act[2020][:, 0, 0].sum() / act[2020][:, 1, 0].sum() * 100))
    return step(act[2020], surv_for("ipss23", 2020, 2025), m, c, sr)


mu_k, mp_k, n_k = mig_rates(2015, 2020)
m_own = shrink(mu_k, mp_k, n_k, kbest)
c_own = cwr_obs(act[2020])
rows = []
for name, m, c in (("自作（縮めた移動率・直近の子ども女性比）", m_own, c_own),
                   ("移動率だけ答えに差し替え", mu_true, c_own),
                   ("子ども女性比だけ答えに差し替え", m_own, c_true),
                   ("両方を答えに差し替え", mu_true, c_true)):
    pr = proj_with(m, c)
    e = tot(pr) / base_pop[2025] - 1
    a04 = pr[:, :, 0].sum(1) / act[2025][:, :, 0].sum(1) - 1
    rows.append(dict(case=name, mape=float(np.mean(np.abs(e)) * 100), bias=float(np.mean(e) * 100),
                     mape_age04=float(np.nanmean(np.abs(a04[np.isfinite(a04)])) * 100)))
orc = pd.DataFrame(rows)
orc.to_csv(RES / "r4_oracle.csv", index=False)
summary["oracle"] = orc.round(3).to_dict("records")
print(orc.round(3))

# 年齢別の外れ（2020年基準→2025年）：年齢3区分の人口の外れ
grp = {"0～14歳": range(0, 3), "15～64歳": range(3, 13), "65歳以上": range(13, NA)}
rows = []
own25 = own_projection(2020, 2025, k=kbest)[2025]
ip25 = POP[("ipss23", 2025)]
for nm, pr in (("自作", own25), ("社人研", ip25)):
    for g, ix in grp.items():
        ix = list(ix)
        e = pr[:, :, ix].sum(axis=(1, 2)) / act[2025][:, :, ix].sum(axis=(1, 2)) - 1
        rows.append(dict(method=nm, age=g, mape=float(np.mean(np.abs(e)) * 100), bias=float(np.mean(e) * 100)))
ag = pd.DataFrame(rows)
ag.to_csv(RES / "r5_by_age.csv", index=False)
summary["by_age"] = ag.round(3).to_dict("records")
print(ag.round(3))

# ---------------------------------------------------------------- 4. 2025年を基準にした自作の2050年と、社人研2023年推計（2020年基準）の2050年
ip50 = None
p23 = pd.read_csv(DATA.parent.parent / "F45_population_projection" / "data" / "pop_2023.csv")
p23 = p23[p23.year == 2050]
t50 = p23.groupby("code")[[c for c in p23.columns if c.startswith("a")]].sum().sum(axis=1)
map50 = {}
for c in codes:
    map50[c] = t50.get(c, np.nan)
ip50 = np.array([map50[c] for c in codes], float)
rows = []
out50 = {}
for name, kw in (("直近5年の移動率", dict(mig="last")), ("直近10年の平均", dict(mig="avg2")),
                 ("移動率を県へ縮める", dict(mig="last", k=kbest)), ("移動率を半分", dict(mig="last", mig_scale=0.5)),
                 ("移動ゼロ", dict(mig="zero"))):
    pr = own_projection(2025, 2050, **kw)
    out50[name] = pr
    v = tot(pr[2050])
    r = v / ip50
    ok = np.isfinite(r)
    rows.append(dict(method=name, total2050=float(v[ok].sum()), ipss2050=float(ip50[ok].sum()),
                     total_ratio=float(v[ok].sum() / ip50[ok].sum()),
                     median_ratio=float(np.median(r[ok])), p10=float(np.quantile(r[ok], 0.1)), p90=float(np.quantile(r[ok], 0.9)),
                     within10=float(np.mean(np.abs(r[ok] - 1) <= 0.1)),
                     share_below60_own=float(np.mean(v[ok] / base_pop[2025][ok] < 0.6)),
                     share_below60_ipss=float(np.mean(ip50[ok] / base_pop[2025][ok] < 0.6)),
                     corr_change=float(np.corrcoef(np.log(v[ok] / base_pop[2025][ok]), np.log(ip50[ok] / base_pop[2025][ok]))[0, 1])))
o50 = pd.DataFrame(rows)
o50.to_csv(RES / "r6_outlook_2050.csv", index=False)
summary["outlook2050"] = o50.round(4).to_dict("records")
summary["pop2025_units"] = float(base_pop[2025].sum())
print(o50.round(4).to_string())
# 図用：単位ごとの2050年
pd.DataFrame(dict(code=codes, pop2025=base_pop[2025], ipss2050=ip50,
                  own_shrink2050=tot(out50["移動率を県へ縮める"][2050]),
                  own_last2050=tot(out50["直近5年の移動率"][2050]),
                  own_avg2050=tot(out50["直近10年の平均"][2050]))).to_csv(RES / "r6_units_2050.csv", index=False)

# 2020年基準の誤差（単位別）を保存（図用）
pd.DataFrame(dict(code=codes, pop2020=base_pop[2020], act2025=base_pop[2025],
                  own=store[(2020, 2025, "移動率を県へ縮める")], raw=store[(2020, 2025, "直近5年の移動率")],
                  ipss=store[(2020, 2025, "社人研")],
                  own1525=store[(2015, 2025, "移動率を県へ縮める")], ipss1525=store[(2015, 2025, "社人研")],
                  pop2015=base_pop[2015])).to_csv(RES / "r2_units_2025.csv", index=False)

# ---------------------------------------------------------------- 5. 頑健性
rows = []


def rob(label, b, t, **kw):
    pr = tot(own_projection(b, t, **kw)[t])
    st = err_stats(pr, base_pop[t])
    ip = err_stats(tot(POP[(ipss_of[b], t)]), base_pop[t])
    rows.append(dict(check=label, base=b, target=t, mape=st["mape"], bias=st["bias"], ipss_mape=ip["mape"],
                     diff_vs_ipss=st["mape"] - ip["mape"]))


for b, t in cases:
    rob("基本（縮めた移動率）", b, t, k=kbest)
    rob("生残率を1つ前の推計のものに", b, t, k=kbest, surv_v={2015: "ipss13", 2020: "ipss18"}[b])
    rob("子ども女性比の分母を女性20～44歳に", b, t, k=kbest, fidx=F2044)
    rob("移動率を男女まとめて", b, t, k=kbest, combine_sex=True)
    rob("縮め方を2倍（k×2）", b, t, k=kbest * 2)
    rob("縮め方を半分（k÷2）", b, t, k=kbest / 2)
rb = pd.DataFrame(rows)
# 小さい町を除く
for b, t in cases:
    sz = base_pop[b] >= 1000
    pr = tot(own_projection(b, t, k=kbest)[t])
    ip = tot(POP[(ipss_of[b], t)])
    st = err_stats(pr, base_pop[t], sz); si = err_stats(ip, base_pop[t], sz)
    rb = pd.concat([rb, pd.DataFrame([dict(check="人口1千人未満を除く", base=b, target=t, mape=st["mape"], bias=st["bias"],
                                          ipss_mape=si["mape"], diff_vs_ipss=st["mape"] - si["mape"])])])
# ブートストラップ：自作−社人研の MAPE の差の区間（単位を引き直す）
boot = {}
for b, t in cases:
    eo = np.abs(store[(b, t, "移動率を県へ縮める")] / base_pop[t] - 1)
    ei = np.abs(store[(b, t, "社人研")] / base_pop[t] - 1)
    er = np.abs(store[(b, t, "直近5年の移動率")] / base_pop[t] - 1)
    ec = np.abs(store[(b, t, "自作と社人研の平均")] / base_pop[t] - 1)
    B = []
    for _ in range(2000):
        ii = rng.integers(0, U, U)
        B.append([(eo[ii].mean() - ei[ii].mean()) * 100, (er[ii].mean() - ei[ii].mean()) * 100, (ec[ii].mean() - ei[ii].mean()) * 100])
    B = np.array(B)
    boot[f"{b}→{t}"] = dict(shrink_minus_ipss=[float(np.mean(B[:, 0])), *map(float, np.quantile(B[:, 0], [0.025, 0.975]))],
                            raw_minus_ipss=[float(np.mean(B[:, 1])), *map(float, np.quantile(B[:, 1], [0.025, 0.975]))],
                            combo_minus_ipss=[float(np.mean(B[:, 2])), *map(float, np.quantile(B[:, 2], [0.025, 0.975]))])
summary["boot"] = boot
rb.to_csv(RES / "r7_robustness.csv", index=False)
summary["robustness"] = rb.round(3).to_dict("records")
print(rb.round(3).to_string())
print(json.dumps(boot, ensure_ascii=False, indent=1))
json.dump(summary, open(RES / "summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
