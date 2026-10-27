"""F45 コーホート要因法：社人研の再現・自作の素朴な推計・過去の推計の当たり方・シナリオ・頑健性。

結果は results/ に CSV と summary.json で出す。
"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, F2044, F1549, project

YEARS23 = [2020, 2025, 2030, 2035, 2040, 2045, 2050]


def per(a, b):
    return f"{a}→{b}"


def load(v, nage):
    p = pd.read_csv(DATA / f"pop_{v}.csv")
    A = [f"a{i}" for i in range(nage)]
    P = {}
    for r in p.itertuples(index=False):
        P.setdefault(r.code, {})[(r.year, r.sex)] = np.array([getattr(r, a) for a in A], float)
    info = p.drop_duplicates("code").set_index("code")[["kind", "pref", "muni"]]
    S = M = C = None
    sv = "2013_pref" if v == "2013_pref" else v
    if (DATA / f"surv_{sv}.csv").exists():
        R = [f"r{i}" for i in range(nage - 1)]
        S, M, C = {}, {}, {}
        for name, D in (("surv", S), ("nmig", M)):
            q = pd.read_csv(DATA / f"{name}_{sv}.csv")
            for r in q.itertuples(index=False):
                D.setdefault(r.code, {})[(r.period, r.sex)] = np.array([getattr(r, x) for x in R], float)
        c = pd.read_csv(DATA / f"cwr_{sv}.csv")
        for r in c.itertuples(index=False):
            C.setdefault(r.code, {})[r.year] = (r.cwr, r.sr)
    return dict(P=P, S=S, M=M, C=C, info=info)


def total(mf):
    return float(mf[0].sum() + mf[1].sum())


def c19(a):
    """20区分（95歳～）を19区分（90歳以上）にまとめる。"""
    a = np.asarray(a, float)
    return np.concatenate([a[:18], [a[18] + a[19]]])


def c19_rate(rate, pop_start):
    """20区分用の率（長さ19）を19区分用（長さ18）にする。最後は 85～89歳と90歳以上の人口で加重平均。"""
    w = np.array([pop_start[17], pop_start[18] + pop_start[19]], float)
    last = (rate[17] * w[0] + rate[18] * w[1]) / w.sum() if w.sum() > 0 else rate[17]
    return np.concatenate([rate[:17], [last]])


def ipss_steps(d, code, years, fidx_unused=None):
    st = []
    for a, b in zip(years[:-1], years[1:]):
        k = per(f"{a}年", f"{b}年") if (per(f"{a}年", f"{b}年"), "M") in d["S"][code] else per(a, b)
        st.append((d["S"][code][(k, "M")], d["S"][code][(k, "F")],
                   d["M"][code][(k, "M")], d["M"][code][(k, "F")], *d["C"][code][b]))
    return st


def norm_period_keys(d):
    """期間のキーを "2020→2025" にそろえる。"""
    for D in (d["S"], d["M"]):
        for code in D:
            D[code] = {(k.replace("年", ""), s): v for (k, s), v in D[code].items()}


summary = {}

# ---------------------------------------------------------------- 読み込み
d23 = load("2023", 20); norm_period_keys(d23)
d18 = load("2018", 19); norm_period_keys(d18)
d13 = load("2013_pref", 19); norm_period_keys(d13)
c25 = load("census2025", 20)


def steps_from(d, code, years):
    st = []
    for a, b in zip(years[:-1], years[1:]):
        k = per(a, b)
        st.append((d["S"][code][(k, "M")], d["S"][code][(k, "F")],
                   d["M"][code][(k, "M")], d["M"][code][(k, "F")], *d["C"][code][b]))
    return st


# ---------------------------------------------------------------- 1. 社人研の推計を再現する
rows = []
for v, d, years, fidx in (("2023", d23, YEARS23, F2044),
                          ("2018", d18, [2015, 2020, 2025, 2030, 2035, 2040, 2045], F1549),
                          ("2013", d13, [2010, 2015, 2020, 2025, 2030, 2035, 2040], F1549)):
    for code in d["S"]:
        if code not in d["P"] or (years[0], "M") not in d["P"][code]:
            continue
        try:
            res = project(d["P"][code][(years[0], "M")], d["P"][code][(years[0], "F")],
                          steps_from(d, code, years), fidx=fidx)
        except KeyError:
            continue
        pub = d["P"][code][(years[-1], "M")] + d["P"][code][(years[-1], "F")]
        mine = res[-1][0] + res[-1][1]
        rows.append(dict(vintage=v, code=code, kind=d["info"].loc[code, "kind"], pub=pub.sum(), mine=mine.sum(),
                         pct=mine.sum() / pub.sum() - 1, max_age_abs=np.abs(mine - pub).max()))
rep = pd.DataFrame(rows)
rep.to_csv(RES / "r1_reproduce.csv", index=False)
rep = rep[rep.pct.notna()]
summary["reproduce"] = rep.groupby("vintage").agg(
    n=("code", "size"), median_abs_pct=("pct", lambda x: float(np.abs(x).median() * 100)),
    share_within_01pct=("pct", lambda x: float((np.abs(x) <= 0.001).mean())),
    max_abs_pct=("pct", lambda x: float(np.abs(x).max() * 100)),
    max_abs_pct_pop10k=("pct", lambda x: float(np.abs(x[rep.loc[x.index, "pub"] >= 10000]).max() * 100)),
    max_age_abs=("max_age_abs", "max")).round(5).to_dict("index")

# ---------------------------------------------------------------- 共通の市区町村の単位
# 2018年推計で区に分かれていない政令市は市全体、福島県は2018年推計に市町村の値がないので除く、那珂川町→那珂川市
info18 = d18["info"]; info23 = d23["info"]
ward_prefix18 = {c // 10 for c, r in info18.iterrows() if r.kind == "0"}
units = []
for c, r in info18.iterrows():
    if c // 1000 == 7:
        continue
    if r.kind in ("0", "2", "3"):
        units.append((c, 40231 if c == 40305 else c))
    elif r.kind == "1" and (c // 10) not in ward_prefix18:
        units.append((c, c))
units = pd.DataFrame(units, columns=["code18", "code23"])
units = units[units.code23.isin(info23.index)]
units["kind"] = units.code18.map(info18.kind)
units["pref"] = units.code23.map(info23.pref)
units["muni"] = units.code23.map(info23.muni)
summary["n_units"] = int(len(units))


# ---------------------------------------------------------------- 2. 自作の素朴な推計（2015→20年の動きが続くと仮定）
def naive_rates(p0m, p0f, p1m, p1f, sm, sf):
    """期首・期末の人口（19区分）と生残率（18）から、純移動率（18）を残差で出す。"""
    out = []
    for p0, p1, s in ((p0m, p1m, sm), (p0f, p1f, sf)):
        m = np.zeros(18)
        den = p0[0:17]
        with np.errstate(divide="ignore", invalid="ignore"):
            m[:17] = np.where(den > 0, p1[1:18] / den - s[:17], 0.0)
            d2 = p0[17] + p0[18]
            m[17] = p1[18] / d2 - s[17] if d2 > 0 else 0.0
        out.append(m)
    return out


def ipss19_surv(code, years=YEARS23):
    """社人研2023年推計の生残率を19区分に直したもの（期首人口は社人研の推計値で加重）。"""
    st = []
    for a, b in zip(years[:-1], years[1:]):
        k = per(a, b)
        pm = d23["P"][code][(a, "M")]; pf = d23["P"][code][(a, "F")]
        st.append((c19_rate(d23["S"][code][(k, "M")], pm), c19_rate(d23["S"][code][(k, "F")], pf)))
    return st


def cwr_obs(pm, pf):
    f = pf[F2044].sum()
    return ((pm[0] + pf[0]) / f if f > 0 else 0.0), (pm[0] / pf[0] * 100 if pf[0] > 0 else 105.0)


def naive_project(code23, p15m, p15f, s1520m, s1520f, mig_scale=1.0, combine_sex=False, years=YEARS23):
    p20m = c19(d23["P"][code23][(2020, "M")]); p20f = c19(d23["P"][code23][(2020, "F")])
    mm, mf = naive_rates(p15m, p15f, p20m, p20f, s1520m, s1520f)
    if combine_sex:
        with np.errstate(divide="ignore", invalid="ignore"):
            tot0 = p15m[:17] + p15f[:17]
            mc = np.where(tot0 > 0, ((p20m[1:18] + p20f[1:18]) - (p15m[:17] * s1520m[:17] + p15f[:17] * s1520f[:17])) / tot0, 0)
        mm = mm.copy(); mf = mf.copy(); mm[:17] = mc; mf[:17] = mc
    cw, sr = cwr_obs(p20m, p20f)
    surv = ipss19_surv(code23, years)
    steps = [(sm, sf, mm * mig_scale, mf * mig_scale, cw, sr) for sm, sf in surv]
    return project(p20m, p20f, steps, fidx=F2044)


rows = []
for u in units.itertuples(index=False):
    try:
        p15m = d18["P"][u.code18][(2015, "M")]; p15f = d18["P"][u.code18][(2015, "F")]
        s1520 = (d18["S"][u.code18][("2015→2020", "M")], d18["S"][u.code18][("2015→2020", "F")])
        res = naive_project(u.code23, p15m, p15f, *s1520)
    except KeyError:
        continue
    p20 = total((d23["P"][u.code23][(2020, "M")], d23["P"][u.code23][(2020, "F")]))
    ip = {y: total((d23["P"][u.code23][(y, "M")], d23["P"][u.code23][(y, "F")])) for y in YEARS23}
    rows.append(dict(code=u.code23, kind=u.kind, pref=u.pref, muni=u.muni, pop2015=float(p15m.sum() + p15f.sum()),
                     pop2020=p20, ipss2025=ip[2025], ipss2050=ip[2050],
                     naive2025=total(res[1]), naive2050=total(res[-1])))
nv = pd.DataFrame(rows)
nv["ipss_ratio"] = nv.ipss2050 / nv.pop2020
nv["naive_ratio"] = nv.naive2050 / nv.pop2020
nv["naive_over_ipss"] = nv.naive2050 / nv.ipss2050
nv.to_csv(RES / "r2_naive_vs_ipss_muni.csv", index=False)
summary["naive_vs_ipss_muni"] = dict(
    n=int(len(nv)),
    corr_ratio=float(np.corrcoef(np.log(nv.ipss_ratio), np.log(nv.naive_ratio))[0, 1]),
    median_naive_over_ipss=float(nv.naive_over_ipss.median()),
    p10=float(nv.naive_over_ipss.quantile(0.1)), p90=float(nv.naive_over_ipss.quantile(0.9)),
    share_within_10pct=float((np.abs(nv.naive_over_ipss - 1) <= 0.1).mean()),
    share_half_ipss=float((nv.ipss_ratio < 0.5).mean()), share_half_naive=float((nv.naive_ratio < 0.5).mean()),
    sum_ipss2050=float(nv.ipss2050.sum()), sum_naive2050=float(nv.naive2050.sum()), sum_2020=float(nv.pop2020.sum()))
by_size = nv.assign(size=pd.cut(nv.pop2020, [0, 5000, 20000, 100000, 1e8], labels=["5千人未満", "5千～2万人", "2万～10万人", "10万人以上"]))
summary["naive_vs_ipss_by_size"] = by_size.groupby("size", observed=True).agg(
    n=("code", "size"), ipss=("ipss_ratio", "median"), naive=("naive_ratio", "median"),
    ratio=("naive_over_ipss", "median")).round(4).to_dict("index")

# 都道府県
prow = []
for code in [c for c, r in d23["info"].iterrows() if r.kind == "a"]:
    p15m = d18["P"][code][(2015, "M")]; p15f = d18["P"][code][(2015, "F")]
    s1520 = (d18["S"][code][("2015→2020", "M")], d18["S"][code][("2015→2020", "F")])
    res = naive_project(code, p15m, p15f, *s1520)
    prow.append(dict(code=code, pref=d23["info"].loc[code, "pref"],
                     pop2020=total((d23["P"][code][(2020, "M")], d23["P"][code][(2020, "F")])),
                     ipss2050=total((d23["P"][code][(2050, "M")], d23["P"][code][(2050, "F")])),
                     naive2050=total(res[-1])))
nvp = pd.DataFrame(prow)
nvp.to_csv(RES / "r2_naive_vs_ipss_pref.csv", index=False)
summary["naive_vs_ipss_pref"] = dict(ipss2050=float(nvp.ipss2050.sum()), naive2050=float(nvp.naive2050.sum()),
                                     pop2020=float(nvp.pop2020.sum()))

# ---------------------------------------------------------------- 3. 過去の推計の当たり方
# 3a. 令和7年国勢調査（2025年）で答え合わせ：社人研2023年推計と自作の素朴な推計
act = {}
for c, r in c25["info"].iterrows():
    if (2025, "M") in c25["P"][c]:
        act[c] = total((c25["P"][c][(2025, "M")], c25["P"][c][(2025, "F")]))
# 浜松市は2024年に区を再編したので市全体（22130）で、浜通り地域（7999）は13市町村の合計で比べる
hamadori = [7204, 7209, 7212, 7541, 7542, 7543, 7544, 7545, 7546, 7547, 7548, 7561, 7564]
act[7999] = sum(act.get(c, np.nan) for c in hamadori)
bt = nv[["code", "kind", "pref", "muni", "pop2015", "pop2020", "ipss2025", "naive2025"]].copy()
bt["act2025"] = bt.code.map(act)
# 福島県など、2018年推計に市町村の値がない単位も社人研2023年推計だけで比べる
extra = []
for c, r in d23["info"].iterrows():
    if r.kind in ("0", "2", "3", "9") and c not in set(bt.code) and c // 1000 != 22:
        extra.append(dict(code=c, kind=r.kind, pref=r.pref, muni=r.muni, pop2015=np.nan,
                          pop2020=total((d23["P"][c][(2020, "M")], d23["P"][c][(2020, "F")])),
                          ipss2025=total((d23["P"][c][(2025, "M")], d23["P"][c][(2025, "F")])), naive2025=np.nan,
                          act2025=act.get(c, np.nan)))
bt = pd.concat([bt, pd.DataFrame(extra)], ignore_index=True)
bt = bt[bt.act2025.notna() & (bt.act2025 > 0)]
bt["err_ipss"] = bt.ipss2025 / bt.act2025 - 1
bt["err_naive"] = bt.naive2025 / bt.act2025 - 1
bt["err_flat"] = bt.pop2020 / bt.act2025 - 1          # 「2020年のまま」という一番単純な予測
bt["chg_actual"] = bt.act2025 / bt.pop2020 - 1
bt["size"] = pd.cut(bt.pop2020, [0, 5000, 20000, 100000, 1e8], labels=["5千人未満", "5千～2万人", "2万～10万人", "10万人以上"])
bt.to_csv(RES / "r3_backtest_2025_muni.csv", index=False)
both = bt[bt.err_naive.notna()]


def err_stats(e):
    e = e.dropna()
    return dict(n=int(len(e)), mape=float(np.abs(e).mean() * 100), mdape=float(np.abs(e).median() * 100),
                bias=float(e.mean() * 100), p90=float(np.abs(e).quantile(0.9) * 100))


summary["bt2025"] = dict(ipss_all=err_stats(bt.err_ipss), ipss_common=err_stats(both.err_ipss),
                         naive_common=err_stats(both.err_naive), flat_common=err_stats(both.err_flat),
                         naive_better_share=float((np.abs(both.err_naive) < np.abs(both.err_ipss)).mean()))
summary["bt2025_by_size"] = {str(k): dict(ipss=err_stats(g.err_ipss), naive=err_stats(g.err_naive), n=int(len(g)))
                             for k, g in both.groupby("size", observed=True)}
# 全国・都道府県の合計
pa = {c: act[c] for c in act if c in d23["info"].index and d23["info"].loc[c, "kind"] == "a"}
summary["bt2025_japan"] = dict(actual=float(sum(pa.values())),
                               ipss=float(sum(total((d23["P"][c][(2025, "M")], d23["P"][c][(2025, "F")])) for c in pa)),
                               naive_pref=float(sum(total(naive_project(c, d18["P"][c][(2015, "M")], d18["P"][c][(2015, "F")],
                                                                        d18["S"][c][("2015→2020", "M")], d18["S"][c][("2015→2020", "F")])[1])
                                                    for c in pa)))
# 年齢別（全国）の当たり方：社人研2023年推計
age_ip = sum(d23["P"][c][(2025, "M")] + d23["P"][c][(2025, "F")] for c in pa)
age_ac = sum(c25["P"][c][(2025, "M")] + c25["P"][c][(2025, "F")] for c in pa)
summary["bt2025_age_ipss_pct"] = {i: round(float(age_ip[i] / age_ac[i] - 1) * 100, 2) for i in range(20)}

# 3b. 10年前の推計：社人研2013年推計（2010年基準）の2020年・2025年を実績と比べる（都道府県）
rows = []
for c in d13["P"]:
    for y, src in ((2015, d18), (2020, d23), (2025, c25)):
        pr = total((d13["P"][c][(y, "M")], d13["P"][c][(y, "F")]))
        if y == 2025:
            ac = act.get(c, np.nan)
        else:
            ac = total((src["P"][c][(y, "M")], src["P"][c][(y, "F")]))
        rows.append(dict(vintage="2013年推計", horizon=y - 2010, year=y, code=c, proj=pr, act=ac))
for c in [k for k, r in d18["info"].iterrows() if r.kind == "a"]:
    for y, src in ((2020, d23), (2025, c25)):
        pr = total((d18["P"][c][(y, "M")], d18["P"][c][(y, "F")]))
        ac = act.get(c, np.nan) if y == 2025 else total((src["P"][c][(y, "M")], src["P"][c][(y, "F")]))
        rows.append(dict(vintage="2018年推計", horizon=y - 2015, year=y, code=c, proj=pr, act=ac))
for c in [k for k, r in d23["info"].iterrows() if r.kind == "a"]:
    rows.append(dict(vintage="2023年推計", horizon=5, year=2025, code=c,
                     proj=total((d23["P"][c][(2025, "M")], d23["P"][c][(2025, "F")])), act=act.get(c, np.nan)))
hp = pd.DataFrame(rows)
hp["err"] = hp.proj / hp.act - 1
hp.to_csv(RES / "r3_backtest_vintages_pref.csv", index=False)
summary["bt_vintages_pref"] = {f"{v}_{h}年先": dict(mape=round(float(np.abs(g.err).mean() * 100), 3),
                                                   bias=round(float(g.err.mean() * 100), 3),
                                                   japan_err=round(float(g.proj.sum() / g.act.sum() - 1) * 100, 3))
                               for (v, h), g in hp.groupby(["vintage", "horizon"])}
# 市区町村：2018年推計（2015年基準）の2025年＝10年先
b18 = units.copy()
b18["proj2025"] = b18.code18.map(lambda c: total((d18["P"][c][(2025, "M")], d18["P"][c][(2025, "F")])))
b18["proj2020"] = b18.code18.map(lambda c: total((d18["P"][c][(2020, "M")], d18["P"][c][(2020, "F")])))
b18["act2020"] = b18.code23.map(lambda c: total((d23["P"][c][(2020, "M")], d23["P"][c][(2020, "F")])))
b18["act2025"] = b18.code23.map(act)
b18 = b18[b18.act2025.notna()]
summary["bt2018_muni"] = dict(h5=err_stats(b18.proj2020 / b18.act2020 - 1), h10=err_stats(b18.proj2025 / b18.act2025 - 1))
b18.to_csv(RES / "r3_backtest_2018_muni.csv", index=False)

# 3c. 自作の素朴な推計の「10年前版」：2010→15年の動きが続くとして、2015年から2025年を推計（都道府県）
rows = []
for c in [k for k, r in d18["info"].iterrows() if r.kind == "a"]:
    p10m, p10f = d13["P"][c][(2010, "M")], d13["P"][c][(2010, "F")]
    p15m, p15f = d18["P"][c][(2015, "M")], d18["P"][c][(2015, "F")]
    mm, mf = naive_rates(p10m, p10f, p15m, p15f, d13["S"][c][("2010→2015", "M")], d13["S"][c][("2010→2015", "F")])
    cw, sr = cwr_obs(p15m, p15f)
    steps = [(d18["S"][c][(per(a, b), "M")], d18["S"][c][(per(a, b), "F")], mm, mf, cw, sr) for a, b in ((2015, 2020), (2020, 2025))]
    res = project(p15m, p15f, steps, fidx=F2044)
    rows.append(dict(code=c, naive2020=total(res[1]), naive2025=total(res[2]),
                     act2020=total((d23["P"][c][(2020, "M")], d23["P"][c][(2020, "F")])), act2025=act.get(c, np.nan),
                     ipss2020=total((d18["P"][c][(2020, "M")], d18["P"][c][(2020, "F")])),
                     ipss2025=total((d18["P"][c][(2025, "M")], d18["P"][c][(2025, "F")]))))
nb = pd.DataFrame(rows)
nb.to_csv(RES / "r3_naive_from2015_pref.csv", index=False)
summary["naive_from2015_pref"] = {f"{w}{y}": round(float(np.abs(nb[f"{w}{y}"] / nb[f"act{y}"] - 1).mean() * 100), 3)
                                  for w in ("naive", "ipss") for y in (2020, 2025)}

# ---------------------------------------------------------------- 4. 仮定を変えたシナリオ（都道府県の合計＝全国）
prefs = [c for c, r in d23["info"].iterrows() if r.kind == "a"]
TOKYO = [11000, 12000, 13000, 14000]


def scen(code, mig=1.0, cwr_mult=1.0, cwr_fixed=False):
    st = steps_from(d23, code, YEARS23)
    p20m, p20f = d23["P"][code][(2020, "M")], d23["P"][code][(2020, "F")]
    cw0, sr0 = cwr_obs(p20m, p20f)
    out = []
    for sm, sf, mm, mf, cw, sr in st:
        out.append((sm, sf, mm * mig, mf * mig, (cw0 if cwr_fixed else cw) * cwr_mult, sr))
    return project(p20m, p20f, out, fidx=F2044)


SC = {"社人研の仮定": {}, "移動ゼロ": dict(mig=0.0), "移動を半分": dict(mig=0.5),
      "子ども女性比 +10%": dict(cwr_mult=1.1), "子ども女性比 −10%": dict(cwr_mult=0.9),
      "子ども女性比を2020年のまま": dict(cwr_fixed=True)}
rows = []
for name, kw in SC.items():
    res = {c: scen(c, **kw) for c in prefs}
    for i, y in enumerate(YEARS23):
        tot = sum(total(res[c][i]) for c in prefs)
        tk = sum(total(res[c][i]) for c in TOKYO)
        old = sum(res[c][i][0][13:].sum() + res[c][i][1][13:].sum() for c in prefs)
        rows.append(dict(scenario=name, year=y, japan=tot, tokyo_area_share=tk / tot, aged65_share=old / tot,
                         pref_below70=sum(total(res[c][i]) / total(res[c][0]) < 0.7 for c in prefs)))
# 自作の素朴な推計（都道府県）
res = {}
for c in prefs:
    res[c] = naive_project(c, d18["P"][c][(2015, "M")], d18["P"][c][(2015, "F")],
                           d18["S"][c][("2015→2020", "M")], d18["S"][c][("2015→2020", "F")])
for i, y in enumerate(YEARS23):
    tot = sum(total(res[c][i]) for c in prefs)
    tk = sum(total(res[c][i]) for c in TOKYO)
    old = sum(res[c][i][0][13:].sum() + res[c][i][1][13:].sum() for c in prefs)
    rows.append(dict(scenario="自作（2015→20年の動きが続く）", year=y, japan=tot, tokyo_area_share=tk / tot,
                     aged65_share=old / tot, pref_below70=sum(total(res[c][i]) / total(res[c][0]) < 0.7 for c in prefs)))
sc = pd.DataFrame(rows)
sc.to_csv(RES / "r4_scenarios.csv", index=False)
summary["scenarios_2050"] = sc[sc.year == 2050].set_index("scenario")[["japan", "tokyo_area_share", "aged65_share", "pref_below70"]].round(4).to_dict("index")

# ---------------------------------------------------------------- 5. 外れやすい市区町村の特徴（2025年の答え合わせ、社人研2023年推計）
fx = bt.copy()
p20 = {c: (d23["P"][c][(2020, "M")] + d23["P"][c][(2020, "F")]) for c in fx.code}
fx["share65"] = fx.code.map(lambda c: p20[c][13:].sum() / p20[c].sum())
fx["share2024"] = fx.code.map(lambda c: p20[c][4:5].sum() / p20[c].sum())
fx["chg1520"] = fx.pop2020 / fx.pop2015 - 1
fx["abs_err"] = np.abs(fx.err_ipss)
fx["ward"] = (fx.kind == "0").astype(int)
fx["town"] = (fx.kind == "3").astype(int)
import statsmodels.formula.api as smf
m = smf.ols("np.log(abs_err*100+0.1) ~ np.log(pop2020) + share65 + share2024 + ward + town", data=fx).fit(cov_type="HC1")
summary["miss_regression"] = {k: dict(coef=round(float(m.params[k]), 4), se=round(float(m.bse[k]), 4)) for k in m.params.index}
summary["miss_regression_r2"] = float(m.rsquared)
summary["miss_by_size"] = fx.groupby("size", observed=True).agg(n=("code", "size"), mape=("abs_err", lambda x: x.mean() * 100),
                                                                mdape=("abs_err", lambda x: x.median() * 100),
                                                                bias=("err_ipss", lambda x: x.mean() * 100)).round(3).to_dict("index")
summary["miss_by_kind"] = fx.groupby("kind").agg(n=("code", "size"), mape=("abs_err", lambda x: x.mean() * 100),
                                                 bias=("err_ipss", lambda x: x.mean() * 100)).round(3).to_dict("index")
q = pd.qcut(fx.share2024, 5, labels=False)
summary["miss_by_share2024_q"] = fx.groupby(q).agg(mape=("abs_err", lambda x: x.mean() * 100),
                                                   bias=("err_ipss", lambda x: x.mean() * 100)).round(3).to_dict("index")
fx.to_csv(RES / "r5_miss_features.csv", index=False)

# ---------------------------------------------------------------- 6. 頑健性
rob = []
# 6a. 移動率の基準期間：2010→15年 と 2015→20年（都道府県、2020年から2050年）
for c in prefs:
    p10m, p10f = d13["P"][c][(2010, "M")], d13["P"][c][(2010, "F")]
    p15m, p15f = d18["P"][c][(2015, "M")], d18["P"][c][(2015, "F")]
    mm, mf = naive_rates(p10m, p10f, p15m, p15f, d13["S"][c][("2010→2015", "M")], d13["S"][c][("2010→2015", "F")])
    p20m = c19(d23["P"][c][(2020, "M")]); p20f = c19(d23["P"][c][(2020, "F")])
    cw, sr = cwr_obs(p20m, p20f)
    r1015 = project(p20m, p20f, [(sm, sf, mm, mf, cw, sr) for sm, sf in ipss19_surv(c)], fidx=F2044)
    r1520 = naive_project(c, p15m, p15f, d18["S"][c][("2015→2020", "M")], d18["S"][c][("2015→2020", "F")])
    rsex = naive_project(c, p15m, p15f, d18["S"][c][("2015→2020", "M")], d18["S"][c][("2015→2020", "F")], combine_sex=True)
    rob.append(dict(code=c, pref=d23["info"].loc[c, "pref"], pop2020=total((p20m, p20f)),
                    ipss2050=total((d23["P"][c][(2050, "M")], d23["P"][c][(2050, "F")])),
                    base1015=total(r1015[-1]), base1520=total(r1520[-1]), sex_combined=total(rsex[-1]),
                    act2025=act.get(c, np.nan), base1015_2025=total(r1015[1]), base1520_2025=total(r1520[1]),
                    sexc_2025=total(rsex[1])))
rb = pd.DataFrame(rob)
rb.to_csv(RES / "r6_robust_pref.csv", index=False)
summary["robust_pref"] = dict(
    japan2050=dict(ipss=float(rb.ipss2050.sum()), base1520=float(rb.base1520.sum()), base1015=float(rb.base1015.sum()),
                   sex_combined=float(rb.sex_combined.sum())),
    corr_1015_1520=float(np.corrcoef(rb.base1015 / rb.pop2020, rb.base1520 / rb.pop2020)[0, 1]),
    mape2025=dict(base1520=float(np.abs(rb.base1520_2025 / rb.act2025 - 1).mean() * 100),
                  base1015=float(np.abs(rb.base1015_2025 / rb.act2025 - 1).mean() * 100),
                  sex_combined=float(np.abs(rb.sexc_2025 / rb.act2025 - 1).mean() * 100)))

# 6b. 男女をまとめた移動率（市区町村、2025年の答え合わせ）
rows = []
for u in units.itertuples(index=False):
    try:
        r = naive_project(u.code23, d18["P"][u.code18][(2015, "M")], d18["P"][u.code18][(2015, "F")],
                          d18["S"][u.code18][("2015→2020", "M")], d18["S"][u.code18][("2015→2020", "F")], combine_sex=True)
    except KeyError:
        continue
    rows.append(dict(code=u.code23, naive_sexc2025=total(r[1]), naive_sexc2050=total(r[-1])))
sx = both.merge(pd.DataFrame(rows), on="code")
summary["robust_sex_combined_muni"] = dict(sex_specific=err_stats(sx.err_naive),
                                           sex_combined=err_stats(sx.naive_sexc2025 / sx.act2025 - 1))

# 6c. 小さい町村（2020年に5千人未満）を県ごとにまとめる
small = both[both.pop2020 < 5000]
agg = []
for pref, g in small.groupby("pref"):
    agg.append(dict(pref=pref, n=len(g), act=g.act2025.sum(), ipss=g.ipss2025.sum(), naive=g.naive2025.sum()))
ag = pd.DataFrame(agg)
summary["robust_small_merged"] = dict(
    n_small=int(len(small)), n_groups=int(len(ag)),
    individual=dict(ipss=err_stats(small.err_ipss), naive=err_stats(small.err_naive)),
    merged=dict(ipss=err_stats(ag.ipss / ag.act - 1), naive=err_stats(ag.naive / ag.act - 1)))
ag.to_csv(RES / "r6_small_merged.csv", index=False)

# 6d. 2050年の比較を、移動率の基準期間を変えずに「移動を半分」にした自作でも確認（市区町村）
rows = []
for u in units.itertuples(index=False):
    try:
        r = naive_project(u.code23, d18["P"][u.code18][(2015, "M")], d18["P"][u.code18][(2015, "F")],
                          d18["S"][u.code18][("2015→2020", "M")], d18["S"][u.code18][("2015→2020", "F")], mig_scale=0.5)
    except KeyError:
        continue
    rows.append(dict(code=u.code23, naive_half2050=total(r[-1])))
hh = nv.merge(pd.DataFrame(rows), on="code")
summary["robust_naive_half_mig"] = dict(median_over_ipss=float((hh.naive_half2050 / hh.ipss2050).median()),
                                        corr=float(np.corrcoef(np.log(hh.ipss_ratio), np.log(hh.naive_half2050 / hh.pop2020))[0, 1]))

json.dump(summary, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps(summary, ensure_ascii=False, indent=1, default=float)[:9000])
