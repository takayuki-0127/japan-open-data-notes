"""03 分析：石川・富山の日本人延べ宿泊者数への効果を、SCM・SDID・ASCM・単純な差の差・構造時系列で推定"""
import json
import numpy as np, pandas as pd
import statsmodels.api as sm
from common import *

np.random.seed(SEED)
W = {c: load_panel(c) for c in ["japanese", "foreign", "total"]}
PREFS = list(W["japanese"].columns)
donors = [p for p in PREFS if p not in TREATED + BASE_EXCL]
print("対照県", len(donors))
out = {"donors": donors}

def run_all(y, tr, donors, open_=OPEN):
    s, a, d = scm(y, tr, donors, open_), ascm(y, tr, donors, open_), did(y, tr, donors, open_)
    sd = sdid(y, tr, donors, open_)
    return dict(SCM=s, SDID=sd, ASCM=a, DID=d)

def to_people(wide, tr, gap, open_=OPEN, post1=POST1):
    act = wide.loc[open_:post1, tr]
    g = gap.loc[open_:post1]
    cf = act * np.exp(-g)
    return float((act - cf).sum()), float(cf.sum()), float(act.sum())

# ---- 1. 基本：日本人、石川・富山
y = prep(W["japanese"])
main = {}
rows = []
for tr in TREATED:
    R = run_all(y, tr, donors)
    main[tr] = R
    for m, r in R.items():
        gap = r["gap"]
        add, cf, act = to_people(W["japanese"], tr, gap)
        first = gap.loc["2015-03":"2016-02"].mean()
        rows.append(dict(pref=tr, method=m, att_log=r["att"], att_pct=np.expm1(r["att"]) * 100,
                         first_year_pct=np.expm1(first) * 100, add_nights=add, cf_nights=cf, act_nights=act,
                         pre_rmse=float(np.sqrt((gap[gap.index < OPEN] ** 2).mean()))))
# 石川＋富山 をまとめた SDID
sd2 = sdid(y, TREATED, donors)
rows.append(dict(pref="石川＋富山", method="SDID", att_log=sd2["att"], att_pct=np.expm1(sd2["att"]) * 100))
est = pd.DataFrame(rows); est.to_csv(RES / "estimates_main.csv", index=False)
print(est.round(3).to_string())

# 年ごとの効果（石川、各手法）
yr = []
for m, r in main["石川"].items():
    g = r["gap"].loc[OPEN:POST1]
    for Y, v in g.groupby(g.index.year).mean().items():
        yr.append(dict(method=m, year=Y, pct=np.expm1(v) * 100))
pd.DataFrame(yr).to_csv(RES / "effect_by_year_ishikawa.csv", index=False)
# 系列（図用）
ser = pd.DataFrame({"actual": y["石川"]})
for m, r in main["石川"].items():
    if "synth" in r: ser[m] = r["synth"]
ser["DID_gap"] = main["石川"]["DID"]["gap"]
ser.to_csv(RES / "series_ishikawa.csv")
ser_t = pd.DataFrame({"actual": y["富山"]})
for m in ["SCM", "SDID", "ASCM"]: ser_t[m] = main["富山"][m]["synth"]
ser_t.to_csv(RES / "series_toyama.csv")
# 重み
wt = pd.DataFrame({f"{tr}_{m}": main[tr][m]["w"] for tr in TREATED for m in ["SCM", "SDID"]}).fillna(0)
wt.to_csv(RES / "donor_weights.csv")
pd.Series(main["石川"]["SDID"]["lam"]).to_csv(RES / "sdid_time_weights_ishikawa.csv")
out["ascm_alpha"] = {tr: float(main[tr]["ASCM"]["alpha"]) for tr in TREATED}

# ---- 2. プラセボ（対照県を1つずつ処置とみなす）
pl = []
for p in donors:
    others = [q for q in donors if q != p]
    s = scm(y, p, others); a = ascm(y, p, others, alpha=out["ascm_alpha"]["石川"]); sd = sdid(y, p, others)
    pl.append(dict(pref=p, SCM=s["att"], ASCM=a["att"], SDID=sd["att"],
                   ratio=s["post_rmse"] / s["pre_rmse"], pre_rmse=s["pre_rmse"]))
pl = pd.DataFrame(pl)
for tr in TREATED:
    s = main[tr]["SCM"]
    pl = pd.concat([pl, pd.DataFrame([dict(pref=tr, SCM=s["att"], ASCM=main[tr]["ASCM"]["att"], SDID=main[tr]["SDID"]["att"],
                                           ratio=s["post_rmse"] / s["pre_rmse"], pre_rmse=s["pre_rmse"])])])
pl.to_csv(RES / "placebo_in_space.csv", index=False)
plc = pl[~pl.pref.isin(TREATED)]
inf = {}
for tr in TREATED:
    r = pl[pl.pref == tr].iloc[0]
    inf[tr] = {m: dict(att_pct=float(np.expm1(r[m]) * 100),
                       rank=int((plc[m] >= r[m]).sum() + 1), n=int(len(plc) + 1),
                       p_one_sided=float(((plc[m] >= r[m]).sum() + 1) / (len(plc) + 1)),
                       placebo_sd_pct=float(np.std(np.expm1(plc[m]) * 100, ddof=1)))
               for m in ["SCM", "ASCM", "SDID"]}
    inf[tr]["ratio_rank"] = int((plc.ratio >= r.ratio).sum() + 1)
    # SDID のプラセボ分散による標準誤差（Arkhangelsky ほか の placebo 法）
    se = float(np.std(plc.SDID, ddof=1))
    inf[tr]["SDID_ci_pct"] = [float(np.expm1(r.SDID - 1.96 * se) * 100), float(np.expm1(r.SDID + 1.96 * se) * 100)]
out["inference"] = inf
print(json.dumps(inf, ensure_ascii=False, indent=1))

# 時間のプラセボ：2013年3月に開業したことにする（事後は2013/3〜2015/2）
yt = prep(W["japanese"], pre0=pd.Timestamp("2011-03-01"), post1=pd.Timestamp("2015-02-01"), open_=pd.Timestamp("2013-03-01"))
tp = {}
for tr in TREATED:
    R = run_all(yt, tr, donors, open_=pd.Timestamp("2013-03-01"))
    tp[tr] = {m: float(np.expm1(r["att"]) * 100) for m, r in R.items()}
out["placebo_in_time_2013"] = tp

# ---- 3. 頑健性（石川・SDID と SCM と ASCM）
def variant(name, wide=W["japanese"], dn=donors, pre0=PRE0, post1=POST1):
    yy = prep(wide, pre0=pre0, post1=post1)
    R = run_all(yy, "石川", dn)
    return dict(variant=name, **{m: float(np.expm1(R[m]["att"]) * 100) for m in ["SCM", "SDID", "ASCM", "DID"]})
rb = [variant("基本（日本人・33県・事前2012/1〜）")]
rb.append(variant("福井も対照に入れる", dn=donors + ["福井"]))
rb.append(variant("東北3県も対照に入れる", dn=donors + EXCL_QUAKE))
rb.append(variant("九州新幹線の4県も入れる", dn=donors + EXCL_KYUSHU))
big = ["東京", "大阪", "京都", "神奈川", "愛知", "千葉", "沖縄"]
rb.append(variant("大都市・沖縄を除く", dn=[d for d in donors if d not in big]))
rb.append(variant("近畿・中部・北陸の近い県だけ", dn=[d for d in donors if d in ["岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山", "山梨"]]))
rb.append(variant("事前を2011/1からにする", pre0=pd.Timestamp("2011-01-01")))
rb.append(variant("事前を2013/1からにする", pre0=pd.Timestamp("2013-01-01")))
rb.append(variant("事後を2016/2まで（1年）", post1=pd.Timestamp("2016-02-01")))
rb.append(variant("外国人を含む（総数）", wide=W["total"]))
rb.append(variant("外国人だけ", wide=W["foreign"]))
rb = pd.DataFrame(rb); rb.to_csv(RES / "robustness_ishikawa.csv", index=False)
print(rb.round(1).to_string())
# 総数・外国人の人泊
for col in ["total", "foreign"]:
    yy = prep(W[col]); R = run_all(yy, "石川", donors)
    out[f"ishikawa_{col}"] = {m: dict(pct=float(np.expm1(R[m]["att"]) * 100),
                                      add=to_people(W[col], "石川", R[m]["gap"])[0]) for m in ["SCM", "SDID", "ASCM"]}

# 一つ抜き（SCM の重みが大きい県を1つずつ外す）
w_s = main["石川"]["SCM"]["w"].sort_values(ascending=False)
loo = []
for p in w_s[w_s > 0.01].index:
    dn = [d for d in donors if d != p]
    R = run_all(y, "石川", dn)
    loo.append(dict(drop=p, weight=float(w_s[p]), **{m: float(np.expm1(R[m]["att"]) * 100) for m in ["SCM", "SDID", "ASCM"]}))
pd.DataFrame(loo).to_csv(RES / "leave_one_out_ishikawa.csv", index=False)

# ---- 4. F04 と同じ流儀：構造時系列（局所水準＋対照県平均を説明変数、最尤）
ci = {}
for tr in TREATED:
    yy = prep(W["japanese"])
    x = yy[donors].mean(axis=1)
    pre = yy.index < OPEN; npost = int((~pre).sum())
    mod = sm.tsa.UnobservedComponents(yy.loc[pre, tr].values, level="local level", exog=x[pre].values)
    res = mod.fit(disp=False)
    fc = res.get_forecast(steps=npost, exog=x[~pre].values.reshape(-1, 1))
    mean = fc.predicted_mean; ci_ = fc.conf_int(alpha=0.05)
    g = yy.loc[~pre, tr].values - mean
    # 平均の効果の区間：シミュレーション
    sims = res.simulate(nsimulations=npost, repetitions=2000, anchor="end", exog=x[~pre].values.reshape(-1, 1))
    sims = np.asarray(sims).reshape(npost, -1)
    eff = yy.loc[~pre, tr].values[:, None] - sims
    m_eff = eff.mean(axis=0)
    ci[tr] = dict(att_pct=float(np.expm1(g.mean()) * 100),
                  ci_pct=[float(np.expm1(np.percentile(m_eff, 2.5)) * 100), float(np.expm1(np.percentile(m_eff, 97.5)) * 100)],
                  beta=float(res.params[-1]))
    if tr == "石川":
        pd.DataFrame({"date": yy.index[~pre], "actual": yy.loc[~pre, tr].values, "pred": mean,
                      "lo": ci_[:, 0], "hi": ci_[:, 1]}).to_csv(RES / "bsts_ishikawa.csv", index=False)
out["structural_ts"] = ci
print(json.dumps(ci, ensure_ascii=False))

# 事前期間の水準：2014年の石川・富山の日本人宿泊（参考）
for tr in TREATED:
    a = W["japanese"][tr]
    out[f"{tr}_nights"] = {str(Y): int(a[str(Y)].sum()) for Y in [2013, 2014, 2015, 2016, 2019]}
json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
