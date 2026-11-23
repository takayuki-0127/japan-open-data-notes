"""1031 遅れの平均と、遅れた便の遅れの平均は、どれだけ違うのか？（架空のデータ）

架空の路線A・B（1日100便、365日）。便ごとの終点に着く時刻のずれ（分）を作成者が置く：
ずれ＝ふだんのずれ（正規分布、早着もある）＋（確率 p で）遅れの分（対数正規分布）。
p は朝夕の混む時間に高く、日ごとにも振れる。乗る人の数は朝夕に多い。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1031
SRC = "架空の路線A・Bの便（作成者が乱数で作成、seed 1031）"
N_DAY, N_TRIP = 365, 100
DEP = 6 * 60 + np.arange(N_TRIP) * 10.8            # 6:00 から 10.8分おき（分）
HOUR = (DEP // 60).astype(int)
RUSH = np.isin(HOUR, [7, 8, 17, 18])
LINES = {"A線": dict(p_base=0.06, p_rush=0.18, med=5.0),
         "B線": dict(p_base=0.28, p_rush=0.45, med=1.6)}
COMMON = dict(sd_delay=0.8, day_sd=0.3, ord_mu=-0.3, ord_sd=0.4, pax_base=80, pax_rush=5.0)
THR = 1.0                                          # 遅れた便：1分以上


def make(rng, p_base, p_rush, med, n_day=N_DAY, pax_rush=None, **kw):
    c = {**COMMON, **kw}
    if pax_rush is None:
        pax_rush = c["pax_rush"]
    p = np.where(RUSH, p_rush, p_base)[None, :] * np.exp(rng.normal(0, c["day_sd"], n_day))[:, None]
    p = np.clip(p, 0, 0.95)
    hit = rng.random((n_day, N_TRIP)) < p
    extra = med * np.exp(rng.normal(0, c["sd_delay"], (n_day, N_TRIP)))
    dev = rng.normal(c["ord_mu"], c["ord_sd"], (n_day, N_TRIP)) + np.where(hit, extra, 0.0)
    lam = c["pax_base"] * np.where(RUSH, pax_rush, 1.0)
    pax = rng.poisson(np.broadcast_to(lam, (n_day, N_TRIP)))
    return dev, pax


def measures(dev, pax, thr=THR):
    late = np.maximum(dev, 0)
    dl = dev >= thr
    w = pax.astype(float)
    small = np.where(dl, 0.0, late)
    return {"mean_all_early0": float(late.mean()),
            "mean_all_signed": float(dev.mean()),
            "share_delayed_pct": float(dl.mean() * 100),
            "mean_delayed": float(late[dl].mean()),
            "mean_per_passenger": float((late * w).sum() / w.sum()),
            "mean_delayed_per_passenger": float((late * w)[dl].sum() / w[dl].sum()),
            "share_passengers_on_delayed_pct": float(w[dl].sum() / w.sum() * 100),
            "identity_share_x_delayed_plus_small": float(dl.mean() * late[dl].mean() + small.mean()),
            "small_part_under_thr": float(small.mean())}


def r(d, k=2):
    return {a: round(b, k) for a, b in d.items()}


NAMES = {"mean_all_early0": "全便の遅れの平均（早着は0）",
         "mean_all_signed": "全便のずれの平均（早着はマイナス）",
         "mean_delayed": "遅れた便（1分以上）の遅れの平均",
         "mean_per_passenger": "乗った人1人あたりの遅れの平均"}


def main():
    rng = np.random.default_rng(SEED)
    sims, res = {}, {}
    for ln, prm in LINES.items():
        dev, pax = make(rng, **prm)
        sims[ln] = (dev, pax)
        m = measures(dev, pax)
        m["ratio_delayed_to_all"] = m["mean_delayed"] / m["mean_all_early0"]
        m["ratio_passenger_to_all"] = m["mean_per_passenger"] / m["mean_all_early0"]
        m["rush_share_delayed_pct"] = float((dev[:, RUSH] >= THR).mean() * 100)
        m["other_share_delayed_pct"] = float((dev[:, ~RUSH] >= THR).mean() * 100)
        m["rush_to_other_delayed_ratio"] = m["rush_share_delayed_pct"] / m["other_share_delayed_pct"]
        m["rush_share_of_passengers_pct"] = float(pax[:, RUSH].sum() / pax.sum() * 100)
        m["rush_share_of_trips_pct"] = float(RUSH.mean() * 100)
        m["early_share_pct"] = float((dev < 0).mean() * 100)
        m["p90_delay_of_delayed"] = float(np.quantile(np.maximum(dev, 0)[dev >= THR], .9))
        res[ln] = r(m)
    tab = pd.DataFrame({ln: {NAMES[k]: res[ln][k] for k in NAMES} for ln in LINES})
    tab.loc["遅れた便の割合（%）"] = [res[ln]["share_delayed_pct"] for ln in LINES]
    tab.to_csv(RES / "measures.csv")

    # 遅れた便の決め方（0分超・1分以上・3分以上）
    thr_rows = []
    for ln in LINES:
        dev, pax = sims[ln]
        for thr in [0.0001, 1.0, 3.0]:
            m = measures(dev, pax, thr)
            thr_rows.append({"line": ln, "threshold": "0分超" if thr < 0.01 else f"{thr:.0f}分以上",
                             "share_delayed_pct": round(m["share_delayed_pct"], 2),
                             "mean_delayed": round(m["mean_delayed"], 2),
                             "ratio_to_all": round(m["mean_delayed"] / m["mean_all_early0"], 2)})
    thr_df = pd.DataFrame(thr_rows)
    thr_df.to_csv(RES / "threshold.csv", index=False)

    # 時刻ごと
    hours = []
    for ln in LINES:
        dev, pax = sims[ln]
        for h in sorted(set(HOUR)):
            mk = HOUR == h
            hours.append({"line": ln, "hour": int(h), "share_delayed_pct": round(float((dev[:, mk] >= THR).mean() * 100), 2),
                          "mean_all_early0": round(float(np.maximum(dev[:, mk], 0).mean()), 2),
                          "pax_per_trip": round(float(pax[:, mk].mean()), 1)})
    hours = pd.DataFrame(hours)
    hours.to_csv(RES / "by_hour.csv", index=False)

    # 確かめ1：A線の遅れの大きさ × B線の遅れの起きやすさ（9通り）
    grid = []
    for i, medA in enumerate([3.0, 5.0, 8.0]):
        for j, sc in enumerate([0.7, 1.0, 1.4]):
            g = np.random.default_rng(SEED * 100 + i * 10 + j)
            a = measures(*make(g, **{**LINES["A線"], "med": medA}))
            b = measures(*make(g, LINES["B線"]["p_base"] * sc, LINES["B線"]["p_rush"] * sc, LINES["B線"]["med"]))
            grid.append({"A_med": medA, "B_p_scale": sc,
                         "A_mean_all": round(a["mean_all_early0"], 2), "B_mean_all": round(b["mean_all_early0"], 2),
                         "A_mean_delayed": round(a["mean_delayed"], 2), "B_mean_delayed": round(b["mean_delayed"], 2),
                         "A_mean_pax": round(a["mean_per_passenger"], 2), "B_mean_pax": round(b["mean_per_passenger"], 2),
                         "A_ratio": round(a["mean_delayed"] / a["mean_all_early0"], 2),
                         "B_ratio": round(b["mean_delayed"] / b["mean_all_early0"], 2),
                         "order_flips": bool((a["mean_all_early0"] < b["mean_all_early0"]) !=
                                             (a["mean_delayed"] < b["mean_delayed"]))})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "robustness_grid.csv", index=False)

    # 確かめ2：朝夕に乗る人の集まり方（1倍・5倍・10倍）
    pr = []
    for k, f in enumerate([1.0, 5.0, 10.0]):
        for ln, prm in LINES.items():
            g = np.random.default_rng(SEED * 7 + k * 3 + (ln == "B線"))
            m = measures(*make(g, **prm, pax_rush=f))
            pr.append({"pax_rush_factor": f, "line": ln, "mean_all_early0": round(m["mean_all_early0"], 2),
                       "mean_per_passenger": round(m["mean_per_passenger"], 2),
                       "ratio_passenger_to_all": round(m["mean_per_passenger"] / m["mean_all_early0"], 2),
                       "share_passengers_on_delayed_pct": round(m["share_passengers_on_delayed_pct"], 2)})
    pr = pd.DataFrame(pr)
    pr.to_csv(RES / "robustness_passengers.csv", index=False)

    # データ：最初の30日
    rows = []
    for ln in LINES:
        dev, pax = sims[ln]
        for d in range(30):
            for t in range(N_TRIP):
                rows.append((ln, d + 1, t + 1, f"{int(DEP[t] // 60):02d}:{int(round(DEP[t] % 60)):02d}",
                             round(float(dev[d, t]), 2), int(pax[d, t])))
    pd.DataFrame(rows, columns=["line", "day", "trip_no", "dep_time", "deviation_min", "passengers"]) \
        .to_csv(DATA / "trips_30days.csv", index=False)

    out = {"lines": res, "B_minus_A_mean_all_early0": round(res["B線"]["mean_all_early0"] - res["A線"]["mean_all_early0"], 2),
           "threshold": thr_df.to_dict("records"), "by_hour": hours.to_dict("records"),
           "robustness_grid": grid.to_dict("records"),
           "robustness_grid_summary": {"n": int(len(grid)), "order_flips": int(grid.order_flips.sum()),
                                       "A_ratio_min": float(grid.A_ratio.min()), "A_ratio_max": float(grid.A_ratio.max()),
                                       "B_ratio_min": float(grid.B_ratio.min()), "B_ratio_max": float(grid.B_ratio.max())},
           "robustness_passengers": pr.to_dict("records")}
    json.dump(out, open(RES / "a1031_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：遅れの分布
    fig, axs = plt.subplots(1, 2, figsize=(8.2, 3.8), sharey=True)
    bins = np.arange(-2, 30.5, 0.5)
    for ax, ln, c in zip(axs, LINES, [BLUE, ORANGE]):
        dev = sims[ln][0].ravel()
        h, e = np.histogram(np.clip(dev, -2, 30), bins=bins)
        ax.bar(e[:-1] + .25, h / dev.size * 100, width=.5, color=c)
        ax.set_yscale("log"); ax.set_xlabel("着いた時刻のずれ（分、マイナスは早着、\n−2分以下は−2、30分以上は30にまとめた）", fontsize=9.5)
        ax.axvline(res[ln]["mean_all_early0"], color=INK, lw=1)
        ax.axvline(res[ln]["mean_delayed"], color=INK, lw=1, ls="--")
        ax.set_title(f"{ln}：全便の平均{res[ln]['mean_all_early0']:.2f}分、遅れた便の平均{res[ln]['mean_delayed']:.2f}分",
                     fontsize=10)
    axs[0].set_ylabel("便の割合（%、対数の目盛り）")
    fig.suptitle("実線＝全便の遅れの平均、点線＝遅れた便（1分以上）の遅れの平均", fontsize=11, y=1.0)
    save(fig, "a1031_hist.png", SRC, y=-0.07)

    # 図2：4つの平均
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    keys = list(NAMES)
    yy = np.arange(len(keys))
    for off, ln, c in [(.2, "A線", BLUE), (-.2, "B線", ORANGE)]:
        vals = [res[ln][k] for k in keys]
        ax.barh(yy - off, vals, height=.38, color=c, label=ln)
        for i, v in enumerate(vals):
            ax.text(max(v, 0) + .08, i - off, f"{v:.2f}分", va="center", fontsize=8.5)
    ax.set_yticks(yy); ax.set_yticklabels([NAMES[k] for k in keys]); ax.invert_yaxis()
    ax.axvline(0, color=GRAY, lw=.8); ax.set_xlim(-0.5, max(res["A線"]["mean_delayed"], res["B線"]["mean_delayed"]) * 1.2)
    ax.set_xlabel("分（365日×1日100便）"); ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("どの平均で比べるかで、A線とB線の順が入れかわる")
    save(fig, "a1031_measures.png", SRC)

    # 図3：時刻ごと（上：乗る人、下：遅れた便の割合）
    fig, axs = plt.subplots(2, 1, figsize=(7.2, 5.2), sharex=True)
    hA = hours[hours.line == "A線"]
    axs[0].bar(hA.hour, hA.pax_per_trip, color=GRAY)
    axs[0].set_ylabel("1便に乗る人（平均）")
    for ln, c in [("A線", BLUE), ("B線", ORANGE)]:
        h = hours[hours.line == ln]
        axs[1].plot(h.hour, h.share_delayed_pct, marker="o", color=c, lw=2, label=ln)
    axs[1].set_ylabel("遅れた便の割合（%）"); axs[1].set_xlabel("出る時刻（時）")
    axs[1].set_xticks(range(6, 24, 2))
    axs[1].legend(frameon=False, fontsize=9)
    axs[0].set_title("朝夕は乗る人が多く、遅れる便も多い（両方の路線で乗る人は同じ置き方）", fontsize=11)
    save(fig, "a1031_hour.png", SRC)
    print(json.dumps({"lines": res, "grid": out["robustness_grid_summary"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
