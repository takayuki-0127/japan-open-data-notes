"""994 入口のゲートで数えるか、チケットで数えるかで、人数は変わるのか？（架空のデータ）

架空の3日間の展示会。1日券（日ごとに5,000・8,000・7,000枚）と3日通し券（1,500枚）を売る。
1日券の8%は来ない。通し券の人は各日に70%の確率で来る。券を持つ人は平均0.15人の子ども（券なし・無料）を連れる。
来た人（子どもも）は、その日に平均0.4回、外に出て入り直す（再入場）。スタッフ・出展者300人も同じ入口を、1日に平均3回通る。
数え方は3つ：販売枚数（1日券＋通し券）、チケットの読み取り（その日の最初の入場で券を読む）、
入口のゲートのセンサー（入る向きに通った回数。並んで通ると8%を見落とす）。本当の人数は、その日に来た人（子どもを含む、スタッフを含まない）。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 994
SRC = "架空の3日間の展示会の入場（作成者が乱数で作成、seed 994）"
T1 = np.array([5000, 8000, 7000])
PASS = 1500
BASE = {"noshow": 0.08, "q": 0.7, "c": 0.15, "r": 0.4, "staff": 300, "staff_pass": 3.0, "m": 0.08}
REPS = 200
GRID = {"r": [0.0, 0.2, 0.4, 0.8], "m": [0.0, 0.08, 0.15], "staff": [0, 300, 600], "c": [0.0, 0.15, 0.3]}
GRID_REPS = 20
R3 = [0.4, 0.6, 0.8, 1.0]


def one_event(rng, noshow, q, c, r, staff, staff_pass, m, r_day=None):
    """3日分を数える。r_day を渡すと日ごとの再入場の平均を変える"""
    r_day = [r] * 3 if r_day is None else r_day
    kids_pass = rng.poisson(c, PASS)
    pass_att = rng.random((3, PASS)) < q
    rows, uniq = [], 0
    for d in range(3):
        att1 = rng.random(T1[d]) >= noshow
        kids1 = rng.poisson(c, T1[d])
        holders = att1.sum() + pass_att[d].sum()
        kids = kids1[att1].sum() + kids_pass[pass_att[d]].sum()
        visitors = holders + kids
        uniq += att1.sum() + kids1[att1].sum()
        passes_v = visitors + rng.poisson(r_day[d] * visitors)            # 来た人の入る向きの通過
        passes_s = staff + rng.poisson((staff_pass - 1) * staff) if staff else 0
        gate = rng.binomial(passes_v + passes_s, 1 - m)
        rows.append({"day": d + 1, "sold": int(T1[d] + PASS), "scanned": int(holders), "gate": int(gate),
                     "true_visitors": int(visitors), "holders": int(holders), "kids": int(kids),
                     "passes_visitors": int(passes_v), "passes_staff": int(passes_s)})
    anyday = pass_att.any(0)
    uniq += anyday.sum() + kids_pass[anyday].sum()
    return rows, int(uniq)


def formula(noshow, q, c, r, staff, staff_pass, m):
    v = (T1 * (1 - noshow) + PASS * q) * (1 + c)
    return {"gate": ((v * (1 + r) + staff * staff_pass) * (1 - m)) / v, "scanned": 1 / (1 + c),
            "sold": (T1 + PASS) / v}


def main():
    t0 = time.time()
    # 1) 基本（200回）
    recs, uniqs = [], []
    for k in range(REPS):
        rows, u = one_event(np.random.default_rng(SEED * 1000 + k), **BASE)
        for x in rows:
            x["rep"] = k
        recs += rows; uniqs.append(u)
        if k == 0:
            pd.DataFrame(rows).drop(columns="rep").to_csv(DATA / "event_example.csv", index=False)
    df = pd.DataFrame(recs)
    daym = df.groupby("day").mean(numeric_only=True).drop(columns="rep")
    for col in ["sold", "scanned", "gate"]:
        daym[f"{col}_ratio"] = daym[col] / daym.true_visitors
    daym.round(4).to_csv(RES / "by_day_200reps.csv")
    tot = df.groupby("rep")[["sold", "scanned", "gate", "true_visitors"]].sum()
    tot["unique3"] = uniqs
    totm = tot.mean()
    f = formula(**BASE)

    # 2) 確かめ：再入場・見落とし・スタッフ・子どもの108通り（各20回）
    grid = []
    gi = 0
    for r in GRID["r"]:
        for m in GRID["m"]:
            for st in GRID["staff"]:
                for c in GRID["c"]:
                    p = {**BASE, "r": r, "m": m, "staff": st, "c": c}
                    acc = []
                    for k in range(GRID_REPS):
                        rows, u = one_event(np.random.default_rng(SEED * 100000 + gi * 100 + k), **p)
                        s = pd.DataFrame(rows)[["sold", "scanned", "gate", "true_visitors"]].sum()
                        acc.append(s)
                    a = pd.DataFrame(acc).mean()
                    fm = formula(**p)
                    g = {"r": r, "m": m, "staff": st, "c": c,
                         "sold_ratio": a.sold / a.true_visitors, "scanned_ratio": a.scanned / a.true_visitors,
                         "gate_ratio": a.gate / a.true_visitors,
                         "gate_ratio_formula": float(np.sum(fm["gate"] * (T1 * (1 - p["noshow"]) + PASS * p["q"])) /
                                                     np.sum(T1 * (1 - p["noshow"]) + PASS * p["q"]))}
                    g["closer"] = "ゲート" if abs(np.log(g["gate_ratio"])) < abs(np.log(g["scanned_ratio"])) else "読み取り"
                    grid.append(g); gi += 1
    grid = pd.DataFrame(grid)
    grid.round(4).to_csv(RES / "sensitivity_grid.csv", index=False)

    # 3) 3日目だけ再入場が多いと、2日目→3日目の増減の向きは
    dirs = []
    for j, r3 in enumerate(R3):
        rr = []
        for k in range(REPS):
            rows, _ = one_event(np.random.default_rng(SEED * 7000 + j * 1000 + k), **BASE, r_day=[0.4, 0.4, r3])
            d = pd.DataFrame(rows)
            rr.append({m: d[m].iloc[2] / d[m].iloc[1] for m in ["sold", "scanned", "gate", "true_visitors"]})
        rr = pd.DataFrame(rr)
        dirs.append({"r3": r3, **{f"{m}_day3_over_day2": rr[m].mean() for m in rr},
                     "gate_says_up_pct": (rr.gate > 1).mean() * 100,
                     "true_up_pct": (rr.true_visitors > 1).mean() * 100})
    dirs = pd.DataFrame(dirs)
    dirs.round(4).to_csv(RES / "day3_reentry.csv", index=False)

    r3 = lambda x: round(float(x), 3)
    out = {
        "setting": {"T1": T1.tolist(), "pass": PASS, **BASE, "reps": REPS},
        "by_day_mean": {int(d): {c: r3(v) for c, v in row.items()} for d, row in daym.iterrows()},
        "three_days_mean": {c: r3(v) for c, v in totm.items()},
        "three_days_ratio_to_sum_of_days": {c: r3(totm[c] / totm.true_visitors) for c in ["sold", "scanned", "gate"]},
        "three_days_ratio_to_unique": {c: r3(totm[c] / totm.unique3) for c in ["sold", "scanned", "gate", "true_visitors"]},
        "formula_ratio_by_day": {"gate": [r3(x) for x in f["gate"]], "scanned": r3(f["scanned"]),
                                 "sold": [r3(x) for x in f["sold"]]},
        "grid": {"n": int(len(grid)),
                 "gate_ratio_range": [r3(grid.gate_ratio.min()), r3(grid.gate_ratio.max())],
                 "scanned_ratio_range": [r3(grid.scanned_ratio.min()), r3(grid.scanned_ratio.max())],
                 "sold_ratio_range": [r3(grid.sold_ratio.min()), r3(grid.sold_ratio.max())],
                 "n_gate_closer": int((grid.closer == "ゲート").sum()),
                 "n_gate_below_1": int((grid.gate_ratio < 1).sum()),
                 "gate_formula_max_abs_gap": r3((grid.gate_ratio - grid.gate_ratio_formula).abs().max()),
                 "n_settings_per_r": int((grid.r == GRID["r"][0]).sum()),
                 "n_gate_closer_by_r": {str(r): int(((grid.r == r) & (grid.closer == "ゲート")).sum()) for r in GRID["r"]},
                 "gate_ratio_range_r0": [r3(grid[grid.r == 0].gate_ratio.min()), r3(grid[grid.r == 0].gate_ratio.max())]},
        "day3_reentry": dirs.round(3).to_dict("records"),
    }
    json.dump(out, open(RES / "a994_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：日ごとの、3つの数え方と本当の人数
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    w = 0.2
    cols = [("true_visitors", "本当の人数（子どもを含む）", INK), ("sold", "販売枚数", GRAY),
            ("scanned", "チケットの読み取り", BLUE), ("gate", "ゲートのセンサー", ORANGE)]
    for j, (cname, lab, col) in enumerate(cols):
        ax.bar(np.arange(3) + (j - 1.5) * w, daym[cname], w, color=col, label=lab)
    ax.set_xticks(np.arange(3), ["1日目", "2日目", "3日目"]); ax.set_ylabel("人（200回の平均）")
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper left"); ax.set_ylim(0, daym.gate.max() * 1.25)
    ax.set_title(f"同じ日の「来場者数」が、数え方で本当の人数の{daym.scanned_ratio.min():.2f}〜{daym.gate_ratio.max():.2f}倍に分かれる", fontsize=12)
    save(fig, "a994_methods.png", SRC)

    # 図2：108通りの、ゲートと読み取りの本当の人数に対する倍率
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    rng = np.random.default_rng(SEED)
    for i, r in enumerate(GRID["r"]):
        g = grid[grid.r == r]
        x = i + rng.uniform(-0.12, 0.12, len(g))
        ax.scatter(x - 0.18, g.scanned_ratio, s=14, color=BLUE, alpha=.7, lw=0, label="チケットの読み取り" if i == 0 else None)
        ax.scatter(x + 0.18, g.gate_ratio, s=14, color=ORANGE, alpha=.7, lw=0, label="ゲートのセンサー" if i == 0 else None)
    ax.axhline(1, color=INK, lw=1, ls="--"); ax.text(3.45, 1.02, "本当の人数", fontsize=9, ha="right")
    ax.set_xticks(range(4), [f"平均{r}回" for r in GRID["r"]]); ax.set_xlabel("1人が1日に入り直す回数（再入場）")
    ax.set_ylabel("本当の人数に対する倍率（3日間）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("再入場がなければゲートは下に外れ、多ければ上に外れる（108通り）", fontsize=12)
    save(fig, "a994_grid.png", SRC)

    # 図3：3日目の再入場を増やしたときの、2日目→3日目の比
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for cname, lab, col in cols:
        ax.plot(dirs.r3, dirs[f"{cname}_day3_over_day2"], marker="o", color=col, label=lab)
    ax.axhline(1, color=GRAY, lw=1, ls=":")
    ax.text(0.41, 0.915, "本当の人数・販売枚数・読み取りは、どれも0.89前後で重なる", fontsize=9, color=INK)
    ax.set_xticks(R3, [f"{x}" for x in R3])
    ax.set_xlabel("3日目だけの再入場の平均（1・2日目は0.4回）"); ax.set_ylabel("3日目 ÷ 2日目")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("本当は3日目が少なくても、再入場が多い日はゲートで増えて見える", fontsize=12)
    save(fig, "a994_day_direction.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
