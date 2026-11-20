"""890 見積もりの作業時間は、何%外れやすいのか？（架空のデータ）

架空のフリーランスの人の案件の記録（見積もりの作業時間と、実際にかかった作業時間）。
同じ記録から「何%外れたか」を、案件ごとの平均・中央値・合計の比・実際を分母にした数え方などで数え、
数え方でどれだけ違うか、記録の件数でどれだけ振れるか、置き方を変えるとどう動くかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 890
SRC = "架空のフリーランスの人と案件の記録（作成者が乱数で作成、seed 890）"
BASE = {"bias": 1.2, "sigma_mode": "small_wide"}
SIGMA_MODES = {"small_wide": "小さい案件ほど外れやすい（基本）", "flat": "大きさによらず同じ", "large_wide": "大きい案件ほど外れやすい"}
METRICS = [("mean_ratio", "案件ごとの（実際÷見積もり−1）の平均"),
           ("median_ratio", "案件ごとの（実際÷見積もり−1）の中央値"),
           ("total_ratio", "合計の実際÷合計の見積もり−1"),
           ("mean_short", "案件ごとの（1−見積もり÷実際）の平均"),
           ("mean_abs", "外れの大きさ｜実際÷見積もり−1｜の平均"),
           ("median_abs", "外れの大きさ｜実際÷見積もり−1｜の中央値"),
           ("share_out20", "±20%を超えて外れた案件の割合"),
           ("share_late", "見積もりより長くかかった案件の割合")]


def sigma_of(E, mode):
    t = np.clip(np.log(E) / np.log(40), 0, 1)  # 1時間で0、40時間で1
    if mode == "small_wide":
        return 0.5 - 0.3 * t
    if mode == "large_wide":
        return 0.2 + 0.3 * t
    return np.full_like(E, 0.35)


def make_jobs(rng, n, bias=1.2, sigma_mode="small_wide"):
    E = np.clip(np.round(np.exp(rng.normal(np.log(6), 0.8, n)) * 2) / 2, 1, 60)
    s = sigma_of(E, sigma_mode)
    A = E * bias * np.exp(s * rng.normal(size=n))
    return E, A


def metrics(E, A, axis=None):
    r = A / E
    return {"mean_ratio": np.mean(r - 1, axis=axis), "median_ratio": np.median(r - 1, axis=axis),
            "total_ratio": A.sum(axis=axis) / E.sum(axis=axis) - 1, "mean_short": np.mean(1 - E / A, axis=axis),
            "mean_abs": np.mean(np.abs(r - 1), axis=axis), "median_abs": np.median(np.abs(r - 1), axis=axis),
            "share_out20": np.mean(np.abs(r - 1) > 0.2, axis=axis), "share_late": np.mean(r > 1, axis=axis)}


def pct(x):
    return round(float(x) * 100, 1)


def main():
    rng = np.random.default_rng(SEED)

    # 1) 基本の置き方：たくさんの案件（100万件）での値
    E, A = make_jobs(np.random.default_rng(SEED * 10), 1_000_000, **BASE)
    big = {k: pct(v) for k, v in metrics(E, A).items()}
    # 大きさの区切りごと
    bins = [0, 2, 5, 10, 20, 61]
    lab = ["2時間以下", "2〜5時間", "5〜10時間", "10〜20時間", "20時間超"]
    cut = pd.cut(E, bins, labels=lab, right=True)
    by_size = []
    for l in lab:
        m = np.asarray(cut == l)
        mm = metrics(E[m], A[m])
        by_size.append({"size": l, "share_of_jobs": pct(m.mean()), "share_of_hours": pct(E[m].sum() / E.sum()),
                        "mean_ratio": pct(mm["mean_ratio"]), "median_ratio": pct(mm["median_ratio"]),
                        "share_out20": pct(mm["share_out20"])})
    by_size = pd.DataFrame(by_size)
    by_size.to_csv(RES / "by_job_size.csv", index=False)

    # 2) 1人の記録の件数ごとの振れ（2,000人）
    rec = []
    for n in [20, 50, 200]:
        Ep, Ap = make_jobs(np.random.default_rng(SEED * 100 + n), 2000 * n, **BASE)
        Ep, Ap = Ep.reshape(2000, n), Ap.reshape(2000, n)
        mm = metrics(Ep, Ap, axis=1)
        for k in ["mean_ratio", "median_ratio", "total_ratio", "share_out20"]:
            rec.append({"n_records": n, "metric": k, "p10": pct(np.quantile(mm[k], .1)), "p50": pct(np.median(mm[k])),
                        "p90": pct(np.quantile(mm[k], .9))})
        if n == 20:
            mean_gt_total_share20 = pct(np.mean(mm["mean_ratio"] > mm["total_ratio"]))
            spread20 = mm["mean_ratio"] - mm["total_ratio"]
            spread20_p10, spread20_p90 = pct(np.quantile(spread20, .1)), pct(np.quantile(spread20, .9))
    rec = pd.DataFrame(rec)
    rec.to_csv(RES / "by_record_count.csv", index=False)

    # 3) 確かめ：癖（中央値の比）×外れやすさの形
    sens = []
    j = 0
    for b in [1.0, 1.2, 1.5]:
        for sm in ["small_wide", "flat", "large_wide"]:
            j += 1
            e, a = make_jobs(np.random.default_rng(SEED * 7 + j), 400_000, bias=b, sigma_mode=sm)
            mm = {k: pct(v) for k, v in metrics(e, a).items()}
            vals = [mm["mean_ratio"], mm["median_ratio"], mm["total_ratio"], mm["mean_short"]]
            sens.append({"bias": b, "sigma_mode": sm, **mm, "max_minus_min_4": round(max(vals) - min(vals), 1)})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)
    flat1 = sens[(sens.bias == 1.0) & (sens.sigma_mode == "flat")].iloc[0]
    formula_flat = pct(np.exp(0.35 ** 2 / 2) - 1)

    # 1人分の記録（200件）
    E1, A1 = make_jobs(rng, 200, **BASE)
    one = pd.DataFrame({"job": np.arange(1, 201), "estimate_h": E1, "actual_h": A1.round(2)})
    one.to_csv(DATA / "one_person_200jobs.csv", index=False)
    one_m = {k: pct(v) for k, v in metrics(E1, one.actual_h.values).items()}

    out = {"base": BASE, "metrics_names": dict(METRICS), "base_1m_jobs": big, "by_job_size": by_size.to_dict("records"),
           "by_record_count": rec.to_dict("records"),
           "records20_mean_gt_total_pct": mean_gt_total_share20,
           "records20_mean_minus_total_p10_p90": [spread20_p10, spread20_p90],
           "sensitivity": sens.to_dict("records"),
           "sens_range_mean_ratio": [float(sens.mean_ratio.min()), float(sens.mean_ratio.max())],
           "sens_range_max_minus_min_4": [float(sens.max_minus_min_4.min()), float(sens.max_minus_min_4.max())],
           "sens_mean_gt_median_all": bool((sens.mean_ratio > sens.median_ratio).all()),
           "flat_bias1": {"mean_ratio": float(flat1.mean_ratio), "median_ratio": float(flat1.median_ratio),
                          "formula_exp_sigma2_half": formula_flat, "share_late": float(flat1.share_late),
                          "mean_short": float(flat1.mean_short)},
           "one_person_200": one_m}
    json.dump(out, open(RES / "a890_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：同じ記録の「何%外れたか」
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    keys = ["mean_ratio", "total_ratio", "median_ratio", "mean_short"]
    names = ["案件ごとの（実際÷見積もり−1）の平均", "合計の実際÷合計の見積もり−1", "案件ごとの（実際÷見積もり−1）の中央値",
             "案件ごとの（1−見積もり÷実際）の平均"]
    vals = [big[k] for k in keys]
    ax.barh(names[::-1], vals[::-1], color=[GRAY, LIGHT, BLUE, ORANGE][::-1], height=.6)
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 0.5, i, f"{v:+.1f}%", va="center", fontsize=9.5)
    ax.set_xlim(0, max(vals) * 1.2); ax.set_xlabel("見積もりより何%多くかかったか（同じ100万件の記録）")
    ax.set_title("同じ記録でも、「何%多くかかったか」は数え方で2.5倍違う", fontsize=12.5)
    save(fig, "a890_metrics.png", SRC)

    # 図2：1人分の200件
    fig, ax = plt.subplots(figsize=(7.2, 4.1))
    r = one.actual_h / one.estimate_h
    ax.scatter(one.estimate_h, r, s=14, color=BLUE, alpha=.6, lw=0)
    ax.axhline(1, color=INK, lw=.8); ax.axhline(1.2, color=GRAY, lw=.8, ls=":"); ax.axhline(0.8, color=GRAY, lw=.8, ls=":")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks([1, 2, 5, 10, 20, 50], ["1", "2", "5", "10", "20", "50"])
    ax.set_yticks([0.5, 0.8, 1, 1.2, 1.5, 2, 3], ["0.5", "0.8", "1", "1.2", "1.5", "2", "3"])
    ax.set_xlabel("見積もりの作業時間（時間、対数の目盛り）"); ax.set_ylabel("実際÷見積もり（対数の目盛り）")
    ax.yaxis.set_minor_formatter(plt.NullFormatter())
    ax.text(ax.get_xlim()[1], 0.79, "±20%の線", color=GRAY, fontsize=8.5, ha="right", va="top")
    ax.set_title("小さい案件ほど、実際÷見積もりが上下に大きく散らばる（1人の200件）", fontsize=11.5)
    save(fig, "a890_scatter.png", SRC)

    # 図3：置き方を変えると
    fig, ax = plt.subplots(figsize=(7.8, 4.6))
    ylab = [f"癖 {b:.1f}倍・{SIGMA_MODES[m].replace('（基本）', '')}" for b, m in zip(sens.bias, sens.sigma_mode)]
    y = np.arange(len(sens))[::-1]
    for k, c, mk, nm in [("mean_ratio", GRAY, "o", "案件ごとの平均"), ("total_ratio", LIGHT, "s", "合計の比"),
                         ("median_ratio", BLUE, "D", "案件ごとの中央値"), ("mean_short", ORANGE, "^", "実際を分母にした平均")]:
        ax.scatter(sens[k], y, color=c, marker=mk, s=36, label=nm, zorder=3, edgecolor=INK if c == LIGHT else "none", lw=.4)
    for yy, (lo, hi) in zip(y, zip(sens[["mean_ratio", "median_ratio", "total_ratio", "mean_short"]].min(1),
                                    sens[["mean_ratio", "median_ratio", "total_ratio", "mean_short"]].max(1))):
        ax.plot([lo, hi], [yy, yy], color=GRAY, lw=.8, zorder=1)
    ax.axvline(0, color=INK, lw=.6)
    ax.set_yticks(y, ylab, fontsize=8.5); ax.set_xlabel("「何%多くかかったか」（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("置き方を変えても、数え方による差は残る（各40万件）", fontsize=12.5)
    save(fig, "a890_sensitivity.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__":
    main()
