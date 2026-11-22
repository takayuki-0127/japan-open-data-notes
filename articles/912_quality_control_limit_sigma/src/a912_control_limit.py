"""912 管理図の線を3σにするか2σにするかで、止める回数はどう変わるのか？（架空のデータ）

架空の工場で作る樹脂の部品の長さ（狙い 20.00mm、1個ごとのばらつき σ=0.05mm）。
1時間ごとに5個を測って平均を打つ管理図（Xbar 管理図）。1年は 250日×8時間＝2,000時間（点）。
線（管理限界）は 中心 ± k × σ/√5。k を 2・2.5・3 と、3σ＋補助ルール（3点中2点が同じ側の2σの外）で比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import norm
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 912
SRC = "架空の工場の部品の長さ（作成者が乱数で作成、seed 912）"
MU0, SIG, N, SPEC = 20.00, 0.05, 5, 0.15      # 狙い・1個のばらつき・1回に測る個数・規格の幅（±）
HOURS = 2000                                 # 1年の点の数
PER_HOUR = 100                               # 1時間に作る個数
C4 = 0.9400                                  # n=5 の c4
SE = SIG / np.sqrt(N)
RULES = ["2σ", "2.5σ", "3σ", "3σ＋補助ルール"]
KS = {"2σ": 2.0, "2.5σ": 2.5, "3σ": 3.0, "3σ＋補助ルール": 3.0}


def out_frac(delta):
    """平均が delta×σ ずれたときの規格外の割合（1個あたり）"""
    z = SPEC / SIG
    return norm.cdf(-z + delta) + norm.cdf(-z - delta)


def estimate_limits(rng, m, n_sub=25, between=0.0, phi=0.0):
    """最初の n_sub 時間（ずれなし）から、中心と σ を見積もる。m 工場分。
    σ は5個の中のばらつき（s の平均÷c4）から、中心は点の平均から。between>0 なら時間ごとの揺れも入る"""
    x = rng.normal(MU0, SIG, (m, n_sub, N))
    if between > 0:
        d = np.zeros((m, n_sub))
        d[:, 0] = rng.normal(0, between * SE, m)
        for t in range(1, n_sub):
            d[:, t] = phi * d[:, t - 1] + rng.normal(0, between * SE * np.sqrt(1 - phi ** 2), m)
        x = x + d[:, :, None]
    center = x.mean(axis=(1, 2))
    sig_hat = x.std(axis=2, ddof=1).mean(1) / C4
    return center, sig_hat


def run_year(rng, m, rule, center, sig_hat, rate=0.0, size=(0.5, 2.0), between=0.0, phi=0.0, need_out=False):
    """m 工場の1年を1時間ずつ進める。
    rate：1時間あたりにずれが起きる確率。size：ずれの大きさ（σの何倍、一様）。向きは上下半々。
    between：時間ごとの揺れ（平均の揺れの標準偏差を σ/√5 の何倍か）。phi：その揺れの引き継ぎ。
    返り値：止めた回数（ずれなし＝空振り／ずれあり）、ずれの続いた時間、規格外の個数（期待値）の増え"""
    k = KS[rule]
    se_hat = sig_hat / np.sqrt(N)
    shift = np.zeros(m)
    drift = rng.normal(0, between * SE, m) if between > 0 else np.zeros(m)
    prev1 = np.zeros(m, dtype=int)  # 1つ前の点の 2σ外（+1 上・-1 下・0 内）
    prev2 = np.zeros(m, dtype=int)
    false_stop = np.zeros(m, dtype=int)
    true_stop = np.zeros(m, dtype=int)
    shift_hours = np.zeros(m)
    extra_out = np.zeros(m)
    delays = []
    start = np.full(m, -1)
    base = out_frac(0.0)
    innov = between * SE * np.sqrt(1 - phi ** 2)
    for t in range(HOURS):
        new = (shift == 0) & (rng.random(m) < rate)
        if new.any():
            d = rng.uniform(size[0], size[1], new.sum()) * rng.choice([-1, 1], new.sum())
            shift[new] = d
            start[new] = t
        if between > 0:
            drift = phi * drift + rng.normal(0, innov, m)
        mean_t = MU0 + shift * SIG + drift
        xbar = rng.normal(mean_t, SE)
        z = (xbar - center) / se_hat
        stop = np.abs(z) > k
        if rule == "3σ＋補助ルール":
            side = np.where(z > 2, 1, np.where(z < -2, -1, 0))
            two_of_three = (side != 0) & ((side == prev1) | (side == prev2))
            stop = stop | two_of_three
            prev2, prev1 = prev1, side
        on = shift != 0
        shift_hours += on
        # 規格外の個数の増え（期待値）：ずれと時間ごとの揺れの両方を入れる
        if need_out:
            dev = (mean_t - MU0) / SIG
            extra_out += PER_HOUR * (out_frac(dev) - base)
        ts = stop & on
        fs = stop & ~on
        true_stop += ts
        false_stop += fs
        if ts.any():
            delays.extend((t - start[ts] + 1).tolist())
            shift[ts] = 0
            start[ts] = -1
        if stop.any() and rule == "3σ＋補助ルール":
            prev1[stop] = 0
            prev2[stop] = 0
    return {"false_stop": false_stop, "true_stop": true_stop, "shift_hours": shift_hours,
            "extra_out": extra_out, "delays": np.array(delays)}


def q(a, p):
    return round(float(np.quantile(a, p)), 1)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    out = {"setting": {"target_mm": MU0, "sigma_mm": SIG, "n_per_hour": N, "spec_pm_mm": SPEC,
                       "hours_per_year": HOURS, "parts_per_hour": PER_HOUR,
                       "out_frac_no_shift": round(float(out_frac(0.0)), 5), "c4_n5": C4, "days": 250, "hours_per_day": 8}}

    # 1) ずれのない1年：空振りの回数（線を正しく知っている場合の式・25時間で見積もった線で1,000工場）
    m = 1000
    center, sig_hat = estimate_limits(np.random.default_rng(SEED * 10 + 1), m)
    center100, sig100 = estimate_limits(np.random.default_rng(SEED * 10 + 2), m, 100)
    rows = []
    for rule in RULES:
        k = KS[rule]
        p_formula = 2 * norm.sf(k)
        r25 = run_year(np.random.default_rng(SEED * 100 + RULES.index(rule)), m, rule, center, sig_hat)
        r100 = run_year(np.random.default_rng(SEED * 200 + RULES.index(rule)), m, rule, center100, sig100)
        rk = run_year(np.random.default_rng(SEED * 300 + RULES.index(rule)), m, rule,
                      np.full(m, MU0), np.full(m, SIG))
        rows.append({"rule": rule,
                     "formula_per_year": round(HOURS * p_formula, 1) if rule != "3σ＋補助ルール" else None,
                     "known_mean": round(float(rk["false_stop"].mean()), 1),
                     "est25_median": q(r25["false_stop"], .5), "est25_p10": q(r25["false_stop"], .1),
                     "est25_p90": q(r25["false_stop"], .9),
                     "est100_median": q(r100["false_stop"], .5), "est100_p10": q(r100["false_stop"], .1),
                     "est100_p90": q(r100["false_stop"], .9)})
    false_tab = pd.DataFrame(rows)
    false_tab.to_csv(RES / "false_stops_no_shift.csv", index=False)
    out["false_stops_no_shift"] = rows

    # 2) ずれが起きたとき：見つけるまでの時間と、その間に出る規格外の個数（線は正しく知っている）
    rows = []
    for rule in RULES:
        for delta in [0.5, 1.0, 1.5, 2.0]:
            r = run_year(np.random.default_rng(SEED * 400 + int(delta * 10) + 7 * RULES.index(rule)), 2000, rule,
                         np.full(2000, MU0), np.full(2000, SIG), rate=1.0, size=(delta, delta))
            d = r["delays"]
            k = KS[rule]
            p1 = norm.cdf(-k + delta * np.sqrt(N)) + norm.cdf(-k - delta * np.sqrt(N))
            rows.append({"rule": rule, "delta_sigma": delta, "delay_mean_h": round(float(d.mean()), 2),
                         "delay_median_h": float(np.median(d)), "delay_p90_h": float(np.quantile(d, .9)),
                         "delay_formula_h": round(1 / p1, 2) if rule != "3σ＋補助ルール" else None,
                         "extra_out_per_shift": round(float(d.mean() * PER_HOUR * (out_frac(delta) - out_frac(0))), 1),
                         "n_shifts": int(len(d))})
    det = pd.DataFrame(rows)
    det.to_csv(RES / "detection_delay.csv", index=False)
    out["detection_delay"] = rows

    # 3) 1年の運転：ずれは平均100時間に1回起き、大きさは σ の0.5〜2倍。線は最初の25時間で見積もる
    m = 1000
    c3, s3 = estimate_limits(np.random.default_rng(SEED * 10 + 3), m)
    rows = []
    year_runs = {}
    for rule in RULES:
        r = run_year(np.random.default_rng(SEED * 500 + RULES.index(rule)), m, rule, c3, s3, rate=0.01, need_out=True)
        year_runs[rule] = r
        rows.append({"rule": rule, "false_stop_mean": round(float(r["false_stop"].mean()), 1),
                     "false_stop_p10": q(r["false_stop"], .1), "false_stop_p90": q(r["false_stop"], .9),
                     "true_stop_mean": round(float(r["true_stop"].mean()), 1),
                     "share_false": round(float(r["false_stop"].sum() / (r["false_stop"].sum() + r["true_stop"].sum())), 3),
                     "shift_hours_mean": round(float(r["shift_hours"].mean()), 1),
                     "extra_out_mean": round(float(r["extra_out"].mean()), 1),
                     "delay_mean_h": round(float(r["delays"].mean()), 2)})
    year = pd.DataFrame(rows)
    base3 = float(year.set_index("rule").loc["3σ", "extra_out_mean"])
    year["extra_out_vs_3s"] = (year.extra_out_mean / base3 - 1).round(3)
    rows = year.to_dict("records")
    year.to_csv(RES / "one_year_operation.csv", index=False)
    out["one_year_operation"] = rows

    # 4) 確かめ：時間ごとの揺れ（σ/√5 の0・0.5・1倍、引き継ぎ0・0.5）を置き、線は5個の中のばらつきから引く
    rows = []
    for between in [0.0, 0.5, 1.0]:
        for phi in [0.0, 0.5]:
            if between == 0 and phi > 0:
                continue
            cc, ss = estimate_limits(np.random.default_rng(SEED * 10 + 4), 1000, between=between, phi=phi)
            for rule in RULES:
                r = run_year(np.random.default_rng(SEED * 600 + int(between * 10) + int(phi * 100) + RULES.index(rule)),
                             1000, rule, cc, ss, between=between, phi=phi)
                rows.append({"between_x_se": between, "phi": phi, "rule": rule,
                             "false_stop_median": q(r["false_stop"], .5), "false_stop_p10": q(r["false_stop"], .1),
                             "false_stop_p90": q(r["false_stop"], .9)})
    rob = pd.DataFrame(rows)
    rob.to_csv(RES / "robust_between_hour.csv", index=False)
    out["robust_between_hour"] = rows

    # 4b) 確かめ：ずれの起きやすさ（平均400・100・25時間に1回）×大きさ（0.5〜1・0.5〜2・1〜3σ）の9通り
    rows = []
    for rate in [1 / 400, 1 / 100, 1 / 25]:
        for size in [(0.5, 1.0), (0.5, 2.0), (1.0, 3.0)]:
            cc, ss = estimate_limits(np.random.default_rng(SEED * 10 + 5), 500)
            for rule in RULES:
                r = run_year(np.random.default_rng(SEED * 700 + int(1 / rate) + int(size[1] * 10) + RULES.index(rule)),
                             500, rule, cc, ss, rate=rate, size=size, need_out=True)
                rows.append({"every_h": int(round(1 / rate)), "size": f"{size[0]}〜{size[1]}", "rule": rule,
                             "false_stop_mean": round(float(r["false_stop"].mean()), 1),
                             "true_stop_mean": round(float(r["true_stop"].mean()), 1),
                             "extra_out_mean": round(float(r["extra_out"].mean()), 1)})
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "robust_rate_size.csv", index=False)
    # 2σ と 3σ の比べ：空振りの倍率・規格外の減り
    cmp_rows = []
    for (e, s), g in grid.groupby(["every_h", "size"], sort=False):
        g = g.set_index("rule")
        cmp_rows.append({"every_h": int(e), "size": s,
                         "false_2s": float(g.loc["2σ", "false_stop_mean"]), "false_3s": float(g.loc["3σ", "false_stop_mean"]),
                         "extra_out_2s": float(g.loc["2σ", "extra_out_mean"]), "extra_out_3s": float(g.loc["3σ", "extra_out_mean"]),
                         "out_reduction_2s_vs_3s": round(1 - float(g.loc["2σ", "extra_out_mean"]) / float(g.loc["3σ", "extra_out_mean"]), 3),
                         "true_share_2s": round(float(g.loc["2σ", "true_stop_mean"] / (g.loc["2σ", "true_stop_mean"] + g.loc["2σ", "false_stop_mean"])), 3),
                         "true_share_3s": round(float(g.loc["3σ", "true_stop_mean"] / (g.loc["3σ", "true_stop_mean"] + g.loc["3σ", "false_stop_mean"])), 3)})
    out["robust_rate_size"] = cmp_rows
    out["robust_rate_size_range"] = {
        "out_reduction_2s_vs_3s_min": min(r["out_reduction_2s_vs_3s"] for r in cmp_rows),
        "out_reduction_2s_vs_3s_max": max(r["out_reduction_2s_vs_3s"] for r in cmp_rows),
        "true_share_2s_min": min(r["true_share_2s"] for r in cmp_rows),
        "true_share_2s_max": max(r["true_share_2s"] for r in cmp_rows),
        "true_share_3s_min": min(r["true_share_3s"] for r in cmp_rows),
        "true_share_3s_max": max(r["true_share_3s"] for r in cmp_rows)}

    # data：1工場の200時間。作成者が100時間目から σ の1倍のずれを置いた例（3σの線を超えたら直す）
    g = np.random.default_rng(SEED * 900)
    cen, sh = estimate_limits(g, 1)
    shift, rows, fixed_at = 0.0, [], None
    for t in range(200):
        if t == 99:
            shift = 1.0
        xb = g.normal(MU0 + shift * SIG, SE)
        z = (xb - cen[0]) / (sh[0] / np.sqrt(N))
        rows.append({"hour": t + 1, "true_shift_sigma": round(shift, 3), "xbar_mm": round(xb, 4),
                     "z": round(z, 3), "beyond_2s": int(abs(z) > 2), "beyond_3s": int(abs(z) > 3)})
        if abs(z) > 3 and shift != 0:
            shift, fixed_at = 0.0, t + 1
    dd = pd.DataFrame(rows)
    dd.to_csv(DATA / "one_factory_200h.csv", index=False)
    no = dd.true_shift_sigma == 0
    out["data_one_factory"] = {"center_mm": round(float(cen[0]), 4), "sigma_hat_mm": round(float(sh[0]), 4),
                               "shift_start_hour": 100, "found_at_hour_3s": fixed_at,
                               "first_2s_in_shift_hour": int(dd[(~no) & (dd.beyond_2s == 1)].hour.min()) if ((~no) & (dd.beyond_2s == 1)).any() else None,
                               "hours_with_shift": int((~no).sum()),
                               "no_shift_beyond_2s": int(dd[no].beyond_2s.sum()), "no_shift_beyond_3s": int(dd[no].beyond_3s.sum())}

    json.dump(out, open(RES / "a912_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1工場の200時間の点と線
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    se_h = sh[0] / np.sqrt(N)
    ax.plot(dd.hour, dd.xbar_mm, color=BLUE, lw=.8, marker="o", ms=2.2)
    for k, c, ls in [(3, ORANGE, "-"), (2, GRAY, "--")]:
        for s in [1, -1]:
            ax.hlines(cen[0] + s * k * se_h, 0, 201, color=c, lw=1, ls=ls)
    ax.hlines(cen[0], 0, 201, color=INK, lw=.6)
    on = dd.true_shift_sigma != 0
    ax.fill_between(dd.hour, ax.get_ylim()[0], ax.get_ylim()[1], where=on, color=LIGHT, alpha=.5, lw=0,
                    label="作成者が置いたずれのある時間")
    ax.set_xlim(-5, 214)
    ax.text(204, cen[0] + 3 * se_h, "3σ", color=ORANGE, va="center", fontsize=9)
    ax.text(204, cen[0] + 2 * se_h, "2σ", color=GRAY, va="center", fontsize=9)
    ax.set_xlabel("時間（1時間に5個を測った平均の点）"); ax.set_ylabel("5個の長さの平均（mm）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower left")
    ax.set_title("1つの工場の200時間（100時間目からσの1倍のずれを置いた例）")
    save(fig, "a912_chart.png", SRC)

    # 図2：1年の運転での空振りと本当のずれでの止め、規格外の増え
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.8))
    y = np.arange(len(year))[::-1]
    axes[0].barh(y, year.false_stop_mean, color=GRAY, label="空振り（ずれなし）")
    axes[0].barh(y, year.true_stop_mean, left=year.false_stop_mean, color=BLUE, label="本当のずれ")
    for i, (f, tr) in enumerate(zip(year.false_stop_mean, year.true_stop_mean)):
        axes[0].text(f + tr + 2, y[i], f"{f:.0f}＋{tr:.0f}", va="center", fontsize=8.5)
    axes[0].set_yticks(y); axes[0].set_yticklabels(year.rule)
    axes[0].set_xlabel("1年に止めた回数（1,000工場の平均）"); axes[0].set_xlim(0, year.false_stop_mean.max() * 1.35 + 20)
    axes[0].legend(frameon=False, fontsize=8, loc="lower right")
    axes[1].barh(y, year.extra_out_mean, color=ORANGE)
    for i, v in enumerate(year.extra_out_mean):
        axes[1].text(v + 5, y[i], f"{v:.0f}個", va="center", fontsize=8.5)
    axes[1].set_yticks(y); axes[1].set_yticklabels([])
    axes[1].set_xlabel("ずれで増えた規格外の個数（1年、期待値）"); axes[1].set_xlim(0, year.extra_out_mean.max() * 1.3)
    fig.suptitle("線を狭くすると規格外は減るが、止める回数の多くは空振りになる", fontsize=12.5)
    fig.tight_layout()
    save(fig, "a912_year_tradeoff.png", SRC)

    # 図3：時間ごとの揺れを置いたときの空振り（中央値）
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    labs = []
    sub = rob[rob.rule.isin(["2σ", "3σ"])]
    conds = sub[["between_x_se", "phi"]].drop_duplicates().values.tolist()
    x = np.arange(len(conds))
    for j, (rule, c) in enumerate([("2σ", GRAY), ("3σ", ORANGE)]):
        vals = [float(sub[(sub.rule == rule) & (sub.between_x_se == b) & (sub.phi == p)].false_stop_median.iloc[0]) for b, p in conds]
        ax.bar(x + (j - .5) * .38, vals, .38, color=c, label=rule)
        for xi, v in zip(x, vals):
            ax.text(xi + (j - .5) * .38, v + 3, f"{v:.0f}", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels([f"揺れ{b:g}倍\n引き継ぎ{p:g}" for b, p in conds], fontsize=9)
    ax.set_ylabel("ずれのない1年の空振り（回、中央値）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("時間ごとの揺れがあると、3σの線でも空振りが増える")
    save(fig, "a912_between_hour.png", SRC, y=-0.06)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:4000])
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
