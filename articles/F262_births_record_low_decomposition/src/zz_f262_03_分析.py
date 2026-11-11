"""03 分析：出生数の変化を「女性の数」「年齢の並び方」「年齢別出生率」に分ける

B_t = Σ_a W_{a,t} f_{a,t} = N_t Σ_a c_{a,t} f_{a,t}（a：15〜19 … 45〜49歳、N：15〜49歳の女性の数、c：構成比、f：出生率）
- Das Gupta（1993）の3要因の対称な分解（各年齢の項 N·c_a·f_a に当てはめて足す。ΔB と完全に一致）
- Kitagawa（1955）の2要因の分解（W_a と f_a）
- 順番を決めた分解（人口を先に／率を先に）
- 各年の分解を足し合わせた「つなぎ」
出力：results/*.csv, results/main.json
"""
import json, pathlib
import numpy as np, pandas as pd
B = pathlib.Path(__file__).resolve().parents[1]
P, OUT = B / "data" / "processed", B / "results"
OUT.mkdir(exist_ok=True)
AG = ["a15", "a20", "a25", "a30", "a35", "a40", "a45"]
bi = pd.read_csv(P / "births_by_age.csv").set_index("year")
wa = pd.read_csv(P / "women_by_age.csv")
ri = pd.read_csv(P / "asfr_ipss.csv").set_index("year")

def women(source):
    """source: 'main'（2000〜2024 人口推計、2025 国勢調査）, 'implied'（出生数÷率）, 'main_or_implied'（2004年以前は逆算）"""
    est = wa[wa.source.isin(["estimate", "census2025"])].set_index("year")[AG]
    imp = wa[wa.source == "implied"].set_index("year")[AG].replace([np.inf, -np.inf], np.nan)
    if source == "main": return est
    if source == "implied": return imp
    return pd.concat([imp[imp.index < 2000], est]).sort_index()

def parts(y0, y1, W, ages=AG):
    b0, b1 = bi.loc[y0, ages].values.astype(float), bi.loc[y1, ages].values.astype(float)
    w0, w1 = W.loc[y0, ages].values.astype(float), W.loc[y1, ages].values.astype(float)
    f0, f1 = b0 / w0, b1 / w1
    N0, N1 = w0.sum(), w1.sum(); c0, c1 = w0 / N0, w1 / N1
    # Das Gupta 3要因（項ごと）
    eN = (N1 - N0) * ((c0 * f0 + c1 * f1) / 3 + (c0 * f1 + c1 * f0) / 6)
    ec = (c1 - c0) * ((N0 * f0 + N1 * f1) / 3 + (N0 * f1 + N1 * f0) / 6)
    ef = (f1 - f0) * ((N0 * c0 + N1 * c1) / 3 + (N0 * c1 + N1 * c0) / 6)
    dB = b1.sum() - b0.sum()
    assert abs(eN.sum() + ec.sum() + ef.sum() - dB) < 1e-6 * max(1, abs(dB)), "分解が合わない"
    kw = ((w1 - w0) * (f0 + f1) / 2).sum(); kf = ((f1 - f0) * (w0 + w1) / 2).sum()
    seq_pop_first = ((w1 - w0) * f0).sum(); seq_rate_first = ((w1 - w0) * f1).sum()
    return dict(y0=y0, y1=y1, B0=b0.sum(), B1=b1.sum(), dB=dB, pct=dB / b0.sum() * 100,
                N=eN.sum(), c=ec.sum(), f=ef.sum(), popeff=eN.sum() + ec.sum(),
                share_pop=(eN.sum() + ec.sum()) / dB, share_c_in_pop=ec.sum() / (eN.sum() + ec.sum()),
                kit_pop=kw, kit_rate=kf, kit_share_pop=kw / dB,
                seq_popfirst_share=seq_pop_first / dB, seq_ratefirst_share=seq_rate_first / dB,
                N0=N0, N1=N1, Npct=(N1 / N0 - 1) * 100, tfr0=5 * f0.sum(), tfr1=5 * f1.sum(),
                age_pop=list(eN + ec), age_rate=list(ef))

Wm = women("main")
main = {}
# 主な期間
for y0, y1 in [(2005, 2015), (2015, 2025), (2005, 2025)]:
    main[f"{y0}-{y1}"] = parts(y0, y1, Wm)
# 各年 2006〜2025
annual = pd.DataFrame([parts(y - 1, y, Wm) for y in range(2006, 2026)])
annual.drop(columns=["age_pop", "age_rate"]).to_csv(OUT / "annual_decomposition.csv", index=False)
# つなぎ（各年の和）
def chain(y0, y1, W):
    a = pd.DataFrame([parts(y - 1, y, W) for y in range(y0 + 1, y1 + 1)])
    s = a[["dB", "N", "c", "f"]].sum(); return dict(dB=s.dB, N=s.N, c=s.c, f=s.f, share_pop=(s.N + s.c) / s.dB, share_c_in_pop=s.c / (s.N + s.c))
# 長い期間（5年ごと、2004年以前は逆算した人口）
Wl = women("main_or_implied")
# 1990年などは45〜49歳の率が0.0（小数1桁で丸め）で逆算できないため、長い期間は15〜44歳で分解する
long = pd.DataFrame([parts(y0, y1, Wl, AG[:6]) for y0, y1 in [(1975, 1980), (1980, 1985), (1985, 1990), (1990, 1995), (1995, 2000), (2000, 2005), (2005, 2010), (2010, 2015), (2015, 2020), (2020, 2025)]])
long.drop(columns=["age_pop", "age_rate"]).to_csv(OUT / "long_decomposition.csv", index=False)

# 仮説の判定
p1525, p0515 = main["2015-2025"], main["2005-2015"]
yrs = annual[(annual.y1 >= 2016) & (annual.y1 <= 2025)]
n_rate_bigger = int((yrs.f.abs() > yrs.popeff.abs()).sum())
hyp = {
    "H1_share_pop_2015_2025": p1525["share_pop"], "H1_supported": p1525["share_pop"] < 0.5,
    "H2_rate_effect_2005_2015": p0515["f"], "H2_supported": p0515["f"] > 0,
    "H3_years_rate_bigger_2016_2025": n_rate_bigger, "H3_supported": n_rate_bigger >= 5,
    "H4_share_c_in_pop_2015_2025": p1525["share_c_in_pop"], "H4_supported": p1525["share_c_in_pop"] >= 0.25,
}

# 頑健性
rob = []
def add(name, d): rob.append({"case": name, **{k: d[k] for k in ["dB", "N", "c", "f", "share_pop", "share_c_in_pop"]}})
add("基準：Das Gupta 2015→2025（人口推計＋2025国勢調査）", p1525)
rob.append({"case": "Kitagawa 2要因", "dB": p1525["dB"], "share_pop": p1525["kit_share_pop"]})
rob.append({"case": "順番：人口を先に", "dB": p1525["dB"], "share_pop": p1525["seq_popfirst_share"]})
rob.append({"case": "順番：率を先に", "dB": p1525["dB"], "share_pop": p1525["seq_ratefirst_share"]})
add("各年の分解の和（2015→2025）", chain(2015, 2025, Wm))
add("年齢 20〜44歳", parts(2015, 2025, Wm, AG[1:6]))
add("人口：出生数÷出生率で逆算（2015→2024）", parts(2015, 2024, women("implied")))
add("終わりを2024年（2015→2024、推計人口のみ）", parts(2015, 2024, Wm))
add("2016→2025", parts(2016, 2025, Wm))
add("2014→2024", parts(2014, 2024, Wm))
# 14歳以下・50歳以上を除く（2015・2025 の値は厚労省 第6表）
x = pd.read_excel(B / "data" / "raw" / "mhlw_kakutei25_06_hyoR07.xlsx", "第６表", header=None)
lab = x[1].astype(str).str.replace(r"\s", "", regex=True); hdr = x.iloc[6].astype(str).str.replace(" ", "").tolist()
col = {2015: [i for i, h in enumerate(hdr) if "27年" in h][0], 2025: [i for i, h in enumerate(hdr) if "７年（'25）" in h][0]}
def g(y, k):
    v = x.iat[lab[lab.str.startswith(k)].index[0], col[y]]; return 0.0 if str(v).strip() in ("-", "nan") else float(v)
bkeep = bi.copy()
for y in (2015, 2025):
    bi.loc[y, "a15"] -= g(y, "14歳以下"); bi.loc[y, "a45"] -= g(y, "50歳以上")
add("14歳以下・50歳以上を除く", parts(2015, 2025, Wm))
bi = bkeep
# 2015・2025 の厚労省 第6表と IPSS 表4-7 の 2015 がそろうか
b15_mhlw = {k: g(2015, k) for k in ["総数"]}
rob = pd.DataFrame(rob); rob.to_csv(OUT / "robustness.csv", index=False)

# 年齢別（2015→2025）
ages = pd.DataFrame({"age": ["15〜19", "20〜24", "25〜29", "30〜34", "35〜39", "40〜44", "45〜49"],
                     "births2015": bi.loc[2015, AG].values, "births2025": bi.loc[2025, AG].values,
                     "women2015": Wm.loc[2015, AG].values, "women2025": Wm.loc[2025, AG].values,
                     "pop_effect": p1525["age_pop"], "rate_effect": p1525["age_rate"]})
ages["rate2015"] = ages.births2015 / ages.women2015 * 1000; ages["rate2025"] = ages.births2025 / ages.women2025 * 1000
ages.to_csv(OUT / "age_2015_2025.csv", index=False)

# 女性の数をそろえた出生数（各年の率 × 2025年の女性）と、合計特殊出生率
W25 = Wm.loc[2025, AG].values.astype(float)
yrs_all = [y for y in bi.index if y in Wl.index]
std = pd.DataFrame({"year": yrs_all,
                    "births": [bi.loc[y, AG].sum() for y in yrs_all],
                    "births_total_all": [bi.loc[y, "total_all"] for y in yrs_all],
                    "women15_49": [Wl.loc[y, AG].sum() for y in yrs_all],
                    "tfr_calc": [5 * np.nansum(bi.loc[y, AG].values / Wl.loc[y, AG].values) for y in yrs_all],
                    "births_at_2025_women": [np.nansum(bi.loc[y, AG].values / Wl.loc[y, AG].values * W25) for y in yrs_all],
                    "births_at_2015_rates": [np.nansum(bi.loc[2015, AG].values / Wl.loc[2015, AG].values * Wl.loc[y, AG].values) for y in yrs_all]})
# 45〜49歳を逆算できない年（率が0.0）は、その年齢を除いて計算している（影響は出生数の0.05%未満）
std.to_csv(OUT / "standardized.csv", index=False)

# H3 の頑健性：各年で「率の効果の大きさ > 人口の効果の大きさ」の年の数
def h3count(W, y_end=2025, ages=AG, method="dg"):
    n = 0; tot = 0
    for y in range(2016, y_end + 1):
        d = parts(y - 1, y, W, ages); tot += 1
        pe, fe = (d["popeff"], d["f"]) if method == "dg" else (d["kit_pop"], d["kit_rate"])
        n += abs(fe) > abs(pe)
    return n, tot
h3rob = {"基準（Das Gupta、2016〜2025）": h3count(Wm), "Kitagawa": h3count(Wm, method="kit"),
         "20〜44歳": h3count(Wm, ages=AG[1:6]), "逆算した人口（2016〜2024）": h3count(women("implied"), 2024),
         "推計人口のみ（2016〜2024）": h3count(Wm, 2024)}
pd.DataFrame([{"case": k, "years_rate_bigger": v[0], "years": v[1]} for k, v in h3rob.items()]).to_csv(OUT / "robustness_h3.csv", index=False)

# 問い直し（結果を見た後に加えた）：「過去最少」は、女性の数が減らなくても起きていたか／率が下がらなくても起きていたか
# (a) 女性の数と年齢の並びを2025年にそろえた出生数（＝その年の年齢別出生率 × 2025年の女性）の、それまでの最小を下回った年
# (b) 年齢別出生率を2015年にそろえた出生数（2015年の率 × その年の女性）が、それまでの実際の出生数の最小を下回った年
act = std.set_index("year").births
def record_years(series, start=2006):
    out = []
    for y in series.index:
        if y < start: continue
        prev = series[series.index < y]
        if series[y] < prev.min(): out.append(int(y))
    return out
rec_actual = record_years(act)
s_std25 = std.set_index("year").births_at_2025_women
rec_std25 = record_years(s_std25)
W15 = Wm.loc[2015, AG].values.astype(float)
s_std15 = pd.Series({y: np.nansum(bi.loc[y, AG].values / Wl.loc[y, AG].values * W15) for y in yrs_all})
rec_std15 = record_years(s_std15)
cf = std.set_index("year").births_at_2015_rates
rec_cf = [int(y) for y in range(2016, 2026) if cf[y] < min(act[act.index < 2016].min(), cf[(cf.index >= 2016) & (cf.index < y)].min() if y > 2016 else np.inf)]
reask = {"record_actual_2006_2025": rec_actual, "record_std_women2025": rec_std25, "record_std_women2015": rec_std15,
         "record_if_rates_2015": rec_cf,
         "std25_2005": s_std25[2005], "std25_2015": s_std25[2015], "std25_2022": s_std25[2022], "std25_2023": s_std25[2023], "std25_2025": s_std25[2025],
         "cf_2016": cf[2016], "cf_2025": cf[2025], "min_actual_before_2016": act[act.index < 2016].min(),
         "cf_annual_pct": list(((cf.loc[2016:2025].values / cf.loc[2015:2024].values) - 1) * 100)}
res_reask = reask

res = {"main": {k: {kk: vv for kk, vv in v.items() if kk not in ("age_pop", "age_rate")} for k, v in main.items()},
       "hypotheses": hyp, "h3_robust": h3rob, "reask": res_reask, "chain_2015_2025": chain(2015, 2025, Wm), "chain_2005_2015": chain(2005, 2015, Wm)}
(OUT / "main.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float))
pd.set_option("display.width", 220)
print(json.dumps(res["main"], ensure_ascii=False, indent=0, default=lambda v: round(float(v), 4))[:3000])
print(json.dumps(hyp, ensure_ascii=False, default=float)); print(h3rob); print(json.dumps(res_reask, ensure_ascii=False, default=lambda v: round(float(v), 3)))
print(annual[["y1", "dB", "pct", "N", "c", "f", "share_pop", "Npct", "tfr1"]].round(3).to_string())
print(rob.round(3).to_string())
print(long[["y0", "y1", "dB", "pct", "N", "c", "f", "share_pop"]].round(3).to_string())
print(std.round(3).to_string())
print(ages.round(1).to_string())
