"""517 保険金額の大きい契約と小さい契約が混ざると、損害率の振れは契約件数ではなく何で決まるのか（保険数理・リスク）

架空の契約 n 件。保険金額 S_i は対数正規（ばらつき σ）で、平均1にそろえる。σ=0 なら全件同じ額。
1年に事故が起きる確率 p=5%、事故のときの損害は S_i × U（U は 0〜1 の一様乱数、保険金額のうち壊れた割合）。
保険料は S_i × p × E[U] ÷ 0.65（目標の損害率 65%）。損害率 = Σ損害 ÷ Σ保険料。
同じ契約の顔ぶれのまま、事故だけを 20,000年分くり返して損害率の標準偏差を数え、
「実質の件数」n_eff = (ΣS)² / ΣS² から出す式 sd = 0.65 × CV(1件の損害) / √n_eff と比べる。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 517
SRC = "架空の契約と事故（作成者が乱数で作成、seed 517）"
P, TARGET, N, REPS = 0.05, 0.65, 10_000, 20_000
CV1 = np.sqrt((P * (1 / 3) - (P * 0.5) ** 2)) / (P * 0.5)   # 1件の損害 I・U の変動係数


def portfolio(sigma, n, rng):
    s = np.exp(rng.normal(0, sigma, n)) if sigma > 0 else np.ones(n)
    return s / s.mean()


def sim_lr(s, rng, reps=REPS, chunk=500):
    prem = (s * P * 0.5 / TARGET).sum(); out = []
    for _ in range(reps // chunk):
        hit = rng.random((chunk, len(s))) < P
        u = rng.random((chunk, len(s)))
        out.append((hit * u * s).sum(axis=1) / prem)
    return np.concatenate(out)


def n_eff(s):
    return float(s.sum() ** 2 / (s ** 2).sum())


def main():
    rng = np.random.default_rng(SEED)
    rows = []; ports = {}
    for sig in [0, 0.5, 1.0, 1.5, 2.0]:
        s = portfolio(sig, N, rng); ports[sig] = s
        lr = sim_lr(s, rng); ne = n_eff(s)
        top = np.sort(s)[::-1]
        rows.append(dict(sigma=sig, n=N, n_eff=round(ne, 1), n_eff_ratio=round(ne / N, 4),
                         top1pct_share=round(float(top[: N // 100].sum() / s.sum()), 4), max_share=round(float(top[0] / s.sum()), 4),
                         sd_sim_pt=round(float(lr.std() * 100), 3), sd_formula_pt=round(float(TARGET * CV1 / np.sqrt(ne) * 100), 3),
                         sd_count_formula_pt=round(float(TARGET * CV1 / np.sqrt(N) * 100), 3),
                         p_lr_over_80=round(float((lr > 0.80).mean()), 4), mean_lr=round(float(lr.mean()), 4)))
    df = pd.DataFrame(rows); df.to_csv(RES / "by_sigma.csv", index=False)
    # 件数を変えたとき（σ=0 と σ=1.5）
    rows2 = []
    for sig in [0, 1.5]:
        for n in [1000, 3000, 10000, 30000]:
            s = portfolio(sig, n, rng); lr = sim_lr(s, rng, reps=4000)
            rows2.append(dict(sigma=sig, n=n, n_eff=round(n_eff(s), 1), sd_sim_pt=round(float(lr.std() * 100), 3)))
    dn = pd.DataFrame(rows2); dn.to_csv(RES / "by_n.csv", index=False)
    # 大きい契約を k 件除く
    rows3 = []
    for sig in [1.0, 1.5, 2.0]:
        s = np.sort(ports[sig])[::-1]
        for k in [0, 1, 10, 100]:
            ss = s[k:]; ne = n_eff(ss)
            rows3.append(dict(sigma=sig, removed=k, removed_share=round(float(s[:k].sum() / s.sum()), 4), n_eff=round(ne, 1),
                              sd_formula_pt=round(float(TARGET * CV1 / np.sqrt(ne) * 100), 3)))
    dr = pd.DataFrame(rows3)
    # 除いたときもシミュレーションで確かめる（σ=2 の上位10件）
    s2 = np.sort(ports[2.0])[::-1][10:]
    chk = float(sim_lr(s2, np.random.default_rng(SEED + 1), reps=10000).std() * 100)
    dr.to_csv(RES / "remove_top.csv", index=False)
    out = dict(seed=SEED, p=P, target=TARGET, n=N, reps=REPS, cv_one_contract=round(float(CV1), 4),
               by_sigma=df.to_dict("records"), by_n=dn.to_dict("records"), remove_top=dr.to_dict("records"),
               check_sigma2_remove10_sd_sim_pt=round(chk, 3))
    json.dump(out, open(RES / "a517_main.json", "w"), ensure_ascii=False, indent=1)
    print(df.to_string()); print(dn.to_string()); print(dr.to_string()); print("chk", chk)

    # 図1：σ と損害率の振れ
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ax.plot(df.sigma, df.sd_sim_pt, "o-", color=BLUE, lw=2.4, ms=8, label="シミュレーション（20,000年分）")
    ax.plot(df.sigma, df.sd_formula_pt, "x--", color=ORANGE, lw=1.6, ms=9, label="実質の件数 n_eff から出した式")
    ax.plot(df.sigma, df.sd_count_formula_pt, ":", color=GRAY, lw=1.6, label="契約件数（1万件）から出した式")
    for x, y in zip(df.sigma, df.sd_sim_pt):
        ax.annotate(f"{y:.1f}", (x, y), textcoords="offset points", xytext=(-6, 8), fontsize=9, color=INK)
    ax.set_xlabel("保険金額のばらつき σ（0＝全件同じ額）"); ax.set_ylabel("損害率の標準偏差（ポイント）")
    ax.set_title("契約は同じ1万件でも、保険金額がばらつくほど損害率は大きく振れる")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a517_sd_by_sigma.png", SRC + "。事故の確率5%、目標の損害率65%")

    # 図2：実質の件数
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    bars = ax.bar([f"σ={s:g}" for s in df.sigma], df.n_eff, color=[LIGHT, LIGHT, BLUE, BLUE, INK])
    for b_, v, r in zip(bars, df.n_eff, df.top1pct_share):
        ax.text(b_.get_x() + b_.get_width() / 2, v, f"{v:,.0f}件\n上位1%の額 {r*100:.0f}%", ha="center", va="bottom", fontsize=8.5)
    ax.set_yscale("log"); ax.set_ylim(50, 40000); ax.set_ylabel("実質の件数 n_eff（対数）")
    ax.set_title("1万件の契約が、振れの大きさでは何件分にあたるか")
    save(fig, "a517_n_eff.png", SRC + "。n_eff = (保険金額の合計)² ÷ (保険金額の2乗の合計)")

    # 図3：大きい契約を除く
    fig, ax = plt.subplots(figsize=(7.6, 4.4)); w = 0.25; xs = np.arange(4)
    for j, (sig, col) in enumerate([(1.0, LIGHT), (1.5, BLUE), (2.0, INK)]):
        x = dr[dr.sigma == sig]
        ax.bar(xs + (j - 1) * w, x.sd_formula_pt, w, color=col, label=f"σ={sig:g}")
    ax.set_xticks(xs, ["除かない", "上位1件を除く", "上位10件を除く", "上位100件を除く"])
    ax.set_ylabel("損害率の標準偏差（ポイント）")
    ax.set_title("保険金額のばらつきが大きいほど、上位の数件を除いたときに振れが大きく下がる")
    ax.legend(frameon=False, fontsize=9)
    save(fig, "a517_remove_top.png", SRC + "。n_eff の式から計算。σ=2 の上位10件除外はシミュレーションでも確かめた")


if __name__ == "__main__":
    main()
