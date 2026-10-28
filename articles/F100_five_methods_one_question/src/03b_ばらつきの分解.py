"""03b 推定値のばらつきを、比べ方・手法・県の扱い・対象のどれが生んだかに分ける（それぞれだけで回帰したときの決定係数）"""
import json
import pandas as pd
import statsmodels.formula.api as smf
from common import RES

S = pd.read_csv(RES / "specifications.csv")
S["meth"] = S.method.str.replace("（.*）", "", regex=True)  # DML の3つ、空間回帰の2つはそれぞれ1つの手法として数える
out = {}
for q in ["q1", "q2"]:
    s = S[S.q == q]
    if q == "q2":
        s = s[s.method != "マッチング"]  # 問い2のマッチングは区間が極端に広く、1つで分散を左右するので除く
    out[q] = {lab: float(smf.ols("coef~" + f, s).fit().rsquared) for lab, f in
              [("比べ方（水準か変化か）", "C(design)"), ("手法", "C(meth)"), ("県の違いを除くか", "C(pref)"),
               ("対象（人口1万人以上だけか）", "C(sample)"), ("比べ方×県の扱い", "C(design)*C(pref)")]}
    out[q]["n"] = len(s)
    main = s[(s.pref) & (s["sample"] == "all")]
    out[q]["範囲（県あり・全体）"] = {d: [float(g.coef.min()), float(g.coef.max())] for d, g in main.groupby("design")}
    print(q, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in out[q].items()})
json.dump(out, open(RES / "variance_share.json", "w"), ensure_ascii=False, indent=1)
