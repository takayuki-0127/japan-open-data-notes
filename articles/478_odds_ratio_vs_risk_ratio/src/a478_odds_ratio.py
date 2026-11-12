"""478 オッズ比を「何倍なりやすい」と読むと、どれだけ大げさになるのか（架空の申込みデータ、seed 478）"""
import json
import numpy as np, pandas as pd
import statsmodels.api as sm
from common import *

SEED = 478
SRC = "架空の申込みデータ（作成者が乱数で作成、seed 478）"

# ---- 1. 式：もとの割合と本当の倍率ごとの、オッズ比 ----
P0 = [0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60]
RR = [1.2, 1.5, 2.0, 3.0]
odds = lambda p: p / (1 - p)
rows = []
for rr in RR:
    for p0 in P0:
        p1 = p0 * rr
        if p1 >= 0.999: continue
        o = odds(p1) / odds(p0)
        rows.append(dict(もとの割合=p0, 本当の倍率=rr, あとの割合=round(p1, 4), オッズ比=round(o, 3), 大げさの度合い=round((o / rr - 1) * 100, 1),
                         増えた分の大げさ=round(((o - 1) / (rr - 1) - 1) * 100, 1)))
grid = pd.DataFrame(rows); grid.to_csv(RES / "odds_ratio_grid.csv", index=False)

# 境目：オッズ比が倍率より1割以上大きくなる、もとの割合  (1-p0)/(1-rr*p0)=1+x → p0 = x/((1+x)rr-1)
rows = []
for rr in RR + [1.1, 4.0, 5.0]:
    for x in [0.05, 0.10, 0.25, 0.50]:
        rows.append(dict(本当の倍率=rr, 大げさの度合い=int(x * 100), 境目のもとの割合=round(x / ((1 + x) * rr - 1) * 100, 2)))
thr = pd.DataFrame(rows).sort_values(["本当の倍率", "大げさの度合い"]); thr.to_csv(RES / "threshold_baseline.csv", index=False)

# 逆向き：オッズ比が2と出たとき、本当の倍率はいくつか
rows = []
for o in [1.5, 2.0, 3.0, 5.0]:
    for p0 in P0:
        p1 = o * odds(p0) / (1 + o * odds(p0))
        rows.append(dict(オッズ比=o, もとの割合=p0, 本当の倍率=round(p1 / p0, 3), あとの割合=round(p1, 4)))
rev = pd.DataFrame(rows); rev.to_csv(RES / "reverse_reading.csv", index=False)

# ---- 2. 架空の申込みデータ：ロジスティック回帰から倍率へ直す ----
rng = np.random.default_rng(SEED)


def make(n, p_base, rr, rng):
    """入力フォームを短くした（1）／そのまま（0）。端末（スマホ1／PC0）で完了しやすさが違う。短いフォームは完了の割合を rr 倍にする"""
    form = rng.integers(0, 2, n); phone = (rng.random(n) < 0.6).astype(int)
    p0 = np.where(phone == 1, p_base * 0.7, p_base * 1.45)          # 端末ごとのもとの割合
    p = np.clip(p0 * np.where(form == 1, rr, 1.0), 0, 0.98)
    y = (rng.random(n) < p).astype(int)
    return pd.DataFrame(dict(完了=y, 短いフォーム=form, スマホ=phone))


def true_rr(p_base, rr):
    p0 = 0.6 * p_base * 0.7 + 0.4 * p_base * 1.45
    p1 = 0.6 * min(p_base * 0.7 * rr, 0.98) + 0.4 * min(p_base * 1.45 * rr, 0.98)
    return p1 / p0, p0


def estimates(d):
    X = sm.add_constant(d[["短いフォーム", "スマホ"]].astype(float))
    m = sm.Logit(d.完了, X).fit(disp=0)
    orr = float(np.exp(m.params["短いフォーム"]))
    X1, X0 = X.copy(), X.copy(); X1["短いフォーム"] = 1.0; X0["短いフォーム"] = 0.0
    std = float(m.predict(X1).mean() / m.predict(X0).mean())             # 予測値の平均どうしの比
    p0 = d[d.短いフォーム == 0].完了.mean()
    zy = orr / (1 - p0 + p0 * orr)                                        # 換算式
    crude = d[d.短いフォーム == 1].完了.mean() / p0
    try:
        pois = sm.GLM(d.完了, X, family=sm.families.Poisson()).fit(cov_type="HC1")
        mp = float(np.exp(pois.params["短いフォーム"]))                   # 対数リンクで割合の比を直接出す
    except Exception:
        mp = np.nan
    return orr, std, zy, mp, crude


rows = []
for p_base in [0.02, 0.10, 0.30, 0.45]:
    for rr in [1.2, 1.5, 2.0]:
        t, p0 = true_rr(p_base, rr)
        for n in [2_000, 20_000]:
            E = np.array([estimates(make(n, p_base, rr, rng)) for _ in range(300)])
            med = np.median(E, axis=0)
            rmse = np.sqrt(((E / t - 1) ** 2).mean(axis=0)) * 100
            rows.append(dict(もとの割合=round(p0, 3), 設定した倍率=rr, 本当の倍率=round(t, 3), 件数=n,
                             オッズ比=round(med[0], 3), 予測値の比=round(med[1], 3), 換算式=round(med[2], 3), 対数リンク=round(med[3], 3), 単純な比=round(med[4], 3),
                             オッズ比をそのまま読んだずれ=round((med[0] / t - 1) * 100, 1), 予測値の比のずれ=round((med[1] / t - 1) * 100, 1),
                             換算式のずれ=round((med[2] / t - 1) * 100, 1), 対数リンクのずれ=round((med[3] / t - 1) * 100, 1),
                             RMSE_オッズ比=round(rmse[0], 1), RMSE_予測値の比=round(rmse[1], 1), RMSE_換算式=round(rmse[2], 1), RMSE_対数リンク=round(rmse[3], 1)))
sim = pd.DataFrame(rows); sim.to_csv(RES / "regression_to_ratio.csv", index=False)
make(2000, 0.30, 1.5, np.random.default_rng(SEED)).to_csv(DATA / "example_applications.csv", index=False)

# ---- 3. 端末をそろえるだけでオッズ比が変わる（割合の比は変わらない）----
rows = []
for p_base in [0.10, 0.30, 0.45]:
    d = make(400_000, p_base, 1.5, rng); X = sm.add_constant(d[["短いフォーム", "スマホ"]].astype(float))
    adj = float(np.exp(sm.Logit(d.完了, X).fit(disp=0).params["短いフォーム"]))
    cr = float(np.exp(sm.Logit(d.完了, sm.add_constant(d[["短いフォーム"]].astype(float))).fit(disp=0).params["短いフォーム"]))
    rr_s = d[(d.短いフォーム == 1) & (d.スマホ == 1)].完了.mean() / d[(d.短いフォーム == 0) & (d.スマホ == 1)].完了.mean()
    rr_p = d[(d.短いフォーム == 1) & (d.スマホ == 0)].完了.mean() / d[(d.短いフォーム == 0) & (d.スマホ == 0)].完了.mean()
    rr_all = d[d.短いフォーム == 1].完了.mean() / d[d.短いフォーム == 0].完了.mean()
    rows.append(dict(もとの割合=round(true_rr(p_base, 1.5)[1], 3), 端末を入れないオッズ比=round(cr, 3), 端末を入れたオッズ比=round(adj, 3),
                     割合の比_スマホ=round(rr_s, 3), 割合の比_PC=round(rr_p, 3), 割合の比_全体=round(rr_all, 3)))
collapse = pd.DataFrame(rows); collapse.to_csv(RES / "noncollapsibility.csv", index=False)

# ---- 図 ----
fig, ax = plt.subplots(figsize=(8, 4.6))
pp = np.linspace(0.005, 0.62, 300)
for rr, c in zip(RR, [LIGHT, BLUE, ORANGE, "#8f3210"]):
    m = pp * rr < 0.97
    ax.plot(pp[m] * 100, odds(pp[m] * rr) / odds(pp[m]), color=c, lw=2.2, label=f"本当の倍率 {rr}倍")
    ax.axhline(rr, color=c, lw=0.8, ls=":")
ax.set_ylim(1, 8); ax.set_xlabel("もとの割合（%）"); ax.set_ylabel("オッズ比"); ax.legend(fontsize=9, frameon=False)
ax.set_title("もとの割合が大きいほど、オッズ比は本当の倍率から離れる", loc="left")
save(fig, "a478_odds_ratio_curve.png", f"出典：式から計算。点線が本当の倍率（割合の比）")

fig, ax = plt.subplots(figsize=(8, 4.6))
s = rev[rev.オッズ比 == 2.0]
ax.bar(np.arange(len(s)), s.本当の倍率, color=BLUE)
for i, v in enumerate(s.本当の倍率): ax.text(i, v + 0.02, f"{v:.2f}倍", ha="center", fontsize=9)
ax.axhline(2, color=ORANGE, lw=1.2); ax.text(len(s) - 0.4, 2.03, "「2倍」と読んだ場合", color=ORANGE, fontsize=9, ha="right")
ax.set_xticks(np.arange(len(s))); ax.set_xticklabels([f"{int(p * 100)}%" for p in s.もとの割合]); ax.set_ylim(1, 2.25)
ax.set_xlabel("もとの割合"); ax.set_ylabel("本当の倍率（割合の比）"); ax.set_title("オッズ比が2のとき、本当は何倍なりやすいか", loc="left")
save(fig, "a478_reading_or2.png", "出典：式から計算")

fig, ax = plt.subplots(figsize=(8, 4.6))
s = sim[(sim.件数 == 20_000) & (sim.設定した倍率 == 1.5)]
w = 0.2; xs = np.arange(len(s))
for j, (col, lab, c) in enumerate([("オッズ比をそのまま読んだずれ", "オッズ比をそのまま読む", ORANGE), ("換算式のずれ", "換算式で直す", GRAY), ("予測値の比のずれ", "予測値の平均どうしの比", BLUE), ("対数リンクのずれ", "割合の比を直接出す回帰", "#14427a")]):
    ax.bar(xs + (j - 1.5) * w, s[col], w, color=c, label=lab)
    for x, v in zip(xs, s[col]): ax.text(x + (j - 1.5) * w, max(v, 0) + 1, ("0" if abs(v) < 0.5 else f"{v:+.0f}"), ha="center", fontsize=8)
ax.axhline(0, color=INK, lw=0.8); ax.set_xticks(xs); ax.set_xticklabels([f"もとの割合 {p * 100:.0f}%" for p in s.もとの割合])
ax.set_ylabel("本当の倍率からのずれ（%）"); ax.set_title("回帰の結果を「何倍」に直す4つの方法（本当は1.5倍）", loc="left"); ax.legend(fontsize=8.5, frameon=False)
save(fig, "a478_regression_methods.png", f"出典：{SRC}。2万件のデータを300回。中央値")

main = dict(seed=SEED, 境目_1割=dict(zip(thr[thr.大げさの度合い == 10].本当の倍率.astype(str), thr[thr.大げさの度合い == 10].境目のもとの割合)),
            オッズ比2の本当の倍率=dict(zip(s2.もとの割合.astype(str), s2.本当の倍率)) if (s2 := rev[rev.オッズ比 == 2.0]) is not None else None)
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
print(grid.pivot(index="もとの割合", columns="本当の倍率", values="オッズ比").to_string()); print(grid.pivot(index="もとの割合", columns="本当の倍率", values="大げさの度合い").to_string())
print(thr.to_string()); print(rev.pivot(index="もとの割合", columns="オッズ比", values="本当の倍率").to_string()); print(sim.drop(columns=[c for c in sim.columns if c.startswith("RMSE")]).to_string()); print(sim[["もとの割合", "設定した倍率", "件数"] + [c for c in sim.columns if c.startswith("RMSE")]].to_string()); print(collapse.to_string())
