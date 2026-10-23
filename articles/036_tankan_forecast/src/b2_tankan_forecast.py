"""B2：短観の「先行き」（予測DI）は、3か月後の実績をどれくらい当てているか。予測誤差・かたより（バイアス）・素朴な予測との比較・Mincer–Zarnowitz 回帰"""
from common import *
import statsmodels.formula.api as smf
Q = quarterly()
G = {"大企業・製造業": ("TK99F1000601GCQ01000", "TK99F1000601GCQ11000"), "大企業・非製造業": ("TK99F2000601GCQ01000", "TK99F2000601GCQ11000"),
     "中小企業・製造業": ("TK99F1000601GCQ03000", "TK99F1000601GCQ13000"), "中小企業・非製造業": ("TK99F2000601GCQ03000", "TK99F2000601GCQ13000")}
S = pd.Period("1990Q1", "Q"); E = Q.index.max()
rows, paths = [], {}
for nm, (a, f) in G.items():
    d = pd.DataFrame({"actual": Q[a], "fcst": Q[f]})          # 予測は「対象の四半期」の行に入っている（前の四半期の調査で答えたもの）
    d["prev"] = d.actual.shift(1)                              # 素朴な予測：前の四半期の実績がそのまま続く
    d = d.loc[S:].dropna()
    d["err"] = d.actual - d.fcst; d["err_naive"] = d.actual - d.prev
    d["chg_true"] = d.actual - d.prev; d["chg_fcst"] = d.fcst - d.prev
    mz = smf.ols("actual ~ fcst", d).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
    tst = mz.f_test("Intercept = 0, fcst = 1")
    bias = smf.ols("err ~ 1", d).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
    # 方向：前の四半期から良くなるか悪くなるか（予測の変化 ≠ 0 のとき）
    nz = d[(d.chg_fcst != 0) & (d.chg_true != 0)]
    hit = (np.sign(nz.chg_fcst) == np.sign(nz.chg_true)).mean()
    rows.append({"group": nm, "n": len(d), "mae": d.err.abs().mean(), "mae_naive": d.err_naive.abs().mean(), "rmse": np.sqrt((d.err ** 2).mean()), "rmse_naive": np.sqrt((d.err_naive ** 2).mean()),
                 "bias": d.err.mean(), "bias_p": bias.pvalues.iloc[0], "share_actual_above": (d.err > 0).mean(), "mz_a": mz.params.Intercept, "mz_b": mz.params.fcst, "mz_joint_p": float(tst.pvalue),
                 "dir_hit": hit, "n_dir": len(nz), "corr_chg": np.corrcoef(d.chg_fcst, d.chg_true)[0, 1]})
    paths[nm] = d
E = max(p.index.max() for p in paths.values())
T = pd.DataFrame(rows); T.round(3).to_csv(RES / "b2_accuracy.csv", index=False, encoding="utf-8-sig"); print(T.round(2).to_string())
# 大きく外れた四半期（大企業・製造業）
d = paths["大企業・製造業"]; big = d.reindex(d.err.abs().sort_values(ascending=False).index).head(8)
big.to_csv(RES / "b2_big_misses_large_mfg.csv", encoding="utf-8-sig"); print(big[["actual", "fcst", "prev", "err"]])
# 期間別のかたより
per = []
for nm, d in paths.items():
    for a, b in [("1990Q1", "1999Q4"), ("2000Q1", "2009Q4"), ("2010Q1", "2019Q4"), ("2020Q1", str(E))]:
        x = d.loc[a:b]; per.append({"group": nm, "period": f"{a[:4]}–{b[:4]}", "bias": x.err.mean(), "mae": x.err.abs().mean(), "n": len(x)})
per = pd.DataFrame(per); per.round(2).to_csv(RES / "b2_bias_by_period.csv", index=False, encoding="utf-8-sig"); print(per.pivot(index="group", columns="period", values="bias").round(2))
latest = {nm: {"q": str(p.index[-1]), "actual": p.actual.iloc[-1]} for nm, p in paths.items()}
nxt = {nm: Q[f].dropna() for nm, (a, f) in G.items()}
s = {"period": f"{S}–{E}", "n_quarters": len(paths["大企業・製造業"]), "large_mfg_bias": T.set_index("group").loc["大企業・製造業", "bias"], "large_mfg_mae": T.set_index("group").loc["大企業・製造業", "mae"], "large_mfg_mae_naive": T.set_index("group").loc["大企業・製造業", "mae_naive"],
     "small_nonmfg_bias": T.set_index("group").loc["中小企業・非製造業", "bias"], "large_mfg_last_fcst_q": str(nxt["大企業・製造業"].index[-1]), "large_mfg_last_fcst": nxt["大企業・製造業"].iloc[-1],
     "large_mfg_last_actual_q": latest["大企業・製造業"]["q"], "large_mfg_last_actual": latest["大企業・製造業"]["actual"]}
pd.Series(s).to_csv(RES / "b2_summary.csv", header=["value"]); print(pd.Series(s))

SRC = SOURCE + "（短観 業況判断DI）"
d = paths["大企業・製造業"]
fig, ax = plt.subplots(figsize=(9.5, 4.2)); x = d.index.to_timestamp()
ax.plot(x, d.actual, color=INK, lw=1.6, label="実績")
ax.plot(x, d.fcst, color=ORANGE, lw=1.2, ls="--", label="3か月前の予測（先行き）")
ax.axhline(0, color=INK, lw=0.5); ax.set_ylabel("業況判断DI（%ポイント）"); ax.legend(frameon=False, loc="lower left")
ax.set_title("大企業・製造業：予測は実績のあとを追い、大きな変化には遅れる", loc="left")
fig.text(0.01, -0.04, SRC, fontsize=7.2, color="#8a8984"); fig.savefig(FIG / "b2_path.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 4)); yy = np.arange(len(T)); w = 0.36
ax.barh(yy - w / 2, T.mae, w, color=ORANGE, label="短観の予測（先行き）"); ax.barh(yy + w / 2, T.mae_naive, w, color=GRAY, label="「前の四半期と同じ」とする素朴な予測")
for i, (a_, b_) in enumerate(zip(T.mae, T.mae_naive)): ax.text(a_ + 0.1, i - w / 2, f"{a_:.1f}", va="center", fontsize=9); ax.text(b_ + 0.1, i + w / 2, f"{b_:.1f}", va="center", fontsize=9)
ax.set_yticks(yy, T.group); ax.invert_yaxis(); ax.set_xlabel("平均絶対誤差（%ポイント）"); ax.legend(frameon=False, fontsize=9, loc="lower right")
ax.set_title("製造業では素朴な予測より当たり、非製造業では素朴な予測に負ける", loc="left")
fig.text(0.01, -0.05, SRC + f"（{S}〜{E}）", fontsize=7.2, color="#8a8984"); fig.savefig(FIG / "b2_mae.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 4)); bp = per.pivot(index="period", columns="group", values="bias")[list(G)]
bp.plot(kind="bar", ax=ax, color=[BLUE, LIGHT, ORANGE, "#f4b393"], width=0.8, rot=0)
ax.axhline(0, color=INK, lw=0.7); ax.set_ylabel("実績 − 予測 の平均（%ポイント）"); ax.set_xlabel(""); ax.legend(frameon=False, fontsize=8.5, ncol=2)
ax.set_title("1990年代は予測が楽観的、2010年代からは実績が予測を上回りがち", loc="left")
fig.text(0.01, -0.05, SRC, fontsize=7.2, color="#8a8984"); fig.savefig(FIG / "b2_bias.png"); plt.close(fig)
