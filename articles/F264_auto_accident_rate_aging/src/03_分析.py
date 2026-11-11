"""F264 03 分析：免許保有者10万人当たり事故件数の変化を、年齢構成の効果と年齢ごとの率の効果に分ける。"""
import json, pathlib
import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parents[1]
P, RES = BASE / "data" / "processed", BASE / "results"
RES.mkdir(exist_ok=True)
AGES = ["16～19歳", "20～24歳", "25～29歳", "30～34歳", "35～39歳", "40～44歳", "45～49歳",
        "50～54歳", "55～59歳", "60～64歳", "65～69歳", "70～74歳", "75～79歳", "80～84歳", "85歳以上"]
GROUPS = {
    "表の15区分": {a: a for a in AGES},
    "65歳以上をまとめる": {a: (a if AGES.index(a) < 10 else "65歳以上") for a in AGES},
    "10歳刻み": {a: ["16～24歳", "16～24歳", "25～34歳", "25～34歳", "35～44歳", "35～44歳", "45～54歳",
                     "45～54歳", "55～64歳", "55～64歳", "65～74歳", "65～74歳", "75歳以上", "75歳以上", "75歳以上"][i]
                 for i, a in enumerate(AGES)},
}
main = pd.read_csv(P / "police_age_year_main.csv")
long = pd.read_csv(P / "police_age_year_long.csv")


def panel(df, kind, grouping="表の15区分"):
    d = df[(df.kind == kind) & (df.age.isin(AGES))].copy()
    d["g"] = d.age.map(GROUPS[grouping])
    g = d.groupby(["year", "g"], sort=False)[["count", "lic"]].sum().reset_index()
    g["r"] = g["count"] / g["lic"] * 1e5
    g["w"] = g.lic / g.groupby("year").lic.transform("sum")
    return g


def total_rate(g):
    return g.assign(x=g.w * g.r).groupby("year").x.sum()


def kitagawa(g, s, t, weight="mid"):
    a = g[g.year == s].set_index("g")
    b = g[g.year == t].set_index("g").loc[a.index]
    if weight == "mid":
        mix = ((b.w - a.w) * (a.r + b.r) / 2).sum(); rate = ((b.r - a.r) * (a.w + b.w) / 2).sum()
    elif weight == "start":   # 年齢構成の効果を始点の率で、率の効果を終点の構成で
        mix = ((b.w - a.w) * a.r).sum(); rate = ((b.r - a.r) * b.w).sum()
    else:                     # end
        mix = ((b.w - a.w) * b.r).sum(); rate = ((b.r - a.r) * a.w).sum()
    tot = (b.w * b.r).sum() - (a.w * a.r).sum()
    return dict(s=s, t=t, R_s=(a.w * a.r).sum(), R_t=(b.w * b.r).sum(), total=tot, mix=mix, rate=rate,
                mix_share_abs=mix / abs(tot), resid=tot - mix - rate)


def count_decomp(g, s, t):
    """件数の変化 = 保有者の総数 + 年齢構成 + 年齢ごとの率（対数で分ける、LMDI）。"""
    a = g[g.year == s].set_index("g"); b = g[g.year == t].set_index("g").loc[a.index]
    L = lambda x, y: np.where(np.isclose(x, y), x, (y - x) / (np.log(y) - np.log(x)))
    Ca, Cb = a["count"], b["count"]
    wgt = L(Ca.values, Cb.values)
    Na, Nb = a.lic.sum(), b.lic.sum()
    eff_n = (wgt * np.log(Nb / Na)).sum(); eff_w = (wgt * np.log(b.w.values / a.w.values)).sum()
    eff_r = (wgt * np.log(b.r.values / a.r.values)).sum()
    return dict(s=s, t=t, C_s=Ca.sum(), C_t=Cb.sum(), total=Cb.sum() - Ca.sum(), licensees=eff_n, age_mix=eff_w, rate=eff_r)


out = {}
for kind in ["all", "fatal"]:
    g = panel(main, kind)
    tr = total_rate(g)
    table_total = main[(main.kind == kind) & (main.age == "合計")].set_index("year").rate
    out[f"{kind}_series"] = pd.DataFrame({"R_reconstructed": tr, "R_table": table_total}).round(3).reset_index().to_dict("records")
    # 年齢をそろえた率（2009年と2025年の構成で固定）
    std = {}
    for base in [2009, 2025]:
        wb = g[g.year == base].set_index("g").w
        std[base] = g.assign(x=g.g.map(wb) * g.r).groupby("year").x.sum()
    out[f"{kind}_std"] = pd.DataFrame({"raw": tr, "std2009": std[2009], "std2025": std[2025]}).round(2).reset_index().to_dict("records")
    for (s, t) in [(2009, 2025), (2009, 2019), (2019, 2025), (2015, 2025)]:
        out[f"{kind}_kit_{s}_{t}"] = {w: kitagawa(g, s, t, w) for w in ["mid", "start", "end"]}
    out[f"{kind}_kit_groupings_2009_2025"] = {k: kitagawa(panel(main, kind, k), 2009, 2025) for k in GROUPS}
    # 毎年つないだ分解（コロナ期の 2019→2022 を除く版も）
    yrs = sorted(g.year.unique())
    chain = [kitagawa(g, a, b) for a, b in zip(yrs[:-1], yrs[1:])]
    out[f"{kind}_chain"] = chain
    ch = pd.DataFrame(chain)
    ex = ch[~ch.t.isin([2020, 2021, 2022])]
    out[f"{kind}_chain_sum"] = dict(total=ch.total.sum(), mix=ch.mix.sum(), rate=ch.rate.sum(),
                                    ex_covid_total=ex.total.sum(), ex_covid_mix=ex.mix.sum(), ex_covid_rate=ex.rate.sum(),
                                    ex_covid_mix_share=ex.mix.sum() / abs(ex.total.sum()))
    # 年齢ごとの率 2009→2025
    a = g[g.year == 2009].set_index("g").r; b = g[g.year == 2025].set_index("g").r
    out[f"{kind}_age_rate_change"] = pd.DataFrame({"r2009": a, "r2025": b, "pct": (b / a - 1) * 100}).round(2).reset_index().to_dict("records")
    out[f"{kind}_count_decomp_2009_2025"] = count_decomp(g, 2009, 2025)
    out[f"{kind}_count_decomp_2019_2025"] = count_decomp(g, 2019, 2025)
    # 版の重なる年（2015〜2019）で率がそろうか
    ov = long[(long.kind == kind) & long.year.between(2015, 2019) & long.age.isin(AGES + ["合計"])]
    pv = ov.pivot_table(index=["year", "age"], columns="edition", values="rate")
    pv["diff_pct"] = (pv["2025ed"] / pv["2019ed"] - 1) * 100
    out[f"{kind}_edition_overlap"] = dict(max_abs_pct=float(pv.diff_pct.abs().max()),
                                          total_rows=pv.reset_index()[pv.reset_index().age == "合計"].round(3).to_dict("records"))
    g.round(6).to_csv(RES / f"panel_{kind}.csv", index=False)

# 保険の頻度との比較（年ごとの変化率の相関）
ins = pd.read_csv(P / "giroj_jibaiseki_freq.csv").set_index("fy")
nn = pd.read_csv(P / "giroj_nini_freq.csv").set_index("fy")
pol = pd.Series({r["year"]: r["R_reconstructed"] for r in out["all_series"]})
polstd = pd.Series({r["year"]: r["std2009"] for r in out["all_std"]})
cmp = pd.DataFrame({"police": pol, "police_std2009": polstd, "jibai": ins.freq_per_10k, "nini": nn.freq_per_10k}).loc[2009:2025]
chg = np.log(cmp).diff()
def corr(a, b, rng):
    x = chg.loc[rng, [a, b]].dropna()
    return dict(n=len(x), r=float(x.corr().iloc[0, 1]) if len(x) > 2 else None, years=[int(i) for i in x.index])
out["insurance"] = dict(
    levels=cmp.round(3).reset_index().rename(columns={"index": "year"}).to_dict("records"),
    jibai_vs_police=corr("jibai", "police", slice(2010, 2025)),
    jibai_vs_police_ex_covid=corr("jibai", "police", [y for y in range(2010, 2024) if y not in (2020, 2021, 2022)]),
    nini_vs_police=corr("nini", "police", slice(2018, 2025)),
    jibai_vs_police_std=corr("jibai", "police_std2009", slice(2010, 2025)),
    jibai_change_2009_2023=float(cmp.jibai.loc[2023] / cmp.jibai.loc[2009] - 1),
    police_change_2009_2023=float(cmp.police.loc[2023] / cmp.police.loc[2009] - 1),
)

# 仮説の判定
k = out["all_kit_2009_2025"]["mid"]; f = out["fatal_kit_2009_2025"]["mid"]
H = {}
H["H1"] = dict(mix=k["mix"], total=k["total"], share=k["mix_share_abs"],
               verdict="支持" if (k["mix"] > 0 and k["mix_share_abs"] < 0.2) else "外れ")
H["H2"] = dict(all_share=k["mix_share_abs"], fatal_share=f["mix_share_abs"], ratio=f["mix_share_abs"] / k["mix_share_abs"],
               verdict="支持" if f["mix_share_abs"] >= 2 * k["mix_share_abs"] else "外れ")
up = [r["g"] for r in out["all_age_rate_change"] if r["pct"] > 0]
upf = [r["g"] for r in out["fatal_age_rate_change"] if r["pct"] > 0]
H["H3"] = dict(rose_all=up, rose_fatal=upf, verdict="支持" if not up else "外れ")
ji = out["insurance"]["jibai_vs_police"]
H["H4"] = dict(r=ji["r"], n=ji["n"], verdict=("判定せず" if ji["n"] < 6 else ("支持" if ji["r"] >= 0.7 else "外れ")))
out["hypotheses"] = H
json.dump(out, open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)

def fmt(d): return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()}
for kind in ["all", "fatal"]:
    print("==", kind)
    for key in [f"{kind}_kit_2009_2025", f"{kind}_kit_2009_2019", f"{kind}_kit_2019_2025", f"{kind}_kit_2015_2025"]:
        print(key, {w: (round(v["mix"], 2), round(v["rate"], 2), round(v["total"], 2), round(v["mix_share_abs"], 4)) for w, v in out[key].items()})
    print("groupings", {k: (round(v["mix"], 2), round(v["mix_share_abs"], 4)) for k, v in out[f"{kind}_kit_groupings_2009_2025"].items()})
    print("chain", fmt(out[f"{kind}_chain_sum"]))
    print("count2009-25", fmt(out[f"{kind}_count_decomp_2009_2025"]))
    print("count2019-25", fmt(out[f"{kind}_count_decomp_2019_2025"]))
    print("overlap max %", round(out[f"{kind}_edition_overlap"]["max_abs_pct"], 3))
    print(pd.DataFrame(out[f"{kind}_age_rate_change"]).to_string())
    print(pd.DataFrame(out[f"{kind}_std"]).to_string())
print({k: v for k, v in out["insurance"].items() if k != "levels"})
print(json.dumps(H, ensure_ascii=False, default=float))

# ---- 問い直し：年齢構成だけで、これから10年でどれだけ動くか（推測を含む投影）----
def project_mix(kind, base=2025, back=2015, youth_scale=1.0):
    g = panel(main, kind)
    L = {y: g[g.year == y].set_index("g").lic.reindex(AGES).values for y in (back, base)}
    R = g[g.year == base].set_index("g").r.reindex(AGES).values
    n = len(AGES)
    lic_new = np.zeros(n)
    # 2つ上の区分へ（10年で2段）：同じ生まれ年の人の残り方を、前の10年（back→base）と同じとみなす
    for i in range(n - 3):
        rho = L[base][i + 2] / L[back][i]
        lic_new[i + 2] = L[base][i] * rho
    # 85歳以上（開いた区分）
    rho_open = L[base][n - 1] / L[back][n - 3:].sum()
    lic_new[n - 1] = L[base][n - 3:].sum() * rho_open
    # 16〜24歳は、いまと同じ人数（youth_scale 倍）とおく
    lic_new[0] = L[base][0] * youth_scale; lic_new[1] = L[base][1] * youth_scale
    w0 = L[base] / L[base].sum(); w1 = lic_new / lic_new.sum()
    R0 = (w0 * R).sum(); R1 = (w1 * R).sum()
    return dict(kind=kind, back=back, youth_scale=youth_scale, R_base=R0, R_proj_mix_only=R1, pct=(R1 / R0 - 1) * 100,
                share65_base=float(w0[10:].sum()), share65_proj=float(w1[10:].sum()),
                share75_base=float(w0[12:].sum()), share75_proj=float(w1[12:].sum()),
                lic_total_base=float(L[base].sum()), lic_total_proj=float(lic_new.sum()))

proj = []
for kind in ["all", "fatal"]:
    for back, ys in [(2015, 1.0), (2015, 0.85), (2015, 1.15)]:
        proj.append(project_mix(kind, 2025, back, ys))
# 同じ方法で、過去（2009→2019 の残り方で 2019 から 2029 を出す代わりに、2015→2025 の実際と照らす）
def backtest(kind):
    g = panel(main, kind)
    L = {y: g[g.year == y].set_index("g").lic.reindex(AGES).values for y in (2009, 2015, 2019, 2025)}
    # 2015 の構成を、2009→2019 の残り方…は年がずれるので、2009→2015 の6年ではなく 10 年差がそろう 2015→2025 の実際の構成と、
    # 2015 の構成に 2009→2019 の残り方を当てた投影を比べる
    n = len(AGES); new = np.zeros(n)
    for i in range(n - 3):
        new[i + 2] = L[2015][i] * (L[2019][i + 2] / L[2009][i])
    new[n - 1] = L[2015][n - 3:].sum() * (L[2019][n - 1] / L[2009][n - 3:].sum())
    new[0], new[1] = L[2015][0], L[2015][1]
    R = g[g.year == 2015].set_index("g").r.reindex(AGES).values
    w_proj = new / new.sum(); w_act = L[2025] / L[2025].sum(); w0 = L[2015] / L[2015].sum()
    return dict(kind=kind, mix_only_proj_pct=((w_proj * R).sum() / (w0 * R).sum() - 1) * 100,
                mix_only_actual_pct=((w_act * R).sum() / (w0 * R).sum() - 1) * 100,
                share75_proj=float(w_proj[12:].sum()), share75_actual=float(w_act[12:].sum()))
bt = [backtest(k) for k in ["all", "fatal"]]
# 年齢層ごとの、年齢構成の効果への寄与（2009→2025、中点）
contrib = {}
for kind in ["all", "fatal"]:
    g = panel(main, kind); a = g[g.year == 2009].set_index("g"); b = g[g.year == 2025].set_index("g").loc[a.index]
    contrib[kind] = pd.DataFrame({"w2009": a.w, "w2025": b.w, "mix_contrib": (b.w - a.w) * (a.r + b.r) / 2,
                                  "r_mid": (a.r + b.r) / 2}).round(4).reset_index().to_dict("records")
out["reask"] = dict(projection=proj, backtest=bt)
out["mix_contrib_2009_2025"] = contrib
json.dump(out, open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
pd.DataFrame(proj).to_csv(RES / "reask_projection.csv", index=False)
print(pd.DataFrame(proj).round(4).to_string()); print(pd.DataFrame(bt).round(4).to_string())
print(pd.DataFrame(contrib["all"]).to_string()); print(pd.DataFrame(contrib["fatal"]).to_string())

# 年齢層ごとの寄与を、全体の平均の率からの差で表す（Σ Δw = 0 なので合計は同じ。どの年齢層が押し上げ・押し下げたかを読むため）
cent = {}
for kind in ["all", "fatal"]:
    g = panel(main, kind); a = g[g.year == 2009].set_index("g"); b = g[g.year == 2025].set_index("g").loc[a.index]
    rbar = ((a.w * a.r).sum() + (b.w * b.r).sum()) / 2
    c = (b.w - a.w) * ((a.r + b.r) / 2 - rbar)
    tot = (b.w * b.r).sum() - (a.w * a.r).sum()
    old = c[[x for x in c.index if AGES.index(x) >= 10]].sum(); young = c[[x for x in c.index if AGES.index(x) < 10]].sum()
    cent[kind] = dict(by_age=c.round(4).to_dict(), sum65plus=float(old), sum_under65=float(young), total_change=float(tot),
                      share65plus=float(old / abs(tot)), share_under65=float(young / abs(tot)))
out["mix_contrib_centered_2009_2025"] = cent
# 頑健性の一覧
rob = []
for kind in ["all", "fatal"]:
    for (s, t) in [(2009, 2025), (2009, 2019), (2019, 2025), (2015, 2025)]:
        for w in ["mid", "start", "end"]:
            d = out[f"{kind}_kit_{s}_{t}"][w]
            rob.append(dict(kind=kind, check=f"期間{s}→{t}・重み{w}", mix=d["mix"], total=d["total"], mix_share=d["mix_share_abs"]))
    for gname, d in out[f"{kind}_kit_groupings_2009_2025"].items():
        rob.append(dict(kind=kind, check=f"区分:{gname}", mix=d["mix"], total=d["total"], mix_share=d["mix_share_abs"]))
    c = out[f"{kind}_chain_sum"]
    rob.append(dict(kind=kind, check="毎年つなぐ", mix=c["mix"], total=c["total"], mix_share=c["mix"] / abs(c["total"])))
    rob.append(dict(kind=kind, check="毎年つなぐ・コロナ期(2020〜22年)を除く", mix=c["ex_covid_mix"], total=c["ex_covid_total"], mix_share=c["ex_covid_mix_share"]))
pd.DataFrame(rob).round(5).to_csv(RES / "robustness.csv", index=False)
json.dump(out, open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print({k: {kk: (round(vv, 3) if isinstance(vv, float) else vv) for kk, vv in v.items() if kk != "by_age"} for k, v in cent.items()})
print(pd.DataFrame(rob).round(4).to_string())
