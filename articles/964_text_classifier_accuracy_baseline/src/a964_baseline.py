"""964 文章を自動で分類したときの正解率は、何と比べればよいのか？（架空のデータ）

架空の通信販売の店への問い合わせの短文。正しい分類（配送・返品・支払い・会員登録）を作成者が置き、
語は作成者が書いた語の一覧から乱数で並べる。分類器は、学習用の文章で分類ごとに語の回数を数えるだけの
簡単なもの（作成者が書いたもの）。正解率を「全部いちばん多い分類と答える」などの比べる相手と並べる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 964
SRC = "架空の店への問い合わせの短文（作成者が乱数で作成、seed 964）"

CATS = ["配送", "返品", "支払い", "会員登録"]
KEYS = {
    "配送": ["届かない", "配達", "発送", "到着", "追跡番号", "日時指定", "置き配", "不在票", "宅配ボックス", "遅れ",
             "送り先", "梱包", "再配達", "受け取り", "時間帯"],
    "返品": ["返品", "交換", "サイズ違い", "色違い", "返送", "返金", "傷", "不良品", "未使用", "期限",
             "着払い", "伝票", "イメージと違う", "破損", "取り替え"],
    "支払い": ["支払い", "請求", "引き落とし", "振込", "領収書", "二重", "金額", "ポイント", "クーポン", "決済",
               "後払い", "明細", "分割", "残高", "割引"],
    "会員登録": ["会員", "ログイン", "パスワード", "メールアドレス", "退会", "登録", "認証", "マイページ", "住所変更",
                 "通知", "メルマガ", "画面", "入れない", "変更", "確認メール"],
}
COMMON = ["お世話になります", "先日", "注文", "商品", "確認", "お願いします", "教えて", "いつ", "どう", "したい",
          "ですか", "でした", "今日", "昨日", "急ぎ", "すみません", "問い合わせ", "番号", "件", "について",
          "できますか", "わかりません", "ありがとうございます", "よろしく", "前回", "また", "方法", "対応", "もう一度", "手続き"]
VOCAB = COMMON + [w for c in CATS for w in KEYS[c]]
VIDX = {w: i for i, w in enumerate(VOCAB)}
V = len(VOCAB)
REST = np.array([3, 2, 1]) / 6.0   # 最多の分類以外の3分類の分け方（返品:支払い:会員登録 = 3:2:1）


def shares(top):
    return np.concatenate([[top], (1 - top) * REST])


def make_texts(rng, n, sh, q, cross=0.04):
    """n 件の問い合わせ。1件は6〜12語。1語ずつ、確率 q で自分の分類の手がかりの語、
    確率 cross でほかの分類の手がかりの語、残りは一般の語から選ぶ"""
    y = rng.choice(len(CATS), size=n, p=sh)
    L = rng.integers(6, 13, n)
    nc = len(COMMON)
    row = np.repeat(np.arange(n), L)
    own = y[row]
    tot = len(row)
    u = rng.random(tot)
    other = (own + rng.integers(1, len(CATS), tot)) % len(CATS)     # 自分以外の3分類から1つ
    cat = np.where(u < q, own, other)
    w = np.where(u < q + cross, nc + 15 * cat + rng.integers(0, 15, tot), rng.integers(0, nc, tot))
    X = np.zeros((n, V), dtype=np.int32)
    np.add.at(X, (row, w), 1)
    texts = np.split(w, np.cumsum(L)[:-1])
    return X, y, texts


def fit(X, y, alpha=1.0):
    cnt = np.array([X[y == c].sum(0) for c in range(len(CATS))], dtype=float) + alpha
    logp = np.log(cnt / cnt.sum(1, keepdims=True))
    prior = np.log(np.bincount(y, minlength=len(CATS)) / len(y))
    return logp, prior


def predict(model, X, use_prior):
    logp, prior = model
    s = X @ logp.T + (prior if use_prior else 0)
    return s.argmax(1)


def kappa(y, p, k=len(CATS)):
    po = (y == p).mean()
    pe = sum((y == c).mean() * (p == c).mean() for c in range(k))
    return (po - pe) / (1 - pe)


def evaluate(y, p):
    rec = [float((p[y == c] == c).mean()) if (y == c).any() else np.nan for c in range(len(CATS))]
    return {"accuracy": float((y == p).mean()), "macro_recall": float(np.nanmean(rec)),
            "kappa": float(kappa(y, p)), **{f"recall_{CATS[c]}": rec[c] for c in range(len(CATS))}}


def one_setting(seed, top, q, n_train=2000, n_test=2000, test_top=None):
    rng = np.random.default_rng(seed)
    Xtr, ytr, _ = make_texts(rng, n_train, shares(top), q)
    Xte, yte, _ = make_texts(rng, n_test, shares(top if test_top is None else test_top), q)
    m = fit(Xtr, ytr)
    out = {}
    out["分類器（分類の多さを足さない）"] = evaluate(yte, predict(m, Xte, False))
    out["分類器（分類の多さを足す）"] = evaluate(yte, predict(m, Xte, True))
    major = np.bincount(ytr, minlength=len(CATS)).argmax()          # 学習用で最多の分類
    out["全部いちばん多い分類と答える"] = evaluate(yte, np.full(len(yte), major))
    prop = rng.choice(len(CATS), size=len(yte), p=np.bincount(ytr, minlength=4) / len(ytr))
    out["学習用の割合どおりにでたらめに答える"] = evaluate(yte, prop)
    return out


METHODS = ["分類器（分類の多さを足さない）", "分類器（分類の多さを足す）", "全部いちばん多い分類と答える",
           "学習用の割合どおりにでたらめに答える"]


def run(seed0, reps, **kw):
    rows = []
    for r in range(reps):
        o = one_setting(seed0 + r, **kw)
        for k in METHODS:
            rows.append({"method": k, **o[k]})
    return pd.DataFrame(rows).groupby("method", sort=False).mean().loc[METHODS]


def pct(x):
    return round(float(x) * 100, 2)


def fmt(df):
    """割合は%（小数2桁）、κ はそのまま（小数4桁）"""
    d = df.copy()
    for c in d.columns:
        d[c] = d[c].astype(float).round(4) if c == "kappa" else (d[c].astype(float) * 100).round(2)
    return d


def main():
    rng = np.random.default_rng(SEED)
    TOP, Q = 0.7, 0.2

    # ---- data：1回分の問い合わせ（学習用・確かめ用）----
    Xtr, ytr, ttr = make_texts(rng, 2000, shares(TOP), Q)
    Xte, yte, tte = make_texts(rng, 2000, shares(TOP), Q)
    m = fit(Xtr, ytr)
    p0, p1 = predict(m, Xte, False), predict(m, Xte, True)
    rows = []
    for part, y, tt in [("学習用", ytr, ttr), ("確かめ用", yte, tte)]:
        for i, (yy, ws) in enumerate(zip(y, tt)):
            r = {"part": part, "id": f"{'L' if part == '学習用' else 'T'}{i + 1:04d}", "true_class": CATS[yy],
                 "text": " ".join(VOCAB[w] for w in ws)}
            if part == "確かめ用":
                r["pred_no_prior"] = CATS[p0[i]]; r["pred_with_prior"] = CATS[p1[i]]
            rows.append(r)
    pd.DataFrame(rows).to_csv(DATA / "inquiries.csv", index=False)
    conf = pd.crosstab(pd.Categorical([CATS[c] for c in yte], CATS), pd.Categorical([CATS[c] for c in p1], CATS),
                       rownames=["正しい分類"], colnames=["分類器（多さを足す）の答え"], dropna=False)
    conf.to_csv(RES / "confusion_one_draw.csv")
    one = {"test_share_pct": {CATS[c]: pct((yte == c).mean()) for c in range(4)},
           "no_prior": {k: (round(v, 4) if k == "kappa" else pct(v)) for k, v in evaluate(yte, p0).items()},
           "with_prior": {k: (round(v, 4) if k == "kappa" else pct(v)) for k, v in evaluate(yte, p1).items()}}

    # ---- 基本の置き方：100回 ----
    base = run(SEED * 1000, 100, top=TOP, q=Q)
    bt = fmt(base)
    bt.to_csv(RES / "methods_base.csv")
    # 割合どおりにでたらめに答えたときの正解率の式：Σ 割合^2
    formula_prop = pct((shares(TOP) ** 2).sum())

    # ---- 確かめ：最多の分類の割合 × 手がかりの濃さ ----
    grid = []
    for top in [0.4, 0.7, 0.9, 0.95]:
        for q in [0.1, 0.2, 0.4]:
            g = run(SEED * 100 + int(top * 100) * 10 + int(q * 10), 40, top=top, q=q)
            for k in METHODS:
                grid.append({"top_share": top, "q": q, "method": k, **fmt(g).loc[k].to_dict()})
    gd = pd.DataFrame(grid)
    gd.to_csv(RES / "grid_top_q.csv", index=False)
    # 分類器（足す）が「全部最多」を上回った幅
    piv = gd.pivot_table(index=["top_share", "q"], columns="method", values="accuracy")
    lift = (piv["分類器（分類の多さを足す）"] - piv["全部いちばん多い分類と答える"]).round(2)
    lift0 = (piv["分類器（分類の多さを足さない）"] - piv["全部いちばん多い分類と答える"]).round(2)
    lt = pd.DataFrame({"with_prior_minus_majority": lift, "no_prior_minus_majority": lift0}).reset_index()
    lt.to_csv(RES / "grid_lift_over_majority.csv", index=False)

    # ---- 確かめ：学習用は最多70%のまま、確かめ用の割合だけ変わる ----
    shift = []
    for tt in [0.4, 0.55, 0.7, 0.85, 0.95]:
        g = run(SEED * 50 + int(tt * 100), 40, top=TOP, q=Q, test_top=tt)
        for k in METHODS:
            shift.append({"test_top_share": tt, "method": k, **fmt(g).loc[k].to_dict()})
    sd = pd.DataFrame(shift)
    sd.to_csv(RES / "test_mix_shift.csv", index=False)

    out = {"setup": {"classes": CATS, "shares_base": dict(zip(CATS, [round(float(x), 4) for x in shares(TOP)])),
                     "vocab": V, "q": Q, "cross": 0.04, "n_train": 2000, "n_test": 2000, "words_per_text": "6〜12"},
           "formula_proportional_random_accuracy_pct": formula_prop,
           "base_lift_over_majority_pts": {
               "with_prior": round(float(bt.loc["分類器（分類の多さを足す）", "accuracy"] - bt.loc["全部いちばん多い分類と答える", "accuracy"]), 2),
               "no_prior": round(float(bt.loc["分類器（分類の多さを足さない）", "accuracy"] - bt.loc["全部いちばん多い分類と答える", "accuracy"]), 2)},
           "one_draw": one, "base_100reps_pct": bt.reset_index().to_dict("records"),
           "grid_lift_over_majority": lt.to_dict("records"),
           "grid_lift_range": {"with_prior": [float(lift.min()), float(lift.max())],
                               "no_prior": [float(lift0.min()), float(lift0.max())]},
           "test_mix_shift": sd.to_dict("records")}
    json.dump(out, open(RES / "a964_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：基本の置き方で4つの答え方
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    labels = ["分類器（多さを足さない）", "分類器（多さを足す）", "全部いちばん多い分類", "割合どおりにでたらめ"]
    y = np.arange(4)[::-1]
    ax.barh(y + 0.18, bt["accuracy"], height=0.36, color=BLUE, label="正解率")
    ax.barh(y - 0.18, bt["macro_recall"], height=0.36, color=ORANGE, label="分類ごとの当たりの平均")
    for yy, a, b in zip(y, bt["accuracy"], bt["macro_recall"]):
        ax.text(a + 1, yy + 0.18, f"{a:.2f}%", va="center", fontsize=8.5)
        ax.text(b + 1, yy - 0.18, f"{b:.2f}%", va="center", fontsize=8.5)
    ax.set_yticks(y); ax.set_yticklabels(labels); ax.set_xlim(0, 105)
    ax.set_xlabel("%（最多の分類「配送」が70%、100回の平均）")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("全部「配送」と答えるだけで正解率70%になる")
    save(fig, "a964_methods.png", SRC)

    # 図2：最多の割合ごとの正解率（手がかりの濃さ0.2）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for k, c, lab in [("分類器（分類の多さを足す）", BLUE, "分類器（多さを足す）"),
                      ("分類器（分類の多さを足さない）", LIGHT, "分類器（多さを足さない）"),
                      ("全部いちばん多い分類と答える", ORANGE, "全部いちばん多い分類"),
                      ("学習用の割合どおりにでたらめに答える", GRAY, "割合どおりにでたらめ")]:
        x = gd[(gd.method == k) & (gd.q == 0.2)]
        ax.plot(x.top_share * 100, x.accuracy, marker="o", color=c, label=lab)
    ax.set_xticks([40, 70, 90, 95]); ax.set_xlabel("いちばん多い分類の割合（%）"); ax.set_ylabel("正解率（%）")
    ax.set_ylim(0, 100); ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("最多の分類が多いほど、「全部いちばん多い分類」との差は縮む（手がかり0.2）")
    save(fig, "a964_by_top_share.png", SRC)

    # 図3：確かめ用の割合だけ変わると
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for k, c, lab in [("分類器（分類の多さを足す）", BLUE, "正解率：分類器（多さを足す）"),
                      ("全部いちばん多い分類と答える", ORANGE, "正解率：全部いちばん多い分類")]:
        x = sd[sd.method == k]
        ax.plot(x.test_top_share * 100, x.accuracy, marker="o", color=c, label=lab)
    x = sd[sd.method == "分類器（分類の多さを足す）"]
    ax.plot(x.test_top_share * 100, x.macro_recall, marker="s", color=BLUE, ls="--", label="分類ごとの当たりの平均：分類器（多さを足す）")
    ax.set_xlabel("確かめ用の文章で「配送」が占める割合（%、学習用は70%のまま）"); ax.set_ylabel("%")
    ax.set_ylim(0, 100); ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax.set_title("分類器は同じでも、確かめる文章の割合で正解率は動く")
    save(fig, "a964_test_mix.png", SRC)
    print(json.dumps({k: out[k] for k in ["formula_proportional_random_accuracy_pct", "base_lift_over_majority_pts", "one_draw", "base_100reps_pct",
                                         "grid_lift_range"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
