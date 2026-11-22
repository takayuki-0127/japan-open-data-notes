"""957 単語の数え方（区切り方）で、多い言葉の順位は変わるのか？（架空のデータ）

架空の雑貨の通販「A商店」への問い合わせ文を、作成者が決まり文句と語を乱数で組み合わせて作る。
話題ごとの本当の件数の割合は作成者が置く。区切り方の4つの決まり（すべて作成者が決めた簡単な決まり）で
語を数え、多い言葉の上位10語がどれだけ入れかわるかを数える。外部の辞書や解析の道具は使わない。
"""
import json
import re
import time
from collections import Counter
from functools import lru_cache
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 957
SRC = "架空の通販の問い合わせ文（作成者が乱数で語を組み合わせて作成、seed 957）"
N_TEXT = 2000
N_REP = 200
TOP = 10

ITEMS = ["マグカップ", "タオル", "ノート", "トートバッグ", "キャンドル", "手帳", "花瓶", "クッション"]
# 話題：本当の割合と文の型。{品} は品物、{A|B} は A（複合語で書く）か B（分けて書く）を選ぶ
TOPICS = {
    "届かない": (0.22, ["注文した{品}がまだ届きません。", "{配送日|配送の日}を教えてください。",
                        "{配送状況|配送の状況}を確認したいです。"]),
    "配送料": (0.12, ["{配送料|配送の料金}はいくらですか。", "{配送料|配送の料金}が無料になる条件を知りたいです。"]),
    "返品": (0.16, ["{品}を返品したいです。", "返品の{送料|送付の料金}はどちらの負担ですか。",
                    "サイズが合わないので交換できますか。"]),
    "ポイント": (0.12, ["ポイントカードを作りたいです。", "ポイントが付いていません。", "ポイントの期限を知りたいです。"]),
    "支払い": (0.12, ["クレジットカードで払えますか。", "{支払方法|支払いの方法}を変えたいです。"]),
    "ギフト": (0.08, ["ギフトカードは使えますか。", "ギフト用の包装をお願いできますか。"]),
    "在庫": (0.12, ["{品}の在庫はありますか。", "在庫が戻る日を知りたいです。"]),
    "会員登録": (0.06, ["{会員登録|会員の登録}の方法を教えてください。", "{登録メール|登録のメール}が届きません。"]),
}
OPENERS = ["お世話になります。", "初めて注文しました。", "先日{品}を注文しました。"]
CLOSERS = ["よろしくお願いします。", "返信をお待ちしています。"]

# 作成者の語のリスト（内容語）。COMPOUND は複合語で、「短い単位」では使わない
COMPOUND = ["配送日", "配送状況", "配送料", "送料", "ポイントカード", "クレジットカード", "ギフトカード",
            "支払方法", "会員登録", "登録メール", "マグカップ", "トートバッグ"]
BASIC = ["注文", "届き", "配送", "日", "状況", "料金", "料", "送付", "送", "確認", "教え", "知り", "無料", "条件",
         "返品", "負担", "サイズ", "合わ", "交換", "ポイント", "カード", "作り", "付い", "期限", "クレジット",
         "払え", "支払い", "支払", "方法", "変え", "ギフト", "用", "包装", "願い", "使え", "在庫", "戻る",
         "会員", "登録", "メール", "返信", "待ち", "世話", "初めて", "先日", "マグ", "カップ", "タオル",
         "ノート", "トート", "バッグ", "キャンドル", "手帳", "花瓶", "クッション"]
# 数えない語（助詞・語尾など）
FUNC = ["が", "を", "は", "の", "に", "で", "て", "た", "し", "まだ", "ます", "ません", "です", "ください",
        "たい", "いくら", "なる", "どちら", "ので", "ない", "できます", "か", "お", "なり", "しました",
        "した", "して", "います", "い", "あります", "よろしく", "。"]
RULES = ["長い単位", "短い単位", "文字種", "2文字ずつ"]
RULE_NOTE = {"長い単位": "語のリスト（複合語あり）で最長一致", "短い単位": "語のリスト（複合語なし）で最長一致",
             "文字種": "漢字・カタカナの続きを1語", "2文字ずつ": "漢字・カタカナの続きを2文字ずつ"}


def parse(tpl):
    """文の型を、そのままの部分・品物・A|B の選びに分けておく"""
    out = []
    for piece in re.split(r"(\{[^{}]+\})", tpl):
        if not piece:
            continue
        if piece == "{品}":
            out.append(("item",))
        elif piece.startswith("{"):
            out.append(("alt",) + tuple(piece[1:-1].split("|")))
        else:
            out.append(("lit", piece))
    return out


P_TOPICS = {k: [parse(t) for t in v[1]] for k, v in TOPICS.items()}
P_OPEN = [parse(t) for t in OPENERS]
P_CLOSE = [parse(t) for t in CLOSERS]


class Stream:
    """先にまとめて引いた一様乱数を順に使う（速さのため）"""
    def __init__(self, rng, n):
        self.u = rng.random(n).tolist(); self.i = 0

    def __call__(self):
        self.i += 1
        return self.u[self.i - 1]

    def pick(self, k):
        return int(self() * k)


def fill(ptpl, st, q):
    s = []
    for p in ptpl:
        if p[0] == "lit":
            s.append(p[1])
        elif p[0] == "item":
            s.append(ITEMS[st.pick(len(ITEMS))])
        else:
            s.append(p[1] if st() < q else p[2])
    return "".join(s)


def make_texts(rng, n=N_TEXT, q=0.5):
    names = list(TOPICS)
    p = np.array([TOPICS[k][0] for k in names])
    # 話題は重みつきで重ならずに選ぶ（鍵 u^(1/p) の大きい順）
    keys = rng.random((n, len(names))) ** (1 / p)
    order = np.argsort(-keys, axis=1)[:, :2]
    st = Stream(rng, n * 40)
    texts, topics = [], []
    for i in range(n):
        k = 1 if st() < 0.8 else 2
        tp = order[i, :k]
        parts = []
        if st() < 0.5:
            parts.append(fill(P_OPEN[st.pick(len(P_OPEN))], st, q))
        for t in tp:
            tpls = P_TOPICS[names[t]]
            if st() < 0.6:
                js = [st.pick(len(tpls))]
            else:
                a = st.pick(len(tpls)); b = (a + 1 + st.pick(len(tpls) - 1)) % len(tpls)
                js = [a, b]
            for j in js:
                parts.append(fill(tpls[j], st, q))
        if st() < 0.4:
            parts.append(fill(P_CLOSE[st.pick(len(P_CLOSE))], st, q))
        texts.append("".join(parts))
        topics.append("・".join(names[t] for t in tp))
    return texts, topics


def ctype(c):
    if "一" <= c <= "鿿" or c == "々":
        return "K"
    if "゠" <= c <= "ヿ":
        return "T"
    if "぀" <= c <= "ゟ":
        return "H"
    return "O"


LONG_SET = set(COMPOUND + BASIC)
SHORT_SET = set(BASIC)
FUNC_SET = set(FUNC)
MAXLEN = max(len(w) for w in LONG_SET | FUNC_SET)


def longest_match(text, content):
    """左から、リストにある語のうち一番長いものを取る。リストにない文字は1文字ずつ（数えない）"""
    out, i = [], 0
    allw = content | FUNC_SET
    while i < len(text):
        for L in range(min(MAXLEN, len(text) - i), 0, -1):
            w = text[i:i + L]
            if w in allw:
                break
        else:
            L, w = 1, text[i]
        if w in content:
            out.append(w)
        i += L
    return out


def runs(text):
    return [m.group(0) for m in re.finditer(r"[一-鿿々]+|[゠-ヿ]+", text)]


@lru_cache(maxsize=None)
def tokens(text, rule):
    if rule == "長い単位":
        return tuple(longest_match(text, LONG_SET))
    if rule == "短い単位":
        return tuple(longest_match(text, SHORT_SET))
    if rule == "文字種":
        return tuple(runs(text))
    out = []
    for r in runs(text):
        out += [r] if len(r) == 1 else [r[i:i + 2] for i in range(len(r) - 1)]
    return tuple(out)


def count(texts, rule):
    c = Counter()
    for t in texts:
        c.update(tokens(t, rule))
    return c


def top_list(c, k=TOP):
    # 同じ回数は語の文字コード順で並べる（流し直しで同じ順になるように）
    return [w for w, _ in sorted(c.items(), key=lambda x: (-x[1], x[0]))[:k]]


def overlap(a, b):
    return len(set(a) & set(b))


def sim(seed_base, n, q, reps):
    """reps 回作り直し、区切り方どうしと、同じ区切り方で別の文章どうしの上位10語の重なりを数える"""
    pairs = [(a, b) for i, a in enumerate(RULES) for b in RULES[i + 1:]]
    ov = {f"{a}×{b}": [] for a, b in pairs}
    same = {r: [] for r in RULES}
    first = {r: Counter() for r in RULES}
    watch = ["配送", "カード", "ポイント", "日", "届き"]
    ranks = {r: {w: [] for w in watch} for r in RULES}
    prev = None
    for k in range(reps):
        g = np.random.default_rng(seed_base + k)
        texts, _ = make_texts(g, n, q)
        cs = {r: count(texts, r) for r in RULES}
        tops = {r: top_list(cs[r]) for r in RULES}
        for a, b in pairs:
            ov[f"{a}×{b}"].append(overlap(tops[a], tops[b]))
        for r in RULES:
            first[r][tops[r][0]] += 1
            order = {x: i + 1 for i, (x, _) in enumerate(sorted(cs[r].items(), key=lambda x: (-x[1], x[0])))}
            for w in watch:
                ranks[r][w].append(order.get(w, np.nan))
        if prev is not None:
            for r in RULES:
                same[r].append(overlap(tops[r], prev[r]))
        prev = tops
    return ov, same, first, ranks


def main():
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    texts, topics = make_texts(rng)
    pd.DataFrame({"text_id": np.arange(1, len(texts) + 1), "topics": topics, "text": texts}).to_csv(
        DATA / "inquiries.csv", index=False)
    # 話題の本当の件数（1回分）
    tc = Counter()
    for t in topics:
        tc.update(t.split("・"))
    topic_counts = {k: int(tc[k]) for k in TOPICS}

    # 1) 1回分：区切り方ごとの上位10語
    cs = {r: count(texts, r) for r in RULES}
    rows = []
    for r in RULES:
        for i, (w, v) in enumerate(sorted(cs[r].items(), key=lambda x: (-x[1], x[0]))[:TOP]):
            rows.append({"rule": r, "rank": i + 1, "word": w, "count": int(v)})
    one = pd.DataFrame(rows)
    one.to_csv(RES / "top10_one_draw.csv", index=False)
    one_ov = {f"{a}×{b}": overlap(top_list(cs[a]), top_list(cs[b]))
              for i, a in enumerate(RULES) for b in RULES[i + 1:]}
    example = texts[:5]
    example_tokens = {r: [list(tokens(t, r)) for t in example[:3]] for r in RULES}

    # 2) 作り直して200回（基本：2,000件、複合語で書く割合 q=0.5）
    ov, same, first, ranks = sim(SEED * 1000, N_TEXT, 0.5, N_REP)
    ov_mean = {k: round(float(np.mean(v)), 2) for k, v in ov.items()}
    same_mean = {k: round(float(np.mean(v)), 2) for k, v in same.items()}
    first_share = {r: {w: round(c / N_REP, 3) for w, c in first[r].most_common()} for r in RULES}
    rank_med = {r: {w: (None if np.all(np.isnan(v)) else float(np.nanmedian(v))) for w, v in ranks[r].items()}
                for r in RULES}
    pd.DataFrame([{"pair": k, "overlap_mean": v} for k, v in ov_mean.items()] +
                 [{"pair": f"{k}（別の文章どうし）", "overlap_mean": v} for k, v in same_mean.items()]).to_csv(
        RES / "overlap_200reps.csv", index=False)

    # 3) 確かめ：複合語で書く割合 q と件数 n を変える（各100回）
    sens = []
    for n in [200, 2000]:
        for q in [0.2, 0.5, 0.8]:
            o, s, f, _ = sim(SEED * 7000 + int(q * 10) * 100 + n, n, q, 100)
            sens.append({"n_text": n, "q_compound": q,
                         "long_x_short": round(float(np.mean(o["長い単位×短い単位"])), 2),
                         "long_x_chartype": round(float(np.mean(o["長い単位×文字種"])), 2),
                         "long_x_bigram": round(float(np.mean(o["長い単位×2文字ずつ"])), 2),
                         "same_rule_long": round(float(np.mean(s["長い単位"])), 2),
                         "same_rule_short": round(float(np.mean(s["短い単位"])), 2),
                         "first_long": f["長い単位"].most_common(1)[0][0],
                         "first_long_share": round(f["長い単位"].most_common(1)[0][1] / 100, 2),
                         "first_short": f["短い単位"].most_common(1)[0][0],
                         "first_short_share": round(f["短い単位"].most_common(1)[0][1] / 100, 2)})
    sens = pd.DataFrame(sens)
    sens.to_csv(RES / "sensitivity_q_n.csv", index=False)

    out = {"n_text": N_TEXT, "reps": N_REP, "topic_true_share": {k: v[0] for k, v in TOPICS.items()},
           "one_draw_topic_counts": topic_counts, "one_draw_overlap_top10": one_ov,
           "one_draw_top10": {r: one[one.rule == r][["word", "count"]].values.tolist() for r in RULES},
           "example_texts": example, "example_tokens": example_tokens,
           "overlap_top10_mean_200reps": ov_mean, "overlap_top10_same_rule_other_texts": same_mean,
           "first_word_share_200reps": first_share, "median_rank_200reps": rank_med,
           "sensitivity": sens.to_dict("records"), "rule_note": RULE_NOTE}
    json.dump(out, open(RES / "a957_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=lambda x: int(x) if isinstance(x, np.integer) else float(x))

    # 図1：1回分の上位10語（区切り方ごと）
    fig, axes = plt.subplots(1, 4, figsize=(11, 4.4))
    base = set(top_list(cs["長い単位"]))
    for ax, r in zip(axes, RULES):
        d = one[one.rule == r]
        col = [BLUE if w in base else ORANGE for w in d.word]
        ax.barh(d.word[::-1], d["count"][::-1], color=col[::-1])
        for i, v in enumerate(d["count"][::-1]):
            ax.text(v, i, f" {v}", va="center", fontsize=8)
        ax.set_title(f"{r}\n（{RULE_NOTE[r]}）", fontsize=9.5)
        ax.set_xlim(0, d["count"].max() * 1.3); ax.tick_params(axis="x", labelsize=8)
        ax.set_xlabel("出た回数（延べ）", fontsize=8.5)
    fig.suptitle("同じ2,000件でも、区切り方で上位10語が入れかわる（青：長い単位の上位10語にもある語）", fontsize=12)
    fig.tight_layout()
    save(fig, "a957_top10_by_rule.png", SRC)

    # 図2：上位10語の重なり（200回の平均）と、同じ区切り方で別の文章どうしの重なり
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    labs = list(ov_mean) + [f"{r}（別の文章どうし）" for r in RULES]
    vals = list(ov_mean.values()) + list(same_mean.values())
    col = [ORANGE] * len(ov_mean) + [GRAY] * len(same_mean)
    ax.barh(labs[::-1], vals[::-1], color=col[::-1])
    for i, v in enumerate(vals[::-1]):
        ax.text(v + 0.1, i, f"{v:.1f}語", va="center", fontsize=8.5)
    ax.set_xlim(0, 11); ax.set_xlabel("上位10語のうち重なった語の数（200回の平均）")
    ax.tick_params(axis="y", labelsize=8.5)
    ax.set_title("2,000件では、区切り方を変えたときの入れかわりは取り直しより大きい")
    save(fig, "a957_overlap.png", SRC)

    # 図3：確かめ（複合語で書く割合と件数）
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    for n, mk, ls in [(200, "o", "--"), (2000, "s", "-")]:
        d = sens[sens.n_text == n]
        ax.plot(d.q_compound, d.long_x_short, marker=mk, ls=ls, color=ORANGE, label=f"長い単位×短い単位（{n:,}件）")
        ax.plot(d.q_compound, d.same_rule_long, marker=mk, ls=ls, color=GRAY, label=f"長い単位どうし・別の文章（{n:,}件）")
    ax.set_ylim(0, 10.5); ax.set_xticks([0.2, 0.5, 0.8])
    ax.set_xlabel("複合語で書く割合（例：「配送料」と書くか「配送の料金」と書くか）")
    ax.set_ylabel("上位10語の重なり（語、100回の平均）")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    ax.set_title("200件では、複合語が少ないと、取り直すだけでも同じくらい入れかわる")
    save(fig, "a957_sensitivity.png", SRC)
    out["run_sec"] = round(time.time() - t0, 1)
    print(json.dumps({k: out[k] for k in ["one_draw_top10", "overlap_top10_mean_200reps",
                                          "overlap_top10_same_rule_other_texts", "first_word_share_200reps",
                                          "median_rank_200reps", "sensitivity", "one_draw_topic_counts",
                                          "example_tokens", "run_sec"]}, ensure_ascii=False, indent=1,
                     default=lambda x: int(x) if isinstance(x, np.integer) else float(x)))


if __name__ == "__main__":
    main()
