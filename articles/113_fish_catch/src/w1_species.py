"""W1：魚種別の漁獲量は、いつから減ったか・増えたか（1956〜2024年）
ピークの年と直近値のピーク比、対数漁獲量の平均水準の変化点（ruptures の動的計画法、区間の数はBICで選ぶ）"""
import ruptures as rpt
import matplotlib.ticker as mticker
from common import *

MAIN = ["まいわし", "さば類", "かたくちいわし", "すけとうだら", "さんま", "さけ類", "するめいか", "ぶり類"]


def breaks(s, kmax=4, min_size=5):
    """log10(漁獲量)の平均の変化点。BIC = n·ln(RSS/n) + (2k+1)·ln(n) で k を選ぶ"""
    s = s.dropna()
    s = s[s > 0]
    x = np.log10(s.values).reshape(-1, 1)
    n = len(x)
    algo = rpt.Dynp(model="l2", min_size=min_size, jump=1).fit(x)
    best = None
    for k in range(0, kmax + 1):
        bk = [n] if k == 0 else algo.predict(n_bkps=k)
        rss = sum(((x[a:b] - x[a:b].mean()) ** 2).sum() for a, b in zip([0] + bk[:-1], bk))
        bic = n * np.log(rss / n) + (2 * k + 1) * np.log(n)
        if best is None or bic < best[0]:
            best = (bic, k, bk)
    bk = best[2]
    segs = []
    for a, b in zip([0] + bk[:-1], bk):
        segs.append({"from": int(s.index[a]), "to": int(s.index[b - 1]), "mean_t": float(10 ** x[a:b].mean())})
    return [int(s.index[b]) for b in bk[:-1]], segs


def main():
    nat = national()
    y0, y1 = nat.index.min(), nat.index.max()
    # 1) 全魚種のピークと直近値（ピーク1万トン以上、小計・計の行は除く）
    rows = []
    for c in nat.columns:
        s = nat[c].dropna()
        if len(s) < 40 or s.max() < 10000:
            continue
        rows.append({"species": c, "peak_year": int(s.idxmax()), "peak_t": s.max(), "y1956_t": s.get(1956, np.nan),
                     "y2024_t": s.get(2024, np.nan), "ratio_2024_to_peak": s.get(2024, np.nan) / s.max(),
                     "is_total": ("計" in c) or ("小計" in c)})
    pk = pd.DataFrame(rows).sort_values("peak_t", ascending=False)
    pk.to_csv(RES / "w1_peaks.csv", index=False)
    # 2) 主な魚種の変化点
    br = []
    for c in ["漁獲量計"] + MAIN:
        b, segs = breaks(nat[c])
        for i, sg in enumerate(segs):
            br.append({"species": c, "segment": i + 1, **sg, "breaks": " ".join(map(str, b))})
    br = pd.DataFrame(br)
    br.to_csv(RES / "w1_breaks.csv", index=False)
    # 3) 主な魚種の表
    tb = nat[["漁獲量計"] + MAIN].loc[[1956, 1970, 1980, 1990, 2000, 2010, 2020, 2024]]
    tb.to_csv(RES / "w1_species_table.csv")
    # 魚種構成：2024年に多い魚種
    top = nat.loc[2024, [c for c in nat.columns if "計" not in c]].sort_values(ascending=False).head(10)
    top.rename("t_2024").to_csv(RES / "w1_top2024.csv")

    # 図1：漁獲量計とおもな魚種の積み上げ
    fig, ax = plt.subplots(figsize=(9, 4.8))
    yrs = nat.index
    stack = nat[["まいわし", "さば類", "すけとうだら", "かたくちいわし"]].fillna(0)
    other = nat["漁獲量計"] - stack.sum(axis=1)
    cols = [BLUE, GREEN, PURPLE, LIGHT, GRAY]
    ax.stackplot(yrs, *(stack[c] / 1e4 for c in stack.columns), other / 1e4, colors=cols,
                 labels=list(stack.columns) + ["その他"], alpha=0.9)
    b, _ = breaks(nat["漁獲量計"])
    for x in b:
        ax.axvline(x - 0.5, color=INK, lw=0.8, ls="--")
        ax.text(x - 0.3, nat["漁獲量計"].max() / 1e4 * 0.98, f"{x}年〜", fontsize=9, va="top")
    ax.set_ylabel("万トン")
    ax.set_title("海面漁業の漁獲量（全国、1956〜2024年）と水準の変化点", loc="left")
    ax.legend(loc="upper left", fontsize=9, frameon=False, ncol=5, bbox_to_anchor=(0, -0.08))
    save(fig, "w1_total.png")

    # 図2：主な8魚種（対数軸）と変化点
    fig, axes = plt.subplots(2, 4, figsize=(12, 5.6), sharex=True)
    for ax, c in zip(axes.ravel(), MAIN):
        s = nat[c].dropna()
        s = s[s > 0]
        ax.plot(s.index, s / 1e4, color=BLUE, lw=1.4)
        _, segs = breaks(nat[c])
        for sg in segs:
            ax.hlines(sg["mean_t"] / 1e4, sg["from"] - 0.5, sg["to"] + 0.5, color=ORANGE, lw=2)
        ax.set_yscale("log")
        ax.yaxis.set_major_locator(mticker.LogLocator(base=10, subs=(1, 2, 5)))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.yaxis.set_minor_formatter(mticker.NullFormatter())
        ax.set_title(f"{c}（ピーク{int(s.idxmax())}年）", fontsize=11, loc="left")
        ax.tick_params(labelsize=9)
    fig.supylabel("万トン（対数）", fontsize=10)
    fig.suptitle("主な魚種の漁獲量と、変化点（最大4つ）で区切った各区間の平均（橙、対数の平均）", x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    save(fig, "w1_species.png")

    # 図3：2024年はピークの何％か（ピーク10万トン以上の魚種）
    p = pk[(~pk.is_total) & (pk.peak_t >= 100000) & pk.ratio_2024_to_peak.notna() & ~pk.species.str.startswith("その他")]
    p = p.sort_values("ratio_2024_to_peak")
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(p.species, p.ratio_2024_to_peak * 100, color=[ORANGE if r < 0.1 else BLUE for r in p.ratio_2024_to_peak])
    for i, (r, y) in enumerate(zip(p.ratio_2024_to_peak, p.peak_year)):
        ax.text(r * 100 + 1, i, f"{r * 100:.0f}%（ピーク{y}年）", va="center", fontsize=9)
    ax.set_xlim(0, 125)
    ax.set_xlabel("2024年の漁獲量 ÷ ピークの年の漁獲量（%）")
    ax.set_title("ピーク10万トン以上の魚種：2024年はピークの何％か", loc="left")
    save(fig, "w1_peak.png")

    print(pk[~pk.is_total].head(25).to_string())
    print(br.to_string())
    print(top)
    print(tb.to_string())


if __name__ == "__main__":
    main()
