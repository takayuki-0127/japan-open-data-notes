"""03 分析：2025年国勢調査（人口等基本集計）で、これまでの記事の結論が変わったかを確かめる。

1. F94（市町村合併の扱い方）… 2025年の表には「2000年の市町村ごとの人口」が載っている。
   F94 で仮定を置いて割り戻した（按分した）旧市町村の人口増減を、本当の値と照らし合わせる。2000→2025年
2. F14（コンパクトシティ計画と DID の人口密度）… 計画後の期間を 2020→25年に延ばし、同じマッチングで差を見る
3. F87（未婚割合と年齢・時代・世代）… 2025年の未婚割合を加え、「世代で並べたほうが当てはまる」を予測の当たり方で確かめる
4. F45（将来人口の推計）… すでに2025年で答え合わせ済み（結果を引用するだけ）
出力：results/*.csv, results/results.json
"""
import json
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.neighbors import NearestNeighbors

from common import DATA, RES, SEED

RES.mkdir(exist_ok=True)
rng = np.random.default_rng(SEED)
OUT = {}

# =====================================================================================
# 1. F94：2000年の市町村ごとの本当の2025年人口と、合併の扱い方
# =====================================================================================
old = pd.read_csv(DATA / "old_units_2025.csv", dtype={"code": str, "code2025": str})
cw = pd.read_csv(DATA / "f94_crosswalk_2000_2020.csv", dtype={"code2000": str, "code2020": str})
old = old.merge(cw[["code2000", "code2020", "unchanged", "merged", "n_old"]], left_on="code", right_on="code2000")
old = old[old.pop2000 > 0].copy()          # 三宅村（2000年は全島避難で人口0）を除く（F94 と同じ）
old["pref"] = old.code.str[:2].astype(int)
# 2020→2025年に境域が変わったか（2025年の表の「今の市町村」と F94 の2020年の対応表）
chg = old[old.code2025 != old.code2020]
OUT["boundary_change_2020_2025"] = dict(n_old_units_diff_code=int(len(chg)),
                                        examples=chg[["code", "name", "code2020", "code2025"]].head(10).values.tolist())
# 今の境域（2020年＝2025年）の2025年人口＝旧市町村の合計
p25 = old.groupby("code2020").pop2025.sum()
B = 1000


def stats(df, base="pop0", now="pop1", label="", boot=True):
    d = df[(df[base] > 0) & df[now].notna()].copy()
    d["rate"] = (d[now] / d[base] - 1) * 100
    x = np.log10(d[base].values); y = d.rate.values
    s = np.polyfit(x, y, 1)[0]
    lo = hi = np.nan
    if boot:
        r = np.random.default_rng(94)
        bs = []
        for _ in range(B):
            ix = r.integers(0, len(d), len(d)); bs.append(np.polyfit(x[ix], y[ix], 1)[0])
        lo, hi = np.percentile(bs, [2.5, 97.5])
    return dict(label=label, n=int(len(d)), median=float(np.median(y)),
                weighted_mean=float((d[now].sum() / d[base].sum() - 1) * 100),
                share_decline20=float((y <= -20).mean() * 100), share_decline30=float((y <= -30).mean() * 100),
                share_increase=float((y > 0).mean() * 100),
                slope=float(s), slope_lo=float(lo), slope_hi=float(hi)), d


def build(o, p1, years=25, base="pop2000"):
    o = o.copy(); o["pop0"] = o[base]
    out = {}
    t = o.set_index("code")[["pop0", "pop2025"]].rename(columns={"pop2025": "pop1"})
    out["TRUE"] = t                                                    # 本当の値（2025年の表の旧市町村）
    a = o.groupby("code2020").pop0.sum().to_frame(); a["pop1"] = p1.reindex(a.index)
    out["A"] = a
    b = o[o.unchanged].groupby("code2020").pop0.sum().to_frame(); b["pop1"] = p1.reindex(b.index)
    out["B"] = b
    c = o.set_index("code")[["pop0", "code2020", "unchanged"]].copy()
    c = c[c.index.isin(p1.index)]; c["pop1"] = p1.reindex(c.index)
    out["C"] = c
    for k, how in [("D1", "pop"), ("D2", "area"), ("D3", "trend")]:
        d = o.set_index("code")[["pop0", "pop2000", "pop1995", "area", "code2020", "pop2025", "merged"]].copy()
        if how == "pop":
            w = d.pop2000
        elif how == "area":
            w = d.area
        else:
            g = (d.pop2000 / d.pop1995).clip(0.5, 2.0).fillna(1.0)
            w = d.pop2000 * g ** (years / 5)
        d["w"] = w / w.groupby(d.code2020).transform("sum")
        d["pop1"] = d.w * p1.reindex(d.code2020).values
        out[k] = d
    return out


LAB = {"TRUE": "本当の値（旧市町村ごと、2025年の表）", "A": "A 再集計（今の境域）", "B": "B 変化なしだけ", "C": "C コード突合",
       "D1": "D1 按分（2000年人口比）", "D2": "D2 按分（面積比）", "D3": "D3 按分（1995→2000年の伸びを延長）"}
fr = build(old, p25)
rows, frames = [], {}
for k in ["TRUE", "A", "B", "C", "D1", "D2", "D3"]:
    st, frames[k] = stats(fr[k], label=LAB[k]); st["key"] = k; rows.append(st)
m25 = pd.DataFrame(rows)
m25.to_csv(RES / "f94_methods_2000_2025.csv", index=False)
print(m25[["key", "n", "median", "weighted_mean", "share_decline20", "share_increase", "slope", "slope_lo", "slope_hi"]].round(2).to_string())

# 按分（D）の当たり方：合併に関わった旧市町村について、割り戻した増減率と本当の増減率の差
tr = frames["TRUE"].rate
mg = old.set_index("code").merged
acc = []
for k in ["D1", "D2", "D3"]:
    dd = frames[k]
    e = (dd.rate - tr.reindex(dd.index))
    sel = mg.reindex(dd.index).fillna(False).astype(bool)
    acc.append(dict(key=k, n=int(sel.sum()), mae=float(e[sel].abs().mean()), median_ae=float(e[sel].abs().median()),
                    share_within5=float((e[sel].abs() <= 5).mean() * 100), corr=float(np.corrcoef(dd.rate[sel], tr.reindex(dd.index)[sel])[0, 1]),
                    bias=float(e[sel].mean())))
acc = pd.DataFrame(acc); acc.to_csv(RES / "f94_alloc_accuracy.csv", index=False)
print(acc.round(2).to_string())

# 合併した市町村の中の「中心」と「周辺」：同じグループの中で2000年人口が最大の旧市町村（中心）とそれ以外
t = old.set_index("code").copy()
t["rate"] = tr
t["is_core"] = t.pop2000 == t.groupby("code2020").pop2000.transform("max")
mm = t[t.merged]
core = dict(n_core=int(mm.is_core.sum()), n_periph=int((~mm.is_core).sum()),
            core_median=float(mm.loc[mm.is_core, "rate"].median()), periph_median=float(mm.loc[~mm.is_core, "rate"].median()),
            unmerged_median=float(t.loc[~t.merged, "rate"].median()),
            periph_share_decline30=float((mm.loc[~mm.is_core, "rate"] <= -30).mean() * 100),
            unmerged_share_decline30=float((t.loc[~t.merged, "rate"] <= -30).mean() * 100))
# 同じ人口規模でくらべる：log10(2000年人口)で回帰して「周辺」のダミーの係数
X = pd.DataFrame({"lp": np.log10(t.pop2000), "periph": (t.merged & ~t.is_core).astype(float), "core": (t.merged & t.is_core).astype(float)})
ols = sm.OLS(t.rate, sm.add_constant(X)).fit(cov_type="HC1")
core.update(periph_coef=float(ols.params["periph"]), periph_lo=float(ols.conf_int().loc["periph", 0]), periph_hi=float(ols.conf_int().loc["periph", 1]),
            core_coef=float(ols.params["core"]), core_lo=float(ols.conf_int().loc["core", 0]), core_hi=float(ols.conf_int().loc["core", 1]))
OUT["f94_core_periphery"] = core
print(core)

# 頑健性（F94 と同じ切り口）：本当の値と A・D1 の傾き
rob = []
def add(tag, o, base="pop2000"):
    p1 = o.groupby("code2020").pop2025.sum()
    f = build(o, p1, base=base)
    for k in ["TRUE", "A", "C", "D1", "D3"]:
        st, _ = stats(f[k], label=k)
        rob.append(dict(check=tag, method=k, **{x: st[x] for x in ["n", "median", "share_increase", "slope", "slope_lo", "slope_hi"]}))
add("基本（2000→2025）", old)
add("政令市・東京23区を除く", old[~old.type.isin(["seirei", "ward23"]) & ~old.code2020.str[2:].astype(int).between(100, 199)])
add("福島県を除く", old[old.pref != 7])
small = old.groupby("code2020").pop2000.transform("sum")
add("2000年人口1,000人未満の単位を除く", old[small >= 1000])
# 基準年を1995年に
add("基準年1995（1995→2025）", old[old.pop1995 > 0], base="pop1995")
rob = pd.DataFrame(rob); rob.to_csv(RES / "f94_robustness.csv", index=False)

# F94（2000→2020年）の公表値との並べ比べ用
f94_2020 = {"A": dict(median=-15.5, share_increase=22.0, slope=15.3), "B": dict(median=-14.8, share_increase=26.5, slope=18.1),
            "C": dict(median=-8.9, share_increase=35.6, slope=18.8), "D1": dict(median=-15.9, share_increase=17.1, slope=13.1),
            "D3": dict(median=-18.6, share_increase=17.4, slope=17.5)}
OUT["f94_2020_published"] = f94_2020

# =====================================================================================
# 2. F14：コンパクトシティ計画（立地適正化計画）と DID の人口密度、計画後を 2020→25年に延ばす
# =====================================================================================
did = pd.read_csv(DATA / "f14_did_muni.csv", dtype={"code5": str})
pl = pd.read_csv(DATA / "f14_plans.csv", dtype=str)
d25 = pd.read_csv(DATA / "did_2025.csv", dtype={"code5": str})
df = did.merge(pl[["code", "first_pub", "R0207"]], on="code", how="left").merge(
    d25[["code5", "pop2025", "pop2020", "area2025"]].rename(columns={"pop2020": "pop2020_kumikae"}), on="code5", how="left")
Y = [2005, 2010, 2015, 2020]
df = df.dropna(subset=[f"pop{y}" for y in Y]).copy()
df["総人口"] = pd.to_numeric(df["総人口"])
# 2020年の DID 人口が、2025年の表の「2020年の人口（組替）」と同じか（同じ DID の2020年値を使っているかの確認）
both = df.dropna(subset=["pop2020_kumikae"])
OUT["f14_check_pop2020"] = dict(n=int(len(both)), share_exact=float((np.isclose(both.pop2020, both.pop2020_kumikae)).mean() * 100),
                                median_abs_diff_pct=float((both.pop2020 / both.pop2020_kumikae - 1).abs().median() * 100))
df["dens2025"] = df.pop2025 / df.area2025
OUT["f14_did_lost_2025"] = int(df.pop2025.isna().sum())   # 2025年に DID がなくなった市町村
for a, b in [(2005, 2010), (2010, 2015), (2015, 2020), (2020, 2025)]:
    df[f"d_dens_{b}"] = 100 * (np.log(df[f"dens{b}"]) - np.log(df[f"dens{a}"]))
    df[f"d_pop_{b}"] = 100 * (np.log(df[f"pop{b}"]) - np.log(df[f"pop{a}"]))
    df[f"d_area_{b}"] = 100 * (np.log(df[f"area{b}"]) - np.log(df[f"area{a}"]))
df["d_dens_2015_25"] = df.d_dens_2020 + df.d_dens_2025
for c in [c for c in df.columns if c.startswith("d_")]:
    lo, hi = df[c].quantile([0.01, 0.99]); df[c] = df[c].clip(lo, hi)        # F14 と同じく上下1%で丸める
df["group"] = np.where(df.first_pub.notna(), "作成", np.where(df.R0207.notna(), "作成中", "未作成"))
df["x_lpop"] = np.log(df.pop2010); df["x_ldens"] = np.log(df.dens2010)
df["x_trend"] = df.d_dens_2010; df["x_ptrend"] = df.d_pop_2010; df["x_ndid"] = np.log(df.n_did2010)
df["x_ltot"] = np.log(df["総人口"])
X14 = ["x_lpop", "x_ldens", "x_trend", "x_ptrend", "x_ndid", "x_ltot"]
df = df[~df.code5.str.startswith("131")].copy()


def pscore(d, treat):
    m = sm.Logit(treat.astype(float), sm.add_constant(d[X14])).fit(disp=0)
    return m.predict(sm.add_constant(d[X14]))


def match(d, ps, treat, caliper=0.2):
    lg = np.log(ps / (1 - ps)); cal = caliper * lg.std()
    t = d[treat].index; c = d[~treat].index
    nn = NearestNeighbors(n_neighbors=1).fit(lg[c].values.reshape(-1, 1))
    dist, idx = nn.kneighbors(lg[t].values.reshape(-1, 1))
    return pd.DataFrame([(ti, c[idx[i, 0]]) for i, ti in enumerate(t) if dist[i, 0] <= cal], columns=["t", "c"])


def est_psm(d, y):
    d = d.dropna(subset=[y]).reset_index(drop=True); tr = d.group == "作成"
    ps = pscore(d, tr); pr = match(d, ps, tr)
    return float((d.loc[pr.t, y].values - d.loc[pr.c, y].values).mean())


def est_dr(d, y):
    d = d.dropna(subset=[y]).reset_index(drop=True); tr = d.group == "作成"
    ps = pscore(d, tr).clip(0.01, 0.99)
    ols = sm.OLS(d.loc[~tr, y], sm.add_constant(d.loc[~tr, X14])).fit()
    mu0 = ols.predict(sm.add_constant(d[X14])); w = ps / (1 - ps)
    return float((d.loc[tr, y] - mu0[tr]).mean() - np.average(d.loc[~tr, y] - mu0[~tr], weights=w[~tr]))


def boot(fun, d, Bn=300):
    vals = []
    for _ in range(Bn):
        db = d.loc[rng.choice(d.index, len(d), replace=True)].reset_index(drop=True)
        try: vals.append(fun(db))
        except Exception: pass
    return np.percentile(vals, [2.5, 97.5])


base = df[df.group.isin(["作成", "未作成"])].reset_index(drop=True)
T = base.group == "作成"
ev = []
for per, y in [("2005→10（計画前）", "d_dens_2010"), ("2010→15（計画前）", "d_dens_2015"), ("2015→20（計画後・F14）", "d_dens_2020"),
               ("2020→25（計画後・今回）", "d_dens_2025"), ("2015→25（計画後の10年）", "d_dens_2015_25")]:
    ok = base[y].notna()
    att = est_psm(base, y); lo, hi = boot(lambda d: est_psm(d, y), base)
    ev.append({"期間": per, "n_作成": int((T & ok).sum()), "n_未作成": int((~T & ok).sum()),
               "作成の平均": base.loc[T & ok, y].mean(), "未作成の平均": base.loc[~T & ok, y].mean(),
               "単純な差": base.loc[T & ok, y].mean() - base.loc[~T & ok, y].mean(), "マッチング後の差": att, "95%下": lo, "95%上": hi})
ev = pd.DataFrame(ev); ev.to_csv(RES / "f14_event_psm_2025.csv", index=False, encoding="utf-8-sig")
print(ev.round(2).to_string())
# 頑健性：二重頑健（IPW＋回帰調整）、DID 人口・面積に分ける、作成中も含めた比較
r14 = []
for y, lab in [("d_dens_2025", "密度 2020→25"), ("d_pop_2025", "DID 人口 2020→25"), ("d_area_2025", "DID 面積 2020→25"), ("d_dens_2015_25", "密度 2015→25")]:
    att = est_psm(base, y); lo, hi = boot(lambda d: est_psm(d, y), base, 200)
    dr = est_dr(base, y); dlo, dhi = boot(lambda d: est_dr(d, y), base, 200)
    r14.append(dict(指標=lab, PSM=att, PSM下=lo, PSM上=hi, 二重頑健=dr, 二重頑健下=dlo, 二重頑健上=dhi))
b2 = df[df.group.isin(["作成", "作成中", "未作成"])].copy(); b2["group"] = np.where(b2.group == "作成", "作成", "未作成"); b2 = b2.reset_index(drop=True)
att = est_psm(b2, "d_dens_2025"); lo, hi = boot(lambda d: est_psm(d, "d_dens_2025"), b2, 200)
r14.append(dict(指標="密度 2020→25（作成中も対照に）", PSM=att, PSM下=lo, PSM上=hi))
r14 = pd.DataFrame(r14); r14.to_csv(RES / "f14_robustness_2025.csv", index=False, encoding="utf-8-sig")
print(r14.round(2).to_string())

# =====================================================================================
# 3. F87：2025年の未婚割合と、「時代で並べる」「世代で並べる」予測の当たり方
# =====================================================================================
up = pd.read_csv(DATA / "f87_unmarried_pct.csv", encoding="utf-8-sig")
m25 = pd.read_csv(DATA / "marital_2025.csv")
ages = ["20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64"]
p = up.pivot_table(index=["sex", "age"], columns="year", values="unmarried_pct")
p[2025] = m25.set_index(["sex", "age"]).unmarried_pct
p["2025_incl_unknown"] = m25.set_index(["sex", "age"]).unmarried_pct_incl_unknown
p.to_csv(RES / "f87_unmarried_2015_2025.csv")
# 不詳補完値（2020年遡及・2025年）：配偶関係「不詳」を補完した値どうしで比べる
hk = pd.read_csv(DATA / "marital_hokan_2020_2025.csv").pivot_table(index=["sex", "age"], columns="year", values="unmarried_pct")
p["hokan2020"] = hk[2020]; p["hokan2025"] = hk[2025]
p.to_csv(RES / "f87_unmarried_2015_2025.csv")
cmp_ = []
for sex in ["女", "男"]:
    for a in ages:
        r = p.loc[(sex, a)]
        cmp_.append(dict(sex=sex, age=a, ipss2015=r[2015], ipss2020=r[2020], gen2025_excl_unknown=r[2025], gen2025_incl_unknown=r["2025_incl_unknown"],
                         hokan2020=r["hokan2020"], hokan2025=r["hokan2025"],
                         chg_excl_unknown=r[2025] - r[2020], chg_hokan=r["hokan2025"] - r["hokan2020"], chg_prev_ipss=r[2020] - r[2015]))
cmp_ = pd.DataFrame(cmp_); cmp_.to_csv(RES / "f87_compare_2020_2025.csv", index=False)
print(cmp_.round(1).to_string())
OUT["f87_share_ages_rising"] = dict(
    excl_unknown=int((cmp_.chg_excl_unknown > 0).sum()), hokan=int((cmp_.chg_hokan > 0).sum()), n=int(len(cmp_)))
# 50歳時の未婚割合（45〜49歳と50〜54歳の平均）
u50 = {}
for sex in ["女", "男"]:
    for y in [2010, 2015, 2020, 2025]:
        u50[f"{sex}_{y}"] = float((p.loc[(sex, "45-49"), y] + p.loc[(sex, "50-54"), y]) / 2)
    for c in ["2025_incl_unknown", "hokan2020", "hokan2025"]:
        u50[f"{sex}_{c}"] = float((p.loc[(sex, "45-49"), c] + p.loc[(sex, "50-54"), c]) / 2)
OUT["f87_unmarried_at50"] = u50
OUT["f87_unknown_pct_2025"] = m25.set_index(["sex", "age"]).unknown_pct.round(2).reset_index().query("age in @ages").values.tolist()
print(u50)

# =====================================================================================
# 4. F45（引用のみ）
# =====================================================================================
OUT["f45_cited"] = dict(mae_ipss2023_muni=1.80, mae_naive_muni=2.34, national_actual=122972528, national_ipss=123260000)

json.dump(OUT, open(RES / "results.json", "w"), ensure_ascii=False, indent=1, default=float)
