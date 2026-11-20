"""860 進み具合の「%」は、作業数で数えるか時間で数えるかで変わるのか？（架空のデータ）

架空のプロジェクト。作業40個を1人で順に行う。作業ごとの見積もり（日）は大きさがばらばら（対数正規、中央値2日、0.5日刻み）。
実際の日数＝見積もり×振れ（対数正規、中央値1、ばらつき 0.4）。
進み具合の数え方は3つ：①終わった作業の件数 ②終わった作業の見積もり日数の合計 ③使った日数÷予定の日数（見積もりの合計）。
本当の進み具合＝使った日数÷実際にかかった日数の合計（終わってから分かる）。1人で休まず進めるので、時間に比例する。
作業の順番（小さい順・ばらばら・大きい順）で、各数え方が「50%」「90%」と言ったときの本当の進み具合を数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 860
SRC = "架空のプロジェクトの作業（作成者が乱数で作成、seed 860）"
REPS = 4000
ORDERS = {"small": "小さい作業から", "random": "順番はばらばら", "large": "大きい作業から"}
MEAS = {"count": "件数で数える", "est": "見積もり日数で数える", "time": "使った日数÷予定"}


def make(rng, n=40, size_sigma=0.8, noise=0.4, bias=1.0):
    est = np.maximum(0.5, np.round(2.0 * np.exp(size_sigma * rng.standard_normal(n)) * 2) / 2)
    act = est * bias * np.exp(noise * rng.standard_normal(n))
    return est, act


def arrange(rng, est, act, order):
    if order == "small":
        idx = np.argsort(est, kind="stable")
    elif order == "large":
        idx = np.argsort(-est, kind="stable")
    else:
        idx = rng.permutation(len(est))
    return est[idx], act[idx]


def true_when(est, act, p):
    """各数え方が初めて p 以上になった時刻の、本当の進み具合（使った日数÷実際の合計）"""
    fin = np.cumsum(act); T = fin[-1]; n = len(est)
    k_cnt = int(np.ceil(p * n - 1e-9)) - 1
    k_est = int(np.argmax(np.cumsum(est) / est.sum() >= p - 1e-9))
    t_time = p * est.sum()
    return {"count": fin[k_cnt] / T, "est": fin[k_est] / T, "time": min(t_time / T, 1.0)}


def value_at(est, act, q):
    """本当の進み具合が q のときの、各数え方の値"""
    fin = np.cumsum(act); T = fin[-1]; t = q * T
    k = int(np.searchsorted(fin, t, side="right"))
    return {"count": k / len(est), "est": est[:k].sum() / est.sum(), "time": t / est.sum()}


def run(seed, order, reps=REPS, **kw):
    rng = np.random.default_rng(seed)
    rows = []
    for r in range(reps):
        est, act = make(rng, **kw)
        e, a = arrange(rng, est, act, order)
        w50, w90, v50 = true_when(e, a, .5), true_when(e, a, .9), value_at(e, a, .5)
        rows.append({**{f"true_at50_{m}": w50[m] for m in MEAS}, **{f"true_at90_{m}": w90[m] for m in MEAS},
                     **{f"val_true50_{m}": v50[m] for m in MEAS}, "overrun": a.sum() / e.sum()})
    return pd.DataFrame(rows)


def summ(df):
    o = {}
    for m in MEAS:
        for c in ["true_at50", "true_at90", "val_true50"]:
            s = df[f"{c}_{m}"]
            o[f"{c}_{m}"] = round(float(s.mean()) * 100, 1)
            o[f"{c}_{m}_p10"] = round(float(s.quantile(.1)) * 100, 1)
            o[f"{c}_{m}_p90"] = round(float(s.quantile(.9)) * 100, 1)
    o["overrun_mean_pct"] = round(float(df.overrun.mean() - 1) * 100, 1)
    return o


def main():
    rng = np.random.default_rng(SEED)
    # データ：1回分のプロジェクト（小さい順）
    est, act = make(rng)
    e, a = arrange(rng, est, act, "small")
    pd.DataFrame({"order_no": np.arange(1, 41), "estimate_days": e, "actual_days": a.round(3),
                  "finish_day": np.cumsum(a).round(3)}).to_csv(DATA / "one_project_small_first.csv", index=False)

    # 1) 基本：順番ごと
    base = []
    for i, (o, lab) in enumerate(ORDERS.items()):
        base.append({"order": o, "order_label": lab, **summ(run(SEED * 10 + i, o))})
    base = pd.DataFrame(base)
    base.to_csv(RES / "by_order.csv", index=False)

    # 2) 確かめ：大きさのばらつき・日数の振れ・楽観・作業の数
    cases = [("基本", {}), ("大きさのばらつき 小（0.3）", {"size_sigma": 0.3}),
             ("大きさのばらつき 大（1.2）", {"size_sigma": 1.2}),
             ("日数の振れ 小（0.2）", {"noise": 0.2}), ("日数の振れ 大（0.8）", {"noise": 0.8}),
             ("実際は見積もりの1.3倍かかる", {"bias": 1.3}),
             ("作業20個", {"n": 20}), ("作業100個", {"n": 100})]
    rob = []
    for j, (lab, kw) in enumerate(cases):
        for i, o in enumerate(ORDERS):
            s = summ(run(SEED * 1000 + j * 10 + i, o, reps=2000, **kw))
            rob.append({"case": lab, "order": o, **{k: s[k] for k in
                        ["true_at90_count", "true_at90_est", "true_at90_time", "val_true50_count",
                         "val_true50_est", "val_true50_time", "overrun_mean_pct"]}})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness.csv", index=False)

    out = {"setting": {"tasks": 40, "size": "見積もり＝2日×exp(0.8×標準正規)、0.5日刻み・最小0.5日",
                       "noise_sigma": 0.4, "workers": 1, "reps": REPS},
           "one_project": {"tasks": 40, "estimate_total": float(e.sum()), "actual_total": round(float(a.sum()), 2),
                           "smallest_half_estimate_share": round(float(e[:20].sum() / e.sum()), 3),
                           "true_at50": {m: round(float(v) * 100, 1) for m, v in true_when(e, a, .5).items()},
                           "true_at90": {m: round(float(v) * 100, 1) for m, v in true_when(e, a, .9).items()}},
           "overrun_theory_pct": round(float(np.exp(0.4 ** 2 / 2) - 1) * 100, 1),
           "by_order": base.to_dict("records"), "robustness": rob.to_dict("records")}
    json.dump(out, open(RES / "a860_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1回分の進み具合の線（小さい順）
    fin = np.cumsum(a); T = fin[-1]
    t = np.linspace(0, T, 600)
    k = np.searchsorted(fin, t, side="right")
    cnt = k / 40; ce = np.concatenate([[0], np.cumsum(e)]) / e.sum(); estp = ce[k]
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(t, t / T * 100, color=INK, lw=2, label="本当の進み具合（使った日数÷実際の合計）")
    ax.step(t, cnt * 100, where="post", color=ORANGE, label="件数で数える")
    ax.step(t, estp * 100, where="post", color=BLUE, label="見積もり日数で数える")
    ax.plot(t, t / e.sum() * 100, color=GRAY, ls="--", label="使った日数÷予定")
    ax.set_xlabel("始めてからの日数"); ax.set_ylabel("進み具合（%）"); ax.set_ylim(0, 115)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title(f"小さい作業から片づけた1回分（作業40個、実際は{T:.0f}日）")
    save(fig, "a860_one_project.png", SRC)

    # 図2：「90%」と言ったときの本当の進み具合
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    x = np.arange(3); w = 0.26
    for i, (m, col) in enumerate([("count", ORANGE), ("est", BLUE), ("time", GRAY)]):
        v = base[f"true_at90_{m}"].values
        lo, hi = v - base[f"true_at90_{m}_p10"].values, base[f"true_at90_{m}_p90"].values - v
        ax.bar(x + (i - 1) * w, v, w, color=col, label=MEAS[m], yerr=[lo, hi], capsize=3, ecolor="#555")
        for xx, vv in zip(x + (i - 1) * w, v):
            ax.text(xx, 4, f"{vv:.0f}", ha="center", fontsize=8.5, color="white")
    ax.axhline(90, color=INK, lw=1, ls=":")
    ax.set_xticks(x); ax.set_xticklabels(base.order_label); ax.set_ylim(0, 105)
    ax.set_ylabel("本当の進み具合（%、線は10〜90%）")
    ax.legend(frameon=False, fontsize=9, loc="upper center", ncol=3, bbox_to_anchor=(0.5, -0.12))
    ax.set_title("「90%終わった」と言った時点の、本当の進み具合（4,000回の平均）")
    save(fig, "a860_at90.png", SRC, y=-0.1)

    # 図3：確かめ（件数で数えたときの「90%」の本当の進み具合）
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    labs = [c for c, _ in cases]
    y = np.arange(len(labs))
    for o, col, mk in [("small", ORANGE, "o"), ("random", GRAY, "s"), ("large", BLUE, "D")]:
        g = rob[rob.order == o].set_index("case").loc[labs]
        ax.plot(g.true_at90_count, y, mk, color=col, label=ORDERS[o], ms=6)
    ax.axvline(90, color=INK, lw=1, ls=":")
    ax.set_yticks(y); ax.set_yticklabels(labs, fontsize=9); ax.invert_yaxis()
    ax.set_xlabel("件数で「90%」と言った時点の本当の進み具合（%、2,000回の平均）"); ax.set_xlim(50, 100)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("置き方を変えても、小さい作業から片づけると件数の%は先に進む")
    save(fig, "a860_robust.png", SRC)
    print(out["one_project"]); print(base.T.to_string()); print(rob.to_string())


if __name__ == "__main__":
    main()
