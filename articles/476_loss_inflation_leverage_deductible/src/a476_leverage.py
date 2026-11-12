"""476 損害が一律に5%大きくなると、免責を超えた分の支払いは何%増えるのか（架空の損害、seed 476）"""
import json
import numpy as np, pandas as pd
from scipy import stats
from common import *

SEED = 476
K = 1.05                       # 損害の一律の上がり方
MEAN = 500_000                 # 損害額の平均（円）。どの分布も同じにそろえる
SRC = "架空の損害（作成者が乱数で作成、seed 476）"


class LogN:
    def __init__(self, sigma, mean=MEAN):
        self.s = sigma; self.mu = np.log(mean) - sigma ** 2 / 2; self.name = f"対数正規（σ={sigma}）"
    def mean(self): return float(np.exp(self.mu + self.s ** 2 / 2))
    def sf(self, d): return 1.0 if d <= 0 else float(stats.norm.sf((np.log(d) - self.mu) / self.s))
    def lev(self, d):          # E[min(X,d)]
        if d <= 0: return 0.0
        if np.isinf(d): return self.mean()
        z = (np.log(d) - self.mu) / self.s
        return float(self.mean() * stats.norm.cdf(z - self.s) + d * stats.norm.sf(z))
    def ppf(self, q): return float(np.exp(self.mu + self.s * stats.norm.ppf(q)))
    def draw(self, rng, n): return rng.lognormal(self.mu, self.s, n)
    def scaled(self, k): return LogN(self.s, self.mean() * k)


class Lomax:
    def __init__(self, alpha, mean=MEAN):
        self.a = alpha; self.th = mean * (alpha - 1); self.name = f"パレート型（α={alpha}）"
    def mean(self): return float(self.th / (self.a - 1))
    def sf(self, d): return float((1 + max(d, 0) / self.th) ** (-self.a))
    def lev(self, d):
        if np.isinf(d): return self.mean()
        return float(self.mean() * (1 - (1 + max(d, 0) / self.th) ** (1 - self.a)))
    def ppf(self, q): return float(self.th * ((1 - q) ** (-1 / self.a) - 1))
    def draw(self, rng, n): return self.th * ((1 - rng.random(n)) ** (-1 / self.a) - 1)
    def scaled(self, k): return Lomax(self.a, self.mean() * k)


DISTS = [LogN(1.0), LogN(1.5), LogN(2.0), Lomax(3.0), Lomax(2.0), Lomax(1.5)]
DEDS = [0, 50_000, 100_000, 200_000, 500_000, 1_000_000, 2_000_000, 5_000_000, 10_000_000]


def layer(D, lo, hi):          # 損害のうち lo〜hi の部分の期待値
    return D.lev(hi) - D.lev(lo)


def pct(a, b): return (a / b - 1) * 100


# ---- 1. 免責を超えた分の支払いの増え方 ----
rows = []
for D in DISTS:
    D2 = D.scaled(K)
    for d in DEDS:
        ex0, ex1 = layer(D, d, np.inf), layer(D2, d, np.inf)
        rows.append(dict(分布=D.name, 免責=d, 免責を超える割合=round(D.sf(d) * 100, 3),
                         免責を超えた分の支払いの増え方=round(pct(ex1, ex0), 2),
                         免責を超える件数の増え方=round(pct(D2.sf(d), D.sf(d)), 2),
                         一件あたりの支払いの増え方=round(pct(ex1 / D2.sf(d), ex0 / D.sf(d)), 2),
                         式の値_一律1パーセントあたりの倍率=round(1 + d * D.sf(d) / ex0, 3)))
excess = pd.DataFrame(rows); excess.to_csv(RES / "excess_increase_by_deductible.csv", index=False)

# ---- 2. 上限のある層：免責〜上限、上限を超えた分 ----
rows = []
for D in DISTS:
    D2 = D.scaled(K)
    for lo, hi in [(0, 1_000_000), (0, 5_000_000), (100_000, 1_000_000), (100_000, 5_000_000), (1_000_000, 5_000_000),
                   (5_000_000, 20_000_000), (1_000_000, np.inf), (5_000_000, np.inf), (20_000_000, np.inf)]:
        a, b = layer(D, lo, hi), layer(D2, lo, hi)
        rows.append(dict(分布=D.name, 下の端=lo, 上の端=("なし" if np.isinf(hi) else int(hi)),
                         もとの損害に占める割合=round(a / D.mean() * 100, 2), 増え方=round(pct(b, a), 2)))
layers = pd.DataFrame(rows); layers.to_csv(RES / "layer_increase.csv", index=False)

# ---- 3. 何年か続いた場合（年5%ずつ）----
rows = []
for D in [LogN(1.5), Lomax(2.0)]:
    for yrs in [1, 3, 5, 10]:
        D2 = D.scaled(K ** yrs)
        for d in [0, 100_000, 1_000_000, 5_000_000]:
            rows.append(dict(分布=D.name, 年数=yrs, 免責=d, もとの損害の増え方=round((K ** yrs - 1) * 100, 1),
                             免責を超えた分の増え方=round(pct(layer(D2, d, np.inf), layer(D, d, np.inf)), 1),
                             上限500万円までの分の増え方=round(pct(layer(D2, d, max(d, 5_000_000)), layer(D, d, max(d, 5_000_000))), 1) if d < 5_000_000 else np.nan))
multi = pd.DataFrame(rows); multi.to_csv(RES / "multi_year.csv", index=False)

# ---- 4. 乱数での確かめ（200万件）----
rng = np.random.default_rng(SEED)
rows = []
for D in [LogN(1.5), Lomax(2.0)]:
    x = D.draw(rng, 2_000_000)
    for d in [100_000, 1_000_000, 5_000_000]:
        sim = pct(np.maximum(x * K - d, 0).sum(), np.maximum(x - d, 0).sum())
        simc = pct((x * K > d).sum(), (x > d).sum())
        f = excess[(excess.分布 == D.name) & (excess.免責 == d)].iloc[0]
        rows.append(dict(分布=D.name, 免責=d, 式=f.免責を超えた分の支払いの増え方, 乱数=round(sim, 2), 件数の式=f.免責を超える件数の増え方, 件数の乱数=round(simc, 2)))
    if D.name.startswith("対数正規"):
        pd.DataFrame({"損害額": np.round(x[:2000]).astype(int)}).to_csv(DATA / "example_losses.csv", index=False)
check = pd.DataFrame(rows); check.to_csv(RES / "formula_check.csv", index=False)

# ---- 5. 実績から見えるか：事故の件数ごとの、前年との比べの振れ ----
rows = []
D = LogN(1.5); D2 = D.scaled(K)
for n in [1_000, 10_000, 100_000]:
    for d in [0, 100_000, 1_000_000]:
        ch = []
        for _ in range(1000):
            a, b = D.draw(rng, n), D2.draw(rng, n)
            pa, pb = np.maximum(a - d, 0).sum(), np.maximum(b - d, 0).sum()
            ch.append(pct(pb, pa))
        ch = np.array(ch)
        true = pct(layer(D2, d, np.inf), layer(D, d, np.inf))
        rows.append(dict(事故の件数=n, 免責=d, 本当の増え方=round(true, 2), 見えた増え方の平均=round(ch.mean(), 2), 標準偏差=round(ch.std(), 2),
                         増えたと見えた割合=round((ch > 0).mean() * 100, 1)))
noise = pd.DataFrame(rows); noise.to_csv(RES / "observed_change_noise.csv", index=False)

# ---- 図 ----
x = np.array([d for d in DEDS if d > 0])
fig, ax = plt.subplots(figsize=(8, 4.6))
cols = {DISTS[0].name: LIGHT, DISTS[1].name: BLUE, DISTS[2].name: "#14427a", DISTS[3].name: "#f3b08f", DISTS[4].name: ORANGE, DISTS[5].name: "#8f3210"}
for D in DISTS:
    s = excess[(excess.分布 == D.name) & (excess.免責 > 0)]
    ax.plot(s.免責 / 10000, s.免責を超えた分の支払いの増え方, marker="o", ms=4, lw=2, color=cols[D.name], label=D.name,
            ls="-" if D.name.startswith("対数") else "--")
ax.axhline(5, color=INK, lw=0.8); ax.text(1000, 5.25, "もとの損害の上がり方 +5%", fontsize=9, color=INK, ha="right")
ax.set_xscale("log"); ax.set_xticks([5, 10, 20, 50, 100, 200, 500, 1000]); ax.set_xticklabels(["5万", "10万", "20万", "50万", "100万", "200万", "500万", "1,000万"])
ax.set_xlabel("免責の金額（円）"); ax.set_ylabel("免責を超えた分の支払いの増え方（%）")
ax.set_title("損害が一律に5%上がると、免責を超えた分は5%より多く増える", loc="left"); ax.legend(fontsize=8.5, frameon=False, ncol=2)
save(fig, "a476_excess_increase.png", f"出典：{SRC}。損害額の平均はどの分布も50万円。式から計算")

D = LogN(1.5); s = layers[layers.分布 == D.name]
lab = {(0, 1_000_000): "0〜100万円", (0, 5_000_000): "0〜500万円", (100_000, 1_000_000): "10万〜100万円", (100_000, 5_000_000): "10万〜500万円", (1_000_000, 5_000_000): "100万〜500万円",
       (5_000_000, 20_000_000): "500万〜2,000万円", (1_000_000, "なし"): "100万円を超えた分", (5_000_000, "なし"): "500万円を超えた分", (20_000_000, "なし"): "2,000万円を超えた分"}
fig, ax = plt.subplots(figsize=(8, 4.6))
names = [lab[(int(r.下の端), r.上の端 if r.上の端 == "なし" else int(r.上の端))] for r in s.itertuples()]
vals = s.増え方.values; ypos = np.arange(len(vals))[::-1]
ax.barh(ypos, vals, color=[BLUE if v < 5 else ORANGE for v in vals])
for y, v, sh in zip(ypos, vals, s.もとの損害に占める割合.values): ax.text(max(v, 5) + 0.2, y, f"+{v:.1f}%（損害の{sh:.0f}%）", va="center", fontsize=9)
ax.axvline(5, color=INK, lw=0.8); ax.set_yticks(ypos); ax.set_yticklabels(names); ax.set_xlim(0, max(vals) * 1.35)
ax.set_xlabel("その部分の支払いの増え方（%）"); ax.set_title("上限のある部分は5%より小さく、上限を超えた部分は大きく増える", loc="left")
save(fig, "a476_layers.png", f"出典：{SRC}。対数正規（σ=1.5、平均50万円）。かっこ内は、もとの損害の合計に占める割合")

fig, ax = plt.subplots(figsize=(8, 4.6))
for D, c in [(LogN(1.5), BLUE), (Lomax(2.0), ORANGE)]:
    s = excess[(excess.分布 == D.name) & (excess.免責 > 0)]
    ax.plot(s.免責 / 10000, s.免責を超える件数の増え方, marker="o", ms=4, lw=2, color=c, label=f"{D.name}：免責を超える件数")
    ax.plot(s.免責 / 10000, s.一件あたりの支払いの増え方, marker="s", ms=4, lw=2, color=c, ls=":", label=f"{D.name}：1件あたりの支払額")
ax.axhline(5, color=INK, lw=0.8); ax.set_xscale("log"); ax.set_xticks([5, 10, 20, 50, 100, 200, 500, 1000]); ax.set_xticklabels(["5万", "10万", "20万", "50万", "100万", "200万", "500万", "1,000万"])
ax.set_xlabel("免責の金額（円）"); ax.set_ylabel("増え方（%）"); ax.set_title("増えた分は、「件数が増える分」と「1件あたりが増える分」に分かれる", loc="left"); ax.legend(fontsize=8.5, frameon=False)
save(fig, "a476_count_vs_severity.png", f"出典：{SRC}。損害が一律に5%上がったとき。式から計算")

g = lambda name, d, col: float(excess[(excess.分布 == name) & (excess.免責 == d)][col].iloc[0])
main = dict(seed=SEED, 損害の上がり方=5.0, 平均=MEAN,
            対数正規15_免責10万=g("対数正規（σ=1.5）", 100_000, "免責を超えた分の支払いの増え方"), 対数正規15_免責100万=g("対数正規（σ=1.5）", 1_000_000, "免責を超えた分の支払いの増え方"),
            対数正規15_免責500万=g("対数正規（σ=1.5）", 5_000_000, "免責を超えた分の支払いの増え方"), 対数正規15_免責1000万=g("対数正規（σ=1.5）", 10_000_000, "免責を超えた分の支払いの増え方"),
            パレート2_免責100万=g("パレート型（α=2.0）", 1_000_000, "免責を超えた分の支払いの増え方"), パレート2_免責1000万=g("パレート型（α=2.0）", 10_000_000, "免責を超えた分の支払いの増え方"),
            パレート型の上限_αごと={a: round((K ** a - 1) * 100, 2) for a in (1.5, 2.0, 3.0)},
            式と乱数の差の最大=float((check.式 - check.乱数).abs().max()))
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
print(excess[excess.分布.isin(["対数正規（σ=1.5）", "パレート型（α=2.0）"])].to_string()); print(layers[layers.分布 == "対数正規（σ=1.5）"].to_string()); print(multi.to_string()); print(check.to_string()); print(noise.to_string()); print(main)
