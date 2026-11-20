"""806 「参考になった」順に並べると、最初の口コミが上に残り続けるのか？（架空のデータ）

架空の店1軒に、2年間（720日）で口コミが300件届く。口コミごとに「本当の役に立ち度」
（読んだ人が「参考になった」を押す確率）を作成者が置く。毎日、読む人が来て、並んだ順に上から読み、
読んだ口コミに確率どおり「参考になった」を押す。上の位置ほどよく読まれる。
並べ方ごとに、2年後の上位に何が残るか・読んだ人がどれだけ役に立つ口コミを読めたかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 806
SRC = "架空の口コミと読む人（作成者が乱数で作成、seed 806）"
N_REV, DAYS, EARLY = 300, 720, 30          # EARLY：最初に書かれた30件（全体の1割）
REPS = 100
METHODS = ["参考になった数の順", "参考になった率の順", "数の順＋新着枠2つ", "新しい順", "でたらめな順"]


def attention(top=0.6, decay=0.75, page2=0.02, rest=0.0):
    """位置ごとに読まれる確率：1〜10番目は top×decay^(位置-1)、11〜20番目（2ページ目）は page2、21番目より下は rest"""
    a = np.full(N_REV, rest)
    a[:10] = top * decay ** np.arange(10)
    a[10:20] = page2
    return a


def run(rng, method, visitors=50, switch=0.2, decay=0.75, keep_path=False, att_kw=None):
    post = np.sort(rng.integers(0, DAYS, N_REV)); post[0] = 0
    q = rng.beta(2, 8, N_REV)                       # 本当の役に立ち度（平均0.2）
    votes = np.zeros(N_REV); reads = np.zeros(N_REV)
    att = attention(decay=decay) if att_kw is None else attention(**att_kw)
    q_read_sum = 0.0; read_total = 0.0
    early_top5_path = []
    for day in range(DAYS):
        k = int(np.searchsorted(post, day, side="right"))     # この日までに書かれた件数
        idx = np.arange(k)
        if method == "参考になった数の順":
            order = idx[np.lexsort((-idx, -votes[:k]))]          # 同じ数なら新しい方を上
        elif method == "参考になった率の順":
            score = (votes[:k] + 1) / (reads[:k] + 5)            # 読まれた回数で割る（読まれていない口コミは0.2から）
            order = idx[np.lexsort((-idx, -score))]
        elif method == "数の順＋新着枠2つ":
            base = idx[np.lexsort((-idx, -votes[:k]))]
            new = idx[::-1]
            fresh = new[reads[new] < 20][:2]                     # まだ20回未満しか読まれていない新しい口コミ
            rest = base[~np.isin(base, fresh)]
            order = np.concatenate([rest[:3], fresh[:1], rest[3:6], fresh[1:2], rest[6:]]).astype(int)
        elif method == "新しい順":
            order = idx[::-1]
        else:
            order = rng.permutation(idx)
        v = rng.poisson(visitors)
        v_new = rng.binomial(v, switch)                          # 自分で「新しい順」に切り替えて読む人
        for o, vv in [(order, v - v_new), (idx[::-1], v_new)]:
            r = rng.binomial(vv, att[:k])
            votes[o] += rng.binomial(r, q[o])
            reads[o] += r
            q_read_sum += float((r * q[o]).sum()); read_total += float(r.sum())
        if keep_path:
            early_top5_path.append(float((order[:5] < EARLY).mean()))
    final_order = order
    top10_true = set(np.argsort(-q)[:10])
    res = {"top5_early_share": float((final_order[:5] < EARLY).mean()),
           "top10_precision": len(top10_true & set(final_order[:10].tolist())) / 10,
           "top5_q_mean": float(q[final_order[:5]].mean()),
           "q_of_reads": q_read_sum / read_total,
           "share_read_lt10": float((reads < 10).mean()),
           "late_half_in_top10": float((final_order[:10] >= N_REV // 2).mean())}
    return res, post, q, votes, reads, final_order, early_top5_path


def main():
    rng = np.random.default_rng(SEED)
    # 0) 1回分の例（参考になった数の順）
    res, post, q, votes, reads, order, path = run(rng, "参考になった数の順", keep_path=True)
    rank = np.empty(N_REV, int); rank[order] = np.arange(1, N_REV + 1)
    pd.DataFrame({"review_id": np.arange(1, N_REV + 1), "post_day": post, "true_helpful": q, "votes": votes.astype(int),
                  "reads": reads.astype(int), "final_rank": rank}).to_csv(DATA / "example_reviews.csv", index=False,
                                                                           float_format="%.4f")
    one = {**{k: round(v, 3) for k, v in res.items()},
           "early_votes_share": round(float(votes[:EARLY].sum() / votes.sum()), 3),
           "n_votes_ge1000": int((votes >= 1000).sum()), "n_votes_ge1000_in_early": int((votes[:EARLY] >= 1000).sum()),
           "after30_votes_median": float(np.median(votes[EARLY:])), "after30_votes_max": int(votes[EARLY:].max()),
           "top5_post_days": post[order[:5]].tolist(), "top5_true_rank": [int((q > q[i]).sum() + 1) for i in order[:5]]}

    # 1) 並べ方ごと（100回の平均）
    rows = []
    for rep in range(REPS):
        for m in METHODS:
            r, *_ = run(np.random.default_rng(SEED * 1000 + rep), m)   # 同じ口コミ・同じ書かれた日で比べる
            rows.append({"rep": rep, "method": m, **r})
    sim = pd.DataFrame(rows)
    summ = sim.groupby("method", sort=False).mean(numeric_only=True).drop(columns="rep").round(3)
    summ.to_csv(RES / "order_methods.csv")

    # 3) 確かめ：読む人の数と、「新しい順」に切り替えて読む人の割合を変える（数の順、40回ずつ）
    rob = []
    for visitors in [10, 50, 200]:
        for switch in [0.0, 0.2, 0.4]:
            rr = [run(np.random.default_rng(SEED * 17 + rep + visitors * 100 + int(switch * 10)), "参考になった数の順",
                      visitors=visitors, switch=switch)[0] for rep in range(40)]
            d = pd.DataFrame(rr).mean()
            rob.append({"visitors": visitors, "switch_to_newest": switch, "top5_early_share": round(d.top5_early_share, 3),
                        "top10_precision": round(d.top10_precision, 3), "q_of_reads": round(d.q_of_reads, 3)})
    rob = pd.DataFrame(rob)
    rob.to_csv(RES / "robustness_votes_order.csv", index=False)

    # 4) 確かめ（レビューで追加）：位置ごとに読まれる確率の置き方を変える（数の順と率の順、40回ずつ）
    ATT = {"基本（1番目0.6・下がり方0.75・2ページ目0.02）": dict(top=0.6, decay=0.75, page2=0.02, rest=0.0),
           "ゆるやか（1番目0.6・0.9・2ページ目0.1・3ページ目より下0.02）": dict(top=0.6, decay=0.9, page2=0.1, rest=0.02),
           "かなり平ら（1番目0.3・0.97・2ページ目0.2・3ページ目より下0.1）": dict(top=0.3, decay=0.97, page2=0.2, rest=0.1),
           "位置で差がない（どの位置も0.1）": dict(top=0.1, decay=1.0, page2=0.1, rest=0.1)}
    rob_att = []
    for j, (name, kw) in enumerate(ATT.items()):
        for m in ["参考になった数の順", "参考になった率の順"]:
            rr = [run(np.random.default_rng(SEED * 31 + rep + j * 1000), m, att_kw=kw)[0] for rep in range(40)]
            d = pd.DataFrame(rr).mean()
            rob_att.append({"attention": name, "method": m, "top5_early_share": round(d.top5_early_share, 3),
                            "top10_precision": round(d.top10_precision, 3), "q_of_reads": round(d.q_of_reads, 3),
                            "late_half_in_top10": round(d.late_half_in_top10, 3)})
    rob_att = pd.DataFrame(rob_att)
    rob_att.to_csv(RES / "robustness_attention.csv", index=False)

    out = {"setting": {"reviews": N_REV, "days": DAYS, "early": EARLY, "visitors_per_day": 50,
                       "switch_to_newest": 0.2, "attention_top": 0.6, "attention_decay": 0.75, "true_helpful": "Beta(2,8)", "reps": REPS},
           "order_methods": summ.reset_index().to_dict("records"),
           "robustness_votes_order": rob.to_dict("records"), "robustness_attention": rob_att.to_dict("records"),
           "one_run_votes_order": one}
    json.dump(out, open(RES / "a806_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：書かれた順番と、2年後の「参考になった」の数（1回分）
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    sc = ax.scatter(np.arange(1, N_REV + 1), votes, c=q, cmap="Blues", s=14, edgecolor=GRAY, lw=0.3, vmin=0, vmax=0.6)
    ax.scatter(order[:5] + 1, votes[order[:5]], facecolor="none", edgecolor=ORANGE, s=70, lw=1.4,
               label="2年後の上位5件")
    ax.axvline(EARLY + 0.5, color=GRAY, lw=0.8, ls="--"); ax.text(EARLY + 3, votes.max() * 0.6, "最初の30件", color=GRAY, fontsize=9)
    ax.set_yscale("symlog", linthresh=10); ax.set_ylim(-0.5, votes.max() * 2)
    ax.set_xlabel("書かれた順番（1＝いちばん古い）"); ax.set_ylabel("「参考になった」の数（2年後、対数に近い目盛り）")
    cb = fig.colorbar(sc, ax=ax, pad=0.01); cb.set_label("本当の役に立ち度（濃いほど高い）", fontsize=9)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    ax.set_title("「参考になった」の数は、早く書かれた口コミに集まる（1回分）")
    save(fig, "a806_votes_by_order.png", SRC)

    # 図2：並べ方ごとの比較
    s = summ.reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.8), sharey=True)
    col = [ORANGE, BLUE, LIGHT, GRAY, GRAY]
    for ax, key, lab in [(axes[0], "top5_early_share", "上位5件のうち、最初の30件だった割合（%）"),
                         (axes[1], "q_of_reads", "読まれた口コミの役に立ち度の平均（%）")]:
        ax.barh(s.method[::-1], s[key][::-1] * 100, color=col[::-1])
        for i, v in enumerate(s[key][::-1] * 100):
            ax.text(v + 1, i, f"{v:.0f}%", va="center", fontsize=9)
        ax.set_xlabel(lab, fontsize=9); ax.set_xlim(0, 100 if key == "top5_early_share" else 50)
    fig.suptitle("数の順は古い口コミを上に残す。率の順は、読む人によく役に立つ口コミを出す（100回の平均）", fontsize=11.5)
    save(fig, "a806_methods.png", SRC)

    # 図3：確かめ（読む人の数・新しい順に切り替える人の割合を変えても）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    w = 0.26
    for j, (sw, c) in enumerate([(0.0, INK), (0.2, ORANGE), (0.4, LIGHT)]):
        d = rob[rob.switch_to_newest == sw]
        x = np.arange(3) + (j - 1) * w
        ax.bar(x, d.top5_early_share * 100, width=w, color=c, label=f"切り替える人 {sw*100:.0f}%")
        for xi, v in zip(x, d.top5_early_share * 100):
            ax.text(xi, v + 1, f"{v:.0f}", ha="center", fontsize=8)
    ax.set_xticks(np.arange(3)); ax.set_xticklabels(["1日10人", "1日50人", "1日200人"])
    ax.set_ylim(0, 130); ax.set_yticks(range(0, 101, 20)); ax.set_ylabel("上位5件のうち、最初の30件の割合（%）")
    ax.axhline(100 * EARLY / N_REV, color=GRAY, ls="--", lw=0.8)
    ax.text(-0.5, 100 * EARLY / N_REV + 2, "でたらめなら10%", color=GRAY, fontsize=8.5, ha="left")
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.0))
    ax.set_title("読む人の数や、新しい順に切り替えて読む人の割合を変えても\n上位5件は最初の30件のまま（参考になった数の順・40回の平均）")
    save(fig, "a806_robustness.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
