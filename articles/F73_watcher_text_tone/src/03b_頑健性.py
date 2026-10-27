"""03b_頑健性：設定を変えて、テキスト指数と DI・CI の関係が変わるかを確かめる
- 辞書を絞る（期待・不安・懸念・様子見を外す）
- 語が1つ以上あるコメントだけで平均
- 家計動向／企業動向／雇用 だけ
- コロナ期（2020-03〜2021-12）を除く
- 季節調整値の DI と比べる
- CI を前月比にする
- 埋め込みスコア（03a）
あわせて、テキスト指数と DI の変化の相互相関（どちらが先に動くか）を出す
"""
import json
import numpy as np
import pandas as pd
import importlib
an = importlib.import_module("03_分析")
from common import RES

c, di, ci = an.load()
rows = []

def summarize(tag, m, res):
    x = res["xcorr_text_ci3"]
    best = max(x, key=lambda k: x[k])
    rows.append({"設定": tag, "月数": res["months"],
                 "テキストとDIの相関": round(res["corr_text_di_gen"], 3),
                 "変化どうしの相関": round(res["corr_text_di_gen_diff"], 3),
                 "テキストとCI3の相関": round(res["corr_text_ci3"], 3),
                 "相関が最大のずれ（か月）": int(best), "その相関": round(x[best], 3),
                 "グランジャーp（ラグ1）": round(res["granger_text_to_ci3"][1], 4),
                 "残差→翌月DI（係数）": round(res["resid_to_next_di"]["coef"], 2),
                 "残差→翌月DI（p）": round(res["resid_to_next_di"]["p"], 3)})

m, res = an.analyze(c, di, ci); summarize("基本（辞書・全コメント）", m, res)
base_m = m
m, res = an.analyze(c, di, ci, col="dict_core"); summarize("辞書を絞る", m, res)
m, res = an.analyze(c, di, ci, mask=c.hit); summarize("語のあるコメントだけ", m, res)
for f in ["家計動向", "企業動向", "雇用"]:
    m, res = an.analyze(c, di, ci, mask=(c.field3 == f)); summarize(f"{f}だけ", m, res)
# コロナ期を除く：月の表から外して相関を取り直す
m, res = an.analyze(c, di, ci)
mm = m[(m.index < an.COVID[0]) | (m.index > an.COVID[1])]
rows.append({"設定": "コロナ期を除く", "月数": len(mm),
             "テキストとDIの相関": round(mm[["score_gen", "raw_gen_di"]].corr().iloc[0, 1], 3),
             "変化どうしの相関": round(mm[["score_gen", "raw_gen_di"]].diff().corr().iloc[0, 1], 3),
             "テキストとCI3の相関": round(mm[["score_gen", "ci3"]].corr().iloc[0, 1], 3)})
# 季節調整値の DI
rows.append({"設定": "季節調整値のDIと比べる", "月数": int(m.sa_gen_di.notna().sum()),
             "テキストとDIの相関": round(m[["score_gen", "sa_gen_di"]].corr().iloc[0, 1], 3),
             "変化どうしの相関": round(m[["score_gen", "sa_gen_di"]].diff().corr().iloc[0, 1], 3)})
# CI 前月比
x1 = an.xcorr(m.score_gen, m.ci1); b1 = max(x1, key=lambda k: x1[k])
rows.append({"設定": "CIを前月比にする", "月数": int(m.ci1.notna().sum()),
             "テキストとCI3の相関": round(m[["score_gen", "ci1"]].corr().iloc[0, 1], 3),
             "相関が最大のずれ（か月）": int(b1), "その相関": round(x1[b1], 3),
             "グランジャーp（ラグ1）": round(an.granger_p(m.ci1, m.score_gen)[1], 4)})
# 埋め込み
try:
    e = pd.read_csv(RES / "embed_scores.csv")
    ce = c.merge(e[["id", "emb"]], on="id")
    m, res = an.analyze(ce, di, ci, col="emb"); summarize("埋め込み（各月150件）", m, res)
    md, rd = an.analyze(ce, di, ci, col="dict"); summarize("同じ150件で辞書", md, rd)
    emb_corr = float(np.corrcoef(ce.emb, ce.dict)[0, 1])
    emb_month_corr = float(pd.concat([m.score_gen, md.score_gen], axis=1).corr().iloc[0, 1])
    from sklearn.metrics import roc_auc_score
    emb_auc = {}
    for k in ("gen", "saki"):
        s = ce[(ce.kind == k) & ce.mark.isin(["◎", "○", "▲", "×"])]
        y = s.mark.isin(["◎", "○"]).astype(int)
        emb_auc[k] = {"emb": float(roc_auc_score(y, s.emb)), "dict_same_sample": float(roc_auc_score(y, s.dict))}
except FileNotFoundError:
    emb_corr = emb_month_corr = emb_auc = None

# どちらが先に動くか：テキストの変化と DI の変化の相互相関
d = base_m[["score_gen", "raw_gen_di"]].diff()
xtd = an.xcorr(d.score_gen, d.raw_gen_di, range(-3, 4))
pd.DataFrame(rows).to_csv(RES / "robustness.csv", index=False)
json.dump({"xcorr_textdiff_didiff": xtd, "emb_dict_corr_comment": emb_corr, "emb_dict_corr_month": emb_month_corr, "auc_comment": emb_auc},
          open(RES / "robustness_extra.json", "w"), ensure_ascii=False, indent=1)
print(pd.DataFrame(rows).to_string())
print(xtd, emb_corr, emb_month_corr)
