"""1178 優先の印を一部の人に配ると、印のない人の当たる見込みはどれだけ下がるのか？（架空のデータ）

作成者が置いた架空の工房の限定品の抽選（1回300個、1人1個まで）。会員20,000人のうち一部に「優先の印」を配る。
申し込む確率は、印のある会員と印のない会員で別に置く（印のある会員のほうがよく申し込む）。
決まりは5つ。
  ①印なし（だれも優先しない）
  ②印のある人を先に：印のある申し込みを先に引き、残りの個数を印のない人から引く
  ③印のある人は口が2つ／④口が3つ：口の数に比例して先に引かれやすい（1人1個まで）
  ⑤印の枠は半分まで：印のある人を先に引くが、印の人に回すのは150個まで。残りは印のある人の外れとほかの人をまとめて引く
(1) 基本：印は会員の2%（400人）、申し込む確率は印のある会員50%・印のない会員14.36%。抽選を2,000回
(2) 申し込む人のうち印のある人の割合を0〜40%に変えたとき（申し込む人は3,000人に固定、各400回）
(3) 確かめ：印を配る割合（1・2・5%）×印のある会員の申し込む確率（20・50・90%）×決まり②〜⑤
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1178
SRC = "架空の工房の限定品の抽選（作成者が置いた会員・申し込みと乱数、seed 1178）"
T0 = time.time()
ITEMS = 300
MEMBERS = 20000
PU = 0.1436
RULES = [("none", "①印なし"), ("first", "②印のある人を先に"), ("w2", "③印は口が2つ"), ("w3", "④印は口が3つ"),
         ("cap", "⑤印の枠は半分まで")]


def r(x, d=4):
    return round(float(x), d)


def one_draw(rng, m, u, rule):
    """印のある申し込み m 人・ない u 人。当たった人数（印のある人、ない人）を返す"""
    n = m + u
    if n <= ITEMS:
        return m, u
    if rule == "none":
        k = rng.hypergeometric(m, u, ITEMS)
        return k, ITEMS - k
    if rule == "first":
        if m >= ITEMS:
            return ITEMS, 0
        return m, ITEMS - m
    if rule == "cap":
        cap = ITEMS // 2
        if m <= cap:
            return m, ITEMS - m
        k = rng.hypergeometric(m - cap, u, ITEMS - cap)
        return cap + k, ITEMS - cap - k
    w = 2.0 if rule == "w2" else 3.0
    key = np.concatenate([rng.exponential(1.0, m) / w, rng.exponential(1.0, u)])
    sel = np.argpartition(key, ITEMS - 1)[:ITEMS]
    k = int((sel < m).sum())
    return k, ITEMS - k


def run_members(rng, mark_share, pm, reps):
    nm = int(round(MEMBERS * mark_share))
    nu = MEMBERS - nm
    res = {}
    ms = rng.binomial(nm, pm, reps)
    us = rng.binomial(nu, PU, reps)
    for rule, name in RULES:
        km, ku = np.zeros(reps), np.zeros(reps)
        for i in range(reps):
            km[i], ku[i] = one_draw(rng, int(ms[i]), int(us[i]), rule)
        pmk = km / np.maximum(ms, 1)
        pun = ku / us
        res[rule] = {"name": name, "p_marked_pct": r(km.sum() / ms.sum() * 100, 3),
                     "p_unmarked_pct": r(ku.sum() / us.sum() * 100, 3),
                     "p_unmarked_p05_pct": r(np.percentile(pun, 5) * 100, 3),
                     "p_unmarked_p95_pct": r(np.percentile(pun, 95) * 100, 3),
                     "p_all_pct": r((km.sum() + ku.sum()) / (ms.sum() + us.sum()) * 100, 3),
                     "ratio_unmarked": r(us.sum() / ku.sum(), 3) if ku.sum() > 0 else None}
    meta = {"marked_members": nm, "unmarked_members": nu, "marked_apply_p": pm, "unmarked_apply_p": PU,
            "marked_applicants_mean": r(ms.mean(), 2), "unmarked_applicants_mean": r(us.mean(), 2),
            "applicants_mean": r((ms + us).mean(), 2),
            "marked_share_members_pct": r(nm / MEMBERS * 100, 3),
            "marked_share_applicants_pct": r(ms.sum() / (ms.sum() + us.sum()) * 100, 3),
            "ratio_overall": r((ms + us).mean() / ITEMS, 3)}
    return meta, res


def main():
    rng = np.random.default_rng(SEED)
    out = {"setting": {"items": ITEMS, "members": MEMBERS, "mark_share_members": 0.02, "marked_apply_p": 0.5,
                       "unmarked_apply_p": PU, "reps": 2000}}
    meta, res = run_members(rng, 0.02, 0.5, 2000)
    out["base_meta"] = meta
    out["base"] = res
    rows = [{"rule": k, **v} for k, v in res.items()]
    pd.DataFrame(rows).to_csv(RES / "base_rules.csv", index=False)
    m_mean, u_mean = meta["marked_applicants_mean"], meta["unmarked_applicants_mean"]
    out["formula_first_unmarked_pct"] = r((ITEMS - m_mean) / u_mean * 100, 3)
    out["formula_none_pct"] = r(ITEMS / (m_mean + u_mean) * 100, 3)
    print("base", round(time.time() - T0, 1), flush=True)

    # data：はじめの200回の申し込み人数と当たった人数（②）
    rng_d = np.random.default_rng(SEED + 1)
    ms = rng_d.binomial(400, 0.5, 200)
    us = rng_d.binomial(MEMBERS - 400, PU, 200)
    rec = []
    for i in range(200):
        km, ku = one_draw(rng_d, int(ms[i]), int(us[i]), "first")
        rec.append({"draw": i + 1, "marked_applicants": int(ms[i]), "unmarked_applicants": int(us[i]),
                    "marked_wins": int(km), "unmarked_wins": int(ku)})
    pd.DataFrame(rec).to_csv(DATA / "draws_rule_first.csv", index=False)

    # (2) 申し込む人のうち印のある人の割合
    curve = []
    N = 3000
    for sh in [0, 0.01, 0.02, 0.05, 0.0667, 0.08, 0.1, 0.15, 0.2, 0.3, 0.4]:
        m = int(round(N * sh))
        u = N - m
        for rule, name in RULES:
            reps = 1 if rule in ("first",) else 400
            km = ku = 0
            for _ in range(reps):
                a, b = one_draw(rng, m, u, rule)
                km += a
                ku += b
            curve.append({"marked_share_applicants_pct": r(m / N * 100, 2), "marked": m, "unmarked": u, "rule": rule,
                          "rule_name": name, "p_unmarked_pct": r(ku / (reps * u) * 100, 3),
                          "p_marked_pct": r(km / (reps * m) * 100, 3) if m else None,
                          "formula_first_pct": r(max(0, ITEMS - m) / u * 100, 3) if rule == "first" else None})
    cdf = pd.DataFrame(curve)
    cdf.to_csv(RES / "by_marked_share.csv", index=False)
    out["curve_note"] = "申し込む人3,000人・300個に固定"
    print("curve", round(time.time() - T0, 1), flush=True)

    # (3) 確かめ
    grid = []
    for ms_ in [0.01, 0.02, 0.05]:
        for pm in [0.2, 0.5, 0.9]:
            mt, rs = run_members(rng, ms_, pm, 300)
            for rule, v in rs.items():
                grid.append({"mark_share_members_pct": ms_ * 100, "marked_apply_p": pm,
                             "marked_share_applicants_pct": mt["marked_share_applicants_pct"],
                             "applicants_mean": mt["applicants_mean"], "rule": rule, **{k: v[k] for k in v if k != "name"},
                             "rule_name": v["name"]})
        print("grid", ms_, round(time.time() - T0, 1), flush=True)
    gdf = pd.DataFrame(grid)
    base_none = gdf[gdf.rule == "none"].set_index(["mark_share_members_pct", "marked_apply_p"])["p_unmarked_pct"]
    gdf["unmarked_vs_none"] = [r(row.p_unmarked_pct / base_none.loc[(row.mark_share_members_pct, row.marked_apply_p)], 4)
                               for row in gdf.itertuples()]
    gdf.to_csv(RES / "grid.csv", index=False)
    gs = {}
    for rule, name in RULES[1:]:
        x = gdf[gdf.rule == rule]
        gs[rule] = {"unmarked_vs_none_min": r(x.unmarked_vs_none.min()), "unmarked_vs_none_max": r(x.unmarked_vs_none.max()),
                    "p_unmarked_min_pct": r(x.p_unmarked_pct.min(), 3), "p_unmarked_max_pct": r(x.p_unmarked_pct.max(), 3)}
    gs["marked_share_applicants_min_pct"] = r(gdf.marked_share_applicants_pct.min(), 3)
    gs["marked_share_applicants_max_pct"] = r(gdf.marked_share_applicants_pct.max(), 3)
    gs["n_cases"] = int(gdf[gdf.rule == "none"].shape[0])
    gs["first_zero_cases"] = int(((gdf.rule == "first") & (gdf.p_unmarked_pct == 0)).sum())
    out["grid_summary"] = gs

    # 図1：基本の5つの決まり
    fig, ax = plt.subplots(figsize=(8.2, 4.3))
    xs = np.arange(len(RULES))
    for i, (key, col, lab) in enumerate([("p_marked_pct", ORANGE, "印のある人"), ("p_unmarked_pct", BLUE, "印のない人")]):
        vals = [res[k][key] for k, _ in RULES]
        bars = ax.bar(xs + (i - 0.5) * 0.38, vals, 0.36, color=col, label=lab)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.3f}", ha="center", fontsize=8)
    ax.axhline(res["none"]["p_all_pct"], color=GRAY, ls="--", lw=1)
    ax.set_xticks(xs, [n for _, n in RULES], fontsize=9)
    ax.set_ylabel("1人あたりの当たる見込み（%）")
    ax.set_ylim(0, 112)
    ax.set_title(f"会員の2%に配った印で、印のない人は{res['none']['p_unmarked_pct']:.3f}%→{res['first']['p_unmarked_pct']:.3f}%（②）")
    ax.legend(frameon=False, loc="upper right")
    save(fig, "a1178_rules.png", SRC + "。300個、会員20,000人、抽選2,000回。点線は全体の当たる割合")

    # 図2：申し込む人の中の印の割合と、印のない人の見込み
    fig, ax = plt.subplots(figsize=(8, 4.3))
    for (rule, name), col in zip(RULES, [GRAY, BLUE, GREEN, ORANGE, INK]):
        y = cdf[cdf.rule == rule]
        ax.plot(y.marked_share_applicants_pct, y.p_unmarked_pct, marker="o", ms=3.5, color=col, label=name)
    ax.axvline(10, color=GRAY, lw=0.8, ls=":")
    ax.text(10.4, 10.6, "印のある人＝個数", fontsize=8.5, color=GRAY)
    ax.set_xlabel("申し込む人のうち印のある人の割合（%）")
    ax.set_ylabel("印のない人の当たる見込み（%）")
    ax.set_ylim(0, 11.5)
    ax.set_title("印のある人が個数に近づくほど、②では印のない人が0に近づく")
    ax.legend(frameon=False, fontsize=8.5)
    save(fig, "a1178_by_share.png", SRC + "。申し込む人3,000人・300個に固定、各400回（②は式どおりの1回）")

    # 図3：確かめ（申し込む人の中の印の割合の順に並べる）
    fig, ax = plt.subplots(figsize=(8.2, 4.3))
    for (rule, name), col in zip(RULES[1:], [BLUE, GREEN, ORANGE, INK]):
        y = gdf[gdf.rule == rule].sort_values("marked_share_applicants_pct")
        ax.plot(y.marked_share_applicants_pct, y.unmarked_vs_none, marker="o", ms=4, color=col, label=name)
    ax.set_xlabel("申し込む人のうち印のある人の割合（%）")
    ax.set_ylabel("印のない人の見込み ÷ ①印なし")
    ax.set_ylim(0, 1.05)
    ax.set_xlim(0, None)
    ax.axhline(1, color=GRAY, lw=0.8)
    ax.set_title("9通りすべてで印のない人は下がり、②がいちばん大きく下がる")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    save(fig, "a1178_grid.png", SRC + "。印を配る割合（1・2・5%）×印のある会員の申し込む確率（20・50・90%）の9通り、各300回")

    with open(RES / "a1178_main.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("done", round(time.time() - T0, 1))


if __name__ == "__main__":
    main()
