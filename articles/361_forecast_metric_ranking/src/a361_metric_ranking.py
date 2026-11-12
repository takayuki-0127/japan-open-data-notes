"""A361 予測の良し悪しは、物差しを変えるとどれだけ順位が入れ替わるのか
架空の商品500本（よく売れる250本・たまに売れる250本）の日次需要に、5つの単純な予測を当て、
MAPE・MAE・RMSE・MASE で順位をつけて比べる。乱数の種は361。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED, N_FAST, N_SLOW, T, TEST = 361, 250, 250, 728, 56
MODELS = ["前日の値", "7日前の値", "直近28日の平均", "指数平滑", "同じ曜日の平均"]
METRICS = ["MAPE", "MAE", "RMSE", "MASE"]
SRC = "架空のデータ（作成者が乱数で作成、seed 361）"


def make_series(rng):
    """日次の需要。曜日の山、ゆるい伸び、負の二項分布のばらつき"""
    rows = []
    t = np.arange(T)
    for i in range(N_FAST + N_SLOW):
        fast = i < N_FAST
        base = np.exp(rng.uniform(np.log(20), np.log(200))) if fast else np.exp(rng.uniform(np.log(0.1), np.log(2.0)))
        dow = np.exp(rng.normal(0, 0.25 if fast else 0.15, 7)); dow /= dow.mean()
        trend = np.exp(rng.normal(0, 0.15) * (t / T))
        mu = base * dow[t % 7] * trend
        k = rng.uniform(3, 15) if fast else rng.uniform(0.3, 2.0)       # 小さいほどばらつきが大きい
        y = rng.negative_binomial(k, k / (k + mu))
        rows.append((i, "よく売れる" if fast else "たまに売れる", base, y))
    return rows


def forecasts(y):
    """1日先の予測を、最後の TEST 日について作る（その日までの実績はすべて使える）"""
    n = len(y); idx = np.arange(n - TEST, n)
    f = {}
    f["前日の値"] = y[idx - 1].astype(float)
    f["7日前の値"] = y[idx - 7].astype(float)
    c = np.concatenate([[0], np.cumsum(y)])
    f["直近28日の平均"] = (c[idx] - c[idx - 28]) / 28
    s = np.empty(n); s[0] = y[0]
    for j in range(1, n): s[j] = 0.2 * y[j] + 0.8 * s[j - 1]           # 指数平滑（α=0.2）
    f["指数平滑"] = s[idx - 1]
    f["同じ曜日の平均"] = np.mean([y[idx - 7 * w] for w in range(1, 9)], axis=0)   # 直近8週の同じ曜日
    return idx, f


def metrics(y, idx, fc):
    a = y[idx].astype(float); e = fc - a
    nz = a > 0
    mape = np.mean(np.abs(e[nz]) / a[nz]) * 100 if nz.any() else np.nan     # 実績0の日は計算できない
    mae = np.mean(np.abs(e)); rmse = np.sqrt(np.mean(e ** 2))
    tr = y[: idx[0]].astype(float)
    scale = np.mean(np.abs(tr[7:] - tr[:-7]))                               # 学習期間の「7日前の値」の誤差
    mase = mae / scale if scale > 0 else np.nan
    return mape, mae, rmse, mase, nz.mean()


def main():
    rng = np.random.default_rng(SEED)
    series = make_series(rng)
    recs = []
    for i, grp, base, y in series:
        idx, f = forecasts(y)
        for m in MODELS:
            mape, mae, rmse, mase, nzshare = metrics(y, idx, f[m])
            recs.append(dict(item=i, group=grp, base=base, model=m, MAPE=mape, MAE=mae, RMSE=rmse, MASE=mase,
                             bias=float(np.mean(f[m] - y[idx])), mean_test=float(y[idx].mean()),
                             zero_share=1 - nzshare))
    df = pd.DataFrame(recs)
    df.round(4).to_csv(RES / "scores_by_item_model.csv", index=False)
    ex = pd.DataFrame({"day": np.arange(T), "fast_example": series[0][3], "slow_example": series[N_FAST][3]})
    ex.to_csv(DATA / "example_two_items.csv", index=False)

    # --- 商品ごとの1位 ---
    best = {}
    for met in METRICS:
        p = df.pivot(index="item", columns="model", values=met)[MODELS]
        best[met] = p.idxmin(axis=1)
    best = pd.DataFrame(best); grp = df.drop_duplicates("item").set_index("item")["group"]
    best["group"] = grp
    best.to_csv(RES / "best_model_by_item.csv")
    out = {"n_items": int(len(best)), "test_days": TEST}
    pairs = [("MAPE", "MAE"), ("MAPE", "RMSE"), ("MAE", "RMSE"), ("MAE", "MASE"), ("MAPE", "MASE"), ("RMSE", "MASE")]
    dis = []
    for g in ["よく売れる", "たまに売れる", "全体"]:
        b = best if g == "全体" else best[best.group == g]
        ok = b["MAPE"].notna()
        row = {"group": g, "n": int(len(b)), "mape_defined": int(ok.sum())}
        for a_, b_ in pairs:
            sub = b[ok] if "MAPE" in (a_, b_) else b
            row[f"{a_}≠{b_}"] = round(float((sub[a_] != sub[b_]).mean() * 100), 1)
        sub = b[ok]
        row["4つとも同じ"] = round(float(((sub.MAPE == sub.MAE) & (sub.MAE == sub.RMSE)).mean() * 100), 1)
        dis.append(row)
    dis = pd.DataFrame(dis); dis.to_csv(RES / "disagreement.csv", index=False)
    out["disagreement"] = dis.to_dict("records")

    # --- 1位になった回数 ---
    win = []
    for g in ["よく売れる", "たまに売れる"]:
        b = best[best.group == g]
        for met in ["MAPE", "MAE", "RMSE"]:
            vc = b[met].value_counts(normalize=True).reindex(MODELS).fillna(0) * 100
            for m in MODELS: win.append(dict(group=g, metric=met, model=m, share=round(float(vc[m]), 1)))
    win = pd.DataFrame(win); win.to_csv(RES / "wins_by_metric.csv", index=False)
    out["wins"] = win.to_dict("records")

    # --- MAPE が壊れる ---
    it = df.drop_duplicates("item").set_index("item")
    slow = it[it.group == "たまに売れる"]; fast = it[it.group == "よく売れる"]
    out["zero_share_slow_median"] = round(float(slow.zero_share.median() * 100), 1)
    out["slow_any_zero_day"] = round(float((slow.zero_share > 0).mean() * 100), 1)
    out["slow_half_or_more_zero"] = round(float((slow.zero_share >= 0.5).mean() * 100), 1)
    out["slow_all_zero"] = round(float((slow.zero_share == 1).mean() * 100), 1)
    out["fast_any_zero_day"] = round(float((fast.zero_share > 0).mean() * 100), 1)
    # MAPE で1位のモデルは、低めに予測するモデルか（たまに売れる商品）
    sl = df[df.group == "たまに売れる"].merge(best[["MAPE", "MAE"]].rename(columns={"MAPE": "bM", "MAE": "bA"}),
                                                left_on="item", right_index=True)
    w_mape = sl[sl.model == sl.bM]; w_mae = sl[sl.model == sl.bA]
    out["slow_mape_winner_bias_ratio"] = round(float((w_mape.bias / w_mape.mean_test.replace(0, np.nan)).median() * 100), 1)
    out["slow_mae_winner_bias_ratio"] = round(float((w_mae.bias / w_mae.mean_test.replace(0, np.nan)).median() * 100), 1)
    out["slow_mape_winner_underforecast"] = round(float((w_mape.bias < 0).mean() * 100), 1)
    out["slow_mae_winner_underforecast"] = round(float((w_mae.bias < 0).mean() * 100), 1)
    # 「いつも0」と予測したら MAPE は100%。それより悪い（100%超）モデル×商品の割合
    out["slow_mape_over_100"] = round(float((sl.MAPE > 100).mean() * 100), 1)
    out["slow_best_mape_over_100"] = round(float((w_mape.MAPE > 100).mean() * 100), 1)
    zero_fc = []
    for i, g_, base, y in series[N_FAST:]:
        idx, f = forecasts(y); a = y[idx].astype(float)
        mae0 = np.mean(a); maes = [np.mean(np.abs(f[m] - a)) for m in MODELS]
        zero_fc.append(mae0 < min(maes))
    out["slow_zero_forecast_beats_all_mae"] = round(float(np.mean(zero_fc) * 100), 1)

    # --- 500本をまとめて1つのモデルを選ぶ ---
    agg = []
    for met in METRICS:
        mean = df.groupby("model")[met].mean().reindex(MODELS)
        med = df.groupby("model")[met].median().reindex(MODELS)
        for m in MODELS: agg.append(dict(metric=met, model=m, mean=round(float(mean[m]), 4), median=round(float(med[m]), 4)))
    tot = df.groupby("model")[["MAE"]].sum()
    agg = pd.DataFrame(agg); agg.to_csv(RES / "aggregate_choice.csv", index=False)
    choice = {}
    for met in METRICS:
        a = agg[agg.metric == met].set_index("model")
        choice[met + "の平均"] = a["mean"].idxmin(); choice[met + "の中央値"] = a["median"].idxmin()
    out["aggregate_choice"] = choice
    # RMSE の平均に占める「よく売れる」上位10%の商品の割合
    r = df[df.model == "指数平滑"].sort_values("RMSE", ascending=False)
    out["rmse_top10pct_share"] = round(float(r.RMSE.head(50).sum() / r.RMSE.sum() * 100), 1)
    m_ = df[df.model == "指数平滑"].dropna(subset=["MAPE"]).sort_values("MAPE", ascending=False)
    out["mape_slow_share_of_sum"] = round(float(m_[m_.group == "たまに売れる"].MAPE.sum() / m_.MAPE.sum() * 100), 1)
    json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

    # --- 図1：物差しの組ごとに、1位が違う商品の割合 ---
    fig, ax = plt.subplots(figsize=(8, 4.2))
    labs = ["MAPE と MAE", "MAPE と RMSE", "MAE と RMSE", "MAE と MASE"]; keys = ["MAPE≠MAE", "MAPE≠RMSE", "MAE≠RMSE", "MAE≠MASE"]
    x = np.arange(len(labs)); w = 0.38
    for j, (g, c) in enumerate([("よく売れる", BLUE), ("たまに売れる", ORANGE)]):
        v = [dis.set_index("group").loc[g, k] for k in keys]
        b = ax.bar(x + (j - 0.5) * w, v, w, color=c, label=g + "商品（250本）")
        for xx, vv in zip(x + (j - 0.5) * w, v): ax.text(xx, vv + 1, f"{vv:.0f}%", ha="center", fontsize=10, color=INK)
    ax.set_xticks(x); ax.set_xticklabels(labs); ax.set_ylabel("1位のモデルが違う商品の割合（%）"); ax.set_ylim(0, 100)
    ax.set_title("物差しを変えると、1位のモデルが変わる商品の割合"); ax.legend(frameon=False)
    save(fig, "a361_disagreement.png", SRC + "。5つの予測を商品ごとに順位づけ。MAPE は実績が0でない日だけで計算")

    # --- 図2：1位になった割合 ---
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    cols = [GRAY, LIGHT, BLUE, ORANGE, GREEN]
    for ax, g in zip(axes, ["よく売れる", "たまに売れる"]):
        x = np.arange(3); bottom = np.zeros(3)
        for m, c in zip(MODELS, cols):
            v = [float(win[(win.group == g) & (win.metric == met) & (win.model == m)].share.iloc[0]) for met in ["MAPE", "MAE", "RMSE"]]
            ax.bar(x, v, 0.6, bottom=bottom, color=c, label=m)
            for xx, vv, bb in zip(x, v, bottom):
                if vv >= 7: ax.text(xx, bb + vv / 2, f"{vv:.0f}", ha="center", va="center", fontsize=9, color="white" if c in (BLUE, ORANGE, GREEN) else INK)
            bottom += v
        ax.set_xticks(x); ax.set_xticklabels(["MAPE で選ぶ", "MAE で選ぶ", "RMSE で選ぶ"]); ax.set_title(g + "商品")
    axes[0].set_ylabel("1位になった商品の割合（%）"); axes[1].legend(frameon=False, fontsize=9, loc="center left", bbox_to_anchor=(1.0, 0.5))
    fig.suptitle("どのモデルが1位になるかは、物差しで入れ替わる", y=1.02, fontsize=13)
    save(fig, "a361_wins_by_metric.png", SRC + "。MAPE が計算できない商品（実績がすべて0）は MAPE の集計から除いた")

    # --- 図3：需要の大きさと、0の日の割合・MAPE ---
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    ax = axes[0]
    ax.scatter(slow.mean_test, slow.zero_share * 100, s=10, color=ORANGE, alpha=0.6, label="たまに売れる")
    ax.scatter(fast.mean_test, fast.zero_share * 100, s=10, color=BLUE, alpha=0.6, label="よく売れる")
    ax.set_xscale("log"); ax.set_xlabel("確かめた56日の平均の需要（個／日、対数の目盛り）"); ax.set_ylabel("実績が0の日の割合（%）")
    ax.set_title("需要が小さい商品は、MAPE を計算できない日が多い"); ax.legend(frameon=False)
    ax = axes[1]
    d = df[df.model == "指数平滑"].dropna(subset=["MAPE"])
    for g, c in [("たまに売れる", ORANGE), ("よく売れる", BLUE)]:
        s = d[d.group == g]; ax.scatter(s.mean_test, s.MAPE, s=10, color=c, alpha=0.6, label=g)
    ax.axhline(100, color=GRAY, lw=1, ls="--"); ax.text(d.mean_test.min(), 106, "いつも0と予測したときの MAPE＝100%", ha="left", fontsize=8.5, color=GRAY)
    ax.set_xscale("log"); ax.set_xlabel("確かめた56日の平均の需要（個／日、対数の目盛り）"); ax.set_ylabel("指数平滑の MAPE（%）")
    ax.set_title("需要が小さいほど、MAPE は大きく出る")
    save(fig, "a361_mape_breaks.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
