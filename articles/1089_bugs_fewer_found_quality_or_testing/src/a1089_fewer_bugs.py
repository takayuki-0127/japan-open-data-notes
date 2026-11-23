"""1089 見つかったバグが減ったのは、品質が上がったからか、テストが減ったからか？（架空のデータ）

架空のアプリの開発チームのリリース（2週間ごと）を乱数で作る。リリースごとに入るバグの数（本当の品質）と、
リリース前のテストの時間を作成者が置き、バグ1つごとの見つけやすさから、リリース前に見つかるかを乱数で決める。
見つからなかったバグは、リリース後90日のうちに使う人が見つけて報告することがある。
前の12回と後の12回で「見つかったバグの数」が3割減ったとき、
(A) 入るバグが3割減った（品質が上がった）、(B) テストの時間を減らした、(C) 両方が半分ずつ、を
見つかった数・テスト1時間あたりの数・リリース後の報告を足した数で見分けられるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1089
SRC = "架空のアプリの開発チームのリリースとバグ（作成者が置いた数と確率からの乱数、seed 1089）"
BASE = {"bugs_per_release": 40, "test_hours": 80, "find_share": 0.7, "sigma_find": 1.0,
        "user_share_90d": 0.6, "sigma_user": 1.0, "drop": 0.3, "n_before": 12, "n_after": 12}
REPS = 200
GRID_REPS = 40
GH = np.polynomial.hermite_e.hermegauss(80)  # 見つけやすさ（対数正規）の期待値を出すための節点


def r(x, d=4):
    return round(float(x), d)


def share_found(c_h, sigma):
    """テストの時間×係数 c_h のとき、リリース前に見つかるバグの割合の期待値（式）"""
    x, w = GH
    d = np.exp(sigma * x - sigma ** 2 / 2)
    return float(1 - np.sum(w * np.exp(-c_h * d)) / np.sum(w))


def solve(fun, target, lo=1e-6, hi=1e3):
    for _ in range(200):
        mid = np.sqrt(lo * hi)
        if fun(mid) < target:
            lo = mid
        else:
            hi = mid
    return float(np.sqrt(lo * hi))


def setup(find_share, sigma, drop):
    """係数 c（1時間あたり）と、B・C で見つかる数が (1−drop) 倍になるテスト時間の倍率を式で出す"""
    c_h0 = solve(lambda v: share_found(v, sigma), find_share)
    f0 = share_found(c_h0, sigma)
    hf_b = solve(lambda v: share_found(c_h0 * v, sigma), f0 * (1 - drop), 1e-9, 1.0)
    q_c = 1 - drop / 2  # C：入るバグを drop/2 減らし、残りをテストの時間で減らす
    hf_c = solve(lambda v: share_found(c_h0 * v, sigma), f0 * (1 - drop) / q_c, 1e-9, 1.0)
    return c_h0, f0, hf_b, q_c, hf_c


def user_k(user_share, sigma_u):
    return solve(lambda v: share_found(v, sigma_u), user_share)


def scenarios(drop, hf_b, q_c, hf_c):
    return {"S0": (1.0, 1.0), "A": (1 - drop, 1.0), "B": (1.0, hf_b), "C": (q_c, hf_c)}


def releases(rng, lam_mult, h_mult, c_h0, ku, p, n_b, n_a):
    rows = []
    for t in range(n_b + n_a):
        after = t >= n_b
        lam = p["bugs_per_release"] * (lam_mult if after else 1.0)
        hours = p["test_hours"] * (h_mult if after else 1.0)
        n = rng.poisson(lam)
        d = np.exp(rng.normal(-p["sigma_find"] ** 2 / 2, p["sigma_find"], n))
        found = rng.random(n) < 1 - np.exp(-c_h0 * (hours / p["test_hours"]) * d)
        g = np.exp(rng.normal(-p["sigma_user"] ** 2 / 2, p["sigma_user"], n))
        user = (~found) & (rng.random(n) < 1 - np.exp(-ku * g))
        rows.append({"release": t + 1, "period": "after" if after else "before", "test_hours": r(hours, 2),
                     "bugs_in": int(n), "found_before_release": int(found.sum()), "reported_90d": int(user.sum()),
                     "not_found_90d": int(n - found.sum() - user.sum())})
    return pd.DataFrame(rows)


def compare(df):
    b, a = df[df.period == "before"], df[df.period == "after"]
    out = {}
    for k, fb, fa in [("found", b.found_before_release.sum(), a.found_before_release.sum()),
                      ("per_hour", b.found_before_release.sum() / b.test_hours.sum(), a.found_before_release.sum() / a.test_hours.sum()),
                      ("found_plus_90d", (b.found_before_release + b.reported_90d).sum(), (a.found_before_release + a.reported_90d).sum()),
                      ("true_bugs", b.bugs_in.sum(), a.bugs_in.sum())]:
        out[k] = fa / fb - 1
    sb = b.found_before_release.sum() / (b.found_before_release + b.reported_90d).sum()
    sa = a.found_before_release.sum() / (a.found_before_release + a.reported_90d).sum()
    out["pre_share_before"], out["pre_share_after"] = sb, sa
    return out


def formula(p, drop, c_h0, f0, ku, lam_mult, h_mult):
    """期待値の式：見つかった数・1時間あたり・90日を足した数の変化"""
    f1 = share_found(c_h0 * h_mult, p["sigma_find"])
    u = share_found(ku, p["sigma_user"])
    tot0 = f0 + (1 - f0) * u
    tot1 = f1 + (1 - f1) * u
    return {"found": lam_mult * f1 / f0 - 1, "per_hour": lam_mult * f1 / f0 / h_mult - 1,
            "found_plus_90d": lam_mult * tot1 / tot0 - 1, "true_bugs": lam_mult - 1}


def run_set(p, drop, reps, seed0, keep_one=False):
    c_h0, f0, hf_b, q_c, hf_c = setup(p["find_share"], p["sigma_find"], drop)
    ku = user_k(p["user_share_90d"], p["sigma_user"])
    sc = scenarios(drop, hf_b, q_c, hf_c)
    res, one = [], {}
    for rep in range(reps):
        for k, (lm, hm) in sc.items():
            rr = np.random.default_rng(seed0 + rep * 10 + list(sc).index(k))
            df = releases(rr, lm, hm, c_h0, ku, p, p["n_before"], p["n_after"])
            res.append({"rep": rep, "scenario": k, **compare(df)})
            if keep_one and rep == 0:
                one[k] = df
    res = pd.DataFrame(res)
    forms = {k: formula(p, drop, c_h0, f0, ku, lm, hm) for k, (lm, hm) in sc.items()}
    return res, one, {"c_h0": c_h0, "f0": f0, "hours_mult_B": hf_b, "bugs_mult_C": q_c, "hours_mult_C": hf_c, "ku": ku}, forms


def main():
    t0 = time.time()
    p = dict(BASE)
    res, one, par, forms = run_set(p, p["drop"], REPS, SEED * 1000, keep_one=True)
    NAMES = {"S0": "変化なし", "A": "A 入るバグが3割減った", "B": "B テストの時間を減らした", "C": "C 両方を半分ずつ"}
    METRICS = ["found", "per_hour", "found_plus_90d", "true_bugs"]
    rows = []
    for k in NAMES:
        g = res[res.scenario == k]
        row = {"scenario": k, "name": NAMES[k]}
        for m in METRICS:
            row[f"{m}_mean"] = r(g[m].mean())
            row[f"{m}_p10"] = r(g[m].quantile(.1))
            row[f"{m}_p90"] = r(g[m].quantile(.9))
            row[f"{m}_formula"] = r(forms[k][m])
        row["pre_share_before"] = r(g.pre_share_before.mean())
        row["pre_share_after"] = r(g.pre_share_after.mean())
        row["share_found_drop_ge_20pct"] = r((g.found <= -0.2).mean())
        rows.append(row)
    tab = pd.DataFrame(rows)
    tab.to_csv(RES / "scenarios.csv", index=False)

    # 見つかった数だけで A と B の区別：同じ回の A と B のどちらが大きく減ったか
    wa = res[res.scenario == "A"].set_index("rep"); wb = res[res.scenario == "B"].set_index("rep")
    a_vs_b_found = r((wa.found < wb.found).mean())
    # 90日を足した数が−15%より下がったのを「品質が上がった」と読むと
    rule = {k: r((res[res.scenario == k].found_plus_90d <= -0.15).mean()) for k in NAMES}

    # 確かめ：見つけやすさのばらつき×もとの見つかる割合×減り方（27通り、各40回）
    grid = []
    gi = 0
    for sg in [0.5, 1.0, 1.5]:
        for fs in [0.5, 0.7, 0.9]:
            for dr in [0.15, 0.3, 0.5]:
                pp = dict(BASE, sigma_find=sg, find_share=fs)
                rs, _, pr, fm = run_set(pp, dr, GRID_REPS, SEED * 100000 + gi * 1000)
                row = {"sigma_find": sg, "find_share": fs, "drop": dr, "hours_mult_B": r(pr["hours_mult_B"]),
                       "hours_cut_B": r(1 - pr["hours_mult_B"]),
                       "hours_mult_C": r(pr["hours_mult_C"])}
                for k in ["A", "B", "C"]:
                    g = rs[rs.scenario == k]
                    row[f"{k}_found"] = r(g.found.mean())
                    row[f"{k}_per_hour"] = r(g.per_hour.mean())
                    row[f"{k}_found_plus_90d"] = r(g.found_plus_90d.mean())
                    row[f"{k}_per_hour_formula"] = r(fm[k]["per_hour"])
                    row[f"{k}_plus90_formula"] = r(fm[k]["found_plus_90d"])
                grid.append(row); gi += 1
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid27.csv", index=False)

    # 確かめ：使う人が90日で見つける割合（0.4・0.6・0.8）、リリースの回数（6・12・24回ずつ）
    extra = []
    for name, ch in [("使う人の報告 0.4", {"user_share_90d": 0.4}), ("使う人の報告 0.8", {"user_share_90d": 0.8}),
                     ("6回ずつ", {"n_before": 6, "n_after": 6}), ("24回ずつ", {"n_before": 24, "n_after": 24})]:
        pp = dict(BASE, **ch)
        rs, _, pr, fm = run_set(pp, BASE["drop"], 100, SEED * 7 + len(extra) * 100000)
        row = {"setting": name}
        for k in ["S0", "A", "B"]:
            g = rs[rs.scenario == k]
            row[f"{k}_found_p10"] = r(g.found.quantile(.1)); row[f"{k}_found_p90"] = r(g.found.quantile(.9))
            row[f"{k}_plus90_mean"] = r(g.found_plus_90d.mean())
        wa2 = rs[rs.scenario == "A"].set_index("rep"); wb2 = rs[rs.scenario == "B"].set_index("rep")
        row["A_lt_B_found"] = r((wa2.found < wb2.found).mean())
        extra.append(row)
    extra = pd.DataFrame(extra)
    extra.to_csv(RES / "extra.csv", index=False)

    data = pd.concat([one[k].assign(scenario=k) for k in ["A", "B", "C"]])
    data = data[["scenario", "release", "period", "test_hours", "bugs_in", "found_before_release", "reported_90d", "not_found_90d"]]
    data.to_csv(DATA / "releases_one_run.csv", index=False)
    chk = compare(one["B"])

    t = tab.set_index("scenario")
    out = {"settings": {**BASE, "reps": REPS, "grid_reps": GRID_REPS, "seed": SEED},
           "derived": {**{k: r(v) for k, v in par.items()}, "hours_cut_B": r(1 - par["hours_mult_B"]), "hours_cut_C": r(1 - par["hours_mult_C"])},
           "scenarios": tab.to_dict("records"),
           "A_found_drop_more_than_B_share": a_vs_b_found,
           "rule_plus90_le_minus15pct": rule,
           "grid27_ranges": {k: [r(grid[k].min()), r(grid[k].max())] for k in grid.columns if k not in ("sigma_find", "find_share", "drop")},
           "grid27_B_per_hour_positive": int((grid.B_per_hour > 0).sum()),
           "grid27_C_per_hour_positive": int((grid.C_per_hour > 0).sum()),
           "grid27_hours_cut_B_range": [r(1 - grid.hours_mult_B.max()), r(1 - grid.hours_mult_B.min())],
           "grid27_B_plus90_vs_A_gap": [r((grid.B_found_plus_90d - grid.A_found_plus_90d).min()), r((grid.B_found_plus_90d - grid.A_found_plus_90d).max())],
           "grid27_max_abs_formula_gap_per_hour_B": r((grid.B_per_hour - grid.B_per_hour_formula).abs().max()),
           "grid9_drop30_ranges": {k: [r(grid[grid["drop"] == 0.3][k].min()), r(grid[grid["drop"] == 0.3][k].max())] for k in ["B_per_hour", "B_found_plus_90d", "A_found_plus_90d", "C_per_hour", "C_found_plus_90d", "hours_mult_B"]},
           "grid27_drop30": grid[grid["drop"] == 0.3][["sigma_find", "find_share", "hours_mult_B", "B_per_hour", "B_found_plus_90d", "A_found_plus_90d"]].to_dict("records"),
           "extra": extra.to_dict("records"),
           "data_check": {"B_rep0_found_change": r(chk["found"]), "B_rep0_per_hour_change": r(chk["per_hour"])}}
    json.dump(out, open(RES / "a1089_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分のリリースごとの見つかった数（A と B）
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.8), sharey=True)
    for ax, k, ttl in [(axes[0], "A", "A：入るバグを3割減らした（品質が上がった）"), (axes[1], "B", f"B：テストの時間を{round((1 - par['hours_mult_B']) * 100, 2):g}%減らした")]:
        df = one[k]
        ax.plot(df.release, df.bugs_in, color=GRAY, ls="--", lw=1.3, label="入ったバグ（本当の数）")
        ax.plot(df.release, df.found_before_release, color=BLUE, marker="o", ms=3.5, lw=1.6, label="リリース前に見つかった数")
        ax.plot(df.release, df.found_before_release + df.reported_90d, color=ORANGE, marker="s", ms=3.2, lw=1.3, label="＋リリース後90日の報告")
        ax.axvline(12.5, color=INK, lw=0.8); ax.text(12.7, 3, "ここから後", fontsize=8.5)
        ax.set_ylim(0, 62); ax.set_xlabel("リリース（2週間ごと、1回分の乱数）"); ax.set_title(ttl, fontsize=10.5)
    axes[0].set_ylabel("バグの数（件）")
    axes[0].legend(frameon=False, fontsize=8, loc="upper right")
    fig.suptitle("見つかった数はどちらも減る。リリース後の報告を足すと、Bは減り方が小さい", fontsize=12, y=1.02)
    save(fig, "a1089_releases.png", SRC, y=-0.03)

    # 図2：4つの物差しの変化（200回の平均、10〜90%の範囲）
    fig, ax = plt.subplots(figsize=(8.6, 4.0))
    ML = {"found": "リリース前に\n見つかった数", "per_hour": "テスト1時間\nあたりの数", "found_plus_90d": "＋リリース後\n90日の報告", "true_bugs": "入ったバグ\n（本当の数）"}
    cols = {"A": BLUE, "B": ORANGE, "C": GREEN}
    x = np.arange(len(ML)); wdt = 0.26
    for j, k in enumerate(["A", "B", "C"]):
        v = np.array([t.loc[k, f"{m}_mean"] for m in ML]) * 100
        lo = v - np.array([t.loc[k, f"{m}_p10"] for m in ML]) * 100
        hi = np.array([t.loc[k, f"{m}_p90"] for m in ML]) * 100 - v
        ax.bar(x + (j - 1) * wdt, v, wdt, color=cols[k], label=NAMES[k], yerr=[lo, hi], error_kw={"lw": 0.8, "ecolor": INK, "capsize": 2})
        for xx, vv, l0, h0 in zip(x + (j - 1) * wdt, v, lo, hi):
            if vv >= 0:
                ax.text(xx, vv + h0 + 1.5, f"{round(vv, 2):+g}", ha="center", va="bottom", fontsize=7)
            else:
                ax.text(xx, vv - l0 - 1.5, f"{round(vv, 2):+g}".replace("-", "−"), ha="center", va="top", fontsize=7)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels(ML.values(), fontsize=9)
    ax.set_ylim(-50, 100); ax.set_ylabel("後の12回の、前の12回からの変化（%）")
    ax.legend(frameon=False, fontsize=8.5, ncol=1, loc="upper right")
    ax.set_title("見つかった数が同じ3割減でも、1時間あたりと報告を足した数は分かれる\n（200回の平均、線は10〜90%の範囲）", fontsize=11)
    save(fig, "a1089_metrics.png", SRC, y=-0.03)

    # 図3：確かめ（減り方3割の9通り）：Bの1時間あたりと、報告を足した数
    g3 = grid[grid["drop"] == 0.3].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8.8, 4.0))
    x = np.arange(len(g3)); wdt = 0.27
    ax.bar(x - wdt, g3.B_per_hour * 100, wdt, color=ORANGE, label="B：テスト1時間あたりの数")
    ax.bar(x, g3.B_found_plus_90d * 100, wdt, color=LIGHT, label="B：＋リリース後90日の報告")
    ax.bar(x + wdt, g3.A_found_plus_90d * 100, wdt, color=BLUE, label="A：＋リリース後90日の報告")
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(x); ax.set_xticklabels([f"ばらつき{s}\n見つかる{int(f * 100)}%" for s, f in zip(g3.sigma_find, g3.find_share)], fontsize=7.8)
    ax.set_ylabel("前の12回からの変化（%、各40回の平均）")
    ax.set_xlabel("見つけやすさのばらつき（対数の標準偏差）と、もとのリリース前に見つかる割合")
    for xx, vv in zip(x - wdt, g3.B_per_hour * 100):
        ax.text(xx, vv + 4, f"+{round(vv, 2):g}", ha="center", fontsize=7)
    ax.set_ylim(-45, g3.B_per_hour.max() * 100 + 70)
    ax.legend(frameon=False, fontsize=8.5, ncol=1, loc="upper left")
    ax.set_title("見つかった数が3割減ったとき：置き方9通り（Bはテストの時間を減らした）", fontsize=11)
    save(fig, "a1089_robust.png", SRC, y=-0.04)

    print(json.dumps({k: out[k] for k in ["derived", "A_found_drop_more_than_B_share", "rule_plus90_le_minus15pct", "grid27_ranges", "grid27_B_plus90_vs_A_gap", "grid27_max_abs_formula_gap_per_hour_B", "data_check"]}, ensure_ascii=False, indent=1))
    print(tab.T.to_string()); print(grid.to_string()); print(extra.T.to_string())
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
