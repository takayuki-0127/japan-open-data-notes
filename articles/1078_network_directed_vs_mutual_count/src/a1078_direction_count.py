"""1078 双方向で数えるか片方向で数えるかで、つながりの数は何倍違うのか？（架空のデータ）

架空の会社（社員400人・10部署）の1か月の社内の連絡（誰から誰へ何通送ったか）を、作成者が置いた
「組ごとの仲の良さ」「人ごとの送りやすさ・受けやすさ」からの乱数で作る。つながりを
送った相手・受けた相手・どちらか一方・両方向・送った相手＋受けた相手の5通りで数え、何倍違うかと、
「つながりの多い人」の上位10人がどれだけ入れかわるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1078
SRC = "架空の会社の社内の連絡（作成者が置いた仲の良さ・送りやすさからの乱数、seed 1078）"
N, D = 400, 10
BASE = {"pair_sd": 1.0, "act_sd": 0.7, "vol": 0.5, "between": 0.08, "rho": 0.5, "thr": 1}
REPS = 50
GRID_PAIR = [0.5, 1.0, 1.5]
GRID_ACT = [0.3, 0.7, 1.2]
GRID_VOL = [0.2, 0.5, 1.5]
GRID_REPS = 10
GRID_RHO = [0.0, 0.5, 0.8, 0.95]
WAYS = ["mutual", "out", "in", "either", "out_plus_in"]
WAY_JP = {"mutual": "両方向とも送った相手", "out": "送った相手", "in": "受けた相手",
          "either": "どちらか一方でも送った相手", "out_plus_in": "送った相手＋受けた相手（足し算）"}


def r(x, d=4):
    return round(float(x), d)


def messages(rng, pair_sd, act_sd, vol, between, rho, **_):
    dept = np.repeat(np.arange(D), N // D)
    same = dept[:, None] == dept[None, :]
    z = rng.normal(0, pair_sd, (N, N))
    z = np.triu(z, 1); z = z + z.T                      # 組ごとの仲の良さは両方向で同じ
    c = np.exp(z - pair_sd ** 2 / 2) * np.where(same, 1.0, between)
    e1, e2 = rng.normal(0, 1, N), rng.normal(0, 1, N)
    ls = e1 * act_sd
    la = (rho * e1 + np.sqrt(1 - rho ** 2) * e2) * act_sd
    s = np.exp(ls - act_sd ** 2 / 2); a = np.exp(la - act_sd ** 2 / 2)
    lam = vol * c * s[:, None] * a[None, :]
    np.fill_diagonal(lam, 0)
    return rng.poisson(lam), dept


def count(m, thr):
    t = m >= thr                       # i から j へ thr 通以上送った
    mu = t & t.T
    ei = t | t.T
    deg = {"out": t.sum(1), "in": t.sum(0), "mutual": mu.sum(1), "either": ei.sum(1)}
    deg["out_plus_in"] = deg["out"] + deg["in"]
    arcs = t.sum(); mutual_pairs = mu.sum() / 2; either_pairs = ei.sum() / 2
    rcp = 2 * mutual_pairs / arcs     # 送った向きのうち、相手からも送られていた割合
    return deg, {"arcs": arcs, "mutual_pairs": mutual_pairs, "either_pairs": either_pairs,
                 "reciprocity": rcp, "either_over_mutual": either_pairs / mutual_pairs,
                 "formula_either_over_mutual": (2 - rcp) / rcp,
                 "arcs_over_either": arcs / either_pairs, "formula_arcs_over_either": 1 / (1 - rcp / 2),
                 "sum_person_either_over_pairs": deg["either"].sum() / either_pairs}


def top_ids(v, k=10):
    return set(np.lexsort((np.arange(len(v)), -v))[:k])   # 同じ数は番号の若い順


def rank_corr(x, y):
    return pd.Series(x).rank().corr(pd.Series(y).rank())


def one(rng, kw):
    m, dept = messages(rng, **kw)
    deg, tot = count(m, kw["thr"])
    top = {w: top_ids(deg[w]) for w in WAYS}
    res = dict(tot)
    for w in WAYS:
        res[f"mean_{w}"] = deg[w].mean()
    for w in WAYS:
        res[f"ratio_{w}"] = deg[w].mean() / deg["mutual"].mean()
    res["person_either_over_mutual_median"] = np.median(deg["either"][deg["mutual"] > 0] / deg["mutual"][deg["mutual"] > 0])
    res["no_mutual_share"] = (deg["mutual"] == 0).mean()
    res["top_out_in_overlap"] = len(top["out"] & top["in"])
    res["top_mutual_either_overlap"] = len(top["mutual"] & top["either"])
    res["top_out_either_overlap"] = len(top["out"] & top["either"])
    res["top_in_either_overlap"] = len(top["in"] & top["either"])
    res["top1_out_eq_in"] = float(np.argmax(deg["out"]) == np.argmax(deg["in"]))
    res["rankcorr_out_in"] = rank_corr(deg["out"], deg["in"])
    res["msgs_per_person"] = m.sum() / N
    return res, m, dept, deg


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    rows = []
    first = None
    for i in range(REPS):
        res, m, dept, deg = one(rng, BASE)
        rows.append({"rep": i, **{k: r(v, 4) for k, v in res.items()}})
        if first is None:
            first = (m, dept, deg)
    br = pd.DataFrame(rows)
    br.to_csv(RES / "base_reps.csv", index=False)
    # 3通以上で数える
    rng3 = np.random.default_rng(SEED + 3)
    rows3 = [one(rng3, dict(BASE, thr=3))[0] for _ in range(REPS)]
    b3 = pd.DataFrame(rows3)

    grid = []
    j = 0
    for ps in GRID_PAIR:
        for asd in GRID_ACT:
            for vol in GRID_VOL:
                g_rng = np.random.default_rng(SEED * 100 + j); j += 1
                kw = dict(BASE, pair_sd=ps, act_sd=asd, vol=vol)
                rs = pd.DataFrame([one(g_rng, kw)[0] for _ in range(GRID_REPS)]).mean()
                grid.append({"pair_sd": ps, "act_sd": asd, "vol": vol,
                             "mean_either": r(rs.mean_either, 3), "mean_mutual": r(rs.mean_mutual, 3), "mean_out": r(rs.mean_out, 3),
                             "reciprocity": r(rs.reciprocity, 4), "either_over_mutual": r(rs.either_over_mutual, 3),
                             "arcs_over_either": r(rs.arcs_over_either, 4),
                             "top_out_in_overlap": r(rs.top_out_in_overlap, 2),
                             "top_mutual_either_overlap": r(rs.top_mutual_either_overlap, 2),
                             "rankcorr_out_in": r(rs.rankcorr_out_in, 3)})
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid.csv", index=False)

    # 確かめ：送りやすさと受けやすさの相関（作成者が置いた値）を変える（各10回）
    rho_rows = []
    for k_, rho in enumerate(GRID_RHO):
        r_rng = np.random.default_rng(SEED * 1000 + k_)
        rs = pd.DataFrame([one(r_rng, dict(BASE, rho=rho))[0] for _ in range(GRID_REPS)]).mean()
        rho_rows.append({"rho": rho, "top_out_in_overlap": r(rs.top_out_in_overlap, 2), "rankcorr_out_in": r(rs.rankcorr_out_in, 3),
                         "top1_out_eq_in_pct": r(rs.top1_out_eq_in * 100, 1),
                         "either_over_mutual": r(rs.either_over_mutual, 3), "reciprocity": r(rs.reciprocity, 4)})
    rg = pd.DataFrame(rho_rows)
    rg.to_csv(RES / "rho_check.csv", index=False)

    M = br.mean(numeric_only=True)
    M3 = b3.mean(numeric_only=True)
    ways = pd.DataFrame({"way": [WAY_JP[w] for w in WAYS], "mean_per_person": [r(M[f"mean_{w}"], 2) for w in WAYS],
                         "ratio_to_mutual": [r(M[f"ratio_{w}"], 3) for w in WAYS],
                         "mean_per_person_thr3": [r(M3[f"mean_{w}"], 2) for w in WAYS],
                         "ratio_to_mutual_thr3": [r(M3[f"ratio_{w}"], 3) for w in WAYS]})
    ways.to_csv(RES / "ways.csv", index=False)

    # data：1回分の連絡（1通以上の向き）と社員ごとの数
    m, dept, deg = first
    ii, jj = np.nonzero(m)
    sid = np.array([f"S{i:03d}" for i in range(N)])
    dn = np.array([chr(65 + k) + "部" for k in range(D)])
    pd.DataFrame({"from_id": sid[ii], "to_id": sid[jj], "messages": m[ii, jj]}).to_csv(DATA / "messages_one_run.csv", index=False)
    pd.DataFrame({"staff_id": sid, "dept": dn[dept], **{f"n_{w}": deg[w] for w in WAYS}}).to_csv(DATA / "staff_one_run.csv", index=False)

    hl = {"msgs_per_person": r(M.msgs_per_person, 2),
          **{f"mean_{w}": r(M[f"mean_{w}"], 2) for w in WAYS},
          "either_over_mutual": r(M.either_over_mutual, 3), "formula_either_over_mutual": r(M.formula_either_over_mutual, 3),
          "reciprocity_pct": r(M.reciprocity * 100, 2),
          "arcs_over_either": r(M.arcs_over_either, 3), "formula_arcs_over_either": r(M.formula_arcs_over_either, 3),
          "max_abs_diff_formula": r(max((br.either_over_mutual - br.formula_either_over_mutual).abs().max(),
                                        (br.arcs_over_either - br.formula_arcs_over_either).abs().max()), 4),
          "out_over_mutual": r(M.ratio_out, 3), "out_plus_in_over_mutual": r(M.ratio_out_plus_in, 3),
          "out_plus_in_over_either": r((M.ratio_out_plus_in / M.ratio_either), 3),
          "formula_out_plus_in_over_either": r(1 + 1 / M.either_over_mutual, 3),
          "sum_person_either_over_pairs": r(M.sum_person_either_over_pairs, 3),
          "person_either_over_mutual_median": r(M.person_either_over_mutual_median, 3),
          "no_mutual_pct": r(M.no_mutual_share * 100, 2),
          "top_out_in_overlap": r(M.top_out_in_overlap, 2), "top_mutual_either_overlap": r(M.top_mutual_either_overlap, 2),
          "top_out_either_overlap": r(M.top_out_either_overlap, 2), "top_in_either_overlap": r(M.top_in_either_overlap, 2),
          "top1_out_eq_in_pct": r(M.top1_out_eq_in * 100, 2), "rankcorr_out_in": r(M.rankcorr_out_in, 3),
          "thr3_either_over_mutual": r(M3.either_over_mutual, 3), "thr3_reciprocity_pct": r(M3.reciprocity * 100, 2),
          "thr3_mean_either": r(M3.mean_either, 2), "thr3_mean_mutual": r(M3.mean_mutual, 2),
          "thr3_top_out_in_overlap": r(M3.top_out_in_overlap, 2), "thr3_top_mutual_either_overlap": r(M3.top_mutual_either_overlap, 2),
          "grid_either_over_mutual_min": r(g.either_over_mutual.min(), 3), "grid_either_over_mutual_max": r(g.either_over_mutual.max(), 3),
          "grid_reciprocity_min_pct": r(g.reciprocity.min() * 100, 2), "grid_reciprocity_max_pct": r(g.reciprocity.max() * 100, 2),
          "grid_arcs_over_either_min": r(g.arcs_over_either.min(), 3), "grid_arcs_over_either_max": r(g.arcs_over_either.max(), 3),
          "grid_top_out_in_overlap_min": r(g.top_out_in_overlap.min(), 2), "grid_top_out_in_overlap_max": r(g.top_out_in_overlap.max(), 2),
          "grid_top_mutual_either_overlap_min": r(g.top_mutual_either_overlap.min(), 2),
          "grid_top_mutual_either_overlap_max": r(g.top_mutual_either_overlap.max(), 2)}
    for asd in GRID_ACT:
        sub = g[g.act_sd == asd]
        hl[f"grid_act{asd}_top_out_in_min"] = r(sub.top_out_in_overlap.min(), 2)
        hl[f"grid_act{asd}_top_out_in_max"] = r(sub.top_out_in_overlap.max(), 2)
    for vol in GRID_VOL:
        sub = g[g.vol == vol]
        hl[f"grid_vol{vol}_either_over_mutual_min"] = r(sub.either_over_mutual.min(), 3)
        hl[f"grid_vol{vol}_either_over_mutual_max"] = r(sub.either_over_mutual.max(), 3)
    for _, rw in rg.iterrows():
        hl[f"rho{rw.rho}_top_out_in_overlap"] = rw.top_out_in_overlap
        hl[f"rho{rw.rho}_rankcorr_out_in"] = rw.rankcorr_out_in
        hl[f"rho{rw.rho}_either_over_mutual"] = rw.either_over_mutual
    out = {"base_setting": dict(BASE, n_staff=N, n_dept=D), "reps": REPS, "grid_reps": GRID_REPS, "headline": hl,
           "ways": ways.to_dict("records"), "grid": g.to_dict("records"),
           "rho_check": rg.to_dict("records")}
    json.dump(out, open(RES / "a1078_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：5通りの数え方の、1人あたりのつながりの数（棒、0始まり）
    fig, ax = plt.subplots(figsize=(8.0, 4.3))
    xx = np.arange(len(WAYS)); wd = .38
    ax.bar(xx - wd / 2, ways.mean_per_person, wd, color=BLUE, label="1通以上で数える")
    ax.bar(xx + wd / 2, ways.mean_per_person_thr3, wd, color=ORANGE, label="3通以上で数える")
    for x_, a_, b_ in zip(xx, ways.mean_per_person, ways.mean_per_person_thr3):
        ax.text(x_ - wd / 2, a_ + .5, f"{a_:.2f}", ha="center", fontsize=7.8)
        ax.text(x_ + wd / 2, b_ + .5, f"{b_:.2f}", ha="center", fontsize=7.8)
    ax.set_xticks(xx)
    ax.set_xticklabels(["両方向とも\n送った", "送った", "受けた", "どちらか一方\nでも送った", "送った＋受けた\n（足し算）"])
    ax.set_ylim(0, ways.mean_per_person.max() * 1.18)
    ax.set_ylabel("1人あたりの相手の数（人、50回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("同じ1か月の連絡でも、数え方で1人あたりのつながりは大きく違う")
    save(fig, "a1078_ways.png", SRC)

    # 図2：27通りの、相手からも送られていた割合と「どちらか一方÷両方向」（式の線と重ねる）
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    cl = {0.2: LIGHT, 0.5: BLUE, 1.5: INK}
    mk = {0.3: "o", 0.7: "s", 1.2: "^"}
    for (vol, asd), gg in g.groupby(["vol", "act_sd"]):
        ax.scatter(gg.reciprocity * 100, gg.either_over_mutual, color=cl[vol], marker=mk[asd], s=36, zorder=3)
    xs = np.linspace(max(1, g.reciprocity.min() * 100 * .8), 100, 200)
    ax.plot(xs, (2 - xs / 100) / (xs / 100), color=GRAY, lw=1, ls="--", label="式：(2−割合)÷割合")
    for vol, c in cl.items():
        ax.scatter([], [], color=c, marker="o", label=f"連絡の量 {vol}")
    for asd, m_ in mk.items():
        ax.scatter([], [], color=INK, marker=m_, facecolor="none", label=f"送りやすさの差 {asd}")
    ax.set_xlim(0, 100); ax.set_ylim(0, g.either_over_mutual.max() * 1.1)
    ax.set_xlabel("送った向きのうち、相手からも送られていた割合（%）")
    ax.set_ylabel("どちらか一方の組 ÷ 両方向の組（倍）")
    ax.legend(frameon=False, fontsize=8, loc="upper right", ncol=2)
    ax.set_title("27通り（各10回）：何倍違うかは、相手からも送られる割合で決まる")
    save(fig, "a1078_grid.png", SRC)

    # 図3：1回分の、送った相手と受けた相手の数（上位10人の印）
    fig, ax = plt.subplots(figsize=(6.6, 5.2))
    to, ti = top_ids(deg["out"]), top_ids(deg["in"])
    jit = np.random.default_rng(SEED + 7).uniform(-.25, .25, (2, N))
    base_c = np.full(N, GRAY, dtype=object)
    for i in to:
        base_c[i] = BLUE
    for i in ti:
        base_c[i] = ORANGE
    for i in to & ti:
        base_c[i] = GREEN
    order = np.argsort([0 if c == GRAY else 1 for c in base_c])
    ax.scatter(deg["out"][order] + jit[0][order], deg["in"][order] + jit[1][order], c=list(base_c[order]), s=12, alpha=.7, lw=0)
    lim = max(deg["out"].max(), deg["in"].max()) * 1.08
    ax.plot([0, lim], [0, lim], color=INK, lw=.7, ls="--")
    ax.set_xlim(0, lim); ax.set_ylim(0, lim)
    ax.scatter([], [], color=BLUE, s=16, label=f"送った相手の上位10人だけ（{len(to - ti)}人）")
    ax.scatter([], [], color=ORANGE, s=16, label=f"受けた相手の上位10人だけ（{len(ti - to)}人）")
    ax.scatter([], [], color=GREEN, s=16, label=f"両方の上位10人（{len(to & ti)}人）")
    ax.set_xlabel("送った相手の数（人）"); ax.set_ylabel("受けた相手の数（人）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("1回分の社員400人：送った数の上位と受けた数の上位は別の人")
    save(fig, "a1078_out_in.png", SRC)

    print(json.dumps(hl, ensure_ascii=False, indent=1)); print(ways.to_string()); print(g.to_string()); print(rg.to_string())
    print("first run overlap", len(to & ti))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
