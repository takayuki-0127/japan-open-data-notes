"""1006 重みを少し変えると、上位は何位入れ替わるのか？（架空のデータ）

架空のリーグの60チーム。指数の項目は5つ（得点力・守り・パス・走る量・控えの層）で、リーグの中で標準化した値を使う。
基本の重み（0.30・0.25・0.20・0.15・0.10）から、1つの項目の重みを δ だけ別の1つの項目へ移す（5×4＝20通り）。
δ を 0.02・0.05・0.10 に変え、上位10チームと1位がどれだけ入れ替わるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1006
SRC = "架空のリーグのチームの指数（作成者が乱数で作成、seed 1006）"

ITEMS = ["得点力", "守り", "パス", "走る量", "控えの層"]
SHAPES = {"基本（0.30〜0.10）": np.array([0.30, 0.25, 0.20, 0.15, 0.10]),
          "均等（0.20ずつ）": np.array([0.20] * 5),
          "偏り（0.40・0.30・0.10・0.10・0.10）": np.array([0.40, 0.30, 0.10, 0.10, 0.10])}
W0 = SHAPES["基本（0.30〜0.10）"]
BASE = {"n": 60, "rho": 0.3, "shape": "基本（0.30〜0.10）"}
DELTAS = [0.02, 0.05, 0.10]
N_LEAGUE = 1000
N_SENS = 500
TOP = 10


def moves(w0, d):
    """重み d を項目 i から項目 j へ移す（i≠j）。移せない（重みが d 未満）組は除く"""
    out, lab = [], []
    for i in range(5):
        for j in range(5):
            if i != j and w0[i] >= d - 1e-12:
                w = w0.copy(); w[i] -= d; w[j] += d
                out.append(w); lab.append((ITEMS[i], ITEMS[j]))
    return np.array(out), lab


def make_league(rng, n=60, rho=0.3, **_):
    cov = np.full((5, 5), rho) + np.eye(5) * (1 - rho)
    z = rng.multivariate_normal(np.zeros(5), cov, n)
    return (z - z.mean(0)) / z.std(0)  # リーグの中で標準化


def index_of(s, w):
    return 50 + 10 * (s @ w)  # 指数（点）


def order(score):
    return np.argsort(-score, kind="stable")


def rank_of(score):
    r = np.empty(len(score), int); r[order(score)] = np.arange(1, len(score) + 1); return r


def league_stats(s, w0, d):
    base = index_of(s, w0)
    bo = order(base); btop = set(bo[:TOP]); brank = rank_of(base)
    W, _ = moves(w0, d)
    first_change, drop, pos_change, max_move = [], [], [], []
    for w in W:
        sc = index_of(s, w); o = order(sc); r = rank_of(sc)
        first_change.append(o[0] != bo[0])
        drop.append(len(btop - set(o[:TOP])))
        pos_change.append(int((o[:TOP] != bo[:TOP]).sum()))
        max_move.append(int(np.abs(r[bo[:TOP]] - brank[bo[:TOP]]).max()))
    sb = np.sort(base)[::-1]
    return {"gap12": float(sb[0] - sb[1]), "gap10_11": float(sb[TOP - 1] - sb[TOP]),
            "first_change_mean": float(np.mean(first_change)), "first_change_any": int(np.any(first_change)),
            "drop_mean": float(np.mean(drop)), "drop_max": int(np.max(drop)),
            "pos_change_mean": float(np.mean(pos_change)), "max_move_mean": float(np.mean(max_move)),
            "max_move_max": int(np.max(max_move))}


def run(seed, reps, d, n=60, rho=0.3, shape="基本（0.30〜0.10）"):
    rng = np.random.default_rng(seed)
    return pd.DataFrame([league_stats(make_league(rng, n, rho), SHAPES[shape], d) for _ in range(reps)])


def main():
    # 例のリーグ
    s = make_league(np.random.default_rng(SEED), BASE["n"], BASE["rho"])
    pd.DataFrame(np.round(s, 4), columns=ITEMS).assign(team_id=np.arange(1, BASE["n"] + 1))[["team_id"] + ITEMS] \
        .to_csv(DATA / "league_example.csv", index=False)
    base = index_of(s, W0); bo = order(base)
    W, lab = moves(W0, 0.05)
    exrows = []
    for w, (a, b) in zip(W, lab):
        sc = index_of(s, w); o = order(sc)
        exrows.append({"from": a, "to": b, "weights": "・".join(f"{v:.2f}" for v in w),
                       "top1": int(o[0] + 1), "top10_dropped": len(set(bo[:TOP]) - set(o[:TOP])),
                       "top10_positions_changed": int((o[:TOP] != bo[:TOP]).sum()),
                       "top3": "・".join(str(int(t + 1)) for t in o[:3])})
    exdf = pd.DataFrame(exrows)
    rk_ex = np.array([rank_of(index_of(s, w)) for w in W]); exdf.to_csv(RES / "example_moves_d005.csv", index=False)
    sb = np.sort(base)[::-1]
    ex = {"base_top10": [int(t + 1) for t in bo[:TOP]], "base_top10_index": [round(float(v), 2) for v in sb[:TOP]],
          "gap12": round(float(sb[0] - sb[1]), 3), "n_moves": len(W),
          "n_moves_first_changed": int((exdf.top1 != bo[0] + 1).sum()),
          "n_moves_top10_member_changed": int((exdf.top10_dropped > 0).sum()),
          "n_teams_in_any_top10": len(set().union(*[set(order(index_of(s, w))[:TOP]) for w in W]) | set(bo[:TOP])),
          "n_top15_moved_ge3": int(sum((rk_ex[:, t].max() - rk_ex[:, t].min()) >= 3 for t in bo[:15])),
          "max_range_top15": int(max(rk_ex[:, t].max() - rk_ex[:, t].min() for t in bo[:15])),
          "index_sd": round(float(base.std()), 3),
          "n_teams_can_be_first": len({int(order(index_of(s, w))[0]) for w in W} | {int(bo[0])})}

    # 1,000リーグ × δ
    main_rows, per = [], {}
    for k, d in enumerate(DELTAS):
        df = run(SEED * 10 + k, N_LEAGUE, d)
        per[d] = df
        m = df.mean()
        main_rows.append({"delta": d, "first_change_mean": round(float(m.first_change_mean), 4),
                          "first_change_any": round(float(m.first_change_any), 4),
                          "drop_mean": round(float(m.drop_mean), 3), "drop_max_mean": round(float(m.drop_max), 3),
                          "pos_change_mean": round(float(m.pos_change_mean), 3),
                          "max_move_mean": round(float(m.max_move_mean), 3),
                          "max_move_max_mean": round(float(m.max_move_max), 3),
                          "gap12_median": round(float(df.gap12.median()), 3),
                          "gap10_11_median": round(float(df.gap10_11.median()), 3),
                          "max_gap12_flipped_any": round(float(df.gap12[df.first_change_any == 1].max()), 3)})
    mt = pd.DataFrame(main_rows); mt.to_csv(RES / "by_delta.csv", index=False)
    pd.concat([per[d].assign(delta=d) for d in DELTAS]).to_csv(RES / "leagues_1000.csv", index=False, float_format="%.4f")

    # 1位と2位の差と、δ=0.05 のどれかで1位が変わる割合
    d5 = per[0.05].copy()
    bins = [0, 0.5, 1, 2, 3, 5, 100]
    d5["gap_bin"] = pd.cut(d5.gap12, bins, right=False)
    gb = d5.groupby("gap_bin", observed=True).agg(leagues=("gap12", "size"), first_change_any=("first_change_any", "mean"),
                                                  first_change_mean=("first_change_mean", "mean")).reset_index()
    gb["gap_bin"] = gb.gap_bin.astype(str)
    gb = gb.round(4); gb.to_csv(RES / "by_gap.csv", index=False)
    share_gap_lt1 = round(float((d5.gap12 < 1).mean()), 4)

    # 確かめ：置き方を1つずつ変える（δ=0.05、各500リーグ）
    sens = []
    grid = [("チームの数", "n", [20, 60, 200]), ("項目どうしの相関", "rho", [0.0, 0.3, 0.6]),
            ("基本の重みの形", "shape", list(SHAPES))]
    k = 0
    for label, key, vals in grid:
        for v in vals:
            kw = dict(BASE); kw[key] = v; k += 1
            m = run(SEED * 100 + k, N_SENS, 0.05, **kw).mean()
            sens.append({"changed": label, "value": v, "first_change_mean": round(float(m.first_change_mean), 4),
                         "first_change_any": round(float(m.first_change_any), 4),
                         "drop_mean": round(float(m.drop_mean), 3), "pos_change_mean": round(float(m.pos_change_mean), 3),
                         "max_move_mean": round(float(m.max_move_mean), 3)})
    sens = pd.DataFrame(sens); sens.to_csv(RES / "robustness.csv", index=False)

    out = {"example_league": ex, "by_delta": mt.to_dict("records"), "by_gap_d005": gb.to_dict("records"),
           "share_gap12_lt1_point": share_gap_lt1,
           "robustness_ranges_d005": {c: [float(sens[c].min()), float(sens[c].max())]
                                      for c in ["first_change_any", "first_change_mean", "drop_mean", "pos_change_mean"]},
           "settings": {"n": BASE["n"], "rho": BASE["rho"], "base_weights": W0.tolist(), "top": TOP,
                        "index": "50+10×（重み×標準化した項目の和）"}}
    json.dump(out, open(RES / "a1006_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例のリーグ、上位15チームの指数と、δ=0.05 の20通りでの順位の幅
    top15 = bo[:15]
    rk = np.array([rank_of(index_of(s, w)) for w in W])  # 20×n
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    for i, t in enumerate(top15):
        lo, hi = rk[:, t].min(), rk[:, t].max()
        ax.plot([lo, hi], [i, i], color=ORANGE if hi - lo >= 3 else LIGHT, lw=5, solid_capstyle="round")
        ax.plot(i + 1, i, "o", color=INK, ms=4)
        ax.text(20.2, i, f"{base[t]:.1f}点", va="center", fontsize=8, color=GRAY)
    ax.set_yticks(range(15)); ax.set_yticklabels([f"チーム{t + 1}" for t in top15], fontsize=8.5)
    ax.invert_yaxis(); ax.set_xlabel("順位（黒い点：基本の重み、帯：重みを0.05動かした20通りでの幅）")
    ax.axvline(10.5, color=GRAY, lw=0.8, ls="--"); ax.text(10.6, 14.4, "10位の線", fontsize=8, color=GRAY)
    ax.set_xticks(range(1, 20, 2)); ax.set_xlim(0.5, 21.5)
    ax.text(20.2, -1.1, "基本の指数", fontsize=8, color=GRAY)
    ax.text(0.0, 1.015, "オレンジ：20通りの中で順位が3つ以上動いたチーム", transform=ax.transAxes, ha="left", fontsize=8.5, color=ORANGE)
    ax.set_title("重みを0.05動かすだけで、上位の順位はこれだけ動く（例のリーグ）", pad=20)
    save(fig, "a1006_example_ranges.png", SRC)

    # 図2：1位と2位の差と、どれかで1位が変わる割合（δ=0.05）
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    ax.bar(range(len(gb)), gb.first_change_any * 100, color=BLUE)
    for i, (v, nn) in enumerate(zip(gb.first_change_any * 100, gb.leagues)):
        ax.text(i, v + 1.5, f"{v:.1f}%\n（{nn}リーグ）", ha="center", fontsize=8)
    names = ["0.5点未満", "0.5〜1点", "1〜2点", "2〜3点", "3〜5点", "5点以上"]
    ax.set_xticks(range(len(gb))); ax.set_xticklabels(names[:len(gb)])
    ax.set_ylim(0, 115); ax.set_yticks(range(0, 101, 20))
    ax.set_xlabel("基本の重みでの、1位と2位の指数の差"); ax.set_ylabel("1位が変わったリーグ（%）")
    ax.set_title("1位と2位の差が小さいほど、重みを0.05動かす20通りのどれかで\n1位が変わる（1,000リーグ）")
    save(fig, "a1006_gap.png", SRC)

    # 図3：確かめ
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    yy = np.arange(len(sens))[::-1]
    isbase = [(r.changed == "チームの数" and r.value == 60) or (r.changed == "項目どうしの相関" and r.value == 0.3)
              or (r.changed == "基本の重みの形" and r.value == BASE["shape"]) for r in sens.itertuples()]
    ax.barh(yy, sens.first_change_any * 100, color=[BLUE if b else LIGHT for b in isbase], height=0.7)
    for y, v in zip(yy, sens.first_change_any * 100):
        ax.text(v + 1, y, f"{v:.1f}%", va="center", fontsize=8)
    labels = [f"{r.changed}　{r.value}" if r.changed == "基本の重みの形" else f"{r.changed}　{r.value:g}" for r in sens.itertuples()]
    ax.set_yticks(yy); ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(0, 100); ax.set_xlabel("重みを0.05動かす20通りのどれかで1位が変わったリーグ（%、各500リーグ）")
    ax.set_title("置き方を1つずつ変えても、どれかの小さな動かし方で1位が変わる（濃い色が基本）")
    save(fig, "a1006_robustness.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
