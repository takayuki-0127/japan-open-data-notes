"""954 区域を細かくすると、相関はどう変わるのか？（架空のデータ）

架空の町を48×48のマス（1マス＝1街区）に分け、世帯を置く。世帯ごとに
「店での1か月の買い物額」と「ネット注文の1か月の額」を作成者が置く。
2つの額は、場所で決まる分（なめらかに変わる町の傾向）と、世帯ごとの分の足し算。
同じ世帯を、1×1マスから24×24マスまでの四角い区域でまとめ、区域ごとの平均どうしの相関を数える。
"""
import json
import time
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 954
SRC = "架空の町の世帯の買い物額（作成者が乱数で作成、seed 954）"
G = 48
BLOCKS = [1, 2, 3, 4, 6, 8, 12, 16, 24]     # 区域の1辺（マス）
BASE = dict(w=0.10, rho_s=0.8, rho_e=0.1, L=4.0, hh=8.0)
REPS = 200
STORE_MEAN, STORE_SD = 30.0, 8.0            # 千円／月
NET_MEAN, NET_SD = 12.0, 4.0


def field(rng, L):
    """なめらかな場所の傾向（平均0・標準偏差1）。端はつながっていない"""
    pad = int(3 * L) + 1
    f = gaussian_filter(rng.normal(0, 1, (G + 2 * pad, G + 2 * pad)), L)[pad:-pad, pad:-pad]
    return (f - f.mean()) / f.std()


def make_town(rng, w, rho_s, rho_e, L, hh):
    f1, f2 = field(rng, L), field(rng, L)
    s1 = f1.ravel()
    s2 = (rho_s * f1 + np.sqrt(1 - rho_s ** 2) * f2).ravel()
    n = rng.poisson(hh, G * G)
    cell = np.repeat(np.arange(G * G), n)
    e1 = rng.normal(0, 1, len(cell))
    e2 = rho_e * e1 + np.sqrt(1 - rho_e ** 2) * rng.normal(0, 1, len(cell))
    z1 = np.sqrt(w) * s1[cell] + np.sqrt(1 - w) * e1
    z2 = np.sqrt(w) * s2[cell] + np.sqrt(1 - w) * e2
    x = np.clip(STORE_MEAN + STORE_SD * z1, 0, None)
    y = np.clip(NET_MEAN + NET_SD * z2, 0, None)
    return cell, x, y, s1, s2


def zone_of(cell, b):
    r, c = cell // G, cell % G
    return (r // b) * (G // b) + (c // b)


def zone_means(cell, v, b):
    z = zone_of(cell, b)
    k = (G // b) ** 2
    cnt = np.bincount(z, minlength=k)
    s = np.bincount(z, weights=v, minlength=k)
    ok = cnt > 0
    return s[ok] / cnt[ok], cnt[ok], ok


def corr(a, b):
    return float(np.corrcoef(a, b)[0, 1])


def formula(cell, s1, s2, w, rho_e, b):
    """区域の平均どうしの相関の式：場所で決まる分の共分散＋世帯ごとの分が人数で薄まった分"""
    m1, cnt, _ = zone_means(cell, np.sqrt(w) * s1[cell], b)
    m2, _, _ = zone_means(cell, np.sqrt(w) * s2[cell], b)
    inv = np.mean(1.0 / cnt)
    c = np.cov(m1, m2)
    num = c[0, 1] + (1 - w) * rho_e * inv
    den = np.sqrt((c[0, 0] + (1 - w) * inv) * (c[1, 1] + (1 - w) * inv))
    return float(num / den)


def one_town(rng, w, rho_s, rho_e, L, hh, with_formula=False):
    cell, x, y, s1, s2 = make_town(rng, w, rho_s, rho_e, L, hh)
    out = {"household": corr(x, y)}
    for b in BLOCKS:
        mx, _, _ = zone_means(cell, x, b)
        my, _, _ = zone_means(cell, y, b)
        out[f"b{b}"] = corr(mx, my)
        if with_formula:
            out[f"f{b}"] = formula(cell, s1, s2, w, rho_e, b)
    return out


def run(seed0, reps, with_formula=False, **kw):
    p = {**BASE, **kw}
    rows = [one_town(np.random.default_rng(seed0 + r), with_formula=with_formula, **p) for r in range(reps)]
    return pd.DataFrame(rows)


def main():
    t0 = time.time()
    res = {"base": BASE, "reps": REPS, "households_per_town_mean": None}

    # 1) 例の町1つ
    rng = np.random.default_rng(SEED)
    cell, x, y, s1, s2 = make_town(rng, **BASE)
    hh = pd.DataFrame({"household_id": np.arange(1, len(cell) + 1), "row": cell // G, "col": cell % G,
                       "store_k": x, "net_k": y})
    hh.to_csv(DATA / "households_example_town.csv", index=False, float_format="%.2f")
    ex_rows = []
    for b in BLOCKS:
        mx, cnt, _ = zone_means(cell, x, b)
        my, _, _ = zone_means(cell, y, b)
        ex_rows.append({"block": b, "zones": int(len(mx)), "households_per_zone_mean": round(float(cnt.mean()), 1),
                        "corr": round(corr(mx, my), 3)})
    ex = pd.DataFrame(ex_rows)
    ex.to_csv(RES / "example_town_by_scale.csv", index=False)
    res["example_town"] = {"households": int(len(cell)), "household_corr": round(corr(x, y), 3),
                           "store_mean": round(float(x.mean()), 2), "net_mean": round(float(y.mean()), 2),
                           "by_scale": ex_rows}

    # 2) 町を200回作り直して（基本の置き方）
    sim = run(SEED * 1000, REPS, with_formula=True)
    nz = {b: (G // b) ** 2 for b in BLOCKS}
    tab = [{"block": "世帯ごと", "zones": None, "households_per_zone": 1.0,
            "corr_mean": round(sim.household.mean(), 3), "corr_p10": round(sim.household.quantile(.1), 3),
            "corr_p90": round(sim.household.quantile(.9), 3), "formula_mean": None,
            "share_corr_over_0_5": round(float((sim.household > 0.5).mean()), 3)}]
    for b in BLOCKS:
        c = sim[f"b{b}"]
        tab.append({"block": f"{b}×{b}マス", "zones": nz[b], "households_per_zone": BASE["hh"] * b * b,
                    "corr_mean": round(c.mean(), 3), "corr_p10": round(c.quantile(.1), 3),
                    "corr_p90": round(c.quantile(.9), 3), "formula_mean": round(sim[f"f{b}"].mean(), 3),
                    "share_corr_over_0_5": round(float((c > 0.5).mean()), 3)})
    tab = pd.DataFrame(tab)
    tab.to_csv(RES / "by_scale_200_towns.csv", index=False)
    res["by_scale"] = tab.to_dict(orient="records")
    res["formula_max_abs_gap"] = round(float(max(abs(sim[f"b{b}"].mean() - sim[f"f{b}"].mean()) for b in BLOCKS)), 3)
    res["household_corr_formula"] = round(BASE["w"] * BASE["rho_s"] + (1 - BASE["w"]) * BASE["rho_e"], 3)

    # 3) 場所の傾向どうしに関係がないとき（rho_s=0）と、世帯ごとの向きが逆のとき（rho_e=-0.2）
    special = []
    for name, kw in [("場所の傾向どうしの相関0", dict(rho_s=0.0)),
                     ("世帯ごとの相関−0.2", dict(rho_e=-0.2))]:
        s = run(SEED * 2000 + len(special) * 500, REPS, **kw)
        for col in ["household"] + [f"b{b}" for b in BLOCKS]:
            special.append({"case": name, "level": col, "zones": None if col == "household" else nz[int(col[1:])],
                            "corr_mean": round(s[col].mean(), 3), "corr_p10": round(s[col].quantile(.1), 3),
                            "corr_p90": round(s[col].quantile(.9), 3),
                            "share_over_0_5": round(float((s[col] > 0.5).mean()), 3),
                            "share_negative": round(float((s[col] < 0).mean()), 3),
                            "share_abs_over_0_5": round(float((s[col].abs() > 0.5).mean()), 3)})
    special = pd.DataFrame(special)
    special.to_csv(RES / "special_cases.csv", index=False)
    res["special_cases"] = special.to_dict(orient="records")

    # 4) 確かめ：置き方を変えて（各50の町）
    grid = []
    k = 0
    for w in [0.05, 0.10, 0.30]:
        for rho_s in [0.0, 0.5, 0.8]:
            for rho_e in [-0.2, 0.0, 0.1, 0.3]:
                s = run(SEED * 5000 + k * 100, 50, w=w, rho_s=rho_s, rho_e=rho_e)
                k += 1
                grid.append({"w": w, "rho_s": rho_s, "rho_e": rho_e, "L": BASE["L"], "hh": BASE["hh"],
                             "household": round(s.household.mean(), 3), "b1": round(s.b1.mean(), 3),
                             "b4": round(s.b4.mean(), 3), "b8": round(s.b8.mean(), 3),
                             "b16": round(s.b16.mean(), 3),
                             "b16_p10": round(s.b16.quantile(.1), 3), "b16_p90": round(s.b16.quantile(.9), 3)})
    for L in [2.0, 8.0]:
        s = run(SEED * 7000 + int(L) * 100, 50, L=L)
        grid.append({"w": BASE["w"], "rho_s": BASE["rho_s"], "rho_e": BASE["rho_e"], "L": L, "hh": BASE["hh"],
                     "household": round(s.household.mean(), 3), "b1": round(s.b1.mean(), 3),
                     "b4": round(s.b4.mean(), 3), "b8": round(s.b8.mean(), 3), "b16": round(s.b16.mean(), 3),
                     "b16_p10": round(s.b16.quantile(.1), 3), "b16_p90": round(s.b16.quantile(.9), 3)})
    for h in [2.0, 32.0]:
        s = run(SEED * 8000 + int(h) * 100, 50, hh=h)
        grid.append({"w": BASE["w"], "rho_s": BASE["rho_s"], "rho_e": BASE["rho_e"], "L": BASE["L"], "hh": h,
                     "household": round(s.household.mean(), 3), "b1": round(s.b1.mean(), 3),
                     "b4": round(s.b4.mean(), 3), "b8": round(s.b8.mean(), 3), "b16": round(s.b16.mean(), 3),
                     "b16_p10": round(s.b16.quantile(.1), 3), "b16_p90": round(s.b16.quantile(.9), 3)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "robustness.csv", index=False)
    g = grid[(grid.L == BASE["L"]) & (grid.hh == BASE["hh"])]
    gpos = g[g.rho_s > 0]
    res["robustness"] = {
        "combos": int(len(grid)),
        "b8_minus_household_rho_s_pos_min": round(float((gpos.b8 - gpos.household).min()), 3),
        "b8_minus_household_rho_s_pos_max": round(float((gpos.b8 - gpos.household).max()), 3),
        "household_range_rho_s_pos": [float(gpos.household.min()), float(gpos.household.max())],
        "b8_range_rho_s_pos": [float(gpos.b8.min()), float(gpos.b8.max())],
        "sign_flip_combos": int(((g.household < 0) & (g.b8 > 0)).sum()),
        "base_row_b8": float(g[(g.w == 0.1) & (g.rho_s == 0.8) & (g.rho_e == 0.1)].b8.iloc[0]),
    }

    # 図1：例の町の地図（3つの大きさ）
    fig, axes = plt.subplots(2, 3, figsize=(10.5, 6.6))
    for j, b in enumerate([2, 8, 16]):
        for i, (v, cmap, lab) in enumerate([(x, "Blues", "店での買い物額"), (y, "Oranges", "ネット注文の額")]):
            z = zone_of(cell, b)
            k = (G // b) ** 2
            cnt = np.bincount(z, minlength=k)
            m = np.bincount(z, weights=v, minlength=k) / np.maximum(cnt, 1)
            img = np.repeat(np.repeat(m.reshape(G // b, G // b), b, 0), b, 1)
            ax = axes[i, j]
            im = ax.imshow(img, cmap=cmap, vmin=np.percentile(img, 2), vmax=np.percentile(img, 98))
            ax.set_xticks([]); ax.set_yticks([])
            if i == 0:
                cc = ex.loc[ex.block == b, "corr"].iloc[0]
                ax.set_title(f"{b}×{b}マスの区域（{(G // b) ** 2}区域）\n2つの額の相関 {cc:.2f}", fontsize=11)
            if j == 0:
                ax.set_ylabel(f"{lab}（区域の平均）", fontsize=10)
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03).set_label("千円／月", fontsize=8)
    fig.suptitle(f"同じ世帯でも、区域を大きくすると2つの地図は似てくる（世帯ごとの相関 {corr(x, y):.2f}）", fontsize=13)
    save(fig, "a954_maps.png", SRC + "。架空の町48×48マス・世帯約1万8千。色の幅は区域の大きさごとに変えている")

    # 図2：区域の数と相関
    fig, ax = plt.subplots(figsize=(8.6, 5.0))
    zs = [nz[b] for b in BLOCKS]
    for (dfc, col, lab) in [(sim, BLUE, "基本（場所の傾向どうしの相関0.8）")]:
        ax.fill_between(zs, [dfc[f"b{b}"].quantile(.1) for b in BLOCKS], [dfc[f"b{b}"].quantile(.9) for b in BLOCKS],
                        color=LIGHT, alpha=0.7, lw=0)
        ax.plot(zs, [dfc[f"b{b}"].mean() for b in BLOCKS], "o-", color=col, label=lab + "：平均と10〜90%")
    ax.plot(zs, [sim[f"f{b}"].mean() for b in BLOCKS], "x--", color=INK, lw=1, label="式で出した値")
    s0 = special[special.case == "場所の傾向どうしの相関0"]
    s0z = s0[s0.level != "household"]
    ax.fill_between(zs, s0z.corr_p10, s0z.corr_p90, color=GRAY, alpha=0.25, lw=0)
    ax.plot(zs, s0z.corr_mean, "s-", color=GRAY, label="場所の傾向どうしの相関0：平均と10〜90%")
    ax.axhline(sim.household.mean(), color=ORANGE, ls=":", lw=1.5)
    ax.text(1700, sim.household.mean() + 0.03, f"世帯ごとの相関（200の町の平均）{sim.household.mean():.2f}",
            color=ORANGE, ha="left", fontsize=10)
    ax.axhline(0, color=GRAY, lw=0.6)
    ax.set_xscale("log")
    ax.set_xticks(zs); ax.set_xticklabels([f"{z:,}\n({b}×{b})" for z, b in zip(zs, BLOCKS)], fontsize=8)
    ax.invert_xaxis()
    ax.set_xlabel("区域の数（区域の1辺のマス）　← 細かい　　　大きい →")
    ax.set_ylabel("区域の平均どうしの相関")
    ax.set_ylim(-1, 1.05)
    ax.set_title("区域を大きくするほど、相関は世帯ごとの値から離れる（200の町）")
    ax.legend(fontsize=8.5, loc="lower left", frameon=False)
    save(fig, "a954_corr_by_scale.png", SRC + "。200の町の平均と10〜90%の範囲")

    # 図3：世帯の散らばりと、36区域の平均の散らばり
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
    pick = np.random.default_rng(SEED + 1).choice(len(x), 2000, replace=False)
    axes[0].scatter(x[pick], y[pick], s=5, color=BLUE, alpha=0.35, lw=0)
    axes[0].set_title(f"世帯ごと（2,000世帯を表示）　相関 {corr(x, y):.2f}", fontsize=11)
    mx, _, _ = zone_means(cell, x, 8)
    my, _, _ = zone_means(cell, y, 8)
    axes[1].scatter(mx, my, s=28, color=ORANGE, alpha=0.9, lw=0)
    axes[1].set_title(f"8×8マスの区域の平均（36区域）　相関 {corr(mx, my):.2f}", fontsize=11)
    for ax in axes:
        ax.set_xlabel("店での買い物額（千円／月）")
        ax.set_ylabel("ネット注文の額（千円／月）")
    fig.suptitle("同じ町の同じ世帯を、1世帯ずつ見るか区域の平均で見るか", fontsize=13)
    fig.tight_layout()
    save(fig, "a954_scatter.png", SRC + "。例の町1つ")

    res["households_per_town_mean"] = int(round(BASE["hh"] * G * G))
    res["run_sec"] = round(time.time() - t0, 1)
    run_sec = res.pop("run_sec")
    with open(RES / "a954_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print("sec", run_sec)


if __name__ == "__main__":
    main()
