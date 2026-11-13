"""506 事故の件数と1件あたりの額が一緒に動くとき、別々に見積もった年間損害の「200年に1度」はどれだけ小さく出るのか（保険数理・リスク）

架空の年間損害を作る。年ごとの共通の要因 Z（景気・天候など）が、件数の多さと1件あたりの額の両方を動かす。
  件数  N ~ ポアソン(λ・Z)
  1件の額 X ~ 対数正規(μ + b・log Z, σ)    b がつながりの強さ（b=0 なら件数と額は独立）
「別々に見積もる」：件数は年ごとの件数の分布、額はすべての年の請求を1つに集めた分布を、それぞれそのまま使い（当てはめの誤差はない）、
両者を独立として組み合わせる（件数は新しく引いた Z から、額は集めた請求から無作為に取り出す）。
本当の年間損害との差を、99.5%点（200年に1度）と平均で比べる。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 506
SRC = "架空の年間損害（作成者が乱数で作成、seed 506）"
LAM, MU, SIG = 50, 13.0, 1.0          # 年に平均50件、1件の額の中央値は約44万円（e^13）
YEARS = 200_000                        # シミュレーションする年数


def sim(b, sz, rng, pool=None, years=YEARS):
    """年間損害を years 年分作る。pool を渡すと、額をその請求の集まりから独立に取り出す（別々に見積もった組み合わせ）"""
    zn = np.exp(rng.normal(-sz**2 / 2, sz, years))           # 平均1の共通の要因
    n = rng.poisson(LAM * zn)
    if pool is None:
        x = rng.lognormal(MU, SIG, n.sum()) * np.repeat(zn, n) ** b
    else:
        x = rng.choice(pool, n.sum())
    s = np.zeros(years); np.add.at(s, np.repeat(np.arange(years), n), x)
    mean_sev = np.divide(s, n, out=np.zeros(years), where=n > 0)
    return s, n, mean_sev, x


def rank_corr(a, b):
    ra, rb = pd.Series(a).rank().to_numpy(), pd.Series(b).rank().to_numpy()
    return float(np.corrcoef(ra, rb)[0, 1])


def main():
    rng = np.random.default_rng(SEED)
    rows = []
    for sz in [0.1, 0.2, 0.3]:
        for b in [-0.5, 0.0, 0.5, 1.0, 1.5, 2.0]:
            st, nt, mt, xt = sim(b, sz, rng)
            si, _, _, _ = sim(b, sz, rng, pool=xt)
            ok = nt > 0
            rows.append(dict(sz=sz, b=b, corr_n_meansev=rank_corr(nt[ok], mt[ok]),
                             mean_true=st.mean(), mean_indep=si.mean(),
                             q995_true=np.quantile(st, 0.995), q995_indep=np.quantile(si, 0.995),
                             q99_true=np.quantile(st, 0.99), q99_indep=np.quantile(si, 0.99)))
            if sz == 0.2 and b == 1.0:
                keep = (st, si)
    df = pd.DataFrame(rows)
    for c in ["mean", "q995", "q99"]:
        df[c + "_gap_pct"] = (df[c + "_indep"] / df[c + "_true"] - 1) * 100
    df.round(4).to_csv(RES / "gap_by_strength.csv", index=False)

    # 同じ条件で種を変えて10回くり返し、99.5%点のずれのばらつきを見る（sz=0.2, b=1）
    rep = []
    for k in range(10):
        r2 = np.random.default_rng(SEED * 100 + k)
        a, _, _, xa = sim(1.0, 0.2, r2, years=100_000); c, _, _, _ = sim(1.0, 0.2, r2, pool=xa, years=100_000)
        rep.append((np.quantile(c, 0.995) / np.quantile(a, 0.995) - 1) * 100)
    base = df[(df.sz == 0.2) & (df.b == 1.0)].iloc[0]
    out = dict(seed=SEED, years=YEARS, lam=LAM, mu=MU, sigma=SIG,
               base_case=dict(sz=0.2, b=1.0, corr=round(base.corr_n_meansev, 3),
                              q995_true_oku=round(base.q995_true / 1e8, 3), q995_indep_oku=round(base.q995_indep / 1e8, 3),
                              q995_gap_pct=round(base.q995_gap_pct, 1), mean_gap_pct=round(base.mean_gap_pct, 1)),
               repeat_q995_gap_pct=[round(v, 1) for v in rep],
               table=df[["sz", "b", "corr_n_meansev", "mean_gap_pct", "q99_gap_pct", "q995_gap_pct"]].round(3).to_dict("records"))
    json.dump(out, open(RES / "a506_main.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out["base_case"], ensure_ascii=False), out["repeat_q995_gap_pct"])
    print(df[["sz", "b", "corr_n_meansev", "mean_gap_pct", "q995_gap_pct"]].round(2).to_string(index=False))

    # 図1：年間損害の上側（超える確率）
    st, si = keep
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for s, col, lab in [(st, ORANGE, "本当の年間損害（件数と額が一緒に動く）"), (si, BLUE, "件数と額を別々に見積もって組み合わせた")]:
        xs = np.sort(s)[::-1] / 1e8; p = np.arange(1, len(xs) + 1) / len(xs)
        ax.plot(xs, p, color=col, lw=2, label=lab)
    ax.set_yscale("log"); ax.set_ylim(1e-4, 1); ax.axhline(0.005, color=GRAY, ls="--", lw=1)
    ax.text(ax.get_xlim()[1] * 0.98, 0.0058, "200年に1度（0.5%）", color=GRAY, ha="right", fontsize=9)
    ax.set_xlabel("年間損害（億円）"); ax.set_ylabel("この額を超える年の割合")
    ax.set_title(f"200年に1度の額：本当 {base.q995_true/1e8:.2f}億円、別々に見積もると {base.q995_indep/1e8:.2f}億円")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    save(fig, "a506_tail.png", SRC + "。共通の要因の大きさ0.2、つながりの強さ b=1 の場合")

    # 図2：つながりの強さと99.5%点のずれ
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for sz, col in [(0.1, LIGHT), (0.2, BLUE), (0.3, INK)]:
        d = df[df.sz == sz]
        ax.plot(d.corr_n_meansev, d.q995_gap_pct, "o-", color=col, lw=2, label=f"共通の要因の大きさ {sz}")
    ax.axhline(0, color=GRAY, lw=1)
    ax.set_xlabel("件数と1件あたりの平均額の順位の相関（年ごと）"); ax.set_ylabel("別々に見積もった99.5%点のずれ（%）")
    ax.set_title("一緒に動くほど、別々の見積もりは200年に1度の額を小さく出す")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a506_gap_strength.png", SRC + "。各点20万年分のシミュレーション")

    # 図3：平均のずれと裾のずれ（共通の要因0.2）
    d = df[df.sz == 0.2]
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    w = 0.25; xs = np.arange(len(d))
    for i, (c, col, lab) in enumerate([("mean_gap_pct", GRAY, "平均"), ("q99_gap_pct", LIGHT, "99%点（100年に1度）"), ("q995_gap_pct", BLUE, "99.5%点（200年に1度）")]):
        ax.bar(xs + (i - 1) * w, d[c], w, color=col, label=lab)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(xs, [f"b={b:g}" for b in d.b]); ax.set_ylabel("別々に見積もった値のずれ（%）")
    ax.set_title("平均はほぼ合うのに、裾は大きくずれる（共通の要因の大きさ0.2）")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a506_mean_vs_tail.png", SRC + "。b はつながりの強さ（b=0 で独立、負は逆向き）")


if __name__ == "__main__":
    main()
