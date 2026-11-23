"""999 会員の来場だけで、全体の傾向は読めるのか？（架空のデータ）

架空の美術館の24か月（1年目・2年目）。来る可能性のある人を「常連」3,000人と「時々の人」6万人に分け、
人ごとの1か月の来やすさ（平均の回数）を作成者が置く。会員証で来場が記録されるのは会員だけ。
1年目の会員：常連の40%（よく来る人ほど入りやすい）と時々の人の3%。2年目の初めに会員募集で常連の会員を65%に増やす。
2年目は時々の人の来やすさを0.85倍に下げ、4〜6月目（通算16〜18か月目）に特別展（時々の人2.5倍、常連1.2倍）を置く。
全体の来場（本当の値）と、会員の来場から読んだ傾向を比べる。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 999
SRC = "架空の美術館の来場と会員（作成者が乱数で作成、seed 999）"
N_REG, N_OCC = 3000, 60000
MEAN_REG, MEAN_OCC = 1.5, 0.05
BASE = {"event": 2.5, "member_reg_y2": 0.65, "occ_y2": 0.85}
EVENT_MONTHS = [16, 17, 18]


def season(c):
    """時々の人は春と秋に山（4月目・10月目）、常連はほぼ平ら"""
    occ = 1 + 0.35 * np.cos(4 * np.pi * (c - 4) / 12)
    reg = 1 + 0.05 * np.cos(2 * np.pi * (c - 1) / 12)
    return reg, occ


def pick_weighted(rng, idx, w, k):
    return rng.choice(idx, k, replace=False, p=w / w.sum())


def run(rng, event=2.5, member_reg_y2=0.65, occ_y2=0.85, keep=False):
    r_reg = rng.gamma(2.0, MEAN_REG / 2.0, N_REG)
    r_occ_m = rng.gamma(2.0, MEAN_OCC / 2.0, int(N_OCC * 0.03))   # 時々の人のうち会員（3%）
    sum_occ_non = rng.gamma(2.0 * (N_OCC - len(r_occ_m)), MEAN_OCC / 2.0)  # 会員でない時々の人の来やすさの合計
    # 会員：1年目は常連の40%（来やすさに比例して選ぶ）、2年目の初めに残りの常連から同じ選び方で足す
    k1 = int(N_REG * 0.40); k2 = int(N_REG * member_reg_y2)
    m1 = pick_weighted(rng, np.arange(N_REG), r_reg, k1)
    rest = np.setdiff1d(np.arange(N_REG), m1)
    add = pick_weighted(rng, rest, r_reg[rest], k2 - k1) if k2 > k1 else np.array([], int)
    mem_y1 = np.zeros(N_REG, bool); mem_y1[m1] = True
    mem_y2 = mem_y1.copy(); mem_y2[add] = True

    rows = []
    v_reg = np.zeros((24, N_REG), int); v_occ_m = np.zeros((24, len(r_occ_m)), int)
    for m in range(1, 25):
        c = (m - 1) % 12 + 1
        s_reg, s_occ = season(c)
        f_reg, f_occ = 1.0, 1.0
        if m > 12:
            f_occ = occ_y2
        if m in EVENT_MONTHS:
            f_reg *= 1.2; f_occ *= event
        v_reg[m - 1] = rng.poisson(r_reg * s_reg * f_reg)
        v_occ_m[m - 1] = rng.poisson(r_occ_m * s_occ * f_occ)
        occ_non = rng.poisson(sum_occ_non * s_occ * f_occ)
        mem = mem_y1 if m <= 12 else mem_y2
        reg_v = v_reg[m - 1]
        rows.append({"month": m, "overall": int(reg_v.sum() + v_occ_m[m - 1].sum() + occ_non),
                     "regular": int(reg_v.sum()), "occasional": int(v_occ_m[m - 1].sum() + occ_non),
                     "members": int(reg_v[mem].sum() + v_occ_m[m - 1].sum()),
                     "member_count": int(mem.sum() + len(r_occ_m)),
                     "panel": int(reg_v[mem_y1].sum() + v_occ_m[m - 1].sum()),
                     "panel_reg": int(reg_v[mem_y1].sum()), "panel_occ": int(v_occ_m[m - 1].sum())})
    mo = pd.DataFrame(rows)
    mo["per_member"] = mo.members / mo.member_count
    y1, y2 = mo[mo.month <= 12].sum(), mo[mo.month > 12].sum()

    def yoy(col):
        return 100 * (y2[col] / y1[col] - 1)
    # 群ごとの前年比（1年目からの会員）を、1年目の全体の来場に占める群の割合で重み付け
    sh_reg = y1["regular"] / y1["overall"]
    weighted = sh_reg * (y2["panel_reg"] / y1["panel_reg"]) + (1 - sh_reg) * (y2["panel_occ"] / y1["panel_occ"])
    ev = mo[mo.month.isin(EVENT_MONTHS)].sum(); ev0 = mo[mo.month.isin([m - 12 for m in EVENT_MONTHS])].sum()
    r = {"yoy_overall": yoy("overall"), "yoy_members": yoy("members"),
         "yoy_per_member": 100 * ((y2["members"] / mo.member_count[mo.month > 12].mean()) /
                                  (y1["members"] / mo.member_count[mo.month <= 12].mean()) - 1),
         "yoy_panel": yoy("panel"), "yoy_weighted": 100 * (weighted - 1),
         "event_overall": 100 * (ev["overall"] / ev0["overall"] - 1),
         "event_members": 100 * (ev["members"] / ev0["members"] - 1),
         "event_panel": 100 * (ev["panel"] / ev0["panel"] - 1),
         "member_share_people_y1_pct": 100 * (mem_y1.sum() + len(r_occ_m)) / (N_REG + N_OCC),
         "member_share_visits_y1_pct": 100 * y1["members"] / y1["overall"],
         "member_share_visits_y2_pct": 100 * y2["members"] / y2["overall"],
         "regular_share_visits_y1_pct": 100 * sh_reg,
         "rate_member_reg_y1": float(r_reg[mem_y1].mean()), "rate_nonmember_reg_y1": float(r_reg[~mem_y1].mean()),
         "rate_added_reg": float(r_reg[add].mean()) if len(add) else float("nan")}
    if keep:
        mem_df = pd.DataFrame({"person_id": np.arange(1, N_REG + 1), "group": "常連", "rate": r_reg.round(4),
                               "member_y1": mem_y1.astype(int), "member_y2": mem_y2.astype(int),
                               "visits_y1": v_reg[:12].sum(0), "visits_y2": v_reg[12:].sum(0)})
        occ_df = pd.DataFrame({"person_id": np.arange(N_REG + 1, N_REG + len(r_occ_m) + 1), "group": "時々（会員）",
                               "rate": r_occ_m.round(4), "member_y1": 1, "member_y2": 1,
                               "visits_y1": v_occ_m[:12].sum(0), "visits_y2": v_occ_m[12:].sum(0)})
        r["_people"] = pd.concat([mem_df, occ_df], ignore_index=True)
        r["_monthly"] = mo
    return r


def main():
    t0 = time.time()
    m = run(np.random.default_rng(SEED), keep=True)
    people, mo = m.pop("_people"), m.pop("_monthly")
    people.to_csv(DATA / "regulars_and_occasional_members.csv", index=False)
    mo.round(4).to_csv(DATA / "monthly_visits.csv", index=False)
    main_r = {k: round(float(v), 2) for k, v in m.items()}
    main_r["weighted_minus_overall"] = round(m["yoy_weighted"] - m["yoy_overall"], 2)
    # 常連の来やすさに置いた変化（特別展の3か月だけ1.2倍、季節±5%）から出る、常連の前年比の式の値
    c12 = np.arange(1, 13); s_reg12 = season(c12)[0]; f12 = np.where((c12 >= 4) & (c12 <= 6), 1.2, 1.0)
    main_r["regular_yoy_formula_pct"] = round(float(100 * ((s_reg12 * f12).sum() / s_reg12.sum() - 1)), 2)

    reps = pd.DataFrame([run(np.random.default_rng(SEED * 1000 + i)) for i in range(100)])
    reps.round(3).to_csv(RES / "reps_base.csv", index=False)
    cols = ["yoy_overall", "yoy_members", "yoy_per_member", "yoy_panel", "yoy_weighted",
            "event_overall", "event_members", "event_panel"]
    rs = {c: {"mean": round(float(reps[c].mean()), 2), "p10": round(float(np.percentile(reps[c], 10)), 2),
              "p90": round(float(np.percentile(reps[c], 90)), 2)} for c in cols}
    for c in ["yoy_members", "yoy_per_member", "yoy_panel", "yoy_weighted"]:
        d = reps[c] - reps.yoy_overall
        rs[c]["minus_overall_mean"] = round(float(d.mean()), 2)
        rs[c]["sign_wrong_pct"] = round(100 * float((np.sign(reps[c]) != np.sign(reps.yoy_overall)).mean()), 1)

    # 確かめ：特別展の強さ×2年目の常連の会員の割合×時々の人の2年目の来やすさ（27通り、各20回）
    grid = []
    k = 0
    for ev in [1.0, 2.5, 4.0]:
        for mr in [0.40, 0.65, 0.90]:
            for oc in [1.0, 0.85, 0.7]:
                g = pd.DataFrame([run(np.random.default_rng(SEED * 100000 + 100 * k + i), ev, mr, oc) for i in range(20)])
                k += 1
                grid.append({"event": ev, "member_reg_y2": mr, "occ_y2": oc,
                             **{c: round(float(g[c].mean()), 2) for c in cols}})
    grid = pd.DataFrame(grid)
    for c in ["yoy_members", "yoy_per_member", "yoy_panel", "yoy_weighted"]:
        grid[c + "_err"] = (grid[c] - grid.yoy_overall).round(2)
    grid["event_members_err"] = (grid.event_members - grid.event_overall).round(2)
    grid.to_csv(RES / "grid_event_member_occ.csv", index=False)
    gr = {c: [float(grid[c].min()), float(grid[c].max())] for c in
          ["yoy_members_err", "yoy_per_member_err", "yoy_panel_err", "yoy_weighted_err", "event_members_err", "yoy_overall", "yoy_panel", "yoy_members", "yoy_per_member"]}
    nd = grid[grid.member_reg_y2 == 0.40]
    gr["no_drive_members_err"] = [float(nd.yoy_members_err.min()), float(nd.yoy_members_err.max())]
    gr["sign_wrong_members_cases"] = int((np.sign(grid.yoy_members) != np.sign(grid.yoy_overall)).sum())
    gr["sign_wrong_panel_cases"] = int((np.sign(grid.yoy_panel) != np.sign(grid.yoy_overall)).sum())
    gr["sign_wrong_weighted_cases"] = int((np.sign(grid.yoy_weighted) != np.sign(grid.yoy_overall)).sum())

    out = {"setting": {"regulars": N_REG, "occasional": N_OCC, "mean_rate_regular": MEAN_REG,
                       "mean_rate_occasional": MEAN_OCC, "occasional_members": int(N_OCC * 0.03), **BASE, "event_months": EVENT_MONTHS},
           "main": main_r, "reps100": rs, "grid_range": gr, "grid": grid.to_dict("records")}
    json.dump(out, open(RES / "a999_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：月ごとの来場（1年目の平均＝100）
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    for col, lab, c, mk in [("overall", "全体の来場（本当の値）", INK, "o"), ("members", "会員の来場", BLUE, "s"),
                            ("panel", "1年目からの会員の来場", GREEN, "^")]:
        idx = 100 * mo[col] / mo[col][:12].mean()
        ax.plot(mo.month, idx, marker=mk, ms=4, color=c, label=lab, lw=1.6)
    ax.axvspan(15.5, 18.5, color=ORANGE, alpha=.12, lw=0)
    ax.text(17, 198, "特別展", ha="center", color=ORANGE, fontsize=9)
    ax.axvline(12.5, color=GRAY, lw=1, ls="--")
    ax.text(12.7, 42, "2年目（会員募集のあと）", color=GRAY, fontsize=8.5)
    ax.set_xticks(range(1, 25, 2)); ax.set_xticklabels([f"{i}" for i in range(1, 25, 2)])
    ax.set_xlabel("通算の月"); ax.set_ylabel("1年目の月平均＝100"); ax.set_ylim(35, max(208, ax.get_ylim()[1]))
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("会員の来場は、全体の来場とちがう動きをする（架空の美術館）")
    save(fig, "a999_monthly.png", SRC)

    # 図2：前年比の読み方（100回の平均と10〜90%）
    lab = [("yoy_overall", "全体（本当の値）", INK), ("yoy_members", "会員の来場", BLUE),
           ("yoy_per_member", "会員1人あたり", LIGHT), ("yoy_panel", "1年目からの会員", GREEN),
           ("yoy_weighted", "常連と時々に分けて重み付け", ORANGE)]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for i, (c, l, col) in enumerate(lab):
        v = rs[c]
        ax.barh(len(lab) - 1 - i, v["mean"], color=col, height=0.6)
        ax.errorbar(v["mean"], len(lab) - 1 - i, xerr=[[v["mean"] - v["p10"]], [v["p90"] - v["mean"]]],
                    color=GRAY, capsize=3, lw=1)
        ax.text(max(v["p90"], 0) + 1.0, len(lab) - 1 - i, f"{v['mean']:+.1f}%", va="center", fontsize=9.5)
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_yticks(range(len(lab))); ax.set_yticklabels([l for _, l, _ in lab][::-1])
    ax.set_xlabel("2年目の前年比（%、100回の平均。横線は10〜90%）")
    ax.set_xlim(min(-5, rs["yoy_overall"]["p10"] - 3), max(rs["yoy_members"]["p90"] + 10, 10))
    ax.set_title("同じ2年間の前年比を、会員の来場から読むと")
    save(fig, "a999_yoy.png", SRC)

    # 図3：会員の来場の前年比のずれ（特別展の強さ×常連の会員の割合、時々の人0.85倍）
    sub = grid[grid.occ_y2 == 0.85]
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.5), sharey=True)
    vmax = float(np.abs(grid[["yoy_members_err", "yoy_weighted_err"]].values).max())
    for ax, c, t in zip(axes, ["yoy_members_err", "yoy_weighted_err"], ["会員の来場", "常連と時々に分けて重み付け"]):
        piv = sub.pivot(index="event", columns="member_reg_y2", values=c)
        ax.imshow(piv.values, cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto")
        for i in range(piv.shape[0]):
            for j in range(piv.shape[1]):
                v = piv.values[i, j]
                ax.text(j, i, f"{v:+.1f}", ha="center", va="center", fontsize=10,
                        color="white" if abs(v) > vmax * 0.6 else INK)
        ax.set_xticks(range(3)); ax.set_xticklabels([f"{x:.0%}" for x in piv.columns])
        ax.set_yticks(range(3)); ax.set_yticklabels([f"{x:g}倍" for x in piv.index])
        ax.set_xlabel("2年目の常連の会員の割合（1年目は40%）"); ax.set_title(t, fontsize=11)
        ax.spines["left"].set_visible(False); ax.spines["bottom"].set_visible(False)
    axes[0].set_ylabel("特別展の強さ（時々の人）")
    fig.suptitle("前年比のずれ（読んだ値−本当の値、ポイント。2年目の時々の人0.85倍の9通り、各20回の平均）", fontsize=12, y=1.03)
    save(fig, "a999_grid.png", SRC, y=-0.06)

    out["run_sec"] = round(time.time() - t0, 1)
    print(json.dumps({k: out[k] for k in ["main", "reps100", "grid_range", "run_sec"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
