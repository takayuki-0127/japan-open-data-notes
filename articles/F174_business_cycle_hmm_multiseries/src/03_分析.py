"""03 分析：一致系列7本をそのまま並べた隠れマルコフモデル（多変量の正規分布）で景気の局面を推定し、
内閣府の景気基準日付と比べる。

- 状態の数（2〜5）と、系列どうしの連動を認めるか（共分散：対角／フル）を BIC と一致度で比べる
- 本体は BIC がいちばん小さいモデル
- 比べる相手：CI一致指数1本（F35 と同じ材料）、7系列の単純平均1本、7系列の第1主成分1本
- 頑健性：後退とみなす状態の決め方、系列を1本ずつ抜く、C6・C7 を足す、6か月前比、
  コロナ期を除く、1985年から、初期値の乱数、後退と判定する最短の長さ
- おまけ：先行系列7本で同じことをすると、山より早く後退の状態に入るか
"""
import json, time
import numpy as np, pandas as pd
from sklearn.decomposition import PCA
from common import DATA, RAW, RES, SEED, MAIN, LEAD_NAMES
from hmmtools import fit_best, n_params, recession_states, dated_flag, evaluate

t0 = time.time()
m = pd.read_csv(DATA / "monthly.csv", parse_dates=["month"]).set_index("month")
cyc = pd.read_csv(RAW / "cycle_dates.csv"); cyc["month"] = pd.to_datetime(cyc.month + "-01")
rec = m["rec"]
EVAL = ("1975-04-01", "1985-04-01")

def prep(cols, h=3, start="1975-04-01", end="2026-08-01"):
    X = m[[f"g{h}_{c}" for c in cols]].loc[start:end].dropna()
    return (X - X.mean()) / X.std()

def one(Z, name):
    s = Z.mean(axis=1).to_frame(name)
    return (s - s.mean()) / s.std()

def pc1(Z):
    p = PCA(1).fit(Z.values)
    v = p.components_[0] * np.sign(p.components_[0].sum())
    s = pd.DataFrame({"pc1": Z.values @ v}, index=Z.index)
    return (s - s.mean()) / s.std(), float(p.explained_variance_ratio_[0])

def label(mod, Z, rule="sign"):
    if rule == "sign":                       # 平均がマイナスの状態すべて
        return recession_states(mod)
    if rule == "lowest":                     # 平均がいちばん低い状態だけ
        return [int(np.argmin(mod.means_.mean(axis=1)))]
    if rule == "answer":                     # 答え合わせ用：公式の後退期が過半の状態（後知恵）
        st = mod.predict(Z.values); r = rec.reindex(Z.index).values
        return [k for k in range(mod.n_components) if (st == k).sum() and r[st == k].mean() > 0.5]

def score(name, Z, mod, ll, cov, rule="sign", min_len=3, extra=None):
    post = mod.predict_proba(Z.values)
    rs = label(mod, Z, rule)
    prob = pd.Series(post[:, rs].sum(axis=1) if rs else 0.0, index=Z.index)
    flag = dated_flag(prob, Z.index, min_len)
    d = Z.shape[1]
    out = dict(model=name, K=mod.n_components, cov=cov, n_series=d, rule=rule, min_len=min_len,
               start=Z.index[0].strftime("%Y-%m"), end=Z.index[-1].strftime("%Y-%m"),
               loglik=ll, bic=-2 * ll + n_params(mod, cov, d) * np.log(len(Z)), n_rec_states=len(rs))
    if extra:
        out.update(extra)
    tps = {}
    for es in EVAL:
        if pd.Timestamp(es) < Z.index[0] and es.startswith("1985"):
            continue
        es_eff = max(pd.Timestamp(es), Z.index[0])   # 6か月前比は1975年7月から
        ev, tp = evaluate(flag, rec, cyc, start=es_eff)
        tag = es[:4]
        for k, v in ev.items():
            out[f"{k}_{tag}"] = v
        tps[tag] = tp
    return out, prob, flag, tps

def fit_score(name, Z, K, cov="full", **kw):
    seed = kw.pop("seed", SEED)
    mod, ll = fit_best(Z.values, K, cov=cov, n_init=20, seed=seed)
    o, prob, flag, tps = score(name, Z, mod, ll, cov, **kw)
    return o, mod, prob, flag, tps

rows, probs, tpl, params = [], {}, [], []
def keep(o, key, prob, tps):
    rows.append(dict(o, key=key)); probs[key] = prob
    for tag, tp in tps.items():
        tpl.append(tp.assign(key=key, eval_from=tag))

# A) 状態の数と共分散
Z7 = prep(MAIN)
models = {}
for cov in ("diag", "full"):
    for K in (2, 3, 4, 5):
        o, mod, prob, flag, tps = fit_score("一致7系列", Z7, K, cov)
        keep(dict(o, block="A"), f"multi7_{cov}_K{K}", prob, tps)
        models[(cov, K)] = mod
        print("A", cov, K, round(o["bic"], 1), round(o["acc_1975"], 3), round(time.time() - t0))
A = pd.DataFrame([r for r in rows if r.get("block") == "A"])
best = A.loc[A.bic.idxmin()]
COV, KB = best["cov"], int(best["K"])
main = models[(COV, KB)]
print("本体:", COV, KB)
st = main.predict(Z7.values)
for k in range(KB):
    params.append(dict(state=k, stay=main.transmat_[k, k], dur=1 / (1 - main.transmat_[k, k]),
                       mean_avg=main.means_[k].mean(), months=int((st == k).sum()),
                       share_official_rec=float(rec.reindex(Z7.index).values[st == k].mean()),
                       sd_avg=float(np.sqrt(np.diag(main.covars_[k])).mean()),
                       corr_avg=float((np.corrcoef(main.covars_[k]) if False else
                                       (main.covars_[k] / np.sqrt(np.outer(np.diag(main.covars_[k]), np.diag(main.covars_[k]))))
                                       )[np.triu_indices(7, 1)].mean()),
                       **{f"mean_{c}": main.means_[k][i] for i, c in enumerate(MAIN)},
                       first_months=";".join(Z7.index[st == k][:3].strftime("%Y-%m"))))
pd.DataFrame(params).to_csv(RES / "params_main.csv", index=False, float_format="%.4f")
pd.DataFrame({"state": st}, index=Z7.index).to_csv(RES / "states_main.csv")

# B) 比べる相手（同じ状態の数で、1本にまとめてから推定）
for K in (2, 3):
    o, *_rest = fit_score("CI一致指数1本", prep(["ci_coin"], start="1985-04-01"), K, "full")
    keep(dict(o, block="B"), f"ci_K{K}", _rest[1], _rest[3])
    o, *_rest = fit_score("7系列の単純平均1本", one(Z7, "avg7"), K, "full")
    keep(dict(o, block="B"), f"avg7_K{K}", _rest[1], _rest[3])
    P, share = pc1(Z7)
    o, *_rest = fit_score("7系列の第1主成分1本", P, K, "full", extra=dict(pc1_share=share))
    keep(dict(o, block="B"), f"pc1_K{K}", _rest[1], _rest[3])
print("B", round(time.time() - t0))

# C) 頑健性（本体の設定を1つずつ変える）
for rule in ("lowest", "answer"):
    o, prob, flag, tps = score("一致7系列", Z7, main, float(main.score(Z7.values)), COV, rule=rule)
    keep(dict(o, block="C", variant=f"後退とみなす状態：{rule}"), f"rule_{rule}", prob, tps)
for ml in (1, 6):
    o, prob, flag, tps = score("一致7系列", Z7, main, float(main.score(Z7.values)), COV, min_len=ml)
    keep(dict(o, block="C", variant=f"最短の長さ {ml}か月"), f"minlen_{ml}", prob, tps)
for c in MAIN:
    cols = [x for x in MAIN if x != c]
    o, mod, prob, flag, tps = fit_score("一致6系列", prep(cols), KB, COV)
    keep(dict(o, block="C", variant=f"{c} を抜く"), f"drop_{c}", prob, tps)
o, mod, prob, flag, tps = fit_score("一致9系列", prep(MAIN + ["C6", "C7"]), KB, COV)
keep(dict(o, block="C", variant="C6・C7 を足す（9系列）"), "add_C6C7", prob, tps)
o, mod, prob, flag, tps = fit_score("一致7系列", prep(MAIN, h=6, start="1975-07-01"), KB, COV)
keep(dict(o, block="C", variant="6か月前比"), "h6", prob, tps)
o, mod, prob, flag, tps = fit_score("一致7系列", prep(MAIN, end="2019-12-01"), KB, COV)
keep(dict(o, block="C", variant="コロナ期を除く（〜2019年12月）"), "pre_covid", prob, tps)
o, mod, prob, flag, tps = fit_score("一致7系列", prep(MAIN, start="1985-04-01"), KB, COV)
keep(dict(o, block="C", variant="1985年4月から"), "from1985", prob, tps)
for s in (1, 2, 3):
    o, mod, prob, flag, tps = fit_score("一致7系列", Z7, KB, COV, seed=1000 + s)
    keep(dict(o, block="C", variant=f"初期値の乱数 {1000 + s}"), f"seed_{s}", prob, tps)
print("C", round(time.time() - t0))

# D) 先行系列7本
ZL = prep(list(LEAD_NAMES))
for K in (2, 3):
    o, mod, prob, flag, tps = fit_score("先行7系列", ZL, K, "full")
    keep(dict(o, block="D"), f"lead7_K{K}", prob, tps)
print("D", round(time.time() - t0))

R = pd.DataFrame(rows)
R.to_csv(RES / "models_all.csv", index=False, float_format="%.4f")
pd.DataFrame(probs).to_csv(RES / "probs_all.csv", float_format="%.4f")
pd.concat(tpl).to_csv(RES / "turning_points_all.csv", index=False)
json.dump(dict(main_cov=COV, main_K=KB, main_key=f"multi7_{COV}_K{KB}",
               n_months=len(Z7), seconds=round(time.time() - t0)),
          open(RES / "main_choice.json", "w"), ensure_ascii=False, indent=1)
print("done", round(time.time() - t0))
