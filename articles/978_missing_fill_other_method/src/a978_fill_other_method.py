"""978 欠けたところだけ別の方法で埋めると、何が混ざるのか？（架空のデータ）

架空の3店（A・B・C）の会員6,000人のアンケート。会員ごとに「本当の満足度」（0〜10点）を置き、
答えなかった人（満足度が欠けた人）だけを、別の方法（式で予測・電話で聞き直し）で埋める。
全員の本当の点で数えた値と、埋めたあとの値を比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 978
SRC = "架空の会員アンケート（作成者が乱数で作成、seed 978）"
N_PER = 2000
STORES = np.array(["A", "B", "C"])
STORE_EFF = {"A": 0.0, "B": 0.3, "C": -0.3}
BASE_MISS = {"A": 0.15, "B": 0.25, "C": 0.40}
METHODS = ["除く", "利用回数だけの式で埋める", "利用回数・店・新サービスの式で埋める",
           "同じ式＋散らばりを足して埋める", "電話で聞き直して埋める"]


def expit(v):
    return 1 / (1 + np.exp(-v))


def logit(p):
    return np.log(p / (1 - p))


def make(rng, zlink=0.6, scale=1.0):
    store = np.repeat(STORES, N_PER)
    x = rng.normal(0, 1, len(store))                      # 利用の多さ（標準化）
    visits = np.round(np.exp(1.2 + 0.5 * x)).astype(int)  # 月の利用回数（表示用）
    z = (rng.random(len(store)) < expit(-0.4 + zlink * x)).astype(int)  # 新サービスを使った
    eff = np.vectorize(STORE_EFF.get)(store)
    y = np.clip(6.0 + eff + 0.5 * x + 0.8 * z + rng.normal(0, 1.3, len(store)), 0, 10)
    base = np.vectorize(BASE_MISS.get)(store) * scale
    miss = rng.random(len(store)) < expit(logit(base) - 0.5 * x)
    return pd.DataFrame({"store": store, "x": x, "visits": visits, "new_service": z, "true": y, "missing": miss})


def design(df, cols):
    X = [np.ones(len(df))]
    for c in cols:
        if c == "x":
            X.append(df["x"].values)
        elif c == "store":
            X.append((df["store"] == "B").values.astype(float)); X.append((df["store"] == "C").values.astype(float))
        elif c == "z":
            X.append(df["new_service"].values.astype(float))
    return np.column_stack(X)


def fit_fill(df, cols, rng=None):
    obs = ~df["missing"].values
    X = design(df, cols)
    beta, *_ = np.linalg.lstsq(X[obs], df["true"].values[obs], rcond=None)
    pred = X @ beta
    if rng is not None:
        sd = np.std(df["true"].values[obs] - pred[obs], ddof=X.shape[1])
        pred = pred + rng.normal(0, sd, len(df))
    pred = np.clip(pred, 0, 10)
    y = df["true"].values.copy()
    y[~obs] = pred[~obs]
    return y


def filled(df, method, rng, mode=0.6):
    """method ごとの満足度の列（除くは欠けた行を NaN）"""
    y = df["true"].values.copy()
    m = df["missing"].values
    if method == METHODS[0]:
        y[m] = np.nan
        return y
    if method == METHODS[1]:
        return fit_fill(df, ["x"])
    if method == METHODS[2]:
        return fit_fill(df, ["x", "store", "z"])
    if method == METHODS[3]:
        return fit_fill(df, ["x", "store", "z"], rng)
    y[m] = np.clip(y[m] + mode, 0, 10)                    # 電話では高めに答えると置く
    return y


def measures(df, y):
    ok = ~np.isnan(y)
    s, z, x = df["store"].values[ok], df["new_service"].values[ok], df["x"].values[ok]
    v = y[ok]
    return {"mean": v.mean(), "diff_z": v[z == 1].mean() - v[z == 0].mean(),
            "diff_CA": v[s == "C"].mean() - v[s == "A"].mean(), "sd": v.std(),
            "corr_x": np.corrcoef(x, v)[0, 1], "share_ge8": (v >= 8).mean() * 100}


KEYS = ["mean", "diff_z", "diff_CA", "sd", "corr_x", "share_ge8"]


def run(rng, reps, zlink=0.6, scale=1.0, mode=0.6, methods=METHODS):
    rows = []
    for r in range(reps):
        df = make(rng, zlink, scale)
        tr = measures(df, df["true"].values)
        miss = df["missing"].values
        extra = {"miss_share": miss.mean() * 100,
                 "miss_A": miss[df.store == "A"].mean() * 100, "miss_C": miss[df.store == "C"].mean() * 100}
        for mth in methods:
            es = measures(df, filled(df, mth, rng, mode))
            row = {"rep": r, "method": mth, **extra}
            for k in KEYS:
                row["true_" + k] = tr[k]; row["est_" + k] = es[k]; row["bias_" + k] = es[k] - tr[k]
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)

    # 1回分（data/members.csv）
    df = make(np.random.default_rng(SEED))
    out_df = df[["store", "visits", "new_service", "true", "missing"]].copy()
    out_df.insert(0, "member_id", np.arange(1, len(df) + 1))
    r1 = np.random.default_rng(SEED + 1)
    for mth, col in zip(METHODS, ["drop", "fill_visits", "fill_full", "fill_full_noise", "fill_phone"]):
        out_df[col] = filled(df, mth, r1)
    out_df.to_csv(DATA / "members.csv", index=False, float_format="%.3f")
    miss = df["missing"].values
    y2 = out_df["fill_visits"].values
    one = {"n": int(len(df)), "missing": int(miss.sum()), "missing_share": round(miss.mean() * 100, 2),
           "missing_by_store": {s: round(miss[df.store == s].mean() * 100, 2) for s in STORES},
           # 利用回数だけの式で埋めた行の中での、新サービスの差（測った行は本当の点）
           "fill_visits_diff_z_filled_rows": round(float(y2[miss & (df.new_service == 1)].mean() - y2[miss & (df.new_service == 0)].mean()), 3),
           "true_diff_z_filled_rows": round(float(df.true[miss & (df.new_service == 1)].mean() - df.true[miss & (df.new_service == 0)].mean()), 3),
           "true_diff_z_all": round(float(df.true[df.new_service == 1].mean() - df.true[df.new_service == 0].mean()), 3)}

    # 2) 基本の置き方、200回
    base = run(rng, 200)
    g = base.groupby("method", sort=False)
    summ = pd.DataFrame({k: g["bias_" + k].mean() for k in KEYS})
    summ.columns = ["bias_" + k for k in KEYS]
    truth = base[base.method == METHODS[0]][["true_" + k for k in KEYS]].mean()
    est = pd.DataFrame({k: g["est_" + k].mean() for k in KEYS})
    summ.round(4).to_csv(RES / "methods_base.csv")
    sd_rep = pd.DataFrame({k: g["est_" + k].std() for k in ["diff_z", "diff_CA"]}).round(4)
    miss_share = base[base.method == METHODS[0]][["miss_share", "miss_A", "miss_C"]].mean()

    # 3) 確かめ：欠ける割合×新サービスと利用の多さのつながり（各50回、式で埋める3つと除く）
    grid = []
    for scale in [0.5, 1.0, 1.5]:
        for zl in [0.0, 0.6]:
            d = run(np.random.default_rng(SEED * 10 + int(scale * 10) + int(zl * 100)), 50, zl, scale,
                    methods=METHODS[:4])
            gg = d.groupby("method", sort=False)
            for mth in METHODS[:4]:
                q = gg.get_group(mth)
                grid.append({"miss_scale": scale, "zlink": zl, "method": mth,
                             "miss_share": round(q.miss_share.mean(), 2),
                             "true_diff_z": round(q.true_diff_z.mean(), 4),
                             "bias_diff_z": round(q.bias_diff_z.mean(), 4),
                             "bias_diff_CA": round(q.bias_diff_CA.mean(), 4),
                             "bias_sd": round(q.bias_sd.mean(), 4), "bias_corr_x": round(q.bias_corr_x.mean(), 4)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_fill_model.csv", index=False)

    # 4) 確かめ：電話で高めに答える大きさ×欠ける割合（各50回）。式：ずれ＝高めの分×欠けた割合
    gphone = []
    for scale in [0.5, 1.0, 1.5]:
        for mode in [0.0, 0.3, 0.6, 1.0]:
            d = run(np.random.default_rng(SEED * 100 + int(scale * 10) + int(mode * 100)), 50, 0.6, scale, mode,
                    methods=[METHODS[4]])
            gphone.append({"miss_scale": scale, "mode": mode, "miss_share": round(d.miss_share.mean(), 2),
                           "miss_A": round(d.miss_A.mean(), 2), "miss_C": round(d.miss_C.mean(), 2),
                           "bias_mean": round(d.bias_mean.mean(), 4),
                           "formula_mean": round(mode * d.miss_share.mean() / 100, 4),
                           "bias_diff_CA": round(d.bias_diff_CA.mean(), 4),
                           "formula_diff_CA": round(mode * (d.miss_C.mean() - d.miss_A.mean()) / 100, 4),
                           "bias_diff_z": round(d.bias_diff_z.mean(), 4)})
    gphone = pd.DataFrame(gphone)
    gphone.to_csv(RES / "grid_phone.csv", index=False)

    out = {"one_draw": one,
           "base_200reps": {"truth": {k: round(float(truth["true_" + k]), 4) for k in KEYS},
                            "missing_share": {k: round(float(v), 2) for k, v in miss_share.items()},
                            "estimate": {m: {k: round(float(est.loc[m, k]), 4) for k in KEYS} for m in METHODS},
                            "bias": {m: {k: round(float(summ.loc[m, "bias_" + k]), 4) for k in KEYS} for m in METHODS},
                            "sd_over_reps": {m: {k: float(sd_rep.loc[m, k]) for k in sd_rep.columns} for m in METHODS}},
           "grid_fill_model": {"bias_diff_z_range_fill_visits": [float(grid[grid.method == METHODS[1]].bias_diff_z.min()),
                                                                 float(grid[grid.method == METHODS[1]].bias_diff_z.max())],
                               "bias_diff_z_range_fill_noise": [float(grid[grid.method == METHODS[3]].bias_diff_z.min()),
                                                                float(grid[grid.method == METHODS[3]].bias_diff_z.max())],
                               "bias_sd_range_fill_full": [float(grid[grid.method == METHODS[2]].bias_sd.min()),
                                                           float(grid[grid.method == METHODS[2]].bias_sd.max())]},
           "grid_phone": {"max_abs_gap_mean_vs_formula": round(float((gphone.bias_mean - gphone.formula_mean).abs().max()), 4),
                          "max_abs_gap_CA_vs_formula": round(float((gphone.bias_diff_CA - gphone.formula_diff_CA).abs().max()), 4),
                          "bias_diff_CA_range": [float(gphone.bias_diff_CA.min()), float(gphone.bias_diff_CA.max())]}}
    json.dump(out, open(RES / "a978_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：利用回数と満足度（1回分）。測った点と、利用回数だけの式で埋めた点
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.scatter(df.x[~miss], df.true[~miss], s=5, color=BLUE, alpha=.3, lw=0, label="答えた人（本当の点）")
    ax.scatter(df.x[miss], y2[miss], s=5, color=ORANGE, alpha=.8, lw=0, label="答えなかった人を利用回数だけの式で埋めた点")
    ax.set_xlabel("利用の多さ（平均0・標準偏差1にそろえた値）"); ax.set_ylabel("満足度（0〜10点）")
    ax.set_ylim(0, 10.3)
    ax.legend(frameon=False, fontsize=9, loc="lower right", markerscale=3)
    ax.set_title("式で埋めた点は1本の線の上に並び、新サービスや店の違いを持たない")
    save(fig, "a978_scatter.png", SRC)

    # 図2：埋め方ごとのずれ（200回の平均）
    lab = ["除く", "利用回数だけの式", "利用回数・店・\n新サービスの式", "同じ式＋散らばり", "電話で聞き直し"]
    panels = [("diff_z", "新サービスを使った人と\n使わない人の差のずれ（点）"),
              ("diff_CA", "C店−A店の差のずれ（点）"),
              ("sd", "標準偏差のずれ（点）"), ("corr_x", "利用の多さとの相関のずれ")]
    fig, axes = plt.subplots(2, 2, figsize=(8.6, 6.0))
    for ax, (k, t) in zip(axes.ravel(), panels):
        v = summ["bias_" + k].values
        cols = [GRAY, ORANGE, BLUE, GREEN, INK]
        ax.barh(range(5)[::-1], v, color=cols)
        ax.set_yticks(range(5)[::-1]); ax.set_yticklabels(lab, fontsize=8.5)
        ax.axvline(0, color=INK, lw=.8)
        lim = max(abs(v).max() * 1.45, 0.05)
        ax.set_xlim(-lim, lim)
        for i, val in zip(range(5)[::-1], v):
            ax.text(val + (lim * 0.03 if val >= 0 else -lim * 0.03), i, f"{val:+.3f}", va="center",
                    ha="left" if val >= 0 else "right", fontsize=8)
        ax.set_title(t, fontsize=10)
    fig.suptitle("埋め方ごとの、全員の本当の点で数えた値とのずれ（200回の平均）", fontsize=12)
    fig.tight_layout()
    save(fig, "a978_methods.png", SRC)

    # 図3：電話で高めに答える分と、C店−A店の差のずれ
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for scale, c, lb in [(0.5, LIGHT, "欠ける割合0.5倍"), (1.0, BLUE, "1倍（基本）"), (1.5, INK, "1.5倍")]:
        q = gphone[gphone.miss_scale == scale]
        ax.plot(q["mode"], q.bias_diff_CA, "o", color=c, label=f"{lb}（数えた値）")
        ax.plot(q["mode"], q.formula_diff_CA, "--", color=c, lw=1)
    ax.set_xlabel("電話で答えると高めに出る分（点、作成者が置いた値）")
    ax.set_ylabel("C店−A店の差のずれ（点）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("電話で埋めた人の多い店ほど高く見える（点線は式：高めの分×欠けた割合の差）", fontsize=11)
    save(fig, "a978_phone.png", SRC, y=-0.05)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
