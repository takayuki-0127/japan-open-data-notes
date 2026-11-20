"""894 「月の目標額を超えた」は、何か月続いたら実力と言えるのか？（架空のデータ）

架空の副業の人たち。人ごとに「本当の水準」（毎月の売上の長い目で見た平均を、目標額を1として表したもの）を置き、
毎月の売上は本当の水準のまわりで月ごとに振れる（前の月の振れを少し引き継ぐ）。
「目標額以上が k か月続いた」人のうち、本当の水準が目標額以上の人が何%いるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 894
SRC = "架空の副業の人と月の売上（作成者が乱数で作成、seed 894）"
T_OBS, T_FUT = 24, 12
KS = list(range(1, 13))
BASE = {"median": 0.8, "spread": 0.35, "sigma": 0.30, "rho": 0.3}


def simulate(rng, n, median, spread, sigma, rho, T=T_OBS + T_FUT, true=None):
    """本当の水準 true と、毎月の売上（目標額＝1）を作る"""
    if true is None:
        true = np.exp(rng.normal(np.log(median), spread, n))
    e = np.empty((n, T))
    e[:, 0] = rng.normal(0, 1, n)
    s = np.sqrt(1 - rho ** 2)
    for t in range(1, T):
        e[:, t] = rho * e[:, t - 1] + s * rng.normal(0, 1, n)
    x = true[:, None] * np.exp(sigma * e - sigma ** 2 / 2)
    return true, x


def first_run_month(x, k, T=T_OBS):
    """最初の T か月のうち、目標額以上が k か月続いた最初の月（0始まり、なければ -1）"""
    above = x[:, :T] >= 1.0
    run = np.zeros(len(x), int)
    first = np.full(len(x), -1)
    for t in range(T):
        run = np.where(above[:, t], run + 1, 0)
        hit = (run >= k) & (first < 0)
        first[hit] = t
    return first


def evaluate(true, x, ks=KS):
    rows = []
    good = true >= 1.0
    for k in ks:
        f = first_run_month(x, k)
        ach = f >= 0
        # 達成した月の次の12か月の平均（観測できる「その後」）
        nxt = np.full(len(x), np.nan)
        idx = np.where(ach)[0]
        for t in np.unique(f[idx]):
            sel = idx[f[idx] == t]
            nxt[sel] = x[sel, t + 1:t + 13].mean(1)
        rows.append({"k": k, "share_achieved": ach.mean(),
                     "ppv_true_ge_target": good[ach].mean() if ach.any() else np.nan,
                     "next12_mean_ge_target": (nxt[ach] >= 1.0).mean() if ach.any() else np.nan,
                     "true_median_achievers": float(np.median(true[ach])) if ach.any() else np.nan,
                     "hit_rate_among_true_ge": ach[good].mean(), "hit_rate_among_true_lt": ach[~good].mean()})
    return pd.DataFrame(rows)


def avg_rule(true, x, window):
    """最初の24か月のうち、最後の window か月の平均が目標額以上か（比べるための別の読み方）"""
    good = true >= 1.0
    m = x[:, T_OBS - window:T_OBS].mean(1) >= 1.0
    return {"window": window, "share_flagged": float(m.mean()), "ppv_true_ge_target": float(good[m].mean()),
            "hit_rate_among_true_ge": float(m[good].mean())}


def k_needed(df, level=0.8):
    ok = df[df.ppv_true_ge_target >= level]
    return int(ok.k.min()) if len(ok) else None


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    N = 40000
    true, x = simulate(rng, N, **BASE)
    base = evaluate(true, x)
    base.round(4).to_csv(RES / "base_by_k.csv", index=False)
    share_true_ge = float((true >= 1).mean())
    rules = [avg_rule(true, x, w) for w in (3, 6, 12, 24)]
    pd.DataFrame(rules).round(4).to_csv(RES / "average_rules.csv", index=False)

    # 1人の本当の水準ごとに、24か月のうちにk か月続く確率
    levels = np.round(np.arange(0.6, 1.41, 0.05), 2)
    curve = []
    for lv in levels:
        tr, xx = simulate(np.random.default_rng(SEED * 10 + int(lv * 100)), 20000, None, None, BASE["sigma"],
                          BASE["rho"], true=np.full(20000, lv))
        for k in (1, 3, 6, 12):
            curve.append({"true_level": float(lv), "k": k, "p_run_within_24": float((first_run_month(xx, k) >= 0).mean())})
    curve = pd.DataFrame(curve)
    curve.round(4).to_csv(RES / "run_prob_by_level.csv", index=False)

    # 確かめ：月の振れ×振れの引き継ぎ×人どうしの水準（27通り）
    grid = []
    for i, sg in enumerate([0.15, 0.30, 0.45]):
        for j, rh in enumerate([0.0, 0.3, 0.6]):
            for l, md in enumerate([0.6, 0.8, 1.0]):
                g_rng = np.random.default_rng(SEED * 100 + i * 9 + j * 3 + l)
                tr, xx = simulate(g_rng, 20000, md, BASE["spread"], sg, rh)
                ev = evaluate(tr, xx, ks=[1, 3, 6, 12])
                row = {"sigma": sg, "rho": rh, "median": md, "share_true_ge": float((tr >= 1).mean())}
                for _, r in ev.iterrows():
                    row[f"ppv_k{int(r.k)}"] = float(r.ppv_true_ge_target)
                    row[f"achieved_k{int(r.k)}"] = float(r.share_achieved)
                full = evaluate(tr, xx)
                a12 = avg_rule(tr, xx, 12)
                row["avg12_ppv"], row["avg12_hit"] = a12["ppv_true_ge_target"], a12["hit_rate_among_true_ge"]
                row["run5_ppv"] = float(full.loc[full.k == 5, "ppv_true_ge_target"].iloc[0])
                row["run5_hit"] = float(full.loc[full.k == 5, "hit_rate_among_true_ge"].iloc[0])
                row["k_needed_80"] = k_needed(full, 0.8)
                grid.append(row)
    grid = pd.DataFrame(grid)
    grid.round(4).to_csv(RES / "sensitivity_grid.csv", index=False)

    # 確かめ：人どうしの水準の差（spread）
    sp = []
    for i, s in enumerate([0.2, 0.35, 0.5]):
        tr, xx = simulate(np.random.default_rng(SEED * 1000 + i), 20000, BASE["median"], s, BASE["sigma"], BASE["rho"])
        ev = evaluate(tr, xx, ks=[1, 3, 6])
        sp.append({"spread": s, "share_true_ge": float((tr >= 1).mean()),
                   **{f"ppv_k{int(r.k)}": float(r.ppv_true_ge_target) for _, r in ev.iterrows()}})
    sp = pd.DataFrame(sp)
    sp.round(4).to_csv(RES / "sensitivity_spread.csv", index=False)

    # データ：300人分の24か月
    d = pd.DataFrame(np.round(x[:300, :T_OBS], 4), columns=[f"m{t + 1:02d}" for t in range(T_OBS)])
    d.insert(0, "true_level", np.round(true[:300], 4))
    d.insert(0, "person_id", np.arange(1, 301))
    d.to_csv(DATA / "people_24months.csv", index=False)

    b = base.set_index("k")
    def rng_of(col):
        return [round(float(grid[col].min()), 3), round(float(grid[col].max()), 3)]
    out = {"base_params": BASE, "n_people": N, "share_true_ge_target": round(share_true_ge, 4),
           "base_by_k": base.round(4).to_dict("records"),
           "k_needed_ppv80_base": k_needed(base, 0.8), "k_needed_ppv90_base": k_needed(base, 0.9),
           "average_rules": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in rules],
           "run_prob_by_level": curve.round(4).to_dict("records"),
           "grid_ranges": {c: rng_of(c) for c in ["ppv_k1", "ppv_k3", "ppv_k6", "ppv_k12", "share_true_ge",
                                                  "avg12_ppv", "avg12_hit", "run5_ppv", "run5_hit"]},
           "grid_k_needed_80": grid["k_needed_80"].tolist(),
           "grid_k_needed_80_none_count": int(grid["k_needed_80"].isna().sum()),
           "grid_avg12_hit_gt_run5_hit": int((grid.avg12_hit > grid.run5_hit).sum()),
           "grid_avg12_ppv_gt_run5_ppv": int((grid.avg12_ppv > grid.run5_ppv).sum()),
           "sensitivity_spread": sp.round(4).to_dict("records")}
    json.dump(out, open(RES / "a894_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：続いた月数ごとの、本当に目標額以上の人の割合
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(base.k, base.ppv_true_ge_target * 100, color=BLUE, marker="o", lw=2, label="本当の水準が目標額以上")
    ax.plot(base.k, base.next12_mean_ge_target * 100, color=ORANGE, marker="s", lw=1.5, ls="--",
            label="その後12か月の平均が目標額以上")
    ax.axhline(share_true_ge * 100, color=GRAY, lw=1, ls=":")
    ax.text(0.6, share_true_ge * 100 - 1.5, f"全員のうち、本当の水準が目標額以上の人：{share_true_ge*100:.0f}%", color=GRAY, fontsize=8.5, va="top")
    ax.set_xticks(KS); ax.set_xlabel("目標額以上が続いた月数（24か月のうちに）")
    ax.set_ylabel("続いた人のうちの割合（%）"); ax.set_ylim(0, 100); ax.set_xlim(0.5, 12.5)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("1か月の達成だけでは、本当に目標額以上の人は3人に1人")
    save(fig, "a894_ppv_by_k.png", SRC)

    # 図2：本当の水準ごとに、k か月続く確率
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for k, c, ls in [(1, GRAY, "-"), (3, BLUE, "-"), (6, ORANGE, "-"), (12, GREEN, "-")]:
        cc = curve[curve.k == k]
        ax.plot(cc.true_level * 100, cc.p_run_within_24 * 100, color=c, lw=2, ls=ls, label=f"{k}か月続く")
    ax.axvline(100, color=INK, lw=0.8, ls=":")
    ax.set_xlabel("本当の水準（目標額＝100）"); ax.set_ylabel("24か月のうちに続く確率（%）"); ax.set_ylim(0, 102)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("本当の水準が目標額の9割でも、3か月続くことはよくある")
    save(fig, "a894_run_prob.png", SRC)

    # 図3：置き方を変えたときの幅
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ks4 = [1, 3, 6, 12]
    lo = [grid[f"ppv_k{k}"].min() * 100 for k in ks4]
    hi = [grid[f"ppv_k{k}"].max() * 100 for k in ks4]
    bv = [b.loc[k, "ppv_true_ge_target"] * 100 for k in ks4]
    for i, k in enumerate(ks4):
        ax.plot([lo[i], hi[i]], [i, i], color=LIGHT, lw=8, solid_capstyle="butt")
        ax.plot(bv[i], i, "o", color=BLUE)
        ax.text(hi[i] + 1.5, i, f"{lo[i]:.1f}〜{hi[i]:.1f}%（基本 {bv[i]:.1f}%）", va="center", fontsize=9)
    ax.set_yticks(range(len(ks4))); ax.set_yticklabels([f"{k}か月続いた" for k in ks4])
    ax.invert_yaxis(); ax.set_xlim(0, 125); ax.set_xticks([0, 20, 40, 60, 80, 100])
    ax.set_xlabel("続いた人のうち、本当の水準が目標額以上の割合（%）")
    ax.set_title("置き方27通りの幅：同じ月数でも答えは大きく動く")
    save(fig, "a894_sensitivity.png", SRC)

    print(json.dumps({k: out[k] for k in ["share_true_ge_target", "k_needed_ppv80_base", "grid_ranges"]},
                     ensure_ascii=False, indent=1))
    print(base.round(3).to_string())
    print(pd.DataFrame(rules).round(3).to_string())
    print(grid.round(3).to_string())
    print(sp.round(3).to_string())
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
