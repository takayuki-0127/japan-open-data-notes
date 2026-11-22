"""967 問い合わせの件名だけで分けると、本文と比べて何がずれるのか？（架空のデータ）

架空の店への問い合わせ（件名と本文）。作成者が本当の用件（6分類）を置き、件名と本文を、作成者が作った
言葉の一覧から乱数で語を選んで組み立てる。分け方は、作成者が作った「言葉→分類」の一覧で
(A) 件名だけ：件名で最初に見つかった言葉の分類、(B) 本文：本文でいちばん多く見つかった分類（同数なら先に出た方）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 967
SRC = "架空の店への問い合わせ（作成者が乱数で語を組み合わせて作成、seed 967）"
CATS = ["配送", "返品・交換", "支払い", "会員・ログイン", "商品の質問", "不満・要望"]
NC = len(CATS)
COMPLAINT = 5
TOPICAL = np.arange(5)
SHARE = np.array([0.22, 0.16, 0.14, 0.14, 0.20, 0.14])
KW = {0: ["配送", "未着", "発送", "到着", "配達"], 1: ["返品", "交換", "返金", "返送"],
      2: ["支払い", "決済", "請求", "振込"], 3: ["ログイン", "パスワード", "会員登録", "退会"],
      4: ["サイズ", "在庫", "素材", "使い方"], 5: ["対応", "改善", "不満", "要望", "苦情"]}
PARA = {0: "荷物がまだ来ていません。", 1: "商品を送り返したいです。", 2: "お金の払い方を知りたいです。",
        3: "マイページに入れません。", 4: "大きめか小さめか知りたいです。", 5: "とてもがっかりしました。"}
SUBJ_SPEC = ["{0}について", "{0}の件", "【{0}】"]
SUBJ_TWO = "{0}と{1}について"
SUBJ_GEN = ["お問い合わせ", "質問です", "（件名なし）", "至急", "ご確認ください", "注文について"]
S_MAIN = ["{0}について確認したいです。", "{0}の件で連絡しました。", "{0}のことで困っています。"]
S_COMP = {"対応": "店の対応がよくなかったです。", "改善": "改善してほしいです。", "不満": "不満があります。",
          "要望": "要望があります。", "苦情": "苦情を伝えたいです。"}
S_SECOND = ["あと、{0}についても教えてください。", "それから{0}のことも知りたいです。"]
S_INC = ["前回の{0}は問題ありませんでした。", "{0}の件は前に解決しました。"]
S_TROUBLE = ["{0}の件です。", "先日の{0}についてです。"]
FILLER_HEAD = ["いつも利用しています。", "先週注文しました。"]
FILLER_TAIL = ["よろしくお願いします。", "お手数ですがお願いします。"]
FILLER = FILLER_HEAD + FILLER_TAIL
P = dict(g0=0.25, tilt=1.6, mis_other=0.05, mis_comp=0.35, p_second=0.25, p_trouble=0.7, p_two_subj=0.2,
         p_miss=0.1, p_inc=0.2)
SLOTS = ["inc_first", "trouble", "main1", "main2", "second", "inc_last"]


def simulate(rng, n=2000, **kw):
    p = {**P, **kw}
    c = rng.choice(NC, n, p=SHARE)
    comp = c == COMPLAINT
    # 2つめの用件（不満・要望なら、もとになった困りごとの分類）
    oth = (c + rng.integers(1, 5, n)) % 5          # 主の用件以外の話題の分類（不満のときは0〜4のどれか）
    oth = np.where(comp, rng.integers(0, 5, n), oth)
    has2 = np.where(comp, rng.random(n) < p["p_trouble"], rng.random(n) < p["p_second"])
    sec = np.where(has2, oth, -1)
    # 件名
    g = np.where(comp, min(p["g0"] * p["tilt"], 0.95), p["g0"])
    mis = np.where(comp, p["mis_comp"], p["mis_other"])
    u = rng.random(n)
    stype = np.where(u < g, 0, np.where(u < g + mis, 1, 2))  # 0 一般的 1 別の話題 2 主の用件
    rand_other = (c + rng.integers(1, NC, n)) % NC
    rand_other = np.where(comp, rng.integers(0, 5, n), rand_other)
    s1 = np.where(stype == 2, c, np.where(stype == 1, np.where(sec >= 0, sec, rand_other), -1))
    two = (stype == 2) & (sec >= 0) & (rng.random(n) < p["p_two_subj"])
    s2 = np.where(two, sec, -1)
    # 本文の言葉の並び（スロットごとの分類、-1 は言葉なし）
    slots = np.full((n, 6), -1)
    inc = rng.random(n) < p["p_inc"]
    inc_cat = rng.integers(0, 5, n)
    inc_cat = np.where(inc_cat == c, (inc_cat + 1) % 5, inc_cat)
    inc_first = rng.random(n) < 0.5
    slots[:, 0] = np.where(inc & inc_first, inc_cat, -1)
    miss = rng.random((n, 4)) < p["p_miss"]
    slots[:, 1] = np.where(comp & (sec >= 0) & ~miss[:, 0], sec, -1)
    k2 = rng.random(n) < 0.5                       # 主の用件の文が2文か
    slots[:, 2] = np.where(~miss[:, 1], c, -1)
    slots[:, 3] = np.where(k2 & ~miss[:, 2], c, -1)
    slots[:, 4] = np.where(~comp & (sec >= 0) & ~miss[:, 3], sec, -1)
    slots[:, 5] = np.where(inc & ~inc_first, inc_cat, -1)
    present = np.stack([(slots == k).any(1) for k in range(NC)], 1)
    counts = np.stack([(slots == k).sum(1) for k in range(NC)], 1)
    first = np.stack([np.where((slots == k).any(1), np.argmax(slots == k, 1), 99) for k in range(NC)], 1)
    score = counts * 100 - first
    body = np.where(counts.max(1) > 0, np.argmax(score, 1), -1)
    # 本当の話題（主＋2つめ）と、件名・本文に出た分類
    true_topics = np.zeros((n, NC), bool)
    true_topics[np.arange(n), c] = True
    true_topics[np.arange(n)[sec >= 0], sec[sec >= 0]] = True
    subj_topics = np.zeros((n, NC), bool)
    subj_topics[np.arange(n)[s1 >= 0], s1[s1 >= 0]] = True
    subj_topics[np.arange(n)[s2 >= 0], s2[s2 >= 0]] = True
    return dict(c=c, sec=sec, stype=stype, s1=s1, s2=s2, slots=slots, subj=s1, body=body, inc=inc,
                inc_cat=inc_cat, k2=k2, true_topics=true_topics, subj_topics=subj_topics, body_topics=present)


def metrics(d):
    n = len(d["c"])
    c, subj, body = d["c"], d["subj"], d["body"]
    out = {"acc_subject": float((subj == c).mean()), "acc_body": float((body == c).mean()),
           "unclassified_subject": float((subj < 0).mean()), "unclassified_body": float((body < 0).mean())}
    for k in range(NC):
        out[f"true_{k}"] = float((c == k).mean())
        out[f"subj_{k}"] = float((subj == k).mean())
        out[f"body_{k}"] = float((body == k).mean())
        cl = subj >= 0
        out[f"subj_cl_{k}"] = float((subj[cl] == k).mean())
        out[f"recall_subj_{k}"] = float((subj[c == k] == k).mean())
        out[f"recall_body_{k}"] = float((body[c == k] == k).mean())
    # 2つめの用件を拾えたか
    has2 = d["sec"] >= 0
    i = np.arange(n)[has2]
    out["second_share"] = float(has2.mean())
    out["second_found_subject"] = float(d["subj_topics"][i, d["sec"][has2]].mean())
    out["second_found_body"] = float(d["body_topics"][i, d["sec"][has2]].mean())
    extra = d["body_topics"] & ~d["true_topics"]
    out["body_false_topic_share"] = float(extra.any(1).mean())
    out["subj_false_topic_share"] = float((d["subj_topics"] & ~d["true_topics"]).any(1).mean())
    return out


def render(d, rng):
    """例の文を作り、文から言葉を探し直して、並びが作ったものと同じかを確かめる"""
    allkw = [(w, k) for k, ws in KW.items() for w in ws]
    for t in SUBJ_SPEC + [SUBJ_TWO] + SUBJ_GEN + S_MAIN + S_SECOND + S_INC + S_TROUBLE + FILLER + list(PARA.values()):
        t = t.replace("{0}", "").replace("{1}", "")
        assert not any(w in t for w, _ in allkw), t
    for w, k in allkw:
        assert sum(w2 in w for w2, _ in allkw) == 1, w
    rows = []
    for j in range(len(d["c"])):
        pick = lambda lst: lst[rng.integers(len(lst))]
        kw = lambda k: pick(KW[k])
        s1, s2 = d["s1"][j], d["s2"][j]
        if s1 < 0:
            subject = pick(SUBJ_GEN)
        elif s2 >= 0:
            subject = SUBJ_TWO.format(kw(s1), kw(s2))
        else:
            subject = pick(SUBJ_SPEC).format(kw(s1))
        sl = d["slots"][j]
        sent = []
        if rng.random() < 0.6:
            sent.append(pick(FILLER_HEAD))
        c, sec = d["c"][j], d["sec"][j]
        main_t = int(rng.integers(len(S_MAIN)))
        main_w = int(rng.integers(len(KW[COMPLAINT])))
        for si, name in enumerate(SLOTS):
            k = sl[si]
            if name == "inc_first" and k >= 0:
                sent.append(pick(S_INC).format(kw(k)))
            elif name == "trouble":
                if k >= 0:
                    sent.append(pick(S_TROUBLE).format(kw(k)))
                elif c == COMPLAINT and sec >= 0:
                    sent.append(PARA[sec])
            elif name in ("main1", "main2"):
                if k >= 0:
                    if k == COMPLAINT:
                        ws = KW[k][(main_w + (name == "main2")) % len(KW[k])]
                        sent.append(S_COMP[ws])
                    else:
                        tm = S_MAIN[(main_t + (name == "main2")) % len(S_MAIN)]
                        sent.append(tm.format(kw(k)))
                elif name == "main1" or d["k2"][j]:
                    sent.append(PARA[c])
            elif name == "second":
                if k >= 0:
                    sent.append(pick(S_SECOND).format(kw(k)))
                elif c != COMPLAINT and sec >= 0:
                    sent.append(PARA[sec])
            elif name == "inc_last" and k >= 0:
                sent.append(pick(S_INC).format(kw(k)))
        if rng.random() < 0.5:
            sent.append(pick(FILLER_TAIL))
        text = "".join(sent)
        # 文から言葉を探し直す
        def find(s):
            hits = sorted((s.find(w), k) for w, k in allkw if w in s)
            return [k for _, k in hits]
        assert all(sum(s.count(w) for w, _ in allkw) <= 1 for s in sent)
        bseq = [k for k in sl if k >= 0]
        assert [k for snt in sent for k in find(snt)] == bseq, (text, bseq)
        assert text.count("。") == len(sent)
        fs = find(subject)
        assert (fs[0] if fs else -1) == s1
        rows.append({"id": j + 1, "subject": subject, "body": text, "true_main": CATS[c],
                     "true_second": CATS[sec] if sec >= 0 else "",
                     "by_subject": CATS[s1] if s1 >= 0 else "分類できない",
                     "by_body": CATS[d["body"][j]] if d["body"][j] >= 0 else "分類できない"})
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)
    ex = simulate(rng)
    df = render(ex, np.random.default_rng(SEED + 1))
    df.to_csv(DATA / "inquiries_example.csv", index=False)
    ex_m = metrics(ex)

    # 基本：300回
    reps = pd.DataFrame([metrics(simulate(np.random.default_rng(SEED * 1000 + r))) for r in range(300)])
    base = reps.mean().round(4)
    p10 = reps.quantile(.1).round(4)
    p90 = reps.quantile(.9).round(4)
    share_tab = pd.DataFrame({"category": CATS,
                              "true": [base[f"true_{k}"] for k in range(NC)],
                              "subject": [base[f"subj_{k}"] for k in range(NC)],
                              "subject_classified_only": [base[f"subj_cl_{k}"] for k in range(NC)],
                              "body": [base[f"body_{k}"] for k in range(NC)],
                              "recall_subject": [base[f"recall_subj_{k}"] for k in range(NC)],
                              "recall_body": [base[f"recall_body_{k}"] for k in range(NC)]})
    share_tab.to_csv(RES / "shares_by_category_300reps.csv", index=False)
    # 件名と本文の食い違いの表（例の1回）
    conf = pd.crosstab(df.true_main, df.by_subject).reindex(index=CATS, columns=CATS + ["分類できない"], fill_value=0)
    conf.to_csv(RES / "example_true_vs_subject.csv")

    # 確かめ1：一般的な件名の率 × 不満・要望での偏り（9通り）
    grid = []
    for g0 in [0.1, 0.25, 0.4]:
        for tilt in [1.0, 1.6, 2.5]:
            m = pd.DataFrame([metrics(simulate(np.random.default_rng(SEED * 7 + r + int(g0 * 1000) + int(tilt * 10)),
                                               g0=g0, tilt=tilt)) for r in range(100)]).mean()
            grid.append({"g0": g0, "tilt": tilt, "complaint_true": round(m["true_5"], 4),
                         "complaint_subject": round(m["subj_5"], 4), "complaint_subject_cl": round(m["subj_cl_5"], 4),
                         "complaint_body": round(m["body_5"], 4), "unclassified_subject": round(m["unclassified_subject"], 4),
                         "acc_subject": round(m["acc_subject"], 4), "acc_body": round(m["acc_body"], 4)})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_generic_tilt.csv", index=False)
    # 確かめ2：不満・要望で件名に別の話題を書く率
    mis = []
    for mc in [0.05, 0.35, 0.6]:
        m = pd.DataFrame([metrics(simulate(np.random.default_rng(SEED * 11 + r + int(mc * 100)), mis_comp=mc))
                          for r in range(100)]).mean()
        mis.append({"mis_comp": mc, "complaint_subject": round(m["subj_5"], 4),
                    "complaint_subject_cl": round(m["subj_cl_5"], 4), "complaint_body": round(m["body_5"], 4),
                    "recall_subject_complaint": round(m["recall_subj_5"], 4), "acc_subject": round(m["acc_subject"], 4)})
    mis = pd.DataFrame(mis)
    mis.to_csv(RES / "by_complaint_subject_other_topic.csv", index=False)
    # 確かめ2b：不満・要望の本文で、もとになった困りごとの話題にふれる率
    trb = []
    for pt in [0.3, 0.7, 1.0]:
        m = pd.DataFrame([metrics(simulate(np.random.default_rng(SEED * 17 + r + int(pt * 100)), p_trouble=pt))
                          for r in range(100)]).mean()
        trb.append({"p_trouble": pt, "complaint_true": round(m["true_5"], 4), "complaint_body": round(m["body_5"], 4),
                    "recall_body_complaint": round(m["recall_body_5"], 4), "complaint_subject": round(m["subj_5"], 4),
                    "acc_body": round(m["acc_body"], 4)})
    trb = pd.DataFrame(trb)
    trb.to_csv(RES / "by_complaint_trouble_mention.csv", index=False)
    # 確かめ3：分類による差がないとき（tilt=1・別の話題の率も同じ）→ 分けられた件の中の割合は本当とそろうか
    eq = pd.DataFrame([metrics(simulate(np.random.default_rng(SEED * 13 + r), tilt=1.0, mis_comp=0.05))
                       for r in range(100)]).mean()
    equal = {"complaint_true": round(eq["true_5"], 4), "complaint_subject_cl": round(eq["subj_cl_5"], 4),
             "max_abs_gap_classified_only": round(float(max(abs(eq[f"subj_cl_{k}"] - eq[f"true_{k}"]) for k in range(NC))), 4),
             "unclassified_subject": round(eq["unclassified_subject"], 4)}

    keys = ["acc_subject", "acc_body", "unclassified_subject", "unclassified_body", "second_share",
            "second_found_subject", "second_found_body", "body_false_topic_share", "subj_false_topic_share"]
    out = {"categories": CATS, "params": P, "generic_rate_cap": 0.95, "n_per_rep": 2000,
           "base_300reps": {k: float(base[k]) for k in keys},
           "base_300reps_p10_p90": {k: [float(p10[k]), float(p90[k])] for k in keys + ["subj_5", "body_5"]},
           "shares_300reps": share_tab.to_dict("records"),
           "example": {k: round(v, 4) for k, v in ex_m.items() if not k.startswith(("recall", "subj_cl"))},
           "grid_complaint_subject_range": [float(grid.complaint_subject.min()), float(grid.complaint_subject.max())],
           "grid_complaint_subject_cl_range": [float(grid.complaint_subject_cl.min()), float(grid.complaint_subject_cl.max())],
           "grid_complaint_body_range": [float(grid.complaint_body.min()), float(grid.complaint_body.max())],
           "grid_acc_subject_range": [float(grid.acc_subject.min()), float(grid.acc_subject.max())],
           "grid_acc_body_range": [float(grid.acc_body.min()), float(grid.acc_body.max())],
           "grid_unclassified_subject_range": [float(grid.unclassified_subject.min()), float(grid.unclassified_subject.max())],
           "all12_complaint_subject_range": [float(min(grid.complaint_subject.min(), mis.complaint_subject.min())),
                                             float(max(grid.complaint_subject.max(), mis.complaint_subject.max()))],
           "equal_case": equal,
           "trouble_complaint_body_range": [float(trb.complaint_body.min()), float(trb.complaint_body.max())]}
    json.dump(out, open(RES / "a967_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：分類ごとの割合（本当・件名・本文）
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    x = np.arange(NC + 1)
    tr = list(share_tab.true) + [0]
    sb = list(share_tab.subject) + [base["unclassified_subject"]]
    bd = list(share_tab.body) + [base["unclassified_body"]]
    wdt = 0.27
    ax.bar(x - wdt, np.array(tr) * 100, wdt, color=INK, label="本当の用件")
    ax.bar(x, np.array(sb) * 100, wdt, color=ORANGE, label="件名だけで分けた")
    ax.bar(x + wdt, np.array(bd) * 100, wdt, color=BLUE, label="本文で分けた")
    for xi, v in zip(x, sb):
        ax.text(xi, v * 100 + 0.5, f"{v*100:.1f}", ha="center", fontsize=7.5, color=ORANGE)
    ax.set_xticks(x); ax.set_xticklabels(CATS + ["分類できない"], fontsize=9)
    ax.set_ylabel("全体に占める割合（%、300回の平均）")
    ax.legend(frameon=False, fontsize=9)
    ax.set_title(f"件名だけで分けると、不満・要望は{base['subj_5']*100:.1f}%（本当は{base['true_5']*100:.1f}%）")
    save(fig, "a967_shares.png", SRC)

    # 図2：分類ごとの当たり（件名・本文）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    y = np.arange(NC)[::-1]
    ax.barh(y + 0.2, share_tab.recall_subject * 100, 0.4, color=ORANGE, label="件名だけ")
    ax.barh(y - 0.2, share_tab.recall_body * 100, 0.4, color=BLUE, label="本文")
    for yi, a, b in zip(y, share_tab.recall_subject, share_tab.recall_body):
        ax.text(a * 100 + 1, yi + 0.2, f"{a*100:.1f}%", va="center", fontsize=8)
        ax.text(b * 100 + 1, yi - 0.2, f"{b*100:.1f}%", va="center", fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels(CATS)
    ax.set_xlim(0, 110); ax.set_xlabel("本当の用件どおりに分けられた割合（%、300回の平均）")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_title("件名だけでは、不満・要望の当たりがいちばん低い")
    save(fig, "a967_recall.png", SRC, y=-0.07)

    # 図3：確かめ（9通り）
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    xs = np.arange(len(grid))
    ax.plot(xs, grid.complaint_true * 100, color=INK, marker="o", label="本当")
    ax.plot(xs, grid.complaint_subject * 100, color=ORANGE, marker="s", label="件名だけ（全体に占める割合）")
    ax.plot(xs, grid.complaint_subject_cl * 100, color=ORANGE, marker="^", ls="--", label="件名だけ（分けられた件の中）")
    ax.plot(xs, grid.complaint_body * 100, color=BLUE, marker="D", label="本文")
    ax.set_xticks(xs); ax.set_xticklabels([f"一般{g:.2f}\n偏り{t}" for g, t in zip(grid.g0, grid.tilt)], fontsize=7.5)
    ax.set_ylim(0, 20); ax.set_ylabel("不満・要望の割合（%、100回の平均）")
    ax.legend(frameon=False, fontsize=8, loc="lower left")
    ax.set_title("件名だけの不満・要望の割合は、置き方で大きく動く（9通り）")
    save(fig, "a967_grid.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
