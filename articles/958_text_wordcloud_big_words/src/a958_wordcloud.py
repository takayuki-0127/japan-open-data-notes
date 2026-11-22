"""958 ワードクラウドの大きい文字は、本当に多い意見なのか？（架空のデータ）

架空の喫茶店「B珈琲店」の感想文を、作成者が決まり文句と語を乱数で組み合わせて作る。
意見（困りごと・ほめ言葉）ごとに、持っている人の本当の割合と、言い方（言いかえ）の数を作成者が置く。
語を数えてワードクラウド（回数が多い語ほど大きく書く図）を作り、文字の大きさ・面積が本当の意見の多さと
どれだけ合うかを数える。外部の辞書や解析の道具は使わない。
"""
import json
import time
from collections import Counter
from functools import lru_cache
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 958
SRC = "架空の喫茶店の感想文（作成者が乱数で語を組み合わせて作成、seed 958）"
N_TEXT = 1000
N_REP = 200
N_CLOUD = 25  # ワードクラウドに載せる語の数

# 意見：本当の割合（その意見を持つ人の割合）と、言い方（文, 数える語, 選ばれる重み）
OPINIONS = {
    "待ち時間が長い": (0.26, [("待ち時間が長かったです。", "待ち時間", 0.30), ("出てくるのが遅いです。", "遅い", 0.25),
                              ("かなり待たされました。", "待たされ", 0.20), ("レジに行列ができていました。", "行列", 0.15),
                              ("会計に時間がかかりました。", "時間", 0.10)]),
    "駐車場が狭い": (0.18, [("駐車場が狭いです。", "駐車場", 1.0)]),
    "席が少ない": (0.16, [("席が少ないです。", "席", 0.6), ("いつも満席です。", "満席", 0.4)]),
    "メニューが分かりにくい": (0.12, [("メニューが分かりにくいです。", "メニュー", 1.0)]),
    "店員の対応が良い": (0.10, [("店員さんが丁寧でした。", "店員", 0.4), ("接客が良かったです。", "接客", 0.3),
                                ("笑顔で迎えてくれました。", "笑顔", 0.3)]),
    "コーヒーがおいしい": (0.08, [("コーヒーがおいしかったです。", "コーヒー", 1.0)]),
    "音楽が大きい": (0.06, [("音楽が大きいです。", "音楽", 0.6), ("BGMが気になりました。", "BGM", 0.4)]),
    "コンセントがほしい": (0.04, [("コンセントがある席がほしいです。", "コンセント", 1.0)]),
}
OPENERS = ["今日は友人と店を利用しました。", "週末に家族で来店しました。", "仕事の帰りに一人で寄りました。",
           "初めて店に入りました。"]
CLOSERS = ["また来たいです。", "ごちそうさまでした。"]
GENERIC = ["店", "利用", "今日", "友人", "一人", "家族", "週末", "来店", "仕事", "帰り", "初めて"]  # 意見ではない語
WORDS = sorted({v[1] for o in OPINIONS.values() for v in o[1]} | set(GENERIC))
WORD_OP = {v[1]: k for k, o in OPINIONS.items() for v in o[1]}
MAXLEN = max(len(w) for w in WORDS)
OP_COL = dict(zip(OPINIONS, ["#eb6834", "#2a78d6", "#3aa07a", "#8a5cc2", "#c9a227", "#5b8db8", "#d16fa3", "#8c564b"]))


@lru_cache(maxsize=None)
def tokens(text):
    """区切りの決まり：左から、作成者の語のリストのうち一番長い語を取る。リストにない文字は数えない"""
    out, i = [], 0
    while i < len(text):
        for L in range(min(MAXLEN, len(text) - i), 0, -1):
            if text[i:i + L] in WORDS:
                out.append(text[i:i + L]); i += L
                break
        else:
            i += 1
    return tuple(out)


def make_texts(rng, n=N_TEXT, n_var_wait=None):
    ops = list(OPINIONS)
    p = np.array([OPINIONS[k][0] for k in ops])
    var = {k: OPINIONS[k][1] for k in ops}
    if n_var_wait is not None:  # 「待ち時間が長い」の言い方の数を変える確かめ
        v = OPINIONS["待ち時間が長い"][1][:n_var_wait]
        w = np.array([x[2] for x in v]); w = w / w.sum()
        var["待ち時間が長い"] = [(a, b, c) for (a, b, _), c in zip(v, w)]
    # 1人あたりの意見の数：75%が1つ、25%が2つ。意見は置いた重みで重ならずに選ぶ。
    # 本当の割合は、こうして持たせた人の割合を文章ごとに数えたもの（held）
    cum = {k: np.cumsum([x[2] for x in v]) for k, v in var.items()}
    # 意見は人ごとに別々に持つ（意見 k を持つ確率が本当の割合 p_k）。意見のない人は決まり文句だけを書く
    has = rng.random((n, len(ops))) < p
    u = rng.random((n, 4 + len(ops)))
    texts, held = [], []
    for i in range(n):
        parts, hs = [], []
        if u[i, 0] < 0.5:
            parts.append(OPENERS[int(u[i, 1] * len(OPENERS))])
        for t in np.flatnonzero(has[i]):
            vs = var[ops[t]]
            cw = cum[ops[t]]
            idx = min(int(np.searchsorted(cw, u[i, 4 + t] * cw[-1], side="right")), len(vs) - 1)
            parts.append(vs[idx][0]); hs.append(ops[t])
        if u[i, 2] < 0.3:
            parts.append(CLOSERS[int(u[i, 3] * len(CLOSERS))])
        texts.append("".join(parts) if parts else "特にありません。"); held.append("・".join(hs))
    return texts, held


def cloud(counts, n=N_CLOUD, scale="linear", drop_generic=False):
    """上位 n 語。文字の高さ：回数に比例（linear）か、回数の平方根に比例（sqrt）。面積は 高さ²×文字数（半角は0.6文字）"""
    items = [(w, c) for w, c in sorted(counts.items(), key=lambda x: (-x[1], x[0]))
             if not (drop_generic and w in GENERIC)][:n]
    cmax = items[0][1]
    rows = []
    for w, c in items:
        h = c / cmax if scale == "linear" else np.sqrt(c / cmax)
        width = sum(0.6 if ord(ch) < 128 else 1.0 for ch in w)
        rows.append({"word": w, "count": int(c), "height": h, "chars": width, "area": h * h * width,
                     "opinion": WORD_OP.get(w, "（意見ではない語）")})
    d = pd.DataFrame(rows)
    d["area_share"] = d.area / d.area.sum()
    return d


def by_opinion(d, held_share):
    g = d.groupby("opinion").agg(area_share=("area_share", "sum"), max_height=("height", "max"),
                                 count_sum=("count", "sum"))
    g = g.reindex(list(OPINIONS) + ["（意見ではない語）"]).fillna(0)
    g["true_share"] = [held_share.get(k, np.nan) for k in g.index]
    return g


def spearman(a, b):
    ra, rb = pd.Series(a).rank(), pd.Series(b).rank()
    return float(np.corrcoef(ra, rb)[0, 1])


def tally(texts, held):
    c = Counter()
    for t in texts:
        c.update(tokens(t))
    hc = Counter()
    for h in held:
        hc.update(h.split("・"))
    return c, {k: hc[k] / len(texts) for k in OPINIONS}


def evaluate(texts, held, scale="linear", drop_generic=True, pre=None):
    c, share = pre if pre is not None else tally(texts, held)
    d = cloud(c, scale=scale, drop_generic=drop_generic)
    g = by_opinion(d, share)
    ops = list(OPINIONS)
    top_word = d.iloc[0].word
    big_area = d.sort_values(["area", "word"], ascending=[False, True]).iloc[0].word
    # 意見ごとに、その意見の語でいちばん大きい語の高さ／その意見の語の面積の合計
    return {"top_word": top_word, "top_word_opinion": WORD_OP.get(top_word, "（意見ではない語）"),
            "biggest_area_word": big_area, "biggest_area_opinion": WORD_OP.get(big_area, "（意見ではない語）"),
            "rho_height": spearman(g.loc[ops, "true_share"], g.loc[ops, "max_height"]),
            "rho_area": spearman(g.loc[ops, "true_share"], g.loc[ops, "area_share"]),
            "rho_grouped": spearman(g.loc[ops, "true_share"], g.loc[ops, "count_sum"]),
            "wait_area_share": float(g.loc["待ち時間が長い", "area_share"]),
            "wait_true": share["待ち時間が長い"],
            "parking_area_share": float(g.loc["駐車場が狭い", "area_share"]),
            "parking_true": share["駐車場が狭い"],
            "wait_max_height": float(g.loc["待ち時間が長い", "max_height"]),
            "parking_max_height": float(g.loc["駐車場が狭い", "max_height"]),
            "generic_area_share": float(g.loc["（意見ではない語）", "area_share"]),
            "wait_rank_word": int(d.reset_index().query("opinion == '待ち時間が長い'").index.min() + 1)}, d, g


def draw_cloud(ax, d, title):
    """棚に並べる簡単な置き方（大きい語から左から右へ、行の幅を超えたら次の行）。座標はポイント"""
    fig = ax.figure
    bb = ax.get_window_extent()
    W = bb.width / fig.dpi * 72
    x, y, rowh, first = 0.0, 0.0, 0.0, True
    places = []
    for _, r in d.iterrows():
        fs = 7 + 38 * r.height
        w = fs * r.chars + 10
        if x + w > W and not first:
            y -= rowh * 1.25; x, rowh = 0.0, 0.0
        places.append((x, y, fs, r))
        x += w; rowh = max(rowh, fs); first = False
    for x, yy, fs, r in places:
        ax.text(x, yy, r.word, fontsize=fs, color=OP_COL.get(r.opinion, GRAY), va="top", ha="left")
    ax.set_xlim(0, W); ax.set_ylim(y - rowh * 1.3, 4); ax.axis("off")
    ax.set_title(title, fontsize=11)


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    texts, held = make_texts(rng)
    pd.DataFrame({"text_id": np.arange(1, len(texts) + 1), "opinions": held, "text": texts}).to_csv(
        DATA / "comments.csv", index=False)

    # 1) 1回分（1,000件）
    one = {}
    tables = {}
    for scale in ["linear", "sqrt"]:
        for dg in [False, True]:
            ev, d, g = evaluate(texts, held, scale, dg)
            key = f"{scale}_{'drop' if dg else 'keep'}_generic"
            one[key] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in ev.items()}
            tables[key] = (d, g)
    d0, g0 = tables["linear_drop_generic"]
    d0.round(4).to_csv(RES / "cloud_one_draw_linear.csv", index=False)
    g0.round(4).to_csv(RES / "by_opinion_one_draw_linear.csv")
    dk, gk = tables["linear_keep_generic"]
    dk.round(4).to_csv(RES / "cloud_one_draw_linear_keep_generic.csv", index=False)
    wc = Counter()
    for t in texts:
        wc.update(tokens(t))

    # 2) 作り直して200回
    rows = []
    for r in range(N_REP):
        g = np.random.default_rng(SEED * 1000 + r)
        tx, hd = make_texts(g)
        pre = tally(tx, hd)
        for scale in ["linear", "sqrt"]:
            for dg in [False, True]:
                ev, _, _ = evaluate(tx, hd, scale, dg, pre)
                ev.update({"rep": r, "scale": scale, "generic": "除く" if dg else "残す"})
                rows.append(ev)
    sim = pd.DataFrame(rows)
    summ = sim.groupby(["scale", "generic"]).agg(
        top_is_wait=("top_word_opinion", lambda s: float((s == "待ち時間が長い").mean())),
        top_is_parking=("top_word_opinion", lambda s: float((s == "駐車場が狭い").mean())),
        top_is_generic=("top_word_opinion", lambda s: float((s == "（意見ではない語）").mean())),
        area_is_wait=("biggest_area_opinion", lambda s: float((s == "待ち時間が長い").mean())),
        rho_height=("rho_height", "mean"), rho_area=("rho_area", "mean"), rho_grouped=("rho_grouped", "mean"),
        wait_area_share=("wait_area_share", "mean"), wait_true=("wait_true", "mean"),
        parking_area_share=("parking_area_share", "mean"), parking_true=("parking_true", "mean"),
        generic_area_share=("generic_area_share", "mean"),
        wait_rank_word_median=("wait_rank_word", "median")).round(3)
    summ.to_csv(RES / "summary_200reps.csv")
    top_words = sim[(sim.scale == "linear") & (sim.generic == "除く")].top_word.value_counts()
    area_words = sim[(sim.scale == "linear") & (sim.generic == "除く")].biggest_area_word.value_counts()

    # 3) 確かめ：「待ち時間が長い」の言い方の数（1・3・5）と件数（100・1,000件）、各100回、意見ではない語は除く
    sens = []
    for nv in [1, 3, 5]:
        for n in [100, 1000]:
            rr = []
            for r in range(100):
                g = np.random.default_rng(SEED * 5000 + nv * 1000 + n + r)
                tx, hd = make_texts(g, n, nv)
                pre = tally(tx, hd)
                for scale in ["linear", "sqrt"]:
                    ev, _, _ = evaluate(tx, hd, scale, True, pre)
                    ev["scale"] = scale; rr.append(ev)
            rr = pd.DataFrame(rr)
            for scale in ["linear", "sqrt"]:
                q = rr[rr.scale == scale]
                sens.append({"n_var_wait": nv, "n_text": n, "scale": scale,
                             "top_is_wait": round(float((q.top_word_opinion == "待ち時間が長い").mean()), 2),
                             "area_is_wait": round(float((q.biggest_area_opinion == "待ち時間が長い").mean()), 2),
                             "wait_area_share": round(float(q.wait_area_share.mean()), 3),
                             "wait_true": round(float(q.wait_true.mean()), 3),
                             "rho_area": round(float(q.rho_area.mean()), 3),
                             "rho_grouped": round(float(q.rho_grouped.mean()), 3)})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity_variants_n.csv", index=False)

    out = {"n_text": N_TEXT, "reps": N_REP, "n_cloud_words": N_CLOUD,
           "opinion_true_share_set": {k: v[0] for k, v in OPINIONS.items()},
           "one_draw": one, "one_draw_word_counts_top": sorted(wc.items(), key=lambda x: (-x[1], x[0]))[:12],
           "summary_200reps": summ.reset_index().to_dict("records"),
           "top_word_200reps_linear_drop": {k: int(v) for k, v in top_words.items()},
           "biggest_area_word_200reps_linear_drop": {k: int(v) for k, v in area_words.items()},
           "sensitivity": sens.to_dict("records")}
    json.dump(out, open(RES / "a958_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda x: int(x) if isinstance(x, np.integer) else float(x))

    # 図1：1回分のワードクラウド（意見ではない語を残す／除く）
    fig, axes = plt.subplots(2, 1, figsize=(8.6, 5.6))
    draw_cloud(axes[0], dk, "そのまま（意見ではない語も残す）")
    draw_cloud(axes[1], d0, "意見ではない語（店・利用・今日など）を除く")
    hs = [Patch(color=OP_COL[k], label=f"{k}（置いた割合{v[0]*100:.0f}%）") for k, v in OPINIONS.items()]
    hs.append(Patch(color=GRAY, label="意見ではない語"))
    fig.legend(handles=hs, loc="lower center", ncol=3, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle("感想1,000件のワードクラウド：文字の高さは回数に比例（色は意見）", fontsize=12)
    save(fig, "a958_cloud.png", SRC, y=-0.08)

    # 図2：意見ごとの本当の割合と、クラウドの面積の割合（1回分、意見ではない語を除く）
    ops = list(OPINIONS)
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    yy = np.arange(len(ops))
    tot = g0.loc[ops, "true_share"].sum()
    ax.barh(yy + 0.2, g0.loc[ops, "true_share"] / tot * 100, height=0.4, color=GRAY, label="本当の割合（意見の合計を100%にそろえた）")
    ax.barh(yy - 0.2, g0.loc[ops, "area_share"] * 100, height=0.4, color=ORANGE, label="クラウドの面積の割合")
    for i, k in enumerate(ops):
        ax.text(g0.loc[k, "true_share"] / tot * 100 + 0.4, i + 0.2, f"{g0.loc[k, 'true_share'] / tot * 100:.1f}%", va="center", fontsize=8)
        ax.text(g0.loc[k, "area_share"] * 100 + 0.4, i - 0.2, f"{g0.loc[k, 'area_share'] * 100:.1f}%", va="center", fontsize=8)
    ax.set_yticks(yy); ax.set_yticklabels(ops, fontsize=9); ax.invert_yaxis()
    ax.set_xlabel("%（1回分の1,000件、文字の高さは回数に比例）"); ax.set_xlim(0, 45)
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("いちばん多い意見は、言い方が分かれてクラウドでは小さく見える")
    save(fig, "a958_area_vs_true.png", SRC)

    # 図3：確かめ（言い方の数）
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    for scale, col, lab in [("linear", ORANGE, "高さが回数に比例"), ("sqrt", BLUE, "高さが回数の平方根に比例")]:
        for n, ls, mk in [(100, "--", "o"), (1000, "-", "s")]:
            d = sens[(sens.scale == scale) & (sens.n_text == n)]
            ax.plot(d.n_var_wait, d.wait_area_share * 100, ls=ls, marker=mk, color=col, label=f"{lab}（{n:,}件）")
    ax.set_xticks([1, 3, 5]); ax.set_xlabel("「待ち時間が長い」の言い方の数")
    ax.set_ylabel("クラウドの面積に占める割合（%、100回の平均）"); ax.set_ylim(0, 62)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.set_title("言い方が分かれるほど、本当は26%の意見の面積が小さくなる")
    save(fig, "a958_sensitivity.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1, default=lambda x: int(x) if isinstance(x, np.integer) else float(x)))
    print("run_sec", round(time.time() - t0, 1))


if __name__ == "__main__":
    main()
