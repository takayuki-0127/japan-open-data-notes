"""857 同時に持つ案件を増やすと、1件あたりの日数は何倍になるのか？（架空のデータ）

架空の担当者1人が、K 件の案件を同じ日に受け取る。案件ごとの作業時間は対数正規分布（平均40時間、ばらつき0.5）。1日8時間働く。
「同時に回す」：終わっていない案件を、L 時間ずつ順番に回す。別の案件に切り替えるたびに、頭の切り替えに c 時間かかる（作業は進まない）。
「1件ずつ順に」：受け取った順に1件ずつ終わらせる（切り替えは案件が終わったときだけ）。
1件あたりの日数＝受け取ってから終わるまでの日数（K 件の平均）。1件だけを持ったときの日数（作業時間÷8、K 件の平均）の何倍かを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 857
SRC = "架空の担当者と案件（作成者が乱数で作成、seed 857）"
MEAN_H, SIGMA, DAY_H = 40.0, 0.5, 8.0
REPS = 2000


def sizes(rng, k):
    mu = np.log(MEAN_H) - SIGMA ** 2 / 2
    return rng.lognormal(mu, SIGMA, k)


def run_concurrent(w, L=2.0, c=0.25):
    """終わっていない案件を L 時間ずつ順番に回す。各案件の終わる時刻（時間）と、切り替えに使った時間を返す"""
    left = w.copy(); fin = np.zeros(len(w)); t = 0.0; lost = 0.0; last = None
    while (left > 1e-12).any():
        for i in range(len(w)):
            if left[i] <= 1e-12:
                continue
            if last is not None and last != i:
                t += c; lost += c
            x = min(L, left[i]); t += x; left[i] -= x; last = i
            if left[i] <= 1e-12:
                fin[i] = t
    return fin, lost


def run_sequential(w, c=0.25):
    fin = np.cumsum(w) + c * np.arange(len(w))
    return fin, c * (len(w) - 1)


def stats(rng, k, L=2.0, c=0.25, reps=REPS):
    rows = []
    for _ in range(reps):
        w = sizes(rng, k)
        for name, (fin, lost) in [("同時に回す", run_concurrent(w, L, c)), ("1件ずつ順に", run_sequential(w, c))]:
            rows.append({"policy": name, "lead_days": (fin / DAY_H).mean(), "ratio": fin.mean() / w.mean(),
                         "all_done_days": fin.max() / DAY_H, "lost_share": lost / fin.max()})
    d = pd.DataFrame(rows)
    g = d.groupby("policy", sort=False).agg(lead_days=("lead_days", "mean"), ratio=("ratio", "mean"),
                                           all_done_days=("all_done_days", "mean"), lost_share=("lost_share", "mean"))
    return g.round(3)


def main():
    rng = np.random.default_rng(SEED)

    # 1) 案件の数 K ごと（L=2時間・c=0.25時間）
    rows = []
    for k in range(1, 9):
        g = stats(rng, k)
        for pol, r in g.iterrows():
            rows.append({"K": k, "policy": pol, **r.to_dict()})
    byk = pd.DataFrame(rows)
    byk.to_csv(RES / "by_k.csv", index=False)

    # 2) 確かめ：切り替えの時間 c × 1回に続けて進める時間 L（K=5、各1000回）
    rob = []
    for c in [0.0, 0.25, 0.5, 1.0]:
        for L in [1.0, 2.0, 4.0, 8.0]:
            g = stats(rng, 5, L, c, 1000)
            rob.append({"c_hours": c, "L_hours": L, "conc_ratio": float(g.loc["同時に回す", "ratio"]),
                        "seq_ratio": float(g.loc["1件ずつ順に", "ratio"]),
                        "conc_all_done_days": float(g.loc["同時に回す", "all_done_days"]),
                        "seq_all_done_days": float(g.loc["1件ずつ順に", "all_done_days"]),
                        "conc_lost_share": float(g.loc["同時に回す", "lost_share"])})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness_c_L.csv", index=False)

    # 3) 確かめ：案件の大きさのばらつき（K=5、L=2・c=0.25、各1000回）
    global SIGMA
    sg = []
    for s in [0.0, 0.5, 1.0]:
        SIGMA = s
        g = stats(rng, 5, 2.0, 0.25, 1000)
        sg.append({"sigma": s, "conc_ratio": float(g.loc["同時に回す", "ratio"]), "seq_ratio": float(g.loc["1件ずつ順に", "ratio"]),
                   "conc_lead_days": float(g.loc["同時に回す", "lead_days"]), "seq_lead_days": float(g.loc["1件ずつ順に", "lead_days"])})
    SIGMA = 0.5
    sg = pd.DataFrame(sg)
    sg.to_csv(RES / "robustness_sigma.csv", index=False)

    # 1回分（K=5）の記録
    w = sizes(np.random.default_rng(SEED * 10), 5)
    fc, lc = run_concurrent(w); fs, ls = run_sequential(w)
    pd.DataFrame({"project": np.arange(1, 6), "work_hours": w, "alone_days": w / DAY_H,
                  "concurrent_finish_days": fc / DAY_H, "sequential_finish_days": fs / DAY_H}).to_csv(
        DATA / "one_run_k5.csv", index=False, float_format="%.3f")
    one = {"work_hours": [round(float(x), 1) for x in w], "conc_finish_days": [round(float(x), 1) for x in fc / DAY_H],
           "seq_finish_days": [round(float(x), 1) for x in fs / DAY_H], "conc_lost_hours": round(lc, 2)}

    out = {"by_k": byk.to_dict("records"), "robustness_c_L_k5": rob.to_dict("records"),
           "robustness_sigma_k5": sg.to_dict("records"), "one_run_k5": one}
    json.dump(out, open(RES / "a857_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：K ごとの倍率
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for pol, col in [("同時に回す", ORANGE), ("1件ずつ順に", BLUE)]:
        g = byk[byk.policy == pol]
        ax.plot(g.K, g.ratio, "o-", color=col, label=pol)
        ax.text(8.15, g.ratio.iloc[-1], f"{g.ratio.iloc[-1]:.1f}倍", color=col, va="center", fontsize=9)
    ax.plot([1, 8], [1, 8], color=GRAY, lw=.8, ls=":"); ax.text(6.2, 6.6, "件数と同じ倍率", color=GRAY, fontsize=9)
    ax.set_xlabel("同時に持つ案件の数（件）"); ax.set_ylabel("1件あたりの日数（1件だけのときの何倍か）")
    ax.set_xlim(0.7, 8.8); ax.legend(frameon=False, fontsize=9)
    ax.set_title("同時に回すと、1件あたりの日数はほぼ件数の分だけ延びる")
    save(fig, "a857_by_k.png", SRC + "。2時間ずつ回し、切り替えに15分。各2,000回の平均")

    # 図2：1回分（K=5）のいつ終わるか
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    y = np.arange(1, 6)
    ax.barh(y - 0.2, fs / DAY_H, 0.38, color=BLUE, label="1件ずつ順に")
    ax.barh(y + 0.2, fc / DAY_H, 0.38, color=ORANGE, label="同時に回す")
    ax.scatter(w / DAY_H, y, marker="|", s=200, color=INK, zorder=3, label="1件だけのときの日数")
    ax.set_yticks(y); ax.set_yticklabels([f"案件{k}" for k in y]); ax.invert_yaxis()
    ax.set_xlabel("受け取ってから終わるまでの日数（1日8時間）")
    ax.set_xlim(0, 46); ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("同時に回すと、どの案件も最後のほうまで終わらない（5件・1回分）")
    save(fig, "a857_one_run.png", SRC + "。2時間ずつ回し、切り替えに15分")

    # 図3：切り替えの時間 × 続けて進める時間
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for c, col in zip([0.0, 0.25, 0.5, 1.0], [GRAY, LIGHT, BLUE, INK]):
        g = rob[rob.c_hours == c]
        ax.plot(g.L_hours, g.conc_ratio, "o-", color=col, label=f"切り替え {int(c*60)}分")
    seq = rob[rob.c_hours == 0.25].seq_ratio.mean()
    ax.axhline(seq, color=BLUE, lw=.8, ls="--"); ax.text(8, seq - 0.25, f"1件ずつ順に（約{seq:.1f}倍）", color=BLUE, fontsize=9, ha="right", va="top")
    ax.set_xscale("log", base=2); ax.set_xticks([1, 2, 4, 8]); ax.set_xticklabels(["1時間", "2時間", "4時間", "8時間"])
    ax.set_xlabel("1回に続けて進める時間"); ax.set_ylabel("1件あたりの日数（何倍か）"); ax.set_ylim(0, None)
    ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper right")
    ax.set_title("切り替えが重く、細切れに回すほど、倍率はさらに上がる（5件）")
    save(fig, "a857_switch.png", SRC + "。各1,000回の平均")
    print("done")


if __name__ == "__main__":
    main()
