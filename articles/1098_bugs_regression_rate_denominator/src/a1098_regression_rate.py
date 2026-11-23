"""1098 直したあとに別の所が壊れる率は、何で割るかでどう変わるのか？（架空のデータ）

架空のアプリの開発チーム3つ（A・B・C）の修正の記録を乱数で作る。修正1件が別の所を壊す数（壊れ）は、
作成者が置いたチームごとの壊れやすさ k と、修正の大きさ（変更した行数）で決まる。
同じ3か月の記録を、修正の件数・変更の登録の回数・変更した千行・リリースの回数・
大きさの帯をそろえた修正の件数で割り、さらに「期間の終わりまでに見つかった壊れ」だけを数えた率も出して、
値とチームの順位がどう変わるか、置いた壊れやすさの順（B＞C＞A）をどれだけ当てるかを数える。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1098
SRC = "架空の開発チーム3つの修正の記録（作成者が置いた確率からの乱数、seed 1098）"
TEAMS = ["A", "B", "C"]
TEAM_LABEL = {"A": "A（大きくまとめて直す）", "B": "B（小さく分けて直す）", "C": "C（その間）"}
P = {  # チームごとの置き方
    "A": {"k": 0.05, "fix": 40, "med": 120, "c": 200, "rel": 2, "late": True},
    "B": {"k": 0.075, "fix": 90, "med": 30, "c": 15, "rel": 8, "late": False},
    "C": {"k": 0.06, "fix": 60, "med": 60, "c": 60, "rel": 4, "late": False},
}
BASE = {"beta": 0.7, "sigma": 0.8, "delay": 14.0, "months": 3}
REF_LINES = 60.0
BANDS = [0, 40, 120, 10 ** 9]
RATES = {"per_fix": "①修正1件あたり", "per_commit": "②変更の登録1回あたり", "per_kloc": "③変更した千行あたり",
         "per_release": "④リリース1回あたり", "per_fix_found": "⑤期間内に見つかった分÷修正の件数",
         "per_fix_band": "⑥大きさの帯をそろえた修正1件あたり"}
TRUE_ORDER = ["B", "C", "A"]  # 置いた k の大きい順
REPS = 2000
GRID_REPS = 300


def r(x, d=4):
    return round(float(x), d)


def sim_team(rng, t, reps, beta, sigma, delay, months, k_b=None):
    p = dict(P[t])
    if t == "B" and k_b is not None:
        p["k"] = k_b
    days = 30 * months
    n = rng.poisson(p["fix"] * months, reps)
    rep = np.repeat(np.arange(reps), n)
    m = len(rep)
    lines = np.maximum(1, np.round(np.exp(np.log(p["med"]) + sigma * rng.standard_normal(m)))).astype(int)
    commits = 1 + rng.poisson(lines / p["c"])
    if p["late"]:
        day = 30 * rng.integers(0, months, m) + 30 * rng.beta(3, 1, m)
    else:
        day = days * rng.random(m)
    lam = p["k"] * (lines / REF_LINES) ** beta
    regs = rng.poisson(lam)
    # 壊れごとに見つかるまでの日数を引き、期間の終わりまでに見つかった数を数える
    idx = np.repeat(np.arange(m), regs)
    found_each = (day[idx] + rng.exponential(delay, len(idx))) < days
    found = np.bincount(idx[found_each], minlength=m)
    band = np.digitize(lines, BANDS[1:-1])
    return pd.DataFrame({"rep": rep, "lines": lines, "commits": commits, "day": day, "regs": regs,
                         "found": found, "band": band})


def rates_for(dfs, reps, months):
    """チームごと・回ごとの6つの率"""
    out = {}
    # 大きさの帯の重み：その回の3チームを合わせた修正の件数の割合
    allb = np.zeros((reps, 3))
    for t in TEAMS:
        d = dfs[t]
        for b in range(3):
            allb[:, b] += np.bincount(d.rep[d.band == b], minlength=reps)
    w = allb / allb.sum(1, keepdims=True)
    for t in TEAMS:
        d = dfs[t]
        nf = np.bincount(d.rep, minlength=reps).astype(float)
        rg = np.bincount(d.rep, weights=d.regs, minlength=reps)
        cm = np.bincount(d.rep, weights=d.commits, minlength=reps)
        ln = np.bincount(d.rep, weights=d.lines, minlength=reps)
        fd = np.bincount(d.rep, weights=d.found, minlength=reps)
        band_rate = np.zeros(reps)
        for b in range(3):
            sel = d.band == b
            nb = np.bincount(d.rep[sel], minlength=reps).astype(float)
            rb = np.bincount(d.rep[sel], weights=d.regs[sel], minlength=reps)
            band_rate += w[:, b] * np.divide(rb, nb, out=np.zeros(reps), where=nb > 0)
        out[t] = {"n_fix": nf, "regs": rg, "commits": cm, "lines": ln, "found": fd,
                  "per_fix": rg / nf, "per_commit": rg / cm, "per_kloc": rg / ln * 1000,
                  "per_release": rg / (P[t]["rel"] * months), "per_fix_found": fd / nf, "per_fix_band": band_rate}
    return out


def accuracy(out):
    """置いた順（B＞C＞A）の1位を当てた割合、順をすべて当てた割合（同じ値は外れ）"""
    res = {}
    for k in RATES:
        a, b, c = out["A"][k], out["B"][k], out["C"][k]
        top = (b > a) & (b > c)
        full = (b > c) & (c > a)
        res[k] = {"top_B": float(top.mean()), "full_order": float(full.mean())}
    return res


def formula(t, beta, sigma, k_b=None):
    p = dict(P[t])
    if t == "B" and k_b is not None:
        p["k"] = k_b
    e_pow = (p["med"] / REF_LINES) ** beta * np.exp(beta ** 2 * sigma ** 2 / 2)
    e_l = p["med"] * np.exp(sigma ** 2 / 2)
    per_fix = p["k"] * e_pow
    return {"per_fix": per_fix, "per_commit": per_fix / (1 + e_l / p["c"]), "per_kloc": per_fix / e_l * 1000,
            "per_release": p["fix"] * per_fix / p["rel"]}


def run(rng, reps, beta=BASE["beta"], sigma=BASE["sigma"], delay=BASE["delay"], months=BASE["months"], k_b=None):
    dfs = {t: sim_team(rng, t, reps, beta, sigma, delay, months, k_b) for t in TEAMS}
    return dfs, rates_for(dfs, reps, months)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)

    # 主な結果：3か月×2,000回
    dfs, out = run(rng, REPS)
    rows = []
    for t in TEAMS:
        o = out[t]
        f = formula(t, BASE["beta"], BASE["sigma"])
        row = {"team": t, "k": P[t]["k"], "fix_per_q": r(o["n_fix"].mean(), 2), "lines_mean": r(o["lines"].sum() / o["n_fix"].sum(), 2),
               "commits_per_fix": r(o["commits"].sum() / o["n_fix"].sum(), 3), "regs_per_q": r(o["regs"].mean(), 3),
               "found_share": r(o["found"].sum() / o["regs"].sum(), 4)}
        # 全回を合わせた比（合計÷合計）
        row["per_fix"] = r(o["regs"].sum() / o["n_fix"].sum())
        row["per_commit"] = r(o["regs"].sum() / o["commits"].sum())
        row["per_kloc"] = r(o["regs"].sum() / o["lines"].sum() * 1000)
        row["per_release"] = r(o["regs"].sum() / (P[t]["rel"] * BASE["months"] * REPS))
        row["per_fix_found"] = r(o["found"].sum() / o["n_fix"].sum())
        row["per_fix_band"] = r(o["per_fix_band"].mean())
        for kk, v in f.items():
            row[f"formula_{kk}"] = r(v)
        rows.append(row)
    teams = pd.DataFrame(rows)
    teams.to_csv(RES / "rates_by_team.csv", index=False)

    acc = accuracy(out)
    acc_tab = pd.DataFrame([{"rate": k, "label": RATES[k], "top_B": r(acc[k]["top_B"]), "full_order": r(acc[k]["full_order"])} for k in RATES])
    acc_tab.to_csv(RES / "rank_accuracy.csv", index=False)

    # 1位になったチームの割合（率ごと）
    top_rows = []
    for k in RATES:
        v = np.vstack([out[t][k] for t in TEAMS])
        mx = v.max(0)
        uniq = (v == mx).sum(0) == 1
        for i, t in enumerate(TEAMS):
            top_rows.append({"rate": k, "team": t, "share_top": r(((v[i] == mx) & uniq).mean())})
        top_rows.append({"rate": k, "team": "tie", "share_top": r((~uniq).mean())})
    tops = pd.DataFrame(top_rows)
    tops.to_csv(RES / "top_team_share.csv", index=False)

    # 6つの率の最大÷最小（チームごと、合計÷合計の値は単位が違うので、順位だけを比べる）
    # 期間の長さ（1・3・12か月）
    per_rows = []
    for mo in [1, 3, 12]:
        _, o2 = run(rng, 1000, months=mo)
        a2 = accuracy(o2)
        for k in RATES:
            per_rows.append({"months": mo, "rate": k, "top_B": r(a2[k]["top_B"]), "full_order": r(a2[k]["full_order"])})
    period = pd.DataFrame(per_rows)
    period.to_csv(RES / "by_period.csv", index=False)

    # 確かめ：大きさの効き方 beta × B の壊れやすさ k_B × 大きさの散らばり sigma（36通り、各300回）
    grid_rows = []
    for beta in [0.4, 0.7, 1.0, 1.3]:
        for k_b in [0.075, 0.09, 0.12]:
            for sigma in [0.5, 0.8, 1.1]:
                _, o3 = run(rng, GRID_REPS, beta=beta, sigma=sigma, k_b=k_b)
                a3 = accuracy(o3)
                row = {"beta": beta, "k_B": k_b, "sigma": sigma}
                for k in RATES:
                    row[f"top_B_{k}"] = r(a3[k]["top_B"])
                    row[f"full_{k}"] = r(a3[k]["full_order"])
                fa = {t: formula(t, beta, sigma, k_b) for t in TEAMS}
                for kk in ["per_fix", "per_commit", "per_kloc", "per_release"]:
                    row[f"formula_order_{kk}"] = "".join(sorted(TEAMS, key=lambda t: -fa[t][kk]))
                grid_rows.append(row)
    grid = pd.DataFrame(grid_rows)
    grid.to_csv(RES / "grid.csv", index=False)

    # 確かめ：見つかるまでの日数（⑤だけが変わる。各1,000回）
    dl_rows = []
    for delay in [7.0, 14.0, 28.0]:
        _, o4 = run(rng, 1000, delay=delay)
        a4 = accuracy(o4)
        row = {"delay": delay}
        for t in TEAMS:
            row[f"found_share_{t}"] = r(o4[t]["found"].sum() / o4[t]["regs"].sum())
            row[f"per_fix_found_{t}"] = r(o4[t]["found"].sum() / o4[t]["n_fix"].sum())
        row["uniform_formula_found_share"] = r(1 - delay / (30 * BASE["months"]) * (1 - np.exp(-30 * BASE["months"] / delay)))
        row["top_B_per_fix_found"] = r(a4["per_fix_found"]["top_B"])
        row["top_A_per_fix_found"] = r(float(((o4["A"]["per_fix_found"] > o4["B"]["per_fix_found"]) & (o4["A"]["per_fix_found"] > o4["C"]["per_fix_found"])).mean()))
        dl_rows.append(row)
    delay_tab = pd.DataFrame(dl_rows)
    delay_tab.to_csv(RES / "by_delay.csv", index=False)

    # data：1回目の3か月の修正の記録
    one = []
    for t in TEAMS:
        d = dfs[t][dfs[t].rep == 0].copy()
        d.insert(0, "team", t)
        one.append(d)
    one = pd.concat(one).drop(columns=["rep"]).reset_index(drop=True)
    one.insert(1, "fix_id", np.arange(1, len(one) + 1))
    one["day"] = one["day"].round(2)
    one["band"] = one["band"].map({0: "40行以下", 1: "41〜120行", 2: "121行以上"})
    one.to_csv(DATA / "fixes_one_quarter.csv", index=False)
    chk = {t: {"per_fix": r(one[one.team == t].regs.sum() / (one.team == t).sum()), "sim_rep0": r(out[t]["per_fix"][0])} for t in TEAMS}

    ga = {k: [r(grid[f"top_B_{k}"].min()), r(grid[f"top_B_{k}"].max())] for k in RATES}
    best = grid[[f"top_B_{k}" for k in RATES]].idxmax(axis=1).map(lambda s: s.replace("top_B_", ""))
    out_json = {
        "settings": {"teams": P, "base": BASE, "ref_lines": REF_LINES, "bands": "40行以下・41〜120行・121行以上", "reps": REPS, "grid_reps": GRID_REPS,
                     "true_order": "".join(TRUE_ORDER)},
        "teams": teams.to_dict(orient="records"),
        "rank_accuracy": acc_tab.to_dict(orient="records"),
        "top_team_share": tops.to_dict(orient="records"),
        "by_period": period.to_dict(orient="records"),
        "grid_top_B_range": ga,
        "grid_best_rate_count": best.value_counts().to_dict(),
        "grid_per_kloc_top_B_by_beta": {str(b): [r(g.top_B_per_kloc.min()), r(g.top_B_per_kloc.max())] for b, g in grid.groupby("beta")},
        "grid_per_fix_top_B_by_beta": {str(b): [r(g.top_B_per_fix.min()), r(g.top_B_per_fix.max())] for b, g in grid.groupby("beta")},
        "grid_band_top_B_by_beta": {str(b): [r(g.top_B_per_fix_band.min()), r(g.top_B_per_fix_band.max())] for b, g in grid.groupby("beta")},
        "grid_per_kloc_beats_band": int((grid.top_B_per_kloc > grid.top_B_per_fix_band).sum()),
        "grid_formula_order_per_kloc_true": int((grid.formula_order_per_kloc == "BCA").sum()),
        "grid_formula_order_per_kloc_by_beta": {str(b): sorted(g.formula_order_per_kloc.unique().tolist()) for b, g in grid.groupby("beta")},
        "grid_formula_order_per_fix_B_last": int((grid.formula_order_per_fix.str[-1] == "B").sum()),
        "grid_formula_B_first_per_fix": int((grid.formula_order_per_fix.str[0] == "B").sum()),
        "grid_formula_B_first_per_commit": int((grid.formula_order_per_commit.str[0] == "B").sum()),
        "grid_formula_B_first_per_release": int((grid.formula_order_per_release.str[0] == "B").sum()),
        "grid_formula_B_first_per_kloc": int((grid.formula_order_per_kloc.str[0] == "B").sum()),
        "by_delay": delay_tab.to_dict(orient="records"),
        "formula_max_rel_diff": r(max(abs(row[k] / row[f"formula_{k}"] - 1) for row in rows for k in ["per_fix", "per_commit", "per_kloc", "per_release"])),
        "data_check": chk,
    }
    json.dump(out_json, open(RES / "a1098_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    cols = {"A": GRAY, "B": ORANGE, "C": BLUE}
    # 図1：6つの率のチームごとの値（単位がちがうので小さな図を並べる）
    fig, axes = plt.subplots(2, 3, figsize=(10.2, 5.6))
    units = {"per_fix": "件", "per_commit": "件", "per_kloc": "件", "per_release": "件", "per_fix_found": "件", "per_fix_band": "件"}
    for ax, k in zip(axes.ravel(), RATES):
        v = teams.set_index("team")[k]
        ax.bar(range(3), v.values, color=[cols[t] for t in TEAMS], width=0.6)
        for i, vv in enumerate(v.values):
            ax.text(i, vv * 1.02, f"{vv:g}", ha="center", fontsize=8.5)
        ax.set_xticks(range(3)); ax.set_xticklabels(TEAMS)
        ax.set_ylim(0, v.max() * 1.25)
        ax.set_title(RATES[k], fontsize=10)
        ax.tick_params(labelsize=8)
    fig.suptitle("同じ記録でも、割る数で順が入れかわる（置いた壊れやすさは B＞C＞A、2,000回を合わせた値）", fontsize=11.5, y=1.03)
    fig.text(0.01, 0.975, "縦軸：壊れの件数÷割る数（①②⑤⑥は1件・1回あたり、③は千行あたり、④はリリース1回あたり）", fontsize=8.5, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    save(fig, "a1098_rates.png", SRC, y=-0.01)

    # 図2：3か月ごとに、いちばん壊れやすいと置いた B を1位にした割合
    fig, ax = plt.subplots(figsize=(8.2, 3.9))
    v = acc_tab.top_B.values * 100
    ax.barh(range(len(v)), v, color=[ORANGE if x == v.max() else LIGHT for x in v])
    for i, vv in enumerate(v):
        ax.text(vv + 1, i, f"{vv:.1f}%", va="center", fontsize=9)
    ax.set_yticks(range(len(v))); ax.set_yticklabels(acc_tab.label, fontsize=9); ax.invert_yaxis()
    ax.set_xlim(0, 110); ax.set_xticks(range(0, 101, 20)); ax.set_xlabel("B を1位にした3か月の割合（%、2,000回）")
    ax.set_title(f"基本の置き方では、③千行あたりは B を{v[2]:.1f}%の3か月で1位にし、①②④⑤はほとんど1位にしない", fontsize=10.5)
    save(fig, "a1098_top.png", SRC, y=-0.04)

    # 図3：確かめ：大きさの効き方 beta ごとの、B を1位にした割合の範囲
    fig, ax = plt.subplots(figsize=(8.2, 4.0))
    betas = sorted(grid.beta.unique())
    show = [("per_fix", GRAY), ("per_kloc", BLUE), ("per_fix_band", ORANGE)]
    for j, (k, c) in enumerate(show):
        lo = [grid[grid.beta == b][f"top_B_{k}"].min() * 100 for b in betas]
        hi = [grid[grid.beta == b][f"top_B_{k}"].max() * 100 for b in betas]
        xs = np.arange(len(betas)) + (j - 1) * 0.22
        ax.vlines(xs, lo, hi, color=c, lw=5, label=RATES[k])
        ax.plot(xs, lo, "_", color=c, ms=10); ax.plot(xs, hi, "_", color=c, ms=10)
    ax.set_xticks(range(len(betas))); ax.set_xticklabels([f"大きさの効き方\nβ={b}" for b in betas], fontsize=9)
    ax.set_ylim(0, 105); ax.set_ylabel("B を1位にした割合（%、各300回）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=3)
    ax.set_title("B を1位にする割合は、置いた大きさの効き方で変わる（線は B の壊れやすさと散らばりの9通りの範囲）", fontsize=10.5)
    save(fig, "a1098_robust.png", SRC, y=-0.1)

    print(teams.to_string()); print(acc_tab.to_string()); print(tops.to_string()); print(period.to_string())
    print(grid.to_string()); print(delay_tab.to_string()); print(json.dumps({k: out_json[k] for k in ["grid_top_B_range", "grid_best_rate_count", "grid_per_kloc_beats_band", "data_check"]}, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
