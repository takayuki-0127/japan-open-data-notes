"""1208 送ってから何日目で開封率を締めるかで、遅く開く人の多い配信はどれだけ低く出るのか？（架空のデータ）

作成者が置いた架空の店の会員向けメール。読者20,000人を3つの型に分ける（基本）：
  すぐ見る人 50%（毎日7〜23時に見る）、平日の昼に見る人 30%（月〜金の9〜18時）、週末にまとめて見る人 20%（土日の9〜22時）。
見られる時間の1時間ごとに、まだ開いていないメールを開く見込み（すぐ0.5、平日0.25、週末0.2）を置く（いずれ開く人だけ）。
いずれ開く確率（型ごと）は配信ごとに置く：
  A「平日の案内」 すぐ0.30・平日0.30・週末0.10 → 本当の開封率 26%
  B「週末の催しの案内」 すぐ0.28・平日0.15・週末0.55 → 本当の開封率 29.5%
基本：A も B も火曜10時に送る（違いは読者の顔ぶれだけ）。
本当の開封率＝いずれ開く人の割合（作成者が置いた値）。締めた開封率＝送ってから k 日（24×k 時間）までに開いた人の割合。
(1) 基本の2通を200回。締めの日数 1・2・3・4・5・7・14・30日
(2) 送る時刻と中身を入れかえた2×2（A・B の中身 × 火曜10時・金曜18時）で、遅さが送る時刻と読者の顔ぶれのどちらから来るかを分ける
(3) 確かめ：週末に見る人の割合3通り×開く速さ3通り（見込みを0.5・1・2倍）×B を送る時刻8通り（月〜日の10時と金曜18時）＝72通り（各20回）
式：締めた開封率÷本当の開封率＝Σ（型の割合×開く確率×(1−e^(−見込み×k 日までに見られる時間))）÷Σ（型の割合×開く確率）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1208
SRC = "架空の店の会員向けメール（作成者が置いた読者の型・見る時間・開く確率からの乱数、seed 1208）"
N = 20000
TYPES = ["すぐ見る人", "平日の昼に見る人", "週末にまとめて見る人"]
SHARE = np.array([0.5, 0.3, 0.2])
RATE = np.array([0.5, 0.25, 0.2])
P = {"A": np.array([0.30, 0.30, 0.10]), "B": np.array([0.28, 0.15, 0.55])}
DAYNAME = ["月", "火", "水", "木", "金", "土", "日"]
SEND = {"火曜10時": 1 * 24 + 10, "金曜18時": 4 * 24 + 18}
KS = [1, 2, 3, 4, 5, 7, 14, 30]
H = 24 * 7 * 12      # 12週分の時間
R_MAIN, R_GRID = 200, 20
T0 = time.time()


def r(x, d=4):
    return round(float(x), d)


def avail_matrix():
    h = np.arange(H)
    dow, hod = (h // 24) % 7, h % 24
    a = np.zeros((3, H), bool)
    a[0] = (hod >= 7) & (hod < 23)
    a[1] = (dow <= 4) & (hod >= 9) & (hod < 18)
    a[2] = (dow >= 5) & (hod >= 9) & (hod < 22)
    cum = np.zeros((3, H + 1))
    cum[:, 1:] = np.cumsum(a, axis=1)
    return a, cum


AV, CUM = avail_matrix()


def avail_hours(t, send, k):
    return CUM[t, send + 24 * k] - CUM[t, send]


def formula_ratio(p, share, rate, send, k):
    w = share * p
    f = np.array([1 - np.exp(-rate[t] * avail_hours(t, send, k)) for t in range(3)])
    return float((w * f).sum() / w.sum())


def one_mail(rng, p, send, share=SHARE, rate=RATE, keep=False):
    typ = rng.choice(3, size=N, p=share)
    will = rng.random(N) < p[typ]
    need = rng.exponential(1.0, N) / rate[typ]           # 開くまでに要る「見られる時間」
    target = CUM[typ, send] + need
    open_h = np.full(N, np.inf)
    for t in range(3):
        m = will & (typ == t)
        idx = np.searchsorted(CUM[t], target[m], side="left")   # 見られる時間の合計が need に届いた時刻
        oh = idx.astype(float) - send
        oh[idx > H] = np.inf
        open_h[m] = oh
    res = {"true": will.mean()}
    for k in KS:
        res[f"closed_{k}"] = (open_h <= 24 * k).mean()
    if keep:
        res["table"] = pd.DataFrame({"reader_id": np.arange(1, N + 1), "type": np.array(TYPES)[typ],
                                     "will_open": will.astype(int),
                                     "hours_to_open": np.where(np.isfinite(open_h), np.round(open_h, 0), -1).astype(int)})
    return res


def main():
    rng = np.random.default_rng(SEED)
    ex = one_mail(np.random.default_rng(SEED + 1), P["B"], SEND["火曜10時"], keep=True)
    ex["table"].to_csv(DATA / "readers_mail_b_example.csv", index=False)
    ex_s = {k: r(v) for k, v in ex.items() if k != "table"}

    # (1)(2) 中身 × 送る時刻
    rows = []
    for mail in ["A", "B"]:
        for sname, s in SEND.items():
            xs = pd.DataFrame([one_mail(rng, P[mail], s) for _ in range(R_MAIN)])
            for k in KS:
                rows.append({"mail": mail, "send": sname, "close_day": k, "true": r(xs.true.mean()),
                             "closed": r(xs[f"closed_{k}"].mean()),
                             "closed_p10": r(xs[f"closed_{k}"].quantile(0.1)), "closed_p90": r(xs[f"closed_{k}"].quantile(0.9)),
                             "ratio": r(xs[f"closed_{k}"].mean() / xs.true.mean()),
                             "formula_ratio": r(formula_ratio(P[mail], SHARE, RATE, s, k)),
                             "true_set": r((SHARE * P[mail]).sum())})
    cell = pd.DataFrame(rows)
    cell.to_csv(RES / "by_mail_send_close.csv", index=False)

    # 基本の2通（A・B とも火曜10時）
    a = cell[(cell.mail == "A") & (cell.send == "火曜10時")].set_index("close_day")
    b = cell[(cell.mail == "B") & (cell.send == "火曜10時")].set_index("close_day")
    base = pd.DataFrame({"close_day": KS, "A_closed": a.closed.values, "B_closed": b.closed.values,
                         "A_ratio": a.ratio.values, "B_ratio": b.ratio.values,
                         "B_minus_A_pt": np.round((b.closed.values - a.closed.values) * 100, 4)})
    base.to_csv(RES / "base_two_mails.csv", index=False)
    flip_days = [int(k) for k in KS if b.loc[k, "closed"] < a.loc[k, "closed"]]

    # 型ごとの、いずれ開く人のうちの割合（B と A）
    mix = {m: {TYPES[t]: r(SHARE[t] * P[m][t] / (SHARE * P[m]).sum()) for t in range(3)} for m in ["A", "B"]}

    # (3) 確かめ 72通り
    rows = []
    sends = {f"{DAYNAME[d]}曜10時": d * 24 + 10 for d in range(7)}
    sends["金曜18時"] = SEND["金曜18時"]
    for wk in [0.10, 0.20, 0.35]:
        share = np.array([0.5, 0.5 - wk, wk])     # すぐ見る人50%、残りを平日と週末に分ける
        for sp in [0.5, 1.0, 2.0]:
            rate = RATE * sp
            for sname, s in sends.items():
                xa = pd.DataFrame([one_mail(rng, P["A"], SEND["火曜10時"], share, rate) for _ in range(R_GRID)])
                xb = pd.DataFrame([one_mail(rng, P["B"], s, share, rate) for _ in range(R_GRID)])
                row = {"weekend_share": wk, "speed": sp, "b_send": sname,
                       "A_true": r(xa.true.mean()), "B_true": r(xb.true.mean())}
                for k in [1, 2, 3, 7]:
                    row[f"A_closed_{k}"] = r(xa[f"closed_{k}"].mean())
                    row[f"B_closed_{k}"] = r(xb[f"closed_{k}"].mean())
                    row[f"B_ratio_{k}"] = r(xb[f"closed_{k}"].mean() / xb.true.mean())
                    row[f"B_formula_ratio_{k}"] = r(formula_ratio(P["B"], share, rate, s, k))
                    row[f"B_looks_lower_{k}"] = bool(xb[f"closed_{k}"].mean() < xa[f"closed_{k}"].mean())
                    row[f"order_flipped_{k}"] = bool((xb[f"closed_{k}"].mean() < xa[f"closed_{k}"].mean()) != (xb.true.mean() < xa.true.mean()))
                rows.append(row)
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)

    g = grid
    robust = {"n": int(len(g)), "n_B_truly_higher": int((g.B_true > g.A_true).sum()), "B_true_over_A_true_share_pct": r((g.B_true > g.A_true).mean() * 100, 2),
              "B_true_over_A_true_by_weekend": (g.groupby("weekend_share").apply(lambda d: (d.B_true > d.A_true).mean() * 100)).round(2).to_dict()}
    for k in [1, 2, 3, 7]:
        robust[f"B_ratio_{k}_min"] = r(g[f"B_ratio_{k}"].min())
        robust[f"B_ratio_{k}_max"] = r(g[f"B_ratio_{k}"].max())
        robust[f"B_looks_lower_{k}_share_pct"] = r(g[f"B_looks_lower_{k}"].mean() * 100, 2)
        robust[f"order_flipped_{k}_share_pct"] = r(g[f"order_flipped_{k}"].mean() * 100, 2)
        bt = g[g.B_true > g.A_true]
        robust[f"order_flipped_{k}_share_pct_when_B_truly_higher"] = r(bt[f"order_flipped_{k}"].mean() * 100, 2)
        robust[f"formula_gap_{k}_max"] = r((g[f"B_ratio_{k}"] - g[f"B_formula_ratio_{k}"]).abs().max())
    robust["B_ratio_1_by_send"] = g.groupby("b_send").B_ratio_1.agg(["min", "max"]).round(4).reset_index().to_dict("records")
    robust["order_flipped_2_by_send_pct"] = (g.groupby("b_send").order_flipped_2.mean() * 100).round(2).to_dict()
    robust["B_ratio_2_by_speed"] = g.groupby("speed").B_ratio_2.agg(["min", "max"]).round(4).reset_index().to_dict("records")
    robust["B_ratio_7_by_speed"] = g.groupby("speed").B_ratio_7.agg(["min", "max"]).round(4).reset_index().to_dict("records")
    robust["order_flipped_by_k_and_speed_pct"] = {f"k{k}": (g.groupby("speed")[f"order_flipped_{k}"].mean() * 100).round(2).to_dict()
                                                  for k in [1, 2, 3, 7]}

    c = cell.set_index(["mail", "send", "close_day"])
    headline = {
        "A_true": a.loc[1, "true"], "B_true": b.loc[1, "true"],
        "A_closed_1": a.loc[1, "closed"], "B_closed_1": b.loc[1, "closed"],
        "A_closed_2": a.loc[2, "closed"], "B_closed_2": b.loc[2, "closed"],
        "A_closed_3": a.loc[3, "closed"], "B_closed_3": b.loc[3, "closed"],
        "A_closed_7": a.loc[7, "closed"], "B_closed_7": b.loc[7, "closed"],
        "A_closed_30": a.loc[30, "closed"], "B_closed_30": b.loc[30, "closed"],
        "A_ratio_1": a.loc[1, "ratio"], "B_ratio_1": b.loc[1, "ratio"], "B_ratio_3": b.loc[3, "ratio"],
        "B_formula_ratio_1": b.loc[1, "formula_ratio"],
        "flip_days": flip_days,
        "B_fri_ratio_1": c.loc[("B", "金曜18時", 1), "ratio"], "A_fri_ratio_1": c.loc[("A", "金曜18時", 1), "ratio"],
        "B_fri_ratio_2": c.loc[("B", "金曜18時", 2), "ratio"], "A_fri_ratio_2": c.loc[("A", "金曜18時", 2), "ratio"],
        "B_fri_ratio_3": c.loc[("B", "金曜18時", 3), "ratio"], "A_fri_ratio_3": c.loc[("A", "金曜18時", 3), "ratio"],
        "B_fri_closed_1": c.loc[("B", "金曜18時", 1), "closed"], "A_fri_closed_1": c.loc[("A", "金曜18時", 1), "closed"],
        "B_ratio_4": b.loc[4, "ratio"], "B_ratio_5": b.loc[5, "ratio"], "A_ratio_4": a.loc[4, "ratio"], "A_ratio_5": a.loc[5, "ratio"],
        "A_closed_4": a.loc[4, "closed"], "B_closed_4": b.loc[4, "closed"], "A_closed_5": a.loc[5, "closed"], "B_closed_5": b.loc[5, "closed"],
        "A_ratio_2": a.loc[2, "ratio"], "B_ratio_2": b.loc[2, "ratio"], "A_ratio_3": a.loc[3, "ratio"],
        "formula_gap_max_cells": r((cell.ratio - cell.formula_ratio).abs().max()),
    }
    out = {"settings": {"readers": N, "types": TYPES, "type_share": SHARE.tolist(), "open_rate_per_seen_hour": RATE.tolist(),
                        "open_prob": {m: v.tolist() for m, v in P.items()}, "send": SEND, "close_days": KS,
                        "reps_main": R_MAIN, "reps_grid": R_GRID, "seed": SEED},
           "headline": headline, "openers_mix_by_type": mix, "example_one_run_B_tue": ex_s, "robust": robust}
    with open(RES / "a1208_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # 図1：締めの日数ごとの開封率（基本の2通）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    ax.plot(base.close_day, base.A_closed * 100, marker="o", color=BLUE, label="A 平日の案内（火曜10時に送る）")
    ax.plot(base.close_day, base.B_closed * 100, marker="o", color=ORANGE, label="B 週末の催しの案内（火曜10時に送る）")
    ax.axhline(a.loc[1, "true"] * 100, color=BLUE, ls=":", lw=1)
    ax.axhline(b.loc[1, "true"] * 100, color=ORANGE, ls=":", lw=1)
    ax.text(30, a.loc[1, "true"] * 100 - 1.2, f"A 本当 {a.loc[1, 'true'] * 100:.2f}%", ha="right", va="top", fontsize=8.5, color=BLUE)
    ax.text(30, b.loc[1, "true"] * 100 + 0.6, f"B 本当 {b.loc[1, 'true'] * 100:.2f}%", ha="right", fontsize=8.5, color=ORANGE)
    ax.set_xscale("log")
    ax.set_xticks(KS, [f"{k}日" for k in KS])
    ax.minorticks_off()
    ax.set_xlabel("送ってから締めるまでの日数")
    ax.set_ylabel("締めた開封率（%）")
    ax.set_ylim(0, 35)
    ax.set_title("同じ火曜10時に送っても、早く締めると B が A より低く見えた")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    save(fig, "a1208_close_curve.png", SRC)

    # 図2：2×2（中身 × 送る時刻）で、2日で締めた値÷本当の値
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    k2 = cell[cell.close_day == 2]
    labels, vals, cols = [], [], []
    for mail, col in [("A", BLUE), ("B", ORANGE)]:
        for sname in SEND:
            v = k2[(k2.mail == mail) & (k2.send == sname)].ratio.iloc[0]
            labels.append(f"{mail}の中身\n{sname}に送る")
            vals.append(v * 100)
            cols.append(col)
    x = np.arange(4)
    ax.bar(x, vals, 0.55, color=cols)
    for xi, v in zip(x, vals):
        ax.text(xi, v + 1, f"{v:.2f}%", ha="center", fontsize=9.5)
    ax.set_xticks(x, labels, fontsize=9.5)
    ax.set_ylabel("2日で締めた開封率÷本当の開封率（%）")
    ax.set_ylim(0, 115)
    ax.set_title("2日で締めたとき、本当の開封率の何%が数えられたか")
    save(fig, "a1208_send_vs_mix.png", SRC)

    # 図3：確かめ 72通り（B の締めた値÷本当の値、日数ごと）
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    cmap = {0.5: GRAY, 1.0: BLUE, 2.0: ORANGE}
    for j, k in enumerate([1, 2, 3, 7]):
        for i, sp in enumerate([0.5, 1.0, 2.0]):
            v = g[g.speed == sp][f"B_ratio_{k}"].values * 100
            xx = j + (i - 1) * 0.25 + np.linspace(-0.08, 0.08, len(v))
            ax.scatter(xx, v, s=10, color=cmap[sp], alpha=0.75, label=f"開く速さ {sp:g}倍" if j == 0 else None)
    ax.set_xticks(range(4), ["1日で締める", "2日", "3日", "7日"])
    ax.set_ylabel("B の締めた開封率÷本当の開封率（%）")
    ax.set_ylim(0, 105)
    ax.set_title("72通りの置き方（週末に見る人の割合・開く速さ・B を送る時刻）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    save(fig, "a1208_grid.png", SRC)
    print(json.dumps(headline, ensure_ascii=False), round(time.time() - T0, 1), "s")


if __name__ == "__main__":
    main()
