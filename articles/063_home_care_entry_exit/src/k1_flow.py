"""訪問介護・通所介護の事業所の参入と撤退（半年ごと、12時点の事業所番号を突き合わせ）と、撤退しやすさの離散時間ロジット"""
import numpy as np, pandas as pd, statsmodels.api as sm
import matplotlib.pyplot as plt
from common import *

x = load()
K = len(SNAPS)
rows, panel = [], []
for svc in SVC.values():
    s = x[x.svc == svc]
    pres = {k: set(s[s.k == k].id) for k in range(K)}
    ever_after = {k: set().union(*[pres[j] for j in range(k + 1, K)]) if k < K - 1 else set() for k in range(K)}
    ever_before = {k: set().union(*[pres[j] for j in range(0, k)]) if k > 0 else set() for k in range(K)}
    for k in range(K - 1):
        n = len(pres[k]); gone = pres[k] - pres[k + 1]
        perm = gone - ever_after[k + 1]; temp = gone & ever_after[k + 1]
        new = pres[k + 1] - pres[k] - ever_before[k]; back = (pres[k + 1] - pres[k]) & ever_before[k]
        rows.append({"svc": svc, "k": k, "from": SNAPS[k], "to": SNAPS[k + 1], "n": n, "exit": len(perm), "temp_gap": len(temp),
                     "entry": len(new), "return": len(back), "exit_rate": len(perm) / n * 100, "entry_rate": len(new) / n * 100,
                     "net_rate": (len(pres[k + 1]) - n) / n * 100})
        a = s[s.k == k].copy(); a["exit"] = a.id.isin(perm).astype(int); panel.append(a)
F = pd.DataFrame(rows); F.to_csv(RES / "k1_flows.csv", index=False, encoding="utf-8-sig"); print(F.round(2).to_string())
P = pd.concat(panel, ignore_index=True)

# 離散時間ロジット：撤退 ~ 区間FE + 訪問介護×改定後 + 法人規模 + 法人種別 + 市町村の種類
P["houmon"] = (P.svc == "訪問介護").astype(float)
P["post"] = (P.k >= 6).astype(float)  # 2023-12→2024-06 以降（2024年4月の報酬改定を含む区間から）
P["houmon_post"] = P.houmon * P.post
X = pd.concat([P[["houmon", "houmon_post"]],
               pd.get_dummies(P.k, prefix="k", dtype=float).drop(columns="k_0"),
               pd.get_dummies(P.csize_c, prefix="規模", dtype=float).drop(columns="規模_20か所以上"),
               pd.get_dummies(P.ctype, prefix="種別", dtype=float).drop(columns="種別_社会福祉法人"),
               pd.get_dummies(P.mtype, prefix="地域", dtype=float).drop(columns="地域_市")], axis=1)
X = sm.add_constant(X)
m = sm.Logit(P.exit, X).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(P.id)[0]})
OR = pd.DataFrame({"var": m.params.index, "or": np.exp(m.params.values), "lo": np.exp(m.conf_int()[0].values), "hi": np.exp(m.conf_int()[1].values), "p": m.pvalues.values})
OR.to_csv(RES / "k1_logit_or.csv", index=False, encoding="utf-8-sig"); print(OR[~OR["var"].str.startswith("k_")].round(3).to_string()); print("N", len(P), "exit mean", P.exit.mean())

# 区間ごとの「訪問介護−通所介護」撤退率の差（イベントスタディ風）
es = []
for k in range(K - 1):
    a = P[(P.k == k) & (P.svc == "訪問介護")].exit; b = P[(P.k == k) & (P.svc == "通所介護")].exit
    d_ = (a.mean() - b.mean()) * 100; se = np.sqrt(a.var() / len(a) + b.var() / len(b)) * 100
    es.append({"k": k, "to": SNAPS[k + 1], "diff": d_, "lo": d_ - 1.96 * se, "hi": d_ + 1.96 * se})
ES = pd.DataFrame(es); ES.to_csv(RES / "k1_exit_diff.csv", index=False, encoding="utf-8-sig")

# 法人規模別の撤退率（改定前後）
G = P.groupby(["svc", "csize_c", "post"]).exit.mean().unstack() * 100; G.columns = ["改定前", "改定後"]; G.to_csv(RES / "k1_exit_by_size.csv", encoding="utf-8-sig"); print(G.round(2))

lab = [s.replace("-", "年").replace("06", "6月").replace("12", "12月") for s in SNAPS]
# 図1：事業所数
fig, ax = plt.subplots(figsize=(8, 3.9))
for svc in SVC.values():
    c = x[x.svc == svc].groupby("k").size(); ax.plot(c.index, c / c.iloc[0] * 100, "o-", color=SCOL[svc], lw=2, label=f"{svc}（{c.iloc[0]:,}→{c.iloc[-1]:,}）")
ax.axhline(100, color=GRAY, lw=.8); ax.axvline(6.67, color=GRAY, ls=":", lw=1); ax.text(6.75, 98.6, "2024年4月\n報酬改定", fontsize=8.5, color=GRAY, va="top")
ax.set_xticks(range(K)); ax.set_xticklabels([l if i % 2 == 0 else "" for i, l in enumerate(lab)], fontsize=8.5)
ax.set_ylabel("2020年12月末＝100"); ax.legend(frameon=False, fontsize=9.5, loc="lower left")
ax.set_title("公表されている事業所の数（半年ごと）", loc="left"); note(ax, SOURCE, -0.14)
fig.savefig(FIG / "k1_counts.png"); plt.close(fig)

# 図2：参入率と撤退率
fig, axes = plt.subplots(1, 2, figsize=(10, 3.9), sharey=True)
for ax, svc in zip(axes, SVC.values()):
    f = F[F.svc == svc]
    ax.bar(f.k - .2, f.entry_rate, .4, color=GREEN, label="新しく現れた事業所")
    ax.bar(f.k + .2, f.exit_rate, .4, color=ORANGE, label="消えて戻らなかった事業所")
    ax.plot(f.k, f.net_rate, "o-", color=INK, lw=1.4, ms=4, label="差し引き（純増減）")
    ax.axhline(0, color=INK, lw=.6); ax.axvline(5.5, color=GRAY, ls=":", lw=1)
    ax.set_xticks(f.k); ax.set_xticklabels([t.replace("-", "/") for t in f.to], rotation=60, fontsize=8)
    ax.set_title(svc, loc="left")
axes[0].set_ylabel("半年前の事業所数に対する%"); axes[0].legend(frameon=False, fontsize=8.5, loc="upper left")
fig.suptitle("半年ごとの参入と撤退（横軸は期末の時点、点線の右が報酬改定後）", x=.02, y=1.04, ha="left", fontsize=12)
note(axes[0], SOURCE, -0.3); fig.savefig(FIG / "k1_rates.png"); plt.close(fig)

# 図3：撤退率の差
fig, ax = plt.subplots(figsize=(8, 3.7))
ax.errorbar(ES.k, ES["diff"], yerr=[ES["diff"] - ES.lo, ES.hi - ES["diff"]], fmt="o", color=BLUE, capsize=3, lw=1.4)
ax.axhline(0, color=INK, lw=.6); ax.axvline(5.5, color=GRAY, ls=":", lw=1)
ax.set_xticks(ES.k); ax.set_xticklabels([t.replace("-", "/") for t in ES.to], rotation=45, fontsize=8.5)
ax.set_ylabel("撤退率の差（%ポイント）"); ax.set_title("半年間の撤退率：訪問介護 − 通所介護（点線の右が報酬改定後）", loc="left", fontsize=12)
note(ax, SOURCE + "\nひげは95%信頼区間", -0.24); fig.savefig(FIG / "k1_exit_diff.png"); plt.close(fig)

# 図4：オッズ比
sel = OR[~OR["var"].str.startswith(("k_", "const"))].copy()
names = {"houmon": "訪問介護（通所介護と比べて）", "houmon_post": "訪問介護×報酬改定後"}
sel["label"] = sel["var"].map(lambda v: names.get(v, v.replace("_", "：")))
sel = sel.iloc[::-1]
fig, ax = plt.subplots(figsize=(7.6, 5.2))
yy = np.arange(len(sel))
ax.errorbar(sel["or"], yy, xerr=[sel["or"] - sel.lo, sel.hi - sel["or"]], fmt="o", color=BLUE, capsize=2)
ax.axvline(1, color=INK, lw=.7); ax.set_xscale("log"); ax.set_xticks([0.8, 1, 1.5, 2, 3]); ax.set_xticklabels(["0.8", "1", "1.5", "2", "3"]); ax.minorticks_off(); ax.set_yticks(yy); ax.set_yticklabels(sel.label, fontsize=9)
ax.set_xlabel("撤退のオッズ比（対数目盛、1より右ほど撤退しやすい）")
ax.set_title("撤退しやすさの比較（基準：20か所以上の法人、社会福祉法人、市）", loc="left", fontsize=11.5)
note(ax, SOURCE + "\n半年区間の固定効果つき離散時間ロジット。事業所単位のクラスター頑健標準誤差", -0.12)
fig.savefig(FIG / "k1_odds.png"); plt.close(fig)

# 頑健性：最後の区間（撤退を後の時点で確かめられない）を除く／2区間除く
rob = []
for drop in [0, 1, 2]:
    keep = P.k <= (K - 2 - drop)
    mm = sm.Logit(P.exit[keep], X[keep].loc[:, X[keep].abs().sum() > 0]).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(P.id[keep])[0]})
    ci = mm.conf_int().loc["houmon_post"]
    rob.append({"除いた最後の区間数": drop, "or": np.exp(mm.params["houmon_post"]), "lo": np.exp(ci[0]), "hi": np.exp(ci[1]), "n": int(keep.sum())})
rob = pd.DataFrame(rob); rob.to_csv(RES / "k1_robust.csv", index=False, encoding="utf-8-sig"); print(rob.round(3))
