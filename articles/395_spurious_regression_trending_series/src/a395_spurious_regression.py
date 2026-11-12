"""A395 関係のない2つの右肩上がりの系列は、どれくらい「関係あり」と出てしまうのか。
架空の系列1,000組と、手元の公的統計の年次系列10本（45組）で、水準どうしの回帰と、前年との差どうしの回帰を比べる。
python a395_spurious_regression.py      # 全部を計算し直す（1分以内）
"""
import json, itertools
import numpy as np, pandas as pd
from scipy import stats
from common import *
SEED = 395
SRC = "出典：架空のデータ（作成者が乱数で作成、seed 395）"
TS, PAIRS, DRIFT = (20, 30, 50, 100, 200), 1000, 0.2
METHODS = ["水準どうし", "水準どうし＋年（時間）を入れる", "前年との差どうし"]


def resid_on_trend(v):
    """各行から、直線の傾き（年）で説明できる分を引く"""
    t = np.arange(v.shape[1]) - (v.shape[1] - 1) / 2
    return v - v.mean(1, keepdims=True) - ((v * t).sum(1) / (t * t).sum())[:, None] * t


def slope_test(x, y, k=2):
    """行ごとに y ~ x（切片つき）。p値、相関、ダービン・ワトソン比を返す。k は使った係数の数（年を入れたら3）"""
    a, c = x - x.mean(1, keepdims=True), y - y.mean(1, keepdims=True); n = x.shape[1]
    b = (a * c).sum(1) / (a * a).sum(1); res = c - b[:, None] * a
    se = np.sqrt((res ** 2).sum(1) / (n - k) / (a * a).sum(1))
    r = (a * c).sum(1) / np.sqrt((a * a).sum(1) * (c * c).sum(1))
    dw = (np.diff(res, axis=1) ** 2).sum(1) / (res ** 2).sum(1)
    return 2 * stats.t.sf(np.abs(b / se), n - k), r, dw


def three(x, y):
    out = {}
    out[METHODS[0]] = slope_test(x, y)
    out[METHODS[1]] = slope_test(resid_on_trend(x), resid_on_trend(y), 3)
    out[METHODS[2]] = slope_test(np.diff(x, axis=1), np.diff(y, axis=1))
    return out


def gen(rng, kind, T, n=PAIRS):
    e = rng.normal(0, 1, (n, T))
    if kind == "上り坂のある酔歩": return np.cumsum(DRIFT + e, axis=1)
    if kind == "上り坂のない酔歩": return np.cumsum(e, axis=1)
    if kind == "直線の傾き＋その年かぎりの揺れ": return DRIFT * np.arange(T) + e
    raise ValueError(kind)


KINDS = ["上り坂のある酔歩", "上り坂のない酔歩", "直線の傾き＋その年かぎりの揺れ"]


def simulate(rng):
    rec = []
    for kind in KINDS:
        for T in TS:
            x, y = gen(rng, kind, T), gen(rng, kind, T)                 # 互いに関係のない2本
            for m, (p, r, dw) in three(x, y).items():
                rec.append(dict(kind=kind, T=T, method=m, significant_pct=100 * (p < 0.05).mean(), p001_pct=100 * (p < 0.001).mean(),
                                abs_r_median=np.median(np.abs(r)), abs_r_over_07_pct=100 * (np.abs(r) > 0.7).mean(), dw_median=np.median(dw),
                                r2_over_dw_pct=100 * (r ** 2 > dw).mean()))
    return pd.DataFrame(rec)


def power(rng):
    """本当に関係がある組（y = 0.5×x + 揺れ、x は上り坂のある酔歩）を、差どうしの回帰は見つけられるか"""
    rec = []
    for T in TS:
        x = gen(rng, "上り坂のある酔歩", T); y = 0.5 * x + rng.normal(0, 1, (PAIRS, T))
        for m, (p, r, dw) in three(x, y).items():
            rec.append(dict(T=T, method=m, found_pct=100 * (p < 0.05).mean()))
    return pd.DataFrame(rec)


def public():
    df = pd.read_csv(DATA / "public_annual_series.csv").set_index("year"); names = list(df.columns); rec = []
    for a, b in itertools.combinations(names, 2):
        out = three(df[[a]].T.values, df[[b]].T.values)
        rec.append(dict(a=a, b=b, **{f"p_{i}": float(out[m][0][0]) for i, m in enumerate(METHODS)}, **{f"r_{i}": float(out[m][1][0]) for i, m in enumerate(METHODS)}, dw_levels=float(out[METHODS[0]][2][0])))
    return df, pd.DataFrame(rec)


def figures(sim, pw, df, pub, ex):
    x, y = ex; T = len(x)
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.5, 1]})
    ax[0].plot(range(T), x, color=BLUE, label="系列A"); ax[0].plot(range(T), y, color=ORANGE, label="系列B（Aとは別の乱数）"); ax[0].set_xlabel("年"); ax[0].set_title("互いに関係のない2本の系列（上り坂のある酔歩、50年分）"); ax[0].legend(frameon=False)
    r = np.corrcoef(x, y)[0, 1]; r2 = np.corrcoef(np.diff(x), np.diff(y))[0, 1]
    ax[1].scatter(x, y, s=14, color=BLUE); ax[1].set_xlabel("系列A"); ax[1].set_ylabel("系列B"); ax[1].set_title(f"水準どうしの相関 {r:.2f}\n（前年との差どうしでは {r2:.2f}）")
    save(fig, "a395_example_pair.png", SRC)
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True); C = [ORANGE, GREEN, BLUE]
    for a, kind in zip(ax, KINDS):
        for c, m in zip(C, METHODS):
            g = sim[(sim.kind == kind) & (sim.method == m)]; a.plot(range(len(TS)), g.significant_pct, "o-", color=c, label=m)
            for j, v in enumerate(g.significant_pct): a.text(j, v + 2.5, f"{v:.0f}", ha="center", fontsize=8.5, color=c)
        a.axhline(5, color=INK, lw=0.6, ls=":"); a.set_xticks(range(len(TS))); a.set_xticklabels([f"{t}年" for t in TS]); a.set_title(kind, fontsize=11); a.set_ylim(0, 112); a.set_xlabel("系列の長さ")
    ax[0].set_ylabel("「関係あり」（p<0.05）と出た割合（%）"); ax[2].legend(frameon=False, fontsize=9, loc="center right")
    fig.suptitle("関係のない2本の系列が「関係あり」と出た割合（1,000組ずつ。点線＝本来の5%）", y=1.02)
    save(fig, "a395_false_significance.png", SRC)
    names = list(df.columns); n = len(names)
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.6))
    for a, i, ttl in ((ax[0], 0, "水準どうし"), (ax[1], 2, "前年との差どうし")):
        M = np.full((n, n), np.nan)
        for _, rw in pub.iterrows():
            p, q = names.index(rw.a), names.index(rw.b); M[q, p] = abs(rw[f"r_{i}"])
        im = a.imshow(M, cmap="Blues", vmin=0, vmax=1)
        for _, rw in pub.iterrows():
            p, q = names.index(rw.a), names.index(rw.b); v = abs(rw[f"r_{i}"]); s = rw[f"p_{i}"] < 0.05
            a.text(p, q, f"{v:.2f}" + ("*" if s else ""), ha="center", va="center", fontsize=8, color="white" if v > 0.6 else INK)
        k = int((pub[f"p_{i}"] < 0.05).sum())
        a.set_xticks(range(n)); a.set_xticklabels(names, rotation=60, ha="right", fontsize=8); a.set_yticks(range(n)); a.set_yticklabels(names if a is ax[0] else [], fontsize=8)
        a.set_title(f"{ttl}：45組のうち{k}組が「関係あり」（*）"); [sp.set_visible(False) for sp in a.spines.values()]
    fig.suptitle("公的統計の年次系列10本（1962〜2023年）の相関の大きさ", y=0.98)
    save(fig, "a395_public_series_pairs.png", "出典：文部科学省「学校基本調査」、総務省統計局「労働力調査」、資源エネルギー庁「総合エネルギー統計」、内閣府「国民の祝日」、財務省「貿易統計」、農林水産省「作物統計」、気象庁の観測データをもとに作成者が加工して作成", y=-0.17)


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    sim = simulate(rng); pw = power(rng); df, pub = public()
    r2 = np.random.default_rng(SEED + 1); ex = (gen(r2, KINDS[0], 50, 1)[0], gen(r2, KINDS[0], 50, 1)[0])
    pd.DataFrame({"year": range(50), "series_a": ex[0], "series_b": ex[1]}).round(4).to_csv(DATA / "example_pair_50.csv", index=False)
    sim.round(3).to_csv(RES / "simulation.csv", index=False); pw.round(2).to_csv(RES / "power_true_relation.csv", index=False); pub.round(5).to_csv(RES / "public_pairs.csv", index=False)
    figures(sim, pw, df, pub, ex)
    g = lambda k, T, m, c: round(float(sim[(sim.kind == k) & (sim["T"] == T) & (sim.method == m)][c].iloc[0]), 2)
    main = {"seed": SEED, "pairs": PAIRS, "drift": DRIFT,
            "significant_pct": {k: {m: {str(T): g(k, T, m, "significant_pct") for T in TS} for m in METHODS} for k in KINDS},
            "levels_detail_drift_walk": {str(T): {c: g(KINDS[0], T, METHODS[0], c) for c in ("p001_pct", "abs_r_median", "abs_r_over_07_pct", "dw_median", "r2_over_dw_pct")} for T in TS},
            "levels_detail_no_drift": {str(T): {c: g(KINDS[1], T, METHODS[0], c) for c in ("p001_pct", "abs_r_median", "abs_r_over_07_pct", "dw_median", "r2_over_dw_pct")} for T in TS},
            "power": {m: {str(T): round(float(pw[(pw["T"] == T) & (pw.method == m)].found_pct.iloc[0]), 1) for T in TS} for m in METHODS},
            "public": {"years": [int(df.index.min()), int(df.index.max())], "pairs": len(pub), **{m: int((pub[f"p_{i}"] < 0.05).sum()) for i, m in enumerate(METHODS)},
                       "abs_r_median": {m: round(float(pub[f"r_{i}"].abs().median()), 2) for i, m in enumerate(METHODS)},
                       "abs_r_over_07": {m: int((pub[f"r_{i}"].abs() > 0.7).sum()) for i, m in enumerate(METHODS)}, "dw_levels_median": round(float(pub.dw_levels.median()), 2),
                       "diff_significant_pairs": pub[pub.p_2 < 0.05][["a", "b", "r_2", "p_2"]].round(3).values.tolist()},
            "example": {"r_levels": round(float(np.corrcoef(*ex)[0, 1]), 2), "r_diff": round(float(np.corrcoef(np.diff(ex[0]), np.diff(ex[1]))[0, 1]), 2)}}
    json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1); print(json.dumps(main, ensure_ascii=False, indent=1))
