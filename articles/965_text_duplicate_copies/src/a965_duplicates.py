"""965 同じ文の重複（コピペ）を除かないと、何が起きるのか？（架空のデータ）

架空の店に8週間で届いた問い合わせ。本当の問い合わせ（1人1件）を作成者が置き、返事を待てずに
同じ文を送り直す「再送」と、1人が同じ文を何十回も貼り付けた1件を混ぜる。再送には、そのままの写し・
空白や記号だけ違う写し・頭に1語足した写しがある。重複を除く4つのやり方で、話題の割合・週ごとの件数・
よく出る語・本当は別の人の文を消してしまう数を比べる。
"""
import json
import unicodedata
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 965
SRC = "架空の店への問い合わせの短文（作成者が乱数で作成、seed 965）"

TOPICS = ["配送", "返品", "支払い", "会員登録", "お礼"]
SHARE = np.array([0.30, 0.20, 0.20, 0.15, 0.15])
KEYS = {
    "配送": ["届かない", "配達", "発送", "到着", "追跡番号", "日時指定", "置き配", "不在票", "遅れ", "再配達"],
    "返品": ["返品", "交換", "サイズ違い", "返送", "返金", "傷", "未使用", "伝票", "破損", "取り替え"],
    "支払い": ["支払い", "請求", "引き落とし", "振込", "領収書", "二重", "金額", "クーポン", "決済", "明細"],
    "会員登録": ["会員", "ログイン", "パスワード", "メールアドレス", "退会", "登録", "認証", "マイページ", "住所変更", "通知"],
}
COMMON = ["お世話になります", "先日", "注文", "商品", "確認", "お願いします", "教えて", "いつ", "どう", "したい",
          "ですか", "今日", "昨日", "すみません", "について", "できますか", "わかりません", "前回", "方法", "手続き"]
THANKS_HEAD = ["ありがとうございました", "助かりました", "お礼です"]
THANKS = ["対応", "早い", "丁寧な", "また", "利用します", "安心しました", "届きました", "説明", "わかりやすい"]
ADD = ["再送", "至急", "先ほどの件"]
N_ORIG, WEEKS = 2000, 8
RESEND = np.array([0.15, 0.06, 0.06, 0.06, 0.0])    # 話題ごとに、送り直す人の割合
P_KIND = [0.5, 0.3, 0.2]                            # 写しの種類：そのまま・空白や記号だけ違う・頭に1語足す
CUM = np.cumsum(SHARE)[:-1]
HEAVY = 30                                          # 1人が同じ文を送った回数（1通目＋貼り付け29回、5週目、話題は配送）


def orig_text(rng, t):
    if TOPICS[t] == "お礼":                         # お礼は短い（2〜4語）。別の人でも同じ文になりやすい
        k = int(rng.integers(2, 5))
        return [THANKS_HEAD[int(rng.integers(3))]] + [THANKS[j] for j in rng.choice(len(THANKS), k - 1, replace=False)]
    L = int(rng.integers(6, 13))
    u, ik, ic = rng.random(L), rng.integers(0, 10, L), rng.integers(0, len(COMMON), L)
    kw = KEYS[TOPICS[t]]
    return [kw[a] if uu < 0.4 else COMMON[b] for uu, a, b in zip(u, ik, ic)]


def variant(rng, words, kind):
    s = " ".join(words)
    if kind == 0:
        return s
    if kind == 1:                                   # 全角の空白にする、または末尾に「！」を付ける
        return s.replace(" ", "　") if rng.random() < 0.5 else s + "！"
    return str(rng.choice(ADD)) + " " + s


def make_data(rng, resend_mult=1.0, topic_dep=True, heavy=HEAVY):
    """届いた時刻 t（週の単位、0〜8）を持たせ、t の順に並べる。写しは本人の1通目より後に届く"""
    rows = []
    for i in range(N_ORIG):
        t = int(np.searchsorted(CUM, rng.random(), side="right"))
        t0 = rng.uniform(0, WEEKS)
        w = orig_text(rng, t)
        rows.append({"person": i, "topic": t, "time": t0, "kind": "本人の1通目", "text": " ".join(w), "is_copy": 0})
        pr = (RESEND[t] if topic_dep else RESEND @ SHARE / SHARE[:4].sum() * (t < 4)) * resend_mult
        if rng.random() < pr:
            k = int(rng.geometric(0.6))             # 送り直した回数（1回以上、平均1.67回）
            tc = t0
            for _ in range(k):
                kind = int(rng.choice(3, p=P_KIND))
                tc = tc + rng.exponential(0.15)       # 前の送信から平均0.15週（約1日）後
                if tc >= WEEKS:                         # 8週の外に届いた写しは数えない
                    break
                rows.append({"person": i, "topic": t, "time": tc, "kind": ["そのまま", "空白・記号", "1語足す"][kind],
                             "text": variant(rng, w, kind), "is_copy": 1})
    if heavy:
        w = orig_text(rng, 0)
        pid = N_ORIG
        ts = np.sort(rng.uniform(4, 5, heavy))         # 5週目の中で heavy 回
        for j, tt in enumerate(ts):
            rows.append({"person": pid, "topic": 0, "time": tt, "kind": "本人の1通目" if j == 0 else "貼り付け",
                         "text": " ".join(w), "is_copy": int(j > 0)})
    df = pd.DataFrame(rows).sort_values("time", kind="stable").reset_index(drop=True)
    df["week"] = np.floor(df.time).astype(int) + 1
    df["time"] = df.time.round(4)
    return df


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return s.replace("!", "").replace("！", "")


def tokens(s):
    return set(norm(s).split())


def dedup(df, how, thr=0.8):
    """残す行の印（True）を返す。前に残した文と同じ・似ている文を消す"""
    if how == "除かない":
        return np.ones(len(df), bool)
    if how == "完全一致":
        return ~df.text.duplicated().values
    if how == "空白・記号をそろえて一致":
        return ~df.text.map(lambda s: "".join(norm(s).split())).duplicated().values
    if how == "same_person":                        # 同じ送り主の文どうしだけを、届いた順に比べる
        keep = np.ones(len(df), bool)
        for _, idx in df.groupby("person").indices.items():
            if len(idx) < 2:
                continue
            kept = []
            for i in sorted(idx):
                ti = tokens(df.text.iat[i])
                if any(len(ti & tk) / len(ti | tk) >= thr for tk in kept):
                    keep[i] = False
                else:
                    kept.append(ti)
        return keep
    # 語の重なり：2つの文の語の集合の重なり（共通の語÷どちらかにある語）が thr 以上なら同じとみなす
    toks = [tokens(s) for s in df.text]
    vocab = {w: j for j, w in enumerate(sorted(set().union(*toks)))}
    X = np.zeros((len(toks), len(vocab)), dtype=np.float32)
    for i, ts in enumerate(toks):
        X[i, [vocab[w] for w in ts]] = 1
    inter = X @ X.T
    sz = X.sum(1)
    # 重なり＝共通÷（a＋b−共通）≥ thr を、割り算なしで (1＋thr)×共通 ≥ thr×(a＋b) と調べる
    hit = np.tril(inter * (1 + thr) >= thr * (sz[:, None] + sz[None, :]) - 1e-4, -1)  # 前の文に、線以上に似た文があるか
    keep = np.ones(len(df), bool)
    for i in np.where(hit.any(1))[0]:              # 似た文がある行だけ、届いた順に調べる
        keep[i] = not (hit[i, :i] & keep[:i]).any()
    return keep


HOWS = ["除かない", "完全一致", "空白・記号をそろえて一致", "語の重なり0.8以上", "同じ送り主で語の重なり0.8以上"]
CODE = {"語の重なり0.8以上": "jac", "同じ送り主で語の重なり0.8以上": "same_person"}


def measure(df, keep):
    d = df[keep]
    orig = df[df.is_copy == 0]
    true_share = orig.topic.value_counts(normalize=True).reindex(range(5), fill_value=0).values
    sh = d.topic.value_counts(normalize=True).reindex(range(5), fill_value=0).values
    removed_orig = int(((df.is_copy == 0) & ~keep).sum())
    removed_thanks = int(((df.is_copy == 0) & ~keep & (df.topic == 4)).sum())
    left_copy = int(((df.is_copy == 1) & keep).sum())
    out = {"n_texts": int(keep.sum()), "n_true": int(len(orig)),
           "count_error_pct": round(float((keep.sum() / len(orig) - 1) * 100), 3),
           "max_abs_share_error_pt": round(float(np.abs(sh - true_share).max() * 100), 3),
           "removed_originals": removed_orig, "removed_thanks_originals": removed_thanks,
           "true_thanks": int((orig.topic == 4).sum()), "left_copies": left_copy,
           "all_copies": int(df.is_copy.sum())}
    for t in range(5):
        out[f"share_{TOPICS[t]}"] = round(float(sh[t] * 100), 3)
        out[f"true_share_{TOPICS[t]}"] = round(float(true_share[t] * 100), 3)
    wk = d[d.topic == 0].week.value_counts().reindex(range(1, WEEKS + 1), fill_value=0)
    wt = orig[orig.topic == 0].week.value_counts().reindex(range(1, WEEKS + 1), fill_value=0)
    out["week5_delivery"] = int(wk[5]); out["week5_delivery_true"] = int(wt[5])
    out["week5_vs_other_mean"] = round(float(wk[5] / wk.drop(5).mean()), 3)
    # よく出る語の上位10（本当の1通目だけで数えた上位10と、何語重なるか）
    def top10(x):
        return set(pd.Series(" ".join(x.text.map(norm)).split()).value_counts().index[:10])
    out["top10_overlap"] = len(top10(d) & top10(orig))
    return out


def run(seed0, reps, hows=HOWS, thr=0.8, **kw):
    rows = []
    for r in range(reps):
        df = make_data(np.random.default_rng(seed0 + r), **kw)
        for h in hows:
            keep = dedup(df, CODE.get(h, h), thr)
            rows.append({"rep": r, "method": h, **measure(df, keep)})
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)
    df = make_data(rng)
    keeps = {h: dedup(df, CODE.get(h, h)) for h in HOWS}
    d = df.copy()
    for h, k in zip(["keep_exact", "keep_normalized", "keep_overlap08", "keep_same_sender08"], HOWS[1:]):
        d[h] = keeps[k].astype(int)
    d["topic"] = d.topic.map(dict(enumerate(TOPICS)))
    d.to_csv(DATA / "inquiries.csv", index=False)
    one = {h: measure(df, keeps[h]) for h in HOWS}
    kinds = df.kind.value_counts().to_dict()
    # お礼の文：本当は別の人なのに同じ文になった数
    th = df[(df.is_copy == 0) & (df.topic == 4)]
    one_extra = {"texts": int(len(df)), "originals": int((df.is_copy == 0).sum()), "copies": int(df.is_copy.sum()),
                 "copy_share_pct": round(float(df.is_copy.mean() * 100), 2), "kinds": {k: int(v) for k, v in kinds.items()},
                 "thanks_originals": int(len(th)), "thanks_distinct_texts": int(th.text.nunique()),
                 "thanks_most_common_text": th.text.value_counts().index[0],
                 "thanks_most_common_count": int(th.text.value_counts().iloc[0])}

    # 基本の置き方で100回
    base = run(SEED * 1000, 100)
    cols = ["n_texts", "count_error_pct", "share_配送", "true_share_配送", "share_お礼", "true_share_お礼",
            "max_abs_share_error_pt", "removed_originals", "removed_thanks_originals", "true_thanks", "left_copies",
            "all_copies", "week5_vs_other_mean", "top10_overlap"]
    bs = base.groupby("method", sort=False)[cols].mean().loc[HOWS].round(3)
    bs["removed_thanks_pct"] = (bs.removed_thanks_originals / bs.true_thanks * 100).round(2)
    bs["left_copies_pct"] = (bs.left_copies / bs.all_copies * 100).round(2)
    bs["copy_share_pct"] = (bs.all_copies / (bs.all_copies + bs.n_texts.iloc[0] - bs.all_copies) * 100).round(2)
    bs["bias_delivery_pt"] = (bs["share_配送"] - bs["true_share_配送"]).round(3) + 0.0
    bs.to_csv(RES / "methods_base.csv")

    # 確かめ：再送の多さ × 話題による再送の差（各30回）
    grid = []
    for mult in [0.5, 1.0, 2.0]:
        for dep in [False, True]:
            g = run(SEED * 100 + int(mult * 10) * 2 + int(dep), 30, resend_mult=mult, topic_dep=dep)
            s = g.groupby("method", sort=False)[["share_配送", "true_share_配送", "max_abs_share_error_pt",
                                                 "count_error_pct", "all_copies", "n_true"]].mean().loc[HOWS]
            for h in HOWS:
                grid.append({"resend_mult": mult, "topic_dependent": dep, "method": h,
                             "copy_share_pct": round(float(s.loc[h, "all_copies"] / (s.loc[h, "all_copies"] + s.loc[h, "n_true"]) * 100), 2),
                             "share_delivery": round(float(s.loc[h, "share_配送"]), 2),
                             "true_share_delivery": round(float(s.loc[h, "true_share_配送"]), 2),
                             "bias_delivery_pt": round(float(s.loc[h, "share_配送"] - s.loc[h, "true_share_配送"]), 2) + 0.0,
                             "max_abs_share_error_pt": round(float(s.loc[h, "max_abs_share_error_pt"]), 2),
                             "count_error_pct": round(float(s.loc[h, "count_error_pct"]), 2)})
    gd = pd.DataFrame(grid); gd.to_csv(RES / "grid_resend.csv", index=False)

    # 確かめ：語の重なりの線（0.6・0.8・0.9、各30回）
    th_rows = []
    for thr in [0.6, 0.8, 0.9]:
        g = run(SEED * 300 + int(thr * 10), 30, hows=["語の重なり0.8以上"], thr=thr)
        s = g[cols].mean()
        th_rows.append({"threshold": thr, "removed_originals": round(float(s.removed_originals), 2),
                        "removed_non_thanks_originals": round(float(s.removed_originals - s.removed_thanks_originals), 2),
                        "removed_thanks_pct": round(float(s.removed_thanks_originals / s.true_thanks * 100), 2),
                        "left_copies_pct": round(float(s.left_copies / s.all_copies * 100), 2),
                        "max_abs_share_error_pt": round(float(s.max_abs_share_error_pt), 2)})
    td = pd.DataFrame(th_rows); td.to_csv(RES / "by_threshold.csv", index=False)

    out = {"setup": {"originals": N_ORIG, "weeks": WEEKS, "share": dict(zip(TOPICS, SHARE.tolist())),
                     "resend_prob": dict(zip(TOPICS, RESEND.tolist())), "copy_kind_prob": P_KIND,
                     "copies_per_resender_mean": round(1 / 0.6, 3), "heavy_paste": HEAVY},
           "one_draw": {**one_extra, "by_method": one}, "base_100reps": bs.reset_index().to_dict("records"),
           "grid_resend": gd.to_dict("records"), "by_threshold": td.to_dict("records"),
           "grid_bias_range": {h: [float(gd[gd.method == h].bias_delivery_pt.min()),
                                   float(gd[gd.method == h].bias_delivery_pt.max())] for h in HOWS}}
    json.dump(out, open(RES / "a965_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：週ごとの「配送」の件数（1回分）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    wks = np.arange(1, WEEKS + 1)
    true_w = df[(df.is_copy == 0) & (df.topic == 0)].week.value_counts().reindex(wks, fill_value=0)
    raw_w = df[df.topic == 0].week.value_counts().reindex(wks, fill_value=0)
    ex_w = df[keeps["完全一致"] & (df.topic == 0)].week.value_counts().reindex(wks, fill_value=0)
    ax.plot(wks, raw_w, marker="o", color=ORANGE, label="除かない")
    ax.plot(wks, ex_w, marker="s", color=BLUE, label="完全一致で除く")
    ax.plot(wks, true_w, marker="o", color=INK, ls="--", lw=1, label="本当の問い合わせ（1人1件）")
    ax.set_xticks(wks); ax.set_xticklabels([f"{w}週目" for w in wks]); ax.set_ylim(0, None)
    ax.set_ylabel("「配送」の件数"); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("1人が同じ文を30回送った週は、除かないと「急増」に見える（1回分）")
    save(fig, "a965_weekly.png", SRC)

    # 図2：除き方ごとの「配送」の割合と、消えた別の人のお礼
    fig, axs = plt.subplots(1, 2, figsize=(8.6, 4.2))
    lab = ["除かない", "完全一致", "空白・記号を\nそろえて一致", "語の重なり\n0.8以上", "同じ送り主で\n語の重なり0.8以上"]
    cl = [ORANGE, LIGHT, LIGHT, LIGHT, BLUE]
    y = np.arange(len(HOWS))[::-1]
    tv = bs["true_share_配送"].iloc[0]
    axs[0].barh(y, bs["share_配送"], color=cl)
    axs[0].axvline(tv, color=INK, ls="--", lw=1)
    axs[0].text(tv + 0.1, len(HOWS) - 0.45, f"本当 {tv:.3f}%", fontsize=8.5)
    for yy, v in zip(y, bs["share_配送"]):
        axs[0].text(v + 0.15, yy, f"{v:.3f}%", va="center", fontsize=8.5)
    axs[0].set_xlim(28, 38); axs[0].set_yticks(y); axs[0].set_yticklabels(lab, fontsize=9.5)
    axs[0].set_xlabel("「配送」の割合（%）"); axs[0].set_title("話題の割合", fontsize=11)
    axs[1].barh(y, bs["removed_thanks_pct"], color=cl)
    for yy, v in zip(y, bs["removed_thanks_pct"]):
        axs[1].text(v + 1, yy, f"{v:.2f}%", va="center", fontsize=8.5)
    axs[1].set_xlim(0, 100); axs[1].set_yticks(y); axs[1].set_yticklabels([])
    axs[1].set_xlabel("別の人のお礼の文を消した割合（%）"); axs[1].set_title("消しすぎ", fontsize=11)
    fig.suptitle("文だけで除くと、短いお礼は別の人の文まで消える（100回の平均）", fontsize=12.5, y=1.0)
    save(fig, "a965_methods.png", SRC)

    # 図3：再送の多さごとの「配送」の割合のずれ
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    for h, c, m in [("除かない", ORANGE, "o"), ("完全一致", LIGHT, "s"), ("空白・記号をそろえて一致", GREEN, "^"),
                    ("語の重なり0.8以上", GRAY, "D"), ("同じ送り主で語の重なり0.8以上", BLUE, "v")]:
        x = gd[(gd.method == h) & gd.topic_dependent]
        ax.plot(x.copy_share_pct, x.bias_delivery_pt, marker=m, color=c, label=h)
    ax.axhline(0, color=INK, lw=.6)
    ax.set_xlabel("問い合わせ全体のうち写しの割合（%、再送の多さを0.5・1・2倍）")
    ax.set_ylabel("「配送」の割合のずれ（ポイント）"); ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("配送の人ほど送り直すと、除かない割合は上にずれる（30回の平均）")
    save(fig, "a965_by_resend.png", SRC)
    print(json.dumps({"one_draw": out["one_draw"], "grid_bias_range": out["grid_bias_range"],
                      "by_threshold": out["by_threshold"]}, ensure_ascii=False, indent=1))
    print(bs.T.to_string())


if __name__ == "__main__":
    main()
