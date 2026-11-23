"""1082 似た人どうしがつながっているのは、影響しあったからか、もとから似ていたからか？（架空のデータ）

架空の趣味の会（会員1,500人）。会員ごとに「道具の好み」（手作りの道具が好きか、買った道具が好きか）の本当の値を置く。
3つの会を作る：
  S 会：もとから似ていた（好みの近い人どうしがつながる。つながった人の好みは互いに動かさない）
  I 会：影響しあった（つながりはでたらめ。つながった人の好みに毎年少し寄っていく）
  M 会：両方が半分ずつ
どの会でも、つながりは毎年1割が切れて、同じ数だけ新しくできる。好みは毎年少し変わる。
年1回の調査で好みを点数で聞く（聞き取りの誤差あり）。
1回の調査、2回の調査（好みの変化を友だちの好みで説明する回帰）、新しくできたつながりの「つながる前」の似かたで、
3つの会を見分けられるかを数える。
"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1082
SRC = "架空の趣味の会（作成者が乱数で作成、seed 1082）"
N = 1500
MEAN_DEG = 6
E = N * MEAN_DEG // 2      # つながりの本数（4,500本）
GROUP = 10                 # 班（10人ずつ、150班）
P_IN = 0.8                 # 新しいつながりの相手を同じ班から探す確率
YEARS = 30                 # 調査の前に回す年数
TURN = 0.05                # 毎年切れて入れかわるつながりの割合
A_KEEP = 0.97               # 好みが前の年から引き継がれる度合い
ETA = np.sqrt(1 - A_KEEP ** 2)   # 毎年の好みの変わり方（標準偏差）
SIG_E = 0.5                # 調査の聞き取りの誤差（標準偏差）
WORLDS = {                 # 選び方の強さ h（小さいほど似た人を選ぶ。None はでたらめ）と、寄っていく強さ beta
    "S": dict(h=0.5, beta=0.0, label="もとから似ていた会"),
    "I": dict(h=None, beta=0.2, label="影響しあった会"),
    "M": dict(h=0.8, beta=0.1, label="両方が半分ずつの会"),
}
REPS = 100
GRID_REPS = 30


def pick_pairs(rng, z, k, h):
    """k 本の新しいつながりを引く。h が None ならでたらめ、そうでなければ好みの差で選ぶ（差が小さいほど選ばれやすい）"""
    out = []
    need = k
    while need > 0:
        m = max(need * 6, 200)
        i = rng.integers(0, N, m)
        inside = rng.random(m) < P_IN
        j_in = (i // GROUP) * GROUP + rng.integers(0, GROUP, m)
        j = np.where(inside, j_in, rng.integers(0, N, m))
        ok = i != j
        if h is not None:
            ok &= rng.random(m) < np.exp(-((z[i] - z[j]) ** 2) / (2 * h * h))
        i, j = i[ok][:need], j[ok][:need]
        out.append(np.stack([i, j], 1)); need -= len(i)
    return np.concatenate(out)


def friend_mean(edges, v):
    s = np.bincount(edges[:, 0], v[edges[:, 1]], N) + np.bincount(edges[:, 1], v[edges[:, 0]], N)
    c = np.bincount(edges[:, 0], minlength=N) + np.bincount(edges[:, 1], minlength=N)
    return np.where(c > 0, s / np.maximum(c, 1), np.nan), c


def simulate(rng, h, beta, sig_e=SIG_E, keep=False):
    z = rng.normal(0, 1, N)
    edges = pick_pairs(rng, z, E, h)
    born = np.zeros(E, int)
    hist = {}
    for t in range(1, YEARS + 2):
        m, c = friend_mean(edges, z)
        pull = np.where(c > 0, m - z, 0.0)
        z = A_KEEP * z + beta * pull + rng.normal(0, ETA, N)
        drop = rng.random(len(edges)) < TURN
        new = pick_pairs(rng, z, int(drop.sum()), h)
        edges = np.concatenate([edges[~drop], new]); born = np.concatenate([born[~drop], np.full(len(new), t)])
        if t == YEARS:
            hist["z1"] = z.copy(); hist["edges1"] = edges.copy(); hist["born1"] = born.copy()
    z2 = z
    sd = hist["z1"].std()                     # 聞き取りの誤差は、好みのばらつきの sig_e 倍
    x1 = hist["z1"] + rng.normal(0, sig_e * sd, N)
    x2 = z2 + rng.normal(0, sig_e * sd, N)
    e1 = hist["edges1"]
    # ① 1回の調査：1回目の調査の時点でつながっている2人の好みの相関
    r_snap = np.corrcoef(x1[e1[:, 0]], x1[e1[:, 1]])[0, 1]
    # ② 2回の調査：好みの変化を、自分の1回目の点数と、1回目の友だちの点数の平均で説明する回帰
    fm, c = friend_mean(e1, x1)
    ok = c > 0
    X = np.column_stack([np.ones(ok.sum()), x1[ok], fm[ok]])
    coef = np.linalg.lstsq(X, (x2 - x1)[ok], rcond=None)[0]
    # ③ 1回目と2回目の調査の間に新しくできたつながり：つながる前（1回目）の点数の相関
    newe = edges[born == YEARS + 1]
    r_new_before = np.corrcoef(x1[newe[:, 0]], x1[newe[:, 1]])[0, 1]
    r_new_after = np.corrcoef(x2[newe[:, 0]], x2[newe[:, 1]])[0, 1]
    # 本当の好みでの相関（調査の誤差なし）
    r_true = np.corrcoef(hist["z1"][e1[:, 0]], hist["z1"][e1[:, 1]])[0, 1]
    out = dict(r_snap=r_snap, coef_friend=coef[2], coef_self=coef[1], r_new_before=r_new_before,
               r_new_after=r_new_after, r_true=r_true, n_new=len(newe), sd_z=hist["z1"].std())
    if keep:
        out["_d"] = (x1, x2, e1, newe, hist["born1"])
    return out


def agg(runs, key):
    v = np.array([r[key] for r in runs])
    return dict(mean=round(float(v.mean()), 3), p10=round(float(np.percentile(v, 10)), 3),
                p90=round(float(np.percentile(v, 90)), 3))


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    res = {"N": N, "links": E, "reps": REPS, "sig_e": SIG_E, "params": {
        "group_size": GROUP, "p_in_group": P_IN, "years_before_survey1": YEARS, "turnover": TURN,
        "keep": A_KEEP, "eta_sd": round(float(ETA), 3)}, "worlds": {}}
    rows = []
    base = {}
    for w, p in WORLDS.items():
        runs = [simulate(rng, p["h"], p["beta"]) for _ in range(REPS)]
        base[w] = runs
        d = {k: agg(runs, k) for k in ["r_snap", "r_true", "coef_friend", "coef_self", "r_new_before", "r_new_after"]}
        d["n_new_mean"] = round(float(np.mean([r["n_new"] for r in runs])), 1)
        d["sd_true_pref"] = round(float(np.mean([r["sd_z"] for r in runs])), 3)
        d["label"] = p["label"]; d["h"] = p["h"]; d["beta"] = p["beta"]
        res["worlds"][w] = d
        rows.append(dict(world=p["label"], h=p["h"], beta=p["beta"],
                         snap_corr=d["r_snap"]["mean"], snap_corr_p10=d["r_snap"]["p10"], snap_corr_p90=d["r_snap"]["p90"],
                         friend_coef=d["coef_friend"]["mean"], friend_coef_p10=d["coef_friend"]["p10"], friend_coef_p90=d["coef_friend"]["p90"],
                         new_before_corr=d["r_new_before"]["mean"], new_before_p10=d["r_new_before"]["p10"], new_before_p90=d["r_new_before"]["p90"],
                         new_after_corr=d["r_new_after"]["mean"]))
    pd.DataFrame(rows).to_csv(RES / "three_worlds.csv", index=False)

    # 確かめ1：聞き取りの誤差の大きさ（3つの会 × 誤差4通り）
    g1 = []
    for se in [0.0, 0.25, 0.5, 0.8]:
        for w, p in WORLDS.items():
            rr = [simulate(rng, p["h"], p["beta"], sig_e=se) for _ in range(GRID_REPS)]
            g1.append(dict(sig_e=se, world=p["label"], snap_corr=agg(rr, "r_snap")["mean"],
                           friend_coef=agg(rr, "coef_friend")["mean"], new_before_corr=agg(rr, "r_new_before")["mean"]))
    g1 = pd.DataFrame(g1)
    g1.to_csv(RES / "grid_measurement_error.csv", index=False)
    s_only = g1[g1.world == WORLDS["S"]["label"]]
    i_only = g1[g1.world == WORLDS["I"]["label"]]
    res["grid_error"] = {
        "S_friend_coef_by_err": dict(zip(s_only.sig_e.astype(str), s_only.friend_coef)),
        "I_friend_coef_by_err": dict(zip(i_only.sig_e.astype(str), i_only.friend_coef)),
        "n_S_coef_below_I": int(sum(a < b for a, b in zip(s_only.friend_coef, i_only.friend_coef))),
        "n_S_coef_above_I": int(sum(a > b for a, b in zip(s_only.friend_coef, i_only.friend_coef))),
    }

    # 確かめ2：選び方の強さと寄っていく強さを変える（S会の h、I会の beta、各3通り）
    g2 = []
    for h in [0.35, 0.5, 0.8]:
        rr = [simulate(rng, h, 0.0) for _ in range(GRID_REPS)]
        g2.append(dict(world=WORLDS["S"]["label"], h=h, beta=0.0, snap_corr=agg(rr, "r_snap")["mean"],
                       friend_coef=agg(rr, "coef_friend")["mean"], new_before_corr=agg(rr, "r_new_before")["mean"]))
    for b in [0.1, 0.2, 0.3]:
        rr = [simulate(rng, None, b) for _ in range(GRID_REPS)]
        g2.append(dict(world=WORLDS["I"]["label"], h=None, beta=b, snap_corr=agg(rr, "r_snap")["mean"],
                       friend_coef=agg(rr, "coef_friend")["mean"], new_before_corr=agg(rr, "r_new_before")["mean"]))
    g2 = pd.DataFrame(g2)
    g2.to_csv(RES / "grid_strength.csv", index=False)
    gs, gi = g2[g2.beta == 0], g2[g2.beta > 0]
    res["grid_strength"] = {
        "S_snap_range": [gs.snap_corr.min(), gs.snap_corr.max()],
        "S_new_before_range": [gs.new_before_corr.min(), gs.new_before_corr.max()],
        "S_friend_coef_range": [gs.friend_coef.min(), gs.friend_coef.max()],
        "I_snap_range": [gi.snap_corr.min(), gi.snap_corr.max()],
        "I_new_before_range": [gi.new_before_corr.min(), gi.new_before_corr.max()],
        "I_friend_coef_range": [gi.friend_coef.min(), gi.friend_coef.max()],
    }

    # 例の1回（S会、データとして置く）
    ex = simulate(np.random.default_rng(SEED + 1), WORLDS["S"]["h"], 0.0, keep=True)
    x1, x2, e1, newe, born1 = ex["_d"]
    pd.DataFrame(dict(member_id=np.arange(N) + 1, score_survey1=np.round(x1, 3), score_survey2=np.round(x2, 3))).to_csv(
        DATA / "members_example_S.csv", index=False)
    lk = pd.DataFrame(dict(member_a=np.concatenate([e1[:, 0], newe[:, 0]]) + 1,
                           member_b=np.concatenate([e1[:, 1], newe[:, 1]]) + 1,
                           kind=["調査1の時点" ] * len(e1) + ["調査1と2の間に新しく"] * len(newe)))
    lk.to_csv(DATA / "links_example_S.csv", index=False)
    res["example_S"] = {k: round(float(ex[k]), 3) for k in ["r_snap", "coef_friend", "r_new_before"]}

    # 図1：3つの物差しで3つの会を比べる
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 4.0), sharey=False)
    labs = [WORLDS[w]["label"].replace("の会", "\n会").replace("会", "会") for w in WORLDS]
    labs = ["もとから\n似ていた", "影響\nしあった", "両方が\n半分ずつ"]
    cols = [ORANGE, BLUE, GREEN]
    items = [("r_snap", "①1回の調査：\nつながった2人の好みの相関", (0, 0.6)),
             ("coef_friend", "②2回の調査：好みの変化を\n友だちの好みで説明した係数", (0, 0.4)),
             ("r_new_before", "③新しくつながった2人の\nつながる前の好みの相関", (0, 0.7))]
    for ax, (k, title, yl) in zip(axes, items):
        m = [res["worlds"][w][k]["mean"] for w in WORLDS]
        lo = [res["worlds"][w][k]["p10"] for w in WORLDS]; hi = [res["worlds"][w][k]["p90"] for w in WORLDS]
        x = np.arange(3)
        ax.bar(x, m, color=cols, width=0.6)
        ax.errorbar(x, m, yerr=[np.array(m) - lo, np.array(hi) - m], fmt="none", ecolor=INK, lw=1, capsize=3)
        for xi, v, hh in zip(x, m, hi):
            ax.text(xi, max(v, hh) + yl[1] * 0.03, f"{v:.3f}", ha="center", fontsize=8.5)
        ax.axhline(0, color=INK, lw=0.8)
        ax.set_xticks(x); ax.set_xticklabels(labs, fontsize=8.5)
        ax.set_ylim(min(0, min(lo) * 1.3), yl[1]); ax.set_title(title, fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.suptitle("1回の調査では見分けられず、②はもとから似ていた会でも正になる", fontsize=12, y=0.99)
    save(fig, "a1082_three_tests.png", SRC + f"。各{REPS}回の平均、線は10〜90%の範囲。聞き取りの誤差は好みのばらつきの0.5倍", y=-0.02)

    # 図2：聞き取りの誤差と、②の係数
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    for w, col, mk in [("S", ORANGE, "o"), ("I", BLUE, "s"), ("M", GREEN, "^")]:
        d = g1[g1.world == WORLDS[w]["label"]]
        ax.plot(d.sig_e, d.friend_coef, mk + "-", color=col, label=WORLDS[w]["label"])
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xlabel("調査の聞き取りの誤差（本当の好みのばらつき（標準偏差）の何倍か）")
    ax.set_ylabel("②の係数（友だちの好み）")
    ax.set_ylim(min(0, g1.friend_coef.min() - 0.02), max(0.25, g1.friend_coef.max() + 0.03))
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("聞き取りの誤差が大きいほど、もとから似ていた会でも「影響」が出る")
    save(fig, "a1082_error.png", SRC + f"。各{GRID_REPS}回の平均", y=-0.04)

    # 図3：確かめ（選び方・寄っていく強さ）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    lab = [f"もとから似ていた：h={h:g}" if b == 0 else f"影響しあった：β={b:g}" for h, b in zip(g2.h, g2.beta)]
    y = np.arange(len(g2))[::-1]
    ax.barh(y + 0.2, g2.snap_corr, height=0.4, color=GRAY, label="①1回の調査の相関")
    ax.barh(y - 0.2, g2.new_before_corr, height=0.4, color=ORANGE, label="③つながる前の相関")
    ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=8.5)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_xlim(min(0, g2.new_before_corr.min() - 0.03), 0.8); ax.set_xlabel(f"相関（各{GRID_REPS}回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("強さを変えても、③は「もとから似ていた」ときだけ大きい", fontsize=11)
    save(fig, "a1082_robust.png", SRC + "。h：小さいほど好みの近い人を選ぶ、β：友だちに寄る強さ", y=-0.03)

    with open(RES / "a1082_main.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps(res, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
