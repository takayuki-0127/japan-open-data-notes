"""814 2本の縦軸のグラフで、目盛りの取り方だけで「連動」は作れるのか？（架空のデータ）

架空の2つの数字（店の来店数と、別の商品の売上）を24か月分作る。
無関係に作った組と、月ごとの増減が本当に関係するように作った組を用意し、
2本の縦軸のグラフで、右の縦軸の目盛りの取り方を選ぶと、2本の線がどれだけ重なって見えるかを数える。
重なりの目安：2本の線の縦の離れ（グラフの高さを1とした平均の差）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 814
SRC = "架空の来店数と売上（作成者が乱数で作成、seed 814）"
rng = np.random.default_rng(SEED)
N_PAIR = 2000
T = 24
A_LO, A_HI = 0.05, 0.95          # 左の縦軸：自動（線がグラフの高さの5〜95%に収まる）
GRID = np.round(np.arange(0, 1.0001, 0.02), 2)


def walk(rng, n, t, eps, level):
    drift = rng.normal(0.005, 0.01, n)
    x = np.cumsum(drift[:, None] + eps, axis=1)
    return level[:, None] * np.exp(x)


def make_pairs(rng, kind, n=N_PAIR, t=T, rho=0.8):
    la = np.exp(rng.normal(np.log(1200), 0.3, n))    # 来店数（人）
    lb = np.exp(rng.normal(np.log(300), 0.3, n))     # 売上（万円）
    if kind == "無関係・上り下りあり":
        a = walk(rng, n, t, rng.normal(0, 0.03, (n, t)), la)
        b = walk(rng, n, t, rng.normal(0, 0.03, (n, t)), lb)
    elif kind == "無関係・横ばいの振れ":
        a = la[:, None] * (1 + rng.normal(0, 0.05, (n, t)))
        b = lb[:, None] * (1 + rng.normal(0, 0.05, (n, t)))
    else:  # 本当に関係あり：月ごとの増減の相関が rho
        e1 = rng.normal(0, 1, (n, t)); e2 = rho * e1 + np.sqrt(1 - rho ** 2) * rng.normal(0, 1, (n, t))
        drift = rng.normal(0.005, 0.01, n)
        a = la[:, None] * np.exp(np.cumsum(drift[:, None] + 0.03 * e1, axis=1))
        b = lb[:, None] * np.exp(np.cumsum(drift[:, None] + 0.03 * e2, axis=1))
    return a, b


def norm01(x):
    lo, hi = x.min(1, keepdims=True), x.max(1, keepdims=True)
    return (x - lo) / (hi - lo)


def change_corr(a, b):
    da, db = np.diff(np.log(a), axis=1), np.diff(np.log(b), axis=1)
    da = da - da.mean(1, keepdims=True); db = db - db.mean(1, keepdims=True)
    return (da * db).sum(1) / np.sqrt((da ** 2).sum(1) * (db ** 2).sum(1))


def level_corr(a, b):
    a = a - a.mean(1, keepdims=True); b = b - b.mean(1, keepdims=True)
    return (a * b).sum(1) / np.sqrt((a ** 2).sum(1) * (b ** 2).sum(1))


def gaps(a, b, min_span=0.3, allow_flip=False, return_worst=False):
    """左は自動。右の縦軸は (1) 自動 (2) 線が重なるように選ぶ（線の位置 lo〜hi、幅 min_span 以上）"""
    za = A_LO + (A_HI - A_LO) * norm01(a)
    zb = norm01(b)
    auto = np.abs(za - (A_LO + (A_HI - A_LO) * zb)).mean(1)
    best = np.full(len(a), np.inf); arg = np.zeros((len(a), 2)); worst = np.zeros(len(a))
    pairs = [(lo, hi) for lo in GRID for hi in GRID if hi - lo >= min_span - 1e-9]
    if allow_flip:
        pairs += [(hi, lo) for lo, hi in pairs]
    for lo, hi in pairs:
        g = np.abs(za - (lo + (hi - lo) * zb)).mean(1)
        better = g < best
        best[better] = g[better]; arg[better] = (lo, hi)
        worst = np.maximum(worst, g)
    if return_worst:
        return auto, best, arg, worst
    return auto, best, arg


def main():
    kinds = ["無関係・上り下りあり", "無関係・横ばいの振れ", "本当に関係あり"]
    sims = {}
    for k_i, k in enumerate(kinds):
        a, b = make_pairs(np.random.default_rng(SEED * 10 + k_i), k)
        auto, chosen, arg, apart = gaps(a, b, return_worst=True)
        _, flip, _ = gaps(a, b, allow_flip=True)
        sims[k] = {"a": a, "b": b, "auto": auto, "chosen": chosen, "flip": flip, "arg": arg, "apart": apart,
                   "ccorr": change_corr(a, b), "lcorr": level_corr(a, b)}

    thr = float(np.median(sims["本当に関係あり"]["auto"]))   # 本当に関係のある組の、自動の目盛りでの典型の離れ
    thr_un = float(np.median(sims["無関係・上り下りあり"]["auto"]))  # 無関係の組の、自動の目盛りでの典型の離れ
    rows = []
    for k in kinds:
        s = sims[k]
        rows.append({"kind": k, "change_corr_mean": round(float(s["ccorr"].mean()), 3),
                     "abs_level_corr_gt_0_5": round(float((np.abs(s["lcorr"]) > 0.5).mean()), 3),
                     "gap_auto_median": round(float(np.median(s["auto"])), 3),
                     "gap_chosen_median": round(float(np.median(s["chosen"])), 3),
                     "gap_flip_median": round(float(np.median(s["flip"])), 3),
                     "share_linked_auto": round(float((s["auto"] <= thr).mean()), 3),
                     "share_linked_chosen": round(float((s["chosen"] <= thr).mean()), 3),
                     "share_linked_flip": round(float((s["flip"] <= thr).mean()), 3),
                     "gap_apart_median": round(float(np.median(s["apart"])), 3),
                     "share_apart_ge_unrelated_auto": round(float((s["apart"] >= thr_un).mean()), 3)})
    main_tab = pd.DataFrame(rows)
    main_tab.to_csv(RES / "by_kind.csv", index=False)

    # 1組分のデータ（無関係・上り下りあり の先頭200組）
    s = sims["無関係・上り下りあり"]
    recs = []
    for i in range(200):
        for t in range(T):
            recs.append({"pair_id": i + 1, "month": t + 1, "visitors": round(float(s["a"][i, t])),
                         "sales_manyen": round(float(s["b"][i, t]), 1)})
    pd.DataFrame(recs).to_csv(DATA / "unrelated_pairs.csv", index=False)

    # 確かめ：置き方を変える
    sens = []
    settings = [("基本（24か月・関係の強さ0.8・線の幅30%以上）", 24, 0.8, 0.3),
                ("12か月", 12, 0.8, 0.3), ("60か月", 60, 0.8, 0.3),
                ("関係の強さ0.5で目安を作る", 24, 0.5, 0.3),
                ("右の線の幅を50%以上に限る", 24, 0.8, 0.5)]
    for name, t, rho, span in settings:
        r = np.random.default_rng(SEED * 100 + t + int(rho * 10) + int(span * 10))
        ar, br = make_pairs(r, "本当に関係あり", 1000, t, rho)
        th = float(np.median(gaps(ar, br, span)[0]))
        out_row = {"setting": name, "threshold_gap": round(th, 3)}
        for k, key in [("無関係・上り下りあり", "rw"), ("無関係・横ばいの振れ", "flat")]:
            a2, b2 = make_pairs(r, k, 1000, t)
            au, ch, _ = gaps(a2, b2, span)
            out_row[f"{key}_share_linked_auto"] = round(float((au <= th).mean()), 3)
            out_row[f"{key}_share_linked_chosen"] = round(float((ch <= th).mean()), 3)
        sens.append(out_row)
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    out = {"n_pairs_per_kind": N_PAIR, "months": T, "threshold_gap_related_auto_median": round(thr, 3),
           "unrelated_rw_auto_gap_median": round(thr_un, 3),
           "by_kind": main_tab.to_dict("records"), "sensitivity": sens.to_dict("records")}

    # 図1に使う1組：無関係・上り下りあり で、目盛りを選ぶと目安以下まで重なった組のうち、離れがいちばん縮んだ組
    s = sims["無関係・上り下りあり"]
    ok = np.where(s["chosen"] <= thr)[0]
    i = int(ok[np.argmax(s["auto"][ok] - s["chosen"][ok])])
    a, b = s["a"][i], s["b"][i]
    lo, hi = s["arg"][i]
    out["example_pair"] = {"index": i, "change_corr": round(float(s["ccorr"][i]), 3),
                           "gap_auto": round(float(s["auto"][i]), 3), "gap_chosen": round(float(s["chosen"][i]), 3),
                           "right_line_lo": float(lo), "right_line_hi": float(hi),
                           "level_corr": round(float(s["lcorr"][i]), 3)}
    out["overlapped_unrelated"] = {"count": int(len(ok)), "level_corr_median": round(float(np.median(s["lcorr"][ok])), 3),
                                   "others_level_corr_median": round(float(np.median(np.delete(s["lcorr"], ok))), 3),
                                   "change_corr_mean": round(float(s["ccorr"][ok].mean()), 3)}
    json.dump(out, open(RES / "a814_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：同じ無関係の2本を、右の目盛りだけ変えて
    mo = np.arange(1, T + 1)
    fig, axs = plt.subplots(1, 2, figsize=(9.6, 3.9))
    for ax, mode in zip(axs, ["auto", "chosen"]):
        ax.plot(mo, a, color=BLUE, lw=2)
        ra, rb = a.max() - a.min(), b.max() - b.min()
        ax.set_ylim(a.min() - ra * A_LO / (A_HI - A_LO), a.max() + ra * (1 - A_HI) / (A_HI - A_LO))
        ax.set_ylabel("来店数（人）", color=BLUE); ax.set_xlabel("月")
        ax2 = ax.twinx(); ax2.spines["right"].set_visible(True); ax2.spines["top"].set_visible(False)
        ax2.plot(mo, b, color=ORANGE, lw=2)
        L, H = (A_LO, A_HI) if mode == "auto" else (lo, hi)
        span = rb / (H - L)
        ax2.set_ylim(b.min() - L * span, b.min() + (1 - L) * span)
        ax2.set_ylabel("別の商品の売上（万円）", color=ORANGE)
        ax.set_title("右の縦軸も自動" if mode == "auto" else "右の縦軸の目盛りだけを選んだ", fontsize=11)
    fig.suptitle(f"月ごとの増減は無関係に作った2本（重ねられた組の例）。線の離れ {s['auto'][i]:.2f} → {s['chosen'][i]:.2f}",
                 fontsize=11.5)
    fig.tight_layout()
    save(fig, "a814_pair.png", SRC)

    # 図2：線の離れの分布
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.linspace(0, 0.6, 61)
    ax.hist(sims["本当に関係あり"]["auto"], bins=bins, color=GREEN, alpha=.55, density=True, label="本当に関係あり・右も自動")
    ax.hist(s["auto"], bins=bins, color=GRAY, alpha=.55, density=True, label="無関係（上り下りあり）・右も自動")
    ax.hist(s["chosen"], bins=bins, color=ORANGE, alpha=.55, density=True, label="無関係（上り下りあり）・右の目盛りを選ぶ")
    ax.axvline(thr, color=INK, lw=1, ls="--")
    ax.text(thr + 0.005, ax.get_ylim()[1] * 0.92, f"目安 {thr:.3f}\n（関係ありの組の真ん中）", fontsize=8.5)
    ax.set_xlabel("2本の線の縦の離れ（グラフの高さを1とした平均）"); ax.set_yticks([])
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("右の目盛りを選ぶと離れは縮むが、多くは「関係あり」ほど重ならない")
    save(fig, "a814_gap_hist.png", SRC)

    # 図3：「関係あり並みに重なって見える」割合
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    labs = ["右も自動", "右の目盛りを選ぶ", "選ぶ＋上下を逆にしてもよい"]
    keys = ["share_linked_auto", "share_linked_chosen", "share_linked_flip"]
    x = np.arange(3); w = 0.27
    for j, (k, col) in enumerate(zip(kinds, [GRAY, LIGHT, GREEN])):
        vals = [main_tab.loc[main_tab.kind == k, kk].iloc[0] * 100 for kk in keys]
        ax.bar(x + (j - 1) * w, vals, w, color=col, label=k)
        for xi, v in zip(x + (j - 1) * w, vals):
            ax.text(xi, v + 1.5, f"{v:.0f}%", ha="center", fontsize=8.5)
    ax.set_xticks(x, labs); ax.set_ylim(0, 112); ax.set_ylabel("関係あり並みに重なる組の割合（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=3)
    ax.set_title("目盛りを選んでも、無関係の組で関係あり並みに重なるのは1割前後（各2,000組）")
    save(fig, "a814_share.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
