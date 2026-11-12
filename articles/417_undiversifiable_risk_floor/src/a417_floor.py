"""417 大数の法則が効かないリスクがあると、契約を増やしても損害率の振れはどこで下げ止まるか（架空の契約）
各契約の事故の件数：ポアソン（年5%×その年の共通の要因）。共通の要因：平均1のガンマ。損害額：対数正規（平均1、CV2）。
損害率＝その年の損害の合計 ÷ 見込み（契約数×5%×1）。"""
import json
import numpy as np, pandas as pd
from common import *

SEED, P, CVX, YEARS = 417, 0.05, 2.0, 4000
NS = [1_000, 3_000, 10_000, 30_000, 100_000, 300_000, 1_000_000]
CS = [0.0, 0.05, 0.10, 0.20]                       # 共通の要因の散らばり（標準偏差。平均は1）
S2 = np.log(1 + CVX ** 2)

def year_losses(rng, n, c, years):
    """年ごとの損害率。メモリのため、事故の数が2千万件を超えないように分けて作る"""
    step = max(1, int(2e7 // (n * P))); out = []
    for s0 in range(0, years, step):
        k = min(step, years - s0)
        lam = rng.gamma(1 / c ** 2, c ** 2, k) if c > 0 else np.ones(k)
        N = rng.poisson(n * P * lam)
        X = rng.lognormal(-S2 / 2, np.sqrt(S2), N.sum())
        out.append(np.bincount(np.repeat(np.arange(k), N), weights=X, minlength=k) / (n * P))
    return np.concatenate(out)

rows = []
for ci, c in enumerate(CS):
    for ni, n in enumerate(NS):
        rng = np.random.default_rng([SEED, ci, ni])
        yrs = YEARS if n <= 300_000 else 2000
        lr = year_losses(rng, n, c, yrs)
        th = np.sqrt((1 + CVX ** 2) / (n * P) + c ** 2)
        rows.append(dict(共通の要因=c, 契約数=n, 年数=yrs, 損害率の振れ=lr.std(ddof=1), 式の値=th, 独立と見た見込み=np.sqrt((1 + CVX ** 2) / (n * P)),
                         上位0_5パーセント=np.quantile(lr, 0.995), 上位0_5_独立と見た見込み=np.nan, 見込みの1_1倍を超えた年の割合=(lr > 1.1).mean()))
    print("c", c, "done", flush=True)
T = pd.DataFrame(rows)
ind = T[T.共通の要因 == 0].set_index("契約数")["上位0_5パーセント"]
T["上位0_5_独立と見た見込み"] = T.契約数.map(ind)
T["振れ÷独立と見た見込み"] = T.損害率の振れ / T.独立と見た見込み
T.to_csv(RES / "volatility_by_size.csv", index=False)

# 下げ止まる契約数：振れが「下限（共通の要因の散らばり）の1.1倍」以内になる契約数（式）
floor = pd.DataFrame([dict(共通の要因=c, 下限=c, 下限の1_1倍に入る契約数=(1 + CVX ** 2) / (0.21 * c ** 2 * P), 下限の1_5倍に入る契約数=(1 + CVX ** 2) / (1.25 * c ** 2 * P)) for c in CS if c > 0])
floor.to_csv(RES / "floor_reached_at.csv", index=False)

# 共通の要因が、地域などで K 個に分かれて独立なとき（各グループの契約数は同じ）
rows = []
for ki, K in enumerate([1, 4, 16]):
    for ni, n in enumerate([100_000, 1_000_000]):
        rng = np.random.default_rng([SEED, 50, ki, ni])
        lr = np.mean([year_losses(rng, n // K, 0.10, 2000) for _ in range(K)], axis=0)
        rows.append(dict(グループの数=K, 契約数=n, 損害率の振れ=lr.std(ddof=1), 式の値=np.sqrt((1 + CVX ** 2) / (n * P) + 0.10 ** 2 / K)))
G = pd.DataFrame(rows); G.to_csv(RES / "independent_groups.csv", index=False)

# 自社の実績から共通の要因を見積もれるか：損害率の分散 − 独立の分の分散
rows = []
for ni, n in enumerate([10_000, 100_000, 1_000_000]):
    for yi, yrs in enumerate([10, 20, 50]):
        rng = np.random.default_rng([SEED, 70, ni, yi]); est = []
        reps = 1000 if n <= 100_000 else 200
        lr = year_losses(rng, n, 0.10, yrs * reps).reshape(reps, yrs)
        c2 = lr.var(axis=1, ddof=1) - (1 + CVX ** 2) / (n * P)
        est = np.sqrt(np.clip(c2, 0, None))
        rows.append(dict(契約数=n, 実績の年数=yrs, くり返し=reps, 見積もりが0になった割合=(c2 <= 0).mean(), 見積もりの中央値=np.median(est),
                         見積もりの10パーセント点=np.quantile(est, 0.1), 見積もりの90パーセント点=np.quantile(est, 0.9), 真の値=0.10))
E2 = pd.DataFrame(rows); E2.to_csv(RES / "estimate_common_factor.csv", index=False)

# 例のデータ：契約10万件・共通の要因10%の100年分
rng = np.random.default_rng([SEED, 90])
ex = pd.DataFrame(dict(年=np.arange(1, 101), 共通の要因なし=year_losses(rng, 100_000, 0.0, 100), 共通の要因10パーセント=year_losses(rng, 100_000, 0.10, 100)))
ex.round(4).to_csv(DATA / "example_loss_ratio_100years_n100000.csv", index=False)

g = lambda c, n, col: float(T[(T.共通の要因 == c) & (T.契約数 == n)][col].iloc[0])
main = dict(条件=dict(事故の割合=P, 損害額のCV=CVX, 年数=YEARS, 乱数の種=SEED),
            振れ_パーセント={f"共通{int(c*100)}%": {str(n): round(100 * g(c, n, "損害率の振れ"), 2) for n in NS} for c in CS},
            下げ止まり=floor.round(2).to_dict("records"),
            契約100万件_共通10=dict(振れ=g(0.10, 1_000_000, "損害率の振れ"), 独立と見た見込み=g(0.10, 1_000_000, "独立と見た見込み"), 倍=g(0.10, 1_000_000, "振れ÷独立と見た見込み"),
                              上位0_5=g(0.10, 1_000_000, "上位0_5パーセント"), 上位0_5_独立=g(0.0, 1_000_000, "上位0_5パーセント")),
            契約10万件_共通10=dict(振れ=g(0.10, 100_000, "損害率の振れ"), 独立と見た見込み=g(0.10, 100_000, "独立と見た見込み"), 上位0_5=g(0.10, 100_000, "上位0_5パーセント"), 上位0_5_独立=g(0.0, 100_000, "上位0_5パーセント"),
                              見込みの1_1倍を超えた年=g(0.10, 100_000, "見込みの1_1倍を超えた年の割合"), 独立なら=g(0.0, 100_000, "見込みの1_1倍を超えた年の割合")),
            グループ=G.round(4).to_dict("records"), 見積もり=E2.round(4).to_dict("records"))
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

cols = {0.0: GRAY, 0.05: GREEN, 0.10: BLUE, 0.20: ORANGE}
fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
for c in CS:
    d = T[T.共通の要因 == c]
    ax[0].plot(d.契約数, d.損害率の振れ * 100, "o", color=cols[c], label=f"共通の要因 {int(c*100)}%" if c else "共通の要因なし（独立）")
    ax[0].plot(d.契約数, d.式の値 * 100, "-", color=cols[c], lw=1)
ax[0].set_xscale("log"); ax[0].set_yscale("log"); ax[0].set_xlabel("契約数（対数）"); ax[0].set_ylabel("損害率の振れ（標準偏差、%。対数）")
ax[0].set_title("契約を増やしたときの損害率の振れ\n点＝試した結果、線＝式"); ax[0].legend(fontsize=8, frameon=False)
ax[1].plot(ex.年, ex.共通の要因なし * 100, color=GRAY, lw=1, label="共通の要因なし")
ax[1].plot(ex.年, ex.共通の要因10パーセント * 100, color=BLUE, lw=1.2, label="共通の要因10%")
ax[1].axhline(100, color=INK, lw=0.6); ax[1].set_xlabel("年"); ax[1].set_ylabel("損害率（見込み＝100）"); ax[1].set_title("契約10万件の100年分（例）"); ax[1].legend(fontsize=8, frameon=False)
save(fig, "a417_volatility_floor.png", "架空の契約（事故の割合5%、損害額は対数正規で CV2）。作成者が計算")

fig, ax = plt.subplots(1, 2, figsize=(11, 4.3))
d = T[T.共通の要因 == 0.10]
ax[0].plot(d.契約数, d.上位0_5パーセント * 100, "o-", color=BLUE, label="共通の要因10%")
ax[0].plot(d.契約数, d.上位0_5_独立と見た見込み * 100, "o--", color=GRAY, label="独立と見た場合")
ax[0].axhline(100, color=INK, lw=0.6); ax[0].set_xscale("log"); ax[0].set_xlabel("契約数（対数）"); ax[0].set_ylabel("200年に1度の損害率（見込み＝100）")
ax[0].set_title("200年に1度の年の損害率"); ax[0].legend(fontsize=8.5, frameon=False)
ax[1].bar([f"{int(r.グループの数)}グループ\n{int(r.契約数/10000)}万件" for r in G.itertuples()], G.損害率の振れ * 100, color=[BLUE, BLUE, GREEN, GREEN, ORANGE, ORANGE])
for i, v in enumerate(G.損害率の振れ * 100): ax[1].text(i, v + 0.15, f"{v:.1f}%", ha="center", fontsize=9)
ax[1].set_ylabel("損害率の振れ（%）"); ax[1].set_title("共通の要因が、独立ないくつかのグループに\n分かれているとき（各10%）"); ax[1].tick_params(axis="x", labelsize=8)
save(fig, "a417_tail_and_groups.png", "架空の契約。グループごとの共通の要因はたがいに独立と置いた。作成者が計算")

fig, ax = plt.subplots(figsize=(8.5, 4.3))
lab = [f"{int(r.契約数/10000)}万件\n{int(r.実績の年数)}年" for r in E2.itertuples()]
ax.errorbar(range(len(E2)), E2.見積もりの中央値 * 100, yerr=[(E2.見積もりの中央値 - E2.見積もりの10パーセント点) * 100, (E2.見積もりの90パーセント点 - E2.見積もりの中央値) * 100], fmt="o", color=BLUE, capsize=4)
for i, r in enumerate(E2.itertuples()): ax.text(i + 0.08, r.見積もりの90パーセント点 * 100 + 0.3, f"0になった\n{r.見積もりが0になった割合*100:.0f}%", fontsize=7.5, color=ORANGE)
ax.axhline(10, color=INK, lw=0.8, ls="--"); ax.set_xticks(range(len(E2))); ax.set_xticklabels(lab, fontsize=8.5); ax.set_ylabel("見積もった共通の要因の散らばり（%）"); ax.set_ylim(0, 22)
ax.set_title("自社の実績から見積もった共通の要因（真の値は10%）\n点＝中央値、線＝10〜90%の範囲")
save(fig, "a417_estimate_from_own_data.png", "損害率の分散から、独立の分（事故の数と損害額の散らばり）を引いて見積もった。作成者が計算")
print(json.dumps(main, ensure_ascii=False, indent=1))
