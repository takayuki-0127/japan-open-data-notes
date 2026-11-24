"""1249 新しい本を出したあと、シリーズの前の本の売れ方がどれだけ押し上げられたかは分かるのか？（架空のデータ）

架空の電子書籍のシリーズ。1巻は発売から300日たち、ふだんの売れ方が日ごとにゆっくり減っている（T 日で 1/e）。
0日目に2巻が出ると、1巻に「押し上げ」が乗る（0日目に1巻のふだんの U 倍、τ 日で 1/e に減る）。
同じ分野の本すべてにかかる日ごとの揺れ（全体の揺れ）と、季節の山（0〜20日目に +h）を置く。
別のシリーズの本（同じ作成者の架空の本、押し上げなし）も同じ揺れ・季節の山を受ける。
1日の冊数は、その日の売れ方を平均にして、でたらめに数を引く。押し上げの分の冊数も別に数えて「本当の押し上げ」とする。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1249
SRC = "架空の電子書籍のシリーズ（作成者が乱数で作成、seed 1249）"
PRE, POST = 91, 60                 # 2巻の前91日（-91〜-1日目）、後60日（0〜59日目）
T = np.arange(-PRE, POST)
BASE = dict(B=3.0, Tdec=250.0, U=1.0, tau=10.0, h=0.0, season_end=20, Bc=3.0, Tc=250.0, day_sd=0.2)
WIN = 30                            # 押し上げを数える30日（0〜29日目）
REPS = 4000


def simulate(rng, n, p):
    lam1 = p["B"] * np.exp(-T / p["Tdec"])
    lamc = p["Bc"] * np.exp(-T / p["Tc"])
    push = np.where(T >= 0, lam1 * p["U"] * np.exp(-np.clip(T, 0, None) / p["tau"]), 0.0)
    season = 1 + p["h"] * ((T >= 0) & (T <= p["season_end"]))
    day = np.exp(p["day_sd"] * rng.standard_normal((n, len(T))) - p["day_sd"] ** 2 / 2)  # 全体の揺れ（平均1）
    k = day * season
    base1 = rng.poisson(lam1 * k)
    extra = rng.poisson(push * k)
    ctrl = rng.poisson(lamc * k)
    return base1 + extra, extra, ctrl


def estimates(x, ctrl):
    i0 = PRE
    after = x[:, i0:i0 + WIN].sum(1)
    before = x[:, i0 - WIN:i0].sum(1)
    e1 = after - before                                   # ① 前の30日と比べる
    # ② 前の91日（13週）の減り方を延ばす：週ごとの冊数の対数に直線を当てる
    wk = x[:, :PRE].reshape(len(x), 13, 7).sum(2)
    tw = (np.arange(13) * 7 - PRE + 3.0)                  # 週のまん中の日
    y = np.log(wk + 0.5)
    tb = tw - tw.mean()
    b = (y - y.mean(1, keepdims=True)) @ tb / (tb ** 2).sum()
    a = y.mean(1) - b * tw.mean()
    pred = (np.exp(a[:, None] + b[:, None] * np.arange(WIN)[None, :]) / 7).sum(1)
    e2 = after - pred
    # ③ 別のシリーズの本の前後の変化で割り引く
    ca = ctrl[:, i0:i0 + WIN].sum(1)
    cb = ctrl[:, i0 - WIN:i0].sum(1)
    e3 = after - before * ca / np.maximum(cb, 1)
    return {"前の30日と比べる": e1, "前の91日の減り方を延ばす": e2, "別のシリーズの本の前後の変化で割り引く": e3}


def summarize(est, true, with_push=True):
    rows = []
    for name, e in est.items():
        r = {"method": name, "est_mean": round(float(e.mean()), 1),
             "est_p10": round(float(np.quantile(e, .1)), 1), "est_p90": round(float(np.quantile(e, .9)), 1),
             "true_mean": round(float(true.mean()), 1)}
        if with_push:
            r["bias_share"] = round(float((e.mean() - true.mean()) / true.mean()), 4)
            r["within_25pct"] = round(float((np.abs(e - true) <= 0.25 * true).mean()), 4)
            r["est_le_0"] = round(float((e <= 0).mean()), 4)
        else:
            r["est_ge_10"] = round(float((e >= 10).mean()), 4)
            r["est_le_m10"] = round(float((e <= -10).mean()), 4)
        rows.append(r)
    return rows


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    scen = {"自然な減りだけ": dict(),
            "季節の山（0〜20日目に+30%）": dict(h=0.3),
            "押し上げなし・自然な減りだけ": dict(U=0.0),
            "押し上げなし・季節の山": dict(U=0.0, h=0.3)}
    main_rows, keep = [], {}
    for sname, ch in scen.items():
        p = {**BASE, **ch}
        x, extra, ctrl = simulate(rng, REPS, p)
        true = extra[:, PRE:PRE + WIN].sum(1)
        est = estimates(x, ctrl)
        for r in summarize(est, true, p["U"] > 0):
            main_rows.append({"scenario": sname, **r})
        keep[sname] = (x, extra, ctrl, est, true)
    main_df = pd.DataFrame(main_rows)
    main_df.to_csv(RES / "scenarios.csv", index=False)

    # 式どおりの値：本当の押し上げの期待値、自然な減りで①が出す差の期待値
    t = np.arange(WIN)
    exp_push = float((BASE["B"] * np.exp(-t / BASE["Tdec"]) * np.exp(-t / BASE["tau"])).sum())
    exp_base_after = float((BASE["B"] * np.exp(-t / BASE["Tdec"])).sum())
    exp_base_before = float((BASE["B"] * np.exp(-np.arange(-WIN, 0) / BASE["Tdec"])).sum())
    exp_season = float(0.3 * (BASE["B"] * np.exp(-np.arange(21) / BASE["Tdec"])).sum())
    formula = {"push_30d": round(exp_push, 3), "base_after_30d": round(exp_base_after, 3),
               "base_before_30d": round(exp_base_before, 3), "natural_drop_30d": round(exp_base_after - exp_base_before, 3),
               "season_extra_on_base_30d": round(exp_season, 3),
               "push_share_of_after": round(exp_push / (exp_push + exp_base_after), 4)}

    # 1回分の例（自然な減りだけ）
    x, extra, ctrl, est, true = keep["自然な減りだけ"]
    pd.DataFrame({"day": T, "book1_sold": x[0], "book1_push_part": extra[0], "other_series_sold": ctrl[0]}).to_csv(
        DATA / "daily_example.csv", index=False)
    example = {"true_push_30d": int(true[0]), **{k: round(float(v[0]), 3) for k, v in est.items()}}

    # 確かめ：1巻の減り方 T・季節の山 h・ふだんの売れ方 B（27通り）。別のシリーズの本の減り方は250日のまま
    grid = []
    for Td in [120.0, 250.0, 500.0]:
        for h in [0.0, 0.2, 0.5]:
            for B in [1.0, 3.0, 10.0]:
                g = np.random.default_rng(SEED * 100 + int(Td) + int(h * 10) * 7 + int(B) * 1000)
                p = {**BASE, "Tdec": Td, "h": h, "B": B, "Bc": B}
                x, extra, ctrl = simulate(g, 2000, p)
                true = extra[:, PRE:PRE + WIN].sum(1)
                est = estimates(x, ctrl)
                rec = {"Tdec": Td, "h": h, "B": B, "true_mean": round(float(true.mean()), 1)}
                for key, (name, e) in zip(["m1", "m2", "m3"], est.items()):
                    rec[f"{key}_ratio"] = round(float(e.mean() / true.mean()), 4)
                    rec[f"{key}_within25"] = round(float((np.abs(e - true) <= 0.25 * true).mean()), 4)
                # 押し上げなしで、押し上げがあるように見える割合（本当の押し上げの半分以上）
                p0 = {**p, "U": 0.0}
                x0, _, c0 = simulate(g, 2000, p0)
                e0 = estimates(x0, c0)
                for key, (name, e) in zip(["m1", "m2", "m3"], e0.items()):
                    rec[f"{key}_ghost_ge_half"] = round(float((e >= 0.5 * true.mean()).mean()), 4)
                grid.append(rec)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid.csv", index=False)
    rb = {}
    for key in ["m1", "m2", "m3"]:
        rb[key] = {"ratio_range": [float(grid[f"{key}_ratio"].min()), float(grid[f"{key}_ratio"].max())],
                   "within25_range": [float(grid[f"{key}_within25"].min()), float(grid[f"{key}_within25"].max())],
                   "ghost_range": [float(grid[f"{key}_ghost_ge_half"].min()), float(grid[f"{key}_ghost_ge_half"].max())]}
    same_T = grid[grid.Tdec == 250.0]
    rb["m3_ratio_range_sameT"] = [float(same_T.m3_ratio.min()), float(same_T.m3_ratio.max())]
    rb["m3_ratio_range_T120"] = [float(grid[grid.Tdec == 120].m3_ratio.min()), float(grid[grid.Tdec == 120].m3_ratio.max())]
    rb["m3_ratio_range_T500"] = [float(grid[grid.Tdec == 500].m3_ratio.min()), float(grid[grid.Tdec == 500].m3_ratio.max())]
    rb["m2_ratio_range_h0"] = [float(grid[grid.h == 0].m2_ratio.min()), float(grid[grid.h == 0].m2_ratio.max())]
    rb["m2_ratio_range_h05"] = [float(grid[grid.h == 0.5].m2_ratio.min()), float(grid[grid.h == 0.5].m2_ratio.max())]
    rb["m1_ratio_range_h0"] = [float(grid[grid.h == 0].m1_ratio.min()), float(grid[grid.h == 0].m1_ratio.max())]
    rb["within25_by_B"] = {str(B): {k: [float(grid[grid.B == B][f"{k}_within25"].min()), float(grid[grid.B == B][f"{k}_within25"].max())] for k in ["m1", "m2", "m3"]}
                           for B in [1.0, 3.0, 10.0]}

    out = {"setting": BASE, "window_days": WIN, "reps": REPS, "formula": formula, "example": example,
           "scenarios": main_df.to_dict("records"), "robust": rb}
    json.dump(out, open(RES / "a1249_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の1回（自然な減りだけ）
    x, extra, ctrl, est, true = keep["自然な減りだけ"]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    wk1 = x[0][: (len(T) // 7) * 7].reshape(-1, 7).sum(1)
    wke = extra[0][: (len(T) // 7) * 7].reshape(-1, 7).sum(1)
    tw = T[: (len(T) // 7) * 7].reshape(-1, 7)[:, 0]
    ax.bar(tw + 3, wk1 - wke, 6, color=LIGHT, label="1巻：ふだんの分")
    ax.bar(tw + 3, wke, 6, bottom=wk1 - wke, color=ORANGE, label="1巻：押し上げの分（作成者だけが分かる）")
    lam1 = BASE["B"] * np.exp(-T / BASE["Tdec"]) * 7
    ax.plot(T, lam1, color=INK, lw=1, label="ふだんの売れ方（7日分）")
    ax.axvline(0, color=GRAY, lw=1, ls="--"); ax.text(1, ax.get_ylim()[1] * 0.95, "2巻の発売", fontsize=9, color=GRAY)
    ax.set_ylim(0, None); ax.set_xlabel("2巻の発売からの日（7日ごとにまとめた）"); ax.set_ylabel("1巻の7日の冊数")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("例の1回：1巻の売れ方と、2巻が出たあとの押し上げ")
    save(fig, "a1249_example.png", SRC)

    # 図2：シナリオごとの見積もりの平均（押し上げあり2つ）
    fig, axs = plt.subplots(1, 2, figsize=(8.4, 4.0), sharey=True)
    ms = list(est.keys())
    short = ["①前の30日\nと比べる", "②前の減り方\nを延ばす", "③別のシリーズ\nの本で割り引く"]
    for ax, sname in zip(axs, ["自然な減りだけ", "季節の山（0〜20日目に+30%）"]):
        d = main_df[main_df.scenario == sname]
        v = d.est_mean.values; tr = d.true_mean.values[0]
        ax.bar(short, v, color=[GRAY, BLUE, GREEN])
        ax.errorbar(range(3), v, yerr=[v - d.est_p10.values, d.est_p90.values - v], fmt="none", ecolor=INK, lw=0.8, capsize=3)
        ax.axhline(tr, color=ORANGE, lw=1.2, ls="--"); ax.text(-0.45, tr + 1, f"本当の押し上げ {tr:.1f}冊", color=ORANGE, fontsize=8.5, va="bottom", ha="left", bbox=dict(facecolor="white", edgecolor="none", pad=1))
        for i, vv in enumerate(v):
            ax.text(i, 2, f"{vv:.1f}", fontsize=9, ha="center", color="white", fontweight="bold")
        ax.set_title(sname, fontsize=11); ax.tick_params(axis="x", labelsize=8.5)
    axs[0].set_ylabel("1巻の押し上げの見積もり\n（30日の冊数、4,000回の平均と10〜90%）", linespacing=1.5)
    axs[0].set_ylim(min(0, float(main_df.est_p10.min()) - 5), None)
    for ax in axs:
        ax.axhline(0, color=INK, lw=0.6)
    fig.suptitle("前の30日と比べると、自然な減りの分だけ小さく、季節の山の分だけ大きく出る", fontsize=12, y=1.03)
    save(fig, "a1249_methods.png", SRC)

    # 図3：押し上げなしのとき
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for j, (sname, c) in enumerate(zip(["押し上げなし・自然な減りだけ", "押し上げなし・季節の山"], [BLUE, ORANGE])):
        d = main_df[main_df.scenario == sname]
        ax.bar(np.arange(3) + (j - 0.5) * 0.38, d.est_mean.values, 0.38, color=c, label=sname.replace("押し上げなし・", ""))
        for i, vv in enumerate(d.est_mean.values):
            ax.text(i + (j - 0.5) * 0.38, vv + (0.6 if vv >= 0 else -0.6), f"{vv:.1f}", ha="center", va="bottom" if vv >= 0 else "top", fontsize=8.5)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(range(3)); ax.set_xticklabels(short, fontsize=9)
    ax.set_ylim(-15, 22)
    ax.set_ylabel("押し上げの見積もり\n（30日の冊数、4,000回の平均）", linespacing=1.5)
    ax.legend(frameon=False, fontsize=9, title="押し上げが本当は0のとき", title_fontsize=9)
    ax.set_title("押し上げが本当は0でも、季節の山があると①と②では押し上げがあるように見える", fontsize=11.5)
    save(fig, "a1249_no_push.png", SRC)
    out["run_sec"] = round(time.time() - t0, 1)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
