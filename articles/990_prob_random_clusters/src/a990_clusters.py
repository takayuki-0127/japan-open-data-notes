"""990 偶然の集まり（かたまり）は、どれくらい出るのか？（架空のデータ）

架空の店の、ある焼き菓子の売れた時刻。営業は10時〜20時の600分。1日に売れる個数はポアソン分布（平均30個）、
売れた時刻は営業時間の中で一様（どの時刻も同じ売れやすさ）と作成者が置いた。本当はかたまりのない並びで、
「10分で何個も売れたかたまり」「1時間売れない空白」がどれくらい出るかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import poisson
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 990
SRC = "架空の店の焼き菓子の売れた時刻（作成者が乱数で作成、seed 990）"
OPEN = 600.0          # 営業時間（分）
RATE = 30             # 1日の平均の個数
W = 10.0              # かたまりを見る窓（分）
N_DAYS = 50000
KS = [3, 4, 5, 6, 7]


def day_times(rng, rate=RATE, open_=OPEN):
    n = rng.poisson(rate)
    return np.sort(rng.uniform(0, open_, n))


def sliding_max(t, w):
    """長さ w の窓を自由に動かしたときの、窓に入る個数の最大"""
    if len(t) == 0:
        return 0
    return int((np.searchsorted(t, t + w, "left") - np.arange(len(t))).max())


def fixed_max(t, w, open_=OPEN):
    """10時0分から w 分ずつ区切ったときの、区切りに入る個数の最大"""
    if len(t) == 0:
        return 0
    return int(np.bincount((t // w).astype(int), minlength=int(open_ // w)).max())


def longest_gap(t, open_=OPEN):
    """売れない時間のいちばん長いところ（開店から1個目、最後から閉店までも含む）"""
    e = np.concatenate([[0.0], t, [open_]])
    return float(np.diff(e).max())


def evened_times(rng, rate=RATE, open_=OPEN):
    """作成者が置いた「均した並び」：600分を30個の20分に分け、それぞれに1個ずつ置く"""
    slot = open_ / rate
    return np.sort(np.arange(rate) * slot + rng.uniform(0, slot, rate))


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 1) 基本：かたまりのない売れ方の日を5万日
    rows = []
    days = []
    for d in range(N_DAYS):
        t = day_times(rng)
        if d < 30:
            days.append(t)
        h = np.bincount((t // 60).astype(int), minlength=10)
        rows.append({"n": len(t), "slide10": sliding_max(t, W), "fixed10": fixed_max(t, W),
                     "max_hour": int(h.max()), "empty_hours": int((h == 0).sum()), "gap": longest_gap(t)})
    df = pd.DataFrame(rows)

    lam = RATE * W / OPEN                          # 10分あたりの平均 0.5個
    share = []
    for k in KS:
        formula = 1 - poisson.cdf(k - 1, lam) ** int(OPEN // W)
        share.append({"k": k, "sliding": round(float((df.slide10 >= k).mean()) * 100, 2),
                      "fixed": round(float((df.fixed10 >= k).mean()) * 100, 2),
                      "fixed_formula": round(formula * 100, 2)})
    share = pd.DataFrame(share)
    share["ratio_sliding_fixed"] = (share.sliding / share.fixed).round(2)
    share.to_csv(RES / "cluster_share.csv", index=False)

    # 30個ちょうどの日の、いちばん長い空白の平均（式：600/31 × (1 + 1/2 + … + 1/31)）
    n30 = df[df.n == 30]
    gap_formula = OPEN / 31 * sum(1 / i for i in range(1, 32))
    hour_mean = RATE / 10
    base = {
        "days": N_DAYS, "mean_per_10min": lam, "mean_per_hour": hour_mean,
        "median_slide10": float(df.slide10.median()), "median_slide10_ratio": round(float(df.slide10.median()) / lam, 2),
        "max_abs_fixed_vs_formula": round(float((share.fixed - share.fixed_formula).abs().max()), 2),
        "slide10_dist": {int(k): round(float(v) * 100, 2) for k, v in df.slide10.value_counts(normalize=True).sort_index().items()},
        "max_hour_ge6_pct": round(float((df.max_hour >= 2 * hour_mean).mean()) * 100, 2),
        "max_hour_median": float(df.max_hour.median()),
        "empty_hour_ge1_pct": round(float((df.empty_hours >= 1).mean()) * 100, 2),
        "gap_mean": round(float(df.gap.mean()), 2), "gap_median": round(float(df.gap.median()), 2),
        "gap_ge60_pct": round(float((df.gap >= 60).mean()) * 100, 2),
        "gap_even_spacing": OPEN / RATE,
        "gap_mean_n30": round(float(n30.gap.mean()), 2), "gap_formula_n30": round(gap_formula, 2), "n30_days": int(len(n30)),
    }

    # 均した並び（人が思い描きやすい「でたらめ」として作成者が置いたもの）
    ev = [evened_times(rng) for _ in range(5000)]
    base["evened_days"] = len(ev)
    base["evened"] = {"slide10_ge3_pct": round(float(np.mean([sliding_max(t, W) >= 3 for t in ev])) * 100, 2),
                      "gap_mean": round(float(np.mean([longest_gap(t) for t in ev])), 2)}

    # 2) 本当のかたまりがある日を見分けられるか：10分の間に M 個多く売れた日（ラッシュの日）と、ふつうの日
    detect = []
    for m in [3, 6]:
        hit = {k: 0 for k in KS}
        nr = 10000
        for _ in range(nr):
            t = day_times(rng)
            s = rng.uniform(0, OPEN - W)
            t = np.sort(np.concatenate([t, s + rng.uniform(0, W, m)]))
            sm = sliding_max(t, W)
            for k in KS:
                hit[k] += sm >= k
        for k in KS:
            detect.append({"extra": m, "k": k, "hit_rush_pct": round(hit[k] / nr * 100, 2),
                           "false_alarm_pct": float(share.loc[share.k == k, "sliding"].iloc[0])})
    detect = pd.DataFrame(detect)
    detect.to_csv(RES / "detect_rush.csv", index=False)
    # ラッシュの日が全体の q（5%・10%・30%）のとき、「かたまりあり」の日のうちラッシュの日の割合（上の2つの割合から式で出す）
    ppv = {}
    for q in [0.05, 0.1, 0.3]:
        for _, r in detect.iterrows():
            h, f = r.hit_rush_pct / 100, r.false_alarm_pct / 100
            ppv[f"rush{int(q * 100)}pct_extra{int(r.extra)}_k{int(r.k)}"] = round(q * h / (q * h + (1 - q) * f) * 100, 2)

    # 3) 確かめ：1日の個数と窓の長さを変える（各3,000日）
    grid = []
    for rate in [15, 30, 60, 120]:
        for w in [5, 10, 20, 30]:
            g = np.random.default_rng(SEED * 100 + rate * 7 + int(w))
            mx = np.array([sliding_max(day_times(g, rate), w) for _ in range(3000)])
            ex = rate * w / OPEN
            grid.append({"rate": rate, "window": int(w), "expected": round(ex, 3),
                         "median_max": float(np.median(mx)), "ratio_median": round(float(np.median(mx)) / ex, 2)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_rate_window.csv", index=False)
    grid_info = {"cases": int(len(grid)), "days_each": 3000}

    # データ：最初の30日の売れた時刻
    rec = [{"day": i + 1, "sale_no": j + 1, "minute": round(float(x), 2)} for i, t in enumerate(days) for j, x in enumerate(t)]
    pd.DataFrame(rec).to_csv(DATA / "sales_30days.csv", index=False)
    one = []
    for i, t in enumerate(days):
        one.append({"day": i + 1, "n": len(t), "slide10": sliding_max(t, W), "gap": round(longest_gap(t), 2)})
    one = pd.DataFrame(one)

    out = {"base": base, "cluster_share": share.to_dict("records"), "detect": detect.to_dict("records"),
           "rush_share_among_flagged": ppv, "grid": grid.to_dict("records"), "grid_info": grid_info,
           "first30": {"days_slide10_ge4": int((one.slide10 >= 4).sum()), "days_gap_ge60": int((one.gap >= 60).sum()),
                       "max_slide10": int(one.slide10.max()), "max_gap": float(one.gap.max())},
           "grid_ratio_range": [float(grid.ratio_median.min()), float(grid.ratio_median.max())]}
    pick = int(one[one.n.between(27, 33)].sort_values(["slide10", "gap"], ascending=False).index[0])
    out["fig1_day"] = {k: (float(v) if k == "gap" else int(v)) for k, v in one.loc[pick].items()}
    json.dump(out, open(RES / "a990_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：でたらめの日と均した日の売れた時刻
    t_r = days[pick]
    t_e = evened_times(np.random.default_rng(SEED + 1))
    fig, axes = plt.subplots(2, 1, figsize=(7.4, 3.4), sharex=True)
    for ax, t, lab, c in [(axes[0], t_r, f"でたらめに売れた日（{pick + 1}日目、{len(t_r)}個）", BLUE),
                          (axes[1], t_e, "作成者が均した日（20分ごとに1個、30個）", GRAY)]:
        ax.vlines(t, 0, 1, color=c, lw=1.6)
        ax.set_yticks([]); ax.set_ylim(0, 1.45)
        ax.spines["left"].set_visible(False)
        ax.text(0, 1.12, lab, fontsize=9.5, color=INK)
    # かたまりと空白に印
    cnt = np.searchsorted(t_r, t_r + W, "left") - np.arange(len(t_r))
    i0 = int(cnt.argmax())
    axes[0].axvspan(t_r[i0], t_r[i0] + W, color=ORANGE, alpha=.25, lw=0)
    axes[0].text(t_r[i0] + W / 2, 1.12, f"10分で{int(cnt.max())}個", color=ORANGE, fontsize=9, ha="center")
    e = np.concatenate([[0.0], t_r, [OPEN]]); j = int(np.diff(e).argmax())
    axes[0].axvspan(e[j], e[j + 1], color=GRAY, alpha=.18, lw=0)
    axes[0].text((e[j] + e[j + 1]) / 2, 0.45, f"{e[j + 1] - e[j]:.1f}分\n売れない", color=INK, fontsize=9, ha="center")
    axes[1].set_xticks(np.arange(0, 601, 60)); axes[1].set_xticklabels([f"{10 + i}時" for i in range(11)], fontsize=9)
    axes[1].set_xlabel("売れた時刻（営業時間 10時〜20時）")
    fig.suptitle("どの時刻も同じ売れやすさでも、かたまりと空白が出る", fontsize=13, y=1.02)
    save(fig, "a990_timeline.png", SRC)

    # 図2：「10分で k 個以上」が出た日の割合
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    x = np.arange(len(KS)); bw = 0.38
    ax.bar(x - bw / 2, share.sliding, bw, color=BLUE, label="窓を自由に動かす（どの10分でも）")
    ax.bar(x + bw / 2, share.fixed, bw, color=LIGHT, label="10時0分から10分ずつ区切る")
    ax.plot(x + bw / 2, share.fixed_formula, "o", color=INK, ms=4, label="区切ったときの式の値")
    for i, (a, b) in enumerate(zip(share.sliding, share.fixed)):
        ax.text(i - bw / 2, a + 1.5, f"{a:.1f}%", ha="center", fontsize=8.5)
        ax.text(i + bw / 2, b + 1.5, f"{b:.1f}%", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels([f"{k}個以上" for k in KS])
    ax.set_xlabel("10分の間に売れた個数（10分あたりの平均は0.5個）")
    ax.set_ylabel("その日がある割合（%、5万日）"); ax.set_ylim(0, 105)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    ax.set_title("1日30個がでたらめに売れる店で、「10分で何個も」が出た日の割合")
    save(fig, "a990_share.png", SRC)

    # 図3：1日の個数と窓の長さを変えたとき、いちばん混んだ窓が平均の何倍か
    piv = grid.pivot(index="rate", columns="window", values="ratio_median")
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    im = ax.imshow(piv.values, cmap="Blues", aspect="auto", vmin=0, vmax=piv.values.max() * 1.15)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            ax.text(j, i, f"{v:.1f}倍", ha="center", va="center", fontsize=10,
                    color="white" if v > piv.values.max() * 0.6 else INK)
    ax.set_xticks(range(piv.shape[1])); ax.set_xticklabels([f"{c}分" for c in piv.columns])
    ax.set_yticks(range(piv.shape[0])); ax.set_yticklabels([f"{r}個" for r in piv.index])
    ax.set_xlabel("かたまりを見る窓の長さ"); ax.set_ylabel("1日の平均の個数")
    ax.spines["left"].set_visible(False); ax.spines["bottom"].set_visible(False)
    ax.set_title("いちばん混んだ窓の個数は、窓の平均の何倍か（中央値、各3,000日）", fontsize=12)
    save(fig, "a990_grid.png", SRC)

    out["run_sec"] = round(time.time() - t0, 1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
