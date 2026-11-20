"""834 くじは、先に引くのと後に引くのでどちらが有利か？（架空のデータ）

架空のくじ（箱の中に10本、当たり1本）を、10人が順番に1本ずつ引く（引いたくじは戻さない）。
引く順番ごとの当たりの割合を数える。よく混ぜたくじ・当たりの札が取りやすい（取りにくい）くじ・
少ない回数の記録で、順番の有利不利がどう見えるかを比べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 834
SRC = "架空のくじ引き（作成者が乱数で作成、seed 834）"
rng = np.random.default_rng(SEED)
N_ROUND = 100000


def draw(rng, n_lot, n_win, rounds, w=1.0):
    """n_lot 本（うち当たり n_win 本）を全部順に引く。当たりの札の取りやすさを w 倍にする。
    重みつきで戻さずに引く順番は、log(重み)+ガンベル乱数の大きい順と同じになる。
    返り値：rounds × n_lot の 0/1（引いた順に、当たりなら1）"""
    weight = np.ones(n_lot); weight[:n_win] = w
    key = np.log(weight)[None, :] + rng.gumbel(size=(rounds, n_lot))
    order = np.argsort(-key, axis=1)
    return (order < n_win).astype(np.int8)


def main():
    out = {}

    # 1) よく混ぜたくじ：順番ごとの当たりの割合（10本1当たり・30本3当たり・100本5当たり）
    fair = {}
    for n_lot, n_win in [(10, 1), (30, 3), (100, 5)]:
        hit = draw(np.random.default_rng(SEED + n_lot), n_lot, n_win, N_ROUND)
        r = hit.mean(0)
        fair[f"{n_lot}本{n_win}当たり"] = {"true_rate": round(n_win / n_lot, 4),
                                       "by_position": [round(float(v), 4) for v in r],
                                       "min": round(float(r.min()), 4), "max": round(float(r.max()), 4)}
    out["fair"] = fair
    hit10 = draw(np.random.default_rng(SEED + 10), 10, 1, N_ROUND)
    pd.DataFrame({"position": np.arange(1, 11), "hit_rate": hit10.mean(0).round(4)}).to_csv(
        RES / "fair_10_by_position.csv", index=False)

    # 2) 前の人の結果が見えるとき：前の人が全員外れたと分かった k 番目の人の当たりの割合
    cond = []
    for k in range(1, 11):
        prev_miss = hit10[:, :k - 1].sum(1) == 0
        cond.append({"position": k, "share_all_prev_miss": round(float(prev_miss.mean()), 4),
                     "hit_if_all_prev_miss_sim": round(float(hit10[prev_miss, k - 1].mean()), 4),
                     "hit_if_all_prev_miss_exact": round(1 / (10 - k + 1), 4),
                     "hit_unconditional": round(float(hit10[:, k - 1].mean()), 4)})
    out["conditional_10"] = cond

    # 3) 当たりの札の取りやすさ w（1=よく混ぜたくじ）を変える（10本1当たり）
    bias = {}
    rows = []
    for w in [0.5, 1.0, 1.5, 2.0, 3.0]:
        r = draw(np.random.default_rng(SEED * 10 + int(w * 10)), 10, 1, N_ROUND, w).mean(0)
        bias[str(w)] = {"first": round(float(r[0]), 4), "last": round(float(r[-1]), 4),
                        "first_half": round(float(r[:5].sum()), 4), "by_position": [round(float(v), 4) for v in r]}
        for k, v in enumerate(r, 1):
            rows.append({"w": w, "position": k, "hit_rate": round(float(v), 4)})
    out["bias_10"] = bias
    pd.DataFrame(rows).to_csv(RES / "bias_by_position.csv", index=False)

    # 4) 少ない回数の記録：よく混ぜたくじを R 回だけ引いた記録で、いちばん当たった順番はどう見えるか
    rec = {}
    for R in [30, 100, 1000]:
        g = np.random.default_rng(SEED * 100 + R)
        best_rate, ge2x, worst0 = [], [], []
        for _ in range(2000):
            c = draw(g, 10, 1, R).sum(0)
            best_rate.append(c.max() / R)
            ge2x.append(c.max() / R >= 0.2)
            worst0.append(c.min() == 0)
        rec[str(R)] = {"best_position_rate_mean": round(float(np.mean(best_rate)), 4),
                       "share_best_ge_20pct": round(float(np.mean(ge2x)), 4),
                       "share_some_position_0": round(float(np.mean(worst0)), 4)}
    out["small_record"] = rec

    # 1回分の30回の記録（data）
    one = draw(rng, 10, 1, 30)
    df = pd.DataFrame(one, columns=[f"pos{k}" for k in range(1, 11)])
    df.insert(0, "round", np.arange(1, 31))
    df.to_csv(DATA / "record_30.csv", index=False)
    cnt = one.sum(0)
    out["one_record_30"] = {"wins_by_position": [int(v) for v in cnt],
                            "best_position": int(cnt.argmax() + 1), "best_wins": int(cnt.max())}

    json.dump(out, open(RES / "a834_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：よく混ぜたくじの順番ごとの当たり
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    pos = np.arange(1, 11)
    r10 = fair["10本1当たり"]["by_position"]
    ax.bar(pos, np.array(r10) * 100, color=BLUE, width=.65, label="10本中1本（10人が引く）")
    ax.axhline(10, color=ORANGE, lw=1, ls="--"); ax.text(10.45, 10.3, "10%", color=ORANGE, fontsize=9)
    for k, v in zip(pos, r10):
        ax.text(k, v * 100 + .25, f"{v*100:.1f}", ha="center", fontsize=8)
    ax.set_xticks(pos); ax.set_xlabel("引く順番（何番目に引くか）"); ax.set_ylabel("当たりの割合（%）")
    ax.set_ylim(0, 13)
    ax.set_title("よく混ぜたくじなら、何番目に引いても当たりは10%（10万回）")
    save(fig, "a834_position.png", SRC)

    # 図2：当たりの札の取りやすさで、順番ごとの当たりはどう変わるか
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    col = {0.5: GREEN, 1.0: GRAY, 1.5: LIGHT, 2.0: BLUE, 3.0: ORANGE}
    lab = {0.5: "当たりが取りにくい（0.5倍）", 1.0: "よく混ぜたくじ（1倍）", 1.5: "取りやすい（1.5倍）",
           2.0: "取りやすい（2倍）", 3.0: "取りやすい（3倍）"}
    for w in [0.5, 1.0, 1.5, 2.0, 3.0]:
        r = np.array(bias[str(w)]["by_position"]) * 100
        ax.plot(pos, r, marker="o", ms=4, color=col[w], lw=2 if w == 1.0 else 1.5, label=lab[w])
    ax.set_xticks(pos); ax.set_xlabel("引く順番（何番目に引くか）"); ax.set_ylabel("当たりの割合（%）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.52, 1.0))
    ax.set_title("当たりの札だけ取りやすい（取りにくい）と、順番で差が出る（10本中1本）")
    save(fig, "a834_bias.png", SRC)

    # 図3：30回だけの記録
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.8), gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    c = ["#eb6834" if k == cnt.argmax() else BLUE for k in range(10)]
    ax.bar(pos, cnt, color=c, width=.65)
    ax.axhline(3, color=GRAY, lw=1, ls="--"); ax.text(8, 3.12, "本当は3回", color=GRAY, fontsize=8.5, ha="center",
                                                    va="bottom")
    ax.set_xticks(pos); ax.set_xlabel("引く順番"); ax.set_ylabel("当たった回数（30回中）")
    ax.set_title("ある30回の記録", fontsize=11)
    ax = axes[1]
    Rs = ["30", "100", "1000"]
    v = [rec[R]["share_best_ge_20pct"] * 100 for R in Rs]
    ax.bar(["30回", "100回", "1,000回"], v, color=[ORANGE, LIGHT, GRAY], width=.6)
    for i, x in enumerate(v):
        ax.text(i, x + 1.5, f"{x:.0f}%", ha="center", fontsize=9)
    ax.set_ylim(0, 105); ax.set_ylabel("当たり20%以上の順番が\nある記録の割合（%）", fontsize=10)
    ax.set_title("記録の回数と、見かけの「当たる順番」", fontsize=11)
    fig.suptitle("よく混ぜたくじでも、少ない回数の記録では「当たる順番」があるように見える", fontsize=12.5, y=1.02)
    fig.tight_layout(w_pad=2.5)
    save(fig, "a834_record.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
