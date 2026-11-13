"""569 死亡率の実績と予定の比（A/E）を、件数で見るか保険金額で見るかで、どれだけ違うか（架空の保有契約）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SRC = "架空の保有契約と死亡率（作成者が乱数で作成、seed 569）。記事569"
N = 50_000
REPS = 500

def q_expected(age):
    """予定の死亡率（架空。Gompertz–Makeham）"""
    mu = 0.0002 + 0.000012 * 1.105 ** (age + .5)
    return 1 - np.exp(-mu)

def portfolio(rng, sigma):
    age = rng.integers(30, 71, N)
    si = rng.lognormal(np.log(1000), sigma, N)          # 保険金額（万円）、中央値1,000万円
    return age, si

def one(rng, age, si, beta):
    qe = q_expected(age)
    qa = np.minimum(qe * (si / 1000) ** (-beta), 1)    # 金額が大きいほど死亡率が低い（beta>0）
    d = rng.random(N) < qa
    ae_n = d.sum() / qe.sum()
    ae_a = (si * d).sum() / (si * qe).sum()
    # 95% 区間（正規近似）：件数は Var=Σq(1-q)、金額は Var=Σ si² q(1-q)
    se_n = np.sqrt((qe * (1 - qe)).sum()) / qe.sum()
    se_a = np.sqrt((si ** 2 * qe * (1 - qe)).sum()) / (si * qe).sum()
    return dict(ae_n=ae_n, ae_a=ae_a, se_n=se_n, se_a=se_a, deaths=int(d.sum()), exp_n=qe.sum(),
                true_n=qa.sum() / qe.sum(), true_a=(si * qa).sum() / (si * qe).sum()), d

def main():
    rng = np.random.default_rng(569)
    rows = []; keep = {}
    for sigma in (0.5, 0.8, 1.2):
        age, si = portfolio(rng, sigma)
        for beta in (0.0, 0.2):
            out = [one(rng, age, si, beta)[0] for _ in range(REPS)]
            D = pd.DataFrame(out)
            cover_n = np.mean(np.abs(D.ae_n - D.true_n) <= 1.96 * D.se_n)
            cover_a = np.mean(np.abs(D.ae_a - D.true_a) <= 1.96 * D.se_a)
            rows.append(dict(sigma=sigma, beta=beta, mean_ae_n=D.ae_n.mean(), mean_ae_a=D.ae_a.mean(),
                             true_n=D.true_n.iloc[0], true_a=D.true_a.iloc[0],
                             sd_ae_n=D.ae_n.std(), sd_ae_a=D.ae_a.std(), half_n=1.96 * D.se_n.mean(), half_a=1.96 * D.se_a.mean(),
                             cover_n=cover_n, cover_a=cover_a, mean_deaths=D.deaths.mean(),
                             top1pct_share_si=float(np.sort(si)[::-1][:N // 100].sum() / si.sum())))
            keep[(sigma, beta)] = D
    T = pd.DataFrame(rows); T.to_csv(RES / "summary.csv", index=False)

    # 金額の帯ごとの件数の A/E（sigma=0.8, beta=0.2。同じ契約で200回分の死亡を合わせる）
    age, si = portfolio(np.random.default_rng(5691), .8)
    rg = np.random.default_rng(5692)
    r, d = one(rg, age, si, .2)
    qe = q_expected(age)
    P = pd.DataFrame(dict(age=age, sum_insured=si.round(2), q_expected=qe, death=d.astype(int)))
    P.to_csv(RES / "example_portfolio.csv", index=False)
    band = pd.qcut(si, 5, labels=["下位20%", "20〜40%", "40〜60%", "60〜80%", "上位20%"])
    dsum = d.astype(int).copy()
    for _ in range(199):
        dsum += one(rg, age, si, .2)[1]
    Bd = pd.DataFrame(dict(band=band, deaths=dsum, expected=qe * 200, si=si)).groupby("band", observed=True).agg(
        n=("si", "size"), deaths=("deaths", "sum"), expected=("expected", "sum"), si_share=("si", "sum")).reset_index()
    Bd["ae"] = Bd.deaths / Bd.expected; Bd["si_share"] = Bd.si_share / Bd.si_share.sum(); Bd["band"] = Bd.band.astype(str)
    Bd.to_csv(RES / "by_band_200years.csv", index=False)

    con = duckdb.connect(); con.execute("SET threads=1"); con.register("policies", P)
    q = con.execute((SQL / "a569_ae.sql").read_text()).df(); q.to_csv(RES / "sql_example.csv", index=False)
    match = bool(np.isclose(q.ae_count.iloc[0], r["ae_n"], rtol=1e-12) and np.isclose(q.ae_amount.iloc[0], (P.sum_insured * P.death).sum() / (P.sum_insured * P.q_expected).sum(), rtol=1e-12))

    J = dict(N=N, reps=REPS, summary=T.round(5).to_dict("records"), example=dict(ae_n=r["ae_n"], ae_a=r["ae_a"], deaths=r["deaths"]),
             by_band=Bd.round(4).to_dict("records"), sql_check=dict(sql=q.round(8).to_dict("records")[0], match=match))
    json.dump(J, open(RES / "a569_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：500回の A/E の分布（sigma=0.8）
    fig, ax = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for i, beta in enumerate((0.0, 0.2)):
        D = keep[(.8, beta)]; bins = np.linspace(.6, 1.6, 51)
        ax[i].hist(D.ae_n, bins, color=BLUE, alpha=.7, label="件数で見た A/E")
        ax[i].hist(D.ae_a, bins, color=ORANGE, alpha=.6, label="金額で見た A/E")
        ax[i].axvline(1, color=INK, lw=.8)
        ttl = "金額と死亡率が関係なし" if beta == 0 else "金額が大きいほど死亡率が低い"
        ax[i].set_title(f"{ttl}\n件数 平均{D.ae_n.mean():.2f}・金額 平均{D.ae_a.mean():.2f}", fontsize=11)
        ax[i].set_xlabel("A/E（実績 ÷ 予定）")
    ax[0].set_ylabel("回数（500回中）"); ax[0].legend(fontsize=8.5)
    save(fig, "a569_hist.png", SRC)

    # 図2：金額の帯ごとの件数の A/E
    fig, ax = plt.subplots(figsize=(8, 4.2))
    b = ax.bar(Bd.band, Bd.ae, color=[LIGHT, LIGHT, LIGHT, LIGHT, BLUE]); ax.bar_label(b, fmt="%.2f")
    ax2 = ax.twinx(); ax2.plot(Bd.band, Bd.si_share * 100, "o-", color=ORANGE); ax2.set_ylabel("保険金額の合計に占める割合（%）", color=ORANGE)
    ax2.spines["right"].set_visible(True)
    ax.axhline(1, color=INK, lw=.8); ax.set_ylabel("件数で見た A/E"); ax.set_xlabel("保険金額の大きさ（5等分）")
    ax.set_title("金額の大きい契約ほど A/E が低く、金額では重く数えられる（200回分を合計）")
    save(fig, "a569_by_band.png", SRC)

    # 図3：金額のばらつきと区間の幅
    t = T[T.beta == 0]
    fig, ax = plt.subplots(figsize=(8, 4.2)); xs = np.arange(len(t)); w = .38
    b1 = ax.bar(xs - w / 2, t.half_n, w, color=BLUE, label="件数で見た A/E"); b2 = ax.bar(xs + w / 2, t.half_a, w, color=ORANGE, label="金額で見た A/E")
    ax.bar_label(b1, fmt="±%.3f", fontsize=9); ax.bar_label(b2, fmt="±%.3f", fontsize=9)
    ax.set_xticks(xs, [f"σ={s}\n（上位1%の金額が{p*100:.0f}%）" for s, p in zip(t.sigma, t.top1pct_share_si)])
    ax.set_ylabel("95%区間の半分の幅"); ax.set_xlabel("保険金額のばらつき（対数正規のσ）")
    ax.set_title("金額がばらつくほど、金額で見た A/E の区間は広い"); ax.legend()
    save(fig, "a569_ci_width.png", SRC, y=-0.07)
    print(T.round(4).to_string()); print(Bd.round(3).to_string()); print(J["sql_check"], J["example"])

if __name__ == "__main__":
    main()
