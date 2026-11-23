"""1094 深刻度の分け方で、「重大なバグ」の件数はどれだけ変わるのか？（架空のデータ）

架空のアプリの1か月分のバグ（平均400件）に、作成者が「影響を受ける利用者の割合」と「止まり方」（4段）を置く。
同じバグを4つの分け方で「重大」に分け、件数と顔ぶれの違いを数える。
さらに、バグを記録する人が利用者の割合と止まり方を見積もるときのぶれを置き、見積もった値で分けた件数と、
置いた本当の値で分けた件数を比べる。月ごとの件数の上下と、分け方を途中で変えたときの段差も数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1094
SRC = "架空のアプリのバグ（作成者が置いた利用者の割合・止まり方・見積もりのぶれからの乱数、seed 1094）"
N_MONTH = 400
STOPS = ["見た目だけ", "回り道できる", "機能が使えない", "データが壊れる"]
BASE = {"u_sd": 1.5, "stop_mix": "基本", "err": "基本"}
MIX = {"軽め": [0.45, 0.35, 0.15, 0.05], "基本": [0.35, 0.35, 0.22, 0.08], "重め": [0.25, 0.3, 0.3, 0.15]}
ERR = {"なし": (0.0, 0.0), "基本": (0.7, 0.15), "大きい": (1.2, 0.3)}   # 利用者の割合の対数の標準偏差, 止まり方を1段ずらす確率
U_MED = 0.01
RULES = [("R1", "止まり方が「機能が使えない」以上"),
         ("R2", "利用者の割合10%以上"),
         ("R3", "「機能が使えない」以上 かつ 利用者1%以上"),
         ("R4", "「データが壊れる」、または「機能が使えない」かつ利用者10%以上")]
REPS = 400


def r(x, d=4):
    return round(float(x), d)


def bugs(rng, n, u_sd, stop_mix):
    u = np.minimum(1.0, U_MED * np.exp(rng.normal(0, u_sd, n)))
    s = rng.choice(4, n, p=MIX[stop_mix]) + 1
    return u, s


def judge(rng, u, s, err):
    sd, ps = ERR[err]
    uj = np.minimum(1.0, u * np.exp(rng.normal(0, sd, len(u)))) if sd > 0 else u.copy()
    move = rng.random(len(s)) < ps
    step = rng.choice([-1, 1], len(s))
    sj = np.clip(s + move * step, 1, 4)
    return uj, sj


def major(u, s, rule, th=0.10):
    if rule == "R1":
        return s >= 3
    if rule == "R2":
        return u >= th
    if rule == "R3":
        return (s >= 3) & (u >= 0.01)
    if rule == "R4":
        return (s == 4) | ((s == 3) & (u >= 0.10))
    raise ValueError(rule)


def run_setting(rng, reps, u_sd, stop_mix, err):
    """reps か月分：分け方ごとの件数（本当の値・見積もった値）と、2人が別々に見積もったときのそろい方"""
    rows = []
    for _ in range(reps):
        n = rng.poisson(N_MONTH)
        u, s = bugs(rng, n, u_sd, stop_mix)
        u1, s1 = judge(rng, u, s, err)
        u2, s2 = judge(rng, u, s, err)
        row = {"n": n}
        for k, _ in RULES:
            t, j1, j2 = major(u, s, k), major(u1, s1, k), major(u2, s2, k)
            either = (j1 | j2).sum()
            row.update({f"{k}_true": int(t.sum()), f"{k}_judged": int(j1.sum()),
                        f"{k}_two_agree": (j1 & j2).sum() / either if either else np.nan,
                        f"{k}_judged_hit": (j1 & t).sum() / j1.sum() if j1.sum() else np.nan})
        all4 = np.all([major(u, s, k) for k, _ in RULES], 0)
        any4 = np.any([major(u, s, k) for k, _ in RULES], 0)
        row["all_rules_share_of_any"] = all4.sum() / any4.sum()
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)
    # 1) 1か月分（400件ちょうど）
    u, s = bugs(rng, N_MONTH, BASE["u_sd"], BASE["stop_mix"])
    uj, sj = judge(rng, u, s, BASE["err"])
    df = pd.DataFrame({"bug_id": np.arange(1, N_MONTH + 1), "users_share": u.round(5), "stop_level": s,
                       "users_share_judged": uj.round(5), "stop_level_judged": sj})
    for k, _ in RULES:
        df[f"major_{k}"] = major(u, s, k).astype(int)
        df[f"major_{k}_judged"] = major(uj, sj, k).astype(int)
    df.to_csv(DATA / "bugs_one_month.csv", index=False)
    cnt = {k: int(df[f"major_{k}"].sum()) for k, _ in RULES}
    cntj = {k: int(df[f"major_{k}_judged"].sum()) for k, _ in RULES}
    sets = {k: set(df.bug_id[df[f"major_{k}"] == 1]) for k, _ in RULES}
    overlap = pd.DataFrame([[len(sets[a] & sets[b]) / len(sets[a] | sets[b]) for b in sets] for a in sets],
                           index=list(sets), columns=list(sets)).round(4)
    overlap.to_csv(RES / "overlap_one_month.csv")
    any4 = set.union(*sets.values()); all4 = set.intersection(*sets.values())
    th_counts = {f"{int(t*100)}%": int((u >= t).sum()) for t in [0.05, 0.10, 0.20]}
    near = int(((u >= 0.05) & (u < 0.20)).sum())
    one = {"count_true": cnt, "count_judged": cntj, "max_over_min_true": r(max(cnt.values()) / min(cnt.values()), 2),
           "any_rule": len(any4), "all_rules": len(all4), "all_over_any": r(len(all4) / len(any4)),
           "R2_threshold_counts": th_counts, "users_5_to_20pct": near,
           "stop_level_counts": {STOPS[i]: int((s == i + 1).sum()) for i in range(4)}}

    # 2) 基本の置き方で400か月
    base = run_setting(np.random.default_rng(SEED * 10), REPS, **BASE)
    base_s = {}
    for k, lab in RULES:
        base_s[k] = {"label": lab, "true_mean": r(base[f"{k}_true"].mean(), 2),
                     "judged_mean": r(base[f"{k}_judged"].mean(), 2),
                     "judged_over_true": r(base[f"{k}_judged"].mean() / base[f"{k}_true"].mean(), 2),
                     "true_p10": r(base[f"{k}_true"].quantile(.1), 1), "true_p90": r(base[f"{k}_true"].quantile(.9), 1),
                     "two_agree": r(base[f"{k}_two_agree"].mean()), "judged_hit": r(base[f"{k}_judged_hit"].mean())}
    base_s["all_rules_share_of_any"] = r(base.all_rules_share_of_any.mean())

    # 3) 12か月：6か月目までR3、7か月目からR1に変えたとき（本当のバグの出方は毎月同じ）
    m = base.iloc[:12].copy()
    m["month"] = np.arange(1, 13)
    m["reported"] = np.where(m.month <= 6, m.R3_judged, m.R1_judged)
    m[["month", "n", "R3_judged", "R1_judged", "reported"]].to_csv(RES / "months_rule_change.csv", index=False)
    r3 = base.R3_judged
    months = {"R3_judged_month_p10": r(r3.quantile(.1), 1), "R3_judged_month_p90": r(r3.quantile(.9), 1),
              "R3_judged_month_max_over_min_in_12": r(m.R3_judged.max() / m.R3_judged.min(), 2),
              "first6_mean": r(m.reported[:6].mean(), 2), "last6_mean": r(m.reported[6:].mean(), 2),
              "jump_ratio": r(m.reported[6:].mean() / m.reported[:6].mean(), 2)}

    # 4) 置き方を変えた確かめ：利用者の割合の散らばり × 止まり方の内わけ × 見積もりのぶれ
    rows = []
    gi = 0
    for u_sd in [1.0, 1.5, 2.0]:
        for mix in MIX:
            for err in ERR:
                gi += 1
                g = run_setting(np.random.default_rng(SEED * 100 + gi), 150, u_sd, mix, err)
                tr = {k: g[f"{k}_true"].mean() for k, _ in RULES}
                row = {"u_sd": u_sd, "stop_mix": mix, "err": err,
                       **{f"{k}_true": r(tr[k], 2) for k, _ in RULES},
                       **{f"{k}_judged_over_true": r(g[f"{k}_judged"].mean() / tr[k], 2) for k, _ in RULES},
                       **{f"{k}_two_agree": r(g[f"{k}_two_agree"].mean()) for k, _ in RULES},
                       "max_over_min_rules_true": r(max(tr.values()) / min(tr.values()), 2),
                       "all_rules_share_of_any": r(g.all_rules_share_of_any.mean())}
                rows.append(row)
    grid = pd.DataFrame(rows)
    grid.to_csv(RES / "grid.csv", index=False)
    ge = grid[grid.err != "なし"]
    out = {"n_per_month_mean": N_MONTH, "users_share_median": U_MED, "base_setting": BASE, "stop_mix": MIX,
           "judge_error": {k: {"users_log_sd": v[0], "stop_shift_prob": v[1]} for k, v in ERR.items()},
           "rules": dict(RULES), "one_month": one, "base_400months": base_s, "rule_change_12months": months,
           "grid_n": int(len(grid)),
           "grid_max_over_min_rules_true_range": [r(grid.max_over_min_rules_true.min(), 2), r(grid.max_over_min_rules_true.max(), 2)],
           "grid_all_rules_share_of_any_range": [r(grid.all_rules_share_of_any.min()), r(grid.all_rules_share_of_any.max())],
           "grid_with_error_n": int(len(ge)),
           "grid_with_error_R2_judged_over_true_range": [r(ge.R2_judged_over_true.min(), 2), r(ge.R2_judged_over_true.max(), 2)],
           "grid_with_error_R2_over_1": int((ge.R2_judged_over_true > 1).sum()),
           "grid_with_error_R4_judged_over_true_range": [r(ge.R4_judged_over_true.min(), 2), r(ge.R4_judged_over_true.max(), 2)],
           "grid_with_error_R4_over_1": int((ge.R4_judged_over_true > 1).sum()),
           "grid_with_error_two_agree_range": {k: [r(ge[f"{k}_two_agree"].min()), r(ge[f"{k}_two_agree"].max())] for k, _ in RULES}}
    json.dump(out, open(RES / "a1094_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    pd.DataFrame([{"rule": k, **{kk: vv for kk, vv in v.items()}} for k, v in base_s.items() if isinstance(v, dict)]) \
        .to_csv(RES / "rules_base.csv", index=False)

    # 図1：同じ400件を4つの分け方で（本当の値で分けた件数と、見積もった値で分けた件数）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    y = np.arange(len(RULES))[::-1]
    ax.barh(y + 0.19, [cnt[k] for k, _ in RULES], height=0.36, color=BLUE, label="置いた本当の値で分けた件数")
    ax.barh(y - 0.19, [cntj[k] for k, _ in RULES], height=0.36, color=ORANGE, label="記録した人の見積もりで分けた件数")
    for yi, (k, _) in zip(y, RULES):
        ax.text(cnt[k] + 1, yi + 0.19, f"{cnt[k]}件", va="center", fontsize=8.5)
        ax.text(cntj[k] + 1, yi - 0.19, f"{cntj[k]}件", va="center", fontsize=8.5)
    ax.set_yticks(y); ax.set_yticklabels([f"{k} {lab}" for k, lab in RULES], fontsize=8.5)
    ax.set_xlim(0, max(max(cnt.values()), max(cntj.values())) * 1.2)
    ax.set_xlabel("「重大」の件数（1か月400件のうち）")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.set_title(f"同じ400件でも、分け方で「重大」は{min(cnt.values())}〜{max(cnt.values())}件")
    save(fig, "a1094_rules.png", SRC)

    # 図2：12か月の報告の件数（7か月目に分け方を変えた）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    ax.bar(m.month, m.reported, color=[BLUE] * 6 + [ORANGE] * 6)
    for x, v in zip(m.month, m.reported):
        ax.text(x, v + 1, str(int(v)), ha="center", fontsize=8.5)
    ax.axvline(6.5, color=GRAY, lw=1, ls="--")
    ax.text(3.5, m.reported.max() * 1.12, "R3で数えた月", ha="center", color=BLUE, fontsize=9)
    ax.text(9.5, m.reported.max() * 1.12, "R1で数えた月", ha="center", color=ORANGE, fontsize=9)
    ax.set_ylim(0, m.reported.max() * 1.22); ax.set_xticks(range(1, 13))
    ax.set_xlabel("月（本当のバグの出方は12か月とも同じに置いた）"); ax.set_ylabel("報告した「重大」の件数")
    ax.set_title(f"分け方を変えた月から、「重大」は{months['jump_ratio']:.2f}倍になった（後の6か月の平均÷前の6か月）", fontsize=11)
    save(fig, "a1094_months.png", SRC)

    # 図3：置き方27通り：見積もった値で分けた件数÷本当の値で分けた件数（R2とR4）
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    x = np.arange(len(grid))
    ax.plot(x, grid.R2_judged_over_true, "o", color=ORANGE, label="R2 利用者の割合10%以上")
    ax.plot(x, grid.R4_judged_over_true, "s", color=BLUE, ms=5, label="R4 データが壊れる、または…")
    ax.axhline(1, color=INK, lw=0.8)
    for k in range(1, 3):
        ax.axvline(k * 9 - 0.5, color=GRAY, lw=0.6)
    for k, sd in enumerate([1.0, 1.5, 2.0]):
        ax.text(k * 9 + 4, 7.0, f"利用者の割合の散らばり {sd}", ha="center", fontsize=8)
    ax.set_ylim(0, 7.4); ax.set_xticks([])
    ax.set_xlabel("置き方27通り（各区切りの中は、止まり方の内わけ3通り×見積もりのぶれ なし・基本・大きい）")
    ax.set_ylabel("見積もりで分けた件数÷本当の件数")
    ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0.36, 0.8))
    ax.set_title("見積もりのぶれを置いた18通りすべてで、R2・R4の「重大」は本当より多く出る", fontsize=11.5)
    save(fig, "a1094_robust.png", SRC)


if __name__ == "__main__":
    main()
