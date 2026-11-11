"""F240 キャンペーンの効果を、比べる相手がないときにどう測るか？
大阪・関西万博（2025年4〜10月）の期間中、大阪府の日本人延べ宿泊者数はどれだけ増えたのかを、
前年比・中断時系列（ITS）・合成対照・ベイズ構造時系列（CausalImpact 型）・プラセボで比べる。
"""
import json, warnings
from pathlib import Path
import numpy as np, pandas as pd
from scipy.optimize import minimize
import statsmodels.api as sm

warnings.filterwarnings("ignore")
np.random.seed(240)
BASE = Path(__file__).resolve().parents[1]
RES = BASE / "results"; RES.mkdir(exist_ok=True)

d = pd.read_csv(BASE / "data/lodging_pref_monthly_2011_2025.csv", parse_dates=["date"])
TREAT = "27大阪府"
KANSAI = ["25滋賀県", "26京都府", "28兵庫県", "29奈良県", "30和歌山県"]
EXPO = pd.date_range("2025-04-01", "2025-10-01", freq="MS")
AFTER = pd.date_range("2025-11-01", "2025-12-01", freq="MS")
POST = EXPO.append(AFTER)
PRE_B = pd.date_range("2023-01-01", "2025-03-01", freq="MS")          # コロナ後
PRE_A = pd.date_range("2015-01-01", "2019-12-01", freq="MS")          # コロナ前
COVID = pd.date_range("2020-01-01", "2022-12-01", freq="MS")


def wide(col):
    w = d.pivot(index="date", columns="pref", values=col).astype(float)
    return np.log(w)


def sc_fit(Y, treat, donors, pre, post, demean_blocks=None):
    """合成対照：前の期間の（ブロックごとに平均を引いた）対数値を、非負・合計1の重みで合わせる"""
    blocks = demean_blocks or [pre]
    def dm(s):
        out = s.copy()
        for b in blocks:
            out.loc[b] = s.loc[b] - s.loc[b].mean()
        return out
    yt = Y[treat]; Xd = Y[donors]
    # 期間中の値は「直前のブロック（コロナ後）の平均」で引く
    last = blocks[-1]
    yt_dm = dm(yt); Xd_dm = Xd.apply(dm)
    yt_post = yt.loc[post] - yt.loc[last].mean(); Xd_post = Xd.loc[post] - Xd.loc[last].mean()
    prei = pd.DatetimeIndex(np.concatenate([b.values for b in blocks]))
    A = Xd_dm.loc[prei].values; b = yt_dm.loc[prei].values
    n = A.shape[1]
    obj = lambda w: np.mean((A @ w - b) ** 2)
    cons = ({"type": "eq", "fun": lambda w: w.sum() - 1},)
    r = minimize(obj, np.full(n, 1 / n), bounds=[(0, 1)] * n, constraints=cons, method="SLSQP",
                 options={"maxiter": 500, "ftol": 1e-12})
    w = r.x
    pre_gap = b - A @ w
    synth_post = Xd_post.values @ w
    gap_post = yt_post.values - synth_post
    synth_level = np.exp(synth_post + yt.loc[last].mean())  # 合成の水準（人）
    rmspe_pre = np.sqrt(np.mean(pre_gap ** 2))
    return dict(w=pd.Series(w, index=donors), pre_gap=pd.Series(pre_gap, index=prei),
                gap_post=pd.Series(gap_post, index=post), synth_level=pd.Series(synth_level, index=post),
                rmspe_pre=rmspe_pre)


def pct(x):
    return float(np.exp(x) - 1)


def sc_path(Y, treat, donors, blocks, span):
    """図用：span の各月の実際と合成（直前ブロックの平均を基準にした水準）"""
    out = sc_fit(Y, treat, donors, blocks[-1], span, demean_blocks=blocks)
    return out


out = {}
Yj = wide("japanese"); Yt = wide("total"); Yf = wide("foreign")
osaka = d[d.pref == TREAT].set_index("date")
donors_all = [p for p in Yj.columns if p != TREAT]
donors_nok = [p for p in donors_all if p not in KANSAI]

# ---------- A. 素朴な比較（前年同月比） ----------
yoy = (osaka["japanese"] / osaka["japanese"].shift(12) - 1)
nat = d[~d.pref.isin([TREAT])].groupby("date")["japanese"].sum()
nat_yoy = nat / nat.shift(12) - 1
A = pd.DataFrame({"osaka_jp": osaka["japanese"], "osaka_yoy": yoy, "others_yoy": nat_yoy}).loc["2023-01":]
A.to_csv(RES / "A_yoy.csv")
expo_yoy = osaka.loc[EXPO, "japanese"].sum() / osaka.loc[EXPO - pd.DateOffset(years=1), "japanese"].sum() - 1
others_expo_yoy = nat.loc[EXPO].sum() / nat.loc[EXPO - pd.DateOffset(years=1)].sum() - 1
out["A_yoy"] = dict(osaka_expo_yoy=expo_yoy, others_expo_yoy=others_expo_yoy,
                    diff_pt=expo_yoy - others_expo_yoy,
                    osaka_expo_persons=int(osaka.loc[EXPO, "japanese"].sum()),
                    osaka_expo_persons_2024=int(osaka.loc[EXPO - pd.DateOffset(years=1), "japanese"].sum()))

# ---------- B. 中断時系列（大阪だけ） ----------
def its(y, fit_idx, pred_idx, extra_level=None):
    df = pd.DataFrame({"y": y})
    df["t"] = np.arange(len(df)) / 12.0
    for m in range(2, 13):
        df[f"m{m}"] = (df.index.month == m).astype(float)
    cols = ["t"] + [f"m{m}" for m in range(2, 13)]
    if extra_level is not None:
        df["post_covid"] = (df.index >= extra_level).astype(float); cols.append("post_covid")
    X = sm.add_constant(df[cols])
    m = sm.OLS(df.loc[fit_idx, "y"], X.loc[fit_idx]).fit()
    pr = m.get_prediction(X.loc[pred_idx]).summary_frame(alpha=0.05)
    gap = df.loc[pred_idx, "y"] - pr["mean"]
    # 平均の効果の区間：obs_ci（予測区間）を月ごとに使い、平均では残差の自己相関を無視しない近似として
    # 予測の平均の分散 = 平均の推定の分散 + σ²/n
    Xp = X.loc[pred_idx].values; cov = m.cov_params().values
    xbar = Xp.mean(0); var_mean = xbar @ cov @ xbar + m.scale / len(pred_idx)
    eff = gap.mean(); se = np.sqrt(var_mean)
    return dict(gap=gap, pred=pr, eff=eff, lo=eff - 1.96 * se, hi=eff + 1.96 * se, model=m)

ly = np.log(osaka["japanese"].astype(float))
itsB = its(ly, PRE_B, POST)
itsL = its(ly, PRE_A.append(PRE_B), POST, extra_level=pd.Timestamp("2023-01-01"))
out["B_its"] = {
    "pre_2023_25": dict(eff=pct(itsB["eff"]), lo=pct(itsB["lo"]), hi=pct(itsB["hi"]),
                        expo_eff=pct(itsB["gap"].loc[EXPO].mean())),
    "pre_2015_19_2023_25": dict(eff=pct(itsL["eff"]), lo=pct(itsL["lo"]), hi=pct(itsL["hi"]),
                                expo_eff=pct(itsL["gap"].loc[EXPO].mean())),
}
# 期間中だけの区間
for k, r, fit in [("pre_2023_25", itsB, PRE_B), ("pre_2015_19_2023_25", itsL, PRE_A.append(PRE_B))]:
    rr = its(ly, fit, EXPO, extra_level=(pd.Timestamp("2023-01-01") if "2015" in k else None))
    out["B_its"][k].update(expo_eff=pct(rr["eff"]), expo_lo=pct(rr["lo"]), expo_hi=pct(rr["hi"]))
pd.DataFrame({"actual": ly.loc[POST], "its_B": itsB["pred"]["mean"], "its_B_lo": itsB["pred"]["obs_ci_lower"],
              "its_B_hi": itsB["pred"]["obs_ci_upper"], "its_L": itsL["pred"]["mean"]}).to_csv(RES / "B_its.csv")

# ---------- C. 合成対照 ----------
def sc_summary(Y, treat, donors, blocks, label):
    r = sc_fit(Y, treat, donors, blocks[-1], POST, demean_blocks=blocks)
    g = r["gap_post"]
    act = np.exp(Y.loc[EXPO, treat]).sum(); syn = r["synth_level"].loc[EXPO].sum()
    return r, dict(label=label, expo_eff=pct(g.loc[EXPO].mean()), after_eff=pct(g.loc[AFTER].mean()),
                   persons=float(act - syn), rmspe_pre=r["rmspe_pre"],
                   ratio=float(np.sqrt(np.mean(g.loc[EXPO] ** 2)) / r["rmspe_pre"]),
                   top_w={k: round(float(v), 3) for k, v in r["w"].sort_values(ascending=False).head(5).items() if v > 0.005})

scm, scm_s = sc_summary(Yj, TREAT, donors_nok, [PRE_B], "主：日本人・関西を除く対照・2023-01〜2025-03")
C = [scm_s]
for Y, dn, bl, lab in [
    (Yj, donors_all, [PRE_B], "日本人・関西も対照に入れる"),
    (Yj, donors_nok, [PRE_A, PRE_B], "日本人・前の期間に2015〜19年も入れる"),
    (Yj, [p for p in donors_nok if p != "13東京都"], [PRE_B], "日本人・東京も除く"),
    (Yt, donors_nok, [PRE_B], "総数（日本人＋外国人）"),
    (Yf, donors_nok, [PRE_B], "外国人"),
]:
    C.append(sc_summary(Y, TREAT, dn, bl, lab)[1])
pd.DataFrame(C).to_csv(RES / "C_sc_variants.csv", index=False)
out["C_sc"] = C
# 図用の経路（2023-01〜2025-12、主の重みで）
w = scm["w"]
span = PRE_B.append(POST)
base_t = Yj.loc[PRE_B, TREAT].mean(); base_d = Yj.loc[PRE_B, donors_nok].mean()
synth_path = (Yj.loc[span, donors_nok] - base_d) @ w.values + base_t
pd.DataFrame({"actual": np.exp(Yj.loc[span, TREAT]), "synth": np.exp(synth_path)}).to_csv(RES / "C_sc_path.csv")

# ---------- D. プラセボ（場所） ----------
pl = []
pool = donors_nok + [TREAT]
for p in pool:
    dn = [q for q in pool if q != p]
    r = sc_fit(Yj, p, dn, PRE_B, POST)
    ge = r["gap_post"].loc[EXPO]
    pl.append(dict(pref=p, rmspe_pre=r["rmspe_pre"], expo_eff=pct(ge.mean()),
                   ratio=float(np.sqrt(np.mean(ge ** 2)) / r["rmspe_pre"]),
                   gaps=[float(x) for x in np.concatenate([r["pre_gap"].values, r["gap_post"].values])]))
P = pd.DataFrame(pl)
P["rank_ratio"] = P["ratio"].rank(ascending=False)
P["rank_eff"] = P["expo_eff"].rank(ascending=False)
os_row = P[P.pref == TREAT].iloc[0]
out["D_placebo_space"] = dict(n=len(P), osaka_rank_ratio=int(os_row.rank_ratio), osaka_rank_eff=int(os_row.rank_eff),
                              p_ratio=float(os_row.rank_ratio / len(P)), p_eff=float(os_row.rank_eff / len(P)),
                              # 合わせの悪い県（前の期間の外れが大阪の2倍超）を除いた版
                              n_good=int((P.rmspe_pre <= 2 * os_row.rmspe_pre).sum()),
                              rank_eff_good=int(P[P.rmspe_pre <= 2 * os_row.rmspe_pre]["expo_eff"].rank(ascending=False)[P.pref == TREAT].iloc[0]))
P.drop(columns="gaps").to_csv(RES / "D_placebo_space.csv", index=False)
np.save(RES / "D_placebo_gaps.npy", np.array([g for g in P.gaps]))
json.dump({"prefs": P.pref.tolist(), "index": [str(x.date()) for x in PRE_B.append(POST)]},
          open(RES / "D_placebo_gaps_index.json", "w"), ensure_ascii=False)

# ---------- E. プラセボ（時期）：2024年4〜10月に「やった」ことにする ----------
FAKE = pd.date_range("2024-04-01", "2024-10-01", freq="MS")
PRE_F = pd.date_range("2023-01-01", "2024-03-01", freq="MS")
rf = sc_fit(Yj, TREAT, donors_nok, PRE_F, FAKE)
itf = its(ly, PRE_F, FAKE)
out["E_placebo_time"] = dict(sc_eff=pct(rf["gap_post"].mean()), its_eff=pct(itf["eff"]), its_lo=pct(itf["lo"]), its_hi=pct(itf["hi"]),
                             yoy_osaka=float(osaka.loc[FAKE, "japanese"].sum() / osaka.loc[FAKE - pd.DateOffset(years=1), "japanese"].sum() - 1),
                             yoy_others=float(nat.loc[FAKE].sum() / nat.loc[FAKE - pd.DateOffset(years=1)].sum() - 1))
# 2023年4〜10月（コロナ後の回復期）にも
FAKE2 = pd.date_range("2023-04-01", "2023-10-01", freq="MS")
yoy23 = float(osaka.loc[FAKE2, "japanese"].sum() / osaka.loc[FAKE2 - pd.DateOffset(years=1), "japanese"].sum() - 1)
yoy23o = float(nat.loc[FAKE2].sum() / nat.loc[FAKE2 - pd.DateOffset(years=1)].sum() - 1)
out["E_placebo_time"].update(yoy_osaka_2023=yoy23, yoy_others_2023=yoy23o)

# ---------- F. ベイズ構造時系列（CausalImpact 型） ----------
def bsts(y_log, x_log, fit_end, post, covid=COVID, seed=240):
    yy = y_log.copy().loc["2015-01":]
    xx = x_log.loc[yy.index]
    yy.loc[yy.index.isin(covid)] = np.nan
    yy.loc[post] = np.nan
    mod = sm.tsa.UnobservedComponents(yy, level="local level", freq_seasonal=[{"period": 12, "harmonics": 3}],
                                      exog=xx.values.reshape(-1, 1))
    res = mod.fit(disp=False, maxiter=200)
    pr = res.get_prediction(start=post[0], end=post[-1])
    sf = pr.summary_frame(alpha=0.05)
    # 期間全体の平均の区間：予測分布からシミュレーション
    rng = np.random.default_rng(seed)
    mu = pr.predicted_mean.values; cov = pr.var_pred_mean if hasattr(pr, "var_pred_mean") else None
    # 同時分布の代わりに、状態の不確かさを月で完全相関・独立の2通りで挟む
    sd = np.sqrt(pr.var_pred_mean.values)
    act = y_log.loc[post].values
    gap = act - mu
    m_eff = gap.mean()
    lo_ind = m_eff - 1.96 * np.sqrt(np.mean(sd ** 2) / len(sd)); hi_ind = m_eff + 1.96 * np.sqrt(np.mean(sd ** 2) / len(sd))
    lo_cor = m_eff - 1.96 * sd.mean(); hi_cor = m_eff + 1.96 * sd.mean()
    return dict(sf=sf, gap=pd.Series(gap, index=post), eff=m_eff, lo=lo_cor, hi=hi_cor, lo_ind=lo_ind, hi_ind=hi_ind,
                params=res.params.to_dict())

ctrl = np.log(d[d.pref.isin(donors_nok)].groupby("date")["japanese"].sum().astype(float))
bs = bsts(ly, ctrl, "2025-03", EXPO)
out["F_bsts"] = dict(eff=pct(bs["eff"]), lo=pct(bs["lo"]), hi=pct(bs["hi"]), lo_ind=pct(bs["lo_ind"]), hi_ind=pct(bs["hi_ind"]),
                     beta=float([v for k, v in bs["params"].items() if "beta" in k or "x1" in k][0]))
bs_noctrl = bsts(ly, ctrl * 0, "2025-03", EXPO)
out["F_bsts"]["no_control"] = dict(eff=pct(bs_noctrl["eff"]), lo=pct(bs_noctrl["lo"]), hi=pct(bs_noctrl["hi"]))
bs_fake = bsts(ly, ctrl, "2024-03", FAKE)
out["F_bsts"]["placebo_2024"] = dict(eff=pct(bs_fake["eff"]), lo=pct(bs_fake["lo"]), hi=pct(bs_fake["hi"]))
pd.DataFrame({"actual": ly.loc[EXPO], "pred": bs["sf"]["mean"], "lo": bs["sf"]["mean_ci_lower"], "hi": bs["sf"]["mean_ci_upper"]}).to_csv(RES / "F_bsts.csv")

# ---------- G. 周りの府県への波及（大阪と関西を除いた対照で） ----------
G = []
for p in KANSAI:
    r = sc_fit(Yj, p, donors_nok, PRE_B, POST)
    G.append(dict(pref=p, expo_eff=pct(r["gap_post"].loc[EXPO].mean()), rmspe_pre=r["rmspe_pre"]))
pd.DataFrame(G).to_csv(RES / "G_spillover.csv", index=False)
out["G_spillover"] = G

# ---------- 月ごとの効果（主の合成対照） ----------
M = pd.DataFrame({"actual": np.exp(Yj.loc[POST, TREAT]), "synth": scm["synth_level"],
                  "eff_pct": np.exp(scm["gap_post"]) - 1, "its_pct": np.exp(itsB["gap"]) - 1,
                  "bsts_pct": pd.concat([np.exp(bs["gap"]) - 1, pd.Series(np.nan, index=AFTER)])})
M["persons"] = M["actual"] - M["synth"]
M.to_csv(RES / "M_monthly.csv")
out["M_monthly"] = {str(k.date()): {kk: (None if pd.isna(vv) else float(vv)) for kk, vv in v.items()} for k, v in M.iterrows()}

json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: v for k, v in out.items() if k != "M_monthly"}, ensure_ascii=False, indent=1, default=float)[:6000])
