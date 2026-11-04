"""03 分析：2つの統計の一致度（Bland–Altman・一致相関 CCC・系統的なずれ）
入力: data/pairs_pref.csv, data/pairs_muni.csv
出力: results/*.csv, results/summary.json
"""
import pandas as pd, numpy as np, json, pathlib
from scipy import stats
B = pathlib.Path(__file__).resolve().parents[1]; D = B / "data"; RS = B / "results"; RS.mkdir(exist_ok=True)
rng = np.random.default_rng(180)
P = pd.read_csv(D / "pairs_pref.csv"); M = pd.read_csv(D / "pairs_muni.csv", dtype={"code5": str})
# 2011年の原発事故で避難指示区域が設定された福島県の12市町村（国勢調査は実際に住む場所、住基は住民票の場所で数えるため、差が極端になる）
EVAC = {"07211", "07212", "07308", "07541", "07542", "07543", "07544", "07545", "07546", "07547", "07548", "07564"}
M["evac12"] = M["code5"].isin(EVAC)
M = M[(M["A1101"] > 0) & (M["A7101"] > 0)]  # 国勢調査で人口0の町（対数がとれない）を除く
P["lfs_pop15"] = P["lfs_pop15_k"] * 1000; P["lfs_emp"] = P["lfs_emp_k"] * 1000

def ccc(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    sxy = np.mean((x - x.mean()) * (y - y.mean()))
    return 2 * sxy / (x.var() + y.var() + (x.mean() - y.mean()) ** 2)

def diff(x, y, scale):
    """scale='pct': 100*ln(y/x)（対数の差、%）, 'pt': y−x（ポイント）, 'level': y−x（そのまま）"""
    x, y = np.asarray(x, float), np.asarray(y, float)
    return 100 * np.log(y / x) if scale == "pct" else y - x

def agree(x, y, scale, nb=2000):
    x, y = np.asarray(x, float), np.asarray(y, float)
    d = diff(x, y, scale); n = len(d)
    bias, sd = d.mean(), d.std(ddof=1)
    # 比例的なずれ：差を「大きさ」（対数の平均 or 平均）に回帰
    mag = (np.log(x) + np.log(y)) / 2 if scale == "pct" else (x + y) / 2
    sl = stats.linregress(mag, d)
    bs = []
    for _ in range(nb):
        i = rng.integers(0, n, n); db = d[i]
        bs.append((db.mean(), db.mean() - 1.96 * db.std(ddof=1), db.mean() + 1.96 * db.std(ddof=1)))
    bs = np.array(bs)
    lx, ly = (np.log(x), np.log(y)) if scale == "pct" else (x, y)
    return dict(n=n, bias=bias, sd=sd, loa_lo=bias - 1.96 * sd, loa_hi=bias + 1.96 * sd,
                bias_ci=[round(float(v), 4) for v in np.percentile(bs[:, 0], [2.5, 97.5])],
                loa_lo_ci=[round(float(v), 4) for v in np.percentile(bs[:, 1], [2.5, 97.5])], loa_hi_ci=[round(float(v), 4) for v in np.percentile(bs[:, 2], [2.5, 97.5])],
                prop_slope=sl.slope, prop_p=sl.pvalue,
                r_level=stats.pearsonr(x, y)[0], ccc_level=ccc(x, y),
                r_scaled=stats.pearsonr(lx, ly)[0], ccc_scaled=ccc(lx, ly),
                share_within_1=float(np.mean(np.abs(d) <= 1.0)), max_abs=float(np.abs(d).max()))

PAIRS = [  # (id, 名前, 国勢調査側, もう一方, 尺度)
    ("pop_total", "人口（総数）：国勢調査 vs 住民基本台帳（翌1月1日）", "A1101", "juki_pop_total", "pct"),
    ("pop_total_oct", "人口（総数）：国勢調査 vs 住民基本台帳（10月1日にならす）", "A1101", "juki_pop_total_oct", "pct"),
    ("pop_japanese", "日本人人口：国勢調査 vs 住民基本台帳", "A1102", "juki_pop_japanese", "pct"),
    ("pop_foreign", "外国人人口：国勢調査 vs 住民基本台帳", "A1700", "juki_pop_foreign", "pct"),
    ("households", "世帯数：国勢調査 vs 住民基本台帳（翌1月1日）", "A7101", "juki_hh_total", "pct"),
    ("households_oct", "世帯数：国勢調査 vs 住民基本台帳（10月1日にならす）", "A7101", "juki_hh_total_oct", "pct"),
    ("pop15", "15歳以上人口：国勢調査 vs 労働力調査", "cen_pop15", "lfs_pop15", "pct"),
    ("employed", "就業者数：国勢調査 vs 労働力調査", "F1102", "lfs_emp", "pct"),
    ("unemp_rate", "完全失業率：国勢調査 vs 労働力調査（ポイント）", "cen_unemp_rate", "lfs_unemp_rate", "pt"),
    ("emp_rate_known", "就業率：国勢調査（不詳を除く）vs 労働力調査（ポイント）", "cen_emp_rate_known", "lfs_emp_rate", "pt"),
    ("emp_rate_all15", "就業率：国勢調査（不詳を分母に含む）vs 労働力調査（ポイント）", "cen_emp_rate_all15", "lfs_emp_rate", "pt"),
]
rows = []
for pid, name, cx, cy, sc in PAIRS:
    for yr in [2015, 2020]:
        g = P[P.year == yr].dropna(subset=[cx, cy])
        r = agree(g[cx], g[cy], sc); r.update(pair=pid, name=name, year=yr, unit="都道府県", scale=sc); rows.append(r)
# 市区町村（人口・世帯数）
for pid, name, cx, cy in [("pop_total", "人口（総数）", "A1101", "juki_pop"), ("households", "世帯数", "A7101", "juki_hh")]:
    for yr in [2015, 2020]:
        for tag, g in [("市区町村", M[M.year == yr]), ("市区町村・12市町村を除く", M[(M.year == yr) & ~M.evac12])]:
            r = agree(g[cx], g[cy], "pct"); r.update(pair=pid, name=name + f"（{tag}）", year=yr, unit=tag, scale="pct"); rows.append(r)
T = pd.DataFrame(rows)
T.to_csv(RS / "agreement_table.csv", index=False, float_format="%.5g")

# 尺度を変える（同じ人口の組を、水準・対数・人口あたりで）
sc_rows = []
for yr in [2015, 2020]:
    g = P[P.year == yr]
    for pid, cx, cy in [("pop_total", "A1101", "juki_pop_total"), ("households", "A7101", "juki_hh_total"), ("pop_foreign", "A1700", "juki_pop_foreign")]:
        x, y = g[cx].values.astype(float), g[cy].values.astype(float)
        sc_rows.append(dict(pair=pid, year=yr, r_level=stats.pearsonr(x, y)[0], ccc_level=ccc(x, y),
                            ccc_log=ccc(np.log(x), np.log(y)),
                            ccc_per_capita=ccc(x / g["A1101"] * 1000, y / g["juki_pop_total"] * 1000) if pid != "pop_total" else np.nan,
                            r_per_capita=stats.pearsonr(x / g["A1101"], y / g["juki_pop_total"])[0] if pid != "pop_total" else np.nan))
S = pd.DataFrame(sc_rows); S.to_csv(RS / "scale_comparison.csv", index=False, float_format="%.5g")

# 年が変わっても、県ごとのずれは同じ向きか（系統的なずれの安定性）
st = []
for pid, cx, cy, sc in [(p[0], p[2], p[3], p[4]) for p in PAIRS]:
    a = P[P.year == 2015].set_index("pref_code"); b = P[P.year == 2020].set_index("pref_code")
    da, db = diff(a[cx], a[cy], sc), diff(b[cx], b[cy], sc)
    st.append(dict(pair=pid, r_2015_2020=stats.pearsonr(da, db)[0], spearman=stats.spearmanr(da, db)[0], same_sign=float(np.mean(np.sign(da) == np.sign(db)))))
ST = pd.DataFrame(st); ST.to_csv(RS / "stability_across_years.csv", index=False, float_format="%.4g")
dm = M[~M.evac12].pivot_table(index="code5", columns="year", values=["A1101", "juki_pop", "A7101", "juki_hh"]).dropna()
for v, (cx, cy) in {"pop": ("A1101", "juki_pop"), "hh": ("A7101", "juki_hh")}.items():
    d15 = 100 * np.log(dm[(cy, 2015)] / dm[(cx, 2015)]); d20 = 100 * np.log(dm[(cy, 2020)] / dm[(cx, 2020)])
    ST.loc[len(ST)] = dict(pair=f"muni_{v}", r_2015_2020=stats.pearsonr(d15, d20)[0], spearman=stats.spearmanr(d15, d20)[0], same_sign=float(np.mean(np.sign(d15) == np.sign(d20))))
ST.to_csv(RS / "stability_across_years.csv", index=False, float_format="%.4g")

# 市区町村：ずれと人口規模（規模別の幅）
M["size"] = pd.cut(M["A1101"], [0, 5e3, 2e4, 1e5, 1e6, 1e8], labels=["5千人未満", "5千〜2万", "2万〜10万", "10万〜100万", "100万以上"])
M["d_pop"] = 100 * np.log(M["juki_pop"] / M["A1101"]); M["d_hh"] = 100 * np.log(M["juki_hh"] / M["A7101"])
SZ = M[~M.evac12].groupby(["year", "size"], observed=True).agg(n=("d_pop", "size"), pop_bias=("d_pop", "mean"), pop_sd=("d_pop", "std"),
        pop_p05=("d_pop", lambda s: s.quantile(.05)), pop_p95=("d_pop", lambda s: s.quantile(.95)),
        hh_bias=("d_hh", "mean"), hh_sd=("d_hh", "std")).reset_index()
SZ.to_csv(RS / "muni_by_size.csv", index=False, float_format="%.4g")

# 失業率：労働力調査の小数1桁の丸めの影響（±0.05 の一様な揺れを足して1000回）
g = P[P.year == 2020]; sims = []
for _ in range(1000):
    y = g["lfs_unemp_rate"].values + rng.uniform(-0.05, 0.05, len(g))
    sims.append((ccc(g["cen_unemp_rate"], y), stats.pearsonr(g["cen_unemp_rate"], y)[0]))
sims = np.array(sims)
# 労働力状態「不詳」の割合と、就業率のずれの関係
uk = []
for yr in [2015, 2020]:
    g = P[P.year == yr]
    for k in ["cen_emp_rate_known", "cen_emp_rate_all15"]:
        r = stats.pearsonr(g["cen_labor_unknown_share"], g["lfs_emp_rate"] - g[k]); uk.append(dict(year=yr, census_def=k, r_unknown_vs_diff=r[0], p=r[1]))
UK = pd.DataFrame(uk); UK.to_csv(RS / "unknown_share_vs_emp_diff.csv", index=False, float_format="%.4g")

summ = dict(
    unemp_rounding=dict(ccc_mean=float(sims[:, 0].mean()), ccc_range=[float(sims[:, 0].min()), float(sims[:, 0].max())],
                        r_mean=float(sims[:, 1].mean())),
    unknown_share=P.groupby("year")["cen_labor_unknown_share"].describe()[["mean", "min", "max"]].round(2).to_dict("index"),
    totals={int(y): dict(cen_pop=int(g["A1101"].sum()), juki_pop=int(g["juki_pop_total"].sum()),
                         cen_hh=int(g["A7101"].sum()), juki_hh=int(g["juki_hh_total"].sum()),
                         cen_for=int(g["A1700"].sum()), juki_for=int(g["juki_pop_foreign"].sum()),
                         cen_unemp_nat=float(100 * g["F1107"].sum() / (g["F1102"].sum() + g["F1107"].sum())),
                         lfs_unemp_mean=float(g["lfs_unemp_rate"].mean()), cen_unemp_mean=float(g["cen_unemp_rate"].mean()))
            for y, g in P.groupby("year")},
)
# 失業率：比例的なずれ（労働力調査は県の差を縮めて出すか）
for yr in [2015, 2020]:
    g = P[P.year == yr]
    ls = stats.linregress(g["cen_unemp_rate"], g["lfs_unemp_rate"])
    summ[f"unemp_slope_{yr}"] = dict(slope=ls.slope, se=ls.stderr, sd_cen=float(g["cen_unemp_rate"].std()), sd_lfs=float(g["lfs_unemp_rate"].std()))
json.dump(summ, open(RS / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
pd.set_option("display.width", 250)
print(T[["pair", "unit", "year", "n", "bias", "loa_lo", "loa_hi", "prop_slope", "prop_p", "r_level", "ccc_level", "ccc_scaled", "share_within_1"]].round(3).to_string())
print(S.round(4).to_string()); print(ST.round(3).to_string()); print(SZ.round(2).to_string()); print(UK.round(3).to_string())
print(json.dumps(summ, ensure_ascii=False, default=float)[:1500])
