"""528 5歳刻みで同じ保険料にすると、区分の上の年齢に加入が偏ったとき、損害率は何%上がるのか（保険数理・リスク）

架空の年齢別の事故率と加入者の年齢分布。
- 年齢 20〜69歳（1歳きざみ）。事故率は年齢とともに一定の割合で上がる：1歳あたり 2%・4%・8%
- 保険料：区分（1歳・5歳・10歳刻み）の中で年齢が均等にいる前提で、区分の平均の事故率に合わせる（このとき損害率は100%）
- 実際の加入：区分の中で年齢が上ほど多い。重み ∝ exp(b ×（区分の中での年齢の位置）)、b = 0・0.1・0.2・0.4
- 損害率 = 実際の事故の見込み ÷ 保険料。上がり幅（%）を出す
件数の偶然の振れとの比較のため、加入者5,000人・事故率ポアソンで2,000回くじを引く。乱数の種 528。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "架空の年齢別の事故率と年齢分布（作成者が乱数で作成、seed 528）"
AGES = np.arange(20, 70)
GROWTHS = [0.02, 0.04, 0.08]
TILTS = [0.0, 0.1, 0.2, 0.4]
WIDTHS = [1, 5, 10]
BASE = 0.05


def rate(g):
    return BASE * np.exp(g * (AGES - 20))


def weights(width, b):
    pos = (AGES - 20) % width
    return np.exp(b * pos)               # 各区分の中で上の年齢ほど重い（区分ごとの合計人数は後でそろえる）


def premiums(c, width):
    band = (AGES - 20) // width
    p = np.zeros_like(c)
    for k in np.unique(band):
        m = band == k
        p[m] = c[m].mean()               # 区分の中は均等にいる前提
    return p, band


def portfolio(c, width, b):
    p, band = premiums(c, width)
    w = weights(width, b)
    for k in np.unique(band):            # 区分ごとの人数は同じにそろえる（区分の間の偏りは見ない）
        m = band == k
        w[m] = w[m] / w[m].sum()
    return w, p, band


def main():
    rows = []
    for g in GROWTHS:
        c = rate(g)
        for width in WIDTHS:
            for b in TILTS:
                w, p, band = portfolio(c, width, b)
                lr = (w * c).sum() / (w * p).sum()
                pos = (AGES - 20) % width
                mean_off = float(((w * pos).sum() / w.sum()) - (width - 1) / 2)
                rows.append(dict(growth=g, width=width, tilt=b, loss_ratio=round(float(lr), 5), lr_up_pct=round(float(lr - 1) * 100, 2),
                                 mean_age_shift=round(mean_off, 2)))
    df = pd.DataFrame(rows)
    df.to_csv(RES / "summary.csv", index=False)

    # 偶然の振れ：加入者5,000人、g=4%、5歳刻み
    rng = np.random.default_rng(528)
    N, SIMS = 5000, 2000
    c = rate(0.04)
    sim = {}
    for b in [0.0, 0.2]:
        w, p, band = portfolio(c, 5, b)
        prob = w / w.sum()
        lrs = []
        for _ in range(SIMS):
            ages = rng.choice(len(AGES), N, p=prob)
            claims = rng.poisson(c[ages]).sum()
            lrs.append(claims / p[ages].sum())
        sim[b] = np.array(lrs)
    sim_res = {f"b={b}": dict(mean=round(float(v.mean()), 4), sd=round(float(v.std()), 4),
                              p_over_105=round(float((v > 1.05).mean()), 4)) for b, v in sim.items()}
    pd.DataFrame({f"b={b}": v for b, v in sim.items()}).to_csv(RES / "sim_loss_ratio.csv", index=False)

    piv = {f"事故率の伸び{g*100:.0f}%": {f"{w}歳刻み": {f"b={b}": float(df[(df.growth == g) & (df.width == w) & (df.tilt == b)].lr_up_pct.iloc[0]) for b in TILTS} for w in WIDTHS} for g in GROWTHS}
    shift = {f"{w}歳刻み": {f"b={b}": float(df[(df.growth == 0.04) & (df.width == w) & (df.tilt == b)].mean_age_shift.iloc[0]) for b in TILTS} for w in WIDTHS}
    json.dump({"損害率の上がり幅%": piv, "区分の中の平均年齢のずれ（歳）": shift, "偶然の振れ（5千人・伸び4%・5歳刻み）": sim_res},
              open(RES / "a528_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：5歳刻み、偏りの強さと損害率の上がり幅
    fig, ax = plt.subplots(figsize=(8, 4.3))
    for g, c_ in zip(GROWTHS, [GRAY, BLUE, ORANGE]):
        s = df[(df.growth == g) & (df.width == 5)]
        ax.plot(s.tilt, s.lr_up_pct, marker="o", color=c_, label=f"事故率の伸び 1歳あたり{g*100:.0f}%")
        ax.text(s.tilt.iloc[-1] + 0.01, s.lr_up_pct.iloc[-1], f"{s.lr_up_pct.iloc[-1]:.1f}%", va="center", fontsize=9, color=c_)
    ax.set_xlabel("区分の中の偏り b（大きいほど上の年齢に寄る）"); ax.set_ylabel("損害率の上がり幅（%）")
    ax.set_xticks(TILTS); ax.legend(frameon=False, fontsize=9)
    ax.set_title("5歳刻み：事故率の伸びが大きいほど、偏りで損害率が上がる", fontsize=12)
    save(fig, "a528_tilt_5yr.png", SRC)

    # 図2：刻みの幅ごと（g=4%）
    fig, ax = plt.subplots(figsize=(8, 4.3))
    wbar = 0.25
    for k, (width, c_) in enumerate([(1, GRAY), (5, BLUE), (10, ORANGE)]):
        s = df[(df.growth == 0.04) & (df.width == width)]
        xs = np.arange(len(TILTS)) + (k - 1) * wbar
        ax.bar(xs, s.lr_up_pct, wbar, color=c_, label=f"{width}歳刻み")
        for x_, y_ in zip(xs, s.lr_up_pct):
            ax.text(x_, y_ + 0.15, f"{y_:.1f}", ha="center", fontsize=8)
    ax.set_xticks(range(len(TILTS))); ax.set_xticklabels([f"b={b}" for b in TILTS])
    ax.set_ylabel("損害率の上がり幅（%）"); ax.legend(frameon=False, fontsize=9)
    ax.set_title("刻みが粗いほど、同じ偏りでも上がり幅は大きい（伸び4%）", fontsize=12)
    save(fig, "a528_by_width.png", SRC)

    # 図3：偶然の振れと比べる
    fig, ax = plt.subplots(figsize=(8, 4.3))
    bins = np.linspace(0.85, 1.2, 71)
    for b, c_ in [(0.0, GRAY), (0.2, BLUE)]:
        ax.hist(sim[b] * 100, bins=bins * 100, histtype="step", lw=1.8, color=c_, density=True,
                label=f"偏り b={b}（平均 {sim[b].mean()*100:.1f}%）")
    ax.axvline(100, color=INK, lw=0.8, ls="--")
    ax.set_xlabel("1年の損害率（%）"); ax.set_ylabel("密度"); ax.legend(frameon=False, fontsize=9)
    ax.set_title("加入者5,000人では、偏りの影響は1年の偶然の振れより小さい", fontsize=12)
    save(fig, "a528_vs_noise.png", SRC)
    print(df.pivot_table(index=["growth", "width"], columns="tilt", values="lr_up_pct").to_string())
    print(df[df.growth == 0.04].pivot_table(index="width", columns="tilt", values="mean_age_shift"))
    print(sim_res)


if __name__ == "__main__":
    main()
