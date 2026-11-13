"""527 予定利率と実際の利回りが0.5ポイントずれると、30年の積立金はどれだけ足りなくなるのか（保険数理・リスク）

架空の積立：毎年の期初に同じ額（1）を30年積み立てる。
- 予定利率 i：0.5%・1.5%・3.0%。目標額 = 予定利率どおりに増えたときの30年後の積立金
- 実際の利回り：平均 = i − ずれ（ずれ 0・0.25・0.5・1.0 ポイント）、年ごとの振れ（標準偏差）0・2・5%、年ごとに独立な正規分布
不足率（1 − 実際 ÷ 目標、中央値）と、目標に届かない確率を出す。乱数の種 527、各場面 10万通り。
"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import FIG, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SRC = "架空の積立と利回り（作成者が乱数で作成、seed 527）"
YEARS, SIMS = 30, 100_000
RATES = [0.005, 0.015, 0.03]
GAPS = [0.0, 0.0025, 0.005, 0.01]
VOLS = [0.0, 0.02, 0.05]


def fv(r):
    # r: (sims, YEARS)。期初に1ずつ積み立てる
    growth = np.cumprod((1 + r)[:, ::-1], axis=1)   # 後ろから掛ける：k年目の積立は残り年数分増える
    return growth.sum(axis=1)


def main():
    rng = np.random.default_rng(527)
    z = rng.standard_normal((SIMS, YEARS))          # 全場面で同じ乱数を使う（差を比べやすくする）
    rows, keep = [], {}
    for i in RATES:
        target = float(fv(np.full((1, YEARS), i))[0])
        for g in GAPS:
            for v in VOLS:
                f = fv(i - g + v * z)
                short = 1 - f / target
                rows.append(dict(plan=i, gap=g, vol=v, target=round(target, 3),
                                 short_median=round(float(np.median(short)), 4), short_mean=round(float(short.mean()), 4),
                                 p_short=round(float((f < target).mean()), 4),
                                 short_p95=round(float(np.quantile(short, 0.95)), 4),
                                 extra_contrib=round(float(target / np.median(f) - 1), 4)))
                if i == 0.015 and v in (0.0, 0.02, 0.05) and g in (0.0, 0.005):
                    keep[(g, v)] = short
    df = pd.DataFrame(rows)
    df.to_csv(RES / "summary.csv", index=False)

    # 確定的なずれの解析的な確認：振れ0のとき
    det = df[df.vol == 0][["plan", "gap", "short_median"]]
    main_ = {f"予定{p*100:.1f}%": {f"ずれ{g*100:.2f}pt・振れ{v*100:.0f}%": dict(不足率中央値=r.short_median, 届かない確率=r.p_short, 不足率95点=r.short_p95)
                                   for g, v, r in [(r.gap, r.vol, r) for r in df[df.plan == p].itertuples()]}
             for p in RATES}
    json.dump({"years": YEARS, "sims": SIMS, "結果": main_}, open(RES / "a527_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：ずれと不足率（振れ0、予定利率ごと）
    fig, ax = plt.subplots(figsize=(8, 4.3))
    for i, c in zip(RATES, [GRAY, BLUE, ORANGE]):
        s = df[(df.plan == i) & (df.vol == 0)]
        ax.plot(s.gap * 100, s.short_median * 100, marker="o", color=c, label=f"予定利率 {i*100:.1f}%")
    ax.set_xlabel("実際の利回りが予定利率を下回る幅（ポイント）"); ax.set_ylabel("30年後の不足率（%）")
    ax.set_xticks([0, 0.25, 0.5, 1.0]); ax.legend(frameon=False, fontsize=9)
    t05 = df[(df.vol == 0) & (df.gap == 0.005)].sort_values("plan")
    ax.text(0.55, 0.12, "ずれ0.5ポイントのとき：" + "・".join(f"予定{r.plan*100:.1f}%で{r.short_median*100:.1f}%" for r in t05.itertuples()),
            transform=ax.transAxes, fontsize=9, ha="center")
    ax.set_title("振れがなくても、0.5ポイントのずれで30年後に約8%足りない", fontsize=12)
    save(fig, "a527_gap_shortfall.png", SRC)

    # 図2：振れを入れたときの不足率の分布（予定1.5%）
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    bins = np.linspace(-60, 60, 121)
    for j, g in enumerate([0.0, 0.005]):
        for v, c in [(0.02, BLUE), (0.05, ORANGE)]:
            ax[j].hist(keep[(g, v)] * 100, bins=bins, histtype="step", color=c, lw=1.6, density=True, label=f"年ごとの振れ {v*100:.0f}%")
        ax[j].axvline(keep[(g, 0.0)][0] * 100, color=INK, ls="--", lw=1, label="振れなし")
        ax[j].axvline(0, color=GRAY, lw=0.8)
        ax[j].set_title(f"平均のずれ {g*100:.1f}ポイント（予定1.5%）", fontsize=11)
        ax[j].set_xlabel("不足率（%、右ほど足りない）")
    ax[0].legend(frameon=False, fontsize=9)
    fig.suptitle("振れが大きいと、平均のずれより振れのほうが結果を大きく左右する", fontsize=12, y=1.03)
    save(fig, "a527_dist.png", SRC)

    # 図3：目標に届かない確率
    fig, ax = plt.subplots(figsize=(8, 4.3))
    s = df[df.plan == 0.015]
    w = 0.25
    for k, (v, c) in enumerate([(0.0, GRAY), (0.02, BLUE), (0.05, ORANGE)]):
        t = s[s.vol == v]
        xs = np.arange(len(GAPS)) + (k - 1) * w
        ax.bar(xs, t.p_short * 100, w, color=c, label=f"振れ {v*100:.0f}%")
        for x_, y_ in zip(xs, t.p_short * 100):
            ax.text(x_, y_ + 1, f"{y_:.0f}", ha="center", fontsize=8)
    ax.set_xticks(range(len(GAPS))); ax.set_xticklabels([f"{g*100:.2f}pt" for g in GAPS])
    ax.set_xlabel("平均のずれ"); ax.set_ylabel("目標に届かない確率（%）"); ax.set_ylim(0, 122)
    ax.legend(frameon=False, fontsize=9, loc="upper left", ncol=3)
    ax.set_title("ずれ0なら約半分、0.5ポイントずれると振れ2%で約9割が届かない（予定1.5%）", fontsize=12)
    save(fig, "a527_p_short.png", SRC)
    print(df.to_string())


if __name__ == "__main__":
    main()
