"""1056 A のあとに B を測る順番を固定すると、何が差にまざるのか？（架空のデータ）

架空のアプリの処理 A と B の処理時間（ミリ秒）を、作成者が置いた決まりで乱数から作る。
- A・B それぞれの本来の処理時間と、次の回にまわる「後片付け」の時間（A のほうが多く残す）
- 測っているあいだに機械がだんだん遅くなる分（直線）と、混み具合のゆっくりした揺れ
- 1回ごとの振れ
1回の計測は A・B 50回ずつ（計100回）。並べ方（ブロック・交互・でたらめ・往復）ごとに、
測った差（B の平均−A の平均）が本当の差からどれだけずれるかと、その中身を数える。実機の計測はしていない。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1056
SRC = "架空のアプリの処理時間（作成者が置いた分布からの乱数、seed 1056）"
N_EACH = 50
N = 2 * N_EACH
SESS = 10000
BASE = {"work_A": 96.0, "work_B": 95.0, "clean_A": 4.0, "clean_B": 2.0, "drift_total": 4.0,
        "ar_sd": 2.0, "ar_phi": 0.95, "noise_sd": 0.04}
DESIGNS = ["①ブロック（A50回→B50回）", "②交互（ABAB…、いつもAが先）", "③全体をでたらめに並べる", "④往復（A25回→B50回→A25回）"]
SHORT = ["①ブロック", "②交互", "③でたらめ", "④往復"]


def r(x, d=4):
    return round(float(x), d)


def orders(rng, k):
    """並べ方ごとの順番（0=A, 1=B）。③はセッションごとにでたらめ"""
    blk = np.r_[np.zeros(N_EACH), np.ones(N_EACH)].astype(int)
    alt = np.tile([0, 1], N_EACH)
    rt = np.r_[np.zeros(N_EACH // 2), np.ones(N_EACH), np.zeros(N_EACH // 2)].astype(int)
    rnd = np.argsort(rng.random((k, N)), axis=1) >= N_EACH
    return [np.tile(blk, (k, 1)), np.tile(alt, (k, 1)), rnd.astype(int), np.tile(rt, (k, 1))]


def run_times(rng, order, kw, drift=True, carry=True, ar=True, noise=True):
    """order: (k, N) の 0/1。戻り値は (k, N) の処理時間"""
    k = order.shape[0]
    work = np.where(order == 1, kw["work_B"], kw["work_A"])
    clean = np.where(order == 1, kw["clean_B"], kw["clean_A"])
    # 前の回が残した後片付けを払う。最初の回は、同じ処理の慣らしの1回が前にあったとみなす
    prev_clean = np.concatenate([clean[:, :1], clean[:, :-1]], axis=1)
    pay = prev_clean if carry else clean
    base = work + pay
    sd = kw["noise_sd"]
    mult = np.exp(rng.normal(-sd ** 2 / 2, sd, (k, N))) if noise else 1.0
    t = base * mult
    if drift:
        t = t + kw["drift_total"] * np.arange(N) / (N - 1)
    if ar and kw["ar_sd"] > 0:
        e = rng.normal(0, kw["ar_sd"] * np.sqrt(1 - kw["ar_phi"] ** 2), (k, N))
        s = np.zeros((k, N))
        s[:, 0] = rng.normal(0, kw["ar_sd"], k)
        for i in range(1, N):
            s[:, i] = kw["ar_phi"] * s[:, i - 1] + e[:, i]
        t = t + s
    return t


def diff(order, t):
    b = (t * order).sum(1) / N_EACH
    a = (t * (1 - order)).sum(1) / N_EACH
    return b - a


def true_diff(kw):
    return (kw["work_B"] + kw["clean_B"]) - (kw["work_A"] + kw["clean_A"])


def formula_bias(kw):
    """期待値の式：①②④は順番が決まっているので、だんだん遅くなる分と持ちこしの分を順番から直接足す。
    ③は前の回が A か B かがほぼ半々（49/99 と 50/99）になる式"""
    out = []
    pos = np.arange(N)
    seqs = orders(np.random.default_rng(0), 1)
    cA, cB = kw["clean_A"], kw["clean_B"]
    for j, o in enumerate(seqs):
        o = o[0]
        if j == 2:
            d_drift = 0.0
            d_carry = (cA - cB) * N / (N - 1)
        else:
            clean = np.where(o == 1, cB, cA)
            prev = np.r_[clean[:1], clean[:-1]]
            d_carry = ((prev - clean) * o).sum() / N_EACH - ((prev - clean) * (1 - o)).sum() / N_EACH
            dr = kw["drift_total"] * pos / (N - 1)
            d_drift = (dr * o).sum() / N_EACH - (dr * (1 - o)).sum() / N_EACH
        out.append({"drift": d_drift, "carry": d_carry, "total": d_drift + d_carry})
    return out


def evaluate(rng, kw, k=SESS):
    td = true_diff(kw)
    res = []
    for j, o in enumerate(orders(rng, k)):
        d = diff(o, run_times(rng, o, kw))
        res.append({"design": DESIGNS[j], "mean_diff": d.mean(), "bias": d.mean() - td, "sd_diff": d.std(),
                    "p_B_faster": (d < 0).mean(), "p_wrong_dir": ((d > 0) if td < 0 else (d < 0)).mean()})
    return res


def main():
    rng = np.random.default_rng(SEED)
    kw = BASE
    td = true_diff(kw)

    # 1回分の計測（data）
    rows = []
    rr = np.random.default_rng(SEED + 1)
    for j, o in enumerate(orders(rr, 1)):
        t = run_times(rr, o, kw)[0]
        for i in range(N):
            rows.append({"design": SHORT[j], "position": i + 1, "method": "AB"[o[0][i]], "ms": round(float(t[i]), 3)})
    one = pd.DataFrame(rows)
    one.to_csv(DATA / "one_session_runs.csv", index=False)

    # 1) 基本：並べ方ごと
    base = pd.DataFrame(evaluate(rng, kw))
    # 2) 中身を分ける：しくみを1つずつ入れる
    comp = []
    for name, flags in [("1回ごとの振れだけ", dict(drift=False, carry=False, ar=False)),
                        ("＋だんだん遅くなる", dict(drift=True, carry=False, ar=False)),
                        ("＋後片付けの持ちこし", dict(drift=False, carry=True, ar=False)),
                        ("＋混み具合の揺れ", dict(drift=False, carry=False, ar=True)),
                        ("全部", dict(drift=True, carry=True, ar=True))]:
        for j, o in enumerate(orders(rng, SESS)):
            d = diff(o, run_times(rng, o, kw, **flags))
            comp.append({"parts": name, "design": DESIGNS[j], "bias": r(d.mean() - td), "sd_diff": r(d.std()),
                         "p_B_faster": r((d < 0).mean())})
    comp = pd.DataFrame(comp)
    comp.to_csv(RES / "components.csv", index=False)
    fb = formula_bias(kw)

    # 3) A と B が同じ処理のとき（本当の差0）
    same = dict(kw, work_B=kw["work_A"], clean_A=3.0, clean_B=3.0)
    same_res = pd.DataFrame(evaluate(rng, same))
    same_res["p_B_slower_by_1ms"] = None
    for j, o in enumerate(orders(rng, SESS)):
        d = diff(o, run_times(rng, o, same))
        same_res.loc[j, "p_B_slower_by_1ms"] = r((d > 1.0).mean())

    # 4) 置き方を変えると（27通り）：だんだん遅くなる量 × 持ちこしの差 × 揺れの大きさ（本当の差は −3ms のまま）
    grid = []
    gi = 0
    for D in [0.0, 4.0, 8.0]:
        for cd in [0.0, 2.0, 4.0]:
            for ars in [0.0, 2.0, 4.0]:
                cA, cB = 3 + cd / 2, 3 - cd / 2
                g = dict(kw, drift_total=D, clean_A=cA, clean_B=cB, ar_sd=ars)
                g["work_B"] = g["work_A"] + cA - cB - 3.0
                ev = evaluate(np.random.default_rng(SEED * 100 + gi), g, 3000)
                gi += 1
                for e in ev:
                    grid.append({"drift_total": D, "carry_diff": cd, "ar_sd": ars, "design": e["design"],
                                 "bias": r(e["bias"]), "sd_diff": r(e["sd_diff"]), "p_B_faster": r(e["p_B_faster"])})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)

    base_out = base.copy()
    for c in ["mean_diff", "bias", "sd_diff", "p_B_faster", "p_wrong_dir"]:
        base_out[c] = base_out[c].map(lambda v: r(v))
    base_out.to_csv(RES / "designs_base.csv", index=False)
    gs = grid.groupby("design", sort=False).agg(bias_min=("bias", "min"), bias_max=("bias", "max"),
                                                 p_min=("p_B_faster", "min"), p_max=("p_B_faster", "max"))
    # 往復で残る：混み具合の揺れ（直線でない動き）
    rt_ar = grid[(grid.design == DESIGNS[3])]
    alt0 = grid[(grid.design == DESIGNS[1]) & (grid.carry_diff == 0)]

    out = {"base_setting": BASE, "n_each": N_EACH, "sessions": SESS, "grid_sessions": 3000, "true_diff_ms": td,
           "true_A_ms": kw["work_A"] + kw["clean_A"], "true_B_ms": kw["work_B"] + kw["clean_B"],
           "designs_base": base_out.to_dict("records"),
           "formula_bias": [{"design": DESIGNS[j], **{k: r(v) for k, v in f.items()}} for j, f in enumerate(fb)],
           "components": comp.to_dict("records"),
           "same_code": same_res.assign(**{c: same_res[c].map(lambda v: r(v)) for c in
                                           ["mean_diff", "bias", "sd_diff", "p_B_faster", "p_wrong_dir"]}).to_dict("records"),
           "grid_ranges_by_design": {d: {k: r(v) for k, v in gs.loc[d].items()} for d in DESIGNS},
           "grid_roundtrip_p_B_faster_when_ar4": [r(rt_ar[rt_ar.ar_sd == 4].p_B_faster.min()),
                                                  r(rt_ar[rt_ar.ar_sd == 4].p_B_faster.max())],
           "grid_alternating_when_carry0_p_B_faster": [r(alt0.p_B_faster.min()), r(alt0.p_B_faster.max())],
           "grid_alternating_when_carry0_bias": [r(alt0.bias.min()), r(alt0.bias.max())],
           "grid_sd_diff_ar4": {d: r(grid[(grid.design == d) & (grid.ar_sd == 4)].sd_diff.mean(), 3) for d in DESIGNS},
           "headline": {"true_diff_ms": td,
                        **{f"bias_{SHORT[j]}": r(base.bias[j], 2) for j in range(4)},
                        **{f"mean_diff_{SHORT[j]}": r(base.mean_diff[j], 2) for j in range(4)},
                        **{f"p_B_faster_pct_{SHORT[j]}": r(base.p_B_faster[j] * 100, 1) for j in range(4)},
                        "same_block_p_B_slower_1ms_pct": r(same_res.p_B_slower_by_1ms[0] * 100, 1),
                        "same_block_mean_diff": r(same_res.mean_diff[0], 2)}}
    json.dump(out, open(RES / "a1056_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の計測（①ブロック と ②交互）
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.8), sharey=True)
    for ax, j in zip(axes, [0, 1]):
        s = one[one.design == SHORT[j]]
        for m, c in [("A", BLUE), ("B", ORANGE)]:
            q = s[s.method == m]
            ax.scatter(q.position, q.ms, s=12, color=c, label=f"{m}（本当は{out['true_' + m + '_ms']:.0f}ms）")
            ax.axhline(q.ms.mean(), color=c, lw=1.2, ls="--")
        ax.set_title(DESIGNS[j], fontsize=11)
        ax.set_xlabel("測った順番（回目）")
        ax.set_ylim(80, 120)
    axes[0].set_ylabel("処理時間（ms）")
    axes[0].legend(frameon=False, fontsize=8.5, loc="upper left")
    fig.suptitle("Bのほうが3ms速いのに、ブロックでは差が縮み、交互では逆になった（1回分、点線は平均）", fontsize=12, y=1.03)
    save(fig, "a1056_one_session.png", SRC)

    # 図2：ずれの中身（しくみを1つずつ入れたときのずれ）
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    parts = ["＋だんだん遅くなる", "＋後片付けの持ちこし", "＋混み具合の揺れ", "全部"]
    cols = [ORANGE, GREEN, GRAY, INK]
    w = 0.2
    y = np.arange(4)
    for i, (p, c) in enumerate(zip(parts, cols)):
        v = [comp[(comp.parts == p) & (comp.design == d)].bias.iloc[0] for d in DESIGNS]
        ax.barh(y + (i - 1.5) * w, v, w, color=c, label=p.replace("＋", ""))
        for yy, vv in zip(y + (i - 1.5) * w, v):
            ax.text(max(vv, 0) + 0.05, yy, "0.00" if abs(vv) < 0.005 else f"{vv:+.2f}", va="center", ha="left",
                    fontsize=7.5)
    ax.axvline(0, color=INK, lw=.8)
    ax.set_yticks(y, SHORT); ax.invert_yaxis()
    ax.set_xlim(-0.5, 5.5)
    ax.set_xlabel("測った差（B−A）の本当の差（−3ms）からのずれ（ms、1万回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("ブロックには遅くなる分が、交互には後片付けの分が2倍でまざる")
    save(fig, "a1056_components.png", SRC)

    # 図3：27通りで「Bが速い」と出た割合
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    for j, d in enumerate(DESIGNS):
        v = grid[grid.design == d].p_B_faster.values * 100
        xs = j + np.linspace(-0.25, 0.25, len(v))
        ax.scatter(xs, v, s=14, color=LIGHT, edgecolor=BLUE, lw=.5)
        ax.scatter([j], [base.p_B_faster[j] * 100], s=70, marker="D", color=ORANGE, zorder=3,
                   label="基本の置き方" if j == 0 else None)
    ax.axhline(50, color=GRAY, ls="--", lw=1); ax.text(3.45, 51, "半々", color=GRAY, fontsize=8.5, ha="right")
    ax.set_xticks(range(4), SHORT); ax.set_ylim(0, 105)
    ax.set_ylabel("本当に速いBが「速い」と出た割合（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="center right", bbox_to_anchor=(1, 0.66))
    pr = gs.loc[DESIGNS[3]]
    ax.set_title(f"27通り（点）：往復は{pr.p_min*100:.1f}〜{pr.p_max*100:.0f}%、ほかは向きが逆に出る置き方があった", fontsize=12)
    save(fig, "a1056_grid.png", SRC)
    print(json.dumps(out["headline"], ensure_ascii=False, indent=1))
    print(json.dumps(out["formula_bias"], ensure_ascii=False))
    print(gs)


if __name__ == "__main__":
    main()
