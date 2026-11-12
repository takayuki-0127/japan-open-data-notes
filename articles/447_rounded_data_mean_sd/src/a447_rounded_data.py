"""447 5歳刻みや千円単位に丸めたデータから出した平均とばらつきは、元のデータとどれだけ違うのか
架空のデータ（3つの形）を階級に入れ、階級の真ん中の値で平均・標準偏差を出す。seed 447"""
import json
import numpy as np, pandas as pd
from common import *

rng = np.random.default_rng(447)
N, REP = 20000, 200
RATIOS = [0.25, 0.5, 1.0, 1.5, 2.0, 3.0]          # 刻みの幅 ÷ 元の標準偏差


def gen(shape, n):
    if shape == "山が真ん中（正規分布）": return rng.normal(45, 12, n)
    if shape == "右に裾が長い（対数正規）": return rng.lognormal(np.log(3000), 0.8, n)
    if shape == "0の近くがいちばん多い（指数分布）": return rng.exponential(2000, n)


SHAPES = ["山が真ん中（正規分布）", "右に裾が長い（対数正規）", "0の近くがいちばん多い（指数分布）"]
TRUE_SD = {"山が真ん中（正規分布）": 12.0,
           "右に裾が長い（対数正規）": float(3000 * np.exp(0.32) * np.sqrt(np.exp(0.64) - 1)),
           "0の近くがいちばん多い（指数分布）": 2000.0}


def grouped(x, h, offset=0.0):
    """幅 h の階級（境目は offset＋k×h）に入れ、階級の真ん中の値に置き換える"""
    return (np.floor((x - offset) / h) + 0.5) * h + offset


rows = []
for shape in SHAPES:
    for ratio in RATIOS:
        h = ratio * TRUE_SD[shape]
        acc = []
        for _ in range(REP):
            x = gen(shape, N)
            off = rng.uniform(0, h) if shape == "山が真ん中（正規分布）" else 0.0   # 金額は0から区切る
            g = grouped(x, h, off)
            m0, s0 = x.mean(), x.std(ddof=1); m1, s1 = g.mean(), g.std(ddof=1)
            s2 = np.sqrt(max(s1 ** 2 - h ** 2 / 12, 0))                       # シェパードの補正
            acc.append([(m1 / m0 - 1) * 100, (s1 / s0 - 1) * 100, (s2 / s0 - 1) * 100])
        a = np.array(acc)
        rows.append(dict(shape=shape, width_over_sd=ratio, width=round(h, 1), mean_bias_pct=a[:, 0].mean(),
                         sd_bias_pct=a[:, 1].mean(), sd_bias_sheppard_pct=a[:, 2].mean(),
                         sd_bias_pct_p05=np.percentile(a[:, 1], 5), sd_bias_pct_p95=np.percentile(a[:, 1], 95)))
sweep = pd.DataFrame(rows); sweep.round(3).to_csv(RES / "bias_by_width.csv", index=False)

# ---- 具体例：年齢を5歳・10歳刻み、金額を千円・5千円・1万円単位
rows = []
for label, shape, hs, unit in [("年齢（平均45歳・標準偏差12歳）", SHAPES[0], [1, 5, 10, 20], "歳"),
                               ("金額（中央値3,000円・右に裾が長い）", SHAPES[1], [100, 1000, 5000, 10000], "円"),
                               ("金額（平均2,000円・0の近くが多い）", SHAPES[2], [100, 1000, 5000, 10000], "円")]:
    for h in hs:
        acc = []
        for _ in range(REP):
            x = gen(shape, N); g = grouped(x, h, 0.0)
            s1 = g.std(ddof=1); s2 = np.sqrt(max(s1 ** 2 - h ** 2 / 12, 0))
            acc.append([x.mean(), g.mean(), x.std(ddof=1), s1, s2])
        a = np.array(acc).mean(0)
        rows.append(dict(data=label, width=h, unit=unit, mean_raw=a[0], mean_grouped=a[1], sd_raw=a[2], sd_grouped=a[3], sd_sheppard=a[4],
                         mean_bias_pct=(a[1] / a[0] - 1) * 100, sd_bias_pct=(a[3] / a[2] - 1) * 100, sd_sheppard_bias_pct=(a[4] / a[2] - 1) * 100))
ex = pd.DataFrame(rows); ex.round(3).to_csv(RES / "examples.csv", index=False)

# ---- 階級の代表値の取り違え：満年齢（切り捨て）の5歳階級「20〜24歳」を 22 とするか 22.5 とするか
acc = []
for _ in range(REP):
    x = np.clip(rng.normal(45, 12, N), 0, None)
    cls = np.floor(x / 5) * 5
    acc.append([x.mean(), np.floor(x).mean(), (cls + 2).mean(), (cls + 2.5).mean()])
a = np.array(acc).mean(0)
rep_val = dict(mean_exact_age=a[0], mean_completed_age=a[1], mean_class_plus2=a[2], mean_class_plus2_5=a[3])

# ---- いちばん上の階級が「〜以上」でまとめられている場合（金額：上位5%をまとめる）
rows = []
for shape in SHAPES[1:]:
    acc = []
    for _ in range(REP):
        x = gen(shape, N); h = 1000; cut = np.ceil(np.percentile(x, 95) / h) * h
        g = grouped(x, h, 0.0); top = x >= cut
        g1 = g.copy(); g1[top] = cut + h / 2            # 上の階級を「次の階級と同じ幅」とみなす
        g2 = g.copy(); g2[top] = cut * 1.5              # 上の階級を「下限の1.5倍」とみなす
        acc.append([x.mean(), g1.mean(), g2.mean(), x.std(ddof=1), g1.std(ddof=1), g2.std(ddof=1), x[top].mean() / cut])
    a = np.array(acc).mean(0)
    rows.append(dict(shape=shape, mean_bias_same_width_pct=(a[1] / a[0] - 1) * 100, mean_bias_1_5x_pct=(a[2] / a[0] - 1) * 100,
                     sd_bias_same_width_pct=(a[4] / a[3] - 1) * 100, sd_bias_1_5x_pct=(a[5] / a[3] - 1) * 100, true_top_mean_over_cut=a[6]))
top = pd.DataFrame(rows); top.round(3).to_csv(RES / "open_top_class.csv", index=False)

# ---- 件数が少ないとき：丸めのずれと、標本の振れのどちらが大きいか（年齢・5歳刻み）
rows = []
for n in [50, 200, 1000, 10000]:
    acc = []
    for _ in range(2000):
        x = rng.normal(45, 12, n); g = grouped(x, 5, 0.0)
        acc.append([x.std(ddof=1), g.std(ddof=1)])
    a = np.array(acc)
    rows.append(dict(n=n, sd_sampling_cv_pct=a[:, 0].std() / 12 * 100, rounding_bias_pct=(a[:, 1].mean() / a[:, 0].mean() - 1) * 100))
small = pd.DataFrame(rows); small.round(3).to_csv(RES / "sample_size.csv", index=False)

x = gen(SHAPES[1], 2000); pd.DataFrame({"amount": np.round(x, 0), "amount_1000yen_class_mid": grouped(x, 1000)}).to_csv(DATA / "example_amounts.csv", index=False)

g_ = lambda s, r, c: round(float(sweep[(sweep["shape"] == s) & (sweep.width_over_sd == r)][c].iloc[0]), 2)
main = dict(n=N, rep=REP,
            sd_bias_pct={s: {str(r): g_(s, r, "sd_bias_pct") for r in RATIOS} for s in SHAPES},
            sd_bias_sheppard_pct={s: {str(r): g_(s, r, "sd_bias_sheppard_pct") for r in RATIOS} for s in SHAPES},
            mean_bias_pct={s: {str(r): g_(s, r, "mean_bias_pct") for r in RATIOS} for s in SHAPES},
            examples=ex.round(2).to_dict("records"), representative_value={k: round(float(v), 3) for k, v in rep_val.items()},
            open_top=top.round(2).to_dict("records"), sample_size=small.round(2).to_dict("records"))
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

SRC = "架空のデータ（作成者が乱数で作成、seed 447）。2万件・200回の平均"
cols = dict(zip(SHAPES, [BLUE, ORANGE, GREEN]))
fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.3), sharey=True)
for s in SHAPES:
    d = sweep[sweep["shape"] == s]
    axes[0].plot(d.width_over_sd, d.sd_bias_pct, "o-", color=cols[s], label=s)
    axes[1].plot(d.width_over_sd, d.sd_bias_sheppard_pct, "o-", color=cols[s], label=s)
axes[0].plot(RATIOS, [(np.sqrt(1 + r ** 2 / 12) - 1) * 100 for r in RATIOS], ":", color=GRAY, label="式：幅の2乗÷12 が分散に足される")
for ax, t in zip(axes, ["階級の真ん中の値でそのまま計算", "シェパードの補正（分散から 幅²÷12 を引く）"]):
    ax.axhline(0, color=INK, lw=0.8); ax.set_xlabel("刻みの幅 ÷ 元の標準偏差"); ax.set_title(t)
axes[0].set_ylabel("標準偏差のずれ（%）"); axes[0].legend(frameon=False, fontsize=8.5)
fig.suptitle("標準偏差は、山が真ん中の形では大きく、偏った形では小さく出る。補正が効くのは山が真ん中の形だけ", y=1.02)
save(fig, "a447_sd_bias_by_width.png", SRC)

fig, ax = plt.subplots(figsize=(7.6, 4.4))
for s in SHAPES:
    d = sweep[sweep["shape"] == s]; ax.plot(d.width_over_sd, d.mean_bias_pct, "o-", color=cols[s], label=s)
ax.axhline(0, color=INK, lw=0.8); ax.set_xlabel("刻みの幅 ÷ 元の標準偏差"); ax.set_ylabel("平均のずれ（%）")
ax.set_title("平均は、山が真ん中ならずれない。0の近くが多い形では大きく出る"); ax.legend(frameon=False, fontsize=9)
save(fig, "a447_mean_bias_by_width.png", SRC)

fig, axes = plt.subplots(1, 3, figsize=(11, 3.8))
for ax, s, h, xl in zip(axes, SHAPES, [10, 5000, 5000], ["年齢（歳）", "金額（円）", "金額（円）"]):
    x = gen(s, 200000); hi = np.percentile(x, 99.5)
    ax.hist(x[x < hi], bins=120, density=True, color=LIGHT)
    edges = np.arange(np.floor(x.min() / h) * h, hi + h, h); cnt, _ = np.histogram(x, bins=edges, density=True)
    ax.step(edges[:-1], cnt, where="post", color=ORANGE, lw=1.6)
    for e0, c in zip(edges[:-1], cnt):
        m_in = x[(x >= e0) & (x < e0 + h)]
        if len(m_in) > 200:
            ax.plot([e0 + h / 2], [c], "o", color=ORANGE, ms=4); ax.plot([m_in.mean()], [c], "x", color=INK, ms=6)
    ax.set_title(s, fontsize=10); ax.set_xlabel(xl); ax.set_yticks([])
fig.suptitle("階級の真ん中（丸）と、その階級に入った値の本当の平均（×）", y=1.03)
save(fig, "a447_class_mid_vs_true_mean.png", "架空のデータ（作成者が乱数で作成、seed 447）。20万件。オレンジの段は階級（年齢10歳、金額5千円）")
print(json.dumps(main, ensure_ascii=False)[:3000])
