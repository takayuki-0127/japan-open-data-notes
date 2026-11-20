"""852 余裕を作業ごとに持つのと、最後にまとめて持つのでは？（架空のデータ）

架空のプロジェクト：10個の作業を順に行う。作業ごとの日数は右に長い分布（対数正規）から引く。
同じ「全体の日数」を、作業ごとに割り振るか（A）、作業は最もありそうな日数で並べて最後にまとめて置くか（B）で比べる。
早く終わった分を次の作業へ渡す割合 f を置く（f=0 は、早く終わっても割り当ての日まで次に渡さない）。
"""
import json, time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 852
SRC = "架空のプロジェクト（作成者が乱数で作成、seed 852）"
MED = np.array([3, 5, 4, 6, 2, 8, 5, 4, 3, 6], float)  # 作業ごとの中央値（最もありそうな日数の目安）
SIGMA = 0.5
N_SIM = 100_000
Z90 = 1.2815515655446004


def draw(rng, med, sigma, n=N_SIM):
    return med[None, :] * np.exp(rng.normal(0, sigma, (n, len(med))))


def finish(d, target, f):
    """作業ごとの目標 target。早く終わったら、余った日数の f だけ次に渡す"""
    early = d < target[None, :]
    e = np.where(early, target[None, :] - f * (target[None, :] - d), d)
    return e.sum(1)


def compare(d, med, total, f):
    k = total / med.sum()
    fa = finish(d, med * k, f)          # A：作業ごとに余裕
    fb = finish(d, med, f)              # B：作業は中央値、余裕は最後に
    return {"A_ontime": float((fa <= total + 1e-9).mean()), "B_ontime": float((fb <= total + 1e-9).mean()),
            "A_mean": float(fa.mean()), "B_mean": float(fb.mean()),
            "A_late_mean": float(np.maximum(fa - total, 0).mean()), "B_late_mean": float(np.maximum(fb - total, 0).mean())}, fa, fb


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    d = draw(rng, MED, SIGMA)
    sum_med = MED.sum()
    pd.DataFrame(np.round(d[:2000], 3), columns=[f"task{i+1}" for i in range(len(MED))]).assign(
        sim=np.arange(1, 2001)).iloc[:, [10] + list(range(10))].to_csv(DATA / "task_days_2000.csv", index=False)

    # 1) 作業ごとに90%の日数を積む vs 全体の90%
    q90_each = MED * np.exp(Z90 * SIGMA)
    total_q90 = float(q90_each.sum())
    s = d.sum(1)
    proj_q90 = float(np.quantile(s, 0.9))
    pad = {"sum_median": float(sum_med), "sum_of_task_q90": round(total_q90, 2), "project_q90_if_passed_on": round(proj_q90, 2),
           "mean_total_days": round(float(s.mean()), 2),
           "pad_each_days": round(total_q90 - sum_med, 2), "pad_pooled_days": round(proj_q90 - sum_med, 2)}
    # 作業ごとに90%の日数を割り当て、早く終わっても渡さない（f=0）ときの、全体の期限内の割合
    fa0 = finish(d, q90_each, 0.0)
    pad["ontime_task_q90_f0"] = round(float((fa0 <= total_q90 + 1e-9).mean()), 4)
    pad["ontime_task_q90_f0_formula"] = round(0.9 ** len(MED), 4)
    pad["ontime_task_q90_f1"] = round(float((s <= total_q90).mean()), 4)

    # 2) 同じ全体の日数（中央値の合計の1.2倍＝55.2日）で A と B
    base_total = round(sum_med * 1.2, 1)
    main_rows = []
    for f in [0.0, 0.5, 1.0]:
        r, fa, fb = compare(d, MED, base_total, f)
        main_rows.append({"f": f, **{k: round(v, 4) for k, v in r.items()}})
        if f == 0.0:
            fa_keep, fb_keep = fa, fb
    main_df = pd.DataFrame(main_rows)
    main_df.to_csv(RES / "same_total_1_2.csv", index=False)

    # 3) 全体の日数を変えたときの、期限内の割合（f=0 と f=1）
    curve = []
    for mult in np.round(np.arange(1.0, 2.01, 0.05), 2):
        tot = sum_med * mult
        for f in [0.0, 1.0]:
            r, _, _ = compare(d, MED, tot, f)
            curve.append({"mult": float(mult), "total_days": round(float(tot), 2), "f": f,
                          "A_ontime": round(r["A_ontime"], 4), "B_ontime": round(r["B_ontime"], 4)})
    curve = pd.DataFrame(curve)
    curve.to_csv(RES / "ontime_by_total.csv", index=False)
    # 期限内90%に必要な全体の日数
    need = {}
    for f in [0.0, 1.0]:
        c = curve[curve.f == f]
        for col in ["A_ontime", "B_ontime"]:
            ok = c[c[col] >= 0.9]
            need[f"f{f:g}_{col[0]}"] = float(ok.mult.min()) if len(ok) else None
    need["f0_A_ontime_at_mult2"] = float(curve[(curve.f == 0) & (curve.mult == 2.0)].A_ontime.iloc[0])

    # 4) 確かめ：ばらつき・作業の数・渡す割合を変える（全体の日数は中央値の合計の1.2倍）
    sens = []
    for sigma in [0.3, 0.5, 0.7]:
        for n_task in [5, 10, 20]:
            med = np.resize(MED, n_task)
            dd = draw(np.random.default_rng(SEED * 10 + int(sigma * 10) * 100 + n_task), med, sigma, 40_000)
            for f in [0.0, 0.5, 1.0]:
                r, _, _ = compare(dd, med, med.sum() * 1.2, f)
                q90e = med * np.exp(Z90 * sigma)
                sens.append({"sigma": sigma, "n_task": n_task, "f": f, "A_ontime": round(r["A_ontime"], 4),
                             "B_ontime": round(r["B_ontime"], 4),
                             "pad_each_over_pooled": round(float((q90e.sum() - med.sum()) /
                                                               (np.quantile(dd.sum(1), 0.9) - med.sum())), 3)})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)

    out = {"setting": {"tasks_median_days": MED.tolist(), "sigma": SIGMA, "n_sim": N_SIM, "base_total_days": base_total},
           "padding_q90": pad, "same_total_1_2": main_rows, "need_mult_for_90pct": need,
           "sensitivity_ranges": {
               "f0_A_ontime": [float(sens[sens.f == 0].A_ontime.min()), float(sens[sens.f == 0].A_ontime.max())],
               "f0_B_ontime": [float(sens[sens.f == 0].B_ontime.min()), float(sens[sens.f == 0].B_ontime.max())],
               "f1_A_minus_B_maxabs": float((sens[sens.f == 1].A_ontime - sens[sens.f == 1].B_ontime).abs().max()),
               "pad_each_over_pooled": [float(sens.pad_each_over_pooled.min()), float(sens.pad_each_over_pooled.max())]}}
    json.dump(out, open(RES / "a852_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：全体の日数と期限内の割合
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    c0, c1 = curve[curve.f == 0], curve[curve.f == 1]
    ax.plot(c0.total_days, c0.A_ontime * 100, color=ORANGE, lw=2, label="A 作業ごとに余裕（早く終わっても渡さない）")
    ax.plot(c0.total_days, c0.B_ontime * 100, color=BLUE, lw=2, label="B 最後にまとめて余裕（早く終わっても渡さない）")
    ax.plot(c1.total_days, c1.A_ontime * 100, color=GRAY, lw=1.5, ls="--", label="早く終わった分を全部渡す（A・B同じ）")
    ax.axvline(base_total, color=GRAY, lw=.8, ls=":")
    ax.text(base_total + .5, 92, f"全体{base_total:g}日", color=GRAY, fontsize=9)
    ax.set_xlabel("全体の日数（中央値の合計46日〜その2倍）"); ax.set_ylabel("全体の日数の中に終わる割合（%）")
    ax.set_ylim(0, 102); ax.legend(frameon=False, fontsize=8.5, loc="center right", bbox_to_anchor=(1.0, 0.6))
    ax.set_title("同じ全体の日数でも、余裕の置き場所で間に合う割合が変わる")
    save(fig, "a852_ontime_curve.png", SRC)

    # 図2：90%の余裕の大きさ
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    labels = ["作業ごとに90%の日数を積む", "全体の90%の日数（最後にまとめる）"]
    vals = [pad["pad_each_days"], pad["pad_pooled_days"]]
    ax.barh(labels[::-1], vals[::-1], color=[BLUE, ORANGE])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + .5, i, f"+{v:.1f}日", va="center", fontsize=10)
    ax.set_xlabel("中央値の合計（46日）に足す余裕の日数"); ax.set_xlim(0, max(vals) * 1.2)
    ax.set_title("作業ごとに積んだ余裕は、全体でまとめた余裕の約%.1f倍" % (vals[0] / vals[1]))
    save(fig, "a852_padding.png", SRC, y=-0.08)

    # 図3：全体55.2日・f=0 の終わる日の分布
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    bins = np.linspace(40, 110, 71)
    ax.hist(fa_keep, bins=bins, color=ORANGE, alpha=.6, density=True, label="A 作業ごとに余裕")
    ax.hist(fb_keep, bins=bins, color=BLUE, alpha=.6, density=True, label="B 最後にまとめて余裕")
    ax.axvline(base_total, color=INK, lw=1, ls="--"); ax.text(base_total + .5, ax.get_ylim()[1] * .9, f"期限 {base_total:g}日", fontsize=9)
    ax.set_xlabel("全体が終わる日（日）"); ax.set_yticks([]); ax.legend(frameon=False, fontsize=9)
    ax.set_title("早く終わっても次に渡さないと置くと、Aは期限より前に終わらない")
    save(fig, "a852_finish_hist.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
