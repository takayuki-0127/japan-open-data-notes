"""334 要因を1つずつ見た事故率の差は、まとめて推定するとどれだけ変わるか（架空の契約、seed 334）"""
import json, itertools
import numpy as np, pandas as pd
import statsmodels.api as sm
from common import *

SEED, REPS, N = 334, 200, 200_000
BASE = 0.05                                                   # 基準の区分（35〜59歳・地方・普通車）の事故率
TRUE = {"age": {"35〜59歳": 1.0, "34歳以下": 1.6, "60歳以上": 1.2},
        "area": {"地方": 1.0, "都市": 1.3},
        "car": {"普通車": 1.0, "スポーツ型": 1.4, "軽": 0.9}}
MARG = {"age": [0.5, 0.25, 0.25], "area": [0.5, 0.5], "car": [0.6, 0.15, 0.25]}
LEV = {k: list(v) for k, v in TRUE.items()}


def cell_probs(t):
    """区分の組み合わせ（3×2×3=18通り）の契約の割合。t=0 なら要因どうしは無関係、t が大きいほど
    「若い人は都市に多く、スポーツ型に多い」「60歳以上は地方に多く、軽に多い」という偏りが強まる"""
    p = {}
    for a, r, c in itertools.product(range(3), range(2), range(3)):
        w = MARG["age"][a] * MARG["area"][r] * MARG["car"][c]
        w *= np.exp(t * ((a == 1) * (r == 1) * 1.2 + (a == 1) * (c == 1) * 1.6 + (a == 2) * (r == 0) * 1.0 + (a == 2) * (c == 2) * 1.0 + (r == 1) * (c == 1) * 0.6))
        p[(a, r, c)] = w
    s = sum(p.values()); return {k: v / s for k, v in p.items()}


def true_rate(a, r, c, inter=1.0):
    m = BASE * list(TRUE["age"].values())[a] * list(TRUE["area"].values())[r] * list(TRUE["car"].values())[c]
    return m * (inter if (a == 1 and c == 1) else 1.0)       # inter≠1 なら「若い×スポーツ型」だけ掛け算からずれる


def draw(rng, t, n=N, inter=1.0):
    p = cell_probs(t); keys = list(p)
    cnt = rng.multinomial(n, [p[k] for k in keys])
    claims = rng.poisson([cnt[i] * true_rate(*k, inter) for i, k in enumerate(keys)])
    return pd.DataFrame({"age": [k[0] for k in keys], "area": [k[1] for k in keys], "car": [k[2] for k in keys], "n": cnt, "claims": claims})


def one_way(df):
    """1要因ずつ：その区分の事故率 ÷ 基準の区分の事故率"""
    out = {}
    for f in ("age", "area", "car"):
        g = df.groupby(f)[["claims", "n"]].sum(); r = g.claims / g.n
        for l in range(1, len(r)): out[(f, l)] = r[l] / r[0]
    return out


def glm(df):
    """まとめて推定：ポアソン回帰（対数リンク、契約数をオフセット）"""
    d = df[df.n > 0]
    X = pd.get_dummies(d[["age", "area", "car"]].astype(str), drop_first=True).astype(float)
    X = sm.add_constant(X)
    m = sm.GLM(d.claims, X, family=sm.families.Poisson(), offset=np.log(d.n)).fit()
    return {(c.split("_")[0], int(c.split("_")[1])): float(np.exp(m.params[c])) for c in X.columns if c != "const"}, float(np.exp(m.params["const"]))


def truth_rel():
    return {(f, l): list(TRUE[f].values())[l] for f in TRUE for l in range(1, len(TRUE[f]))}


def name(k): return f"{LEV[k[0]][k[1]]}"


def experiment(rng, t, n=N, inter=1.0, reps=REPS):
    ow = {k: [] for k in truth_rel()}; gl = {k: [] for k in truth_rel()}; prem = {"ow": [], "glm": []}; base = []
    for _ in range(reps):
        df = draw(rng, t, n, inter); o = one_way(df); g, b0 = glm(df); base.append(b0)
        for k in ow: ow[k].append(o[k]); gl[k].append(g[k])
        # 「34歳以下×都市×スポーツ型」の料率（基準の何倍か）
        prem["ow"].append(o[("age", 1)] * o[("area", 1)] * o[("car", 1)]); prem["glm"].append(g[("age", 1)] * g[("area", 1)] * g[("car", 1)])
    return ow, gl, prem


def main():
    rng = np.random.default_rng(SEED); tr = truth_rel(); TS = [0.0, 0.25, 0.5, 0.75, 1.0]
    res = dict(settings=dict(seed=SEED, reps=REPS, n=N, base=BASE, true=TRUE, marginals=MARG)); rows = []
    for t in TS:
        ow, gl, prem = experiment(rng, t)
        p = cell_probs(t); young_sport = sum(v for k, v in p.items() if k[0] == 1 and k[2] == 1) / sum(v for k, v in p.items() if k[0] == 1)
        other_sport = sum(v for k, v in p.items() if k[0] != 1 and k[2] == 1) / sum(v for k, v in p.items() if k[0] != 1)
        young_city = sum(v for k, v in p.items() if k[0] == 1 and k[1] == 1) / sum(v for k, v in p.items() if k[0] == 1)
        for k in tr:
            rows.append(dict(t=t, factor=k[0], level=name(k), true=tr[k], one_way=float(np.mean(ow[k])), glm=float(np.mean(gl[k])),
                             one_way_err_pct=float(100 * (np.mean(ow[k]) / tr[k] - 1)), glm_err_pct=float(100 * (np.mean(gl[k]) / tr[k] - 1)),
                             glm_sd_pct=float(100 * np.std(gl[k]) / tr[k]), one_way_sd_pct=float(100 * np.std(ow[k]) / tr[k]),
                             one_way_excess_err_pct=float(100 * ((np.mean(ow[k]) - 1) / (tr[k] - 1) - 1))))
        true_prem = 1.6 * 1.3 * 1.4
        rows.append(dict(t=t, factor="cell", level="34歳以下×都市×スポーツ型", true=true_prem, one_way=float(np.mean(prem["ow"])), glm=float(np.mean(prem["glm"])),
                         one_way_err_pct=float(100 * (np.mean(prem["ow"]) / true_prem - 1)), glm_err_pct=float(100 * (np.mean(prem["glm"]) / true_prem - 1)),
                         glm_sd_pct=float(100 * np.std(prem["glm"]) / true_prem), one_way_sd_pct=float(100 * np.std(prem["ow"]) / true_prem)))
        res[f"mix_t{t}"] = dict(young_sport_share=young_sport, other_sport_share=other_sport, young_city_share=young_city)
    T = pd.DataFrame(rows); T.round(4).to_csv(RES / "relativities.csv", index=False)
    # 契約の数を変える（偏り t=0.75）
    size = {}
    for n in (5_000, 20_000, 200_000):
        ow, gl, prem = experiment(rng, 0.75, n=n)
        size[str(n)] = {name(k): dict(one_way_rmse_pct=float(100 * np.sqrt(np.mean((np.array(ow[k]) / tr[k] - 1) ** 2))),
                                     glm_rmse_pct=float(100 * np.sqrt(np.mean((np.array(gl[k]) / tr[k] - 1) ** 2)))) for k in tr}
    res["by_size"] = size
    # 掛け算からずれる組み合わせがあるとき（若い×スポーツ型が 1.3倍 余分に高い、偏り t=0.75）
    ow, gl, prem = experiment(rng, 0.75, inter=1.3)
    res["interaction"] = dict(true_cell=1.6 * 1.3 * 1.4 * 1.3, one_way_cell=float(np.mean(prem["ow"])), glm_cell=float(np.mean(prem["glm"])),
                              glm_rel={name(k): float(np.mean(gl[k])) for k in tr}, one_way_rel={name(k): float(np.mean(ow[k])) for k in tr})
    json.dump(res, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    ex = draw(np.random.default_rng(SEED), 0.75); ex["age"] = ex.age.map(dict(enumerate(LEV["age"]))); ex["area"] = ex.area.map(dict(enumerate(LEV["area"]))); ex["car"] = ex.car.map(dict(enumerate(LEV["car"])))
    ex.to_csv(DATA / "example_portfolio_t075.csv", index=False)

    # 図1：偏り t=0.75 での 1要因ずつ・まとめて・正解
    g = T[(T.t == 0.75) & (T.factor != "cell")]; fig, ax = plt.subplots(figsize=(8.4, 4.3)); x = np.arange(len(g)); w = 0.27
    ax.bar(x - w, g.true, w, color=GRAY, label="正解（置いた値）"); ax.bar(x, g.one_way, w, color=ORANGE, label="1要因ずつ集計")
    ax.bar(x + w, g.glm, w, color=BLUE, label="まとめて推定（ポアソン回帰）")
    for i, (a, b, c) in enumerate(zip(g.true, g.one_way, g.glm)):
        ax.text(i - w, a + .02, f"{a:.2f}", ha="center", fontsize=8); ax.text(i, b + .02, f"{b:.2f}", ha="center", fontsize=8); ax.text(i + w, c + .02, f"{c:.2f}", ha="center", fontsize=8)
    ax.axhline(1, color=INK, lw=.8); ax.set_xticks(x); ax.set_xticklabels(g.level); ax.set_ylabel("基準の区分に対する事故率の倍率"); ax.set_ylim(0.6, 2.35)
    ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper right"); ax.set_title("1要因ずつ見ると、ほかの要因の分まで拾って倍率が大きく出る")
    save(fig, "a334_relativities.png", "架空の契約20万件×200回の平均（偏りの強さ0.75、seed 334）。基準は 35〜59歳・地方・普通車")

    # 図2：偏りの強さと、1要因ずつのずれ
    fig, ax = plt.subplots(figsize=(8, 4.3)); cols = [ORANGE, BLUE, GREEN, "#8a5cc2", GRAY]
    for (k, c) in zip(tr, cols):
        d = T[(T.factor == k[0]) & (T.level == name(k))]; ax.plot(d.t, d.one_way_err_pct, "o-", color=c, label=name(k))
    d = T[T.factor == "cell"]; ax.plot(d.t, d.one_way_err_pct, "s--", color=INK, label="3つを掛けた料率（34歳以下×都市×スポーツ型）")
    ax.axhline(0, color=GRAY, lw=1); ax.set_xlabel("要因どうしの偏りの強さ（0＝無関係）"); ax.set_ylabel("1要因ずつの倍率の、正解からのずれ（%）")
    ax.legend(frameon=False, fontsize=8.5); ax.set_title("要因どうしが偏るほど、1要因ずつの倍率は正解から離れる")
    save(fig, "a334_error_by_association.png", "架空の契約20万件×200回の平均。まとめて推定した倍率のずれは、どの強さでも±0.4%以内")

    # 図3：契約の数と、推定の揺れ（偏り0.75）
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4), sharey=True); labs = [name(k) for k in tr]
    for ax, key, ttl in zip(axes, ("one_way_rmse_pct", "glm_rmse_pct"), ("1要因ずつ集計", "まとめて推定")):
        for n, c in zip(size, (ORANGE, BLUE, GREEN)):
            ax.plot(range(len(labs)), [size[n][l][key] for l in labs], "o-", color=c, label=f"{int(n):,}件")
        ax.set_xticks(range(len(labs))); ax.set_xticklabels(labs, fontsize=8); ax.set_title(ttl, fontsize=11)
    axes[0].set_ylabel("倍率の誤差の大きさ（RMSE、%）"); axes[0].legend(title="契約の数", frameon=False, fontsize=9)
    fig.suptitle("1要因ずつのずれは契約を増やしても残り、まとめて推定の揺れは契約が増えると縮む", y=1.02)
    save(fig, "a334_error_by_size.png", "架空の契約（偏りの強さ0.75、200回）。RMSE は偏りと揺れを合わせた誤差", y=-0.05)
    print(T[["t", "level", "true", "one_way", "glm", "one_way_err_pct", "glm_err_pct", "glm_sd_pct", "one_way_excess_err_pct"]].round(3).to_string())
    print(json.dumps(size, ensure_ascii=False)); print(json.dumps(res["interaction"], ensure_ascii=False)); print({k: v for k, v in res.items() if k.startswith("mix")})


if __name__ == "__main__":
    main()
