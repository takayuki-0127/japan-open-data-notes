"""1307 「番号を台数で割った余り」で置く台を決める振り分けで1台足すと、置き場所が変わるデータは全体の何割になるのか？（架空のデータ）

作成者が置いた架空のアプリのデータ1万件。1件ごとに番号（1〜10億のでたらめな整数、重なりなし）を置き、
「番号 ÷ 台数 の余り」の台に置く。台数を変えたとき、置く台が変わる件数の割合を数える。
必要な最小の量：足すときは新しい台に入る件数、減らすときは外す台にあった件数（それ以外は動かさなくてよい）。
基本：10台→11台、番号を作り直して200回。
確かめ：もとの台数 2・3・5・10・20・50・100台で1台足す／1台減らす、10台から2・5・10・20台足す、
番号を1〜1万の連番にしたとき、10台から1台ずつ20台まで足したときの延べの量。
式：1台足す（N→N+1）と、置く台が変わらないのは番号を N×(N+1) で割った余りが N 未満のときだけなので、変わる割合は N÷(N+1)。
実機では測らず、すべてシミュレーション。
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 1307
SRC = "架空のアプリのデータの振り分け（作成者が置いた番号・台数からの乱数、seed 1307）"
N_REC, REPS = 10_000, 200


def ids(rng):
    return rng.choice(1_000_000_000, size=N_REC, replace=False) + 1


def change(idv, a, b):
    """台数 a → b にしたときの、動いた割合・必要な最小の割合など（%）"""
    s0, s1 = idv % a, idv % b
    moved = s0 != s1
    if b > a:
        need = s1 >= a                      # 新しい台に入る件数
        to_new = moved & (s1 >= a)
    else:
        need = s0 >= b                      # 外す台にあった件数
        to_new = np.zeros_like(moved)
    between = moved & ~to_new & ~(s0 >= b if b < a else np.zeros_like(moved))
    return {"moved_pct": moved.mean() * 100, "need_pct": need.mean() * 100,
            "to_new_pct": to_new.mean() * 100, "between_existing_pct": between.mean() * 100}


def avg(rows):
    d = pd.DataFrame(rows)
    out = d.mean().round(2).to_dict()
    out["moved_p10"] = round(float(d.moved_pct.quantile(.1)), 2)
    out["moved_p90"] = round(float(d.moved_pct.quantile(.9)), 2)
    out["moved_over_need"] = round(float(d.moved_pct.sum() / d.need_pct.sum()), 3)
    return out


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    id_sets = [ids(rng) for _ in range(REPS)]

    # 基本：10台→11台
    base = avg([change(v, 10, 11) for v in id_sets])
    base["stay_pct"] = round(100 - base["moved_pct"], 2)
    base.update({"formula_moved_pct": round(10 / 11 * 100, 2), "formula_to_new_pct": round(1 / 11 * 100, 2),
                 "formula_between_pct": round(9 / 11 * 100, 2)})
    v = id_sets[0]
    pd.DataFrame({"record_id": v, "server_10": v % 10 + 1, "server_11": v % 11 + 1}).to_csv(
        DATA / "set1_records.csv", index=False)
    one = change(v, 10, 11)
    flow = pd.crosstab(pd.Series(v % 10 + 1, name="before_10"), pd.Series(v % 11 + 1, name="after_11"))
    flow.to_csv(RES / "set1_flow_10_to_11.csv")

    # 連番の番号（作りどおり）
    seq = np.arange(1, N_REC + 1)
    seq_r = {k: round(x, 2) for k, x in change(seq, 10, 11).items()}

    # もとの台数ごと：1台足す／1台減らす
    rows = []
    for n in [2, 3, 5, 10, 20, 50, 100]:
        a = avg([change(v, n, n + 1) for v in id_sets]); a.update({"from": n, "to": n + 1, "kind": "1台足す",
                                                                 "formula_moved_pct": round(n / (n + 1) * 100, 2)})
        r = avg([change(v, n, n - 1) for v in id_sets]) if n > 2 else None
        rows.append(a)
        if r:
            r.update({"from": n, "to": n - 1, "kind": "1台減らす", "formula_moved_pct": round((1 - 1 / n) * 100, 2)})
            rows.append(r)
    by_n = pd.DataFrame(rows)[["kind", "from", "to", "moved_pct", "moved_p10", "moved_p90", "formula_moved_pct",
                               "need_pct", "moved_over_need"]]
    by_n.to_csv(RES / "by_servers.csv", index=False)

    # 10台から何台か足す
    rows = []
    for add in [1, 2, 5, 10, 20]:
        a = avg([change(v, 10, 10 + add) for v in id_sets]); a.update({"from": 10, "to": 10 + add})
        rows.append(a)
    by_add = pd.DataFrame(rows)[["from", "to", "moved_pct", "moved_p10", "moved_p90", "need_pct", "moved_over_need"]]
    by_add.to_csv(RES / "by_added.csv", index=False)

    # 10台から1台ずつ20台まで足したときの延べ
    steps = []
    for n in range(10, 20):
        c = avg([change(v, n, n + 1) for v in id_sets])
        steps.append({"from": n, "to": n + 1, "moved_pct": c["moved_pct"], "need_pct": c["need_pct"]})
    steps = pd.DataFrame(steps)
    steps.to_csv(RES / "one_by_one_10_to_20.csv", index=False)
    once = avg([change(v, 10, 20) for v in id_sets])
    cum = {"cum_moved_pct": round(float(steps.moved_pct.sum()), 2), "cum_need_pct": round(float(steps.need_pct.sum()), 2),
           "formula_cum_moved_pct": round(sum(n / (n + 1) for n in range(10, 20)) * 100, 2),
           "formula_cum_need_pct": round(sum(1 / (n + 1) for n in range(10, 20)) * 100, 2),
           "once_10_to_20_moved_pct": once["moved_pct"], "once_10_to_20_need_pct": once["need_pct"]}

    out = {"base_10_to_11": base, "set1_10_to_11": {k: round(x, 2) for k, x in one.items()},
           "sequential_ids_10_to_11": seq_r, "by_servers": by_n.to_dict("records"),
           "by_added_from_10": by_add.to_dict("records"), "one_by_one_10_to_20": cum,
           "range_add1_moved_pct": [float(by_n[by_n.kind == "1台足す"].moved_pct.min()), float(by_n[by_n.kind == "1台足す"].moved_pct.max())],
           "range_add1_over_need": [float(by_n[by_n.kind == "1台足す"].moved_over_need.min()), float(by_n[by_n.kind == "1台足す"].moved_over_need.max())],
           "max_abs_gap_formula_pt": round(float((by_n.moved_pct - by_n.formula_moved_pct).abs().max()), 2)}
    json.dump(out, open(RES / "a1307_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)

    # 図1：10台→11台の内訳
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    labels = ["同じ台のまま", "新しい11台目へ", "もとの10台のあいだで移る"]
    vals = [base["stay_pct"], base["to_new_pct"], base["between_existing_pct"]]
    ax.barh(labels[::-1], vals[::-1], color=[ORANGE, BLUE, GRAY][::-1])
    for i, x in enumerate(vals[::-1]):
        ax.text(x + 1, i, f"{x:.2f}%", va="center", fontsize=9.5)
    ax.set_xlim(0, 100); ax.set_xlabel("全体の件数に対する割合（%、番号を作り直して200回の平均）")
    ax.set_title(f"10台→11台で置く台が変わるのは{base['moved_pct']:.2f}%。必要な最小は11台目へ移す{base['need_pct']:.2f}%", fontsize=12)
    save(fig, "a1307_breakdown.png", SRC)

    # 図2：もとの台数ごと
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for kind, col in (("1台足す", BLUE), ("1台減らす", ORANGE)):
        d = by_n[by_n.kind == kind]
        ax.plot(d["from"], d.moved_pct, "o-", color=col, label=f"{kind}：置く台が変わる割合")
        ax.plot(d["from"], d.need_pct, "o:", color=col, ms=4, label=f"{kind}：必要な最小の割合")
    ax.set_xscale("log"); ax.set_xticks([2, 3, 5, 10, 20, 50, 100]); ax.set_xticklabels(["2", "3", "5", "10", "20", "50", "100"])
    ax.set_ylim(0, 105); ax.set_xlabel("もとの台数（対数の目盛り）"); ax.set_ylabel("全体の件数に対する割合（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="center right")
    ax.set_title("台数が多いほど、1台の増減で動く割合は100%に近づく")
    save(fig, "a1307_by_servers.png", SRC)

    # 図3：10台から何台足すか
    fig, ax = plt.subplots(figsize=(8.0, 3.8))
    x = np.arange(len(by_add)); w = 0.38
    ax.bar(x - w / 2, by_add.moved_pct, w, color=BLUE, label="置く台が変わる割合")
    ax.bar(x + w / 2, by_add.need_pct, w, color=LIGHT, label="必要な最小の割合（新しい台に入る分）")
    for i, (m, nd) in enumerate(zip(by_add.moved_pct, by_add.need_pct)):
        ax.text(i - w / 2, m + 1.5, f"{m:.2f}%", ha="center", fontsize=8.5)
        ax.text(i + w / 2, nd + 1.5, f"{nd:.2f}%", ha="center", fontsize=8.5)
    ax.set_xticks(x); ax.set_xticklabels([f"10→{t}台" for t in by_add["to"]])
    ax.set_ylim(0, 110); ax.set_ylabel("全体の件数に対する割合（%）")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("20台・30台のように何倍かにすると、動く割合は必要な最小と同じ（作りどおり）")
    save(fig, "a1307_by_added.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=float)); print("sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
