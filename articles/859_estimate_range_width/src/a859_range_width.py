"""859 見積もりの幅（最短〜最長）を書くと、外れ方はどう変わるのか？（架空のデータ）

架空の作業。作業ごとの実際の日数は対数正規分布（中央値 med、ばらつき sigma）。見積もる人は中央値を正しく当てる（基本）。
見積もる人は「9割はこの中に入る」つもりで幅を書くが、ばらつきを本当の f 倍（基本 f=0.6、狭く見る）に感じている。
幅の書き方：点だけ／左右同じ日数の幅（中央値±同じ日数）／右に長い幅（分布の5%点〜95%点の形）。
過去の作業で「幅に入った割合」を数えて幅を広げ直すと、次の作業で入る割合はどこまで9割に近づくかも数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 859
SRC = "架空の作業の見積もりと実績（作成者が乱数で作成、seed 859）"
Z90 = 1.6448536269514722  # 9割の幅（左右5%ずつ）の標準正規の点
N_BIG = 200000


def tasks(rng, n, sigma=0.5):
    med = rng.integers(2, 21, n).astype(float)        # 中央値 2〜20日
    sig = rng.uniform(sigma - 0.2, sigma + 0.2, n)   # 作業ごとのばらつき
    act = med * np.exp(sig * rng.standard_normal(n))
    return med, sig, act


def ranges(med, sig, f, bias=1.0):
    """見積もる人の書く幅。bias<1 は中央値を短めに見る（楽観）"""
    m = med * bias
    s = sig * f
    lo, hi = m * np.exp(-Z90 * s), m * np.exp(Z90 * s)   # 右に長い幅
    half = (hi - lo) / 2                                  # 同じ幅を左右同じ日数で
    return m, (lo, hi), (np.maximum(m - half, 0), m + half)


def score(act, lo, hi):
    inside = (act >= lo) & (act <= hi)
    late, early = act > hi, act < lo
    miss = (~inside).sum()
    over = np.where(late, act / hi - 1, np.nan)
    return {"hit": round(float(inside.mean()), 4), "late": round(float(late.mean()), 4),
            "early": round(float(early.mean()), 4),
            "late_share_of_miss": round(float(late.sum() / miss), 3) if miss else None,
            "late_over_median_pct": round(float(np.nanmedian(over) * 100), 1) if late.any() else None,
            "late_over_p90_pct": round(float(np.nanquantile(over, .9) * 100), 1) if late.any() else None}


def point_score(act, m):
    r = act / m - 1
    return {"within10": round(float((np.abs(r) <= .1).mean()), 4), "within20": round(float((np.abs(r) <= .2).mean()), 4),
            "late": round(float((r > 0).mean()), 4), "abs_err_median_pct": round(float(np.median(np.abs(r)) * 100), 1),
            "late_err_p90_pct": round(float(np.quantile(r[r > 0], .9) * 100), 1)}


def recalib(rng, n_past, f, n_next=100, reps=2000, sigma=0.5, bias=1.0):
    """過去 n_past 件で、log(実際/中央値) / (見積もる人のばらつき) の絶対値の9割点を取り、幅をその倍率に広げる"""
    hits, late, miss = [], 0, 0
    for _ in range(reps):
        med, sig, act = tasks(rng, n_past + n_next, sigma)
        m = med * bias
        k = np.abs(np.log(act[:n_past] / m[:n_past])) / (sig[:n_past] * f)
        kq = np.quantile(k, 0.9) if n_past > 0 else Z90
        lo, hi = m[n_past:] * np.exp(-kq * sig[n_past:] * f), m[n_past:] * np.exp(kq * sig[n_past:] * f)
        a = act[n_past:]
        hits.append(((a >= lo) & (a <= hi)).mean())
        late += int((a > hi).sum()); miss += int(((a > hi) | (a < lo)).sum())
    h = np.array(hits)
    return {"hit_mean": round(float(h.mean()), 4), "hit_p10": round(float(np.quantile(h, .1)), 3),
            "hit_p90": round(float(np.quantile(h, .9)), 3), "share_below_80": round(float((h < 0.8).mean()), 3),
            "late_share_of_miss": round(late / miss, 3)}


def main():
    rng = np.random.default_rng(SEED)
    # データ：架空の作業30件の見積もり（f=0.6）と実績
    med, sig, act = tasks(rng, 30)
    m, (lo, hi), (slo, shi) = ranges(med, sig, 0.6)
    one30 = {"inside_skew": int(((act >= lo) & (act <= hi)).sum()), "late": int((act > hi).sum()),
             "early": int((act < lo).sum())}
    pd.DataFrame({"task_id": np.arange(1, 31), "median_days": med, "sigma": sig.round(3),
                  "range_lo": lo.round(2), "range_hi": hi.round(2), "sym_lo": slo.round(2), "sym_hi": shi.round(2),
                  "actual_days": act.round(2)}).to_csv(DATA / "tasks_30.csv", index=False)

    # 1) 書き方 × 感じているばらつき（f）
    med, sig, act = tasks(np.random.default_rng(SEED * 10), N_BIG)
    point = point_score(act, med)
    rows = []
    for f in [0.4, 0.6, 0.8, 1.0, 1.2]:
        m, (lo, hi), (slo, shi) = ranges(med, sig, f)
        rows.append({"f": f, "shape": "右に長い幅", **score(act, lo, hi)})
        rows.append({"f": f, "shape": "左右同じ日数の幅", **score(act, slo, shi)})
    by_f = pd.DataFrame(rows)
    by_f.to_csv(RES / "by_shape_f.csv", index=False)
    theory = {str(f): round(float(2 * (0.5 * (1 + __import__("math").erf(Z90 * f / 2 ** .5))) - 1), 4)
              for f in [0.4, 0.6, 0.8, 1.0, 1.2]}  # sigma が作業ごとに違っても、幅も同じ割合なので式は同じ

    # 2) 確かめ：本当のばらつき・楽観
    rob = []
    for sigma in [0.3, 0.5, 0.8]:
        med2, sig2, act2 = tasks(np.random.default_rng(SEED * 20 + int(sigma * 10)), N_BIG, sigma)
        for f in [0.6, 1.0]:
            for bias in [1.0, 0.8]:
                m, (lo, hi), (slo, shi) = ranges(med2, sig2, f, bias)
                a = score(act2, lo, hi); b = score(act2, slo, shi)
                rob.append({"sigma": sigma, "f": f, "bias": bias,
                            "hit_skew": a["hit"], "late_share_skew": a["late_share_of_miss"],
                            "hit_sym": b["hit"], "late_share_sym": b["late_share_of_miss"]})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    # 3) 過去の件数で幅を広げ直す
    rec = []
    for f, bias in [(0.6, 1.0), (1.0, 1.0), (0.6, 0.8)]:
        for n in [0, 5, 10, 20, 50, 100]:
            r = recalib(np.random.default_rng(SEED * 1000 + n + int(f * 10) * 7 + int(bias * 100)), n, f, bias=bias)
            rec.append({"f": f, "bias": bias, "n_past": n, **r})
    rec = pd.DataFrame(rec)
    rec.to_csv(RES / "recalibration.csv", index=False)

    out = {"setting": {"median_days": "2〜20の整数", "sigma_base": "0.3〜0.7（一様）", "z90": round(Z90, 4),
                       "n_tasks": N_BIG, "recalib_reps": 2000, "recalib_next": 100},
           "tasks30_f0.6": one30, "point_only": point, "by_shape_f": by_f.to_dict("records"), "theory_hit_skew_by_f": theory,
           "robustness": rob.to_dict("records"), "recalibration": rec.to_dict("records")}
    json.dump(out, open(RES / "a859_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：作業30件の幅と実績
    d = pd.read_csv(DATA / "tasks_30.csv").sort_values("median_days").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    y = np.arange(len(d))
    inside = (d.actual_days >= d.range_lo) & (d.actual_days <= d.range_hi)
    ax.hlines(y, d.range_lo, d.range_hi, color=LIGHT, lw=5)
    ax.plot(d.median_days, y, "|", color=INK, ms=9)
    ax.scatter(d.actual_days[inside], y[inside], color=BLUE, s=18, zorder=3, label="実際の日数（幅の中）")
    ax.scatter(d.actual_days[~inside], y[~inside], color=ORANGE, s=22, zorder=3, label="実際の日数（幅の外）")
    ax.set_yticks([]); ax.set_xlabel("日数"); ax.set_ylabel("作業30件（見積もりの短い順）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title(f"「9割入る」つもりの幅（水色）に入ったのは30件中{int(inside.sum())}件")
    save(fig, "a859_ranges30.png", SRC)

    # 図2：感じているばらつき f と、幅に入る割合・外れの向き
    fig, axes = plt.subplots(1, 2, figsize=(8.8, 3.8))
    for shape, col in [("右に長い幅", BLUE), ("左右同じ日数の幅", ORANGE)]:
        g = by_f[by_f["shape"] == shape]
        axes[0].plot(g.f, g.hit * 100, "o-", color=col, label=shape)
        axes[1].plot(g.f, g.late_share_of_miss * 100, "o-", color=col, label=shape)
    axes[0].axhline(90, color=GRAY, ls=":", lw=1); axes[0].text(0.41, 91.5, "ねらいの9割", fontsize=8.5, color=GRAY)
    axes[0].set_ylim(0, 100); axes[0].set_ylabel("幅に入った割合（%）")
    axes[1].axhline(50, color=GRAY, ls=":", lw=1); axes[1].set_ylim(0, 100); axes[1].set_ylabel("外れのうち、遅れの側の割合（%）")
    for ax in axes:
        ax.set_xlabel("感じているばらつき（本当の何倍か）")
    axes[0].legend(frameon=False, fontsize=9, loc="lower right")
    axes[0].set_title("幅が狭いと、入る割合は9割に届かない", fontsize=11)
    axes[1].set_title("左右同じ日数の幅は、外れがほぼ遅れの側", fontsize=11)
    save(fig, "a859_hit_by_f.png", SRC)

    # 図3：過去の件数で広げ直す
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for (f, bias), col, lab in [((0.6, 1.0), BLUE, "狭く見る人（0.6倍）"), ((1.0, 1.0), GREEN, "正しく見る人（1倍）"),
                                ((0.6, 0.8), ORANGE, "狭く見て、短めにも見る人")]:
        g = rec[(rec.f == f) & (rec.bias == bias)]
        x = np.arange(len(g))
        ax.plot(x, g.hit_mean * 100, "o-", color=col, label=lab)
        if f == 0.6 and bias == 1.0:
            ax.fill_between(x, g.hit_p10 * 100, g.hit_p90 * 100, color=col, alpha=.15, lw=0,
                            label="狭く見る人の10〜90%（2,000回）")
    ax.set_xticks(np.arange(6)); ax.set_xticklabels(["直さない", "5件", "10件", "20件", "50件", "100件"])
    ax.axhline(90, color=GRAY, ls=":", lw=1)
    ax.set_xlabel("幅を広げ直すのに使った過去の作業の件数"); ax.set_ylabel("次の100件が幅に入った割合（%）")
    ax.set_ylim(40, 100); ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("過去の実績で幅を広げ直すと9割に近づくが、件数が少ないと振れる")
    save(fig, "a859_recalib.png", SRC)
    print(json.dumps(point, ensure_ascii=False)); print(by_f.to_string()); print(theory); print(rob.to_string()); print(rec.to_string())


if __name__ == "__main__":
    main()
