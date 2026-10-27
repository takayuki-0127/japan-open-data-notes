"""03b その時点までのデータだけで推定（リアルタイムに近い形）

各月 t（1995年1月〜）について、1985年〜t のデータで本体と同じモデルを推定し直し、
t の月の「その月まで」の後退期の確率を記録する。前の月の推定値を初期値にする（毎年1月と最初の月だけ、乱数の初期値10通りとも比べて良いほうを使う）。
注意：使っているのは今の時点の改定後のデータで、当時実際に公表されていた値（速報値）ではない。
"""
import json
import common  # noqa: F401
import numpy as np
import pandas as pd
from common import DATA, RES, cycle_dates, episodes
from msmodel import fit_ms, nonexp_prob, classify, scores, months_between

d = pd.read_csv(DATA / "monthly.csv", parse_dates=["month"]).set_index("month")
cyc = cycle_dates()
y = d["ci_m3"].dropna()
summary = json.load(open(RES / "summary.json"))
probs = pd.read_csv(RES / "probs_main.csv", index_col=0, parse_dates=True)
ck = RES / "realtime_probs.csv"
rt = {}
if ck.exists():
    rt = pd.read_csv(ck, index_col=0, parse_dates=True).iloc[:, 0].to_dict()
prev = None
for t in y["1995-01":].index:
    if t in rt:
        continue
    # 毎年1月だけ乱数の初期値10通りも試し、ほかの月は前の月の推定値から始める（計算時間を抑えるため）
    rr = fit_ms(y[:t], k=3, switching_variance=False, start_params=prev,
                search_reps=10, n_seeds=1 if (prev is None or t.month == 1) else 0)
    prev = rr.params.values
    rt[t] = float(nonexp_prob(rr, "filtered").iloc[-1])
    if t.month == 12:
        pd.Series(rt, name="後退期の確率（その時点まで推定）").sort_index().to_csv(ck, encoding="utf-8-sig")
rt = pd.Series(rt, name="後退期の確率（その時点まで推定）").sort_index()
rt.to_csv(RES / "realtime_probs.csv", encoding="utf-8-sig")

# 後退のサインを「確率が2か月続けて0.5を超えた月」、回復のサインを「2か月続けて0.5を下回った月」とする
def first_run(s, cond, start, end):
    s = s[start:end]
    ok = cond(s)
    for i in range(1, len(ok)):
        if ok.iloc[i] and ok.iloc[i - 1]:
            return s.index[i]
    return None

rows = []
peaks = cyc[cyc.type == "peak"].month.tolist(); troughs = cyc[cyc.type == "trough"].month.tolist()
for p in peaks:
    if p < pd.Timestamp("1995-06-01"):
        continue
    t = [x for x in troughs if x > p][0]
    sig = first_run(rt, lambda s: s > 0.5, p - pd.DateOffset(months=6), t)
    rec = first_run(rt, lambda s: s < 0.5, t - pd.DateOffset(months=6), t + pd.DateOffset(months=24))
    rows.append({"山": p.strftime("%Y-%m"), "谷": t.strftime("%Y-%m"),
                 "後退のサインが出たデータの月": sig.strftime("%Y-%m") if sig is not None else "出ず",
                 "山からの月数": months_between(p, sig) if sig is not None else np.nan,
                 "回復のサインが出たデータの月": rec.strftime("%Y-%m") if rec is not None else "出ず",
                 "谷からの月数": months_between(t, rec) if rec is not None else np.nan})
rtt = pd.DataFrame(rows)
rtt.to_csv(RES / "realtime_turning_points.csv", index=False, encoding="utf-8-sig")
# 公式の後退期以外で、その時点の確率が2か月続けて0.5を超えた区間（空振り）
flag_rt = ((rt > 0.5) & (rt.shift(1) > 0.5)).astype(int)
off = d["recession"].reindex(rt.index)
fa = []
for s, e in episodes(flag_rt):
    win = off[s - pd.DateOffset(months=6): e]
    if win.sum() == 0:
        fa.append((s.strftime("%Y-%m"), e.strftime("%Y-%m")))
summary["リアルタイム"] = {"期間": f"{rt.index.min():%Y-%m}〜{rt.index.max():%Y-%m}", "空振り": fa,
                         **scores(classify(rt, 2), d["recession"])}
summary["最新"] = {"月": f"{y.index.max():%Y-%m}", "後退期の確率（平滑化）": float(probs["後退期の確率（平滑化）"].iloc[-1]),
                 "後退期の確率（その時点まで推定）": float(rt.iloc[-1])}
print(rtt.to_string()); print(summary["リアルタイム"], summary["最新"])
json.dump(summary, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=str)
