"""03_分析：公表文の「景気の現状判断の文」から、会合ごとの強気・弱気のスコアを作り、景気・金利・株価と比べる

スコアは2通り
- 辞書法：文ごとに（強気語の数 − 弱気語の数）÷（強気語＋弱気語）を出し、会合で平均（−1〜+1）
- 埋め込み：ruri-v3-30m で文をベクトルにし、強気の基準文5つとの近さ − 弱気の基準文5つとの近さを会合で平均
比べる相手
- 景気動向指数（CI 一致）の12か月前比（3か月前比も参考に）：会合の2か月前の月（会合の時点で公表済み）と、会合の6か月後の月（先の動き）
- 景気基準日付（山・谷）
- 無担保コールレート（政策金利）、長期金利、TOPIX の会合月の前月比
"""
import json
import numpy as np
import pandas as pd
from common import DATA, RAW, RES, POS, NEG, ANCHOR_POS, ANCHOR_NEG, MODEL, SEED

START = "2008-01-01"
MINN = 1   # 現状判断の文が1つ以上ある会合を使う（3つ以上に絞った場合は 03b_頑健性 で確かめる）


def dict_score(s, pos=POS, neg=NEG):
    p = sum(s.count(w) for w in pos)
    n = sum(s.count(w) for w in neg)
    return 0.0 if p + n == 0 else (p - n) / (p + n)


def embed_scores(sentences, prefix=""):
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(MODEL, device="cpu")
    E = m.encode([prefix + s for s in sentences], batch_size=64, normalize_embeddings=True)
    P = m.encode([prefix + s for s in ANCHOR_POS], normalize_embeddings=True)
    N = m.encode([prefix + s for s in ANCHOR_NEG], normalize_embeddings=True)
    return (E @ P.T).mean(1) - (E @ N.T).mean(1)


def monthly():
    ci = pd.read_csv(RAW / "f13_ci.csv", parse_dates=["month"]).set_index("month")
    ci["ci3"] = ci.ci_coin.pct_change(3, fill_method=None) * 100
    ci["ci12"] = ci.ci_coin.pct_change(12, fill_method=None) * 100
    cr = pd.read_csv(RAW / "f43_boj_callrate.csv", encoding="utf-8-sig")
    cr["month"] = pd.to_datetime(cr.date.astype(str) + "01")
    cr = cr.set_index("month").value.rename("call")
    tl = pd.read_csv(RAW / "f18_topix_longrate.csv", parse_dates=["month"]).set_index("month")
    tl.columns = ["topix", "long"]
    m = ci[["ci_coin", "ci3", "ci12"]].join(cr, how="outer").join(tl, how="outer")
    m["topix_ret"] = m.topix.pct_change(fill_method=None) * 100
    return m


def cycle_flags(months):
    c = pd.read_csv(RAW / "cycle_dates.csv")
    c["month"] = pd.to_datetime(c.month + "-01")
    peaks = c[c.type == "peak"].month.tolist()
    troughs = c[c.type == "trough"].month.tolist()
    f = pd.Series(0, index=months)
    for p in peaks:
        t = [x for x in troughs if x > p]
        end = t[0] if t else months.max()
        f[(f.index > p) & (f.index <= end)] = 1
    return f, peaks, troughs


def build(sen, dpos=POS, dneg=NEG, kinds=("current",)):
    s = sen[sen.kind2.isin(kinds) & (sen.date >= START)].copy()
    s["dict"] = [dict_score(x, dpos, dneg) for x in s.sentence]
    return s


def meeting_table(s, col):
    g = s.groupby("date").agg(n=("sentence", "size"), score=(col, "mean")).reset_index()
    g["date"] = pd.to_datetime(g.date)
    g["month"] = g.date.dt.to_period("M").dt.to_timestamp()
    return g


def attach(g, m):
    out = g.copy()
    lag = (out.month - pd.DateOffset(months=2))
    lead = (out.month + pd.DateOffset(months=6))
    out["ci12_known"] = m.ci12.reindex(lag).values    # 会合の時点で公表済みの景気（12か月前比）
    out["ci12_after"] = m.ci12.reindex(lead).values   # 会合の6か月後（先の動き）
    out["ci3_known"] = m.ci3.reindex(lag).values
    out["call"] = m.call.reindex(out.month).values
    out["long"] = m.long.reindex(out.month).values
    out["topix_ret"] = m.topix_ret.reindex(out.month).values
    f, _, _ = cycle_flags(pd.date_range("2007-01-01", "2026-12-01", freq="MS"))
    out["recession"] = f.reindex(out.month).values
    return out


def corr_table(t):
    rows = []
    for c in ["ci12_known", "ci12_after", "ci3_known", "topix_ret"]:
        x = t[["score", c]].dropna()
        rows.append({"vs": c, "n": len(x), "r": x.corr().iloc[0, 1]})
    d = t[["score"]].diff().join(t[["topix_ret"]]).dropna()
    rows.append({"vs": "score_change_vs_topix_ret", "n": len(d), "r": d.corr().iloc[0, 1]})
    return pd.DataFrame(rows)


def turning_points(t, col="score"):
    """直近3会合の平均でならしたスコア（その時点までの会合だけを使う）が、正から負・負から正に変わった会合"""
    sm = t[col].rolling(3, min_periods=2).mean()
    sg = np.sign(sm)
    ch = t.loc[(sg != sg.shift()) & sg.shift().notna() & (sg != 0), ["date"]].copy()
    ch["to"] = np.where(sg[ch.index] > 0, "強気へ", "弱気へ")
    return ch, sm


def main():
    rng = np.random.default_rng(SEED)
    sen = pd.read_csv(DATA / "sentences.csv")
    s = build(sen)
    print("current sentences", len(s), "meetings", s.date.nunique())
    s["emb"] = embed_scores(s.sentence.tolist())
    s[["date", "i", "sentence", "dict", "emb"]].to_csv(RES / "sentence_scores.csv", index=False)

    m = monthly()
    td = attach(meeting_table(s, "dict"), m)
    te = attach(meeting_table(s, "emb"), m)
    n_all = len(td)
    keep = td.n >= MINN
    td, te = td[keep].reset_index(drop=True), te[keep].reset_index(drop=True)
    td["score_emb"] = te.score
    td["score_emb_z"] = (te.score - te.score.mean()) / te.score.std()
    td["score_dict_z"] = (td.score - td.score.mean()) / td.score.std()
    td.to_csv(RES / "meeting_scores.csv", index=False)

    res = {"n_meetings_all": int(n_all), "n_meetings": int(len(td)), "n_sentences": int(len(s)), "n_sentences_used": int(td.n.sum()),
           "first": str(td.date.min().date()), "last": str(td.date.max().date()),
           "dict_emb_corr": float(td.score.corr(te.score))}
    ct = corr_table(td).assign(method="dict")
    ce = corr_table(te).assign(method="emb")
    ctab = pd.concat([ct, ce])
    ctab.to_csv(RES / "correlations.csv", index=False)
    res["corr"] = ctab.round(3).to_dict("records")

    # 後退期と拡張期の平均
    res["by_phase"] = td.groupby("recession").agg(n=("score", "size"), dict=("score", "mean"), emb_z=("score_emb_z", "mean")).round(3).reset_index().to_dict("records")

    # 年ごとの平均
    yr = td.groupby(td.date.dt.year).agg(n=("score", "size"), dict=("score", "mean"), emb_z=("score_emb_z", "mean"))
    yr.to_csv(RES / "yearly.csv")

    # 転換点（辞書・埋め込み）
    tpd, smd = turning_points(td, "score")
    tpe, sme = turning_points(td.assign(score=td.score_emb_z), "score")
    td["smooth_dict"] = smd
    td["smooth_emb_z"] = sme
    td.to_csv(RES / "meeting_scores.csv", index=False)
    tpd.assign(method="dict").to_csv(RES / "turning_points_dict.csv", index=False)
    tpe.assign(method="emb").to_csv(RES / "turning_points_emb.csv", index=False)
    res["turning_dict"] = [f"{d.date()} {t}" for d, t in zip(tpd.date, tpd.to)]
    res["turning_emb"] = [f"{d.date()} {t}" for d, t in zip(tpe.date, tpe.to)]
    _, peaks, troughs = cycle_flags(pd.date_range("2007-01-01", "2026-12-01", freq="MS"))
    res["cycle"] = {"peaks": [str(p.date()) for p in peaks if p.year >= 2007], "troughs": [str(t.date()) for t in troughs if t.year >= 2007]}

    # 景気に対して先か後か：会合スコアと CI3 の月のずれ（−6〜+6 か月）
    lags = []
    for k in range(-6, 7):
        for h, ser in (("12", m.ci12), ("3", m.ci3)):
            x = ser.reindex(td.month + pd.DateOffset(months=k)).values
            ok = ~np.isnan(x)
            lags.append({"h": h, "k": k, "r_dict": np.corrcoef(td.score[ok], x[ok])[0, 1],
                         "r_emb": np.corrcoef(te.score[ok], x[ok])[0, 1], "n": int(ok.sum())})
    lags = pd.DataFrame(lags)
    lags.to_csv(RES / "lag_corr.csv", index=False)
    l12 = lags[lags.h == "12"]
    res["lag_best_dict"] = l12.loc[l12.r_dict.idxmax()].to_dict()
    res["lag_best_emb"] = l12.loc[l12.r_emb.idxmax()].to_dict()
    res["lag12"] = l12[["k", "r_dict", "r_emb"]].round(3).to_dict("records")

    # 政策金利を変えた会合（公表文の題名から）のスコア
    # 会合の翌月と前月のコールレートの差が 0.1%ポイントを超えた会合を「利上げの会合」とする
    nxt = m.call.reindex(td.month + pd.DateOffset(months=1)).values
    prv = m.call.reindex(td.month - pd.DateOffset(months=1)).values
    td["policy_change"] = (nxt - prv) > 0.1
    res["policy_change_meetings"] = td.loc[td.policy_change, ["date", "score", "score_emb_z"]].assign(date=lambda d: d.date.dt.strftime("%Y-%m-%d")).round(3).to_dict("records")
    td.to_csv(RES / "meeting_scores.csv", index=False)
    res["mean_score_all"] = float(td.score.mean())

    # 単語ごとの寄与（どの語がスコアを動かしたか）：語ごとの出現回数を年で数える
    words = []
    for w in POS + NEG:
        c = s.groupby(pd.to_datetime(s.date).dt.year).sentence.apply(lambda x: x.str.count(w).sum())
        words.append(pd.Series(c, name=w))
    W = pd.concat(words, axis=1).fillna(0).astype(int)
    W.to_csv(RES / "word_counts_by_year.csv")
    res["top_words"] = W.sum().sort_values(ascending=False).head(12).to_dict()

    # ブートストラップ：CI と のの相関の 95% 区間（会合を復元抽出、1000回）
    x = td[["score", "ci12_known"]].dropna().values
    xe = te.assign(ci=td.ci12_known)[["score", "ci"]].dropna().values
    bs, be = [], []
    for _ in range(1000):
        i = rng.integers(0, len(x), len(x))
        bs.append(np.corrcoef(x[i, 0], x[i, 1])[0, 1])
        j = rng.integers(0, len(xe), len(xe))
        be.append(np.corrcoef(xe[j, 0], xe[j, 1])[0, 1])
    res["ci_corr_ci95_dict"] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
    res["ci_corr_ci95_emb"] = [float(np.percentile(be, 2.5)), float(np.percentile(be, 97.5))]

    json.dump(res, open(RES / "key_numbers.json", "w"), ensure_ascii=False, indent=1, default=float)
    print(json.dumps(res, ensure_ascii=False, indent=1, default=float))
    print(yr.round(3).to_string())


if __name__ == "__main__":
    main()
