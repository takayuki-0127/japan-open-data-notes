"""948 小さい区域の率は、なぜ地図の端に極端な色が出やすいのか？（架空のデータ）

架空の町を20×20の格子（400区域）に分ける。架空の店の会員は町の中心に多く、外側ほど少ない。
区域ごとの「この1か月に買った会員の割合（購入率）」を色で塗る。
本当の購入率は作成者が置き、場所とは関係なく区域ごとに少しずつ違うとする。
"""
import json
import time
import numpy as np
import pandas as pd
from scipy.special import betaln
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 948
SRC = "架空の町の区域と店の会員（作成者が乱数で作成、seed 948）"
G = 20
BASE_P = 0.20
TAU = 0.2          # 本当の購入率の区域どうしの差（ロジットの標準偏差）
SCALE = 1.0        # 会員数の倍率
REPS = 200
BANDS = [(0, 10, "10人未満"), (10, 30, "10〜29人"), (30, 100, "30〜99人"), (100, 10**9, "100人以上")]

ii, jj = np.meshgrid(np.arange(G), np.arange(G), indexing="ij")
DIST = np.hypot(ii - (G - 1) / 2, jj - (G - 1) / 2).ravel()
RING = np.minimum.reduce([ii, jj, G - 1 - ii, G - 1 - jj]).ravel()
OUTER = RING < 2   # 外側の2列の区域（144区域）


def logit(p):
    return np.log(p / (1 - p))


def make_town(rng, tau=TAU, scale=SCALE):
    n = np.round(scale * 300 * np.exp(-DIST / 3.0) * np.exp(rng.normal(0, 0.3, G * G))).astype(int)
    n = np.maximum(n, 2)
    p = 1 / (1 + np.exp(-(logit(BASE_P) + tau * rng.normal(0, 1, G * G))))
    x = rng.binomial(n, p)
    return n, p, x


def shrink(n, x):
    """全体の購入率に、区域の会員数に応じて寄せる（ベータ二項分布の尤度が最大になる m を格子で探す）"""
    pbar = x.sum() / n.sum()
    ms = np.logspace(0, 6, 121)
    ll = [(betaln(x + m * pbar, n - x + m * (1 - pbar)) - betaln(m * pbar, m * (1 - pbar))).sum() for m in ms]
    m = float(ms[int(np.argmax(ll))])
    return (x + m * pbar) / (n + m), pbar, m


def extremes(score, rng, k=40):
    """上位k・下位kの区域（同じ値は乱数で順を決める）"""
    jit = rng.random(len(score))
    order = np.lexsort((jit, score))
    return order[:k], order[-k:]


def band_of(n):
    out = np.empty(len(n), dtype=object)
    for lo, hi, lab in BANDS:
        out[(n >= lo) & (n < hi)] = lab
    return out


def funnel_out(n, x, pbar):
    """全体の購入率のまわりの95%の帯（正規近似）の外に出た区域"""
    se = np.sqrt(pbar * (1 - pbar) / n)
    r = x / n
    return np.abs(r - pbar) > 1.96 * se


def one_rep(rng, tau=TAU, scale=SCALE):
    n, p, x = make_town(rng, tau, scale)
    r = x / n
    s, pbar, m = shrink(n, x)
    lo, hi = extremes(r, rng)
    ext = np.zeros(G * G, bool); ext[lo] = True; ext[hi] = True
    slo, shi = extremes(s, rng)
    sext = np.zeros(G * G, bool); sext[slo] = True; sext[shi] = True
    tlo, thi = extremes(p, rng)
    small = n < 30
    out = {"outer_share_ext": OUTER[ext].mean(), "outer_share_shrunk_ext": OUTER[sext].mean(),
           "small_share_ext": small[ext].mean(), "small_share_shrunk_ext": small[sext].mean(),
           "hit_top_raw": len(set(hi) & set(thi)) / 40, "hit_top_shrunk": len(set(shi) & set(thi)) / 40,
           "hit_bottom_raw": len(set(lo) & set(tlo)) / 40, "hit_bottom_shrunk": len(set(slo) & set(tlo)) / 40,
           "m": m, "log10_m": np.log10(m), "funnel_out_share": funnel_out(n, x, pbar).mean()}
    return out, (n, p, x, r, s, ext, sext, pbar)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1回分の町（data と図に使う）
    _, (n, p, x, r, s, ext, sext, pbar) = one_rep(np.random.default_rng(SEED))
    df = pd.DataFrame({"row": ii.ravel(), "col": jj.ravel(), "outer": OUTER.astype(int), "members": n, "buyers": x,
                       "rate": r, "true_rate": p, "shrunk_rate": s, "extreme_raw": ext.astype(int),
                       "extreme_shrunk": sext.astype(int)})
    df.to_csv(DATA / "town_example.csv", index=False, float_format="%.4f")
    one = {"total_members": int(n.sum()), "members_min": int(n.min()), "members_max": int(n.max()),
           "members_median": float(np.median(n)), "outer_members_share": round(float(n[OUTER].sum() / n.sum()), 4),
           "outer_area_share": round(float(OUTER.mean()), 4), "overall_rate": round(float(pbar), 4),
           "rate_min": round(float(r.min()), 4), "rate_max": round(float(r.max()), 4),
           "true_rate_min": round(float(p.min()), 4), "true_rate_max": round(float(p.max()), 4),
           "n_rate_zero": int((x == 0).sum()), "outer_in_extremes": int(OUTER[ext].sum()),
           "outer_in_extremes_shrunk": int(OUTER[sext].sum()),
           "shrunk_min": round(float(s.min()), 4), "shrunk_max": round(float(s.max()), 4)}

    # 2) 200回の町で
    rows, band_rows = [], []
    for k in range(REPS):
        rr = np.random.default_rng(SEED * 1000 + k)
        o, (n, p, x, r, s, ext, sext, pb) = one_rep(rr)
        o["rep"] = k
        rows.append(o)
        b = band_of(n)
        fo = funnel_out(n, x, pb)
        for _, _, lab in BANDS:
            sel = b == lab
            band_rows.append({"rep": k, "band": lab, "areas": int(sel.sum()), "ext_raw": int((ext & sel).sum()),
                              "ext_shrunk": int((sext & sel).sum()), "funnel_out": int((fo & sel).sum()),
                              "abs_err_raw": float(np.abs(r - p)[sel].sum()),
                              "abs_err_shrunk": float(np.abs(s - p)[sel].sum())})
    sim = pd.DataFrame(rows)
    summ = sim.drop(columns=["rep", "m", "log10_m"]).mean().round(4).to_dict()
    summ["m_median"] = round(float(sim.m.median()), 1)
    summ["m_p10"] = round(float(sim.m.quantile(.1)), 1)
    summ["m_p90"] = round(float(sim.m.quantile(.9)), 1)
    bd = pd.DataFrame(band_rows).groupby("band", sort=False).sum().drop(columns="rep")
    bd = bd.loc[[lab for _, _, lab in BANDS]]
    tab = pd.DataFrame({"band": bd.index,
                        "areas_per_town": (bd.areas / REPS).round(1).values,
                        "share_of_areas": (bd.areas / bd.areas.sum()).round(4).values,
                        "share_of_extremes_raw": (bd.ext_raw / bd.ext_raw.sum()).round(4).values,
                        "share_of_extremes_shrunk": (bd.ext_shrunk / bd.ext_shrunk.sum()).round(4).values,
                        "rate_in_extremes_raw": (bd.ext_raw / bd.areas).round(4).values,
                        "funnel_out_rate": (bd.funnel_out / bd.areas).round(4).values,
                        "mean_abs_err_raw_pt": (bd.abs_err_raw / bd.areas * 100).round(2).values,
                        "mean_abs_err_shrunk_pt": (bd.abs_err_shrunk / bd.areas * 100).round(2).values})
    tab.to_csv(RES / "by_members_band.csv", index=False)

    # 3) 本当の差がないとき（tau=0）の、帯の外に出る割合（会員数の層ごと）
    null_rows = []
    for k in range(REPS):
        rr = np.random.default_rng(SEED * 3000 + k)
        n, p, x = make_town(rr, 0.0)
        pb = x.sum() / n.sum()
        fo = funnel_out(n, x, pb)
        r = x / n
        lo, hi = extremes(r, rr)
        ext = np.zeros(G * G, bool); ext[lo] = True; ext[hi] = True
        b = band_of(n)
        for _, _, lab in BANDS:
            sel = b == lab
            null_rows.append({"band": lab, "areas": int(sel.sum()), "funnel_out": int((fo & sel).sum()),
                              "ext": int((ext & sel).sum())})
    nb = pd.DataFrame(null_rows).groupby("band", sort=False).sum().loc[[lab for _, _, lab in BANDS]]
    null_tab = pd.DataFrame({"band": nb.index, "funnel_out_rate": (nb.funnel_out / nb.areas).round(4).values,
                             "rate_in_extremes": (nb.ext / nb.areas).round(4).values,
                             "share_of_extremes": (nb.ext / nb.ext.sum()).round(4).values})
    null_tab.to_csv(RES / "no_true_difference.csv", index=False)
    null_small = round(float(nb.ext.iloc[:2].sum() / nb.ext.sum()), 4)

    # 4) 確かめ：本当の差 tau × 会員数の倍率（12通り、各50回）
    sens = []
    for tau in [0.0, 0.1, 0.2, 0.4]:
        for sc in [0.5, 1.0, 2.0]:
            ss = [one_rep(np.random.default_rng(SEED * 7000 + int(tau * 100) * 10 + int(sc * 2) * 100000 + k), tau, sc)[0]
                  for k in range(50)]
            ss = pd.DataFrame(ss).mean()
            sens.append({"tau": tau, "members_scale": sc, "outer_share_ext": round(ss.outer_share_ext, 4),
                         "outer_share_shrunk_ext": round(ss.outer_share_shrunk_ext, 4),
                         "small_share_ext": round(ss.small_share_ext, 4),
                         "hit_top_raw": round(ss.hit_top_raw, 4) if tau > 0 else None,
                         "hit_top_shrunk": round(ss.hit_top_shrunk, 4) if tau > 0 else None})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity_grid.csv", index=False)
    pos = sens[sens.tau > 0]

    out = {"setup": {"grid": f"{G}x{G}", "areas": G * G, "outer_areas": int(OUTER.sum()), "base_rate": BASE_P,
                     "tau_logit_sd": TAU, "reps": REPS, "extreme_k_each_side": 40},
           "one_town": one, "mean_over_200": summ,
           "by_members_band": tab.to_dict("records"), "no_true_difference": null_tab.to_dict("records"),
           "no_true_difference_share_of_extremes_members_lt30": null_small,
           "sensitivity": {"outer_share_ext_range": [float(sens.outer_share_ext.min()), float(sens.outer_share_ext.max())],
                           "outer_share_shrunk_ext_range": [float(sens.outer_share_shrunk_ext.min()),
                                                            float(sens.outer_share_shrunk_ext.max())],
                           "hit_top_raw_range_tau_pos": [float(pos.hit_top_raw.min()), float(pos.hit_top_raw.max())],
                           "hit_top_shrunk_range_tau_pos": [float(pos.hit_top_shrunk.min()), float(pos.hit_top_shrunk.max())],
                           "shrunk_better_in_all_tau_pos": bool((pos.hit_top_shrunk >= pos.hit_top_raw).all()),
                           "grid": sens.astype(object).where(pd.notna(sens), None).to_dict("records")}}

    # 図1：会員数の地図と、購入率の地図（1回分）
    d = df
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.6), gridspec_kw={"wspace": 0.45})
    im0 = axes[0].imshow(np.log10(d.members.values.reshape(G, G)), cmap="Greys", vmin=0, vmax=np.log10(400))
    cb = fig.colorbar(im0, ax=axes[0], fraction=.046, pad=.03, ticks=np.log10([2, 10, 30, 100, 300]))
    cb.ax.set_yticklabels(["2", "10", "30", "100", "300"]); cb.set_label("会員数（人、対数の目盛り）")
    axes[0].set_title("区域ごとの会員数", fontsize=11)
    im1 = axes[1].imshow(d.rate.values.reshape(G, G) * 100, cmap="Blues", vmin=0, vmax=60)
    cb = fig.colorbar(im1, ax=axes[1], fraction=.046, pad=.03); cb.set_label("見かけの購入率（%）")
    for k in np.where(d.extreme_raw.values == 1)[0]:
        axes[1].add_patch(Rectangle((d.col[k] - .5, d.row[k] - .5), 1, 1, fill=False, ec=ORANGE, lw=1.3))
    axes[1].set_title("見かけの購入率（橙の枠＝上下1割の区域）", fontsize=11)
    for ax in axes:
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(f"上下1割の80区域のうち{one['outer_in_extremes']}区域が、外側の2列（全体の36%）にあった（1回分の町）",
                 fontsize=12, y=1.0)
    save(fig, "a948_maps.png", SRC)

    # 図2：会員数と見かけの購入率（ろうと形）
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    ax.scatter(d.members, d.rate * 100, s=12, color=np.where(d.outer == 1, ORANGE, BLUE), alpha=.6, lw=0)
    nn = np.logspace(np.log10(2), np.log10(d.members.max()), 200)
    pb = one["overall_rate"]
    se = np.sqrt(pb * (1 - pb) / nn)
    ax.plot(nn, (pb + 1.96 * se) * 100, color=GRAY, lw=1, ls="--")
    ax.plot(nn, np.maximum(pb - 1.96 * se, 0) * 100, color=GRAY, lw=1, ls="--")
    ax.axhline(pb * 100, color=INK, lw=.8)
    ax.set_xscale("log"); ax.set_xlabel("区域の会員数（対数の目盛り）"); ax.set_ylabel("見かけの購入率（%）")
    ax.text(300, 50, "点線：全体の率のまわりの95%の帯", fontsize=8.5, color=GRAY, ha="right")
    ax.scatter([], [], color=ORANGE, s=12, label="外側の2列の区域"); ax.scatter([], [], color=BLUE, s=12, label="内側の区域")
    ax.legend(frameon=False, fontsize=9, loc="upper right", bbox_to_anchor=(1, 0.9))
    ax.set_title("会員の少ない区域ほど、購入率は上にも下にも振れる（1回分の町）")
    save(fig, "a948_funnel.png", SRC)

    # 図3：会員数の層ごとの、区域の割合と上下1割に入った割合
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    xs = np.arange(len(tab)); w = .27
    for off, col, c, lab in [(-w, "share_of_areas", GRAY, "全区域に占める割合"),
                             (0, "share_of_extremes_raw", ORANGE, "上下1割の区域に占める割合（見かけの率）"),
                             (w, "share_of_extremes_shrunk", BLUE, "上下1割の区域に占める割合（会員数で寄せた率）")]:
        v = tab[col].values * 100
        ax.bar(xs + off, v, w, color=c, label=lab)
        for xx, vv in zip(xs + off, v):
            ax.text(xx, vv + 1, f"{vv:.0f}", ha="center", fontsize=8)
    ax.set_xticks(xs); ax.set_xticklabels([f"会員{b}" for b in tab.band]); ax.set_ylabel("%（200回の町の合計）")
    ax.set_ylim(0, 100); ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("見かけの率で上下1割を塗ると、会員10人未満の区域が多く入る")
    save(fig, "a948_bands.png", SRC)

    json.dump(out, open(RES / "a948_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
