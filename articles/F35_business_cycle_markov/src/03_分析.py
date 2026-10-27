"""03 分析：マルコフ切り替えモデルで景気の局面を推定し、景気基準日付と比べる

本体：CI一致指数の3か月前比（月あたり）、3状態（急落・後退・拡張）、平均が切り替わり分散は共通。
後退期の確率＝平均がマイナスの状態（後退・急落）にいる確率の合計。0.5 を超え、3か月以上続いた区間を後退期と判定する。
"""
import json
import common  # noqa: F401  （スレッド数の固定）
import numpy as np
import pandas as pd
from common import DATA, RES, cycle_dates
from msmodel import fit_ms, regime_order, nonexp_prob, classify, scores, match_episodes

RES.mkdir(exist_ok=True)
d = pd.read_csv(DATA / "monthly.csv", parse_dates=["month"]).set_index("month")
cyc = cycle_dates()
summary = json.load(open(RES / "summary.json")) if (RES / "summary.json").exists() else {}

# 1) 本体
y = d["ci_m3"].dropna()
r = fit_ms(y, k=3, switching_variance=False)
order, consts = regime_order(r)
names = {order[0]: "急落", order[1]: "後退", order[2]: "拡張"}
probs = pd.DataFrame({names[i]: r.smoothed_marginal_probabilities[i] for i in range(3)})
probs["後退期の確率（平滑化）"] = nonexp_prob(r, "smoothed")
probs["後退期の確率（その月まで）"] = nonexp_prob(r, "filtered")
probs["CI一致_3か月前比"] = y
probs["公式の後退期"] = d["recession"].reindex(probs.index)
cls = classify(probs["後退期の確率（平滑化）"])
probs["推定の後退期"] = cls
probs.to_csv(RES / "probs_main.csv", encoding="utf-8-sig")
P = r.regime_transition[:, :, 0]
params = pd.DataFrame({
    "状態": [names[i] for i in order],
    "平均（3か月前比、%/月）": [consts[i] for i in order],
    "とどまる確率": [P[i, i] for i in order],
    "平均の続く月数": [1 / (1 - P[i, i]) if P[i, i] < 1 else np.inf for i in order],
    "その状態にいた月数（確率>0.5）": [int((r.smoothed_marginal_probabilities[i] > 0.5).sum()) for i in order],
})
params.to_csv(RES / "params_main.csv", index=False, encoding="utf-8-sig")
summary["本体"] = {**scores(cls, d["recession"]), "sigma2": float(r.params["sigma2"]), "llf": float(r.llf)}
tp, false = match_episodes(cls, cyc)
tp.to_csv(RES / "turning_points_main.csv", index=False, encoding="utf-8-sig")
summary["本体"]["公式にない推定の後退期"] = false
crash_months = [m.strftime("%Y-%m") for m in probs.index[probs["急落"] > 0.5]]
summary["本体"]["急落の月"] = crash_months
print(params.round(3).to_string()); print(tp.to_string()); print("公式にない区間:", false)

# 2) 比べるモデル（頑健性）
variants = {
    "2状態（平均と分散が切り替わる）": dict(col="ci_m3", k=2, sv=True),
    "2状態（平均だけ切り替わる）": dict(col="ci_m3", k=2, sv=False),
    "3状態（平均と分散が切り替わる）": dict(col="ci_m3", k=3, sv=True),
    "前月比で3状態": dict(col="ci_m1", k=3, sv=False),
    "コロナ期を除く（〜2019年12月）2状態": dict(col="ci_m3", k=2, sv=True, end="2019-12"),
    "コロナ期を除く（〜2019年12月）3状態": dict(col="ci_m3", k=3, sv=False, end="2019-12"),
    "鉱工業生産・3状態（1985年〜）": dict(col="iip_m3", k=3, sv=False, start="1985-01"),
    "鉱工業生産・2状態（1985年〜、平均と分散）": dict(col="iip_m3", k=2, sv=True, start="1985-01"),
    "鉱工業生産・3状態（1975年〜）": dict(col="iip_m3", k=3, sv=False),
}
rows = [{"モデル": "本体：CI一致・3か月前比・3状態（平均だけ切り替わる）", **summary["本体"],
         "公式にない推定の後退期": len(false), "見つからなかった公式の後退期": int((tp["推定の始まり"] == "見つからず").sum())}]
rows[0].pop("急落の月"); rows[0].pop("sigma2"); rows[0].pop("llf")
var_probs = {}
tp_all = []
for name, v in variants.items():
    yy = d[v["col"]].dropna()
    if "start" in v:
        yy = yy[v["start"]:]
    if "end" in v:
        yy = yy[:v["end"]]
    rv = fit_ms(yy, k=v["k"], switching_variance=v["sv"])
    pr = nonexp_prob(rv, "smoothed")
    cv = classify(pr)
    tpv, fv = match_episodes(cv, cyc)
    _, cs = regime_order(rv)
    rows.append({"モデル": name, **scores(cv, d["recession"]), "公式にない推定の後退期": len(fv),
                 "見つからなかった公式の後退期": int((tpv["推定の始まり"] == "見つからず").sum()),
                 "状態ごとの平均": ", ".join(f"{c:.2f}" for c in sorted(cs)), "対数尤度": float(rv.llf)})
    var_probs[name] = pr
    tpv.insert(0, "モデル", name)
    tp_all.append(tpv)
pd.concat(tp_all).to_csv(RES / "turning_points_variants.csv", index=False, encoding="utf-8-sig")
acc = pd.DataFrame(rows)
acc.to_csv(RES / "accuracy_models.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(var_probs).to_csv(RES / "probs_variants.csv", encoding="utf-8-sig")
print(acc.drop(columns=["公式にない推定の後退期"]).round(3).to_string())

json.dump(summary, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=str)
