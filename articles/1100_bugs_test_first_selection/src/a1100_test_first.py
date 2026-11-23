"""1100 テストを先に書いた機能にバグが少ないのは、書き方の効果か、機能の選ばれ方か？（架空のデータ）

架空のアプリの開発チームが1年に作る機能300件を乱数で作る。機能ごとに難しさ・大きさ（行数）・公開した日を置き、
「テストを先に書く」かどうかは、易しい機能ほど・年の後半ほど選ばれやすいと置く。
テストを先に書くことの効果（公開後のバグの数を何倍にするか）は、基本では1倍（効果なし）と作成者が置く。
公開後に見つかったバグの数を、先に書いた機能と書かなかった機能で比べると何倍に見えるかを、
そのまま・公開後の日数をそろえる・千行あたり・見積もりの難しさの帯をそろえる・でたらめに選んだ場合で数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1100
SRC = "架空の開発チームの機能と公開後のバグ（作成者が置いた確率からの乱数、seed 1100）"
N_FEAT = 300
YEAR = 360
WINDOW = 90           # 公開後の日数をそろえるときの日数
BASE = {"effect": 1.0, "g_diff": 1.0, "g_time": 2.0, "pt_noise": 0.7, "share": 0.4,
        "med_lines": 400, "size_diff": 0.5, "size_noise": 0.4, "bugs_per_400": 3.0, "diff_bugs": 0.6, "find_mean_days": 60}
METHODS = {"raw": "①そのまま（1機能あたり、今までの分）", "window": "②公開後90日の分（1機能あたり）",
           "window_kloc": "③②を千行あたり", "window_kloc_band": "④③を見積もりの難しさの帯ごとにそろえる",
           "random": "⑤でたらめに選んだとき（③と同じ数え方）"}
REPS = 1000
GRID_REPS = 300


def r(x, d=4):
    return round(float(x), d)


def make(rng, reps, effect, g_diff, g_time, pt_noise):
    d = rng.standard_normal((reps, N_FEAT))                                   # 難しさ
    lines = np.round(BASE["med_lines"] * np.exp(BASE["size_diff"] * d + BASE["size_noise"] * rng.standard_normal((reps, N_FEAT))))
    lines = np.maximum(lines, 10)
    day = rng.uniform(0, YEAR, (reps, N_FEAT))                                # 公開した日
    pts = d + pt_noise * rng.standard_normal((reps, N_FEAT))                  # 見積もりの難しさ（ポイント）
    # 先に書くかどうか：易しいほど・年の後半ほど選ばれやすい。全体の割合を share にそろえる
    score = -g_diff * d + g_time * (day / YEAR - 0.5) * 2 + rng.logistic(size=(reps, N_FEAT))
    cut = np.quantile(score, 1 - BASE["share"], axis=1, keepdims=True)
    tf = score > cut
    tf_rand = rng.random((reps, N_FEAT)).argsort(1).argsort(1) < int(BASE["share"] * N_FEAT)
    mu_total = BASE["bugs_per_400"] * (lines / BASE["med_lines"]) * np.exp(BASE["diff_bugs"] * d - BASE["diff_bugs"] ** 2 / 2)

    age = YEAR - day
    p_age = 1 - np.exp(-age / BASE["find_mean_days"])                       # 公開から今までに見つかる確率
    p_win = np.minimum(1 - np.exp(-WINDOW / BASE["find_mean_days"]), p_age)  # 公開後90日までに見つかる確率

    def bugs(tfx):
        # バグが見つかるまでの日数は、公開から平均60日の指数分布
        n_all = rng.poisson(mu_total * np.where(tfx, effect, 1.0))
        win = rng.binomial(n_all, p_win)
        found_now = win + rng.binomial(n_all - win, np.clip((p_age - p_win) / (1 - p_win), 0, 1))
        return n_all, found_now, win

    n_all, found_now, win = bugs(tf)
    n_all_r, _, win_r = bugs(tf_rand)
    return {"d": d, "lines": lines, "day": day, "pts": pts, "tf": tf, "tf_rand": tf_rand,
            "n_all": n_all, "found_now": found_now, "win": win, "win_r": win_r}


def ratios(s):
    tf, ok = s["tf"], s["day"] <= YEAR - WINDOW
    out = {}

    def per(x, m):
        return (x * m).sum(1) / m.sum(1)
    out["raw"] = per(s["found_now"], tf) / per(s["found_now"], ~tf)
    out["window"] = per(s["win"], tf & ok) / per(s["win"], ~tf & ok)

    def kloc(x, m):
        return (x * m).sum(1) / (s["lines"] * m).sum(1)
    out["window_kloc"] = kloc(s["win"], tf & ok) / kloc(s["win"], ~tf & ok)
    # 見積もりの難しさの帯（5つ、その年の機能の5分位）ごとに千行あたりを出し、帯の機能の数で重み付けして比べる
    q = np.quantile(s["pts"], [0.2, 0.4, 0.6, 0.8], axis=1).T
    band = (s["pts"][:, :, None] > q[:, None, :]).sum(2)
    num_t = np.zeros(len(tf)); num_c = np.zeros(len(tf)); wsum = np.zeros(len(tf))
    for b in range(5):
        mb = (band == b) & ok
        mt, mc = mb & tf, mb & ~tf
        has = (mt.sum(1) > 0) & (mc.sum(1) > 0)
        w = mb.sum(1) * has
        num_t += w * np.divide(kloc(s["win"], mt), 1, where=has, out=np.zeros(len(tf)))
        num_c += w * np.divide(kloc(s["win"], mc), 1, where=has, out=np.zeros(len(tf)))
        wsum += w
    out["window_kloc_band"] = num_t / num_c
    rr = s["tf_rand"]
    out["random"] = kloc(s["win_r"], rr & ok) / kloc(s["win_r"], ~rr & ok)
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    b = BASE
    s = make(rng, REPS, b["effect"], b["g_diff"], b["g_time"], b["pt_noise"])
    rt = ratios(s)
    tab = pd.DataFrame([{"method": k, "label": METHODS[k], "median": r(np.median(v)), "p10": r(np.percentile(v, 10)),
                         "p90": r(np.percentile(v, 90)), "share_below_0_8": r((v < 0.8).mean())} for k, v in rt.items()])
    tab.to_csv(RES / "ratio_by_method.csv", index=False)

    tf = s["tf"]
    ok = s["day"] <= YEAR - WINDOW
    prof = {"tf_share": r(tf.mean()), "diff_mean_tf": r(s["d"][tf].mean()), "diff_mean_other": r(s["d"][~tf].mean()),
            "lines_median_tf": r(np.median(s["lines"][tf]), 1), "lines_median_other": r(np.median(s["lines"][~tf]), 1),
            "day_mean_tf": r(s["day"][tf].mean(), 2), "day_mean_other": r(s["day"][~tf].mean(), 2),
            "found_share_now_tf": r(s["found_now"][tf].sum() / s["n_all"][tf].sum()),
            "found_share_now_other": r(s["found_now"][~tf].sum() / s["n_all"][~tf].sum()),
            "bugs_per_feature_now_tf": r(s["found_now"][tf].mean(), 3), "bugs_per_feature_now_other": r(s["found_now"][~tf].mean(), 3),
            "share_window_ok": r(ok.mean()),
            "formula_window_found_share": r(1 - np.exp(-WINDOW / b["find_mean_days"])),
            "corr_pts_diff": r(np.corrcoef(s["pts"].ravel(), s["d"].ravel())[0, 1])}

    # 効果を0.8倍と置いたとき
    s8 = make(rng, REPS, 0.8, b["g_diff"], b["g_time"], b["pt_noise"])
    rt8 = ratios(s8)
    eff8 = {k: r(np.median(v)) for k, v in rt8.items()}
    eff8_p = {k: [r(np.percentile(v, 10)), r(np.percentile(v, 90))] for k, v in rt8.items()}

    # 確かめ：選ばれ方の強さ（難しさ・年の時期）× 見積もりの難しさの誤差 × 置いた効果（48通り、各300回）
    rows = []
    for eff in [1.0, 0.8]:
        for g_diff in [0.0, 0.5, 1.0, 2.0]:
            for g_time in [0.0, 2.0]:
                for pn in [0.35, 0.7, 1.4]:
                    sg = make(rng, GRID_REPS, eff, g_diff, g_time, pn)
                    rg = ratios(sg)
                    row = {"effect": eff, "g_diff": g_diff, "g_time": g_time, "pt_noise": pn}
                    for k, v in rg.items():
                        row[k] = r(np.median(v))
                    rows.append(row)
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)

    # data：1回目の1年の機能300件
    one = pd.DataFrame({"feature": np.arange(1, N_FEAT + 1), "difficulty": np.round(s["d"][0], 4), "points_est": np.round(s["pts"][0], 4),
                        "lines": s["lines"][0].astype(int), "release_day": np.round(s["day"][0], 2), "test_first": s["tf"][0].astype(int),
                        "bugs_found_by_year_end": s["found_now"][0], "bugs_found_90days": s["win"][0],
                        "has_90days": ok[0].astype(int), "test_first_random": s["tf_rand"][0].astype(int), "bugs_found_90days_random": s["win_r"][0]})
    one.to_csv(DATA / "features_one_year.csv", index=False)
    o_tf, o_ot = one[one.test_first == 1], one[one.test_first == 0]
    chk = {"raw_from_csv": r(o_tf.bugs_found_by_year_end.mean() / o_ot.bugs_found_by_year_end.mean()), "sim_rep0": r(rt["raw"][0])}

    def rng_of(col, sel):
        g = grid[sel]
        return [r(g[col].min()), r(g[col].max())]
    e1, e8 = grid.effect == 1.0, grid.effect == 0.8
    out = {"settings": {**BASE, "n_features": N_FEAT, "year_days": YEAR, "window_days": WINDOW, "reps": REPS, "grid_reps": GRID_REPS},
           "profile": prof, "ratio_by_method": tab.to_dict(orient="records"),
           "effect_0_8_median": eff8, "effect_0_8_p10_p90": eff8_p,
           "grid_effect1_range": {k: rng_of(k, e1) for k in METHODS},
           "grid_effect08_range": {k: rng_of(k, e8) for k in METHODS},
           "grid_effect1_gdiff0_band": rng_of("window_kloc_band", e1 & (grid.g_diff == 0)),
           "grid_effect1_gdiff2_band": rng_of("window_kloc_band", e1 & (grid.g_diff == 2.0)),
           "grid_effect1_band_by_noise": {str(pn): rng_of("window_kloc_band", e1 & (grid.pt_noise == pn)) for pn in [0.35, 0.7, 1.4]},
           "grid_effect1_raw_lt_window": int((grid[e1].raw < grid[e1].window).sum()),
           "grid_effect1_gtime2_raw_lt_window": int((grid[e1 & (grid.g_time == 2.0)].raw < grid[e1 & (grid.g_time == 2.0)].window).sum()),
           "grid_effect1_gtime2_n": int((e1 & (grid.g_time == 2.0)).sum()),
           "grid_effect1_gtime0_raw_minus_window_max": r((grid[e1 & (grid.g_time == 0)].raw - grid[e1 & (grid.g_time == 0)].window).abs().max()),
           "grid_effect08_band_below_08": int((grid[e8].window_kloc_band < 0.8).sum()),
           "grid_effect1_band_below_09": int((grid[e1].window_kloc_band < 0.9).sum()),
           "data_check": chk}
    json.dump(out, open(RES / "a1100_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：比べ方ごとの「先に書いた÷書かなかった」
    fig, ax = plt.subplots(figsize=(8.4, 4.0))
    y = np.arange(len(tab))
    ax.barh(y, tab["median"], color=[GRAY, LIGHT, BLUE, BLUE, ORANGE], height=0.6)
    ax.hlines(y, tab.p10, tab.p90, color=INK, lw=1.2)
    for yy, m, hi in zip(y, tab["median"], tab.p90):
        ax.text(hi + 0.02, yy, f"{m:g}倍", va="center", fontsize=9)
    ax.axvline(1, color=INK, ls="--", lw=0.8)
    ax.text(1.01, 1.5, "置いた効果\n（1倍＝効果なし）", fontsize=8.5, va="center")
    ax.set_yticks(y); ax.set_yticklabels(tab.label, fontsize=9); ax.invert_yaxis()
    ax.set_xlim(0, 1.4); ax.set_xlabel("先に書いた機能÷書かなかった機能のバグ（1,000回の中央値、線は10〜90%）")
    ax.set_title("効果なしと置いても、そのまま比べると先に書いた機能のバグは少なく見える", fontsize=11.5)
    save(fig, "a1100_methods.png", SRC, y=-0.04)

    # 図2：選ばれた機能の難しさ・公開した日（1回目）
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.8))
    bins = np.linspace(-3.5, 3.5, 29)
    axes[0].hist(s["d"][0][~s["tf"][0]], bins=bins, color=GRAY, alpha=0.8, label="書かなかった機能")
    axes[0].hist(s["d"][0][s["tf"][0]], bins=bins, color=ORANGE, alpha=0.8, label="先に書いた機能")
    axes[0].set_xlabel("置いた難しさ（右ほど難しい）"); axes[0].set_ylabel("機能の数（1回目の300件）")
    axes[0].legend(frameon=False, fontsize=8.5)
    axes[0].set_title(f"難しさの平均：先に書いた {prof['diff_mean_tf']:g}、書かなかった {prof['diff_mean_other']:g}", fontsize=9.5)
    bins2 = np.linspace(0, YEAR, 13)
    axes[1].hist(s["day"][0][~s["tf"][0]], bins=bins2, color=GRAY, alpha=0.8, label="書かなかった機能")
    axes[1].hist(s["day"][0][s["tf"][0]], bins=bins2, color=ORANGE, alpha=0.8, label="先に書いた機能")
    axes[1].set_xlabel("公開した日（年の初めから）"); axes[1].set_ylabel("機能の数（1回目の300件）")
    axes[1].set_title(f"公開した日の平均：先に書いた {prof['day_mean_tf']:g}日、書かなかった {prof['day_mean_other']:g}日", fontsize=9.5)
    fig.suptitle("先に書いた機能は、易しく、年の後半に公開されたものに寄っている（作成者がそう置いた）", fontsize=11.5, y=1.02)
    fig.tight_layout()
    save(fig, "a1100_selection.png", SRC, y=-0.03)

    # 図3：確かめ：難しさによる選ばれ方の強さごとの④（効果なし）
    fig, ax = plt.subplots(figsize=(8.0, 4.0))
    gds = [0.0, 0.5, 1.0, 2.0]
    for j, (pn, c) in enumerate([(0.35, BLUE), (0.7, ORANGE), (1.4, GRAY)]):
        v = [grid[e1 & (grid.g_diff == g) & (grid.pt_noise == pn) & (grid.g_time == 2.0)].window_kloc_band.iloc[0] for g in gds]
        ax.bar(np.arange(4) + (j - 1) * 0.26, v, 0.26, color=c, label=f"見積もりの誤差 {pn}")
    ax.axhline(1, color=INK, ls="--", lw=0.8)
    ax.set_xticks(range(4)); ax.set_xticklabels([f"難しさで選ぶ強さ {g}" + ("\n（選ばない）" if g == 0 else "\n（基本）" if g == 1 else "") for g in gds], fontsize=9)
    for j in range(3):
        for i, b in enumerate(ax.containers[j]):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.015, f"{b.get_height():g}", ha="center", fontsize=7)
    ax.set_ylim(0, 1.25); ax.set_ylabel("④の 先に書いた÷書かなかった（倍）")
    ax.set_xlabel("効果なし・年の時期で選ぶ強さ2（基本）のとき。各300回の中央値", fontsize=9)
    ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper right")
    ax.set_title("難しさの帯をそろえても、見積もりに誤差があると、選ばれ方の分が残る", fontsize=11.5)
    save(fig, "a1100_robust.png", SRC, y=-0.08)

    print(tab.to_string()); print(json.dumps({"profile": prof, "eff8": eff8, "eff8_p": eff8_p}, ensure_ascii=False, indent=1))
    print(grid.to_string()); print(json.dumps({k: out[k] for k in out if k.startswith("grid_") or k == "data_check"}, ensure_ascii=False))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
