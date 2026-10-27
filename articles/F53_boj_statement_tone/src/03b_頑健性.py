"""03b_頑健性：スコアの作り方を変えても、景気との関係と転換点が変わらないか

1 現状判断の文が3つ以上ある会合だけ
2 辞書から「横ばい・下げ止まり・大幅に・急速に・慎重・不透明」を外す
3 先行きの文も入れる
4 会合ごとに最初の現状判断の文（多くは「わが国の景気は…」）だけ
5 埋め込みの前に「トピック: 」を付ける
6 埋め込みの基準文を2つずつに減らす
7 2020年（コロナ）を除く
"""
import importlib.util
import json
import numpy as np
import pandas as pd
from common import DATA, RES, POS, NEG, ANCHOR_POS, ANCHOR_NEG, MODEL
import common

spec = importlib.util.spec_from_file_location("a", str(common.ROOT / "src" / "03_分析.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

NEG2 = [w for w in NEG if w not in ("横ばい", "下げ止", "大幅に", "急速に", "慎重", "不透明")]


def emb(sentences, prefix="", npos=5):
    from sentence_transformers import SentenceTransformer
    mdl = emb.m = getattr(emb, "m", None) or SentenceTransformer(MODEL, device="cpu")
    E = mdl.encode([prefix + s for s in sentences], batch_size=64, normalize_embeddings=True)
    P = mdl.encode([prefix + s for s in ANCHOR_POS[:npos]], normalize_embeddings=True)
    N = mdl.encode([prefix + s for s in ANCHOR_NEG[:npos]], normalize_embeddings=True)
    return (E @ P.T).mean(1) - (E @ N.T).mean(1)


def summarize(name, g, m, base):
    t = a.attach(g, m)
    x = t[["score", "ci12_known"]].dropna()
    r = x.corr().iloc[0, 1]
    y = t[["score", "ci12_after"]].dropna()
    ra = y.corr().iloc[0, 1]
    tp, _ = a.turning_points(t.assign(score=(t.score - t.score.mean()) / t.score.std() if "emb" in name else t.score))
    after18 = tp[(tp.date > "2018-10-01") & (tp.to == "弱気へ")].date
    after12 = tp[(tp.date > "2012-11-01") & (tp.to == "強気へ")].date
    mm = base.merge(t[["date", "score"]], on="date", suffixes=("_base", ""))
    return {"variant": name, "n": len(t), "r_ci12_known": round(r, 3), "r_ci12_after6": round(ra, 3),
            "r_with_base": round(mm.score.corr(mm.score_base), 3),
            "weak_after_2018peak": str(after18.iloc[0].date()) if len(after18) else "なし",
            "strong_after_2012trough": str(after12.iloc[0].date()) if len(after12) else "なし"}


def main():
    sen = pd.read_csv(DATA / "sentences.csv")
    m = a.monthly()
    base_scores = pd.read_csv(RES / "sentence_scores.csv")
    base_d = a.meeting_table(base_scores, "dict")
    base_e = a.meeting_table(base_scores, "emb")
    rows = [summarize("基本・辞書", base_d, m, base_d), summarize("基本・埋め込み", base_e, m, base_e)]
    # 1
    rows.append(summarize("文3つ以上の会合・辞書", base_d[base_d.n >= 3], m, base_d))
    rows.append(summarize("文3つ以上の会合・埋め込み", base_e[base_e.n >= 3], m, base_e))
    # 2
    s2 = a.build(sen, POS, NEG2)
    rows.append(summarize("辞書から6語を外す", a.meeting_table(s2, "dict"), m, base_d))
    # 3
    s3 = a.build(sen, kinds=("current", "outlook"))
    rows.append(summarize("先行きの文も入れる・辞書", a.meeting_table(s3, "dict"), m, base_d))
    s3["emb"] = emb(s3.sentence.tolist())
    rows.append(summarize("先行きの文も入れる・埋め込み", a.meeting_table(s3, "emb"), m, base_e))
    # 4
    s4 = base_scores.sort_values(["date", "i"]).groupby("date").head(1)
    rows.append(summarize("最初の文だけ・辞書", a.meeting_table(s4, "dict"), m, base_d))
    rows.append(summarize("最初の文だけ・埋め込み", a.meeting_table(s4, "emb"), m, base_e))
    # 5, 6
    s5 = base_scores.copy()
    s5["emb"] = emb(s5.sentence.tolist(), prefix="トピック: ")
    rows.append(summarize("埋め込み・前置き「トピック: 」", a.meeting_table(s5, "emb"), m, base_e))
    s6 = base_scores.copy()
    s6["emb"] = emb(s6.sentence.tolist(), npos=2)
    rows.append(summarize("埋め込み・基準文2つずつ", a.meeting_table(s6, "emb"), m, base_e))
    # 7
    rows.append(summarize("2020年を除く・辞書", base_d[~base_d.date.dt.year.eq(2020)], m, base_d))
    rows.append(summarize("2020年を除く・埋め込み", base_e[~base_e.date.dt.year.eq(2020)], m, base_e))
    out = pd.DataFrame(rows)
    out.to_csv(RES / "robustness.csv", index=False)
    print(out.to_string())


if __name__ == "__main__":
    main()
