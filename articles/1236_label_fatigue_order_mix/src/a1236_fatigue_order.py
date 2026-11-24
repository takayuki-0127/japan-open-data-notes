"""1236 付け手が疲れて後半ほど判定がゆるむと、付けた順番で何がまざるのか？（架空のデータ）

架空の工場の製品の写真に見立てた件（製品A・B・C）に、1人の付け手が「傷あり／傷なし」を付ける。
1日に300件（各製品100件）を18日。件ごとの見え方 x = 3×（本当に傷あり）＋揺れ（標準偏差1）。
付け手は x が基準 c を超えたら「傷あり」と付ける。基準は1日の中で付けた件数とともに上がる
（c = 1.5 + δ×（その日に付けた件数÷300）、基本 δ=0.8）。後半ほど「傷なし」で通しやすくなる。
並べ方：① 毎日 A→B→C の順にまとめて付ける ② 毎日ばらばら ③ 日ごとに A→B→C・B→C→A・C→A→B と回す。
"""
import json
import time
from math import erf, sqrt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1236
SRC = "架空の製品の写真に見立てた件と付け手（作成者が乱数で作成、seed 1236）"
MU, C0, D0 = 3.0, 1.5, 0.8
DAYS, N0, P0 = 18, 300, 0.10
TYPES = ["A", "B", "C"]
ORDERS = {"block": "① 毎日 A→B→C にまとめる", "shuffle": "② 毎日ばらばら", "rotate": "③ 日ごとに順を回す"}
REP = 200


def Phi(z):
    return 0.5 * (1 + erf(z / sqrt(2)))


def type_matrix(rng, order, n):
    m = n // 3
    base = np.repeat(np.arange(3), m)
    if order == "block":
        return np.tile(base, (DAYS, 1))
    if order == "shuffle":
        return np.array([rng.permutation(base) for _ in range(DAYS)])
    rows = []
    for d in range(DAYS):
        seq = [(d + k) % 3 for k in range(3)]
        rows.append(np.repeat(seq, m))
    return np.array(rows)


def one_run(rng, order, p=(P0, P0, P0), delta=D0, n=N0):
    T = type_matrix(rng, order, n)
    pr = np.asarray(p)[T]
    y = (rng.random(T.shape) < pr).astype(int)
    x = MU * y + rng.normal(0, 1, T.shape)
    pos = np.tile(np.arange(n), (DAYS, 1))
    c = C0 + delta * pos / 300.0
    lab = (x > c).astype(int)
    return T, y, lab, pos


def summ(T, y, lab, pos, n):
    out = {}
    for k, t in enumerate(TYPES):
        msk = T == k
        out[f"label_{t}"] = lab[msk].mean()
        out[f"true_{t}"] = y[msk].mean()
    out["label_all"] = lab.mean(); out["true_all"] = y.mean()
    out["error"] = (lab != y).mean()
    out["miss"] = (lab[y == 1] == 0).mean(); out["over"] = (lab[y == 0] == 1).mean()
    h = pos < n // 2
    out["label_first_half"] = lab[h].mean(); out["label_second_half"] = lab[~h].mean()
    out["true_first_half"] = y[h].mean(); out["true_second_half"] = y[~h].mean()
    return out


def formula_rate(p, c):
    return p * (1 - Phi(c - MU)) + (1 - p) * (1 - Phi(c))


def runs(seed, order, p=(P0, P0, P0), delta=D0, n=N0, rep=REP):
    rng = np.random.default_rng(seed)
    return pd.DataFrame([summ(*one_run(rng, order, p, delta, n), n) for _ in range(rep)])


def main():
    t0 = time.time()
    # 1回分のデータ（① の並べ方）
    rng = np.random.default_rng(SEED)
    T, y, lab, pos = one_run(rng, "block")
    day = np.repeat(np.arange(1, DAYS + 1), N0)
    ex = pd.DataFrame({"day": day, "position_in_day": pos.ravel() + 1, "product": np.array(TYPES)[T.ravel()],
                       "true_scratch": y.ravel(), "label_scratch": lab.ravel()})
    ex.to_csv(DATA / "labels_one_run_block.csv", index=False)
    ex_sum = {t: round(float(ex[ex["product"] == t].label_scratch.mean()) * 100, 2) for t in TYPES}
    ex_sum.update({f"true_{t}": round(float(ex[ex["product"] == t].true_scratch.mean()) * 100, 2) for t in TYPES})

    # 基本：3つの並べ方（本当の傷ありはどの製品も10%）
    head = {}
    rows = []
    for i, (o, name) in enumerate(ORDERS.items()):
        r = runs(SEED * 10 + i, o)
        m = r.mean()
        d = {"order": o, "order_name": name}
        for col in ["label_A", "label_B", "label_C", "label_all", "true_all", "error", "miss", "over",
                    "label_first_half", "label_second_half"]:
            d[col + "_pct"] = round(float(m[col]) * 100, 2)
        d["C_minus_A_pt"] = round(float((r.label_C - r.label_A).mean()) * 100, 2)
        d["C_minus_A_p10_pt"] = round(float(np.percentile(r.label_C - r.label_A, 10)) * 100, 2)
        d["C_minus_A_p90_pt"] = round(float(np.percentile(r.label_C - r.label_A, 90)) * 100, 2)
        d["share_C_below_A_pct"] = round(float((r.label_C < r.label_A).mean()) * 100, 2)
        rows.append(d)
        head[o] = d
    base = pd.DataFrame(rows)
    base.to_csv(RES / "orders_equal_true.csv", index=False)

    # 式どおりの値（①の並べ方の製品ごとの付いた割合）
    cs = C0 + D0 * np.arange(N0) / 300.0
    fr = np.array([formula_rate(P0, c) for c in cs])
    formula = {"block_" + t: round(float(fr[k * 100:(k + 1) * 100].mean()) * 100, 2) for k, t in enumerate(TYPES)}
    formula["all"] = round(float(fr.mean()) * 100, 2)
    formula["start_rate"] = round(float(fr[0]) * 100, 2); formula["end_rate"] = round(float(fr[-1]) * 100, 2)
    formula["miss_start"] = round((Phi(C0 - MU)) * 100, 2)
    formula["miss_end"] = round((Phi(cs[-1] - MU)) * 100, 2)
    formula["over_start"] = round((1 - Phi(C0)) * 100, 2)
    formula["over_end"] = round((1 - Phi(cs[-1])) * 100, 2)
    formula["no_fatigue_rate"] = round(formula_rate(P0, C0) * 100, 2)

    # 位置ごとの付いた割合（② ばらばら、30件ずつ）
    rng = np.random.default_rng(SEED * 10 + 7)
    acc = np.zeros(N0); cnt = 0
    for _ in range(REP):
        T, y, lab, pos = one_run(rng, "shuffle")
        acc += lab.mean(axis=0); cnt += 1
    curve = acc / cnt
    pos_df = pd.DataFrame({"position_from": np.arange(1, N0 + 1, 30), "position_to": np.arange(30, N0 + 1, 30),
                           "label_pct": [round(float(curve[i:i + 30].mean()) * 100, 2) for i in range(0, N0, 30)],
                           "formula_pct": [round(float(fr[i:i + 30].mean()) * 100, 2) for i in range(0, N0, 30)]})
    pos_df.to_csv(RES / "by_position.csv", index=False)

    # 本当にCに傷が多い（A 8%・B 10%・C 12%）とき
    diff_rows = []
    for i, (o, name) in enumerate(ORDERS.items()):
        r = runs(SEED * 10 + 20 + i, o, p=(0.08, 0.10, 0.12))
        diff_rows.append({"order": o, "order_name": name,
                          "label_A_pct": round(float(r.label_A.mean()) * 100, 2),
                          "label_B_pct": round(float(r.label_B.mean()) * 100, 2),
                          "label_C_pct": round(float(r.label_C.mean()) * 100, 2),
                          "C_minus_A_pt": round(float((r.label_C - r.label_A).mean()) * 100, 2),
                          "true_C_minus_A_pt": round(float((r.true_C - r.true_A).mean()) * 100, 2),
                          "share_C_below_A_pct": round(float((r.label_C < r.label_A).mean()) * 100, 2)})
    tdiff = pd.DataFrame(diff_rows)
    tdiff.to_csv(RES / "orders_true_diff.csv", index=False)

    # 確かめ：δ × 本当の傷ありの割合 × 1日の件数（27通り、各50回）
    g = []
    j = 0
    for delta in [0.4, 0.8, 1.2]:
        for p in [0.05, 0.10, 0.20]:
            for n in [150, 300, 600]:
                j += 1
                row = {"delta": delta, "true_rate": p, "per_day": n}
                for i, o in enumerate(ORDERS):
                    r = runs(SEED * 1000 + j * 10 + i, o, p=(p, p, p), delta=delta, n=n, rep=50)
                    row[f"{o}_C_minus_A_pt"] = round(float((r.label_C - r.label_A).mean()) * 100, 2)
                    row[f"{o}_label_all_pct"] = round(float(r.label_all.mean()) * 100, 2)
                row["true_pct"] = round(p * 100, 2)
                cs2 = C0 + delta * np.arange(n) / 300.0
                fr2 = np.array([formula_rate(p, c) for c in cs2])
                m = n // 3
                row["formula_block_C_minus_A_pt"] = round(float(fr2[2 * m:].mean() - fr2[:m].mean()) * 100, 2)
                row["formula_all_pct"] = round(float(fr2.mean()) * 100, 2)
                g.append(row)
    grid = pd.DataFrame(g)
    grid.to_csv(RES / "grid.csv", index=False)
    robust = {
        "settings": len(grid),
        "block_C_minus_A_min": float(grid.block_C_minus_A_pt.min()), "block_C_minus_A_max": float(grid.block_C_minus_A_pt.max()),
        "block_negative_count": int((grid.block_C_minus_A_pt < 0).sum()),
        "shuffle_abs_max": float(grid.shuffle_C_minus_A_pt.abs().max()),
        "rotate_abs_max": float(grid.rotate_C_minus_A_pt.abs().max()),
        "block_vs_formula_absdiff_max": round(float((grid.block_C_minus_A_pt - grid.formula_block_C_minus_A_pt).abs().max()), 2),
        "label_all_minus_true_min": round(float((grid.shuffle_label_all_pct - grid.true_pct).min()), 2),
        "label_all_minus_true_max": round(float((grid.shuffle_label_all_pct - grid.true_pct).max()), 2),
        "order_label_all_spread_max": round(float(grid[[f"{o}_label_all_pct" for o in ORDERS]].max(axis=1)
                                                  .sub(grid[[f"{o}_label_all_pct" for o in ORDERS]].min(axis=1)).max()), 2),
    }
    json.dump({"headline": head, "formula": formula, "true_diff": diff_rows, "example_one_run_block": ex_sum,
               "robust": robust,
               "setup": {"days": DAYS, "per_day": N0, "true_rate": P0, "signal": MU, "start_threshold": C0,
                         "threshold_rise_per_300": D0, "end_threshold": round(C0 + D0 * (N0 - 1) / 300.0, 4), "end_threshold_at_300": round(C0 + D0, 2), "reps": REP}},
              open(RES / "a1236_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：1日の中の位置と付いた割合（② ばらばら）
    fig, ax = plt.subplots(figsize=(7, 3.8))
    xm = (pos_df.position_from + pos_df.position_to) / 2
    ax.plot(xm, pos_df.label_pct, marker="o", color=BLUE, label="「傷あり」と付いた割合（② ばらばら、200回の平均）")
    ax.plot(np.arange(1, N0 + 1), fr * 100, color=GRAY, lw=1, ls="--", label="置いた基準からの式")
    ax.axhline(P0 * 100, color=ORANGE, lw=1.2, label="本当に傷ありの割合（10%）")
    for xi, v in zip(xm, pos_df.label_pct):
        ax.text(xi, v + 0.5, f"{v:.2f}", ha="center", fontsize=7.5)
    ax.set_ylim(0, 18); ax.set_xlabel("その日に付けた順番（件目、30件ずつ）"); ax.set_ylabel("%")
    ax.set_title("1日の後半ほど「傷あり」と付く割合が下がる（基準を上げると置いた）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    save(fig, "a1236_position.png", SRC)

    # 図2：並べ方ごとの製品別の付いた割合
    fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, df, ttl, tr in [(axs[0], base, "本当はどの製品も10%", [10, 10, 10]),
                            (axs[1], tdiff, "本当は A 8%・B 10%・C 12%", [8, 10, 12])]:
        w = 0.25
        for k, (t, c) in enumerate(zip(TYPES, [LIGHT, BLUE, ORANGE])):
            vals = df[f"label_{t}_pct"].values
            xs = np.arange(3) + (k - 1) * w
            ax.bar(xs, vals, w, color=c, label=f"製品{t}（本当は{tr[k]}%）")
            for xx, v in zip(xs, vals):
                ax.text(xx, v + 0.2, f"{v:.2f}", ha="center", fontsize=7)
        ax.set_xticks(np.arange(3), ["① 毎日 A→B→C\nにまとめる", "② 毎日\nばらばら", "③ 日ごとに\n順を回す"], fontsize=8.5)
        ax.set_ylim(0, 18); ax.set_title(ttl, fontsize=11)
        ax.legend(frameon=False, fontsize=8, loc="upper right")
    axs[0].set_ylabel("「傷あり」と付いた割合（%、200回の平均）")
    fig.suptitle("① まとめて同じ順に付けると、後に付けた製品Cに傷が少なく見える", y=1.02)
    save(fig, "a1236_types.png", SRC, y=-0.04)

    # 図3：27通りの C−A
    fig, ax = plt.subplots(figsize=(8, 4))
    xs = np.arange(len(grid))
    ax.bar(xs - 0.27, grid.block_C_minus_A_pt, 0.27, color=ORANGE, label=ORDERS["block"])
    ax.bar(xs, grid.shuffle_C_minus_A_pt, 0.27, color=BLUE, label=ORDERS["shuffle"])
    ax.bar(xs + 0.27, grid.rotate_C_minus_A_pt, 0.27, color=GREEN, label=ORDERS["rotate"])
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(xs, [f"{d:g}/{int(p*100)}%/{n}" for d, p, n in zip(grid.delta, grid.true_rate, grid.per_day)],
                  rotation=90, fontsize=7)
    ax.set_xlabel("基準の上がり方 δ／本当に傷ありの割合／1日の件数")
    ax.set_ylabel("製品C − 製品A（ポイント）")
    ax.set_title("本当の差は0。① は27通りすべてで C を低く見せた（②・③は±0.55以内）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    save(fig, "a1236_grid.png", SRC, y=-0.25)
    print(json.dumps(head, ensure_ascii=False), json.dumps(formula), json.dumps(robust), f"{time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
