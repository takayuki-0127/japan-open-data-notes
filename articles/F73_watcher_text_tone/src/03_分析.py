"""03_分析：景気ウォッチャーのコメントから「強気・弱気」のスコアを作り、DI・景気動向指数と比べる

1. コメントごとの辞書スコア（強気語の数 − 弱気語の数）÷（強気語＋弱気語）、語がなければ 0
2. コメントの判断の記号（◎○□▲×）とテキストのスコアがどれだけ合うか（相関・AUC）
3. 月ごとのテキスト指数（現状・先行き）と、公表の DI（原数値）・CI 一致指数との関係
4. 先行性：テキスト指数・DI と CI の3か月前比の相互相関、グランジャー因果
5. 「記号では表せない分」：月のテキスト指数を、同じコメントの記号の平均で回帰した残差が、翌月の DI や CI を説明するか
6. 話題の語の割合の推移
"""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import grangercausalitytests
from sklearn.metrics import roc_auc_score
from common import COMMENTS, RAW, RES, POS, NEG, POS_CORE, NEG_CORE, TOPICS, SEED

COVID = ("2020-03", "2021-12")


def dict_score(texts, pos=POS, neg=NEG):
    p = sum(texts.str.count(w) for w in pos)
    n = sum(texts.str.count(w) for w in neg)
    tot = p + n
    return np.where(tot > 0, (p - n) / tot.replace(0, 1), 0.0), (tot > 0)


def load():
    c = pd.read_parquet(COMMENTS)
    c["dict"], c["hit"] = dict_score(c.text)
    c["dict_core"], _ = dict_score(c.text, POS_CORE, NEG_CORE)
    di = pd.read_csv(RAW / "di_watcher.csv").set_index("ym")
    ci = pd.read_csv(RAW / "f13_ci.csv", parse_dates=["month"])
    ci["ym"] = ci.month.dt.strftime("%Y-%m")
    ci = ci.set_index("ym")
    ci["ci3"] = ci.ci_coin.pct_change(3, fill_method=None) * 100
    ci["ci1"] = ci.ci_coin.pct_change(1, fill_method=None) * 100
    return c, di, ci


def comment_level(c):
    out = {}
    for k in ("gen", "saki"):
        s = c[c.kind == k]
        out[k] = {
            "n": int(len(s)),
            "hit_share": float(s.hit.mean()),
            "corr_dict_mark": float(np.corrcoef(s.dict, s.score_mark)[0, 1]),
            "mean_by_mark": s.groupby("mark").dict.mean().round(3).to_dict(),
        }
        pn = s[s.mark.isin(["◎", "○", "▲", "×"])]
        y = pn.mark.isin(["◎", "○"]).astype(int)
        out[k]["auc_pos_vs_neg"] = float(roc_auc_score(y, pn.dict))
        pn2 = pn[pn.hit]
        out[k]["auc_pos_vs_neg_hit_only"] = float(roc_auc_score(pn2.mark.isin(["◎", "○"]).astype(int), pn2.dict))
    return out


def monthly(c, col="dict", mask=None):
    s = c if mask is None else c[mask]
    g = s.groupby(["ym", "kind"]).agg(score=(col, "mean"), mark=("score_mark", "mean"), n=(col, "size")).unstack()
    g.columns = [f"{a}_{b}" for a, b in g.columns]
    return g


def zs(x):
    return (x - x.mean()) / x.std()


def xcorr(a, b, lags=range(-6, 7)):
    """lag>0：a が b より lag か月先行（a_t と b_{t+lag} の相関）"""
    return {L: float(pd.concat([a, b.shift(-L)], axis=1).dropna().corr().iloc[0, 1]) for L in lags}


def granger_p(y, x, maxlag=3):
    d = pd.concat([y, x], axis=1).dropna()
    r = grangercausalitytests(d.values, maxlag=maxlag)
    return {int(L): float(r[L][0]["ssr_ftest"][1]) for L in r}


def residual_tone(m):
    """テキスト指数を、同じコメントの記号の平均で回帰した残差（記号では表せない語り口）"""
    X = sm.add_constant(m.mark_gen)
    r = sm.OLS(m.score_gen, X).fit()
    return r.resid, r.rsquared


def lead_reg(m, y, x, ctrl, lag=1):
    """y_{t+lag} − y_t を、x_t と ctrl_t で回帰（HAC）"""
    d = pd.DataFrame({"dy": m[y].shift(-lag) - m[y], "x": m[x]})
    for k in ctrl:
        d[k] = m[k]
    d = d.dropna()
    r = sm.OLS(d.dy, sm.add_constant(d[["x"] + ctrl])).fit(cov_type="HAC", cov_kwds={"maxlags": 3})
    return {"coef": float(r.params["x"]), "lo": float(r.conf_int().loc["x", 0]), "hi": float(r.conf_int().loc["x", 1]),
            "p": float(r.pvalues["x"]), "n": int(r.nobs)}


def analyze(c, di, ci, col="dict", mask=None, tag="base"):
    m = monthly(c, col, mask).join(di[["raw_gen_di", "raw_saki_di", "sa_gen_di", "sa_saki_di"]]).join(ci[["ci_coin", "ci3", "ci1"]])
    m = m[m.index >= "2010-01"]
    m["tone_resid"], r2 = residual_tone(m)
    res = {"tag": tag, "months": int(m.score_gen.notna().sum()),
           "corr_text_di_gen": float(m[["score_gen", "raw_gen_di"]].corr().iloc[0, 1]),
           "corr_text_di_saki": float(m[["score_saki", "raw_saki_di"]].corr().iloc[0, 1]),
           "corr_text_di_gen_diff": float(m[["score_gen", "raw_gen_di"]].diff().corr().iloc[0, 1]),
           "corr_markmean_di_gen": float(m[["mark_gen", "raw_gen_di"]].corr().iloc[0, 1]),
           "r2_text_on_mark": float(r2),
           "corr_text_ci3": float(m[["score_gen", "ci3"]].corr().iloc[0, 1]),
           "corr_di_ci3": float(m[["raw_gen_di", "ci3"]].corr().iloc[0, 1])}
    res["xcorr_text_ci3"] = xcorr(m.score_gen, m.ci3)
    res["xcorr_di_ci3"] = xcorr(m.raw_gen_di, m.ci3)
    res["xcorr_saki_ci3"] = xcorr(m.score_saki, m.ci3)
    res["granger_text_to_ci3"] = granger_p(m.ci3, m.score_gen)
    res["granger_di_to_ci3"] = granger_p(m.ci3, m.raw_gen_di)
    res["granger_ci3_to_text"] = granger_p(m.score_gen, m.ci3)
    # 記号では表せない語り口が、翌月の DI・CI の動きを説明するか（今月の DI を条件にする）
    res["resid_to_next_di"] = lead_reg(m, "raw_gen_di", "tone_resid", ["raw_gen_di"])
    res["resid_to_next_ci3"] = lead_reg(m, "ci3", "tone_resid", ["ci3", "raw_gen_di"])
    res["saki_to_next_gen_di"] = lead_reg(m, "raw_gen_di", "score_saki", ["raw_gen_di", "raw_saki_di"])
    return m, res


def topics(c):
    rows = {}
    for name, ws in TOPICS.items():
        pat = "|".join(ws)
        rows[name] = c[c.kind == "gen"].assign(h=c.text.str.contains(pat)).groupby("ym").h.mean() * 100
    return pd.DataFrame(rows)


def event_table(m):
    ev = {"東日本大震災": "2011-03", "消費税8%": "2014-04", "消費税10%": "2019-10", "コロナ1回目の緊急事態": "2020-04",
          "景気の山（2018-10）": "2018-10"}
    out = []
    for k, ym in ev.items():
        i = m.index.get_loc(ym)
        sl = m.iloc[i - 1:i + 2]
        out.append({"出来事": k, "月": ym,
                    "テキスト_前月": round(sl.score_gen.iloc[0], 3), "テキスト_当月": round(sl.score_gen.iloc[1], 3),
                    "DI原_前月": round(sl.raw_gen_di.iloc[0], 1), "DI原_当月": round(sl.raw_gen_di.iloc[1], 1)})
    return pd.DataFrame(out)


if __name__ == "__main__":
    c, di, ci = load()
    cl = comment_level(c)
    m, res = analyze(c, di, ci)
    m.to_csv(RES / "monthly_index.csv")
    topics(c).round(2).to_csv(RES / "topic_share.csv")
    event_table(m).to_csv(RES / "events.csv", index=False)
    # 上位の語（本文は出さず、語の数だけ）
    cnt = {w: int(c.text.str.count(w).sum()) for w in POS + NEG}
    pd.Series(cnt).sort_values(ascending=False).to_csv(RES / "dict_word_counts.csv", header=["count"])
    json.dump({"comment_level": cl, "base": res}, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=str)
    print(json.dumps(cl, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items()}, ensure_ascii=False, indent=1, default=str))
    print(event_table(m))
