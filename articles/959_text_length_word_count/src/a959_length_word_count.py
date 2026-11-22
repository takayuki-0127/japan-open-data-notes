"""959 文章が長い人ほど、同じ言葉が多く出るのはなぜか？（長さでそろえる）（架空のデータ）

架空のパンの通販「Cベーカリー」に届いた感想文を、作成者が決まり文句を乱数で組み合わせて作る。
短い「注文フォームの感想欄」と長い「メール」の2つの窓口で、「届くのが遅い」と感じた人の本当の割合を作成者が置く。
「遅い」の数え方（延べ回数・語数あたり・出た件の割合・長さの帯をそろえた割合）で、窓口の比べがどう変わるかを数える。
外部の辞書や解析の道具は使わない。
"""
import json
import time
from functools import lru_cache
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 959
SRC = "架空のパンの通販の感想文（作成者が乱数で語を組み合わせて作成、seed 959）"
N_TEXT = 2000   # 窓口ごとの件数
N_REP = 200
TARGET = "遅い"

FIRST = "届くのが遅いです。"                        # 遅いと感じた人が必ず1回書く文
REPEAT = ["思ったより届くのが遅いと感じました。", "次も遅いと困ります。", "やはり遅いのは残念です。"]  # くり返し
OTHER_SENSE = ["遅い時間に受け取りました。", "夜遅い時間でも受け取れて助かりました。"]       # 別の意味の「遅い」
NEUTRAL = ["パンがおいしかったです。", "家族で食べました。", "箱がかわいいです。", "また注文します。",
           "クロワッサンが好きです。", "季節のパンを楽しみにしています。", "冷凍して少しずつ食べています。",
           "友人にも勧めました。", "食パンは厚めに切りました。", "朝ごはんにちょうどよかったです。"]
# 作成者の語のリスト（数える語）。区切りの決まり：左から、このリストのうち一番長い語を取り、リストにない文字は数えない
WORDS = ["遅い", "届く", "感じ", "次", "困り", "残念", "時間", "受け取り", "受け取れ", "夜", "助かり", "パン",
         "食パン", "家族", "食べ", "箱", "注文", "クロワッサン", "好き", "季節", "楽しみ", "冷凍", "友人", "勧め",
         "厚め", "切り", "朝ごはん"]
WSET = set(WORDS)
MAXLEN = max(len(w) for w in WORDS)
CHANNEL = {"フォーム": {"extra_mean": 0.7, "max_sent": 3}, "メール": {"extra_mean": 5.0, "max_sent": 20}}
BASE = {"r": 0.15, "e": 0.03, "p": {"フォーム": 0.20, "メール": 0.20}}


@lru_cache(maxsize=None)
def tokens(text):
    out, i = [], 0
    while i < len(text):
        for L in range(min(MAXLEN, len(text) - i), 0, -1):
            if text[i:i + L] in WSET:
                out.append(text[i:i + L]); i += L
                break
        else:
            i += 1
    return tuple(out)


def make_channel(rng, ch, n, p, r, e, keep_text=False):
    """1件ごとに、文の数・遅いと感じたか・各文を作る。数える語は文ごとに区切る（文をまたぐ語はない）"""
    c = CHANNEL[ch]
    L = np.minimum(1 + rng.poisson(c["extra_mean"], n), c["max_sent"])
    comp = rng.random(n) < p
    rows, texts = [], []
    for i in range(n):
        u = rng.random(3 * L[i] + 1)
        first_at = int(u[0] * L[i]) if comp[i] else -1
        sents, n_first, n_rep, n_other = [], 0, 0, 0
        for j in range(L[i]):
            if j == first_at:
                s = FIRST; n_first += 1
            elif comp[i] and u[1 + 3 * j] < r:
                s = REPEAT[int(u[2 + 3 * j] * len(REPEAT))]; n_rep += 1
            elif u[1 + 3 * j] >= 1 - e:
                s = OTHER_SENSE[int(u[2 + 3 * j] * len(OTHER_SENSE))]; n_other += 1
            else:
                s = NEUTRAL[int(u[3 + 3 * j] * len(NEUTRAL))]
            sents.append(s)
        tk = [t for s in sents for t in tokens(s)]
        rows.append((L[i], int(comp[i]), len(tk), tk.count(TARGET), n_first, n_rep, n_other))
        if keep_text:
            texts.append("".join(sents))
    d = pd.DataFrame(rows, columns=["n_sent", "complaint", "n_words", "n_target", "n_first", "n_repeat", "n_other_sense"])
    d.insert(0, "channel", ch)
    if keep_text:
        d["text"] = texts
    return d


def measures(d):
    short = d[d.n_sent <= 3]
    return {"true_share": d.complaint.mean(), "per_100_texts": 100 * d.n_target.mean(),
            "per_10k_words": 1e4 * d.n_target.sum() / d.n_words.sum(), "present_share": (d.n_target > 0).mean(),
            "present_share_1to3": (short.n_target > 0).mean(), "mean_sent": d.n_sent.mean(), "mean_words": d.n_words.mean(),
            "mean_sent_1to3": short.n_sent.mean()}


MEAS = ["true_share", "per_100_texts", "per_10k_words", "present_share", "present_share_1to3"]
MLAB = {"true_share": "本当の割合（遅いと感じた人）", "per_100_texts": "100件あたりの延べ回数",
        "per_10k_words": "1万語あたりの回数", "present_share": "「遅い」が出た件の割合",
        "present_share_1to3": "1〜3文の件だけで出た割合"}


def run(seed, p, r, e, n=N_TEXT):
    g = np.random.default_rng(seed)
    return {ch: measures(make_channel(g, ch, n, p[ch], r, e)) for ch in CHANNEL}


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    one = pd.concat([make_channel(rng, ch, N_TEXT, BASE["p"][ch], BASE["r"], BASE["e"], keep_text=True)
                     for ch in CHANNEL], ignore_index=True)
    # 文ごとに区切った数と、文章をまるごと区切った数が同じか
    whole = one.text.map(lambda t: tokens(t).count(TARGET))
    check_same = bool((whole == one.n_target).all())
    one.insert(0, "text_id", np.arange(1, len(one) + 1))
    one.to_csv(DATA / "comments.csv", index=False)
    m1 = {ch: {k: round(float(v), 4) for k, v in measures(one[one.channel == ch]).items()} for ch in CHANNEL}

    # 1) 作り直して200回（基本）
    rows = []
    for k in range(N_REP):
        res = run(SEED * 1000 + k, BASE["p"], BASE["r"], BASE["e"])
        for ch, m in res.items():
            rows.append({"rep": k, "channel": ch, **m})
    sim = pd.DataFrame(rows)
    summ = sim.groupby("channel", sort=False)[MEAS + ["mean_sent", "mean_words", "mean_sent_1to3"]].mean()
    ratio = {mm: round(float(summ.loc["メール", mm] / summ.loc["フォーム", mm]), 3) for mm in MEAS}
    summ.round(4).to_csv(RES / "by_channel_200reps.csv")

    # 2) メールの中で、長さの帯ごと（大きめの1回：メール2万件）
    big = make_channel(np.random.default_rng(SEED * 3), "メール", 20000, BASE["p"]["メール"], BASE["r"], BASE["e"])
    big["band"] = pd.cut(big.n_sent, [0, 3, 6, 9, 99], labels=["1〜3文", "4〜6文", "7〜9文", "10文以上"])
    band = big.groupby("band", observed=True).apply(lambda q: pd.Series({
        "n": len(q), "true_share": q.complaint.mean(), "per_100_texts": 100 * q.n_target.mean(),
        "per_10k_words": 1e4 * q.n_target.sum() / q.n_words.sum(), "present_share": (q.n_target > 0).mean(),
        "per_100_complainers": 100 * q[q.complaint == 1].n_target.mean(),
        "present_share_noncomplainers": (q[q.complaint == 0].n_target > 0).mean()}), include_groups=False)
    band.round(4).to_csv(RES / "mail_by_length_band.csv")
    tot = big[["n_first", "n_repeat", "n_other_sense"]].sum()
    parts = {k: round(float(v / tot.sum()), 4) for k, v in tot.items()}
    tot_f = make_channel(np.random.default_rng(SEED * 4), "フォーム", 20000, 0.2, BASE["r"], BASE["e"])[
        ["n_first", "n_repeat", "n_other_sense"]].sum()
    parts_form = {k: round(float(v / tot_f.sum()), 4) for k, v in tot_f.items()}

    # 3) 確かめ：くり返しの強さ r・別の意味の割合 e・メールの本当の割合（0.20 と 0.14）、各50回
    sens = []
    for pm in [0.20, 0.14]:
        for r in [0.0, 0.15, 0.30]:
            for e in [0.0, 0.03, 0.06]:
                acc = {ch: {mm: [] for mm in MEAS} for ch in CHANNEL}
                for k in range(50):
                    res = run(SEED * 9000 + int(pm * 100) * 1000 + int(r * 100) * 10 + int(e * 100) + k * 100000,
                              {"フォーム": 0.20, "メール": pm}, r, e)
                    for ch in CHANNEL:
                        for mm in MEAS:
                            acc[ch][mm].append(res[ch][mm])
                row = {"mail_true": pm, "r_repeat": r, "e_other_sense": e}
                for mm in MEAS:
                    row[f"ratio_{mm}"] = round(float(np.mean(acc["メール"][mm]) / np.mean(acc["フォーム"][mm])), 3)
                sens.append(row)
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity_r_e_true.csv", index=False)

    def rng_of(q, col):
        return [round(float(q[col].min()), 2), round(float(q[col].max()), 2)]
    s20, s14 = sens[sens.mail_true == 0.20], sens[sens.mail_true == 0.14]
    sens_range = {"mail_true_0.20": {mm: rng_of(s20, f"ratio_{mm}") for mm in MEAS[1:]},
                  "mail_true_0.14": {mm: rng_of(s14, f"ratio_{mm}") for mm in MEAS[1:]},
                  "mail_true_0.14_cases_saying_mail_higher": {mm: int((s14[f"ratio_{mm}"] > 1).sum()) for mm in MEAS[1:]},
                  "n_cases_each": int(len(s14))}

    out = {"n_text_per_channel": N_TEXT, "reps": N_REP, "base": BASE, "channels": CHANNEL,
           "check_sentence_vs_whole_text_same": check_same, "one_draw": m1,
           "by_channel_200reps": {ch: {k: round(float(v), 4) for k, v in summ.loc[ch].items()} for ch in CHANNEL},
           "ratio_mail_over_form_200reps": ratio, "mail_by_length_band_20000": band.round(4).reset_index().to_dict("records"),
           "occurrence_parts_mail_20000": parts, "occurrence_parts_form_20000": parts_form,
           "sensitivity": sens.to_dict("records"), "sensitivity_range": sens_range}
    json.dump(out, open(RES / "a959_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda x: int(x) if isinstance(x, np.integer) else float(x))

    # 図1：メールの長さの帯ごと
    b = band.reset_index()
    fig, axes = plt.subplots(1, 3, figsize=(10.6, 3.9))
    for ax, col, lab, c in [(axes[0], "per_100_texts", "100件あたりの「遅い」の延べ回数", ORANGE),
                            (axes[1], "per_10k_words", "1万語あたりの「遅い」の回数", BLUE),
                            (axes[2], "present_share", "「遅い」が出た件の割合（%、点線は置いた本当の20%）", GREEN)]:
        v = b[col] * (100 if col == "present_share" else 1)
        ax.bar(b.band.astype(str), v, color=c)
        for i, x in enumerate(v):
            ax.text(i, x, f"{x:.1f}", ha="center", va="bottom", fontsize=8.5)
        ax.set_title(lab, fontsize=10); ax.tick_params(axis="x", labelsize=8.5); ax.set_ylim(0, v.max() * 1.2)
    axes[2].axhline(BASE["p"]["メール"] * 100, color=GRAY, ls="--", lw=1)
    fig.suptitle("メール2万件を長さで分けると、本当の割合は同じでも数え方で向きが変わる", fontsize=12)
    fig.tight_layout()
    save(fig, "a959_length_band.png", SRC)

    # 図2：窓口の比べ（メール÷フォーム、200回の平均）
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    labs = [MLAB[m] for m in MEAS]
    vals = [ratio[m] for m in MEAS]
    cols = [GRAY, ORANGE, BLUE, GREEN, LIGHT]
    ax.barh(labs[::-1], vals[::-1], color=cols[::-1])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 0.03, i, f"{v:.2f}倍", va="center", fontsize=9)
    ax.axvline(1, color=INK, lw=0.8)
    ax.set_xlabel("メール÷フォーム（200回の平均、1より大きいとメールが多く見える）"); ax.set_xlim(0, max(vals) * 1.2)
    ax.set_title(f"本当の割合はほぼ同じ（{ratio['true_share']:.2f}倍）なのに、数え方で{min(vals):.2f}倍にも{max(vals):.2f}倍にも見える", fontsize=11.5)
    save(fig, "a959_channel_ratio.png", SRC)

    # 図3：確かめ（メールの本当の割合が低い0.14のとき、9通り）
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    x = np.arange(len(s14))
    for mm, c, mk in [("per_100_texts", ORANGE, "o"), ("per_10k_words", BLUE, "s"), ("present_share", GREEN, "^"),
                      ("present_share_1to3", "#5b8db8", "D")]:
        ax.plot(x, s14[f"ratio_{mm}"], marker=mk, color=c, label=MLAB[mm], lw=1)
    ax.axhline(0.7, color=GRAY, ls="--", lw=1); ax.text(8.3, 0.73, "置いた本当の比0.70倍", fontsize=8, color=GRAY, ha="right")
    ax.axhline(1, color=INK, lw=0.6)
    ax.set_xticks(x); ax.set_xticklabels([f"r{r:g}\ne{e:g}" for r, e in zip(s14.r_repeat, s14.e_other_sense)], fontsize=8)
    ax.set_xlabel("r：遅いと感じた人が残りの文でくり返す確率　e：別の意味で「遅い」を書く確率（1文あたり）")
    ax.set_ylabel("メール÷フォーム（50回の平均）")
    ax.set_ylim(0.1, 2.75)
    ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=2)
    ax.set_title("メールの本当の割合が低い（0.14対0.20）とき、どの数え方が向きを当てるか")
    save(fig, "a959_sensitivity.png", SRC, y=-0.07)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=lambda x: int(x) if isinstance(x, np.integer) else float(x)))
    print("run_sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
