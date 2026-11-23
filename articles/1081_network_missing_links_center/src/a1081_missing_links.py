"""1081 記録に残らなかったつながりがあると、中心の人はどう変わるのか？（架空のデータ）

架空の会社（社員300人・10部署×30人）。社員どうしの本当のやり取り（つながり）を作成者が置き、
そのうち社内チャットに残ったつながりだけが「記録」に載るとする。
本当のつながりで数えた「中心の人」（つながりの数・間に立つ度合い）の上位10人が、
記録だけで数えた上位10人にどれだけ残るかを、
①記録の漏れがでたらめに起きるとき、②対面でのやり取りが多い3部署で漏れが多いとき、で比べる。
"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")   # 小さな行列の計算は1つの CPU のほうが速い
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1081
SRC = "架空の会社の社員どうしのやり取り（作成者が乱数で作成、seed 1081）"
N_DEPT, PER = 10, 30
N = N_DEPT * PER
FACE = [0, 1, 2]       # 対面でのやり取りが多い部署（部署1〜3）
SIG_W = 0.6            # やり取りの多さの人ごとの振れ（対数の標準偏差）
C_IN, C_OUT = 0.16, 0.008
Q_FACE, Q_OTHER = 0.4, 0.9   # 記録に残る確率（どちらかが対面の多い部署なら Q_FACE）
MISS_RATES = [0.1, 0.2, 0.3, 0.4, 0.5]
REPS = 100
GRID_REPS = 40
TOP = 10
DEPT = np.repeat(np.arange(N_DEPT), PER)
IS_FACE = np.isin(DEPT, FACE)


def make_true(rng, sig_w=SIG_W):
    w = np.exp(rng.normal(0, sig_w, N))
    same = DEPT[:, None] == DEPT[None, :]
    p = np.minimum(1.0, np.where(same, C_IN, C_OUT) * w[:, None] * w[None, :])
    u = np.triu(rng.random((N, N)) < p, 1)
    return u | u.T


def betweenness(A):
    """間に立つ度合い（媒介中心性、正規化なし）。Brandes の方法を、全員を出発点にして行列で一度に計算する"""
    n = A.shape[0]; Af = A.astype(float)
    reached = np.eye(n, dtype=bool)
    sigma = np.eye(n); fsig = np.eye(n); levels = [np.eye(n)]
    while True:
        nxt = fsig @ Af
        new = (nxt > 0) & ~reached
        if not new.any():
            break
        reached |= new
        fsig = nxt * new; sigma += fsig; levels.append(new.astype(float))
    inv = np.where(sigma > 0, 1 / np.where(sigma > 0, sigma, 1), 0)
    delta = np.zeros((n, n))
    for k in range(len(levels) - 1, 0, -1):
        X = levels[k] * (1 + delta) * inv
        delta += levels[k - 1] * sigma * (X @ Af)
    return (delta.sum(0) - delta.diagonal()) / 2


def betweenness_plain(A):
    """確かめ用：1人ずつ出発点にする、ふつうの書き方の Brandes の方法"""
    n = A.shape[0]; nb = [np.flatnonzero(A[i]) for i in range(n)]
    bc = np.zeros(n)
    for s in range(n):
        order, pred = [], [[] for _ in range(n)]
        sig = np.zeros(n); sig[s] = 1; dist = np.full(n, -1); dist[s] = 0
        q = [s]; qi = 0
        while qi < len(q):
            v = q[qi]; qi += 1; order.append(v)
            for w in nb[v]:
                if dist[w] < 0:
                    dist[w] = dist[v] + 1; q.append(w)
                if dist[w] == dist[v] + 1:
                    sig[w] += sig[v]; pred[w].append(v)
        dl = np.zeros(n)
        for w in reversed(order):
            for v in pred[w]:
                dl[v] += sig[v] / sig[w] * (1 + dl[w])
            if w != s:
                bc[w] += dl[w]
    return bc / 2


def record(rng, A, q):
    """q：つながりごとの記録に残る確率（N×N）"""
    u = np.triu(A & (rng.random((N, N)) < q), 1)
    return u | u.T


def q_matrix(q_face=Q_FACE, q_other=Q_OTHER):
    either = IS_FACE[:, None] | IS_FACE[None, :]
    return np.where(either, q_face, q_other)


def top_set(x, jit):
    return set(np.argsort(-(x + jit), kind="stable")[:TOP])


def spearman(a, b):
    return float(pd.Series(a).rank().corr(pd.Series(b).rank()))


def compare(true_c, rec_c, jit):
    t, r = top_set(true_c, jit), top_set(rec_c, jit)
    t1 = int(np.argmax(true_c + jit)); r1 = int(np.argmax(rec_c + jit))
    rank_of_t1 = int((rec_c + jit > rec_c[t1] + jit[t1]).sum()) + 1
    return dict(overlap=len(t & r), same_top1=int(t1 == r1), rank_of_true1=rank_of_t1,
                spearman=spearman(true_c, rec_c), face_in_top=int(IS_FACE[list(r)].sum()))


def one_network(rng, sig_w=SIG_W, q_face=Q_FACE, q_other=Q_OTHER, miss_rates=MISS_RATES, same_rate=True):
    A = make_true(rng, sig_w)
    jit = rng.random(N) * 1e-6          # 同点を分けるための小さな値（本当と記録で同じものを使う）
    deg_t, bc_t = A.sum(1).astype(float), betweenness(A)
    out = {"mean_deg": A.sum(1).mean(), "face_top_true_deg": int(IS_FACE[list(top_set(deg_t, jit))].sum()),
           "face_top_true_bc": int(IS_FACE[list(top_set(bc_t, jit))].sum())}
    for m in miss_rates:
        R = record(rng, A, np.full((N, N), 1 - m))
        out[f"rand_{m}"] = {"deg": compare(deg_t, R.sum(1).astype(float), jit),
                            "bc": compare(bc_t, betweenness(R), jit)}
    Q = q_matrix(q_face, q_other)
    R = record(rng, A, Q)
    kept = R.sum() / A.sum()
    out["kept_share"] = kept
    deg_r = R.sum(1).astype(float)
    deg_ht = (R / Q).sum(1)                       # 記録に残る確率で割り戻したつながりの数
    out["sys"] = {"deg": compare(deg_t, deg_r, jit), "bc": compare(bc_t, betweenness(R), jit),
                  "deg_ht": compare(deg_t, deg_ht, jit)}
    if not same_rate:
        return out, (A, R, deg_t, bc_t, deg_r, deg_ht, jit)
    R2 = record(rng, A, np.full((N, N), kept))   # 同じ割合だけでたらめに漏れたとき
    out["sys_same_rate_random"] = {"deg": compare(deg_t, R2.sum(1).astype(float), jit),
                                   "bc": compare(bc_t, betweenness(R2), jit)}
    return out, (A, R, deg_t, bc_t, deg_r, deg_ht, jit)


def agg(runs, path):
    vals = {}
    for r in runs:
        d = r
        for p in path:
            d = d[p]
        for k, v in d.items():
            vals.setdefault(k, []).append(v)
    return {k: round(float(np.mean(v)), 4 if k == "spearman" else 3) for k, v in vals.items()}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    runs = [one_network(rng)[0] for _ in range(REPS)]
    res = {"N": N, "reps": REPS, "top": TOP,
           "params": {"n_dept": N_DEPT, "per_dept": PER, "face_depts": [d + 1 for d in FACE], "sig_w": SIG_W,
                      "c_in": C_IN, "c_out": C_OUT, "q_face": Q_FACE, "q_other": Q_OTHER, "grid_reps": GRID_REPS},
           "mean_degree_true": round(float(np.mean([r["mean_deg"] for r in runs])), 2),
           "face_share_people_pct": round(IS_FACE.mean() * 100, 2),
           "face_in_true_top_deg": round(float(np.mean([r["face_top_true_deg"] for r in runs])), 3),
           "face_in_true_top_bc": round(float(np.mean([r["face_top_true_bc"] for r in runs])), 3)}

    # ① でたらめに漏れる
    rows = []
    for m in MISS_RATES:
        for meas, lab in [("deg", "つながりの数"), ("bc", "間に立つ度合い")]:
            a = agg(runs, [f"rand_{m}", meas])
            rows.append(dict(missing_pct=int(m * 100), measure=lab, top10_overlap=a["overlap"],
                             same_top1_pct=round(a["same_top1"] * 100, 2), rank_of_true1=a["rank_of_true1"],
                             spearman=a["spearman"], face_in_top10=a["face_in_top"]))
    rnd = pd.DataFrame(rows)
    rnd.to_csv(RES / "random_missing.csv", index=False)
    res["random_missing"] = rows

    # 1位が上位10人から落ちる割合（でたらめに30%漏れ）
    res["rand30_true1_out_of_top10_pct"] = {
        meas: round(float(np.mean([r["rand_0.3"][meas]["rank_of_true1"] > TOP for r in runs])) * 100, 2)
        for meas in ("deg", "bc")}

    # ② 対面の多い部署で漏れる
    kept = float(np.mean([r["kept_share"] for r in runs]))
    res["sys_kept_share_pct"] = round(kept * 100, 2)
    rows2 = []
    for key, lab in [("sys_same_rate_random", "同じ割合だけでたらめに漏れる"), ("sys", "対面の多い3部署で漏れる")]:
        for meas, ml in [("deg", "つながりの数"), ("bc", "間に立つ度合い")]:
            a = agg(runs, [key, meas])
            rows2.append(dict(case=lab, measure=ml, top10_overlap=a["overlap"], same_top1_pct=round(a["same_top1"] * 100, 2),
                              spearman=a["spearman"], face_in_top10=a["face_in_top"]))
    a = agg(runs, ["sys", "deg_ht"])
    rows2.append(dict(case="対面の多い3部署で漏れる＋記録に残る確率で割り戻す", measure="つながりの数", top10_overlap=a["overlap"],
                      same_top1_pct=round(a["same_top1"] * 100, 2), spearman=a["spearman"], face_in_top10=a["face_in_top"]))
    sysd = pd.DataFrame(rows2)
    sysd.to_csv(RES / "systematic_missing.csv", index=False)
    res["systematic"] = rows2

    # 確かめ：やり取りの多さの振れ × 対面の多い部署の記録に残る確率（9通り）
    grid = []
    for sw in [0.3, 0.6, 0.9]:
        for qf in [0.2, 0.4, 0.6]:
            rr = [one_network(rng, sig_w=sw, q_face=qf, miss_rates=[0.3], same_rate=False)[0] for _ in range(GRID_REPS)]
            ad, ab, ah = agg(rr, ["sys", "deg"]), agg(rr, ["sys", "bc"]), agg(rr, ["sys", "deg_ht"])
            r3d, r3b = agg(rr, ["rand_0.3", "deg"]), agg(rr, ["rand_0.3", "bc"])
            grid.append(dict(sig_w=sw, q_face=qf,
                             kept_pct=round(float(np.mean([x["kept_share"] for x in rr])) * 100, 2),
                             face_true_top_deg=round(float(np.mean([x["face_top_true_deg"] for x in rr])), 3),
                             face_true_top_bc=round(float(np.mean([x["face_top_true_bc"] for x in rr])), 3),
                             sys_overlap_deg=ad["overlap"], sys_overlap_bc=ab["overlap"], sys_overlap_deg_ht=ah["overlap"],
                             sys_face_top_deg=ad["face_in_top"], sys_face_top_bc=ab["face_in_top"], sys_face_top_deg_ht=ah["face_in_top"],
                             rand30_overlap_deg=r3d["overlap"], rand30_overlap_bc=r3b["overlap"]))
    g = pd.DataFrame(grid)
    g.to_csv(RES / "grid_spread_qface.csv", index=False)
    res["grid"] = {
        "n": len(g),
        "rand30_overlap_deg_range": [g.rand30_overlap_deg.min(), g.rand30_overlap_deg.max()],
        "rand30_overlap_bc_range": [g.rand30_overlap_bc.min(), g.rand30_overlap_bc.max()],
        "sys_overlap_deg_range": [g.sys_overlap_deg.min(), g.sys_overlap_deg.max()],
        "sys_overlap_bc_range": [g.sys_overlap_bc.min(), g.sys_overlap_bc.max()],
        "sys_overlap_deg_ht_range": [g.sys_overlap_deg_ht.min(), g.sys_overlap_deg_ht.max()],
        "sys_face_top_bc_range": [g.sys_face_top_bc.min(), g.sys_face_top_bc.max()],
        "face_true_top_bc_range": [g.face_true_top_bc.min(), g.face_true_top_bc.max()],
        "sys_face_top_deg_range": [g.sys_face_top_deg.min(), g.sys_face_top_deg.max()],
        "sys_face_top_deg_ht_range": [g.sys_face_top_deg_ht.min(), g.sys_face_top_deg_ht.max()],
        "face_true_top_deg_range": [g.face_true_top_deg.min(), g.face_true_top_deg.max()],
        "n_ht_face_above_true": int((g.sys_face_top_deg_ht > g.face_true_top_deg).sum()),
        "kept_pct_range": [g.kept_pct.min(), g.kept_pct.max()],
        "n_ht_better_than_raw_deg": int((g.sys_overlap_deg_ht > g.sys_overlap_deg).sum()),
        "n_bc_below_deg_rand30": int((g.rand30_overlap_bc < g.rand30_overlap_deg).sum()),
    }

    # 例の1つ（データとして置く）
    ex, (A, R, deg_t, bc_t, deg_r, deg_ht, jit) = one_network(np.random.default_rng(SEED + 1))
    bc_r = betweenness(R)
    res["check_betweenness_same_as_plain_within_1e-6"] = bool(np.abs(betweenness_plain(A) - bc_t).max() < 1e-6)
    pd.DataFrame(dict(person_id=np.arange(N) + 1, dept=DEPT + 1, face_dept=IS_FACE.astype(int),
                      degree_true=deg_t.astype(int), degree_recorded=deg_r.astype(int),
                      degree_reweighted=np.round(deg_ht, 3),
                      between_true=np.round(bc_t, 3), between_recorded=np.round(bc_r, 3))).to_csv(
        DATA / "people_example.csv", index=False)
    iu = np.triu_indices(N, 1)
    has = A[iu]
    pd.DataFrame(dict(person_a=iu[0][has] + 1, person_b=iu[1][has] + 1, recorded=R[iu][has].astype(int))).to_csv(
        DATA / "links_example.csv", index=False)
    res["example"] = {"n_links_true": int(has.sum()), "n_links_recorded": int(R[iu].sum()),
                      "sys_bc_overlap": ex["sys"]["bc"]["overlap"], "sys_deg_overlap": ex["sys"]["deg"]["overlap"],
                      "sys_bc_face_in_top": ex["sys"]["bc"]["face_in_top"],
                      "true_bc_face_in_top": ex["face_top_true_bc"]}

    # 図1：でたらめに漏れたときの上位10人の残り方
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    for meas, col, mk in [("つながりの数", BLUE, "o"), ("間に立つ度合い", ORANGE, "s")]:
        d = rnd[rnd.measure == meas]
        ax.plot(d.missing_pct, d.top10_overlap, mk + "-", color=col, label=f"{meas}の上位10人")
        for x_, y_ in zip(d.missing_pct, d.top10_overlap):
            ax.text(x_, y_ + (0.35 if meas == "つながりの数" else -0.7), f"{y_:.2f}", ha="center", fontsize=8, color=col)
    ax.set_ylim(0, 10.5); ax.set_xlim(5, 55)
    ax.set_xlabel("記録に残らなかったつながりの割合（%、でたらめに漏れる）")
    ax.text(54, 10.2, "縦軸：本当の上位10人のうち、記録でも上位10人に入った人数", ha="right", va="top", fontsize=8.5, color=GRAY)
    ax.set_ylabel("上位10人に残った人数")
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("でたらめに漏れても、間に立つ度合いの上位は入れかわりやすい")
    save(fig, "a1081_random_missing.png", SRC + f"。{REPS}社の平均", y=-0.04)

    # 図2：対面の多い部署で漏れるとき（上位10人のうち対面の多い部署の人数）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    labs = ["本当のつながり", "同じ割合だけ\nでたらめに漏れる", "対面の多い3部署で\n漏れる", "記録に残る確率で\n割り戻す"]
    vd = [res["face_in_true_top_deg"],
          sysd[(sysd.case == "同じ割合だけでたらめに漏れる") & (sysd.measure == "つながりの数")].face_in_top10.iloc[0],
          sysd[(sysd.case == "対面の多い3部署で漏れる") & (sysd.measure == "つながりの数")].face_in_top10.iloc[0],
          sysd[sysd.case.str.contains("割り戻す")].face_in_top10.iloc[0]]
    vb = [res["face_in_true_top_bc"],
          sysd[(sysd.case == "同じ割合だけでたらめに漏れる") & (sysd.measure == "間に立つ度合い")].face_in_top10.iloc[0],
          sysd[(sysd.case == "対面の多い3部署で漏れる") & (sysd.measure == "間に立つ度合い")].face_in_top10.iloc[0],
          np.nan]
    x = np.arange(4)
    ax.bar(x - 0.2, vd, width=0.4, color=BLUE, label="つながりの数の上位10人")
    ax.bar(x + 0.2, vb, width=0.4, color=ORANGE, label="間に立つ度合いの上位10人")
    for xi, v in zip(x - 0.2, vd):
        ax.text(xi, v + 0.08, f"{v:.2f}", ha="center", fontsize=8.5)
    for xi, v in zip(x + 0.2, vb):
        if not np.isnan(v):
            ax.text(xi, v + 0.08, f"{v:.2f}", ha="center", fontsize=8.5)
    ax.text(3.02, 0.1, "間に立つ度合いは\n割り戻せない", ha="left", va="bottom", fontsize=7.5, color=GRAY)
    ax.set_xticks(x); ax.set_xticklabels(labs, fontsize=9)
    ax.set_ylim(0, 4.5); ax.set_ylabel("上位10人のうち、対面の多い3部署の人数")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("漏れが部署で偏ると、その部署の人が上位から消える")
    save(fig, "a1081_face_depts.png", SRC + f"。{REPS}社の平均。対面の多い3部署は社員の30%", y=-0.03)

    # 図3：確かめ（9通り、対面の多い部署で漏れるときの上位10人の重なり）
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    lab = [f"振れ{a:g}・対面の部署の記録{int(b * 100)}%" for a, b in zip(g.sig_w, g.q_face)]
    y = np.arange(len(g))[::-1]
    ax.scatter(g.sys_overlap_deg, y, color=BLUE, s=24, label="つながりの数", zorder=3)
    ax.scatter(g.sys_overlap_bc, y, color=ORANGE, s=24, marker="s", label="間に立つ度合い", zorder=3)
    ax.scatter(g.sys_overlap_deg_ht, y, color=GREEN, s=30, marker="^", label="つながりの数（割り戻し）", zorder=3)
    ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=8.5)
    ax.set_xlim(0, 10); ax.set_xlabel("本当の上位10人のうち、記録でも上位10人に入った人数（各40社の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    ax.set_title("置き方9通り（振れ：やり取りの多さの人ごとの振れ）", fontsize=11)
    save(fig, "a1081_robust.png", SRC, y=-0.02)

    with open(RES / "a1081_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps(res, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
