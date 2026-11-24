"""1237 似た件が続く並べ方で付けると、前の件の判定にどれだけ引っぱられるのか？（架空のデータ）

架空の問い合わせ文2,000件（話題100個×20件）に、1人の付け手が「急ぎ／急ぎでない」を付ける。
件ごとの本当の急ぎの度合い z = 話題の度合い（平均0・標準偏差1）＋話題の中の散らばり（標準偏差 w=0.6）。
本当の分類は z > 1 なら急ぎ。付け手は z に読みの揺れ（標準偏差 s=0.5）を足して読み、1 を超えたら急ぎと付ける。
前の件が同じ話題（似た件）なら、前の判定の向きに λ=0.4 だけ引っぱられる（前が急ぎなら +λ、急ぎでないなら −λ）。
並べ方：① 話題ごとにまとめる ② ばらばら。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1237
SRC = "架空の問い合わせ文と付け手（作成者が乱数で作成、seed 1237）"
NT, PER = 100, 20
N = NT * PER
TH = 1.0
L0, S0, W0 = 0.4, 0.5, 0.6
REP = 200


def simulate(rng, order, lam=L0, s=S0, w=W0, rep=REP):
    topic = np.repeat(np.arange(NT), PER)
    m = rng.normal(0, 1, (rep, NT))
    z = m[:, topic] + rng.normal(0, w, (rep, N))
    e = rng.normal(0, s, (rep, N))
    y = (z > TH).astype(int)
    # 並べ方：各回の並び順（items の番号の列）
    if order == "block":
        perm = np.empty((rep, N), int)
        for r in range(rep):
            tord = rng.permutation(NT)
            perm[r] = np.concatenate([t * PER + rng.permutation(PER) for t in tord])
    else:
        perm = np.array([rng.permutation(N) for _ in range(rep)])
    rows = np.arange(rep)[:, None]
    zt, et, yt, tt = z[rows, perm], e[rows, perm], y[rows, perm], topic[perm]
    lab = np.zeros((rep, N), int)
    shift = np.zeros((rep, N))
    for t in range(N):
        if t > 0:
            same = tt[:, t] == tt[:, t - 1]
            shift[:, t] = np.where(same, np.where(lab[:, t - 1] == 1, lam, -lam), 0.0)
        lab[:, t] = (zt[:, t] + et[:, t] + shift[:, t] > TH).astype(int)
    nopull = (zt + et > TH).astype(int)      # 引っぱりがなかったときの判定（同じ読みの揺れ）
    return dict(z=zt, y=yt, lab=lab, nopull=nopull, topic=tt, shift=shift)


def measures(d):
    y, lab, nopull, tt, z = d["y"], d["lab"], d["nopull"], d["topic"], d["z"]
    rep = y.shape[0]
    out = {}
    out["error_pct"] = (lab != y).mean() * 100
    out["error_nopull_pct"] = (nopull != y).mean() * 100
    out["pull_error_change_pt"] = out["error_pct"] - out["error_nopull_pct"]
    out["flipped_pct"] = (lab != nopull).mean() * 100
    near = np.abs(z - TH) < 0.3
    out["flipped_near_pct"] = (lab != nopull)[near].mean() * 100
    out["label_rate_pct"] = lab.mean() * 100
    out["label_rate_nopull_pct"] = nopull.mean() * 100
    out["true_rate_pct"] = y.mean() * 100
    same = np.zeros_like(lab, bool); same[:, 1:] = tt[:, 1:] == tt[:, :-1]
    agree = np.zeros_like(lab, bool); agree[:, 1:] = lab[:, 1:] == lab[:, :-1]
    out["share_prev_same_topic_pct"] = same[:, 1:].mean() * 100
    out["same_as_prev_pct"] = agree[:, 1:].mean() * 100
    tagree = np.zeros_like(lab, bool); tagree[:, 1:] = y[:, 1:] == y[:, :-1]
    out["true_same_as_prev_pct"] = tagree[:, 1:].mean() * 100
    # 話題ごとの急ぎの割合のずれ
    rows = np.arange(rep)[:, None]
    lab_t = np.zeros((rep, NT)); y_t = np.zeros((rep, NT)); np_t = np.zeros((rep, NT))
    for k in range(NT):
        msk = tt == k
        lab_t[:, k] = (lab * msk).sum(1) / PER
        y_t[:, k] = (y * msk).sum(1) / PER
        np_t[:, k] = (nopull * msk).sum(1) / PER
    out["topic_abs_err_pt"] = np.abs(lab_t - y_t).mean() * 100
    out["topic_abs_err_nopull_pt"] = np.abs(np_t - y_t).mean() * 100
    out["topic_off_10pt_pct"] = (np.abs(lab_t - y_t) >= 0.1 + 1e-9).mean() * 100
    out["topic_off_10pt_nopull_pct"] = (np.abs(np_t - y_t) >= 0.1 + 1e-9).mean() * 100
    # 判定の上で「前が急ぎ」のあとに急ぎと付く割合（同じ話題が続いたところだけ）
    prev_u = np.zeros_like(lab, bool); prev_u[:, 1:] = lab[:, :-1] == 1
    prev_n = np.zeros_like(lab, bool); prev_n[:, 1:] = lab[:, :-1] == 0
    out["p_urgent_after_urgent_same_pct"] = lab[same & prev_u].mean() * 100 if (same & prev_u).any() else np.nan
    out["p_urgent_after_not_same_pct"] = lab[same & prev_n].mean() * 100 if (same & prev_n).any() else np.nan
    out["after_gap_pt"] = out["p_urgent_after_urgent_same_pct"] - out["p_urgent_after_not_same_pct"]
    return out


def r4(d):
    return {k: (round(float(v), 2) if not isinstance(v, str) else v) for k, v in d.items()}


def main():
    t0 = time.time()
    res = {}
    keep = {}
    for i, (o, lam) in enumerate([("block", L0), ("shuffle", L0), ("block", 0.0), ("shuffle", 0.0)]):
        d = simulate(np.random.default_rng(SEED * 10 + i % 2), o, lam=lam)
        key = f"{o}_lam{lam:g}"
        res[key] = r4(measures(d))
        keep[key] = d
    tab = pd.DataFrame([{"setting": k, **v} for k, v in res.items()])
    tab.to_csv(RES / "orders.csv", index=False)

    # 1回分のデータ（① まとめる、λ=0.4）
    d = keep["block_lam0.4"]
    ex = pd.DataFrame({"position": np.arange(1, N + 1), "topic": d["topic"][0] + 1, "true_urgency": d["z"][0].round(4),
                       "true_urgent": d["y"][0], "label_urgent": d["lab"][0], "label_without_pull": d["nopull"][0]})
    ex.to_csv(DATA / "labels_one_run_block.csv", index=False)
    ex_sum = {"error_pct": round(float((ex.label_urgent != ex.true_urgent).mean()) * 100, 2),
              "flipped": int((ex.label_urgent != ex.label_without_pull).sum())}

    # 本当の度合いごとの「急ぎ」と付いた割合（前の件の判定で分ける、① まとめる）
    z, lab, tt = d["z"], d["lab"], d["topic"]
    same = np.zeros_like(lab, bool); same[:, 1:] = tt[:, 1:] == tt[:, :-1]
    pu = np.zeros_like(lab, bool); pu[:, 1:] = lab[:, :-1] == 1
    bins = np.arange(0.0, 2.01, 0.2)
    crow = []
    for a, b in zip(bins[:-1], bins[1:]):
        inb = (z >= a) & (z < b) & same
        crow.append({"z_from": round(a, 1), "z_to": round(b, 1),
                     "after_urgent_pct": round(float(lab[inb & pu].mean()) * 100, 2),
                     "after_not_pct": round(float(lab[inb & ~pu].mean()) * 100, 2),
                     "n_after_urgent": int((inb & pu).sum()), "n_after_not": int((inb & ~pu).sum())})
    d0 = keep["block_lam0"]
    z0, lab0, tt0 = d0["z"], d0["lab"], d0["topic"]
    same0 = np.zeros_like(lab0, bool); same0[:, 1:] = tt0[:, 1:] == tt0[:, :-1]
    pu0 = np.zeros_like(lab0, bool); pu0[:, 1:] = lab0[:, :-1] == 1
    for c, (a, b) in zip(crow, zip(bins[:-1], bins[1:])):
        inb = (z0 >= a) & (z0 < b) & same0
        c["nopull_after_urgent_pct"] = round(float(lab0[inb & pu0].mean()) * 100, 2)
        c["nopull_after_not_pct"] = round(float(lab0[inb & ~pu0].mean()) * 100, 2)
    curve = pd.DataFrame(crow)
    curve.to_csv(RES / "by_true_urgency.csv", index=False)

    # 確かめ：λ × 読みの揺れ s × 話題の中の散らばり w（27通り、各20回）
    g = []
    j = 0
    for lam in [0.2, 0.4, 0.8]:
        for s in [0.3, 0.5, 0.8]:
            for w in [0.3, 0.6, 1.0]:
                j += 1
                row = {"pull": lam, "read_sd": s, "within_topic_sd": w}
                for i, o in enumerate(["block", "shuffle"]):
                    mm = measures(simulate(np.random.default_rng(SEED * 1000 + j * 10 + i), o, lam, s, w, rep=20))
                    row[f"{o}_error_pct"] = round(float(mm["error_pct"]), 2)
                    row[f"{o}_error_nopull_pct"] = round(float(mm["error_nopull_pct"]), 2)
                    row[f"{o}_flipped_pct"] = round(float(mm["flipped_pct"]), 2)
                    row[f"{o}_topic_abs_err_pt"] = round(float(mm["topic_abs_err_pt"]), 2)
                    row[f"{o}_topic_abs_err_nopull_pt"] = round(float(mm["topic_abs_err_nopull_pt"]), 2)
                    row[f"{o}_label_rate_pct"] = round(float(mm["label_rate_pct"]), 2)
                    row[f"{o}_label_rate_nopull_pct"] = round(float(mm["label_rate_nopull_pct"]), 2)
                    row[f"{o}_true_rate_pct"] = round(float(mm["true_rate_pct"]), 2)
                row["error_gap_pt"] = round(row["block_error_pct"] - row["shuffle_error_pct"], 2)
                row["block_pull_error_change_pt"] = round(row["block_error_pct"] - row["block_error_nopull_pct"], 2)
                g.append(row)
    grid = pd.DataFrame(g)
    grid.to_csv(RES / "grid.csv", index=False)
    robust = {
        "settings": len(grid),
        "error_gap_min": float(grid.error_gap_pt.min()), "error_gap_max": float(grid.error_gap_pt.max()),
        "error_gap_positive_count": int((grid.error_gap_pt > 0).sum()),
        "block_flipped_min": float(grid.block_flipped_pct.min()), "block_flipped_max": float(grid.block_flipped_pct.max()),
        "shuffle_flipped_max": float(grid.shuffle_flipped_pct.max()),
        "block_topic_err_min": float(grid.block_topic_abs_err_pt.min()), "block_topic_err_max": float(grid.block_topic_abs_err_pt.max()),
        "topic_err_increase_min": round(float((grid.block_topic_abs_err_pt - grid.block_topic_abs_err_nopull_pt).min()), 2),
        "pull_error_change_min": float(grid.block_pull_error_change_pt.min()),
        "pull_error_change_max": float(grid.block_pull_error_change_pt.max()),
        "pull_error_up_count": int((grid.block_pull_error_change_pt > 0).sum()),
        "pull_error_up_count_by_read_sd": {f"{v:g}": int(((grid.read_sd == v) & (grid.block_pull_error_change_pt > 0)).sum())
                                           for v in [0.3, 0.5, 0.8]},
        "pull_error_up_count_by_within_sd": {f"{v:g}": int(((grid.within_topic_sd == v) & (grid.block_pull_error_change_pt > 0)).sum())
                                             for v in [0.3, 0.6, 1.0]},
        "pull_rate_down_count": int((grid.block_label_rate_pct < grid.block_label_rate_nopull_pct).sum()),
        "pull_rate_change_min": round(float((grid.block_label_rate_pct - grid.block_label_rate_nopull_pct).min()), 2),
        "pull_rate_change_max": round(float((grid.block_label_rate_pct - grid.block_label_rate_nopull_pct).max()), 2),
        "topic_err_up_count": int((grid.block_topic_abs_err_pt > grid.block_topic_abs_err_nopull_pt).sum()),
        "topic_err_increase_max": round(float((grid.block_topic_abs_err_pt - grid.block_topic_abs_err_nopull_pt).max()), 2),
    }
    json.dump({"orders": res, "example_one_run_block": ex_sum, "robust": robust,
               "setup": {"topics": NT, "per_topic": PER, "threshold": TH, "pull": L0, "read_sd": S0,
                         "within_topic_sd": W0, "topic_sd": 1.0, "near_band": [round(TH - 0.3, 1), round(TH + 0.3, 1)], "reps": REP}},
              open(RES / "a1237_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：前の件の判定で、同じ度合いの件の付き方が変わる
    fig, ax = plt.subplots(figsize=(7, 3.9))
    xm = (curve.z_from + curve.z_to) / 2
    ax.plot(xm, curve.after_urgent_pct, marker="o", color=ORANGE, label="前の件（同じ話題）を「急ぎ」と付けたあと")
    ax.plot(xm, curve.after_not_pct, marker="s", color=BLUE, label="前の件（同じ話題）を「急ぎでない」と付けたあと")
    ax.plot(xm, curve.nopull_after_urgent_pct, color=ORANGE, lw=1, ls=":", label="（参考）引っぱりなし・前が急ぎ")
    ax.plot(xm, curve.nopull_after_not_pct, color=BLUE, lw=1, ls=":", label="（参考）引っぱりなし・前が急ぎでない")
    ax.axvline(TH, color=GRAY, lw=1, ls="--")
    ax.text(TH + 0.02, 3, "本当の境目（1）", color=GRAY, fontsize=8.5)
    ax.set_ylim(0, 100); ax.set_xlim(0, 2)
    ax.set_xlabel("件の本当の急ぎの度合い（0.2ずつ）"); ax.set_ylabel("「急ぎ」と付いた割合（%）")
    ax.set_title("同じ度合いの件でも、前の判定で付き方が変わる（① まとめる、λ=0.4）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)
    save(fig, "a1237_curve.png", SRC, y=-0.24)

    # 図2：並べ方と引っぱりの有無ごとの、まちがいの割合と話題ごとのずれ
    fig, axs = plt.subplots(1, 2, figsize=(10, 3.9))
    keys = ["block_lam0.4", "shuffle_lam0.4", "block_lam0", "shuffle_lam0"]
    names = ["① まとめる\n引っぱり0.4", "② ばらばら\n引っぱり0.4", "① まとめる\n引っぱりなし", "② ばらばら\n引っぱりなし"]
    cols = [ORANGE, BLUE, LIGHT, LIGHT]
    for ax, col, ttl in [(axs[0], "error_pct", "まちがって付いた件の割合（%）"),
                         (axs[1], "topic_abs_err_pt", "話題ごとの急ぎの割合のずれ（平均、ポイント）")]:
        vals = [res[k][col] for k in keys]
        ax.bar(range(4), vals, color=cols)
        for i, v in enumerate(vals):
            ax.text(i, v + max(vals) * 0.02, f"{v:.2f}", ha="center", fontsize=9)
        ax.set_xticks(range(4), names, fontsize=8.5); ax.set_ylim(0, max(vals) * 1.2); ax.set_title(ttl, fontsize=11)
    fig.suptitle("基本の置き方では、① で引っぱられても、まちがいと話題ごとのずれは少し減った（200回の平均）", y=1.02)
    save(fig, "a1237_orders.png", SRC, y=-0.04)

    # 図3：27通り
    fig, axs = plt.subplots(2, 1, figsize=(8, 6.4), sharex=True)
    xs = np.arange(len(grid))
    axs[0].bar(xs, grid.block_flipped_pct, color=BLUE)
    axs[0].set_ylim(0, None); axs[0].set_ylabel("%")
    axs[0].set_title("① まとめる：前の判定に引っぱられて判定が変わった件の割合（各20回）", fontsize=11)
    axs[1].bar(xs, grid.block_pull_error_change_pt, color=[ORANGE if v > 0 else GREEN for v in grid.block_pull_error_change_pt])
    axs[1].axhline(0, color=INK, lw=0.8)
    axs[1].set_ylabel("ポイント")
    axs[1].set_title("① まとめる：引っぱりで変わった、まちがって付いた件の割合（＋は増えた）", fontsize=11)
    axs[1].set_xticks(xs, [f"{l:g}/{s:g}/{w:g}" for l, s, w in zip(grid.pull, grid.read_sd, grid.within_topic_sd)],
                      rotation=90, fontsize=7)
    axs[1].set_xlabel("引っぱりの強さ λ／読みの揺れ s／話題の中の散らばり w")
    save(fig, "a1237_grid.png", SRC, y=-0.08)
    print(json.dumps(res, ensure_ascii=False), json.dumps(robust), ex_sum, f"{time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
