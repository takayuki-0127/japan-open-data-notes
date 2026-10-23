"""D1：人身事故のうち、死亡事故になりやすいのはどんな条件か（2025年の全国の人身事故 約29万件）。
ロジスティック回帰（オッズ比）と勾配ブースティング（予測の当たり方・並べ替え重要度）で調べる"""
from common import *
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.model_selection import StratifiedKFold
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.inspection import permutation_importance
import resource, sys
mem = lambda t: print(t, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1000, "MB", flush=True)

x = load(2025)
x["hourband"] = pd.cut(x.hour, [-1, 5, 9, 15, 19, 23], labels=["0〜5時", "6〜9時", "10〜15時", "16〜19時", "20〜23時"]).astype(str)
x["weekend"] = np.where(x.dow.isin([1, 7]) | (x.holiday == "1"), "土日祝", "平日")
feats = ["night", "weather", "surface", "urban", "road", "type", "ageA", "ageB", "partyA", "partyB", "speedA", "hourband", "weekend"]
x = x.dropna(subset=feats)
x = x[(x.ageA != "不明") & (x.partyA != "相手なし等")]
lab = {"night": "昼夜", "weather": "天候", "surface": "路面", "urban": "地形", "road": "道路形状", "type": "事故類型", "ageA": "年齢（第1当事者）",
       "ageB": "年齢（第2当事者）", "partyA": "第1当事者", "partyB": "第2当事者", "speedA": "速度規制", "hourband": "時間帯", "weekend": "曜日"}

mem("# 1) そのま")
# 1) そのままの死亡事故率
rows = []
for f in feats:
    g = x.groupby(f).agg(n=("fatal", "size"), fatal=("fatal", "sum")); g["rate_pct"] = g.fatal / g.n * 100
    for k, r in g.iterrows(): rows.append(dict(factor=lab[f], level=k, n=int(r.n), fatal=int(r.fatal), rate_pct=r.rate_pct))
raw = pd.DataFrame(rows); raw.round(3).to_csv(RES / "d1_raw_rates.csv", index=False, encoding="utf-8-sig")
base_rate = x.fatal.mean() * 100

mem("# 2) ロジス")
# 2) ロジスティック回帰（基準：昼・晴・乾燥・市街地・単路・車両相互・45〜54歳・乗用車・40以下・10〜15時・平日）
ref = {"night": "昼", "weather": "晴", "surface": "乾燥", "urban": "市街地", "road": "単路", "type": "車両相互", "ageA": "45〜54歳", "ageB": "45〜54歳",
       "partyA": "乗用車", "partyB": "乗用車", "speedA": "40以下", "hourband": "10〜15時", "weekend": "平日"}
D = pd.concat([pd.get_dummies(x[f], prefix=f, prefix_sep="=").drop(columns=f"{f}={ref[f]}") for f in feats if f != "type"], axis=1).astype(float)
D = D.loc[:, D.sum() >= 30]
# 完全に重なる列（例：第2当事者の年齢「不明」＝相手なし）を QR 分解で落とす
import scipy.linalg as sla
Q, R, P = sla.qr(np.column_stack([np.ones(len(D)), D.values])[::7], mode="economic", pivoting=True)
rank = (np.abs(np.diag(R)) > 1e-8 * np.abs(R[0, 0])).sum(); keep = sorted(P[:rank]); keep = [k - 1 for k in keep if k > 0]
print("dropped:", [c for i, c in enumerate(D.columns) if i not in keep]); D = D.iloc[:, keep]
lr = sm.Logit(x.fatal.astype(float).values, sm.add_constant(D)).fit(disp=0, maxiter=200, method="newton")
ci = lr.conf_int()
orr = pd.DataFrame({"OR": np.exp(lr.params), "lo": np.exp(ci[0]), "hi": np.exp(ci[1]), "p": lr.pvalues}).drop("const")
orr["factor"] = [lab[k.split("=")[0]] for k in orr.index]; orr["level"] = [k.split("=", 1)[1] for k in orr.index]
orr.round(4).to_csv(RES / "d1_odds_ratios.csv", encoding="utf-8-sig")
print(orr.sort_values("OR", ascending=False).head(15).round(2)[["factor", "level", "OR", "lo", "hi"]])

mem("# 3) 予測")
# 3) 予測：ロジスティック回帰と勾配ブースティングの5分割交差検証
X = pd.get_dummies(x[feats], drop_first=False).astype(np.uint8); y = x.fatal.values
Xc = x[feats].astype("category").apply(lambda s: s.cat.codes)
skf = StratifiedKFold(5, shuffle=True, random_state=0); res = []
p_lr = np.zeros(len(y)); p_gb = np.zeros(len(y))
for tr, te in skf.split(X, y):
    m1 = LogisticRegression(max_iter=2000, C=1.0).fit(X.iloc[tr], y[tr]); p_lr[te] = m1.predict_proba(X.iloc[te])[:, 1]
    m2 = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, categorical_features="from_dtype" if False else [True] * len(feats), random_state=0)
    m2.fit(Xc.iloc[tr], y[tr]); p_gb[te] = m2.predict_proba(Xc.iloc[te])[:, 1]
score = pd.DataFrame({"model": ["ロジスティック回帰", "勾配ブースティング"], "auc": [roc_auc_score(y, p_lr), roc_auc_score(y, p_gb)],
                      "avg_precision": [average_precision_score(y, p_lr), average_precision_score(y, p_gb)], "base_rate": y.mean()})
score.round(4).to_csv(RES / "d1_cv_scores.csv", index=False, encoding="utf-8-sig"); print(score.round(3))
mem("# 予測の上位1")
# 予測の上位10%に、死亡事故の何%が入るか
top = lambda p: y[p >= np.quantile(p, 0.9)].sum() / y.sum() * 100
capture = {"lr_top10": top(p_lr), "gb_top10": top(p_gb)}
# 校正：予測を10分位に分けて、実際の死亡事故率と比べる
cal = pd.DataFrame({"p": p_gb, "y": y}); cal["bin"] = pd.qcut(cal.p, 10, labels=False, duplicates="drop")
cal = cal.groupby("bin").agg(pred=("p", "mean"), obs=("y", "mean"), n=("y", "size")); cal.to_csv(RES / "d1_calibration.csv", encoding="utf-8-sig")
mem("# 並べ替え重要")
# 並べ替え重要度（最後のfoldのモデルで、そのテストデータ）
pi = permutation_importance(m2, Xc.iloc[te], y[te], scoring="roc_auc", n_repeats=5, random_state=0)
imp = pd.Series(pi.importances_mean, index=[lab[f] for f in feats]).sort_values(ascending=False); imp.round(4).to_csv(RES / "d1_importance.csv", header=["auc_drop"], encoding="utf-8-sig"); print(imp.round(4))

s = {"n": len(x), "n_fatal": int(y.sum()), "base_rate_pct": base_rate, **{f"auc_{k}": v for k, v in zip(["lr", "gb"], score.auc)}, **capture,
     "top_cal_obs_pct": cal.obs.iloc[-1] * 100, "bottom_cal_obs_pct": cal.obs.iloc[0] * 100}
for f, lv in [("night", "夜"), ("partyB", "歩行者"), ("road", "カーブ"), ("urban", "非市街地"), ("ageA", "75歳以上"), ("speedA", "60以下"), ("hourband", "0〜5時"), ("partyA", "自動二輪")]:
    r = orr[(orr.factor == lab[f]) & (orr.level == lv)].iloc[0]; s[f"OR_{f}_{lv}"] = r.OR; s[f"OR_{f}_{lv}_lo"] = r.lo; s[f"OR_{f}_{lv}_hi"] = r.hi
pd.Series(s).to_csv(RES / "d1_summary.csv", header=["value"]); print(pd.Series(s).round(3))

note = "\n（2025年の全国の人身事故。第1当事者＝過失が重い側、第2当事者＝相手。死亡事故＝24時間以内に死者が出た事故）"
# 図1 そのままの率（主要な要因）
show = [("night", ["昼", "夜"]), ("urban", ["市街地", "非市街地"]), ("road", ["交差点", "単路", "カーブ"]), ("partyB", ["乗用車", "自転車等", "歩行者", "相手なし等"]),
        ("ageA", ["24歳以下", "45〜54歳", "65〜74歳", "75歳以上"]), ("hourband", ["6〜9時", "10〜15時", "0〜5時"])]
lbls, vals = [], []
for f, lvs in show:
    for lv in lvs:
        r = raw[(raw.factor == lab[f]) & (raw.level == lv)]
        if len(r): lbls.append(f"{lab[f]}：{lv}".replace("相手なし等", "なし（単独事故）")); vals.append(r.rate_pct.iloc[0])
fig, ax = plt.subplots(figsize=(8, 7))
ax.barh(range(len(vals)), vals, color=[ORANGE if v > base_rate * 2 else BLUE for v in vals]); ax.axvline(base_rate, color=INK, ls="--", lw=1)
ax.text(base_rate, len(vals) - 0.3, f" 全体 {base_rate:.2f}%", fontsize=8.5)
for i, v in enumerate(vals): ax.text(v + 0.05, i, f"{v:.2f}%", va="center", fontsize=8)
ax.set_yticks(range(len(vals))); ax.set_yticklabels(lbls, fontsize=9); ax.invert_yaxis(); ax.set_xlabel("人身事故のうち死亡事故の割合（%）")
ax.set_title("カーブ・単独事故・深夜・歩行者が相手の事故は、死亡事故の割合が高い")
fig.text(0.01, -0.04, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "d1_raw.png"); plt.close(fig)

# 図2 オッズ比
o = orr[orr.lo.notna()].copy(); o = o[((o.hi / o.lo) < 20) & ~o.level.isin(["その他", "対象外"])]
o.loc[(o.factor == "年齢（第2当事者）") & (o.level == "不明"), ["factor", "level"]] = ["第2当事者", "なし（単独事故）"]
o = o.sort_values("OR"); o = pd.concat([o.head(6), o.tail(14)])
fig, ax = plt.subplots(figsize=(8, 7.5))
y_ = np.arange(len(o))
ax.errorbar(o.OR, y_, xerr=[o.OR - o.lo, o.hi - o.OR], fmt="o", color=ORANGE, capsize=3)
ax.axvline(1, color=GRAY, lw=0.8); ax.set_xscale("log")
ax.set_yticks(y_); ax.set_yticklabels([f"{a}：{b}" for a, b in zip(o.factor, o.level)], fontsize=8.5)
ax.set_xlabel("オッズ比（対数目盛。ほかの条件をそろえたとき、基準と比べて死亡事故になりやすい度合い）")
ax.set_title("ほかの条件をそろえると、単独事故・歩行者・高齢の相手・カーブ・深夜で高い")
fig.text(0.01, -0.05, SOURCE + note + "\nロジスティック回帰。基準：昼・晴・乾燥・市街地・単路・45〜54歳・乗用車・40km/h以下・10〜15時・平日。オッズ比の大きい14項目と小さい6項目を表示", fontsize=7, color="#8a8984")
fig.savefig(FIG / "d1_or.png"); plt.close(fig)

# 図3 重要度と校正
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
axes[0].barh(range(len(imp)), imp.values, color=BLUE); axes[0].set_yticks(range(len(imp))); axes[0].set_yticklabels(imp.index, fontsize=9); axes[0].invert_yaxis()
axes[0].set_xlabel("並べ替えたときのAUCの下がり幅"); axes[0].set_title(f"勾配ブースティング（AUC {score.auc[1]:.3f}）の重要度", fontsize=11)
axes[1].plot(cal.pred * 100, cal.obs * 100, "o-", color=ORANGE); mx = max(cal.pred.max(), cal.obs.max()) * 100
axes[1].plot([0, mx], [0, mx], color=GRAY, ls="--", lw=0.8); axes[1].set_xlabel("予測した死亡事故の確率（%、10分位ごとの平均）"); axes[1].set_ylabel("実際の割合（%）")
axes[1].set_title(f"予測の上位10%に、死亡事故の{capture['gb_top10']:.0f}%が入る", fontsize=11)
fig.text(0.01, -0.07, SOURCE + "\n（5分割交差検証。重要度は最後の分割のテストデータで5回並べ替えた平均）", fontsize=7, color="#8a8984")
fig.savefig(FIG / "d1_model.png"); plt.close(fig)
