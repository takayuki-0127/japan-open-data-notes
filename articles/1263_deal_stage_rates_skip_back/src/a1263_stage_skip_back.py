"""1263 商談の段階ごとの進んだ割合を掛けた見込みは、段階を飛ばす商談や戻る商談があるとどれだけずれるのか？（架空のデータ）

作成者が置いた架空の会社の法人向けの商談。段階は 1 初回の面談 → 2 提案 → 3 見積もり → 4 条件の詰め → 受注。
各段階から、次へ進む・1つ飛ばして進む・1つ戻る・失注する、の確率を作成者が置く（前の動きによらない）。
  次へ進む（飛ばしを含む）確率 a_k のうち、割合 s で1つ飛ばす（1→3・2→4・3→受注）。
  失注しそうな分（1-a_k）のうち、割合 b で1つ前の段階へ戻る（2→1・3→2・4→3）。
過去に決まった商談の記録（段階の移り変わり）から段階ごとの割合を数え、いま途中の商談に掛けて見込みを出す。
  ① 来た数で割る：段階 k+1 に来たことのある商談の数 ÷ 段階 k に来たことのある商談の数。掛けると「受注の数÷段階kに来た数」になる
  ② 1つずつ進んだ数で割る：段階 k から k+1 へそのまま移った回数 ÷ 段階 k にいた回数（戻って同じ段階に来たらもう1回と数える）
  ③ 比べる相手：段階 k に来たことのある商談のうち、受注した割合を直接数える
本当の値：置いた確率から式で出した「いま段階 k にいる商談が受注する確率」。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1263
SRC = "架空の法人向けの商談（作成者が置いた段階の進み方・飛ばし・戻りの確率からの乱数、seed 1263）"
STAGES = ["初回の面談", "提案", "見積もり", "条件の詰め"]
K = 4
W, L = 5, 0                      # 受注・失注を表す番号
A_SETS = {"low": [0.45, 0.50, 0.55, 0.50], "base": [0.55, 0.60, 0.65, 0.60], "high": [0.65, 0.70, 0.75, 0.70]}
BASE = dict(a="base", s=0.2, b=0.15)
N_HIST, N_OPEN = 800, 200
OPEN_SHARE = [0.40, 0.25, 0.20, 0.15]


def trans(a, s, b):
    """段階 k（1..4）からの移り先の確率。列：0失注,1..4段階,5受注"""
    P = np.zeros((K + 1, 6))
    for k in range(1, K + 1):
        ak = a[k - 1]
        sk = s if k <= 3 else 0.0           # 4 からは飛ばせない（次が受注）
        bk = b if k >= 2 else 0.0           # 1 からは戻れない
        P[k, min(k + 1, W)] += ak * (1 - sk)
        if sk > 0:
            P[k, min(k + 2, W)] += ak * sk
        if bk > 0:
            P[k, k - 1] += (1 - ak) * bk
        P[k, L] += (1 - ak) * (1 - bk)
    return P


def true_win(P):
    """いま段階 k にいる商談が受注する確率（式で解く）"""
    Q = P[1:K + 1, 1:K + 1]
    r = P[1:K + 1, W]
    return np.linalg.solve(np.eye(K) - Q, r)


def run_deal(rng, P, start=1):
    seq, k = [start], start
    cum = np.cumsum(P, axis=1)
    while 1 <= k <= K:
        k = int(np.searchsorted(cum[k], rng.random(), side="right"))
        seq.append(k)
    return seq


def rates(hists):
    reached = np.zeros(K + 2)     # 1..4 と 受注(5)
    visits = np.zeros(K + 1)
    steps = np.zeros(K + 1)
    won_reached = np.zeros(K + 1)
    skips = backs = 0
    for seq in hists:
        won = seq[-1] == W
        for k in set(seq):
            if 1 <= k <= W:
                reached[k] += 1
                if won and k <= K:
                    won_reached[k] += 1
        for x, y in zip(seq[:-1], seq[1:]):
            visits[x] += 1
            if y == x + 1:
                steps[x] += 1
            elif y == x + 2 or (x == 3 and y == W):
                skips += 1
            elif y == x - 1:
                backs += 1
    r1 = reached[2:W + 1] / reached[1:K + 1]
    r2 = steps[1:] / visits[1:]
    f1 = np.array([np.prod(r1[k:]) for k in range(K)])
    f2 = np.array([np.prod(r2[k:]) for k in range(K)])
    f3 = won_reached[1:] / reached[1:K + 1]
    return dict(r1=r1, r2=r2, f1=f1, f2=f2, f3=f3, skip_deals=skips, back_moves=backs)


def one_rep(rng, a, s, b):
    P = trans(A_SETS[a], s, b)
    h = true_win(P)
    hists = [run_deal(rng, P) for _ in range(N_HIST)]
    rt = rates(hists)
    stage = rng.choice(np.arange(1, K + 1), N_OPEN, p=OPEN_SHARE)
    amt = np.round(rng.lognormal(np.log(300), 0.8, N_OPEN))       # 金額（万円）
    tot = {m: float(np.sum(amt * rt[m][stage - 1])) for m in ["f1", "f2", "f3"]}
    tot["true"] = float(np.sum(amt * h[stage - 1]))
    return h, rt, tot, hists, stage, amt


def main():
    t0 = time.time()
    a, s, b = BASE["a"], BASE["s"], BASE["b"]

    # 1回分（data に置く）
    rng = np.random.default_rng([SEED, 0])
    h, rt, tot, hists, stage, amt = one_rep(rng, a, s, b)
    pd.DataFrame({"deal": np.arange(1, N_HIST + 1),
                  "path": ["-".join({0: "失注", 5: "受注"}.get(x, str(x)) for x in q) for q in hists],
                  "won": [int(q[-1] == W) for q in hists]}).to_csv(DATA / "history_one_set.csv", index=False)
    pd.DataFrame({"deal": np.arange(1, N_OPEN + 1), "stage_now": stage, "amount_man_yen": amt.astype(int),
                  "f1": rt["f1"][stage - 1].round(4), "f2": rt["f2"][stage - 1].round(4),
                  "f3": rt["f3"][stage - 1].round(4), "true_win": h[stage - 1].round(4)}).to_csv(DATA / "open_one_set.csv", index=False)
    n_skip_deal = sum(any((y == x + 2) or (x == 3 and y == W) for x, y in zip(q[:-1], q[1:])) for q in hists)
    n_back_deal = sum(any(y == x - 1 and y >= 1 for x, y in zip(q[:-1], q[1:])) for q in hists)
    one = {"history_deals": N_HIST, "won": int(sum(q[-1] == W for q in hists)),
           "deals_with_skip": int(n_skip_deal), "deals_with_back": int(n_back_deal),
           "pipeline_total_man_yen": int(amt.sum()),
           "forecast_m1": round(tot["f1"]), "forecast_m2": round(tot["f2"]), "forecast_m3": round(tot["f3"]),
           "true_expected": round(tot["true"])}

    # 2) 基本の置き方で500回
    rows, srows = [], []
    for r in range(500):
        h, rt, tot, *_ = one_rep(np.random.default_rng([SEED, 1, r]), a, s, b)
        rows.append({"rep": r, "ratio_m1": tot["f1"] / tot["true"], "ratio_m2": tot["f2"] / tot["true"],
                     "ratio_m3": tot["f3"] / tot["true"]})
        for k in range(K):
            srows.append({"rep": r, "stage": k + 1, "f1": rt["f1"][k], "f2": rt["f2"][k], "f3": rt["f3"][k], "true": h[k]})
    reps = pd.DataFrame(rows)
    reps.round(5).to_csv(RES / "reps_base.csv", index=False)
    st = pd.DataFrame(srows)
    by_stage = st.groupby("stage").mean().drop(columns="rep")
    for m in ["f1", "f2", "f3"]:
        by_stage[m + "_over_true"] = (by_stage[m] / by_stage["true"]).round(3)
    by_stage.insert(0, "stage_name", STAGES)
    by_stage.round(4).to_csv(RES / "by_stage.csv")
    h_base = true_win(trans(A_SETS[a], s, b))

    # 対照：飛ばしも戻りもない／戻りだけ／飛ばしだけ（各200回）
    ctrl = []
    for name, (cs, cb) in {"none": (0.0, 0.0), "back_only": (0.0, b), "skip_only": (s, 0.0), "both": (s, b)}.items():
        rr = []
        for r in range(200):
            h, rt, tot, *_ = one_rep(np.random.default_rng([SEED, 2, int(cs * 100), int(cb * 100), r]), a, cs, cb)
            rr.append([tot["f1"] / tot["true"], tot["f2"] / tot["true"], tot["f3"] / tot["true"]])
        rr = np.array(rr)
        ctrl.append({"case": name, "s": cs, "b": cb, "ratio_m1": round(rr[:, 0].mean(), 3), "ratio_m2": round(rr[:, 1].mean(), 3),
                     "ratio_m3": round(rr[:, 2].mean(), 3)})
    ctrl = pd.DataFrame(ctrl)
    ctrl.round(4).to_csv(RES / "controls.csv", index=False)

    # 3) 確かめ：36通り（各40回）
    grid = []
    for an in A_SETS:
        for gs in [0.0, 0.1, 0.2, 0.3]:
            for gb in [0.0, 0.15, 0.3]:
                rr = []
                for r in range(40):
                    h, rt, tot, *_ = one_rep(np.random.default_rng([SEED, 3, list(A_SETS).index(an), int(gs * 100), int(gb * 100), r]), an, gs, gb)
                    rr.append([tot["f1"] / tot["true"], tot["f2"] / tot["true"], tot["f3"] / tot["true"], rt["f1"][1] / h[1], rt["f2"][0] / h[0]])
                rr = np.array(rr)
                grid.append({"a": an, "s": gs, "b": gb, "ratio_m1": rr[:, 0].mean(), "ratio_m2": rr[:, 1].mean(),
                             "ratio_m3": rr[:, 2].mean(), "stage2_m1_over_true": rr[:, 3].mean(), "stage1_m2_over_true": rr[:, 4].mean()})
    gr = pd.DataFrame(grid)
    gr.round(4).to_csv(RES / "grid.csv", index=False)

    q = lambda x, p: round(float(np.quantile(x, p)), 4)
    head = {"true_win_by_stage": [round(float(x), 4) for x in h_base],
            "ratio_m1_mean": round(reps.ratio_m1.mean(), 4), "ratio_m1_p10_p90": [q(reps.ratio_m1, .1), q(reps.ratio_m1, .9)],
            "ratio_m2_mean": round(reps.ratio_m2.mean(), 4), "ratio_m2_p10_p90": [q(reps.ratio_m2, .1), q(reps.ratio_m2, .9)],
            "ratio_m3_mean": round(reps.ratio_m3.mean(), 4), "ratio_m3_p10_p90": [q(reps.ratio_m3, .1), q(reps.ratio_m3, .9)],
            "share_reps_m1_over_true": round(float(np.mean(reps.ratio_m1 > 1)), 4),
            "share_reps_m2_under_true": round(float(np.mean(reps.ratio_m2 < 1)), 4)}
    g0 = gr[(gr.s == 0)]
    robust = {"settings": int(len(gr)),
              "ratio_m1_range": [round(gr.ratio_m1.min(), 4), round(gr.ratio_m1.max(), 4)],
              "ratio_m2_range": [round(gr.ratio_m2.min(), 4), round(gr.ratio_m2.max(), 4)],
              "ratio_m3_range": [round(gr.ratio_m3.min(), 4), round(gr.ratio_m3.max(), 4)],
              "ratio_m1_range_no_skip": [round(g0.ratio_m1.min(), 4), round(g0.ratio_m1.max(), 4)],
              "ratio_m1_range_skip_0.3": [round(gr[gr.s == 0.3].ratio_m1.min(), 4), round(gr[gr.s == 0.3].ratio_m1.max(), 4)],
              "ratio_m2_range_no_skip_no_back": [round(gr[(gr.s == 0) & (gr.b == 0)].ratio_m2.min(), 4), round(gr[(gr.s == 0) & (gr.b == 0)].ratio_m2.max(), 4)],
              "ratio_m2_range_skip_0.3_back_0.3": [round(gr[(gr.s == 0.3) & (gr.b == 0.3)].ratio_m2.min(), 4), round(gr[(gr.s == 0.3) & (gr.b == 0.3)].ratio_m2.max(), 4)],
              "settings_m1_over_m2_gap_gt_0.2": int(np.sum(gr.ratio_m1 - gr.ratio_m2 > 0.2)),
              "stage2_m1_over_true_range": [round(gr.stage2_m1_over_true.min(), 4), round(gr.stage2_m1_over_true.max(), 4)]}
    out = {"headline": head, "by_stage": by_stage.round(4).reset_index().to_dict(orient="records"),
           "controls": ctrl.round(4).to_dict(orient="records"), "one_set": one, "robust": robust,
           "settings": {"stages": STAGES, "advance": A_SETS, "base": BASE, "history_deals": N_HIST, "open_deals": N_OPEN,
                        "open_stage_share": OPEN_SHARE, "amount": "中央値300万円・対数の標準偏差0.8", "reps_base": 500,
                        "reps_control": 200, "reps_grid": 40}}
    json.dump(out, open(RES / "a1263_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1 段階ごとの見込み÷本当
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    x = np.arange(K)
    for i, (m, lab, c) in enumerate([("f1", "①来た数で割って掛ける", BLUE), ("f2", "②1つずつ進んだ数で割って掛ける", ORANGE),
                                     ("f3", "③来た商談のうち受注した割合", GREEN)]):
        v = by_stage[m + "_over_true"].values
        ax.bar(x + (i - 1) * 0.26, v, 0.26, color=c, label=lab)
        for xx, vv in zip(x + (i - 1) * 0.26, v):
            ax.text(xx, vv + 0.02, f"{vv:.3f}", ha="center", fontsize=7.5)
    ax.axhline(1, color=INK, lw=0.8, ls="--")
    ax.set_xticks(x, [f"いま{n}" for n in STAGES])
    ax.set_ylim(0, max(1.6, by_stage[["f1_over_true", "f2_over_true", "f3_over_true"]].values.max() + 0.2))
    ax.set_ylabel("受注の見込み ÷ 本当の確率")
    ax.set_title("いまの段階ごとの見込み（基本の置き方、500回の平均）")
    ax.legend(fontsize=8.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)
    save(fig, "a1263_by_stage.png", SRC, y=-0.1)

    # 図2 対照
    fig, ax = plt.subplots(figsize=(7.8, 4.0))
    labs = ["飛ばしも戻りもなし", "戻りだけ", "飛ばしだけ", "両方（基本）"]
    x = np.arange(4)
    for i, (m, lab, c) in enumerate([("ratio_m1", "①", BLUE), ("ratio_m2", "②", ORANGE), ("ratio_m3", "③", GREEN)]):
        v = ctrl[m].values
        ax.bar(x + (i - 1) * 0.26, v, 0.26, color=c, label=lab)
        for xx, vv in zip(x + (i - 1) * 0.26, v):
            ax.text(xx, vv + 0.02, f"{vv:.3f}", ha="center", fontsize=7.5)
    ax.axhline(1, color=INK, lw=0.8, ls="--")
    ax.set_xticks(x, labs)
    ax.set_ylim(0, 1.5)
    ax.set_ylabel("見込みの合計 ÷ 本当の見込み")
    ax.set_title("途中の商談200件の見込みの合計（各200回の平均）")
    ax.legend(fontsize=9, frameon=False, ncol=3, loc="upper left")
    save(fig, "a1263_controls.png", SRC)

    # 図3 36通り
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.0), sharey=True)
    for ax, m, ttl in [(axes[0], "ratio_m1", "①来た数で割って掛ける"), (axes[1], "ratio_m2", "②1つずつ進んだ数で割って掛ける")]:
        for gb, c in zip([0.0, 0.15, 0.3], [LIGHT, BLUE, INK]):
            for an, ls in zip(A_SETS, [":", "-", "--"]):
                d = gr[(gr.b == gb) & (gr.a == an)]
                ax.plot(d.s * 100, d[m], color=c, ls=ls, marker="o", ms=3,
                        label=f"戻り{int(gb*100)}%" if an == "base" else None)
        ax.axhline(1, color=GRAY, lw=0.8)
        ax.set_title(ttl, fontsize=11)
        ax.set_xlabel("飛ばす割合（%）")
        ax.set_xticks([0, 10, 20, 30])
    axes[0].set_ylabel("見込みの合計 ÷ 本当の見込み")
    axes[0].set_ylim(0, max(1.6, gr[["ratio_m1", "ratio_m2"]].values.max() + 0.1))
    axes[0].legend(fontsize=8.5, frameon=False, loc="lower left")
    fig.suptitle("36通りの置き方（点線は進む確率が低い組・実線は基本・破線は高い組、各40回の平均）", fontsize=12, y=1.04)
    save(fig, "a1263_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("run_sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
