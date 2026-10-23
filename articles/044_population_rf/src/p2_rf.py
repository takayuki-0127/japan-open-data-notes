"""P2：2050年の推計人口（2020年＝100）は、市町村のどんな特徴で決まっているか。ランダムフォレストと重回帰で比べ、並べ替え重要度と部分依存で読む"""
from common import *
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.inspection import permutation_importance, partial_dependence
d = pd.read_csv(RES / "p1_munis.csv", dtype={"code": str}).set_index("code")
h = pd.read_csv(RAW / "SSDSE-A-2026.csv", encoding="cp932", header=None, nrows=3)
a = pd.read_csv(RAW / "SSDSE-A-2026.csv", encoding="cp932", header=None, skiprows=3); a.columns = list(h.iloc[0])
lab = dict(zip(h.iloc[0], h.iloc[2])); code = {v: k for k, v in lab.items()}
a["code"] = a["SSDSE-A-2026"].str[1:]; a = a.set_index("code")
g = lambda n: pd.to_numeric(a[code[n]], errors="coerce")
pop = g("総人口")
X = pd.DataFrame({
    "人口（対数）": np.log(pop),
    "65歳以上の割合": g("65歳以上人口") / pop * 100,
    "15歳未満の割合": g("15歳未満人口") / pop * 100,
    "出生数（人口千人あたり）": g("出生数") / pop * 1000,
    "転入超過（人口千人あたり）": (g("転入者数（日本人移動者）") - g("転出者数（日本人移動者）")) / pop * 1000,
    "可住地の人口密度（対数）": np.log(pop / g("可住地面積").replace(0, np.nan)),
    "第1次産業の就業者割合": g("第1次産業就業者数") / g("就業者数") * 100,
    "第3次産業の就業者割合": g("第3次産業就業者数") / g("就業者数") * 100,
    "単独世帯の割合": g("単独世帯数") / g("一般世帯数") * 100,
    "外国人の割合": g("外国人人口") / pop * 100,
})
df = d[["muni", "pref", "idx"]].join(X, how="inner").dropna()
print(len(df), "of", len(d))
F = list(X.columns); y = df.idx.values; Xv = df[F].values
kf = KFold(5, shuffle=True, random_state=0)
rf = RandomForestRegressor(n_estimators=500, min_samples_leaf=5, random_state=0, n_jobs=-1)
lr = LinearRegression()
p_rf = cross_val_predict(rf, Xv, y, cv=kf); p_lr = cross_val_predict(lr, Xv, y, cv=kf)
rmse = lambda p: float(np.sqrt(((y - p) ** 2).mean()))
r2 = lambda p: 1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum()
ev = pd.DataFrame({"model": ["平均で当てる", "重回帰", "ランダムフォレスト"], "rmse": [rmse(np.full_like(y, y.mean())), rmse(p_lr), rmse(p_rf)], "r2": [0, r2(p_lr), r2(p_rf)]})
ev.round(3).to_csv(RES / "p2_cv.csv", index=False, encoding="utf-8-sig"); print(ev.round(3))
rf.fit(Xv, y)
pi = permutation_importance(rf, Xv, y, n_repeats=20, random_state=0, scoring="neg_root_mean_squared_error")
imp = pd.DataFrame({"feature": F, "importance": pi.importances_mean, "sd": pi.importances_std}).sort_values("importance", ascending=False)
imp.round(3).to_csv(RES / "p2_importance.csv", index=False, encoding="utf-8-sig"); print(imp.round(2))
# 単相関
corr = df[F + ["idx"]].corr()["idx"].drop("idx").sort_values(); corr.round(3).to_csv(RES / "p2_corr.csv", header=["corr"], encoding="utf-8-sig"); print(corr.round(2))
# 部分依存（上位4つ）
top4 = imp.feature.head(4).tolist(); pdp = {}
fig, axs = plt.subplots(1, 4, figsize=(12, 3.4), sharey=True)
for ax, f in zip(axs, top4):
    j = F.index(f); r = partial_dependence(rf, Xv, [j], grid_resolution=30, percentiles=(0.02, 0.98))
    gx, gy = r["grid_values"][0], r["average"][0]; pdp[f] = pd.Series(gy, index=gx)
    ax.plot(gx, gy, color=BLUE, lw=2); ax.set_title(f, fontsize=9.5, loc="left"); ax.tick_params(labelsize=8)
    ax.scatter(df[f], np.full(len(df), np.nan))
axs[0].set_ylabel("2050年の人口（2020年＝100）の予測")
fig.suptitle("ランダムフォレストの部分依存：ほかの特徴を平均的に保ったとき", x=0.01, ha="left", fontsize=12)
fig.text(0.01, -0.06, SOURCE + "、独立行政法人統計センター「SSDSE-A-2026」をもとに作成者が加工して作成", fontsize=6.8, color="#8a8984"); fig.tight_layout(); fig.savefig(FIG / "p2_pdp.png"); plt.close(fig)
pd.DataFrame({k: v.reset_index(drop=False).rename(columns={"index": "x", 0: "y"}).to_dict("list") for k, v in pdp.items()}).to_json(RES / "p2_pdp.json", force_ascii=False)
# 予測より推計が高い・低い市町村（ランダムフォレストの交差検証予測との差）
df["pred_rf"] = p_rf; df["resid"] = df.idx - df.pred_rf
df.sort_values("resid")[["pref", "muni", "idx", "pred_rf", "resid"]].round(1).to_csv(RES / "p2_resid.csv", encoding="utf-8-sig")
print(df.sort_values("resid")[["pref", "muni", "idx", "pred_rf", "resid"]].round(1).head(6).to_string()); print(df.sort_values("resid")[["pref", "muni", "idx", "pred_rf", "resid"]].round(1).tail(6).to_string())
s = {"n": len(df), "rmse_mean": ev.rmse[0], "rmse_lr": ev.rmse[1], "rmse_rf": ev.rmse[2], "r2_lr": ev.r2[1], "r2_rf": ev.r2[2], "top1": imp.feature.iloc[0], "top2": imp.feature.iloc[1], "top3": imp.feature.iloc[2]}
pd.Series(s).to_csv(RES / "p2_summary.csv", header=["value"]); print(pd.Series(s))

fig, ax = plt.subplots(figsize=(8.5, 4.4)); yy = np.arange(len(imp))
ax.barh(yy, imp.importance, xerr=imp.sd, color=BLUE, ecolor=GRAY); ax.set_yticks(yy, imp.feature); ax.invert_yaxis()
ax.set_xlabel("並べ替え重要度（その特徴をシャッフルしたときに RMSE が何ポイント悪くなるか）")
ax.set_title(f"2050年の推計人口を決めている特徴（ランダムフォレスト、交差検証の決定係数 {s['r2_rf']:.2f}）", loc="left", fontsize=11.5)
fig.text(0.01, -0.04, SOURCE + "、統計センター「SSDSE-A-2026」", fontsize=6.8, color="#8a8984"); fig.savefig(FIG / "p2_importance.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(6.5, 6)); ax.scatter(p_rf, y, s=6, color=LIGHT, edgecolor=BLUE, lw=0.3)
ax.plot([20, 130], [20, 130], color=INK, lw=0.7); ax.set_xlabel("ランダムフォレストの予測（交差検証）"); ax.set_ylabel("将来推計（2050年、2020年＝100）")
ax.set_title(f"予測と推計：RMSE {s['rmse_rf']:.1f}（重回帰 {s['rmse_lr']:.1f}）", loc="left")
fig.text(0.01, -0.04, SOURCE, fontsize=6.5, color="#8a8984"); fig.savefig(FIG / "p2_fit.png"); plt.close(fig)
