"""966 表記ゆれ（全角・半角・言い換え）をそろえると、数はどれだけ動くのか？（架空のデータ）

架空の店への問い合わせ文。作成者が置いた26の用件（本当の用件）ごとに、同じ用件を表す書き方（表記）を
1〜7通り用意し、乱数で語を選んで短い文を組み立てる。語の区切りは、文を作るときに作成者が記録したものを使う。
そろえ方は (0) そのまま (1) 全角・半角と大文字・小文字をそろえる（Unicode の NFKC と小文字化、Python の標準機能）
(2) かな・送り仮名・記号の書き分けを作成者の表でそろえる (3) 言い換えを作成者の表でそろえる
(4) 広げすぎ：別の用件まで1つにまとめる（作成者の表）。
"""
import json
import unicodedata
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 966
SRC = "架空の店への問い合わせ文（作成者が乱数で語を組み合わせて作成、seed 966）"

# 用件 → 書き方の一覧（先頭がもとの書き方）
VOCAB = {
    "Wi-Fi": ["Wi-Fi", "Ｗｉ－Ｆｉ", "wi-fi", "WiFi", "wifi", "ﾜｲﾌｧｲ", "ワイファイ"],
    "問い合わせ": ["問い合わせ", "問合せ", "問合わせ", "お問い合わせ"],
    "予約": ["予約", "ご予約", "よやく"],
    "返品": ["返品", "へんぴん", "返送"],
    "交換": ["交換", "取り替え", "取替え"],
    "ポイント": ["ポイント", "ﾎﾟｲﾝﾄ", "ぽいんと", "pt"],
    "クーポン": ["クーポン", "ｸｰﾎﾟﾝ", "割引券"],
    "メール": ["メール", "ﾒｰﾙ", "Ｅメール", "Eメール"],
    "アプリ": ["アプリ", "ｱﾌﾟﾘ", "アプリケーション"],
    "ログイン": ["ログイン", "ﾛｸﾞｲﾝ", "サインイン"],
    "パスワード": ["パスワード", "ﾊﾟｽﾜｰﾄﾞ", "PW", "ＰＷ"],
    "キャンセル": ["キャンセル", "ｷｬﾝｾﾙ", "取り消し", "取消し"],
    "送料": ["送料", "配送料"],
    "配送": ["配送", "配達", "お届け"],
    "支払い": ["支払い", "支払", "お支払い", "決済"],
    "駐車場": ["駐車場", "ちゅうしゃじょう", "パーキング"],
    "営業時間": ["営業時間", "開店時間"],
    "在庫": ["在庫", "ざいこ"],
    "サイズ": ["サイズ", "ｻｲｽﾞ", "大きさ"],
    "色": ["色", "いろ", "カラー"],
    "店員": ["店員", "スタッフ", "ｽﾀｯﾌ"],
    "電話": ["電話", "でんわ", "TEL", "ＴＥＬ"],
    "領収書": ["領収書", "領収証"],
    "レシート": ["レシート", "ﾚｼｰﾄ"],
    "住所": ["住所"],
    "会員": ["会員", "メンバー"],
}
# (2) かな・送り仮名・記号の表（(1) のあとの書き方 → そろえた書き方）
TABLE2 = {"wifi": "wi-fi", "ワイファイ": "wi-fi", "問合せ": "問い合わせ", "問合わせ": "問い合わせ",
          "お問い合わせ": "問い合わせ", "ご予約": "予約", "よやく": "予約", "へんぴん": "返品", "取替え": "取り替え",
          "ぽいんと": "ポイント", "eメール": "メール", "アプリケーション": "アプリ", "取消し": "取り消し",
          "支払": "支払い", "お支払い": "支払い", "ちゅうしゃじょう": "駐車場", "ざいこ": "在庫", "いろ": "色",
          "でんわ": "電話"}
# (3) 言い換えの表（(2) のあとの書き方 → 用件）
TABLE3 = {"wi-fi": "Wi-Fi", "返送": "返品", "取り替え": "交換", "pt": "ポイント", "割引券": "クーポン",
          "サインイン": "ログイン", "pw": "パスワード", "取り消し": "キャンセル", "配送料": "送料", "配達": "配送",
          "お届け": "配送", "決済": "支払い", "パーキング": "駐車場", "開店時間": "営業時間", "大きさ": "サイズ",
          "カラー": "色", "スタッフ": "店員", "tel": "電話", "領収証": "領収書", "メンバー": "会員"}
# (4) 広げすぎ：別の用件を1つにまとめる
TABLE4 = {"交換": "返品", "レシート": "領収書", "配送": "送料", "クーポン": "ポイント"}
STAGES = ["(0) そのまま", "(1) 全角・半角と大小をそろえる", "(2) かな・送り仮名もそろえる", "(3) 言い換えもそろえる"]
CONCEPTS = list(VOCAB)
FORMS = [(c, f) for c in CONCEPTS for f in VOCAB[c]]


def s1(f):
    return unicodedata.normalize("NFKC", f).lower()


def key_at(f, st):
    if st == 0:
        return f
    k = s1(f)
    if st >= 2:
        k = TABLE2.get(k, k)
    if st >= 3:
        k = TABLE3.get(k, k)
    if st >= 4:
        k = TABLE4.get(k, k)
    return k


KEYS = {st: np.array([key_at(f, st) for _, f in FORMS]) for st in range(5)}
FORM_CONCEPT = np.array([CONCEPTS.index(c) for c, _ in FORMS])
TEMPL = {1: ["{0}について質問です。", "{0}の件で連絡しました。", "{0}はどうなっていますか。"],
         2: ["{0}と{1}について確認したいです。", "{0}の件と、{1}のことも教えてください。"],
         3: ["{0}、{1}、{2}について知りたいです。"]}


def make_shop(rng, n_text=2000, zipf=1.0, alpha=1.0, base_w=1.0, return_rows=False):
    """1つの店の問い合わせを作る。返り値：書き方ごとの件数、用件ごとの本当の件数、（必要なら）文"""
    K = len(CONCEPTS)
    w = 1 / np.arange(1, K + 1) ** zipf
    w = w[rng.permutation(K)]
    w = w / w.sum()
    share = []
    for c in CONCEPTS:
        a = np.full(len(VOCAB[c]), alpha)
        a[0] *= base_w
        share.append(rng.dirichlet(a) if len(a) > 1 else np.array([1.0]))
    n_m = rng.integers(1, 4, n_text)
    offs = np.cumsum([0] + [len(VOCAB[c]) for c in CONCEPTS])
    # 1文の中で同じ用件は1回まで：重みつきで重ならずに引く（ガンベルの方法）
    g = np.log(w)[None, :] + rng.gumbel(size=(n_text, K))
    order = np.argsort(-g, axis=1, kind="stable")[:, :3]
    mask = np.arange(3)[None, :] < n_m[:, None]
    cs_all = order[mask]
    cum = [np.cumsum(s) for s in share]
    u = rng.random(len(cs_all))
    fi_all = np.array([offs[c] + min(int(np.searchsorted(cum[c], x, side="right")), len(cum[c]) - 1)
                       for c, x in zip(cs_all, u)])
    form_count = np.bincount(fi_all, minlength=len(FORMS))
    rows = []
    if return_rows:
        pos = np.concatenate([[0], np.cumsum(n_m)])
        rows = [(cs_all[pos[t]:pos[t + 1]], fi_all[pos[t]:pos[t + 1]]) for t in range(n_text)]
    true = np.bincount(FORM_CONCEPT, weights=form_count, minlength=K)
    return form_count, true, w, share, rows


def stage_table(form_count, st):
    s = pd.Series(form_count, index=KEYS[st]).groupby(level=0).sum()
    return s[s > 0].sort_values(ascending=False, kind="stable")


def key_concepts(st):
    """そろえ方 st の書き方 → 含まれる用件の集まり"""
    d = {}
    for k, c in zip(KEYS[st], FORM_CONCEPT):
        d.setdefault(k, set()).add(c)
    return d


KC = {st: key_concepts(st) for st in range(5)}


def evaluate(form_count, true, k=10):
    top_true = set(np.argsort(-true, kind="stable")[:k])
    out = {}
    for st in range(4):
        tab = stage_table(form_count, st)
        top = tab.index[:k]
        cov = set().union(*[KC[st][x] for x in top])
        # 用件ごとの「いちばん多い書き方の件数」÷本当の件数
        best = np.zeros(len(CONCEPTS))
        for x, v in tab.items():
            for c in KC[st][x]:
                best[c] = max(best[c], v)
        ratio = best / np.maximum(true, 1)
        # 用件の順位（いちばん多い書き方で並べたとき）と本当の順位
        rank_seen = pd.Series(best).rank(ascending=False, method="min").values
        rank_true = pd.Series(true).rank(ascending=False, method="min").values
        out[st] = {"types": int(len(tab)), "top10_concepts_distinct": len(cov),
                   "top10_overlap": len(cov & top_true), "median_ratio": float(np.median(ratio)),
                   "min_ratio": float(ratio.min()),
                   "mean_abs_rank_shift": float(np.mean(np.abs(rank_seen - rank_true))),
                   "top1_correct": bool(set(KC[st][tab.index[0]]) == {int(np.argmax(true))})}
    return out


def main():
    rng = np.random.default_rng(SEED)
    # 作りの確かめ：(3) までそろえると、どの書き方も自分の用件1つに戻る。(1) は NFKC と小文字化だけで動く
    for st in range(4):
        assert all(len(v) == 1 for v in KC[st].values())
    assert len(set(KEYS[3])) == len(CONCEPTS)
    n_merge1 = int(sum(KEYS[1][i] != KEYS[0][i].lower() for i in range(len(FORMS))))

    # 1) 例の店1つ
    fc, true, w, share, rows = make_shop(rng, return_rows=True)
    recs = []
    for t, (cs, fi) in enumerate(rows):
        words = [FORMS[i][1] for i in fi]
        text = TEMPL[len(words)][rng.integers(len(TEMPL[len(words)]))].format(*words)
        recs.append({"text_id": t + 1, "text": text, "words": "|".join(words),
                     "true_concepts": "|".join(CONCEPTS[c] for c in cs)})
    pd.DataFrame(recs).to_csv(DATA / "inquiries_example.csv", index=False)
    voc = pd.DataFrame({"concept": [c for c, _ in FORMS], "form": [f for _, f in FORMS],
                        "key1": KEYS[1], "key2": KEYS[2], "key3": KEYS[3], "key4_overmerge": KEYS[4],
                        "count_example": fc})
    voc.to_csv(DATA / "vocab_forms.csv", index=False)
    ex_eval = evaluate(fc, true)
    ex_tabs = {st: stage_table(fc, st) for st in range(5)}
    for st in range(4):
        t = ex_tabs[st].head(15).reset_index()
        t.columns = ["word", "count"]
        t.to_csv(RES / f"example_top15_stage{st}.csv", index=False)
    true_s = pd.Series(true.astype(int), index=CONCEPTS).sort_values(ascending=False, kind="stable")
    wifi = int(true[CONCEPTS.index("Wi-Fi")])
    wifi_rank_true = int(true_s.index.get_loc("Wi-Fi") + 1)
    ex_rank = {}
    for st in range(4):
        tab = ex_tabs[st]
        keys_w = [k for k in tab.index if CONCEPTS.index("Wi-Fi") in KC[st][k]]
        ex_rank[STAGES[st]] = {"wifi_top_form": keys_w[0], "wifi_top_form_count": int(tab[keys_w[0]]),
                               "wifi_top_form_rank": int(list(tab.index).index(keys_w[0]) + 1)}

    # 2) 店を作り直して500回（基本の置き方）
    reps = []
    over = []
    for r in range(500):
        g = np.random.default_rng(SEED * 1000 + r)
        fc_r, tr_r, *_ = make_shop(g)
        ev = evaluate(fc_r, tr_r)
        for st in range(4):
            reps.append({"rep": r, "stage": STAGES[st], **ev[st]})
        # 広げすぎ
        t4 = stage_table(fc_r, 4)
        rank_true = pd.Series(tr_r).rank(ascending=False, method="min").values
        for a, b in TABLE4.items():
            ia, ib = CONCEPTS.index(a), CONCEPTS.index(b)
            over.append({"rep": r, "pair": f"{b}＋{a}", "merged": int(t4[b]),
                         "larger_true": int(max(tr_r[ia], tr_r[ib])),
                         "merged_rank": int(list(t4.index).index(b) + 1),
                         "best_member_true_rank": int(min(rank_true[ia], rank_true[ib]))})
    rep = pd.DataFrame(reps)
    summ = rep.groupby("stage", sort=False).agg(
        types=("types", "mean"), top10_overlap=("top10_overlap", "mean"),
        top10_overlap_p10=("top10_overlap", lambda x: x.quantile(.1)),
        top10_overlap_p90=("top10_overlap", lambda x: x.quantile(.9)),
        top10_concepts_distinct=("top10_concepts_distinct", "mean"),
        median_ratio=("median_ratio", "mean"), min_ratio=("min_ratio", "mean"),
        mean_abs_rank_shift=("mean_abs_rank_shift", "mean"), top1_correct=("top1_correct", "mean")).round(3)
    summ.to_csv(RES / "by_stage_500reps.csv")
    ov = pd.DataFrame(over)
    ov["ratio"] = ov.merged / ov.larger_true
    ov["rank_up"] = ov.merged_rank < ov.best_member_true_rank
    ovs = ov.groupby("pair", sort=False).agg(ratio=("ratio", "mean"), rank_up=("rank_up", "mean"),
                                             merged_rank=("merged_rank", "median"),
                                             best_member_true_rank=("best_member_true_rank", "median")).round(3)
    ovs.to_csv(RES / "overmerge_500reps.csv")

    # 3) 確かめ：書き方の散り方（alpha）× 用件の偏り（zipf）、もとの書き方の重み
    grid = []
    for zi in [0.7, 1.0, 1.3]:
        for al in [0.3, 1.0, 3.0]:
            ee = []
            for r in range(100):
                g = np.random.default_rng(SEED * 7 + r + int(zi * 1000) + int(al * 10))
                fc_r, tr_r, *_ = make_shop(g, zipf=zi, alpha=al)
                ee.append(evaluate(fc_r, tr_r))
            grid.append({"zipf": zi, "alpha": al,
                         **{f"overlap_stage{st}": round(float(np.mean([e[st]["top10_overlap"] for e in ee])), 3)
                            for st in range(4)},
                         **{f"median_ratio_stage{st}": round(float(np.mean([e[st]["median_ratio"] for e in ee])), 3)
                            for st in range(3)}})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_zipf_alpha.csv", index=False)
    bw = []
    for b in [1.0, 3.0, 10.0]:
        ee = []
        for r in range(100):
            g = np.random.default_rng(SEED * 11 + r + int(b * 100))
            fc_r, tr_r, *_ = make_shop(g, base_w=b)
            ee.append(evaluate(fc_r, tr_r))
        bw.append({"base_weight": b,
                   **{f"overlap_stage{st}": round(float(np.mean([e[st]["top10_overlap"] for e in ee])), 3)
                      for st in range(4)},
                   **{f"median_ratio_stage{st}": round(float(np.mean([e[st]["median_ratio"] for e in ee])), 3)
                      for st in range(3)}})
    bw = pd.DataFrame(bw)
    bw.to_csv(RES / "by_base_weight.csv", index=False)

    n_forms_by_concept = {c: len(v) for c, v in VOCAB.items()}
    out = {"n_concepts": len(CONCEPTS), "n_forms": len(FORMS), "n_forms_changed_by_nfkc_lower": n_merge1,
           "forms_by_concept": n_forms_by_concept,
           "example": {"n_text": 2000, "n_mentions": int(fc.sum()),
                       "types_by_stage": {(STAGES + ["(4) 広げすぎ"])[st]: int(len(ex_tabs[st])) for st in range(5)},
                       "eval": {STAGES[st]: ex_eval[st] for st in range(4)},
                       "wifi_true_count": wifi, "wifi_true_rank": wifi_rank_true, "wifi_by_stage": ex_rank,
                       "true_top10": {k: int(v) for k, v in true_s.head(10).items()}},
           "by_stage_500reps": summ.reset_index().to_dict("records"),
           "overmerge_500reps": ovs.reset_index().to_dict("records"),
           "grid_overlap_range": {f"stage{st}": [float(grid[f"overlap_stage{st}"].min()),
                                                 float(grid[f"overlap_stage{st}"].max())] for st in range(4)},
           "grid_median_ratio_range": {f"stage{st}": [float(grid[f"median_ratio_stage{st}"].min()),
                                                      float(grid[f"median_ratio_stage{st}"].max())]
                                       for st in range(3)},
           "robust_12_settings_overlap_range": {f"stage{st}": [float(min(grid[f"overlap_stage{st}"].min(), bw[f"overlap_stage{st}"].min())),
                                                               float(max(grid[f"overlap_stage{st}"].max(), bw[f"overlap_stage{st}"].max()))]
                                                for st in range(4)},
           "robust_12_settings_stage1_minus_stage0": [round(float(min((grid.overlap_stage1 - grid.overlap_stage0).min(), (bw.overlap_stage1 - bw.overlap_stage0).min())), 3),
                                                      round(float(max((grid.overlap_stage1 - grid.overlap_stage0).max(), (bw.overlap_stage1 - bw.overlap_stage0).max())), 3)],
           "robust_12_settings_order_0_lt_1_lt_2": bool(all(grid.overlap_stage0 < grid.overlap_stage1) and all(grid.overlap_stage1 < grid.overlap_stage2)
                                                        and all(bw.overlap_stage0 < bw.overlap_stage1) and all(bw.overlap_stage1 < bw.overlap_stage2))}
    json.dump(out, open(RES / "a966_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：例の店の上位15語（そのまま と 言い換えまでそろえた）
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 5.0))
    for ax, st, col in [(axes[0], 0, GRAY), (axes[1], 3, BLUE)]:
        t = ex_tabs[st].head(15)
        lab = [k for k in t.index]
        cols = [ORANGE if CONCEPTS.index("Wi-Fi") in KC[st][k] else col for k in t.index]
        ax.barh(range(len(t))[::-1], t.values, color=cols)
        ax.set_yticks(range(len(t))[::-1]); ax.set_yticklabels(lab, fontsize=9)
        for i, v in zip(range(len(t))[::-1], t.values):
            ax.text(v + 5, i, f"{v}", va="center", fontsize=8)
        ax.set_xlabel("件数"); ax.set_title(STAGES[st], fontsize=11)
        ax.set_xlim(0, ex_tabs[3].max() * 1.15)
    fig.suptitle("同じ問い合わせ2,000件でも、そろえ方で上位の語が変わる（橙はWi-Fiの書き方）", fontsize=12)
    fig.tight_layout()
    save(fig, "a966_example_top15.png", SRC)

    # 図2：そろえ方ごとの上位10語の当たり（500回の平均と10〜90%）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    s = summ.reset_index()
    y = np.arange(4)[::-1]
    ax.barh(y, s.top10_overlap, color=[GRAY, LIGHT, LIGHT, BLUE])
    ax.errorbar(s.top10_overlap, y, xerr=[np.maximum(s.top10_overlap - s.top10_overlap_p10, 0), np.maximum(s.top10_overlap_p90 - s.top10_overlap, 0)],
                fmt="none", ecolor=INK, lw=1, capsize=3)
    for yi, v in zip(y, s.top10_overlap):
        ax.text(0.15, yi, f"{v:.1f}", va="center", fontsize=9, color="white" if v > 1 else INK)
    ax.set_yticks(y); ax.set_yticklabels(s.stage, fontsize=9)
    ax.set_xlim(0, 10.5); ax.set_xlabel("上位10語に入った、本当の上位10の用件の数（500回の平均、線は10〜90%）")
    ax.set_title(f"そのまま数えた上位10語に出た本当の上位10の用件は、平均{s.top10_overlap[0]:.1f}個")
    save(fig, "a966_top10_overlap.png", SRC, y=-0.07)

    # 図3：確かめ（散り方×偏りの9通り）
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    xs = np.arange(len(grid))
    for st, col, mk in [(0, GRAY, "o"), (1, LIGHT, "s"), (2, BLUE, "^"), (3, INK, "D")]:
        ax.plot(xs, grid[f"overlap_stage{st}"], marker=mk, color=col, lw=1.2, label=STAGES[st])
    ax.set_xticks(xs); ax.set_xticklabels([f"偏り{z}\n散り{a}" for z, a in zip(grid.zipf, grid.alpha)], fontsize=7.5)
    ax.set_ylim(0, 10.5); ax.set_ylabel("本当の上位10の用件の数（100回の平均）")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    assert all(grid.overlap_stage0 < grid.overlap_stage1) and all(grid.overlap_stage1 < grid.overlap_stage2)
    ax.set_title("置き方を変えても、そのままの数え方がいちばん外れた（9通り）")
    save(fig, "a966_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:6000])


if __name__ == "__main__":
    main()
