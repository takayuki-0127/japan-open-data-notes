"""968 文字数の数え方（文字・バイト・単語）で、何が変わるのか？（架空のデータ）

架空の店の感想フォームに届いた短い文。作成者が用意した語のかたまり（日本語の句・半角英数の語・全角英数・
半角カタカナ・絵文字）を乱数で組み合わせて作る。入口は「スマホのフォーム」と「パソコンのフォーム」の2つで、
かたまりの出やすさを入口ごとに作成者が置く。同じ文を7つの数え方で数える（Python の標準機能だけを使う）。
"""
import json
import unicodedata
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 968
SRC = "架空の感想フォームの文（作成者が乱数で語を組み合わせて作成、seed 968）"
JP = ["注文した商品が届きました", "とても使いやすいです", "色が写真と少し違いました", "また利用したいと思います",
      "梱包がていねいでした", "説明書が分かりやすかったです", "思ったより小さめでした", "届くのが早くて助かりました",
      "店員さんの説明がよかったです", "次は別の色も試します", "少し値段が気になりました", "家族にもすすめました"]
PUNCT_JP = ["。", "！", "、"]
ASCII = ["OK", "size", "M", "L", "app", "update", "PC", "USB", "No.3", "ver2", "Wi-Fi", "mail", "good", "thanks"]
FW = ["ＯＫ", "ＵＳＢ", "ＰＣ", "Ｍ", "Ｌ"]
HWK = ["ｻｲｽﾞ", "ﾎﾟｲﾝﾄ", "ｶﾗｰ", "ﾒｰﾙ"]
# 絵文字（見た目は1字のまとまり）：顔・肌の色つき・異体字の選択子つき・つなぎ文字でつないだもの
EMOJI = ["\U0001F600", "\U0001F44D\U0001F3FB", "❤️", "\U0001F468‍\U0001F469‍\U0001F467",
         "\U0001F647‍♀️", "\U0001F389"]
EMOJI_NAME = ["顔", "肌の色つきの手", "異体字の選択子つきのハート", "つなぎ文字の家族", "つなぎ文字のおじぎ", "クラッカー"]
FORMS = {"スマホ": dict(jp=2.3, emoji=1.6, ascii=0.3, fw=0.0, hwk=0.05),
         "パソコン": dict(jp=2.1, emoji=0.1, ascii=2.5, fw=0.3, hwk=0.4)}
MEASURES = ["見た目の文字", "コードポイント", "UTF-16の単位", "UTF-8のバイト", "Shift_JISのバイト", "全角1・半角0.5", "単語（空白区切り）"]
LIMIT = 50
# 上限：文字の数え方は50、バイトは「全角50字分」（UTF-8 は150バイト、Shift_JIS は100バイト）
LIMITS = {"見た目の文字": 50, "コードポイント": 50, "UTF-16の単位": 50, "UTF-8のバイト": 150, "Shift_JISのバイト": 100,
          "全角1・半角0.5": 50}


def make_text(rng, p):
    """文と、見た目の文字数（作成者が記録した数）を返す"""
    pieces = []  # (文字列, 見た目の文字数)
    n_jp = max(1, rng.poisson(p["jp"]))
    for i in range(n_jp):
        s = JP[rng.integers(len(JP))] + PUNCT_JP[rng.integers(len(PUNCT_JP))]
        pieces.append((s, len(s)))
        if rng.random() < p["hwk"] / n_jp:
            h = HWK[rng.integers(len(HWK))]
            pieces.append((h, len(h)))
        if rng.random() < p["fw"] / n_jp:
            f = FW[rng.integers(len(FW))]
            pieces.append((f, len(f)))
    # 半角英数の語：空白で区切って、どこか1か所に入れる
    n_a = rng.poisson(p["ascii"])
    if n_a > 0:
        s = " " + " ".join(ASCII[rng.integers(len(ASCII))] for _ in range(n_a)) + " "
        pieces.insert(rng.integers(len(pieces) + 1), (s, len(s)))
    n_e = rng.poisson(p["emoji"])
    for _ in range(n_e):
        e = EMOJI[rng.integers(len(EMOJI))]
        pieces.insert(rng.integers(len(pieces) + 1), (e, 1))
    text = "".join(s for s, _ in pieces).strip()
    vis = sum(v for _, v in pieces) - (len("".join(s for s, _ in pieces)) - len(text))
    return text, vis


def measures(text, vis):
    try:
        sj = len(text.encode("cp932"))
        sj_ok = True
    except UnicodeEncodeError:
        sj = len(text.encode("cp932", errors="replace"))  # 表せない文字は1つずつ「?」（1バイト）
        sj_ok = False
    w = sum(1.0 if unicodedata.east_asian_width(ch) in ("F", "W", "A") else 0.5 for ch in text)
    return {"見た目の文字": vis, "コードポイント": len(text), "UTF-16の単位": len(text.encode("utf-16-le")) // 2,
            "UTF-8のバイト": len(text.encode("utf-8")), "Shift_JISのバイト": sj, "全角1・半角0.5": w,
            "単語（空白区切り）": len(text.split()), "sjis_ok": sj_ok}


def make_set(rng, n=3000, forms=FORMS):
    rows = []
    for f, p in forms.items():
        for i in range(n):
            t, v = make_text(rng, p)
            rows.append({"form": f, "text": t, **measures(t, v)})
    return pd.DataFrame(rows)


def summarize(df):
    m = df.groupby("form", sort=False)[MEASURES].mean()
    ratio = (m.loc["パソコン"] / m.loc["スマホ"]).round(3)
    return m, ratio


def main():
    rng = np.random.default_rng(SEED)
    # 作りの確かめ：絵文字はどれも見た目1字、ほかのかたまりは見た目＝コードポイント
    for e in EMOJI:
        assert len(e) >= 1
    df = make_set(rng)
    df.insert(0, "text_id", np.arange(1, len(df) + 1))
    df.to_csv(DATA / "feedback_example.csv", index=False)
    emo = pd.DataFrame([{"emoji": n, "codepoints": len(e), "utf16": len(e.encode("utf-16-le")) // 2,
                         "utf8": len(e.encode("utf-8")), "visual": 1, "sjis_ok": measures(e, 1)["sjis_ok"],
                         "east_asian_width_count": sum(1.0 if unicodedata.east_asian_width(c) in ("F", "W", "A") else 0.5 for c in e)}
                        for n, e in zip(EMOJI_NAME, EMOJI)])
    emo.to_csv(RES / "emoji_counts.csv", index=False)
    piece = pd.DataFrame([{"piece": n, **{k: v for k, v in measures(s, vv).items() if k != "sjis_ok"}}
                          for n, s, vv in [("ひらがな・漢字1字（あ）", "あ", 1), ("半角英字1字（a）", "a", 1),
                                           ("全角英字1字（ａ）", "ａ", 1), ("半角カタカナ1字（ｱ）", "ｱ", 1),
                                           ("半角カタカナの半濁点つき（ﾎﾟ）", "ﾎﾟ", 2)]])
    piece.to_csv(RES / "piece_counts.csv", index=False)

    # 作りの確かめ：絵文字を含まない文では、見た目＝コードポイント＝UTF-16の単位
    no_emoji = ~df.text.map(lambda t: any(e in t for e in EMOJI))
    check_no_emoji = bool(((df.loc[no_emoji, "見た目の文字"] == df.loc[no_emoji, "コードポイント"]) &
                           (df.loc[no_emoji, "コードポイント"] == df.loc[no_emoji, "UTF-16の単位"])).all())
    assert check_no_emoji
    m, ratio = summarize(df)
    m.round(3).to_csv(RES / "mean_by_form.csv")
    # 上限 LIMIT（「50字以内」）を、それぞれの数え方で当てたときに超える割合
    lim = pd.Series(LIMITS)
    over = df.groupby("form", sort=False)[list(LIMITS)].apply(lambda g: (g > lim).mean()).round(4)
    over.to_csv(RES / "over_limit_by_form.csv")
    split = {}
    rows_dis = []
    for f in FORMS:
        g = df[df.form == f]
        o = (g[list(LIMITS)] > lim)
        split[f] = {"any_disagree": round(float((o.any(axis=1) & ~o.all(axis=1)).mean()), 4),
                    "sjis_unencodable": round(float((~g.sjis_ok).mean()), 4)}
        for meas in list(LIMITS)[1:]:
            rows_dis.append({"form": f, "measure": meas,
                             "ok_visual_but_over": round(float((~o["見た目の文字"] & o[meas]).mean()), 4),
                             "over_visual_but_ok": round(float((o["見た目の文字"] & ~o[meas]).mean()), 4)})
    # 確かめ：上限の大きさを変える（30・50・80字、UTF-8 はその3倍のバイト）
    lim_rows = []
    for L in [30, 50, 80]:
        for f in FORMS:
            g = df[df.form == f]
            lim_rows.append({"limit_chars": L, "form": f, "over_visual": round(float((g["見た目の文字"] > L).mean()), 4),
                             "over_utf16": round(float((g["UTF-16の単位"] > L).mean()), 4),
                             "over_utf8": round(float((g["UTF-8のバイト"] > 3 * L).mean()), 4)})
    lim_tab = pd.DataFrame(lim_rows)
    lim_tab.to_csv(RES / "over_limit_by_limit_size.csv", index=False)
    dis = pd.DataFrame(rows_dis)
    dis.to_csv(RES / "limit_disagreement_vs_visual.csv", index=False)
    # 長い順の上位10%：見た目の文字と比べて、どれだけ同じ文か
    k = int(len(df) * 0.1)
    top_vis = set(df.nlargest(k, "見た目の文字", keep="first").text_id)
    top = {}
    for meas in MEASURES:
        tt = df.nlargest(k, meas, keep="first")
        top[meas] = {"overlap_with_visual": round(len(top_vis & set(tt.text_id)) / k, 4),
                     "share_smartphone": round(float((tt.form == "スマホ").mean()), 4)}
    pd.DataFrame(top).T.to_csv(RES / "top10pct_by_measure.csv")
    corr = df[MEASURES].corr(method="spearman").round(3)
    corr.to_csv(RES / "spearman_between_measures.csv")

    # 確かめ：スマホの絵文字の数 × パソコンの半角英数の語の数（9通り、各1,000文ずつ）
    grid = []
    for em in [0.5, 1.6, 3.0]:
        for asc in [1.0, 2.5, 5.0]:
            fm = {"スマホ": {**FORMS["スマホ"], "emoji": em}, "パソコン": {**FORMS["パソコン"], "ascii": asc}}
            g = make_set(np.random.default_rng(SEED * 10 + int(em * 10) + int(asc * 100)), 1000, fm)
            _, r = summarize(g)
            grid.append({"smartphone_emoji": em, "pc_ascii_words": asc, **{f"ratio_{k}": float(v) for k, v in r.items()}})
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_ratio_pc_over_smartphone.csv", index=False)
    rng_r = {k: [float(grid[f"ratio_{k}"].min()), float(grid[f"ratio_{k}"].max())] for k in MEASURES}
    longer = {k: {"pc_longer": int((grid[f"ratio_{k}"] > 1).sum()), "smartphone_longer": int((grid[f"ratio_{k}"] < 1).sum())}
              for k in MEASURES}

    out = {"check_no_emoji_visual_eq_codepoint_eq_utf16": check_no_emoji, "n_no_emoji_texts": int(no_emoji.sum()),
           "n_per_form": 3000, "n_total": int(len(df)),
           "n_pieces": {"jp_phrases": len(JP), "ascii_words": len(ASCII), "fullwidth": len(FW), "halfwidth_kana": len(HWK),
                        "emoji": len(EMOJI)}, "limit": LIMIT, "forms": FORMS,
           "mean_by_form": m.round(3).to_dict(), "ratio_pc_over_smartphone": ratio.to_dict(),
           "limits": LIMITS, "over_limit_by_form": over.to_dict(), "limit_disagreement": split,
           "limit_disagreement_vs_visual": dis.to_dict("records"),
           "top10pct_by_measure": top, "spearman_visual_vs": corr["見た目の文字"].to_dict(),
           "spearman_min_pair": float(corr.where(~np.eye(len(MEASURES), dtype=bool)).min().min()),
           "grid_ratio_range": rng_r, "grid_which_longer_count": longer,
           "emoji_counts": emo.to_dict("records")}
    json.dump(out, open(RES / "a968_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：パソコン÷スマホの平均の比（数え方ごと）
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    y = np.arange(len(MEASURES))[::-1]
    cols = [ORANGE if v < 1 else BLUE for v in ratio.values]
    ax.barh(y, ratio.values, color=cols)
    ax.axvline(1, color=INK, lw=1)
    for yi, v in zip(y, ratio.values):
        ax.text(max(v, 1) + 0.03, yi, f"{v:.2f}倍", va="center", fontsize=9)
    ax.set_yticks(y); ax.set_yticklabels(MEASURES)
    ax.set_xlim(0, max(ratio.values) * 1.2)
    ax.set_xlabel("パソコンの平均 ÷ スマホの平均（各3,000文。1より左はスマホが長い）")
    ax.set_title("どちらの入口の文が長いかは、数え方で入れ替わる")
    save(fig, "a968_ratio_by_measure.png", SRC, y=-0.05)

    # 図2：上限50で超える割合
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    ms = list(LIMITS)
    x = np.arange(len(ms))
    ax.bar(x - 0.2, over.loc["スマホ", ms] * 100, 0.4, color=ORANGE, label="スマホ")
    ax.bar(x + 0.2, over.loc["パソコン", ms] * 100, 0.4, color=BLUE, label="パソコン")
    for xi, a, b in zip(x, over.loc["スマホ", ms], over.loc["パソコン", ms]):
        ax.text(xi - 0.2, a * 100 + 1, f"{a*100:.0f}", ha="center", fontsize=8)
        ax.text(xi + 0.2, b * 100 + 1, f"{b*100:.0f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels([f"{s}\n（{LIMITS[s]}）" for s in ms], fontsize=7.5)
    ax.set_ylabel("上限を超えた文の割合（%）")
    ax.set_ylim(0, 40)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("上限「50字」（バイトは全角50字分）を何で数えるかで、超える文が変わる", fontsize=11.5)
    save(fig, "a968_over_limit.png", SRC)

    # 図3：確かめ（9通り）
    fig, ax = plt.subplots(figsize=(8.8, 4.0))
    xs = np.arange(len(grid))
    style = {"見た目の文字": (INK, "o"), "UTF-8のバイト": (BLUE, "s"), "UTF-16の単位": (LIGHT, "^"),
             "単語（空白区切り）": (GREEN, "D"), "全角1・半角0.5": (ORANGE, "v")}
    for k2, (c, mk) in style.items():
        ax.plot(xs, grid[f"ratio_{k2}"], color=c, marker=mk, lw=1.2, label=k2)
    ax.axhline(1, color=GRAY, lw=1, ls="--")
    ax.set_yscale("log")
    ax.set_yticks([0.75, 1, 1.5, 2, 3, 4, 5]); ax.set_yticklabels(["0.75", "1", "1.5", "2", "3", "4", "5"])
    ax.minorticks_off()
    ax.set_xticks(xs); ax.set_xlabel("スマホの絵文字の数（1文の平均）と、パソコンの半角英数の語の数（同）", fontsize=9)
    ax.set_xticklabels([f"絵文字{e}\n英数の語{a}" for e, a in zip(grid.smartphone_emoji, grid.pc_ascii_words)], fontsize=7.5)
    ax.set_ylabel("パソコン÷スマホ（対数の目盛り）")
    ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(1.01, 1.0))
    ax.set_title("置き方を変えると、どちらが長いかの答えも動く（9通り）")
    save(fig, "a968_grid.png", SRC, y=-0.06)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:5000])


if __name__ == "__main__":
    main()
