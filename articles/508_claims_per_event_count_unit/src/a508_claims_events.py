"""508 同じ事故の複数の請求を別々の損害として数えると、1件あたりの額と大きな損害の層の見積もりはどれだけずれるのか（保険数理・リスク）

架空の事故と請求を作る。1つの事故から請求が1〜5件出て、事故の損害額を請求に分ける。
  事故の数   ：年にポアソン(200)
  事故の損害 ：対数正規（中央値300万円、σ=1.4）
  請求の数   ：1件 55%、2件 20%、3件 12%、4件 8%、5件 5%（大きな事故ほど請求が多くなりやすい）
  分け方     ：ディリクレ分布で事故の額を請求に分ける
層（1事故あたり 5,000万円を超えて 2億円まで＝「1.5億円 xs 5,000万円」）の年間の期待損害を、
  事故単位（正しい数え方）／請求単位（請求を別々の損害として数える）
の2通りで、①観測した値をそのまま使う ②対数正規を当てはめて計算する、で比べる。
"""
import json
import numpy as np, pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 508
SRC = "架空の事故と請求（作成者が乱数で作成、seed 508）"
YEARS, LAM = 10, 200
MED, SIG = 3e6, 1.4
DED, LIM = 5e7, 1.5e8                     # 層：5,000万円を超えて1.5億円分


def make(rng, years=YEARS, lam=LAM, tie=True):
    n_ev = rng.poisson(lam, years)
    ev = pd.DataFrame({"year": np.repeat(np.arange(2016, 2016 + years), n_ev)})
    ev["event"] = range(len(ev))
    ev["loss"] = rng.lognormal(np.log(MED), SIG, len(ev))
    if tie:   # 大きな事故ほど請求が多い：額の順位で請求数の確率を傾ける
        u = stats.norm.cdf(0.6 * stats.norm.ppf((ev.loss.rank() - 0.5) / len(ev)) + 0.8 * rng.standard_normal(len(ev)))
    else:
        u = rng.random(len(ev))
    cut = np.cumsum([0.55, 0.20, 0.12, 0.08, 0.05])
    ev["n_claims"] = np.searchsorted(cut, u * 0.999999) + 1
    cl = []
    for r in ev.itertuples():
        w = rng.dirichlet(np.full(r.n_claims, 1.0))
        for j, s in enumerate(w):
            cl.append((r.event, r.year, j, r.loss * s))
    cl = pd.DataFrame(cl, columns=["event", "year", "claim_no", "amount"])
    return ev, cl


def layer_mean_emp(x):
    return np.clip(x - DED, 0, LIM)


def layer_mean_lognorm(mu, s):
    """対数正規の1件あたりの層の期待値 E[min(max(X-d,0), l)] = E[X∧(d+l)] - E[X∧d]"""
    def lev(u):
        z = (np.log(u) - mu) / s
        return np.exp(mu + s**2 / 2) * stats.norm.cdf(z - s) + u * (1 - stats.norm.cdf(z))
    return lev(DED + LIM) - lev(DED)


def summary(x, per_year):
    lx = np.log(x); mu, s = lx.mean(), lx.std(ddof=0)
    return dict(count_per_year=len(x) / per_year, mean=x.mean(), median=np.median(x),
                q99_emp=np.quantile(x, 0.99), q99_fit=float(np.exp(mu + s * stats.norm.ppf(0.99))),
                mu=mu, s=s, n_over_ded=int((x > DED).sum()),
                layer_emp=layer_mean_emp(x).sum() / per_year,
                layer_fit=len(x) / per_year * layer_mean_lognorm(mu, s))


def main():
    rng = np.random.default_rng(SEED)
    ev, cl = make(rng)
    ev.to_csv(DATA / "fictional_events.csv", index=False); cl.round(0).to_csv(DATA / "fictional_claims.csv", index=False)
    E, C = summary(ev.loss.to_numpy(), YEARS), summary(cl.amount.to_numpy(), YEARS)
    # 本当の層の期待損害：事故の真の分布から解析的に
    true_layer = LAM * layer_mean_lognorm(np.log(MED), SIG)
    tab = pd.DataFrame({"事故単位": E, "請求単位": C}).T
    tab["true_layer_per_year"] = true_layer
    tab.round(3).to_csv(RES / "event_vs_claim.csv")

    # くり返し：100回作り直して、請求単位の層の見積もりが事故単位の何%になるか
    rep = []
    for k in range(100):
        r2 = np.random.default_rng(SEED * 1000 + k)
        for tie in [True, False]:
            e2, c2 = make(r2, tie=tie)
            a, b = summary(e2.loss.to_numpy(), YEARS), summary(c2.amount.to_numpy(), YEARS)
            rep.append(dict(rep=k, tie=tie, layer_emp_ratio=b["layer_emp"] / a["layer_emp"] if a["layer_emp"] > 0 else np.nan,
                            layer_fit_ratio=b["layer_fit"] / a["layer_fit"], layer_fit_event_vs_true=a["layer_fit"] / true_layer,
                            layer_emp_event_vs_true=a["layer_emp"] / true_layer,
                            q99_ratio=b["q99_emp"] / a["q99_emp"], mean_ratio=b["mean"] / a["mean"], count_ratio=b["count_per_year"] / a["count_per_year"]))
    rep = pd.DataFrame(rep); rep.round(4).to_csv(RES / "repeat100.csv", index=False)
    rs = rep.groupby("tie").median(numeric_only=True).drop(columns="rep")

    f = lambda v: float(round(v, 3))
    out = dict(seed=SEED, years=YEARS, lam=LAM, layer=f"{LIM/1e8:g}億円 xs {DED/1e4:,.0f}万円",
               n_events=len(ev), n_claims=len(cl), claims_per_event=f(len(cl) / len(ev)),
               event={k: f(v) for k, v in E.items()}, claim={k: f(v) for k, v in C.items()},
               true_layer_per_year=f(true_layer),
               repeat_median=rs.round(3).reset_index().to_dict("records"))
    json.dump(out, open(RES / "a508_main.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ["n_events", "n_claims", "claims_per_event", "true_layer_per_year"]}))
    print(tab[["count_per_year", "mean", "median", "q99_emp", "q99_fit", "n_over_ded", "layer_emp", "layer_fit"]].round(0).to_string())
    print(rs.round(3).to_string())

    # 図1：件数・平均・99%点の比較
    fig, axs = plt.subplots(1, 3, figsize=(9.6, 3.9))
    for ax, (key, lab, sc, unit) in zip(axs, [("count_per_year", "年あたりの件数", 1, "件"), ("mean", "1件あたりの平均額", 1e4, "万円"), ("q99_emp", "1件の99%点", 1e4, "万円")]):
        v = [E[key] / sc, C[key] / sc]
        ax.bar(["事故単位", "請求単位"], v, color=[BLUE, ORANGE], width=0.6)
        for i, t in enumerate(v):
            ax.text(i, t, f"{t:,.0f}", ha="center", va="bottom", fontsize=10)
        ax.set_title(lab + f"（{unit}）", fontsize=11); ax.set_yticks([])
        ax.spines["left"].set_visible(False)
    fig.suptitle(f"同じ{len(ev):,}件の事故を、請求{len(cl):,}件として数えると", fontsize=13, y=1.05)
    save(fig, "a508_count_mean.png", SRC + "。10年分")

    # 図2：裾（超える確率×年あたり件数＝その額を超える件数が年に何件か）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for x, col, lab in [(ev.loss.to_numpy(), BLUE, "事故単位"), (cl.amount.to_numpy(), ORANGE, "請求単位")]:
        xs = np.sort(x)[::-1]; k = np.arange(1, len(xs) + 1) / YEARS
        ax.plot(xs / 1e4, k, color=col, lw=2, label=lab)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.axvline(DED / 1e4, color=GRAY, ls="--", lw=1); ax.text(DED / 1e4 * 1.08, 60, "層の下限\n5,000万円", color=GRAY, fontsize=9)
    ax.set_xlabel("1件の額（万円、対数目盛）"); ax.set_ylabel("この額を超える件数（年あたり、対数目盛）")
    ax.set_title("大きな額のところで、請求単位は件数を少なく見せる")
    ax.legend(frameon=False)
    save(fig, "a508_tail.png", SRC + "。10年分の観測")

    # 図3：層の期待損害（年あたり）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    labs = ["事故単位\n観測そのまま", "事故単位\n対数正規の当てはめ", "請求単位\n観測そのまま", "請求単位\n対数正規の当てはめ"]
    v = [E["layer_emp"], E["layer_fit"], C["layer_emp"], C["layer_fit"]]
    ax.bar(labs, np.array(v) / 1e4, color=[BLUE, LIGHT, ORANGE, "#f3b49a"], width=0.6)
    ax.axhline(true_layer / 1e4, color=INK, ls="--", lw=1); ax.text(3.35, true_layer / 1e4, "本当の値", va="bottom", ha="right", fontsize=9)
    for i, t in enumerate(v):
        ax.text(i, t / 1e4, f"{t/1e4:,.0f}", ha="center", va="bottom", fontsize=10)
    ax.set_ylabel("層の期待損害（万円／年）")
    ax.set_title(f"層「{LIM/1e8:g}億円 xs 5,000万円」の年あたりの期待損害")
    save(fig, "a508_layer.png", SRC + "。本当の値は、置いた事故の分布から計算")


if __name__ == "__main__":
    main()
