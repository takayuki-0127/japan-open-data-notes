"""899 毎月3%の伸びは、1年で36%なのか？（架空のデータ）

毎月3%ずつ伸びると、伸びた分にもまた3%がかかるので、1年では 1.03 の12乗 − 1 ＝ 42.6% になる（複利）。
例の計算に加え、架空の会社1,000社の会員数（毎月の伸びの平均と振れを作成者が置いたもの）を作り、
「月の伸びの平均×12」「月の伸びの平均で複利」「実際」の3つがどれだけ離れるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 899
SRC = "架空の会社の会員数（作成者が乱数で作成、seed 899）"
N_CO = 1000
START = 10000  # 人


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 例：毎月 g% の伸びが続いたとき
    ex = []
    for g in [1, 2, 3, 5, 10]:
        f = g / 100
        row = {"monthly_pct": g}
        for months in [12, 24, 36]:
            row[f"times_{months}"] = round(g * months, 2)
            row[f"compound_{months}"] = round(((1 + f) ** months - 1) * 100, 2)
        ex.append(row)
    pd.DataFrame(ex).to_csv(RES / "examples.csv", index=False)
    rev = {"annual_36_monthly_compound": round(((1.36) ** (1 / 12) - 1) * 100, 3),
           "annual_36_monthly_divide12": 3.0,
           "annual_42_6_divide12": round(((1.03 ** 12) - 1) * 100 / 12, 3),
           "members_after_12_compound": round(START * 1.03 ** 12, 1),
           "members_after_12_linear": round(START * 1.36, 1),
           "members_after_36_compound": round(START * 1.03 ** 36, 1),
           "members_after_36_linear": round(START * (1 + 0.03 * 36), 1),
           "ratio_after_36_compound": round(1.03 ** 36, 2)}
    m = np.arange(0, 37)
    pd.DataFrame({"month": m, "compound_3pct": np.round(START * 1.03 ** m, 1),
                  "linear_3pct_of_start": np.round(START * (1 + 0.03 * m), 1)}).to_csv(DATA / "example_path_3pct.csv", index=False)

    # 2) 架空の会社1,000社・12か月（毎月の伸びは平均3%・標準偏差2%の正規分布）
    def run(rng, n, months, g, sd):
        r = rng.normal(g, sd, (n, months))
        r = np.maximum(r, -0.95)
        actual = (np.prod(1 + r, 1) - 1) * 100
        mean_r = r.mean(1)
        times = mean_r * months * 100
        comp = ((1 + mean_r) ** months - 1) * 100
        return r, actual, times, comp

    r, actual, times, comp = run(rng, N_CO, 12, 0.03, 0.02)
    mem = np.round(START * np.cumprod(1 + r, 1)).astype(int)
    d = pd.DataFrame(mem, columns=[f"m{k:02d}" for k in range(1, 13)])
    d.insert(0, "m00", START); d.insert(0, "company_id", np.arange(1, N_CO + 1))
    d.to_csv(DATA / "companies_12months.csv", index=False)
    base = {"actual_mean": round(float(actual.mean()), 2), "actual_median": round(float(np.median(actual)), 2),
            "actual_p10": round(float(np.quantile(actual, .1)), 2), "actual_p90": round(float(np.quantile(actual, .9)), 2),
            "times12_mean": round(float(times.mean()), 2), "compound_mean": round(float(comp.mean()), 2),
            "err_times12_mean": round(float((times - actual).mean()), 2),
            "err_compound_mean": round(float((comp - actual).mean()), 2),
            "err_times12_median": round(float(np.median(times - actual)), 2),
            "err_compound_median": round(float(np.median(comp - actual)), 2),
            "share_times12_below_actual": round(float((times < actual).mean()), 3),
            "share_compound_closer": round(float((np.abs(comp - actual) < np.abs(times - actual)).mean()), 3)}

    # 3) 確かめ：月の伸び・振れ・月数（各2,000社）
    rob = []
    i = 0
    for g in [0.01, 0.03, 0.05]:
        for sd in [0.0, 0.02, 0.05, 0.10]:
            for months in [12, 24, 36]:
                i += 1
                _, a, t, c = run(np.random.default_rng(SEED * 100 + i), 2000, months, g, sd)
                rob.append({"monthly_pct": g * 100, "sd_pct": sd * 100, "months": months,
                            "actual_median": round(float(np.median(a)), 2), "actual_mean": round(float(a.mean()), 2),
                            "times_mean": round(float(t.mean()), 2), "compound_mean": round(float(c.mean()), 2),
                            "err_times_mean": round(float((t - a).mean()), 2),
                            "err_times_median": round(float(np.median(t - a)), 2),
                            "err_compound_mean": round(float((c - a).mean()), 2),
                            "err_compound_median": round(float(np.median(c - a)), 2),
                            "share_compound_closer": round(float((np.abs(c - a) < np.abs(t - a)).mean()), 3)})
    rob = pd.DataFrame(rob) + 0.0  # −0.0 を 0.0 にそろえる
    rob.to_csv(RES / "robustness.csv", index=False)
    pick = lambda g, sd, mo: rob[(rob.monthly_pct == g) & (rob.sd_pct == sd) & (rob.months == mo)].iloc[0]
    rs = {"share_compound_closer_min": float(rob.share_compound_closer.min()),
          "share_compound_closer_max": float(rob.share_compound_closer.max()),
          "err_times_median_min": float(rob.err_times_median.min()), "err_times_median_max": float(rob.err_times_median.max()),
          "err_compound_median_min": float(rob.err_compound_median.min()),
          "err_compound_median_max": float(rob.err_compound_median.max()),
          "g3_sd10_m12": pick(3, 10, 12)[["actual_median", "times_mean", "compound_mean", "err_times_median", "err_compound_median",
                                         "share_compound_closer"]].to_dict(),
          "g3_sd10_m36": pick(3, 10, 36)[["actual_median", "times_mean", "compound_mean", "err_times_median", "err_compound_median",
                                         "share_compound_closer"]].to_dict(),
          "g1_sd10_m12": pick(1, 10, 12)[["actual_median", "times_mean", "compound_mean", "err_times_median", "err_compound_median",
                                         "share_compound_closer"]].to_dict()}
    rs = json.loads(json.dumps(rs, default=float))

    out = {"examples": ex, "reverse_and_members": rev, "base_1000companies_12months": base, "robustness_summary": rs,
           "note": "振れのない例は (1+g)^月数 − 1 の式どおり。×月数との差は、伸びた分にまた伸びがかかる分"}
    json.dump(out, open(RES / "a899_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：3%で36か月
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(m, START * 1.03 ** m / 1000, color=ORANGE, lw=2, label="毎月3%の複利（伸びた分にも3%）")
    ax.plot(m, START * (1 + 0.03 * m) / 1000, color=BLUE, lw=2, ls="--", label="始めの3%ずつ足す（×月数）")
    for mo in [12, 36]:
        ax.scatter([mo, mo], [START * 1.03 ** mo / 1000, START * (1 + 0.03 * mo) / 1000], color=[ORANGE, BLUE], s=20, zorder=3)
    ax.text(11.5, START * 1.03 ** 12 / 1000 + 0.5, f"12か月 +{ex[2]['compound_12']:.1f}%", color=ORANGE, fontsize=9, ha="right")
    ax.text(12.5, START * 1.36 / 1000 - 1.6, f"12か月 +{ex[2]['times_12']:.0f}%", color=BLUE, fontsize=9)
    ax.text(27.5, START * 1.03 ** 36 / 1000 - 0.6, f"36か月 +{ex[2]['compound_36']:.1f}%", color=ORANGE, fontsize=9)
    ax.text(29.5, START * (1 + 0.03 * 36) / 1000 - 2.6, f"36か月 +{ex[2]['times_36']:.0f}%", color=BLUE, fontsize=9)
    ax.set_xlabel("月"); ax.set_ylabel("会員数（千人、始めは1万人）"); ax.set_xticks(range(0, 37, 6))
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("毎月3%の伸びは、1年で42.6%、3年で約2.9倍")
    save(fig, "a899_example.png", SRC)

    # 図2：月の伸びごとの、12か月の伸び（×12 と 複利）
    e = pd.DataFrame(ex)
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    xs = np.arange(len(e)); w = 0.38
    ax.bar(xs - w / 2, e.times_12, w, color=BLUE, label="月の伸び×12")
    ax.bar(xs + w / 2, e.compound_12, w, color=ORANGE, label="複利で12か月（実際）")
    for xx, a, b in zip(xs, e.times_12, e.compound_12):
        ax.text(xx - w / 2, a + 3, f"{a:g}", ha="center", fontsize=9)
        ax.text(xx + w / 2, b + 3, f"{b:.1f}", ha="center", fontsize=9)
    ax.set_xticks(xs); ax.set_xticklabels([f"毎月{g}%" for g in e.monthly_pct])
    ax.set_ylabel("12か月の伸び（%）"); ax.set_ylim(0, 230)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("月の伸びが大きいほど、×12 との差は開く（振れのない場合）")
    save(fig, "a899_by_rate.png", SRC)

    # 図3：振れがあるとき（月3%・12か月）：3つの読み方の誤差
    q = rob[(rob.monthly_pct == 3)]
    fig, axs = plt.subplots(1, 2, figsize=(8.2, 3.8))
    for months, c in zip([12, 24, 36], [LIGHT, BLUE, INK]):
        z = q[q.months == months]
        axs[0].plot(z.sd_pct, z.err_times_median, "o-", color=c, label=f"{months}か月")
        axs[1].plot(z.sd_pct, z.err_compound_median, "o-", color=c, label=f"{months}か月")
    for a in axs:
        a.axhline(0, color=GRAY, lw=.8, ls="--"); a.set_xlabel("毎月の伸びの振れ（標準偏差、%）")
    axs[0].set_ylabel("ずれ（ポイント、読み方−実際）"); axs[1].set_ylabel("ずれ（ポイント）")
    axs[0].set_title("月の伸びの平均×月数（中央値）", fontsize=11)
    axs[1].set_title("月の伸びの平均で複利（中央値）", fontsize=11)
    axs[0].legend(frameon=False, fontsize=9)
    fig.suptitle("毎月平均3%：×月数は少なく出て、振れが大きいと複利の読みも外れる", fontsize=12)
    fig.tight_layout()
    save(fig, "a899_robustness.png", SRC)

    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(rob.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
