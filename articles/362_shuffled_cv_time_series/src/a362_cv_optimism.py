"""A362 時系列をばらばらに分けて確かめると、予測の精度をどれだけ甘く見積もるのか
架空の日次需要50本と、商業動態統計（6業態の月次）で、
「ばらばらに分ける交差検証」と「時間の順に分ける確かめ方」を、実際の先の期間の誤差と比べる。乱数の種は362。
"""
import json, sys
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED, N_SERIES, N_TRAIN, N_FUT, K = 362, 50, 1095, 182, 5
SRC = "架空のデータ（作成者が乱数で作成、seed 362）"


def make_series(rng, rho=0.9, drift=0.01):
    """日次の需要：伸び＋曜日＋年の季節＋ゆっくり動く水準（ランダムウォーク）＋続くずれ（AR1）"""
    n = N_TRAIN + N_FUT; t = np.arange(n)
    dow = rng.normal(0, 0.10, 7); dow -= dow.mean()
    level = np.cumsum(rng.normal(0, drift, n))                       # ゆっくり動く水準
    ar = np.zeros(n); e = rng.normal(0, 0.06, n)
    for i in range(1, n): ar[i] = rho * ar[i - 1] + e[i]
    logy = np.log(100) + 0.0002 * t + dow[t % 7] + 0.15 * np.sin(2 * np.pi * t / 365.25 + rng.uniform(0, 6.28)) + level + ar \
        + rng.normal(0, 0.05, n)
    return np.exp(logy)


def feats_calendar(t):
    """日付だけから作る特徴量（通し番号・曜日・年の季節）"""
    X = np.column_stack([t, np.sin(2 * np.pi * t / 365.25), np.cos(2 * np.pi * t / 365.25)]
                        + [(t % 7 == d).astype(float) for d in range(7)])
    return X


def feats_lag(y, t, h=28):
    """h 日以上前の実績だけから作る特徴量（h 日先を当てる想定）"""
    ys = pd.Series(y)
    cols = [ys.shift(h), ys.shift(h + 7), ys.shift(h + 14), ys.shift(h).rolling(28).mean()]
    X = np.column_stack([c.to_numpy() for c in cols] + [(t % 7 == d).astype(float) for d in range(7)])
    return X


def mk(model):
    if model == "gbm": return HistGradientBoostingRegressor(max_iter=60, learning_rate=0.15, random_state=0)
    return Ridge(alpha=1.0)


def mape(a, f): return float(np.mean(np.abs(f - a) / a) * 100)


def evaluate(X, y, n_train, model, rng_seed, fut_len):
    """返り値：(ばらばらの交差検証, 時間の順の確かめ, 実際の先の期間) の MAPE"""
    ok = ~np.isnan(X).any(axis=1)
    tr = np.where(ok & (np.arange(len(y)) < n_train))[0]; fu = np.arange(n_train, len(y))
    ly = np.log(y)
    # 1) ばらばらに5つに分ける
    errs = []
    for a, b in KFold(K, shuffle=True, random_state=rng_seed).split(tr):
        m = mk(model).fit(X[tr[a]], ly[tr[a]]); errs.append(np.abs(np.exp(m.predict(X[tr[b]])) - y[tr[b]]) / y[tr[b]])
    shuf = float(np.mean(np.concatenate(errs)) * 100)
    # 2) 時間の順：前の部分で学び、すぐ後ろの fut_len 個で確かめる（5回、後ろへずらす）
    errs = []
    for j in range(K):
        end = n_train - (K - 1 - j) * fut_len // 2          # 確かめる区間の終わり
        b = tr[(tr >= end - fut_len) & (tr < end)]; a = tr[tr < end - fut_len]
        if len(a) < 200 // (1 if n_train > 500 else 4) or len(b) == 0: continue
        m = mk(model).fit(X[a], ly[a]); errs.append(np.abs(np.exp(m.predict(X[b])) - y[b]) / y[b])
    tsplit = float(np.mean(np.concatenate(errs)) * 100)
    # 3) 実際：全部で学び、その先を当てる
    m = mk(model).fit(X[tr], ly[tr]); true = mape(y[fu], np.exp(m.predict(X[fu])))
    return shuf, tsplit, true


def main():
    quick = "--quick" in sys.argv
    rng = np.random.default_rng(SEED)
    n_series = 10 if quick else N_SERIES
    rows = []; example = None
    t = np.arange(N_TRAIN + N_FUT)
    for s in range(n_series):
        y = make_series(rng)
        if s == 0: example = y
        for name, X, model in [("日付の特徴量＋勾配ブースティング", feats_calendar(t), "gbm"),
                               ("日付の特徴量＋線形回帰", feats_calendar(t), "ridge"),
                               ("28日以上前の実績＋勾配ブースティング", feats_lag(y, t), "gbm")]:
            a, b, c = evaluate(X, y, N_TRAIN, model, s, N_FUT)
            rows.append(dict(series=s, setting=name, shuffled=a, time_ordered=b, future=c))
    df = pd.DataFrame(rows); df.round(3).to_csv(RES / "simulated_series.csv", index=False)
    pd.DataFrame({"day": t, "demand": np.round(example, 2)}).to_csv(DATA / "example_series.csv", index=False)

    summ = []
    for name, g in df.groupby("setting", sort=False):
        summ.append(dict(setting=name, shuffled=round(g.shuffled.median(), 2), time_ordered=round(g.time_ordered.median(), 2),
                         future=round(g.future.median(), 2),
                         shuffled_over_future=round((g.shuffled / g.future).median(), 2),
                         time_over_future=round((g.time_ordered / g.future).median(), 2),
                         shuffled_below_future=round(float((g.shuffled < g.future).mean() * 100), 1),
                         time_below_future=round(float((g.time_ordered < g.future).mean() * 100), 1),
                         shuffled_less_than_half=round(float((g.shuffled < 0.5 * g.future).mean() * 100), 1),
                         time_less_than_half=round(float((g.time_ordered < 0.5 * g.future).mean() * 100), 1)))
    summ = pd.DataFrame(summ); summ.to_csv(RES / "summary_simulated.csv", index=False)

    # --- 続くずれの強さを変える（日付の特徴量＋勾配ブースティング） ---
    sweep = []
    Xc = feats_calendar(t)
    for rho, drift, lab in [(0.0, 0.0, "続くずれなし"), (0.5, 0.0, "弱い（0.5）"), (0.9, 0.0, "強い（0.9）"), (0.9, 0.01, "強い＋水準が動く")]:
        rs = []
        r2 = np.random.default_rng(SEED + int(rho * 10) + int(drift * 1000))
        for s in range(4 if quick else 16):
            y = make_series(r2, rho=rho, drift=drift)
            rs.append(evaluate(Xc, y, N_TRAIN, "gbm", s, N_FUT))
        rs = np.array(rs)
        sweep.append(dict(case=lab, shuffled=round(float(np.median(rs[:, 0])), 2), time_ordered=round(float(np.median(rs[:, 1])), 2),
                          future=round(float(np.median(rs[:, 2])), 2),
                          shuffled_over_future=round(float(np.median(rs[:, 0] / rs[:, 2])), 2),
                          time_over_future=round(float(np.median(rs[:, 1] / rs[:, 2])), 2)))
    sweep = pd.DataFrame(sweep); sweep.to_csv(RES / "sweep_persistence.csv", index=False)

    # --- 本物の月次：商業動態統計 6業態 ---
    m = pd.read_csv(DATA / "meti_sales_monthly.csv", parse_dates=["ym"])
    real = []
    for g, d in m.groupby("gyotai", sort=False):
        d = d.sort_values("ym"); y = d.sales.to_numpy(float); n = len(y); tt = np.arange(n); mon = d.ym.dt.month.to_numpy()
        X = np.column_stack([tt] + [(mon == k).astype(float) for k in range(1, 13)])
        for model, lab in [("gbm", "勾配ブースティング"), ("ridge", "線形回帰")]:
            a, b, c = evaluate(X, y, n - 24, model, 0, 24)
            real.append(dict(gyotai=g, model=lab, months=n, shuffled=round(a, 2), time_ordered=round(b, 2), future=round(c, 2)))
    real = pd.DataFrame(real); real.to_csv(RES / "real_monthly.csv", index=False)

    out = {"n_series": int(n_series), "train_days": N_TRAIN, "future_days": N_FUT,
           "summary": summ.to_dict("records"), "sweep": sweep.to_dict("records"), "real": real.to_dict("records"),
           "real_gbm_shuffled_below_future": int(((real.model == "勾配ブースティング") & (real.shuffled < real.future)).sum()),
           "real_gbm_median_ratio_shuffled": round(float((real[real.model == "勾配ブースティング"].shuffled / real[real.model == "勾配ブースティング"].future).median()), 2),
           "real_gbm_median_ratio_time": round(float((real[real.model == "勾配ブースティング"].time_ordered / real[real.model == "勾配ブースティング"].future).median()), 2)}
    json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

    # --- 図1：3つの組み合わせの中央値 ---
    fig, ax = plt.subplots(figsize=(9, 4.3))
    x = np.arange(len(summ)); w = 0.26
    for j, (k, lab, c) in enumerate([("shuffled", "ばらばらに分けて確かめた誤差", ORANGE), ("time_ordered", "時間の順に分けて確かめた誤差", BLUE), ("future", "実際に先の半年を当てた誤差", INK)]):
        ax.bar(x + (j - 1) * w, summ[k], w, color=c, label=lab)
        for xx, v in zip(x + (j - 1) * w, summ[k]): ax.text(xx, v + 0.2, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels([s.replace("＋", "\n＋") for s in summ.setting], fontsize=9.5)
    ax.set_ylabel("誤差（MAPE、%。50本の中央値）"); ax.set_ylim(0, summ[["shuffled", "time_ordered", "future"]].to_numpy().max() * 1.3); ax.legend(frameon=False, fontsize=9.5, loc="upper center", ncol=3)
    ax.set_title("ばらばらに分けると、実際の先の誤差よりずっと小さく見える")
    save(fig, "a362_three_estimates.png", SRC + "。日次3年分で学び、その先の182日を当てる。交差検証は5分割")

    # --- 図2：1本ごとの散らばり（日付の特徴量＋勾配ブースティング） ---
    g = df[df.setting == "日付の特徴量＋勾配ブースティング"]
    fig, ax = plt.subplots(figsize=(6.6, 5.2))
    mx = max(g.future.max(), g.time_ordered.max()) * 1.05
    ax.plot([0, mx], [0, mx], color=GRAY, lw=1, ls="--"); ax.text(mx * 0.97, mx * 0.99, "見積もり＝実際", ha="right", va="top", fontsize=9, color=GRAY)
    ax.scatter(g.future, g.shuffled, s=18, color=ORANGE, alpha=0.75, label="ばらばらに分けた見積もり")
    ax.scatter(g.future, g.time_ordered, s=18, color=BLUE, alpha=0.75, label="時間の順に分けた見積もり")
    ax.set_xlim(0, mx); ax.set_ylim(0, mx); ax.set_xlabel("実際に先の半年を当てた誤差（MAPE、%）"); ax.set_ylabel("事前の見積もり（MAPE、%）")
    ax.set_title("ばらばらの見積もりは、実際の誤差が大きくても小さいまま"); ax.legend(frameon=False, loc="upper left")
    save(fig, "a362_scatter.png", SRC + "。日付の特徴量＋勾配ブースティング、50本")

    # --- 図3：続くずれの強さ ---
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    x = np.arange(len(sweep)); w = 0.38
    ax.bar(x - w / 2, sweep.shuffled_over_future, w, color=ORANGE, label="ばらばらに分けた見積もり ÷ 実際")
    ax.bar(x + w / 2, sweep.time_over_future, w, color=BLUE, label="時間の順に分けた見積もり ÷ 実際")
    for xx, v in zip(x - w / 2, sweep.shuffled_over_future): ax.text(xx, v + 0.02, f"{v:.2f}", ha="center", fontsize=9.5)
    for xx, v in zip(x + w / 2, sweep.time_over_future): ax.text(xx, v + 0.02, f"{v:.2f}", ha="center", fontsize=9.5)
    ax.axhline(1, color=GRAY, lw=1, ls="--"); ax.set_xticks(x); ax.set_xticklabels(sweep.case)
    ax.set_ylabel("見積もり ÷ 実際の誤差（1なら正確）"); ax.set_ylim(0, 1.6); ax.legend(frameon=False, fontsize=9.5, loc="upper left")
    ax.set_title("日ごとのずれが続くデータほど、ばらばらの見積もりは甘くなる")
    save(fig, "a362_persistence.png", SRC + "。日付の特徴量＋勾配ブースティング、各16本の中央値")
    print(summ.to_string()); print(sweep.to_string()); print(real.to_string())
    print({k: out[k] for k in out if k.startswith("real_")})


if __name__ == "__main__":
    main()
