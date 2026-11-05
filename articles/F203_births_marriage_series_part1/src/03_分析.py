"""F203 前編：出生の減少を「結婚（有配偶率）」と「夫婦の出生（有配偶出生率）」に分ける。

A. 全国の時系列：合計特殊出生率（TFR）＝5×Σ年齢 有配偶割合×有配偶出生率 として、年の間の変化を2つに分ける（対称な分解）
B. 生まれ年（コーホート）：30歳までに産んだ数と、49歳までに産んだ数の関係（遅れた分がどれだけ後で取り戻されたか）
C. 地域（2020年前後）：都道府県・市区町村の TFR を、全国の有配偶出生率を当てはめた「結婚だけで決まる TFR」と、その残り（夫婦の出生）に分ける
"""
import json
import numpy as np, pandas as pd
from common import DATA, RES, AGES, SEED

rng = np.random.default_rng(SEED)
RES.mkdir(exist_ok=True)
res = {}

# ---------- A. 全国の時系列 ----------
asfr = pd.read_csv(DATA / "national_asfr5.csv").set_index("year")
mar = pd.read_csv(DATA / "national_married.csv")
YEARS = [1970, 1980, 1990, 2000, 2010, 2015, 2020]

def comp(year, nonmar=0.0, defn="married", ages=AGES):
    m = mar[mar.year == year].set_index("age")
    share = m["married"] if defn == "married" else 1 - m["never"]
    f = asfr.loc[year, ages].astype(float)
    g = (1 - nonmar) * f / share[ages]       # 有配偶（または結婚経験のある）女性1人あたりの出生率
    return share[ages].astype(float), g

def decompose(y0, y1, **kw):
    m0, g0 = comp(y0, **kw); m1, g1 = comp(y1, **kw)
    marriage = 5 * ((m1 - m0) * (g0 + g1) / 2).sum()
    marital = 5 * ((g1 - g0) * (m0 + m1) / 2).sum()
    # 非嫡出の分（nonmar）は「その他」として残る：TFR 全体の変化＝結婚＋夫婦＋その他
    nm = kw.get("nonmar", 0.0)
    ages = kw.get("ages", AGES)
    t0 = 5 * asfr.loc[y0, ages].sum(); t1 = 5 * asfr.loc[y1, ages].sum()
    other = (t1 - t0) - marriage - marital
    # 片側の重み（始点だけ・終点だけ）での分解も残す（分解の向きによる違い）
    mar_start = 5 * ((m1 - m0) * g0).sum(); mar_end = 5 * ((m1 - m0) * g1).sum()
    return dict(y0=y0, y1=y1, tfr0=t0, tfr1=t1, d=t1 - t0, marriage=marriage, marital=marital, other=other,
                marriage_share=marriage / (t1 - t0), marriage_start=mar_start, marriage_end=mar_end)

A = [decompose(a, b) for a, b in zip(YEARS[:-1], YEARS[1:])]
A_long = [decompose(1970, 2020), decompose(1990, 2020), decompose(2000, 2020), decompose(2010, 2020)]
pd.DataFrame(A + A_long).to_csv(RES / "A_decomposition.csv", index=False)
res["A_main_1970_2020"] = decompose(1970, 2020)
res["A_1990_2020"] = decompose(1990, 2020)
res["A_2010_2020"] = decompose(2010, 2020)
# 頑健性：非嫡出の割合（0/2.5/5%）、定義（有配偶か結婚経験か）、年齢の範囲（20〜39歳）
rob = []
for nm in [0.0, 0.025, 0.05]:
    for defn in ["married", "ever"]:
        for ages, lab in [(AGES, "15-49"), (AGES[1:5], "20-39")]:
            for y0 in [1970, 1990, 2010]:
                d = decompose(y0, 2020, nonmar=nm, defn=defn, ages=ages)
                rob.append(dict(nonmar=nm, defn=defn, ages=lab, y0=y0, d=d["d"], marriage=d["marriage"],
                                marital=d["marital"], other=d["other"], marriage_share=d["marriage_share"],
                                marriage_start=d["marriage_start"], marriage_end=d["marriage_end"]))
rob = pd.DataFrame(rob); rob.to_csv(RES / "A_robustness.csv", index=False)
res["A_rob_range"] = {str(y0): [float(rob[rob.y0 == y0].marriage_share.min()), float(rob[rob.y0 == y0].marriage_share.max())] for y0 in [1970, 1990, 2010]}
# 年齢別の有配偶割合と有配偶出生率（図用）
ag = []
for y in YEARS:
    m, g = comp(y)
    for a in AGES: ag.append(dict(year=y, age=a, married=m[a], marital_rate=g[a], asfr=asfr.loc[y, a]))
pd.DataFrame(ag).to_csv(RES / "A_age_profiles.csv", index=False)
# 2025年：有配偶割合だけ2025年にし、有配偶出生率は2020年のままにした TFR（結婚の分だけの見込み）
m20, g20 = comp(2020)
m25 = mar[mar.year == 2025].set_index("age")["married"][AGES]
tfr20 = 5 * asfr.loc[2020, AGES].sum()
res["A_2025_marriage_only"] = dict(tfr2020=float(tfr20), tfr_with_2025_married=float(5 * (m25 * g20).sum()),
                                   married_2025=dict(zip(AGES, map(float, m25))), married_2020=dict(zip(AGES, map(float, m20))))
# 有配偶出生率の2020年の値を年齢別に（後編のシナリオで使う）
res["A_marital_rate_2020"] = dict(zip(AGES, map(float, g20)))

# ---------- B. 生まれ年（コーホート） ----------
cc = pd.read_csv(DATA / "raw" / "f58_cohort_cumulative.csv").set_index("age")
# 列は「15歳になった年」。生まれ年＝列−15。値はすでに累積（女性1人あたり）
cc.columns = cc.columns.astype(int) - 15
cum = cc
cohorts = [c for c in cc.columns if pd.notna(cc.loc[49, c])]
B = pd.DataFrame({"cohort": cohorts,
                  "cum30": [cum.loc[30, c] for c in cohorts], "cum35": [cum.loc[35, c] for c in cohorts],
                  "cum40": [cum.loc[40, c] for c in cohorts], "cum45": [cum.loc[45, c] for c in cohorts],
                  "cum49": [cum.loc[49, c] for c in cohorts]})
B["after30"] = B.cum49 - B.cum30
B.to_csv(RES / "B_cohort.csv", index=False)
def slope(df, x, y):
    X = np.c_[np.ones(len(df)), df[x]]; b = np.linalg.lstsq(X, df[y], rcond=None)[0]
    r = df[y] - X @ b; se = np.sqrt((r @ r) / (len(df) - 2) / ((df[x] - df[x].mean()) ** 2).sum())
    return float(b[1]), float(se)
b_main, se_main = slope(B, "cum30", "cum49")
res["B_main"] = dict(n=len(B), first=int(B.cohort.min()), last=int(B.cohort.max()), slope=b_main, se=se_main,
                     recovered_share=1 - b_main,
                     cum30_first=float(B.cum30.iloc[0]), cum30_last=float(B.cum30.iloc[-1]),
                     cum49_first=float(B.cum49.iloc[0]), cum49_last=float(B.cum49.iloc[-1]))
# 頑健性：基準の年齢（28・30・32）、終わりの年齢（45・49）、コーホートの範囲
brob = []
for ref in [28, 30, 32]:
    for end in [45, 49]:
        for lo in [1932, 1945, 1955]:
            sub = cohorts if True else None
            d = pd.DataFrame({"c": cohorts, "x": [cum.loc[ref, c] for c in cohorts], "y": [cum.loc[end, c] for c in cohorts]})
            d = d[d.c >= lo]
            s, se = slope(d, "x", "y")
            brob.append(dict(ref_age=ref, end_age=end, from_cohort=lo, n=len(d), slope=s, se=se, recovered_share=1 - s))
brob = pd.DataFrame(brob); brob.to_csv(RES / "B_robustness.csv", index=False)
res["B_rob_range"] = [float(brob.recovered_share.min()), float(brob.recovered_share.max())]
# 結婚経験のある女性あたりの最終の子ども数（国勢調査の45〜49歳の未婚割合を、その年に45〜49歳の生まれ年に当てる）
evm = []
for y in [2000, 2010, 2015, 2020]:
    nev = float(mar[(mar.year == y) & (mar.age == "45-49")].never.iloc[0])
    cs = [c for c in range(y - 49, y - 44) if c in cohorts]
    if not cs: continue
    cfr = float(np.mean([cum.loc[49, c] for c in cs]))
    evm.append(dict(census=y, cohorts=f"{min(cs)}-{max(cs)}", never_45_49=nev, cfr49=cfr, cfr_per_ever_married=cfr / (1 - nev)))
evm = pd.DataFrame(evm); evm.to_csv(RES / "B_ever_married.csv", index=False)
res["B_ever_married"] = evm.to_dict("records")
if len(evm) >= 2:
    e0, e1 = evm.iloc[0], evm.iloc[-1]
    d = e1.cfr49 - e0.cfr49
    # 対称な分解：結婚経験の割合の変化 × 1人あたり ＋ 1人あたりの変化 × 結婚経験の割合
    p0, p1 = 1 - e0.never_45_49, 1 - e1.never_45_49; q0, q1 = e0.cfr_per_ever_married, e1.cfr_per_ever_married
    res["B_cfr_decomp"] = dict(from_=e0.cohorts, to=e1.cohorts, d=float(d), marriage=float((p1 - p0) * (q0 + q1) / 2),
                               per_married=float((q1 - q0) * (p0 + p1) / 2))

# ---------- C. 地域 ----------
ar = pd.read_csv(DATA / "areas_2020.csv", dtype={"code": str})
for c in ar.columns:
    if c.startswith(("tot_", "mar_", "nev_")):
        ar[c] = pd.to_numeric(ar[c].astype(str).str.replace("-", "0"), errors="coerce")
ar = ar[ar.tfr_bayes.notna()].copy()
nat_f = pd.read_csv(DATA / "national_asfr_2018_22.csv").set_index("age")["asfr_bayes"]
# 全国の有配偶割合（2020年国勢調査・不詳補完値の全国）
cen = pd.read_csv(DATA / "raw" / "f203_census2020_women_marital.csv", dtype={"code": str})
natc = cen[cen.code.astype(str).str.zfill(5) == "00000"].set_index("marital")
natc = natc.apply(pd.to_numeric, errors="coerce") if False else natc
for _c in ["a15_19","a20_24","a25_29","a30_34","a35_39","a40_44","a45_49"]: natc[_c] = pd.to_numeric(natc[_c], errors="coerce")
cols = ["a15_19", "a20_24", "a25_29", "a30_34", "a35_39", "a40_44", "a45_49"]
nat_m = pd.Series([natc.loc[2, c] / natc.loc[0, c] for c in cols], index=AGES)
nat_ev = pd.Series([1 - natc.loc[1, c] / natc.loc[0, c] for c in cols], index=AGES)
TFR_NAT = 1.33
g_nat = nat_f / nat_m; g_nat_ev = nat_f / nat_ev
res["C_national"] = dict(tfr=TFR_NAT, married=dict(zip(AGES, map(float, nat_m))), marital_rate=dict(zip(AGES, map(float, g_nat))))

def regional(df, ages=AGES, defn="married", tfr="tfr_bayes"):
    d = df.copy()
    sh = {a: (d["mar_" + a] / d["tot_" + a]) if defn == "married" else (1 - d["nev_" + a] / d["tot_" + a]) for a in ages}
    g = g_nat if defn == "married" else g_nat_ev
    E = 5 * sum(sh[a] * g[a] for a in ages)
    if tfr == "tfr_bayes":
        T = d[tfr] if ages == AGES else 5 * sum(d["b" + a[:2]] / 1000 for a in ages)
    else:
        T = d[tfr] if ages == AGES else 5 * sum(d["r" + a[:2]] / 1000 for a in ages)
    Enat = 5 * sum(((nat_m if defn == "married" else nat_ev)[a]) * g[a] for a in ages)
    Tnat = TFR_NAT if ages == AGES else 5 * sum(nat_f[a] for a in ages)
    d["E"] = E; d["T"] = T
    d["logM"] = np.log(E / Enat); d["logC"] = np.log(T / E); d["logT"] = np.log(T / Tnat)
    d["women"] = sum(d["tot_" + a] for a in AGES)
    return d

def shares(d, w=None):
    x, y = d.logM, d.logC
    if w is None: w = np.ones(len(d))
    w = w / w.sum()
    mx, my = (w * x).sum(), (w * y).sum()
    vx = (w * (x - mx) ** 2).sum(); vy = (w * (y - my) ** 2).sum(); cxy = (w * (x - mx) * (y - my)).sum()
    vt = vx + vy + 2 * cxy
    return dict(n=len(d), var_total=float(vt), marriage=float((vx + cxy) / vt), couple=float((vy + cxy) / vt),
                var_M=float(vx), var_C=float(vy), corr=float(cxy / np.sqrt(vx * vy)))

pref = regional(ar[ar.kind == "pref"]); muni = regional(ar[ar.kind == "muni"])
pref.to_csv(RES / "C_pref.csv", index=False); muni.to_csv(RES / "C_muni.csv", index=False)
res["C_pref"] = shares(pref); res["C_muni"] = shares(muni)
res["C_muni_wt"] = shares(muni, muni.women.values.astype(float))
crob = []
for lab, kw in [("基本", {}), ("結婚経験で定義", {"defn": "ever"}), ("20〜39歳だけ", {"ages": AGES[1:5]}), ("素の出生率", {"tfr": "tfr_raw"})]:
    for kind in ["pref", "muni"]:
        dd = regional(ar[ar.kind == kind], **kw)
        dd = dd[np.isfinite(dd.logC) & np.isfinite(dd.logM)]
        s = shares(dd); s.update(setting=lab, kind=kind); crob.append(s)
        if kind == "muni":
            s2 = shares(dd, dd.women.values.astype(float)); s2.update(setting=lab + "（女性の数で重み）", kind=kind); crob.append(s2)
            big = dd[dd.women >= 5000]; s3 = shares(big); s3.update(setting=lab + "（女性15〜49歳が5千人以上）", kind=kind); crob.append(s3)
crob = pd.DataFrame(crob); crob.to_csv(RES / "C_robustness.csv", index=False)
res["C_rob"] = crob[["setting", "kind", "n", "marriage", "couple", "corr"]].to_dict("records")
# 小さい分母：素の出生率とベイズ推定値で、夫婦の要因（logC）のばらつきが人口規模でどう違うか
mr = regional(ar[ar.kind == "muni"], tfr="tfr_raw"); mb = muni
bins = [0, 1000, 3000, 10000, 30000, 1e9]; labs = ["〜1千人", "1千〜3千人", "3千〜1万人", "1万〜3万人", "3万人〜"]
mb["size"] = pd.cut(mb.women, bins, labels=labs); mr["size"] = pd.cut(mr.women, bins, labels=labs)
fun = pd.DataFrame({"size": labs,
                    "n": [int((mb["size"] == l).sum()) for l in labs],
                    "sd_logC_raw": [float(mr.loc[mr["size"] == l, "logC"].replace([np.inf, -np.inf], np.nan).std()) for l in labs],
                    "sd_logC_bayes": [float(mb.loc[mb["size"] == l, "logC"].std()) for l in labs],
                    "sd_logM": [float(mb.loc[mb["size"] == l, "logM"].std()) for l in labs]})
fun.to_csv(RES / "C_funnel_by_size.csv", index=False)
res["C_funnel"] = fun.to_dict("records")
# 並べ替え：logM と logC の相関が偶然か（市区町村）
obs = res["C_muni"]["corr"]
perm = [np.corrcoef(muni.logM, rng.permutation(muni.logC.values))[0, 1] for _ in range(2000)]
res["C_muni_corr_perm_p"] = float((np.abs(perm) >= abs(obs)).mean())
# 人口規模（女性の数）別に、結婚と夫婦の要因の平均（集計値だけ）
grp = mb.groupby("size", observed=True).agg(n=("code", "size"), tfr=("T", "mean"), M=("logM", "mean"), C=("logC", "mean"))
grp["M_ratio"] = np.exp(grp.M); grp["C_ratio"] = np.exp(grp.C)
grp.to_csv(RES / "C_by_size.csv")
res["C_by_size"] = grp.reset_index().astype({"size": str}).to_dict("records")
json.dump(res, open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: res[k] for k in ["A_main_1970_2020", "A_1990_2020", "A_2010_2020", "A_rob_range", "A_2025_marriage_only", "B_main", "B_rob_range", "B_cfr_decomp", "C_pref", "C_muni", "C_muni_wt", "C_muni_corr_perm_p"] if k in res}, ensure_ascii=False, indent=1, default=float))
print(crob[["setting", "kind", "n", "marriage", "couple", "corr"]].round(3).to_string())
print(fun.round(3).to_string()); print(grp.round(3).to_string()); print(evm.round(3).to_string())

# 自前の縮小（F61 と同じ考え方）：素の出生率の logC を、偶然のばらつき（出生数のポアソン分散≒1/出生数）に応じて県の平均へ寄せる
mr2 = mr[np.isfinite(mr.logC)].copy()
mr2["births5"] = 5 * sum(mr2["r" + a[:2]] / 1000 * mr2["tot_" + a] for a in AGES)   # 5年間の出生数の目安
mr2 = mr2[mr2.births5 > 0]
mr2["pref"] = mr2.code.str[:2]
v_samp = 1 / mr2.births5
dev = mr2.logC - mr2.groupby("pref").logC.transform("mean")
tau2 = max(float(dev.var() - v_samp.mean()), 1e-6)
mr2["k"] = tau2 / (tau2 + v_samp)
mr2["logC"] = mr2.groupby("pref").logC.transform("mean") + mr2.k * dev
mr2["logT"] = mr2.logM + mr2.logC
s_eb = shares(mr2); res["C_muni_raw_eb"] = dict(s_eb, tau=float(np.sqrt(tau2)), k_median=float(mr2.k.median()),
    k_small=float(mr2.loc[mr2.women < 1000, "k"].median()), k_big=float(mr2.loc[mr2.women >= 30000, "k"].median()))
crob2 = pd.concat([crob, pd.DataFrame([dict(s_eb, setting="素の出生率＋自前の縮小（F61 の方法）", kind="muni")])], ignore_index=True)
crob2.to_csv(RES / "C_robustness.csv", index=False)
res["C_rob"] = crob2[["setting", "kind", "n", "marriage", "couple", "corr"]].to_dict("records")
json.dump(res, open(RES / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
print("EB", res["C_muni_raw_eb"])
