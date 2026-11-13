"""534 アンケートの「その他」の自由記述を選択肢に振り直すと、各選択肢の割合は何ポイント動くのか（実務の型）

架空のアンケート（「購入の決め手」を1つ選ぶ、回答2,000件）を作る。「その他」を選んだ人の自由記述には、
既存の選択肢と同じ内容（「安かった」→ 価格、など）と、本当にどれにも当てはまらない内容を混ぜる。
振り直す前、キーワードで振り直した後、人手で振り直した後（作成時の正解ラベルを人手の結果とみなす）の構成比を比べ、
順位の入れ替わりとキーワードの当たり外れを見る。キーワードでの振り直しは SQL（DuckDB）でも行い、Python と一致するか確かめる。
"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, SQL, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 534
SRC = "架空のアンケート（作成者が乱数で作成、seed 534）"
OPTS = ["価格", "品質", "デザイン", "口コミ", "店員の対応", "その他"]
SHARE = [0.30, 0.235, 0.15, 0.115, 0.08, 0.12]          # 選択肢を選んだ割合（「その他」12%）
# 「その他」の自由記述：中身の本当の区分と、書かれ方の例（キーワードに当たる書き方と、当たらない書き方を混ぜる）
TEXTS = {
    "価格": ["安かったから", "セールだった", "値段が手ごろ", "お得だったので", "クーポンが使えた"],
    "品質": ["長持ちしそう", "丈夫そうだった", "値段は高いが丈夫", "作りがしっかりしている", "前の物より壊れにくい"],
    "デザイン": ["色が好き", "見た目がよかった", "形がかわいい", "部屋に合いそう"],
    "口コミ": ["友だちに勧められて", "SNSで見て", "レビューの評価が高い", "家族が使っていて良いと言った", "評判を聞いて"],
    "店員の対応": ["店の人が親切だった", "接客が丁寧", "説明がわかりやすかった"],
    "その他のまま": ["家から近い", "ポイントがたまる", "前から使っている", "贈り物用", "色々比べて家から近い店にした", "なんとなく", "すぐ届くから"],
}
# 「その他」の中身の割合：既存の選択肢と同じ内容が55%、本当のその他が45%
INNER = {"価格": 0.10, "品質": 0.08, "デザイン": 0.07, "口コミ": 0.24, "店員の対応": 0.06, "その他のまま": 0.45}
# キーワード（上から順に当てる。最初に当たったものに振る）
KEYWORDS = [("価格", ["安", "値段", "価格", "セール"]), ("品質", ["品質", "丈夫", "長持ち"]), ("デザイン", ["デザイン", "色", "見た目"]),
            ("口コミ", ["口コミ", "レビュー", "評判"]), ("店員の対応", ["店員", "接客"])]


def make(n=2000, seed=SEED):
    rng = np.random.default_rng(seed)
    ch = rng.choice(OPTS, n, p=SHARE)
    text, truth = [""] * n, list(ch)
    keys = list(INNER); pw = np.array(list(INNER.values()))
    for i in np.where(ch == "その他")[0]:
        k = keys[rng.choice(len(keys), p=pw / pw.sum())]
        text[i] = TEXTS[k][rng.integers(len(TEXTS[k]))]
        truth[i] = "その他" if k == "その他のまま" else k
    return pd.DataFrame({"resp_id": np.arange(1, n + 1), "choice": ch, "other_text": text, "manual_label": truth})


def keyword(t):
    for lab, kws in KEYWORDS:
        if any(k in t for k in kws):
            return lab
    return "その他"


def comp(s):
    return (s.value_counts(normalize=True).reindex(OPTS).fillna(0) * 100)


def main():
    df = make()
    df.to_csv(DATA / "fictional_survey.csv", index=False)
    df["kw_label"] = np.where(df.choice == "その他", df.other_text.map(keyword), df.choice)
    con = duckdb.connect(); con.execute("SET threads=1"); con.register("survey", df[["resp_id", "choice", "other_text"]])
    s = con.execute(open(SQL / "02_other_recode_duckdb.sql", encoding="utf-8").read()).df().sort_values("resp_id")
    sql_ok = bool((s.kw_label.to_numpy() == df.sort_values("resp_id").kw_label.to_numpy()).all())

    before, kw, man = comp(df.choice), comp(df.kw_label), comp(df.manual_label)
    tb = pd.DataFrame({"選択肢": OPTS, "振り直す前(%)": before.round(1).values, "キーワード(%)": kw.round(1).values, "人手(%)": man.round(1).values})
    tb["キーワード−前(pt)"] = (kw - before).round(1).values; tb["人手−前(pt)"] = (man - before).round(1).values
    rk = lambda c: c.drop("その他").rank(ascending=False, method="min").astype(int)
    tb["順位_前"] = tb.選択肢.map(rk(before)); tb["順位_キーワード"] = tb.選択肢.map(rk(kw)); tb["順位_人手"] = tb.選択肢.map(rk(man))
    tb.to_csv(RES / "composition_before_after.csv", index=False)
    oth = df[df.choice == "その他"]
    cm = pd.crosstab(oth.manual_label, oth.kw_label).reindex(index=OPTS, columns=OPTS).fillna(0).astype(int)
    cm.to_csv(RES / "keyword_vs_manual_in_other.csv")
    acc = float((oth.kw_label == oth.manual_label).mean() * 100)
    miss = oth[(oth.kw_label != oth.manual_label)].groupby(["other_text", "manual_label", "kw_label"]).size().rename("件数").reset_index().sort_values("件数", ascending=False)
    miss.to_csv(RES / "keyword_misses.csv", index=False)
    res = {"n": len(df), "n_other": int(len(oth)), "sql_matches_python": sql_ok,
           "other_share_pct": {"前": round(before["その他"], 1), "キーワード": round(kw["その他"], 1), "人手": round(man["その他"], 1)},
           "max_abs_shift_pt": {"キーワード": round(float((kw - before).drop("その他").abs().max()), 1), "人手": round(float((man - before).drop("その他").abs().max()), 1)},
           "keyword_accuracy_in_other_pct": round(acc, 1), "keyword_vs_manual_gap_pt": {o: round(float(kw[o] - man[o]), 1) for o in OPTS},
           "table": tb.to_dict(orient="records")}
    json.dump(res, open(RES / "a534_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：構成比（3通り）
    fig, ax = plt.subplots(figsize=(8, 3.9))
    xs = np.arange(len(OPTS)); wd = 0.27
    for j, (v, c, l) in enumerate([(before, GRAY, "振り直す前"), (kw, ORANGE, "キーワードで振り直し"), (man, BLUE, "人手で振り直し")]):
        ax.bar(xs + (j - 1) * wd, v.values, wd, color=c, label=l)
    ax.set_xticks(xs, OPTS); ax.set_ylabel("構成比（%）"); ax.legend(frameon=False, fontsize=9)
    ax.set_title("「その他」を振り直すと、口コミがいちばん増える")
    save(fig, "a534_composition.png", SRC)
    # 図2：変化（ポイント）
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    d1, d2 = (kw - before), (man - before)
    ax.barh(xs + 0.18, d1.values, 0.36, color=ORANGE, label="キーワード − 前")
    ax.barh(xs - 0.18, d2.values, 0.36, color=BLUE, label="人手 − 前")
    for y, v in zip(xs, d2.values):
        ax.text(v + (0.15 if v >= 0 else -0.15), y - 0.18, f"{v:+.1f}", va="center", ha="left" if v >= 0 else "right", fontsize=8.5)
    ax.set_yticks(xs, OPTS); ax.invert_yaxis(); ax.axvline(0, color=INK, lw=0.8)
    ax.set_xlabel("振り直しによる構成比の変化（ポイント）"); ax.set_xlim(-7.3, 3.8); ax.legend(frameon=False, fontsize=9, loc="center left")
    ax.set_title("動きは「その他」の中身しだい")
    save(fig, "a534_shift.png", SRC)
    # 図3：キーワード × 人手（「その他」の回答だけ）
    fig, ax = plt.subplots(figsize=(6.6, 5))
    ax.imshow(cm.values, cmap="Blues")
    for i in range(len(OPTS)):
        for j in range(len(OPTS)):
            v = cm.values[i, j]
            if v:
                ax.text(j, i, v, ha="center", va="center", color="white" if v > cm.values.max() * 0.6 else INK, fontsize=9)
    ax.set_xticks(range(len(OPTS)), OPTS, rotation=30, ha="right"); ax.set_yticks(range(len(OPTS)), OPTS)
    ax.set_xlabel("キーワードで振った先"); ax.set_ylabel("人手で振った先")
    ax.set_title(f"「その他」{len(oth)}件：キーワードが人手と一致 {acc:.0f}%")
    for sp in ax.spines.values(): sp.set_visible(False)
    save(fig, "a534_keyword_vs_manual.png", SRC)
    print(json.dumps({k: v for k, v in res.items() if k != "table"}, ensure_ascii=False, indent=1)); print(tb.to_string()); print(miss.to_string())


if __name__ == "__main__":
    main()
