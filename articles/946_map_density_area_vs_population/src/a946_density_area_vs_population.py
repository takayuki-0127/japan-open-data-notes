"""946 面積で割るか人口で割るかで、密度の地図はどう変わるのか？（架空のデータ）

架空の町（30×30 のマス、1マス＝0.5km四方＝0.25km²）を12の区（A区〜L区）に分ける。
マスごとの人口は町の中心ほど多く（指数の減り方×対数正規の振れ）、公園・池のマスは人口0。
店（喫茶店）の数は、マスの人口の β 乗に比例する強さのポアソン分布で置く（町全体の店の数の平均は600軒）。
区ごとに「店の数÷面積」「店の数÷住める面積（公園・池を除く）」「店の数÷人口」の3つの密度を出し、
地図の色の順位がどれだけ入れ替わるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 946
SRC = "架空の町の人口と店（作成者が乱数で作成、seed 946）"
G = 30
CELL_KM2 = 0.25
NAMES = [f"{c}区" for c in "ABCDEFGHIJKL"]
XX, YY = np.meshgrid(np.arange(G), np.arange(G), indexing="xy")
CENTER = (13.0, 16.0)
PARK = (23.0, 7.0, 4.2)  # 公園・池の中心と半径（マス）


def districts(rng):
    while True:
        c = rng.uniform(1, G - 1, size=(12, 2))
        d = (XX[None] - c[:, 0, None, None]) ** 2 + (YY[None] - c[:, 1, None, None]) ** 2
        z = d.argmin(0)
        size = np.bincount(z.ravel(), minlength=12)
        if size.min() >= 35:
            # 名前は左上から右下へ（中心の y が大きい順、x が小さい順）
            cy = np.array([YY[z == k].mean() for k in range(12)])
            cx = np.array([XX[z == k].mean() for k in range(12)])
            order = np.lexsort((cx, -np.round(cy / 7)))
            remap = np.empty(12, int); remap[order] = np.arange(12)
            return remap[z]


def make_town(rng, z, beta=0.7, scale=7.0, noise=0.35, n_shops=600, park=True):
    r = np.sqrt((XX - CENTER[0]) ** 2 + (YY - CENTER[1]) ** 2)
    pop = 2200 * np.exp(-r / scale) * np.exp(rng.normal(0, noise, (G, G)))
    pop = np.round(pop)
    is_park = np.zeros((G, G), bool)
    if park:
        is_park = (XX - PARK[0]) ** 2 + (YY - PARK[1]) ** 2 <= PARK[2] ** 2
        pop[is_park] = 0
    w = np.where(pop > 0, np.maximum(pop, 1) ** beta, 0.0)  # 人口0のマス（公園・池）には店を置かない
    lam = n_shops * w / w.sum()
    shops = rng.poisson(lam)
    return pop, shops, is_park


def by_district(z, pop, shops, is_park):
    k = 12
    area = np.bincount(z.ravel(), minlength=k) * CELL_KM2
    live = np.bincount(z.ravel(), weights=(~is_park).ravel().astype(float), minlength=k) * CELL_KM2
    p = np.bincount(z.ravel(), weights=pop.ravel(), minlength=k)
    s = np.bincount(z.ravel(), weights=shops.ravel().astype(float), minlength=k)
    return pd.DataFrame({"district": NAMES, "area_km2": area, "livable_km2": live, "population": p, "shops": s,
                         "per_km2": s / area, "per_livable_km2": s / live, "per_10k_people": s / p * 1e4,
                         "people_per_km2": p / area})


def spearman(a, b):
    ra = pd.Series(a).rank().values; rb = pd.Series(b).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])


def band(v):
    """色の段：順位で上4区・中4区・下4区の3段"""
    r = pd.Series(v).rank(method="first", ascending=False).values
    return np.where(r <= 4, 0, np.where(r <= 8, 1, 2))


def compare(df):
    a, l, p, d = df.per_km2.values, df.per_livable_km2.values, df.per_10k_people.values, df.people_per_km2.values
    return {"rho_area_vs_people": spearman(a, p), "rho_area_vs_popdensity": spearman(a, d),
            "rho_people_vs_popdensity": spearman(p, d), "rho_area_vs_livable": spearman(a, l),
            "band_changed_area_vs_people": int((band(a) != band(p)).sum()),
            "band_changed_area_vs_livable": int((band(a) != band(l)).sum()),
            "same_top_area_vs_people": bool(np.argmax(a) == np.argmax(p)),
            "rank_gap_max": int(np.abs(pd.Series(a).rank().values - pd.Series(p).rank().values).max())}


def main():
    rng = np.random.default_rng(SEED)
    z = districts(rng)
    pop, shops, is_park = make_town(rng, z)
    pd.DataFrame({"x": XX.ravel(), "y": YY.ravel(), "district": np.array(NAMES)[z.ravel()],
                  "park": is_park.ravel().astype(int), "population": pop.ravel().astype(int),
                  "shops": shops.ravel()}).to_csv(DATA / "cells_example_town.csv", index=False)
    ex = by_district(z, pop, shops, is_park)
    ex["band_per_km2"] = band(ex.per_km2.values) + 1
    ex["band_per_10k_people"] = band(ex.per_10k_people.values) + 1
    ex["band_per_livable_km2"] = band(ex.per_livable_km2.values) + 1
    ex.round(3).to_csv(RES / "districts_example.csv", index=False)
    ex_cmp = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in compare(ex).items()}
    ex_cmp["top_per_km2"] = ex.district[ex.per_km2.idxmax()]
    ex_cmp["top_per_10k_people"] = ex.district[ex.per_10k_people.idxmax()]
    ex_cmp["top_per_livable_km2"] = ex.district[ex.per_livable_km2.idxmax()]
    ex_cmp["top_people_per_km2"] = ex.district[ex.people_per_km2.idxmax()]
    park_d = int(np.bincount(z[is_park]).argmax())
    ex_cmp["park_district"] = NAMES[park_d]
    ex_cmp["park_share_of_district"] = round(float(is_park[z == park_d].mean()), 3)
    ex_cmp["total_shops"] = int(shops.sum()); ex_cmp["total_population"] = int(pop.sum())

    # 2) 同じ区割りで、町（人口の振れ・店）を500回作り直す（基本の置き方）
    rows = []
    for r in range(500):
        p2, s2, ip = make_town(np.random.default_rng(SEED * 1000 + r), z)
        rows.append(compare(by_district(z, p2, s2, ip)))
    rep = pd.DataFrame(rows)

    def summ(df):
        return {"rho_area_vs_people_mean": round(float(df.rho_area_vs_people.mean()), 3),
                "rho_area_vs_people_p10": round(float(df.rho_area_vs_people.quantile(.1)), 3),
                "rho_area_vs_people_p90": round(float(df.rho_area_vs_people.quantile(.9)), 3),
                "rho_area_vs_popdensity_mean": round(float(df.rho_area_vs_popdensity.mean()), 3),
                "rho_people_vs_popdensity_mean": round(float(df.rho_people_vs_popdensity.mean()), 3),
                "band_changed_mean": round(float(df.band_changed_area_vs_people.mean()), 2),
                "same_top_share": round(float(df.same_top_area_vs_people.mean()), 3),
                "band_changed_livable_mean": round(float(df.band_changed_area_vs_livable.mean()), 2)}
    base = summ(rep)
    # 2つの地図が無関係（順位がでたらめ）なら、色の段（4区ずつ3段）が変わる区の数の期待値は 12×(1−4/12)＝8
    base["band_changed_if_unrelated"] = 8.0
    # β＝0.7 のとき、人口が2倍のマスの店の強さは 2^0.7 倍
    base["shop_ratio_if_population_doubles_beta07"] = round(2 ** 0.7, 3)
    rep.round(4).to_csv(RES / "towns_500.csv", index=False)

    # 3) 確かめ：店の人口への寄り方 β、人口の集まり方、公園の有無（各300回）
    rob = []
    settings = [("店の人口への寄り方 β", "beta", [0.0, 0.3, 0.5, 0.7, 1.0, 1.3]),
                ("人口の集まり方（中心からの減り方、マス）", "scale", [4.0, 7.0, 12.0]),
                ("公園・池", "park", [True, False])]
    for label, key, vals in settings:
        for v in vals:
            kw = {"beta": 0.7, "scale": 7.0, "park": True}
            kw[key] = v
            rr = []
            for r in range(300):
                p2, s2, ip = make_town(np.random.default_rng(SEED * 10 + r + 7919 * len(rob)), z, **kw)
                rr.append(compare(by_district(z, p2, s2, ip)))
            s = summ(pd.DataFrame(rr))
            rob.append({"変えたもの": label, "値": str(v), "基本": kw == {"beta": 0.7, "scale": 7.0, "park": True},
                        "面積と人口の順位相関": s["rho_area_vs_people_mean"],
                        "10〜90%": f"{s['rho_area_vs_people_p10']:.2f}〜{s['rho_area_vs_people_p90']:.2f}",
                        "面積で割った地図と人口密度の順位相関": s["rho_area_vs_popdensity_mean"],
                        "人口で割った地図と人口密度の順位相関": s["rho_people_vs_popdensity_mean"],
                        "色の段が変わる区の数": s["band_changed_mean"], "1位が同じ区": s["same_top_share"]})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    out = {"example_town": ex_cmp, "example_districts": ex.round(3).to_dict("records"),
           "base_500_towns": base, "robustness": rob.to_dict("records")}
    json.dump(out, open(RES / "a946_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 境界線
    segs = []
    for y in range(G):
        for x in range(G - 1):
            if z[y, x] != z[y, x + 1]:
                segs.append([(x + .5, y - .5), (x + .5, y + .5)])
    for y in range(G - 1):
        for x in range(G):
            if z[y, x] != z[y + 1, x]:
                segs.append([(x - .5, y + .5), (x + .5, y + .5)])

    def draw_bounds(ax, labels=None):
        ax.add_collection(LineCollection(segs, colors=INK, linewidths=1.0))
        for k in range(12):
            yy, xx = np.nonzero(z == k)
            t = NAMES[k] if labels is None else f"{NAMES[k]}\n{labels[k]}"
            ax.text(xx.mean(), yy.mean(), t, ha="center", va="center", fontsize=8, color=INK,
                    bbox=dict(fc="white", ec="none", alpha=.7, pad=1))
        ax.set_xticks([]); ax.set_yticks([])

    # 図1：人口と公園・池
    fig, ax = plt.subplots(figsize=(6.0, 4.9))
    pm = np.ma.masked_where(is_park, pop)
    cmap = plt.get_cmap("Blues").copy(); cmap.set_bad("#bfe3d4")
    im = ax.imshow(pm, origin="lower", cmap=cmap)
    draw_bounds(ax)
    cb = fig.colorbar(im, ax=ax, shrink=.8); cb.set_label("マスの人口（人、1マス＝0.25km²）")
    ax.set_title(f"架空の町の人口と12の区（緑のマスは公園・池、人口0）", fontsize=11)
    save(fig, "a946_population.png", SRC, y=0.08)

    # 図2：2つの密度の地図（3段の色）
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 5.2))
    cols = np.array(["#1f5fa8", "#7fb0e6", "#e3eefa"])
    for ax, col, ttl, fmt in [(axes[0], "per_km2", "店の数÷面積（1km²あたりの店の数）", "{:.1f}"),
                              (axes[1], "per_10k_people", "店の数÷人口（1万人あたりの店の数）", "{:.1f}")]:
        b = band(ex[col].values)
        rgb = np.array([[int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)] for c in cols])
        ax.imshow(rgb[b[z]], origin="lower")
        draw_bounds(ax, [fmt.format(v) for v in ex[col].values])
        ax.set_title(ttl, fontsize=10.5)
    from matplotlib.patches import Patch
    fig.legend([Patch(color=c) for c in cols], ["多い4区", "中ほどの4区", "少ない4区"], loc="lower center",
               ncol=3, frameon=False, fontsize=9, bbox_to_anchor=(0.5, 0.02))
    fig.suptitle(f"同じ店の数でも、割る数で色が変わる（色の段が変わった区：12区のうち{ex_cmp['band_changed_area_vs_people']}区）",
                 fontsize=12)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, "a946_two_maps.png", SRC)

    # 図3：β と順位相関
    rb = rob[rob["変えたもの"].str.startswith("店の人口")]
    xb = rb["値"].astype(float).values
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(xb, rb["面積と人口の順位相関"], "o-", color=BLUE, lw=2, label="面積で割った地図 と 人口で割った地図")
    ax.plot(xb, rb["面積で割った地図と人口密度の順位相関"], "s--", color=GRAY, lw=1.5, label="面積で割った地図 と 人口密度の地図")
    ax.plot(xb, rb["人口で割った地図と人口密度の順位相関"], "^:", color=ORANGE, lw=1.5, label="人口で割った地図 と 人口密度の地図")
    ax.axhline(0, color=GRAY, lw=.8)
    ax.axvline(1.0, color=GRAY, lw=.8, ls=":")
    ax.set_xlabel("店の人口への寄り方 β（0＝人が住むマスに同じだけ、1＝人口に比例）"); ax.set_ylabel("12区の順位相関（300回の平均）")
    ax.set_ylim(-1.05, 1.05)
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=1)
    ax.set_title("2つの地図が似るか逆になるかは、店が人口にどれだけ寄るかで決まる")
    save(fig, "a946_beta.png", SRC, y=-0.2)
    print(json.dumps({k: v for k, v in out.items() if k not in ("robustness", "example_districts")}, ensure_ascii=False, indent=1))
    print(rob.to_string())
    print(ex.round(2).to_string())


if __name__ == "__main__":
    main()
