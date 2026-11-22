"""955 地図の上の「空白」は、ゼロなのかデータがないのか？（架空のデータ）

架空の町を20×20の区域（400区域）に分け、架空の店の配達の注文の件数を区域ごとに地図にする。
地図で空白（色なし）になる区域には、次の3つがまざる：
  ① 本当に0件だった区域
  ② 1〜2件あったが「3件未満は出さない」決まりで空白にした区域
  ③ 配達の対象外で、そもそもデータがない区域（東の3列）
区域ごとの本当の注文の起きやすさ（月の平均件数）は作成者が置く。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 955
SRC = "架空の町の配達の注文（作成者が乱数で作成、seed 955）"
G = 20
BASE = dict(mean=4.0, sigma=0.9, thr=3, unserved=3)
REPS = 200
TYPES = ["本当に0件", "1〜2件（出さない決まり）", "配達の対象外（データなし）"]


def make_town(rng, mean, sigma, unserved):
    lam = mean * np.exp(rng.normal(-sigma ** 2 / 2, sigma, G * G))
    col = np.tile(np.arange(G), G)
    served = col < G - unserved
    y1 = rng.poisson(lam)
    y2 = rng.poisson(lam)
    return lam, served, y1, y2


def read_map(y, served, thr):
    """地図に出る値（空白は NaN）と、空白の種類"""
    shown = served & (y >= thr)
    kind = np.full(len(y), "", dtype=object)
    kind[served & (y == 0)] = TYPES[0]
    kind[served & (y > 0) & (y < thr)] = TYPES[1]
    kind[~served] = TYPES[2]
    val = np.where(shown, y, np.nan)
    return val, shown, kind


def one_town(rng, mean, sigma, thr, unserved):
    lam, served, y1, y2 = make_town(rng, mean, sigma, unserved)
    val, shown, kind = read_map(y1, served, thr)
    blank = ~shown
    nb = blank.sum()
    o = {"blank_zones": int(nb),
         "blank_share_true_zero": (kind == TYPES[0]).sum() / nb if nb else np.nan,
         "blank_share_suppressed": (kind == TYPES[1]).sum() / nb if nb else np.nan,
         "blank_share_unserved": (kind == TYPES[2]).sum() / nb if nb else np.nan,
         # 区域あたりの平均件数の読み方
         "mean_blank_as_zero": np.nansum(val) / (G * G),
         "mean_blank_as_zero_served_only": np.nansum(val) / served.sum() if served.any() else np.nan,
         "mean_blank_dropped": np.nanmean(val) if shown.any() else np.nan,
         "mean_true_served": y1[served].mean() if served.any() else np.nan,
         "mean_potential_all": lam.mean(),
         # 「注文がなかった区域」の割合
         "zero_share_read_from_map": nb / (G * G),
         "zero_share_true_served": (y1[served] == 0).mean() if served.any() else np.nan,
         # 次の月
         "true_zero_next_ge1": (y2[served & (y1 == 0)] >= 1).mean() if (served & (y1 == 0)).any() else np.nan,
         "served_blank_next_shown": (y2[served & blank] >= thr).mean() if (served & blank).any() else np.nan,
         "true_zero_next_ge3": (y2[served & (y1 == 0)] >= 3).mean() if (served & (y1 == 0)).any() else np.nan,
         "true_zero_zones": int((served & (y1 == 0)).sum()),
         "lam_lt_0_5_share_of_true_zero": (lam[served & (y1 == 0)] < 0.5).mean() if (served & (y1 == 0)).any() else np.nan,
         "unserved_potential_share": lam[~served].sum() / lam.sum()}
    return o


def run(seed0, reps, **kw):
    p = {**BASE, **kw}
    return pd.DataFrame([one_town(np.random.default_rng(seed0 + r), **p) for r in range(reps)])


def main():
    t0 = time.time()
    res = {"base": BASE, "reps": REPS, "zones": G * G, "served_zones": G * (G - BASE["unserved"]),
           "unserved_zones": G * BASE["unserved"]}

    # 1) 例の町1つ
    rng = np.random.default_rng(SEED)
    lam, served, y1, y2 = make_town(rng, BASE["mean"], BASE["sigma"], BASE["unserved"])
    val, shown, kind = read_map(y1, served, BASE["thr"])
    row, col = np.repeat(np.arange(G), G), np.tile(np.arange(G), G)
    ex = pd.DataFrame({"zone_id": np.arange(1, G * G + 1), "row": row, "col": col, "served": served.astype(int),
                       "true_mean_orders": lam, "orders_month1": np.where(served, y1, -1),
                       "orders_month2": np.where(served, y2, -1),
                       "map_value_month1": val, "blank_kind_month1": kind})
    ex.to_csv(DATA / "zones_example_town.csv", index=False, float_format="%.3f")
    o = one_town(np.random.default_rng(SEED), **BASE)
    res["example_town"] = {k: (round(float(v), 4) if isinstance(v, float) else v) for k, v in o.items()}
    res["example_town"].update({"blank_true_zero": int((kind == TYPES[0]).sum()),
                                "blank_suppressed": int((kind == TYPES[1]).sum()),
                                "blank_unserved": int((kind == TYPES[2]).sum()),
                                "shown_zones": int(shown.sum()), "orders_total_served": int(y1[served].sum())})

    # 2) 200の町（基本）
    sim = run(SEED * 1000, REPS)
    summ = {c: round(float(sim[c].mean()), 4) for c in sim.columns}
    for c in ["blank_share_true_zero", "mean_blank_as_zero", "mean_blank_dropped", "true_zero_next_ge1"]:
        summ[c + "_p10"] = round(float(sim[c].quantile(.1)), 4)
        summ[c + "_p90"] = round(float(sim[c].quantile(.9)), 4)
    summ["bias_blank_as_zero_vs_served_pct"] = round(float((sim.mean_blank_as_zero / sim.mean_true_served - 1).mean() * 100), 1)
    summ["bias_blank_as_zero_served_only_vs_served_pct"] = round(float((sim.mean_blank_as_zero_served_only / sim.mean_true_served - 1).mean() * 100), 1)
    summ["bias_blank_dropped_vs_served_pct"] = round(float((sim.mean_blank_dropped / sim.mean_true_served - 1).mean() * 100), 1)
    summ["bias_blank_as_zero_vs_potential_pct"] = round(float((sim.mean_blank_as_zero / sim.mean_potential_all - 1).mean() * 100), 1)
    summ["bias_blank_dropped_vs_potential_pct"] = round(float((sim.mean_blank_dropped / sim.mean_potential_all - 1).mean() * 100), 1)
    # 式：ポアソン分布で、置いた起きやすさから空白の中身を出す（ある町の lam で）
    res["summary_200_towns"] = summ

    # 式どおりかの確かめ：本当に0件の確率 = 平均 exp(-lam)
    chk = []
    for r in range(REPS):
        lam_r, served_r, _, _ = make_town(np.random.default_rng(SEED * 1000 + r), BASE["mean"], BASE["sigma"], BASE["unserved"])
        p0 = np.exp(-lam_r[served_r]).sum()
        p12 = (np.exp(-lam_r[served_r]) * (lam_r[served_r] + lam_r[served_r] ** 2 / 2)).sum()
        chk.append((p0, p12, (~served_r).sum()))
    chk = np.array(chk)
    res["formula_blank_share_true_zero"] = round(float((chk[:, 0] / chk.sum(1)).mean()), 4)
    res["formula_true_zero_share_served"] = round(float((chk[:, 0] / (G * (G - BASE["unserved"]))).mean()), 4)

    # 3) 確かめ：平均件数 × 出さない線 × 対象外の列（各50の町）
    grid = []
    k = 0
    for mean in [2.0, 4.0, 8.0]:
        for thr in [1, 3, 5]:
            for uns in [0, 3, 6]:
                s = run(SEED * 5000 + k * 100, 50, mean=mean, thr=thr, unserved=uns)
                k += 1
                grid.append({"mean": mean, "thr": thr, "unserved_cols": uns,
                             "blank_zones": round(s.blank_zones.mean(), 1),
                             "blank_share_true_zero": round(s.blank_share_true_zero.mean(), 4),
                             "blank_share_suppressed": round(s.blank_share_suppressed.mean(), 4),
                             "blank_share_unserved": round(s.blank_share_unserved.mean(), 4),
                             "bias_blank_as_zero_pct": round(float((s.mean_blank_as_zero / s.mean_true_served - 1).mean() * 100), 1),
                             "bias_blank_dropped_pct": round(float((s.mean_blank_dropped / s.mean_true_served - 1).mean() * 100), 1),
                             "true_zero_next_ge1": round(float(s.true_zero_next_ge1.mean()), 4)})
    for sg in [0.5, 1.3]:
        s = run(SEED * 7000 + int(sg * 10) * 100, 50, sigma=sg)
        grid.append({"mean": BASE["mean"], "thr": BASE["thr"], "unserved_cols": BASE["unserved"], "sigma": sg,
                     "blank_zones": round(s.blank_zones.mean(), 1),
                     "blank_share_true_zero": round(s.blank_share_true_zero.mean(), 4),
                     "blank_share_suppressed": round(s.blank_share_suppressed.mean(), 4),
                     "blank_share_unserved": round(s.blank_share_unserved.mean(), 4),
                     "bias_blank_as_zero_pct": round(float((s.mean_blank_as_zero / s.mean_true_served - 1).mean() * 100), 1),
                     "bias_blank_dropped_pct": round(float((s.mean_blank_dropped / s.mean_true_served - 1).mean() * 100), 1),
                     "true_zero_next_ge1": round(float(s.true_zero_next_ge1.mean()), 4)})
    grid = pd.DataFrame(grid)
    grid["sigma"] = grid["sigma"].fillna(BASE["sigma"])
    grid.to_csv(RES / "robustness.csv", index=False)
    g = grid[(grid.sigma == BASE["sigma"])]
    gb = g[(g.thr > 1) & (g.unserved_cols > 0)]
    res["robustness"] = {
        "combos": int(len(grid)),
        "blank_share_true_zero_range_thr_gt1_uns_gt0": [float(gb.blank_share_true_zero.min()), float(gb.blank_share_true_zero.max())],
        "blank_share_true_zero_range_all": [float(grid.blank_share_true_zero.min()), float(grid.blank_share_true_zero.max())],
        "bias_blank_as_zero_range_all": [float(grid.bias_blank_as_zero_pct.min()), float(grid.bias_blank_as_zero_pct.max())],
        "bias_blank_dropped_range_all": [float(grid.bias_blank_dropped_pct.min()), float(grid.bias_blank_dropped_pct.max())],
        "true_zero_next_ge1_range_all": [float(grid.true_zero_next_ge1.min()), float(grid.true_zero_next_ge1.max())],
    }

    # 図1：例の町の地図
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.4))
    img = val.reshape(G, G)
    cm = plt.get_cmap("Blues").copy(); cm.set_bad("white")
    im = axes[0].imshow(np.ma.masked_invalid(img), cmap=cm, vmin=0, vmax=np.nanpercentile(img, 97))
    axes[0].set_title(f"地図に出る形（空白 {int((~shown).sum())}区域）", fontsize=12)
    fig.colorbar(im, ax=axes[0], fraction=0.046, pad=0.03).set_label("注文の件数（1か月）")
    code = np.zeros(G * G)
    code[kind == TYPES[0]] = 1; code[kind == TYPES[1]] = 2; code[kind == TYPES[2]] = 3
    cm2 = ListedColormap(["#eeeeee", ORANGE, "#f6c25b", GRAY])
    axes[1].imshow(code.reshape(G, G), cmap=cm2, norm=BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], 4))
    axes[1].set_title("空白の中身", fontsize=12)
    n0, n1, n2 = [int((kind == t).sum()) for t in TYPES]
    axes[1].legend(handles=[Patch(color=ORANGE, label=f"本当に0件（{n0}区域）"),
                            Patch(color="#f6c25b", label=f"1〜2件で出さない（{n1}区域）"),
                            Patch(color=GRAY, label=f"配達の対象外（{n2}区域）"),
                            Patch(color="#eeeeee", label=f"地図に出ている（{int(shown.sum())}区域）")],
                   loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=9, frameon=False)
    for ax in axes:
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("同じ「空白」に、0件・少なくて出さない・データなしがまざる（例の町1つ）", fontsize=13)
    save(fig, "a955_maps.png", SRC + "。20×20の区域。3件未満は空白、東の3列は配達の対象外")

    # 図2：区域あたりの平均件数の読み方
    fig, ax = plt.subplots(figsize=(8.4, 4.9))
    labs = ["空白を0件として\n400区域で割る", "空白を0件として\n配達する区域で割る", "空白を除いて\n地図に出た区域で割る", "本当の値\n（配達する区域の平均）",
            "本当の起きやすさ\n（対象外も入れた400区域）"]
    vals = [summ["mean_blank_as_zero"], summ["mean_blank_as_zero_served_only"], summ["mean_blank_dropped"], summ["mean_true_served"], summ["mean_potential_all"]]
    cols = [ORANGE, ORANGE, ORANGE, BLUE, LIGHT]
    bars = ax.barh(labs[::-1], vals[::-1], color=cols[::-1])
    for b_, v in zip(bars, vals[::-1]):
        ax.text(v + 0.05, b_.get_y() + b_.get_height() / 2, f"{v:.2f}件", va="center", fontsize=10)
    ax.set_xlabel("区域あたりの注文の件数（1か月、200の町の平均）")
    ax.set_xlim(0, max(vals) * 1.2)
    ax.set_title("空白の扱い方で、区域あたりの平均は上にも下にもずれる")
    save(fig, "a955_mean_readings.png", SRC + "。200の町の平均")

    # 図3：空白のうち本当に0件の割合（平均件数 × 出さない線、対象外3列）
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    for thr, c, mk in [(1, BLUE, "o"), (3, ORANGE, "s"), (5, GREEN, "^")]:
        d = g[(g.thr == thr) & (g.unserved_cols == 3)].sort_values("mean")
        ax.plot(d["mean"], d.blank_share_true_zero * 100, marker=mk, color=c,
                label=f"{thr}件未満を出さない" if thr > 1 else "出さない決まりなし")
        for xv, yv in zip(d["mean"], d.blank_share_true_zero * 100):
            ax.text(xv, yv + (2 if thr < 5 else -5), f"{yv:.1f}%", ha="center", fontsize=8.5, color=c)
    ax.set_xscale("log", base=2)
    ax.set_xticks([2, 4, 8]); ax.set_xticklabels(["2件", "4件（基本）", "8件"])
    ax.set_xlabel("区域あたりの本当の平均件数（1か月）")
    ax.set_ylabel("空白の区域のうち、本当に0件だった割合（%）")
    ax.set_ylim(0, 100)
    ax.set_title("空白が「本当に0件」の割合は、件数の多さと出さない線で動く\n（配達の対象外は東の3列、各50の町）", fontsize=12)
    ax.legend(fontsize=9, frameon=False)
    save(fig, "a955_blank_share_robustness.png", SRC + "。各50の町の平均")

    run_sec = round(time.time() - t0, 1)
    with open(RES / "a955_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print("sec", run_sec)


if __name__ == "__main__":
    main()
