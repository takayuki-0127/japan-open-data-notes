"""B1：円安は、何か月かけて輸入物価と国内企業物価に伝わるか。VAR（ベクトル自己回帰）のインパルス応答と、輸入物価の「為替要因・契約通貨要因」への分解"""
from common import *
from statsmodels.tsa.api import VAR
M = monthly()
M = M.rename(columns={"FXERM07": "usdjpy", "PRCG20_2600000000": "imp_yen", "PRCG20_2500000000": "imp_cc", "PRCG20_2200000000": "cgpi", "PRCG20_2400000000": "exp_yen"})
M.to_csv(RES / "b1_levels.csv", encoding="utf-8-sig")
g = (np.log(M) .diff() * 100)                      # 前月比（%、対数差）
# 1) 輸入物価（円ベース）の前年比を「為替」と「契約通貨ベースの価格」に分ける：円ベース ≒ 契約通貨ベース × 為替（近似）
y = (np.log(M) - np.log(M.shift(12))) * 100
dec = pd.DataFrame({"imp_yen": y.imp_yen, "fx": y.imp_yen - y.imp_cc, "contract": y.imp_cc, "cgpi": y.cgpi, "usdjpy": y.usdjpy}).dropna()
dec.round(3).to_csv(RES / "b1_decomp.csv", encoding="utf-8-sig")
# 2) VAR：為替 → 輸入物価（契約通貨ベース）→ 輸入物価（円ベース）→ 国内企業物価 の順（コレスキー分解）
S, E = "2000-01", "2026-09"
X = g.loc[S:E, ["imp_cc", "usdjpy", "imp_yen", "cgpi"]].dropna()
sel = VAR(X).select_order(12); p = int(sel.aic) if sel.aic > 0 else 2
res = VAR(X).fit(p); print("lag", p, "n", res.nobs)
irf = res.irf(24)
k = list(X.columns)
shock = k.index("usdjpy"); scale = 1 / irf.orth_irfs[0, shock, shock]   # 為替の1%円安ショックにそろえる
cum = irf.orth_irfs.cumsum(0) * scale
# 信頼区間：残差ブートストラップの累積応答
mc = res.irf_errband_mc(orth=True, repl=500, steps=24, signif=0.05, seed=1, cum=True)
lo, hi = mc[0] * scale, mc[1] * scale
out = pd.DataFrame({"h": range(25), "usdjpy": cum[:, shock, shock], "imp_yen": cum[:, k.index("imp_yen"), shock], "imp_yen_lo": lo[:, k.index("imp_yen"), shock], "imp_yen_hi": hi[:, k.index("imp_yen"), shock],
                    "cgpi": cum[:, k.index("cgpi"), shock], "cgpi_lo": lo[:, k.index("cgpi"), shock], "cgpi_hi": hi[:, k.index("cgpi"), shock]})
sc2 = 1 / irf.orth_irfs[0, 0, 0]; cum2 = irf.orth_irfs.cumsum(0) * sc2
out["cgpi_from_cc"] = cum2[:, k.index("cgpi"), 0]; out["cgpi_from_cc_lo"] = lo[:, k.index("cgpi"), 0] / scale * sc2; out["cgpi_from_cc_hi"] = hi[:, k.index("cgpi"), 0] / scale * sc2
out.round(4).to_csv(RES / "b1_irf.csv", index=False, encoding="utf-8-sig"); print(out.iloc[[0, 1, 3, 6, 12, 24]].round(3))
# 3) 安定性：期間を分けて（2000〜2012 と 2013〜2026）
sub = {}
for a, b in [("2000-01", "2012-12"), ("2013-01", "2026-09")]:
    Xs = g.loc[a:b, k].dropna(); r = VAR(Xs).fit(p); ir = r.irf(24); sc = 1 / ir.orth_irfs[0, shock, shock]; cs = ir.orth_irfs.cumsum(0) * sc
    sub[f"{a[:4]}-{b[:4]}"] = {"imp_yen_12": cs[12, k.index("imp_yen"), shock], "cgpi_12": cs[12, k.index("cgpi"), shock], "cgpi_24": cs[24, k.index("cgpi"), shock]}
print(sub)
peak = dec.loc["2021-01":, "imp_yen"].idxmax()
s = {"var_lag": p, "nobs": res.nobs, "imp_yen_h0": out.imp_yen[0], "imp_yen_h3": out.imp_yen[3], "imp_yen_h12": out.imp_yen[12], "cgpi_h0": out.cgpi[0], "cgpi_h3": out.cgpi[3], "cgpi_h6": out.cgpi[6], "cgpi_h12": out.cgpi[12], "cgpi_h24": out.cgpi[24],
     "cgpi_h12_lo": out.cgpi_lo[12], "cgpi_from_cc_h3": out.cgpi_from_cc[3], "cgpi_from_cc_h12": out.cgpi_from_cc[12], "cgpi_from_cc_h12_lo": out.cgpi_from_cc_lo[12], "cgpi_h12_hi": out.cgpi_hi[12], "usdjpy_h12": out.usdjpy[12],
     "sub_2000_2012_cgpi12": sub["2000-2012"]["cgpi_12"], "sub_2013_2026_cgpi12": sub["2013-2026"]["cgpi_12"], "sub_2000_2012_imp12": sub["2000-2012"]["imp_yen_12"], "sub_2013_2026_imp12": sub["2013-2026"]["imp_yen_12"],
     "peak_month": str(peak), "peak_imp_yen": dec.loc[peak, "imp_yen"], "peak_fx": dec.loc[peak, "fx"], "peak_contract": dec.loc[peak, "contract"], "peak_cgpi": dec.loc[peak, "cgpi"],
     "cgpi_yoy_max_2021": dec.loc["2021-01":, "cgpi"].max(), "cgpi_yoy_max_month": str(dec.loc["2021-01":, "cgpi"].idxmax()),
     "usdjpy_2020_12": M.loc["2020-12", "usdjpy"], "usdjpy_2024_07": M.loc["2024-07", "usdjpy"], "usdjpy_latest": M.usdjpy.dropna().iloc[-1], "latest": str(M.usdjpy.dropna().index[-1]),
     "imp_yen_yoy_latest": dec.imp_yen.iloc[-1], "cgpi_yoy_latest": dec.cgpi.iloc[-1]}
pd.Series(s).to_csv(RES / "b1_summary.csv", header=["value"]); print(pd.Series(s))
pd.DataFrame(sub).T.round(3).to_csv(RES / "b1_subperiods.csv", encoding="utf-8-sig")

# 図1：輸入物価（円ベース）の前年比の分解
d2 = dec.loc["2015-01":]
fig, ax = plt.subplots(figsize=(9.5, 4.4)); x = d2.index.to_timestamp()
ax.bar(x, d2.contract, width=25, color=ORANGE, label="契約通貨ベースの価格（原油・資源など）")
ax.bar(x, d2.fx, width=25, bottom=np.where((d2.fx > 0) == (d2.contract > 0), d2.contract, 0), color=BLUE, label="為替（円安・円高）")
ax.plot(x, d2.imp_yen, color=INK, lw=1.4, label="輸入物価（円ベース）の前年比")
ax.plot(x, d2.cgpi, color=GREEN, lw=2, label="国内企業物価の前年比")
ax.axhline(0, color=INK, lw=0.6); ax.set_ylabel("前年比（%、対数差）"); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
ax.set_title("2022年の輸入物価の上がり方は、資源高と円安の両方。国内企業物価は1割上昇", loc="left", fontsize=12)
fig.text(0.01, -0.04, SOURCE + "（為替要因＝円ベース−契約通貨ベース）", fontsize=7.2, color="#8a8984"); fig.savefig(FIG / "b1_decomp.png"); plt.close(fig)

# 図2：インパルス応答（円安1% と 契約通貨ベースの輸入物価1% の比較）
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True); h = out.h
ax = axs[0]
ax.fill_between(h, out.imp_yen_lo, out.imp_yen_hi, color=LIGHT, alpha=0.5); ax.plot(h, out.imp_yen, color=BLUE, marker="o", ms=3, label="輸入物価（円ベース）")
ax.fill_between(h, out.cgpi_lo, out.cgpi_hi, color="#c6e6d8", alpha=0.7); ax.plot(h, out.cgpi, color=GREEN, marker="o", ms=3, label="国内企業物価")
ax.axhline(0, color=INK, lw=0.6); ax.set_xlabel("月数"); ax.set_ylabel("累積の変化（%）"); ax.legend(frameon=False, fontsize=9, loc="center right")
ax.set_title("ドル円が1%円安になると", loc="left", fontsize=11)
ax = axs[1]
ax.fill_between(h, out.cgpi_from_cc_lo, out.cgpi_from_cc_hi, color="#c6e6d8", alpha=0.7); ax.plot(h, out.cgpi_from_cc, color=GREEN, marker="o", ms=3, label="国内企業物価")
ax.axhline(0, color=INK, lw=0.6); ax.set_xlabel("月数"); ax.legend(frameon=False, fontsize=9, loc="center right")
ax.set_title("輸入物価（契約通貨ベース）が1%上がると", loc="left", fontsize=11)
fig.suptitle(f"国内企業物価への効き方：円安1%は1年で約{out.cgpi[12]:.2f}%、資源など輸入品の値上がり1%は約{out.cgpi_from_cc[12]:.1f}%", x=0.01, ha="left", fontsize=12.5)
fig.text(0.01, -0.04, SOURCE + f"（2000年1月〜2026年9月の前月比で VAR（ラグ{p}）、帯は95%区間）", fontsize=7.2, color="#8a8984"); fig.tight_layout(); fig.savefig(FIG / "b1_irf.png"); plt.close(fig)

# 図3：ドル円と国内企業物価の水準
fig, ax = plt.subplots(figsize=(9, 3.8)); m3 = M.loc["2000-01":]; x3 = m3.index.to_timestamp()
ax.plot(x3, m3.usdjpy, color=BLUE, label="ドル円（円／ドル、左）"); ax.set_ylabel("円／ドル")
ax2 = ax.twinx(); ax2.plot(x3, m3.cgpi, color=GREEN, label="国内企業物価（2020年=100、右）"); ax2.spines["top"].set_visible(False)
ax.legend(frameon=False, loc="upper left", fontsize=9); ax2.legend(frameon=False, loc="upper center", fontsize=9)
ax.set_title("2021年以降、円安と企業物価の上昇が同時に進んだ", loc="left")
fig.text(0.01, -0.05, SOURCE, fontsize=7.2, color="#8a8984"); fig.savefig(FIG / "b1_levels.png"); plt.close(fig)

# 4) 頑健性：変数の順番・ラグを変える
rob = []
for cols in [["imp_cc", "usdjpy", "imp_yen", "cgpi"], ["usdjpy", "imp_cc", "imp_yen", "cgpi"], ["usdjpy", "imp_cc", "cgpi"]]:
    for lag in [2, 6, 12]:
        Xr = g.loc[S:E, cols].dropna(); ir = VAR(Xr).fit(lag).irf(24); oi = ir.orth_irfs.cumsum(0)
        sf, sc_, c = cols.index("usdjpy"), cols.index("imp_cc"), cols.index("cgpi")
        rob.append({"order": " → ".join(cols), "lag": lag, "fx_to_cgpi_12": oi[12, c, sf] / ir.orth_irfs[0, sf, sf], "cc_to_cgpi_12": oi[12, c, sc_] / ir.orth_irfs[0, sc_, sc_]})
rob = pd.DataFrame(rob); rob.round(3).to_csv(RES / "b1_robustness.csv", index=False, encoding="utf-8-sig"); print(rob.round(3))
