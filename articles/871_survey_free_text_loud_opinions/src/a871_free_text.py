"""871 自由記述の多い意見は、全体の多い意見なのか？（架空のデータ）

架空の店の来店客アンケート3,000人。8つの困りごとについて、それぞれ持っているかどうかを作成者が置く（本当の割合）。
自由記述に書くかどうかは、困りごとごとの「書きやすさ」と、人ごとの「よく書く人かどうか」で決まると置く。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 871
SRC = "架空の店の来店客アンケート（作成者が乱数で作成、seed 871）"
TOPIC = ["レジの待ち時間", "品ぞろえ", "駐車場の狭さ", "営業時間", "ポイントの仕組み", "店内の案内表示", "店内の清潔さ", "店員の対応"]
TRUE = np.array([0.30, 0.26, 0.22, 0.17, 0.13, 0.11, 0.07, 0.05])   # その困りごとを持っている人の割合
EASE = np.array([1.0, 0.9, 0.7, 0.6, 0.8, 0.5, 1.8, 4.0])           # 書きやすさ（感情の強さ）。1が基準
BASE_W, HEAVY_SHARE, HEAVY_X = 0.10, 0.15, 3.0                       # 基準の書く確率、よく書く人の割合と倍率
N_RESP, REPS, N_CLOSED = 3000, 500, 200


def survey(rng, n=N_RESP, a=1.0):
    hold = rng.random((n, len(TOPIC))) < TRUE
    heavy = rng.random(n) < HEAVY_SHARE
    pw = np.clip(BASE_W * EASE[None, :] ** a * np.where(heavy, HEAVY_X, 1.0)[:, None], 0, 0.95)
    write = hold & (rng.random((n, len(TOPIC))) < pw)
    return hold, heavy, write


def rank_desc(x):
    return (-x).argsort().argsort() + 1


def main():
    rng = np.random.default_rng(SEED)
    true_rank = rank_desc(TRUE)

    # 1回分（data/respondents.csv）
    hold, heavy, write = survey(rng)
    df = pd.DataFrame({"resp_id": np.arange(1, N_RESP + 1), "heavy_writer": heavy.astype(int)})
    for j in range(len(TOPIC)):
        df[f"has_{j+1}"] = hold[:, j].astype(int)
    for j in range(len(TOPIC)):
        df[f"wrote_{j+1}"] = write[:, j].astype(int)
    df.to_csv(DATA / "respondents.csv", index=False)
    pd.DataFrame({"topic_no": np.arange(1, 9), "topic": TOPIC, "true_share": TRUE, "ease": EASE}).to_csv(
        DATA / "topics.csv", index=False)
    cnt = write.sum(0)
    one = {"n_wrote_any": int(write.any(1).sum()), "n_comments": int(cnt.sum()),
           "heavy_share_of_comments": round(float(write[heavy].sum() / cnt.sum()), 4),
           "topics": [{"topic": t, "true_share": float(TRUE[j]), "held_share": round(float(hold[:, j].mean()), 4),
                       "comments": int(cnt[j]), "share_of_respondents": round(float(cnt[j] / N_RESP), 4),
                       "share_of_comments": round(float(cnt[j] / cnt.sum()), 4), "free_rank": int(rank_desc(cnt.astype(float) + 1e-9 * np.arange(8)[::-1])[j])}
                      for j, t in enumerate(TOPIC)]}

    # 2) 500回：自由記述3,000人 と 選択肢で200人に聞いた場合
    rec, rk = [], []
    for r in range(REPS):
        g = np.random.default_rng(SEED * 1000 + r)
        h, hv, w = survey(g)
        c = w.sum(0).astype(float)
        sub = g.choice(N_RESP, N_CLOSED, replace=False)
        cl = h[sub].mean(0)   # 選択肢で全部聞く（持っている人は必ず選ぶと置く）
        fr = rank_desc(c + g.random(8) * 1e-6); cr = rank_desc(cl + g.random(8) * 1e-6)
        rec.append({"rep": r, "spearman_free": spearmanr(c, TRUE)[0], "spearman_closed200": spearmanr(cl, TRUE)[0],
                    "top1_free": int(fr[0] == 1), "top1_closed200": int(cr[0] == 1),
                    "top3_overlap_free": len(set(np.where(fr <= 3)[0]) & {0, 1, 2}),
                    "top3_overlap_closed200": len(set(np.where(cr <= 3)[0]) & {0, 1, 2}),
                    "staff_rank_free": int(fr[7]), "staff_share_of_comments": c[7] / c.sum(),
                    "heavy_share_of_comments": w[hv].sum() / c.sum(), "comments": c.sum()})
        for j in range(8):
            rk.append({"rep": r, "topic": TOPIC[j], "free_rank": int(fr[j]), "closed_rank": int(cr[j]),
                       "share_of_resp_free": c[j] / N_RESP, "share_of_comments": c[j] / c.sum(), "closed": cl[j]})
    sim, rk = pd.DataFrame(rec), pd.DataFrame(rk)
    by_topic = rk.groupby("topic", sort=False).agg(
        free_rank_mean=("free_rank", "mean"), free_rank1=("free_rank", lambda x: (x == 1).mean()),
        closed_rank_mean=("closed_rank", "mean"), share_of_resp_free=("share_of_resp_free", "mean"),
        share_of_comments=("share_of_comments", "mean"), closed200=("closed", "mean")).round(4)
    by_topic.insert(0, "true_share", TRUE); by_topic.insert(1, "true_rank", true_rank)
    by_topic.to_csv(RES / "by_topic.csv")
    summ = sim.drop(columns="rep").mean().round(4).to_dict()
    summ["spearman_free_p05"] = round(float(sim.spearman_free.quantile(.05)), 4)
    summ["spearman_free_p95"] = round(float(sim.spearman_free.quantile(.95)), 4)
    summ["spearman_closed200_p05"] = round(float(sim.spearman_closed200.quantile(.05)), 4)
    summ["spearman_closed200_p95"] = round(float(sim.spearman_closed200.quantile(.95)), 4)
    summ["staff_rank_free_le3"] = round(float((sim.staff_rank_free <= 3).mean()), 4)

    # 3) 確かめ：書きやすさの差の強さ a と、回答者の数
    sens = []
    for a in [0.0, 0.5, 1.0, 1.5]:
        for n in [300, 1000, 3000]:
            sp, t1, st = [], [], []
            for r in range(300):
                g = np.random.default_rng(SEED * 77 + r + int(a * 10) * 1000 + n * 100)
                h, hv, w = survey(g, n, a)
                c = w.sum(0).astype(float)
                fr = rank_desc(c + g.random(8) * 1e-6)
                sp.append(spearmanr(c, TRUE)[0] if c.std() > 0 else np.nan); t1.append(fr[0] == 1); st.append(fr[7])
            sens.append({"a": a, "n_resp": n, "spearman_free": round(float(np.nanmean(sp)), 3),
                         "top1_free": round(float(np.mean(t1)), 3), "staff_rank_mean": round(float(np.mean(st)), 2)})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity.csv", index=False)
    # よく書く人の割合・倍率を変えても（a=1、3,000人）
    sens2 = []
    for hs, hx in [(0.0, 1.0), (0.15, 3.0), (0.30, 5.0)]:
        sp, hc = [], []
        for r in range(300):
            g = np.random.default_rng(SEED * 99 + r + int(hs * 100) * 1000)
            n = N_RESP
            hold_ = g.random((n, 8)) < TRUE
            hv = g.random(n) < hs
            pw = np.clip(BASE_W * EASE[None, :] * np.where(hv, hx, 1.0)[:, None], 0, 0.95)
            w = hold_ & (g.random((n, 8)) < pw)
            c = w.sum(0).astype(float)
            sp.append(spearmanr(c, TRUE)[0]); hc.append(w[hv].sum() / c.sum())
        sens2.append({"heavy_share": hs, "heavy_x": hx, "spearman_free": round(float(np.mean(sp)), 3),
                      "heavy_share_of_comments": round(float(np.mean(hc)), 3)})
    sens2 = pd.DataFrame(sens2)
    sens2.to_csv(RES / "sensitivity_heavy_writers.csv", index=False)

    out = {"settings": {"base_write": BASE_W, "heavy_share": HEAVY_SHARE, "heavy_x": HEAVY_X, "n_resp": N_RESP,
                        "n_closed": N_CLOSED, "reps": REPS},
           "summary_500reps": summ, "by_topic": by_topic.reset_index().to_dict("records"),
           "sensitivity_ease": sens.to_dict("records"), "sensitivity_heavy": sens2.to_dict("records"), "one_draw": one}
    json.dump(out, open(RES / "a871_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：本当の割合と、自由記述の中の割合
    bt = by_topic.reset_index()
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    y = np.arange(8)
    ax.barh(y[::-1] + 0.2, bt.true_share * 100, height=0.38, color=GRAY, label="その困りごとを持っている人の割合（本当）")
    ax.barh(y[::-1] - 0.2, bt.share_of_comments * 100, height=0.38, color=ORANGE, label="自由記述の件数の中の割合")
    for yy, v in zip(y[::-1] + 0.2, bt.true_share * 100):
        ax.text(v + 0.4, yy, f"{v:.0f}%", va="center", fontsize=8.5)
    for yy, v in zip(y[::-1] - 0.2, bt.share_of_comments * 100):
        ax.text(v + 0.4, yy, f"{v:.0f}%", va="center", fontsize=8.5, color=ORANGE)
    ax.set_yticks(y[::-1]); ax.set_yticklabels(bt.topic)
    ax.set_xlabel("%（自由記述は500回の平均）"); ax.set_xlim(0, 36)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("本当はいちばん少ない「店員の対応」が、自由記述では3番目に多い")
    save(fig, "a871_share.png", SRC)

    # 図2：順位の当たり（自由記述3,000人 vs 選択肢200人）
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    bins = np.linspace(-0.2, 1.0, 25)
    ax.hist(sim.spearman_free, bins=bins, color=ORANGE, alpha=.7, label="自由記述の件数（3,000人）")
    ax.hist(sim.spearman_closed200, bins=bins, color=BLUE, alpha=.6, label="選択肢で聞いた割合（200人）")
    ax.set_xlabel("本当の順位との順位相関（1なら順位が完全に一致）"); ax.set_ylabel("回数（500回のうち）")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("200人に選択肢で聞くほうが、3,000人の自由記述より順位が当たる")
    save(fig, "a871_rank.png", SRC, y=-0.07)

    # 図3：確かめ（書きやすさの差の強さ）
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    for n, col in [(300, LIGHT), (1000, GRAY), (3000, ORANGE)]:
        d = sens[sens.n_resp == n]
        ax.plot(d.a, d.spearman_free, marker="o", color=col, label=f"回答者{n:,}人")
    ax.set_xticks([0, 0.5, 1, 1.5])
    ax.set_xticklabels(["0（差なし）", "0.5", "1（基本）", "1.5"])
    ax.set_xlabel("書きやすさの差の強さ（書きやすさの倍率を何乗するか）")
    ax.set_ylabel("本当の順位との順位相関"); ax.set_ylim(0, 1.05)
    ax.legend(frameon=False, fontsize=9, loc="lower left")
    ax.set_title("書きやすさに差がなければ、自由記述の順位もほぼ当たる")
    save(fig, "a871_ease.png", SRC, y=-0.07)
    print(json.dumps({"summary": summ}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
