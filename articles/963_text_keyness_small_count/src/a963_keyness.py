"""963 少ない件数の言葉の「特徴的な度合い」は、なぜ極端に出るのか？（架空のデータ）

架空の2店（A店・B店）の感想の短文。語は作成者が書いた語の一覧と、頭の語×味×品物を組み合わせた架空の品名。
語ごとの本当の出やすさ（全体の出方）を作成者が置き、本当にA店で多い語・B店で多い語を少しだけ置く。
「A店に特徴的な語」の上位10語を、いくつかの数え方で選び、本当にA店で多い語をどれだけ当てるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 963
SRC = "架空の2店の感想の短文（作成者が乱数で作成、seed 963）"

COMMON = ["店員", "接客", "雰囲気", "値段", "量", "味", "待ち時間", "席", "駐車場", "予約", "説明", "笑顔",
          "清潔", "静か", "明るい", "丁寧", "早い", "遅い", "狭い", "広い", "また来たい", "満足", "残念", "友人",
          "家族", "週末", "平日", "昼", "夜", "持ち帰り"]
FLAVOR = ["苺", "抹茶", "栗", "檸檬", "胡麻", "黒糖", "林檎", "桃", "柚子", "珈琲", "南瓜", "葡萄", "蜂蜜",
          "生姜", "白桃", "黒豆"]
ITEM = ["タルト", "ラテ", "プリン", "パイ", "ロール", "ゼリー", "ワッフル", "スコーン", "大福", "マフィン",
        "パフェ", "クッキー", "ソーダ", "ケーキ"]
PREFIX = ["", "季節の", "限定", "特製"]
WORDS = COMMON + [a + f + i for a in PREFIX for f in FLAVOR for i in ITEM]
V = len(WORDS)
K_TOP = 10           # 上位何語を見るか
N_KEY = 10           # 本当にA店で多い語の数（B店で多い語も同じ数）
KEY_RANK_MAX = 300   # 本当に差のある語は、よく出る順で6〜300位の語から選ぶ


def base_probs(rng, zipf=1.0):
    """全体の出方：よく出る語ほど上の順位。順位 r の語は 1/r^zipf に比例"""
    order = np.concatenate([np.arange(len(COMMON)), len(COMMON) + rng.permutation(V - len(COMMON))])
    p = np.empty(V)
    p[order] = 1.0 / np.arange(1, V + 1) ** zipf
    return p / p.sum()


def make_truth(rng, mult=2.0, zipf=1.0):
    p = base_probs(rng, zipf)
    ranks = np.argsort(-p)                             # よく出る順の語の番号
    cand = ranks[5:KEY_RANK_MAX][rng.permutation(KEY_RANK_MAX - 5)[:2 * N_KEY]]  # 6〜300位の語から選ぶ
    m = np.ones(V)
    m[cand[:N_KEY]] = mult          # A店で mult 倍出やすい
    m[cand[N_KEY:]] = 1.0 / mult    # B店で mult 倍出やすい（A店で 1/mult 倍）
    # A店とB店の出やすさ：pA ∝ p*sqrt(m)、pB ∝ p/sqrt(m)
    pa = p * np.sqrt(m); pa /= pa.sum()
    pb = p / np.sqrt(m); pb /= pb.sum()
    key_a = np.zeros(V, bool); key_a[cand[:N_KEY]] = True
    return p, pa, pb, m, key_a


def n_words(rng, n_text):
    return int(rng.integers(5, 13, n_text).sum())   # 1文 5〜12語


def scores(ca, cb, k_add=5.0):
    ta, tb = ca.sum(), cb.sum()
    out = {}
    # 1) 比そのまま（0回のときに割れないよう、両店に0.5回ずつ足す）
    lr = np.log2(((ca + 0.5) / ta) / ((cb + 0.5) / tb))
    out["比そのまま"] = lr
    # 2) 比（両店で合わせて10回以上出た語だけ）
    r = lr.copy(); r[(ca + cb) < 10] = -np.inf
    out["比（10回以上の語だけ）"] = r
    # 3) 出る割合の差（A店の割合−B店の割合）
    out["出る割合の差"] = ca / ta - cb / tb
    # 4) 寄せた比：両店に k_add 回ずつ足してから比を取る（回数の少ない語ほど「同じ」に寄る）
    out["寄せた比"] = np.log2(((ca + k_add) / ta) / ((cb + k_add) / tb))
    # 5) 比÷振れ：比そのまま（自然対数）を、回数から決まる振れの大きさ √(1/a+1/b) で割ったもの
    out["比÷振れ"] = lr * np.log(2) / np.sqrt(1.0 / (ca + 0.5) + 1.0 / (cb + 0.5))
    return out


METHODS = ["比そのまま", "比（10回以上の語だけ）", "出る割合の差", "寄せた比", "比÷振れ"]


def eval_once(rng, n_text=1000, mult=2.0, zipf=1.0, k_add=5.0):
    p, pa, pb, m, key_a = make_truth(rng, mult, zipf)
    ca = rng.multinomial(n_words(rng, n_text), pa).astype(float)
    cb = rng.multinomial(n_words(rng, n_text), pb).astype(float)
    sc = scores(ca, cb, k_add)
    res = {}
    tot = ca + cb
    for k in METHODS:
        # 同じ値は乱数で順を決める
        top = np.lexsort((rng.random(V), -sc[k]))[:K_TOP]
        res[k] = {"precision": key_a[top].mean(), "median_count": float(np.median(tot[top])),
                  "share_le5": float((tot[top] <= 5).mean())}
    extra = {"only_in_A": int(((ca > 0) & (cb == 0)).sum()),
             "only_in_A_truly_A": int(((ca > 0) & (cb == 0) & key_a).sum()),
             "words_used": int((tot > 0).sum())}
    return res, extra, (ca, cb, m, sc)


def run_reps(seed0, reps, **kw):
    rows, ex = [], []
    for r in range(reps):
        res, extra, _ = eval_once(np.random.default_rng(seed0 + r), **kw)
        for k, v in res.items():
            rows.append({"rep": r, "method": k, **v})
        ex.append(extra)
    d = pd.DataFrame(rows)
    s = d.groupby("method", sort=False)[["precision", "median_count", "share_le5"]].mean()
    return s.loc[METHODS], pd.DataFrame(ex).mean()


def main():
    rng = np.random.default_rng(SEED)

    # ---- 1回分の文章（data）----
    p, pa, pb, m, key_a = make_truth(rng)
    texts, ca, cb = [], np.zeros(V), np.zeros(V)
    for shop, pp, cc in [("A", pa, ca), ("B", pb, cb)]:
        for i in range(1000):
            L = int(rng.integers(5, 13))
            idx = rng.choice(V, size=L, p=pp)
            np.add.at(cc, idx, 1)
            texts.append({"shop": shop, "text_id": f"{shop}{i + 1:04d}", "n_words": L,
                          "text": " ".join(WORDS[j] for j in idx)})
    pd.DataFrame(texts).to_csv(DATA / "texts.csv", index=False)
    sc = scores(ca, cb)
    wd = pd.DataFrame({"word": WORDS, "true_ratio_A_over_B": np.round(m, 4), "base_share": np.round(p, 6),
                       "count_A": ca.astype(int), "count_B": cb.astype(int),
                       "ratio_raw_log2": np.round(sc["比そのまま"], 4), "shrunk_log2": np.round(sc["寄せた比"], 4),
                       "ratio_over_se": np.round(sc["比÷振れ"], 4)})
    wd.to_csv(DATA / "words.csv", index=False)
    one = {}
    tot = ca + cb
    for k in METHODS:
        top = np.lexsort((np.random.default_rng(SEED + 1).random(V), -sc[k]))[:K_TOP]
        one[k] = {"words": [WORDS[j] for j in top], "counts_A": ca[top].astype(int).tolist(),
                  "counts_B": cb[top].astype(int).tolist(), "is_truly_A": key_a[top].astype(int).tolist(),
                  "truly_A": int(key_a[top].sum())}
    one_extra = {"texts_per_shop": 1000, "words_A": int(ca.sum()), "words_B": int(cb.sum()),
                 "word_types": V, "used_types": int((tot > 0).sum()),
                 "only_in_A": int(((ca > 0) & (cb == 0)).sum()),
                 "only_in_A_truly_A": int(((ca > 0) & (cb == 0) & key_a).sum()),
                 "only_in_A_max_count": int(ca[(ca > 0) & (cb == 0)].max()) if ((ca > 0) & (cb == 0)).any() else 0}

    # ---- 2) 基本の置き方で200回 ----
    base, base_ex = run_reps(SEED * 1000, 200)
    bt = base.copy()
    bt["precision_pct"] = (bt.precision * 100).round(2); bt["share_le5_pct"] = (bt.share_le5 * 100).round(2)
    bt["median_count"] = bt.median_count.round(2)
    bt[["precision_pct", "median_count", "share_le5_pct"]].to_csv(RES / "methods_base.csv")
    # 作りの確かめ：文章を区切って数えた回数と words.csv の回数
    cnt = pd.Series(" ".join(pd.DataFrame(texts).query("shop == 'A'").text).split()).value_counts()
    check_counts = bool(all(int(cnt.get(w, 0)) == int(c) for w, c in zip(WORDS, ca)))

    # ---- 3) 差のない語で、回数ごとの比の振れ（式との比べ）----
    rows = []
    for r in range(200):
        p_, pa_, pb_, m_, key_ = make_truth(np.random.default_rng(SEED * 10 + r))
        g = np.random.default_rng(SEED * 20 + r)
        ca_ = g.multinomial(n_words(g, 1000), pa_); cb_ = g.multinomial(n_words(g, 1000), pb_)
        null = m_ == 1
        rr = np.log2(((ca_ + 0.5) / ca_.sum()) / ((cb_ + 0.5) / cb_.sum()))
        rows.append(pd.DataFrame({"tot": (ca_ + cb_)[null], "r": rr[null]}))
    nd = pd.concat(rows, ignore_index=True)
    bins = [(1, 2), (3, 5), (6, 10), (11, 30), (31, 100), (101, 300), (301, 100000)]
    sdrows = []
    for lo, hi in bins:
        x = nd[(nd.tot >= lo) & (nd.tot <= hi)]
        mid = np.median(x.tot)
        formula = 2 / np.sqrt(mid) / np.log(2)  # 半々に分かれる回数の比の振れ：√(1/(n/2)+1/(n/2))÷ln2
        sdrows.append({"total_count": f"{lo}〜{hi}" if hi < 100000 else f"{lo}以上", "n_words": int(len(x)),
                       "median_count": float(mid), "sd_log2_ratio": round(float(x.r.std()), 3),
                       "formula_sd_at_median": round(float(formula), 3) if lo >= 11 else "",
                       "share_2x_or_more": round(float((x.r.abs() >= 1).mean()), 4)})
    sdtab = pd.DataFrame(sdrows)
    sdtab.to_csv(RES / "null_ratio_by_count.csv", index=False)

    # ---- 4) 確かめ：文章の数 × 本当の倍率 ----
    grid = []
    for nt in [200, 1000, 5000]:
        for mu in [1.5, 2.0, 3.0]:
            s, ex = run_reps(SEED * 100 + int(nt) + int(mu * 10), 100, n_text=nt, mult=mu)
            for k in METHODS:
                grid.append({"texts_per_shop": nt, "true_mult": mu, "method": k,
                             "precision": round(float(s.loc[k, "precision"]), 4),
                             "share_le5": round(float(s.loc[k, "share_le5"]), 4),
                             "median_count": round(float(s.loc[k, "median_count"]), 2)})
    gd = pd.DataFrame(grid)
    gd.to_csv(RES / "grid_texts_mult.csv", index=False)

    # ---- 5) 確かめ：語の出方の偏り（zipf）と、寄せる強さ（prior）----
    zrows = []
    for z in [0.8, 1.0, 1.2]:
        s, _ = run_reps(SEED * 300 + int(z * 10), 100, zipf=z)
        for k in METHODS:
            zrows.append({"zipf": z, "method": k, "precision": round(float(s.loc[k, "precision"]), 4)})
    zd = pd.DataFrame(zrows); zd.to_csv(RES / "by_zipf.csv", index=False)
    prows = []
    for ka in [1, 5, 20]:
        s, _ = run_reps(SEED * 400 + ka, 100, k_add=ka)
        prows.append({"k_add": ka, "method": "寄せた比", "precision": round(float(s.loc["寄せた比", "precision"]), 4),
                      "median_count": round(float(s.loc["寄せた比", "median_count"]), 2),
                      "share_le5": round(float(s.loc["寄せた比", "share_le5"]), 4)})
    pdx = pd.DataFrame(prows); pdx.to_csv(RES / "by_k_add.csv", index=False)

    rg = lambda k: [float(gd[gd.method == k].precision.min()), float(gd[gd.method == k].precision.max())]
    out = {"setup": {"word_types": V, "key_words_A": N_KEY, "key_words_B": N_KEY, "top_k": K_TOP, "random_pick_expected_precision": round(N_KEY / V, 4),
                     "texts_per_shop": 1000, "words_per_text": "5〜12", "true_mult": 2.0, "zipf": 1.0, "k_add": 5, "key_rank": "6〜300位"},
           "one_draw": {**one_extra, "top10": one},
           "base_200reps": bt[["precision_pct", "median_count", "share_le5_pct"]].reset_index().to_dict("records"),
           "check": {"words_csv_matches_texts_A": check_counts,
                     "null_sd_minus_formula_11plus": [round(float(abs(a - b)), 3) for a, b in
                                                      zip(sdtab.sd_log2_ratio[3:], sdtab.formula_sd_at_median[3:])]},
           "base_200reps_extra": {k: round(float(v), 2) for k, v in base_ex.items()},
           "null_ratio_by_count": sdtab.to_dict("records"),
           "grid_range_precision": {k: rg(k) for k in METHODS},
           "grid": gd.to_dict("records"), "by_zipf": zd.to_dict("records"), "by_k_add": pdx.to_dict("records")}
    json.dump(out, open(RES / "a963_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：回数と比（1回分）
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    r = sc["比そのまま"]
    kb = m < 1
    ax.scatter(tot[~key_a & ~kb], r[~key_a & ~kb], s=10, color=GRAY, alpha=.6, lw=0, label="本当は差のない語")
    ax.scatter(tot[key_a], r[key_a], s=28, color=ORANGE, lw=0, label="本当にA店で2倍出やすい語")
    ax.scatter(tot[kb], r[kb], s=28, color=BLUE, lw=0, label="本当にB店で2倍出やすい語")
    ax.set_xscale("log"); ax.set_xticks([1, 10, 100, 1000]); ax.set_xticklabels(["1", "10", "100", "1,000"])
    ax.axhline(0, color=INK, lw=.6)
    ax.axhline(1, color=ORANGE, lw=.8, ls="--"); ax.axhline(-1, color=BLUE, lw=.8, ls="--")
    ax.set_yticks([-3, -2, -1, 0, 1, 2, 3]); ax.set_yticklabels(["B店が8倍", "B店が4倍", "B店が2倍", "同じ", "A店が2倍", "A店が4倍", "A店が8倍"])
    ax.set_xlabel("2店を合わせてその語が出た回数（対数の目盛り）"); ax.set_ylabel("見かけの比（A店÷B店）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("出た回数が少ない語ほど、差がなくても比は大きく振れる（1回分）")
    save(fig, "a963_scatter.png", SRC)

    # 図2：数え方ごとの当たり
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    b = base.reset_index()
    col = [GRAY, LIGHT, LIGHT, ORANGE, BLUE]
    ax.barh(b.method[::-1], b.precision[::-1] * 100, color=col[::-1])
    for i, (v, s5) in enumerate(zip(b.precision[::-1] * 100, b.share_le5[::-1] * 100)):
        ax.text(v + 1, i, f"{v:.2f}%（5回以下の語 {s5:.2f}%）", va="center", fontsize=8.5)
    ax.set_xlim(0, 100)
    ax.set_xlabel("「A店に特徴的」の上位10語のうち、本当にA店で多い語の割合（%、200回の平均）")
    ax.set_title("比そのままの上位は、少ない回数の語で埋まる")
    save(fig, "a963_precision.png", SRC)

    # 図3：文章の数ごとの当たり（倍率2）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for k, c, ls in [("比そのまま", GRAY, "-"), ("比（10回以上の語だけ）", LIGHT, "-"),
                     ("出る割合の差", GREEN, "--"), ("寄せた比", ORANGE, "-"), ("比÷振れ", BLUE, "-")]:
        x = gd[(gd.method == k) & (gd.true_mult == 2.0)]
        ax.plot(x.texts_per_shop, x.precision * 100, marker="o", color=c, ls=ls, label=k)
    ax.set_xscale("log"); ax.xaxis.set_minor_locator(plt.NullLocator()); ax.set_xticks([200, 1000, 5000]); ax.set_xticklabels(["200件", "1,000件", "5,000件"])
    ax.set_ylim(0, 100); ax.set_xlabel("1店あたりの感想の件数"); ax.set_ylabel("上位10語の当たり（%）")
    ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("件数を増やしても、比そのままの当たりは上がりにくい（本当の差2倍）")
    save(fig, "a963_by_texts.png", SRC)
    print(json.dumps({k: out[k] for k in ["check", "one_draw", "base_200reps", "base_200reps_extra", "null_ratio_by_count",
                                         "grid_range_precision", "by_zipf", "by_k_add"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
