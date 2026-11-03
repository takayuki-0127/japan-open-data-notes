"""03a 元記事 008「人が集まっている街は、所得が高い街か？」を今の手順で作り直す。
元の手順：段階的な重回帰（HC3）。今の手順：①都道府県でクラスタした標準誤差 ②条件の組み合わせ512通り（specification curve）
③都道府県を1つずつ外す ④都道府県の中で所得を並べ替える置換検定 ⑤標本と所得の定義を変える。"""
from common import *
import itertools, statsmodels.formula.api as smf

d = load_muni()
d["net_mig"] = (d["A5103"] - d["A5104"]) / d["A2301"] * 1000
lo, hi = d.net_mig.quantile([.01, .99]); d["net_mig_w"] = d.net_mig.clip(lo, hi)
d["inc_res"] = d["C120110"] / d["A2301"] * 100; d["z_inc_res"] = (np.log(d.inc_res) - np.log(d.inc_res).mean()) / np.log(d.inc_res).std()
OTH = [c for c in CONTROLS if c != "log_inc"]

def fit(f, df, cov="cluster", w=None):
    m = smf.wls(f, df, weights=w) if w is not None else smf.ols(f, df)
    if cov == "cluster":
        return m.fit(cov_type="cluster", cov_kwds={"groups": df["pref_code"].values})
    return m.fit(cov_type=cov)

def coef(r, k="z_log_inc"):
    ci = r.conf_int().loc[k]
    return r.params[k], ci[0], ci[1], r.pvalues[k]

# 0) 元の4段階を再現（HC3）し、都道府県クラスタの標準誤差に替える
steps = [("そのまま", "net_mig ~ z_log_inc"), ("＋都道府県", "net_mig ~ z_log_inc + C(pref_code)"),
         ("＋年齢構成", "net_mig ~ z_log_inc + z_old + C(pref_code)"),
         ("＋ほかの条件すべて", "net_mig ~ z_log_inc + " + " + ".join("z_" + c for c in OTH) + " + C(pref_code)")]
rows = []
for name, f in steps:
    for cov in ["HC3", "cluster"]:
        b, l, h, p = coef(fit(f, d, cov)); rows.append({"step": name, "se": cov, "coef": b, "lo": l, "hi": h, "p": p})
st = pd.DataFrame(rows); st.round(4).to_csv(RES / "a_steps_reproduce.csv", index=False, encoding="utf-8-sig")
orig = pd.read_csv(ORIG / "008_a3_steps.csv")
print(st.round(3)); print("original", orig[["model", "coef", "p"]].round(3).values.tolist())

# 1) フルモデルのほかの係数（元記事は「残ったのは大卒と人口密度」）
FULL = steps[-1][1]
r_h, r_c = fit(FULL, d, "HC3"), fit(FULL, d, "cluster")
full = pd.DataFrame([{"var": LABEL[c], "coef": r_h.params["z_" + c], "p_HC3": r_h.pvalues["z_" + c], "p_cluster": r_c.pvalues["z_" + c],
                      "lo_cluster": r_c.conf_int().loc["z_" + c, 0], "hi_cluster": r_c.conf_int().loc["z_" + c, 1]} for c in CONTROLS])
full.round(4).to_csv(RES / "a_full_se.csv", index=False, encoding="utf-8-sig"); print(full.round(3))

# 2) specification curve：ほかの条件の組み合わせ64 × 都道府県の有無2 × 重み2 × 外れ値の扱い2 = 512通り
spec = []
for k in range(len(OTH) + 1):
    for S in itertools.combinations(OTH, k):
        for fe in [False, True]:
            for wt in ["なし", "人口"]:
                for yv in ["net_mig", "net_mig_w"]:
                    f = f"{yv} ~ z_log_inc" + "".join(" + z_" + c for c in S) + (" + C(pref_code)" if fe else "")
                    r = fit(f, d, "cluster", d.A2301 if wt == "人口" else None)
                    b, l, h, p = coef(r)
                    rec = {"n_ctrl": len(S), "old_in": "old" in S, "fe": fe, "weight": wt, "y": yv, "coef": b, "lo": l, "hi": h, "p": p}
                    for c in OTH: rec["c_" + c] = c in S
                    for c in ["univ", "log_density"]:
                        if c in S: rec["b_" + c], rec["p_" + c] = r.params["z_" + c], r.pvalues["z_" + c]
                    spec.append(rec)
sp = pd.DataFrame(spec); sp.round(5).to_csv(RES / "a_spec_curve.csv", index=False, encoding="utf-8-sig")
def share(df):
    return pd.Series({"n": len(df), "median": df.coef.median(), "pos_sig": ((df.coef > 0) & (df.p < .05)).mean(),
                      "neg_sig": ((df.coef < 0) & (df.p < .05)).mean(), "ns": (df.p >= .05).mean()})
sp_sum = pd.concat({"すべて": share(sp), "65歳以上を入れる": share(sp[sp.old_in]), "65歳以上を入れない": share(sp[~sp.old_in]),
                    "元の4条件と同じ形（全部入り・県あり）": share(sp[(sp.n_ctrl == 6) & sp.fe])}, axis=1).T
sp_sum.round(3).to_csv(RES / "a_spec_summary.csv", encoding="utf-8-sig"); print(sp_sum.round(3))
# どの選択肢がばらつきを生むか（係数を選択肢で回帰したときの寄与）
X = pd.get_dummies(sp[["fe", "weight", "y"] + ["c_" + c for c in OTH]].astype(str), drop_first=True).astype(float)
import statsmodels.api as sm
rv = sm.OLS(sp.coef, sm.add_constant(X)).fit()
drivers = pd.DataFrame({"effect": rv.params.drop("const"), "abs": rv.params.drop("const").abs()}).sort_values("abs", ascending=False)
drivers.round(3).to_csv(RES / "a_spec_drivers.csv", encoding="utf-8-sig"); print(drivers.round(3).head(8), rv.rsquared)
# 大卒・人口密度の係数が「はっきりプラス」の割合（入っている指定のうち）
ud = {c: ((sp["b_" + c] > 0) & (sp["p_" + c] < .05))[sp["c_" + c]].mean() for c in ["univ", "log_density"]}
print("univ/density pos sig share", ud)

# 3) 都道府県を1つずつ外す（フルモデル、クラスタ）
loo = []
for pc in sorted(d.pref_code.unique()):
    b, l, h, p = coef(fit(FULL, d[d.pref_code != pc], "cluster")); loo.append({"drop_pref": pc, "coef": b, "lo": l, "hi": h, "p": p})
loo = pd.DataFrame(loo); loo.round(4).to_csv(RES / "a_leave_pref_out.csv", index=False)
print("LOO range", loo.coef.min().round(3), loo.coef.max().round(3), (loo.p < .05).sum())

# 4) 置換検定：都道府県の中で所得を並べ替えて、フルモデルの係数の分布を作る
rng = np.random.default_rng(SEED); perm = []
b0 = r_c.params["z_log_inc"]
for i in range(1000):
    dd = d.copy(); dd["z_log_inc"] = dd.groupby("pref_code")["z_log_inc"].transform(lambda s: rng.permutation(s.values))
    perm.append(smf.ols(FULL, dd).fit().params["z_log_inc"])
perm = np.array(perm); p_perm = (np.abs(perm) >= abs(b0)).mean()
print("perm p", p_perm)

# 5) 標本・定義を変える
alts = {"基本（フル・クラスタ）": (d, FULL),
        "東京23区を除く": (d[~d.ward23], FULL),
        "人口5千人未満を除く": (d[d.A1101 >= 5000], FULL),
        "転入超過の上下1%を除く": (d[d.net_mig.between(lo, hi)], FULL),
        "所得を住民1人あたりにする": (d, FULL.replace("z_log_inc", "z_inc_res"))}
ar = []
for name, (df, f) in alts.items():
    k = "z_inc_res" if "z_inc_res" in f else "z_log_inc"
    b, l, h, p = coef(fit(f, df, "cluster"), k); ar.append({"variant": name, "n": len(df), "coef": b, "lo": l, "hi": h, "p": p})
ar = pd.DataFrame(ar); ar.round(4).to_csv(RES / "a_variants.csv", index=False, encoding="utf-8-sig"); print(ar.round(3))

summ = {"orig_full_coef": orig.coef.iloc[-1], "orig_full_p": orig.p.iloc[-1], "repro_full_coef_HC3": st.query("step=='＋ほかの条件すべて' and se=='HC3'").coef.iloc[0],
        "full_p_cluster": st.query("step=='＋ほかの条件すべて' and se=='cluster'").p.iloc[0],
        "full_lo_cluster": st.query("step=='＋ほかの条件すべて' and se=='cluster'").lo.iloc[0], "full_hi_cluster": st.query("step=='＋ほかの条件すべて' and se=='cluster'").hi.iloc[0],
        "step2_p_cluster": st.query("step=='＋都道府県' and se=='cluster'").p.iloc[0],
        "spec_n": len(sp), "spec_median": sp.coef.median(), "spec_pos_sig": sp_sum.loc["すべて", "pos_sig"], "spec_neg_sig": sp_sum.loc["すべて", "neg_sig"],
        "spec_pos_sig_old_in": sp_sum.loc["65歳以上を入れる", "pos_sig"], "spec_pos_sig_old_out": sp_sum.loc["65歳以上を入れない", "pos_sig"],
        "spec_neg_sig_old_in": sp_sum.loc["65歳以上を入れる", "neg_sig"],
        "drivers_r2": rv.rsquared, "univ_pos_sig_share": ud["univ"], "density_pos_sig_share": ud["log_density"],
        "univ_p_cluster": full.set_index("var").loc["大卒の割合", "p_cluster"], "density_p_cluster": full.set_index("var").loc["人口密度", "p_cluster"],
        "loo_min": loo.coef.min(), "loo_max": loo.coef.max(), "loo_n_sig": int((loo.p < .05).sum()), "perm_p": p_perm,
        "variants_min": ar.coef.min(), "variants_max": ar.coef.max(), "variants_n_sig": int((ar.p < .05).sum())}
pd.Series(summ).to_csv(RES / "a_summary.csv", header=["value"]); print(pd.Series(summ).round(4))
pd.Series(perm).round(5).to_csv(RES / "a_perm.csv", index=False, header=["coef"])
