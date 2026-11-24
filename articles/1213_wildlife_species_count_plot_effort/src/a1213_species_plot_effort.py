"""1213 調べた区画の数が違う2つの森で、見つかった種の数をそのまま比べると、何がずれるのか？（架空のデータ）

作成者が置いた架空の2つの森。A森には本当に80種、B森には60種がいる（本当はA森のほうが多い）。
種ごとに「1つの区画で見つかる確率」を置き、A森は見つかりにくい珍しい種が多く、B森はどの種も見つかりやすい。
A森は10区画、B森は40区画を調べたとき、見つかった種の数を
  ①そのまま ②1区画あたり（種の数÷区画の数） ③同じ区画の数（10区画）にそろえる
の3つの読み方で比べ、「A森のほうが多い」と正しく読める割合を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1213
SRC = "架空の2つの森（作成者が乱数で作成、seed 1213）"
REPS = 2000
SHAPES = {   # 1区画で見つかる確率の置き方（対数オッズの平均・標準偏差）
    "珍しい種が多い": (-3.2, 1.5),
    "B森と同じ形": (-1.6, 1.0),
    "見つかりやすい種が多い": (-0.8, 0.8),
}
B_SHAPE = (-1.6, 1.0)
N_A_TRUE, N_B_TRUE = 80, 60
BASE_PLOTS = (10, 40)


def r(x, d=3):
    return round(float(x), d)


def q(a, p):
    return float(np.quantile(a, p))


def make_forest(z, shape):
    """z：種ごとの標準の乱数（形を変えても同じ z を使い、種の並びをそろえる）"""
    m, s = shape
    return 1 / (1 + np.exp(-(m + s * z)))


def expected_curve(p, ns):
    return np.array([(1 - (1 - p) ** n).sum() for n in ns])


def survey(rng, p, n_plots):
    """区画ごとに種が見つかったか（区画×種）"""
    return rng.random((n_plots, p.size)) < p[None, :]


def rarefy(found, n):
    """調べた区画から n 区画を選ぶすべての選び方で、見つかる種の数の平均（式で出す）"""
    N = found.shape[0]
    k = found.sum(axis=0)
    k = k[k > 0]
    miss = np.ones(k.size)
    for j in range(n):
        miss *= np.clip((N - k - j) / (N - j), 0, None)
    return float((1 - miss).sum())


def judge(sa, sb):
    """A>B なら1、同じなら0.5、A<B なら0"""
    return np.where(sa > sb, 1.0, np.where(sa == sb, 0.5, 0.0))


def compare(rng, pa, pb, na, nb, reps):
    s_raw = np.zeros((reps, 2)); s_rar = np.zeros((reps, 2))
    for i in range(reps):
        fa = survey(rng, pa, na); fb = survey(rng, pb, nb)
        sa = fa.any(axis=0).sum(); sb = fb.any(axis=0).sum()
        s_raw[i] = [sa, sb]
        m = min(na, nb)
        s_rar[i] = [rarefy(fa, m) if na > m else sa, rarefy(fb, m) if nb > m else sb]
    per = s_raw / np.array([na, nb])[None, :]
    return dict(raw=s_raw, per=per, rar=s_rar,
                p_raw=judge(s_raw[:, 0], s_raw[:, 1]).mean(),
                p_per=judge(per[:, 0], per[:, 1]).mean(),
                p_rar=judge(np.round(s_rar[:, 0], 6), np.round(s_rar[:, 1], 6)).mean())


def main():
    rng = np.random.default_rng(SEED)
    za = rng.standard_normal(N_A_TRUE)
    zb = rng.standard_normal(N_B_TRUE)
    pa = make_forest(za, SHAPES["珍しい種が多い"])
    pb = make_forest(zb, B_SHAPE)
    pd.DataFrame({"forest": ["A"] * N_A_TRUE + ["B"] * N_B_TRUE,
                  "species_id": list(range(1, N_A_TRUE + 1)) + list(range(1, N_B_TRUE + 1)),
                  "p_found_in_one_plot": np.round(np.concatenate([pa, pb]), 5)}).to_csv(DATA / "species.csv", index=False)

    out = {"setup": {"true_species": {"A森": N_A_TRUE, "B森": N_B_TRUE}, "plots": {"A森": BASE_PLOTS[0], "B森": BASE_PLOTS[1]},
                     "reps": REPS,
                     "median_p": {"A森": r(np.median(pa), 4), "B森": r(np.median(pb), 4)},
                     "species_p_below_5pct": {"A森": int((pa < 0.05).sum()), "B森": int((pb < 0.05).sum())}}}

    # ---- 置いた見つかる確率からの見つかる種の数（式） ----
    ns = [1, 2, 5, 10, 20, 40, 80, 160, 320, 640]
    ca, cb = expected_curve(pa, ns), expected_curve(pb, ns)
    curve = pd.DataFrame({"区画の数": ns, "A森_見つかる種の数_式": np.round(ca, 2), "B森_見つかる種の数_式": np.round(cb, 2)})
    curve.to_csv(RES / "expected_curve.csv", index=False)
    nn = np.arange(1, 641)
    da = expected_curve(pa, nn) - expected_curve(pb, nn)
    cross = int(nn[np.argmax(da > 0)])
    out["expected"] = {"cross_plots": cross,
                       "A10": r(ca[ns.index(10)], 2), "B10": r(cb[ns.index(10)], 2), "B40": r(cb[ns.index(40)], 2),
                       "A40": r(ca[ns.index(40)], 2), "A640": r(ca[-1], 2), "B640": r(cb[-1], 2)}

    # ---- 基本：A森10区画、B森40区画 ----
    res = compare(rng, pa, pb, BASE_PLOTS[0], BASE_PLOTS[1], REPS)
    rows = []
    for key, name, unit in [("raw", "そのまま", "種"), ("per", "1区画あたり", "種/区画"), ("rar", "10区画にそろえる", "種")]:
        x = res[key]
        rows.append({"読み方": name, "A森_平均": r(x[:, 0].mean(), 2), "B森_平均": r(x[:, 1].mean(), 2), "単位": unit,
                     "A森が多いと読めた割合%": r(res["p_" + key] * 100, 2)})
    base_df = pd.DataFrame(rows)
    base_df.to_csv(RES / "base_readings.csv", index=False)
    out["base"] = rows
    out["base_raw_B_minus_A_10_90"] = [r(q(res["raw"][:, 1] - res["raw"][:, 0], 0.1), 1), r(q(res["raw"][:, 1] - res["raw"][:, 0], 0.9), 1)]

    # ---- そろえる区画の数を変える（両方の森を640区画まで調べたとして） ----
    matched = []
    for n in [5, 10, 20, 40, 80, 160, 320]:
        sa_ = np.zeros(400); sb_ = np.zeros(400)
        for i in range(400):
            sa_[i] = survey(rng, pa, n).any(axis=0).sum()
            sb_[i] = survey(rng, pb, n).any(axis=0).sum()
        matched.append({"そろえた区画の数": n, "A森_平均": r(sa_.mean(), 2), "B森_平均": r(sb_.mean(), 2),
                        "A森が多いと読めた割合%": r(judge(sa_, sb_).mean() * 100, 2)})
    mdf = pd.DataFrame(matched)
    mdf.to_csv(RES / "matched_plots.csv", index=False)
    out["matched"] = matched

    # ---- 確かめ：A森の区画×B森の区画×A森の種の形 の27通り ----
    grid = []
    for shape_name, shape in SHAPES.items():
        pa_g = make_forest(za, shape)
        for na in [5, 20, 80]:
            for nb in [5, 20, 80]:
                rr = compare(rng, pa_g, pb, na, nb, 400)
                grid.append({"A森の種の形": shape_name, "A森の区画": na, "B森の区画": nb,
                             "そのまま%": r(rr["p_raw"] * 100, 2), "1区画あたり%": r(rr["p_per"] * 100, 2),
                             "同じ区画にそろえる%": r(rr["p_rar"] * 100, 2),
                             "A森_そのまま平均": r(rr["raw"][:, 0].mean(), 2), "B森_そのまま平均": r(rr["raw"][:, 1].mean(), 2)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)
    summ = {}
    for col in ["そのまま%", "1区画あたり%", "同じ区画にそろえる%"]:
        summ[col] = {"min": r(g[col].min(), 2), "max": r(g[col].max(), 2),
                     "below50_count": int((g[col] < 50).sum())}
    summ["by_shape_rar"] = {k: [r(v.min(), 2), r(v.max(), 2)] for k, v in g.groupby("A森の種の形", sort=False)["同じ区画にそろえる%"]}
    summ["by_shape_raw"] = {k: [r(v.min(), 2), r(v.max(), 2)] for k, v in g.groupby("A森の種の形", sort=False)["そのまま%"]}
    summ["by_shape_per"] = {k: [r(v.min(), 2), r(v.max(), 2)] for k, v in g.groupby("A森の種の形", sort=False)["1区画あたり%"]}
    fewer, more = g[g["A森の区画"] < g["B森の区画"]], g[g["A森の区画"] > g["B森の区画"]]
    summ["per_when_A_fewer_plots"] = {"n": len(fewer), "min": r(fewer["1区画あたり%"].min(), 2), "max": r(fewer["1区画あたり%"].max(), 2)}
    summ["per_when_A_more_plots"] = {"n": len(more), "min": r(more["1区画あたり%"].min(), 2), "max": r(more["1区画あたり%"].max(), 2)}
    same = g[g["A森の区画"] == g["B森の区画"]]
    summ["raw_by_plots"] = {"A_more": [r(more["そのまま%"].min(), 2), r(more["そのまま%"].max(), 2)],
                            "A_fewer": [r(fewer["そのまま%"].min(), 2), r(fewer["そのまま%"].max(), 2)],
                            "equal": [r(same["そのまま%"].min(), 2), r(same["そのまま%"].max(), 2)]}
    rare = g[g["A森の種の形"] == "珍しい種が多い"]
    summ["rare_rar_by_matched_plots"] = {int(k): [r(v.min(), 2), r(v.max(), 2)] for k, v in
                                         rare.groupby(rare[["A森の区画", "B森の区画"]].min(axis=1))["同じ区画にそろえる%"]}
    out["grid"] = summ

    # ---- 図1：区画の数と見つかる種の数（式） ----
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.plot(nn, expected_curve(pa, nn), color=ORANGE, lw=2, label=f"A森（本当は{N_A_TRUE}種、珍しい種が多い）")
    ax.plot(nn, expected_curve(pb, nn), color=BLUE, lw=2, label=f"B森（本当は{N_B_TRUE}種）")
    ax.axhline(N_A_TRUE, color=ORANGE, ls=":", lw=1); ax.axhline(N_B_TRUE, color=BLUE, ls=":", lw=1)
    ax.scatter([10], [ca[ns.index(10)]], color=ORANGE, zorder=4); ax.scatter([40], [cb[ns.index(40)]], color=BLUE, zorder=4)
    ax.annotate(f"A森10区画：{ca[ns.index(10)]:.2f}種", (10, ca[ns.index(10)]), (14, 22), fontsize=9, color=ORANGE,
                arrowprops=dict(arrowstyle="-", color=ORANGE, lw=0.8))
    ax.annotate(f"B森40区画：{cb[ns.index(40)]:.2f}種", (40, cb[ns.index(40)]), (60, 45), fontsize=9, color=BLUE,
                arrowprops=dict(arrowstyle="-", color=BLUE, lw=0.8))
    ax.axvline(cross, color=GRAY, lw=0.8, ls="--")
    ax.text(cross * 1.08, 5, f"{cross}区画より多く\n調べるとA森が上", fontsize=9, color=INK)
    ax.set_xscale("log"); ax.set_xlim(1, 640); ax.set_ylim(0, 85)
    ax.set_xticks([1, 5, 10, 40, 100, 640]); ax.set_xticklabels(["1", "5", "10", "40", "100", "640"])
    ax.set_xlabel("調べた区画の数（対数の目盛り）"); ax.set_ylabel("見つかる種の数（置いた確率からの式）")
    ax.set_title("調べた区画が増えるほど、見つかる種の数は伸びる")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    save(fig, "a1213_curve.png", SRC)

    # ---- 図2：3つの読み方で「A森が多い」と読めた割合 ----
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    vals = base_df["A森が多いと読めた割合%"].tolist()
    cols = [ORANGE, GRAY, BLUE]
    ax.barh(range(3), vals, color=cols)
    for i, v in enumerate(vals):
        ax.text(v + 1, i, f"{v:g}%", va="center", fontsize=10)
    ax.set_yticks(range(3)); ax.set_yticklabels(["そのまま\n（A森10区画、B森40区画）", "1区画あたり", "10区画にそろえる"])
    ax.invert_yaxis(); ax.set_xlim(0, 110)
    ax.set_xlabel("本当に多いA森を「多い」と読めた割合（%、2,000回）")
    ax.set_title("本当はA森80種、B森60種：3つの読み方で「A森が多い」と読めた割合", fontsize=11.5)
    save(fig, "a1213_readings.png", SRC)

    # ---- 図3：そろえる区画の数で入れかわる ----
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.plot(mdf["そろえた区画の数"], mdf["A森が多いと読めた割合%"], marker="o", color=INK)
    for _, rw in mdf.iterrows():
        side = rw["そろえた区画の数"] in (20, 40)
        ax.annotate(f"{rw['A森が多いと読めた割合%']:g}%", (rw["そろえた区画の数"], rw["A森が多いと読めた割合%"]),
                    xytext=(-6 if side else 0, 6 if side else 8), textcoords="offset points",
                    ha="right" if side else "center", fontsize=8.5)
    ax.axhline(50, color=GRAY, lw=0.8, ls="--")
    ax.set_xscale("log"); ax.set_xticks(mdf["そろえた区画の数"]); ax.set_xticklabels(mdf["そろえた区画の数"])
    ax.set_ylim(0, 110)
    ax.set_xlabel("両方の森で同じ数だけ調べた区画（対数の目盛り）")
    ax.set_ylabel("A森が多いと読めた割合（%）")
    ax.set_title("区画をそろえても、そろえた数で答えが入れかわる（各400回）")
    save(fig, "a1213_matched.png", SRC)

    with open(RES / "a1213_main.json", "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)
    print(curve.to_string()); print(base_df.to_string()); print(mdf.to_string()); print(g.to_string())
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
