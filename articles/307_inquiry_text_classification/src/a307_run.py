"""307 問い合わせの記録を、カテゴリに自動で分ける（TF-IDF＋ロジスティック回帰）。
架空の問い合わせ文 3,000件を、型の文・言い回し・雑音（誤字、あいさつ、2つの用件、短すぎる文、ラベルの付け間違い）を組み合わせて作る。
"""
import json
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix
from sklearn.pipeline import make_pipeline
from common import DATA, RES

rng = np.random.default_rng(307)
CATS = ["請求・支払い", "ログイン・アカウント", "配送", "返品・交換", "使い方", "解約"]
OBJ = {
 "請求・支払い": (["請求書", "領収書", "引き落とし", "クレジットカードの決済", "今月の料金", "請求額", "支払い方法"],
              ["が届いていません", "の金額が違うようです", "を再発行してほしいです", "が二重になっています", "を変更したいです", "の内訳を教えてください", "がいつになるか知りたいです"]),
 "ログイン・アカウント": (["パスワード", "ログイン", "アカウント", "登録したメールアドレス", "二段階認証", "会員ID"],
              ["ができません", "を忘れてしまいました", "がロックされました", "を変更したいです", "のメールが届きません", "でエラーが出ます"]),
 "配送": (["注文した商品", "荷物", "配送状況", "お届け日", "配送先の住所", "追跡番号"],
        ["がまだ届きません", "を確認したいです", "を変更したいです", "が分かりません", "が予定より遅れています", "はいつ届きますか"]),
 "返品・交換": (["届いた商品", "サイズ", "不良品", "返品の手続き", "交換", "返金"],
           ["が違っていたので返品したいです", "を交換してほしいです", "の方法を教えてください", "はいつ頃になりますか", "が壊れていました", "の送料はどちらの負担ですか"]),
 "使い方": (["設定の方法", "データの取り込み", "アプリの使い方", "通知の設定", "印刷", "ファイルの出力", "初期設定"],
         ["が分かりません", "を教えてください", "がうまくいきません", "はどこからできますか", "の手順を知りたいです", "でつまずいています"]),
 "解約": (["解約", "退会", "定期購入の停止", "プランの解約", "自動更新", "契約の終了"],
        ["をしたいです", "の方法を教えてください", "はいつまでにすればよいですか", "を止めたいです", "の手続きが見つかりません", "をすると返金はありますか"]),
}
# カテゴリをまたいで出てくる言葉（わざと紛らわしくする）
CROSS = {("解約", "請求・支払い"): ["解約したのに請求が来ています", "解約後の引き落としについて確認したいです", "退会したのに料金が発生しています"],
         ("返品・交換", "請求・支払い"): ["返品したのに返金がまだです", "返金の金額が請求と合いません"],
         ("返品・交換", "配送"): ["交換品がまだ届きません", "返品の集荷はいつ来ますか"],
         ("ログイン・アカウント", "使い方"): ["ログイン後の画面の見方が分かりません", "アカウントの設定画面がどこか分かりません"],
         ("ログイン・アカウント", "解約"): ["ログインできないので退会の手続きができません"],
         ("配送", "使い方"): ["配送状況の確認の仕方が分かりません"]}
HEAD = ["", "", "", "お世話になっております。", "お疲れ様です。", "はじめて問い合わせます。", "先日はありがとうございました。", "至急お願いします。", "すみません、"]
TAIL = ["", "", "", "よろしくお願いします。", "ご確認お願いします。", "困っています。", "急ぎです。", "返信お待ちしています。", "何度も連絡しています。"]
SHORT = {"請求・支払い": ["請求の件", "料金について", "領収書"], "ログイン・アカウント": ["ログインできない", "パスワード", "入れません"],
         "配送": ["まだ届かない", "配送の件", "いつ届く？"], "返品・交換": ["返品したい", "交換希望", "壊れてた"],
         "使い方": ["使い方", "設定が分からない", "やり方教えて"], "解約": ["解約したい", "退会", "やめたいです"]}
VAGUE = ["先日の件、どうなっていますか", "連絡がありません", "対応をお願いします", "確認してもらえますか", "前回と同じ件です", "担当の方から折り返しください"]


def typo(s):  # 1文字の抜け・入れ替え・かなの打ち間違い
    if len(s) < 6: return s
    i = int(rng.integers(1, len(s) - 2)); k = rng.integers(3)
    return s[:i] + s[i + 1:] if k == 0 else (s[:i] + s[i + 1] + s[i] + s[i + 2:] if k == 1 else s[:i] + rng.choice(list("のにをがはでと")) + s[i:])


def one(cat):
    kind = rng.choice(["plain", "cross", "two", "short", "vague"], p=[.62, .14, .10, .09, .05])
    if kind == "plain":
        o, v = OBJ[cat]; body = rng.choice(o) + rng.choice(v)
    elif kind == "cross":  # ほかのカテゴリの言葉が混ざる文。ラベルは主な用件のほう
        ks = [k for k in CROSS if k[0] == cat]
        if not ks: o, v = OBJ[cat]; body = rng.choice(o) + rng.choice(v); kind = "plain"
        else: body = rng.choice(CROSS[ks[int(rng.integers(len(ks)))]])
    elif kind == "two":  # 用件が2つ。ラベルは先に書いたほう
        o, v = OBJ[cat]; c2 = rng.choice([c for c in CATS if c != cat]); o2, v2 = OBJ[c2]
        body = rng.choice(o) + rng.choice(v) + "。あと、" + rng.choice(o2) + rng.choice(v2)
    elif kind == "short": body = rng.choice(SHORT[cat])
    else: body = rng.choice(VAGUE)  # 文だけではカテゴリが分からない
    text = rng.choice(HEAD) + body + ("。" if not body.endswith(("。", "？")) else "") + rng.choice(TAIL)
    if rng.random() < .15: text = typo(text)
    return text, kind


N = 3000
p = np.array([.24, .20, .18, .12, .16, .10])
rows = []
for i in range(N):
    cat = CATS[int(rng.choice(6, p=p))]; text, kind = one(cat)
    label = cat if rng.random() >= .04 else rng.choice([c for c in CATS if c != cat])  # 4% は人の付け間違い
    rows.append((i + 1, text, cat, label, kind))
df = pd.DataFrame(rows, columns=["id", "text", "true_category", "label", "kind"])
df.to_csv(DATA / "inquiries.csv", index=False)

test = df.iloc[2400:].reset_index(drop=True); pool = df.iloc[:2400].reset_index(drop=True)


def model(): return make_pipeline(TfidfVectorizer(analyzer="char", ngram_range=(1, 3), sublinear_tf=True, min_df=2),
                                  LogisticRegression(C=10, max_iter=2000))


m = model().fit(pool["text"], pool["label"])  # 学習は付け間違いを含むラベルで行う
pred = m.predict(test["text"]); proba = m.predict_proba(test["text"]).max(axis=1)
test = test.assign(pred=pred, conf=proba, ok=pred == test["true_category"])
acc = float(test.ok.mean())
# 比べる相手：人が最初に書きそうなキーワードの決まり（カテゴリごとに2〜3語。文の中で先に出てきた語のカテゴリにする）
KW = {"請求・支払い": ["請求", "料金", "領収書"], "ログイン・アカウント": ["ログイン", "パスワード", "アカウント"], "配送": ["届", "配送", "荷物"],
      "返品・交換": ["返品", "交換", "返金"], "使い方": ["使い方", "設定", "方法"], "解約": ["解約", "退会"]}
def rule(t):
    hits = [(t.find(w), c) for c in CATS for w in KW[c] if w in t]
    return min(hits)[1] if hits else "（当たらない）"
# 参考：データを作るのに使った言葉を全部入れた決まり（実際には手に入らない、上限の目安）
KWF = {c: sorted(set(OBJ[c][0]) | set(SHORT[c]), key=len, reverse=True) for c in CATS}
def rule_full(t):
    hits = [(t.find(w), c) for c in CATS for w in KWF[c] if w in t]
    return min(hits)[1] if hits else "（当たらない）"
acc_rule_full = float(np.mean([rule_full(t) == c for t, c in zip(test["text"], test["true_category"])]))
test["rule"] = [rule(t) for t in test["text"]]; acc_rule = float((test.rule == test.true_category).mean())
acc_major = float((test.true_category == CATS[0]).mean())
by_cat = test.groupby("true_category").agg(n=("ok", "size"), model_acc=("ok", "mean"), rule_acc=("rule", lambda s: float((s == test.loc[s.index, "true_category"]).mean()))).reindex(CATS).reset_index()
by_kind = test.groupby("kind").agg(n=("ok", "size"), model_acc=("ok", "mean"), rule_acc=("rule", lambda s: float((s == test.loc[s.index, "true_category"]).mean()))).reset_index()
by_cat.round(4).to_csv(RES / "accuracy_by_category.csv", index=False); by_kind.round(4).to_csv(RES / "accuracy_by_kind.csv", index=False)
cm = pd.DataFrame(confusion_matrix(test.true_category, test.pred, labels=CATS), index=CATS, columns=CATS); cm.to_csv(RES / "confusion_matrix.csv")
# 学習に使う件数と正解率（件数ごとに、2,400件から10通りの取り出し方で）
lc = []
for n in [30, 60, 120, 240, 480, 960, 1500, 2400]:
    a = []
    for r in range(10 if n < 2400 else 1):
        idx = np.random.default_rng(1000 + r).choice(2400, n, replace=False)
        sub = pool.iloc[idx]
        if sub["label"].nunique() < 6: continue
        a.append(float((model().fit(sub["text"], sub["label"]).predict(test["text"]) == test["true_category"]).mean()))
    lc.append({"n_train": n, "acc_mean": np.mean(a), "acc_min": np.min(a), "acc_max": np.max(a), "runs": len(a)})
lc = pd.DataFrame(lc); lc.round(4).to_csv(RES / "learning_curve.csv", index=False)
# 自信の高さで分ける：自信が高いものだけ自動で分け、残りは人が見る
th = []
for t in [0.0, 0.5, 0.6, 0.7, 0.8, 0.9]:
    k = test.conf >= t
    th.append({"threshold": t, "auto_share": float(k.mean()), "auto_acc": float(test.ok[k].mean())})
th = pd.DataFrame(th); th.round(4).to_csv(RES / "confidence_threshold.csv", index=False)
# ラベルの付け間違いがなければ（学習のラベルを正しいものにした場合）
acc_clean = float((model().fit(pool["text"], pool["true_category"]).predict(test["text"]) == test["true_category"]).mean())
test[["id", "text", "true_category", "label", "kind", "pred", "conf", "rule"]].round({"conf": 4}).to_csv(RES / "test_predictions.csv", index=False)
off = cm.copy().astype(int); np.fill_diagonal(off.values, 0); st = off.stack(); top = st.sort_values(ascending=False).head(5)
summ = {"n": N, "n_train": 2400, "n_test": 600, "kind_share": df.kind.value_counts(normalize=True).round(3).to_dict(),
        "label_noise_share": round(float((df.label != df.true_category).mean()), 4), "typo_share": 0.15,
        "acc_model": round(acc, 4), "acc_rule": round(acc_rule, 4), "acc_rule_full_vocab": round(acc_rule_full, 4), "rule_no_hit_share": round(float((test.rule == "（当たらない）").mean()), 4), "acc_majority": round(acc_major, 4), "acc_model_clean_labels": round(acc_clean, 4),
        "by_category": {r.true_category: round(float(r.model_acc), 3) for r in by_cat.itertuples()},
        "by_kind": {r.kind: {"n": int(r.n), "model": round(float(r.model_acc), 3), "rule": round(float(r.rule_acc), 3)} for r in by_kind.itertuples()},
        "top_confusions": [{"true": a, "pred": b, "n": int(v)} for (a, b), v in top.items()], "errors": int((~test.ok).sum()),
        "learning_curve": {int(r.n_train): round(float(r.acc_mean), 3) for r in lc.itertuples()},
        "threshold": {str(r.threshold): {"auto_share": round(float(r.auto_share), 3), "auto_acc": round(float(r.auto_acc), 3)} for r in th.itertuples()}}
json.dump(summ, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(summ, ensure_ascii=False, indent=0))
