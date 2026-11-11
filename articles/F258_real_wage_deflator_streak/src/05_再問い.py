"""05 再問い：連続マイナスを途中で切ったのは、賞与の多い月だったのか？
現金給与総額（賞与を含む）と、きまって支給する給与（賞与などを除く）で、2022〜2024年の向きを月ごとに比べる。"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, CPI, SHORT

m = pd.read_csv(DATA / "monthly_calc.csv", parse_dates=["month"]).set_index("month")
real = lambda n, p: (((1 + n / 100) / (1 + p / 100) - 1) * 100).round(1) + 0.0
w = m.loc["2022-01-01":"2024-12-01"]
tab = pd.DataFrame({
    "名目_総額": w.pub_total, "名目_きまって": w.pub_regular, "物価_公表と同じ": w.p_0163.round(2),
    "実質_総額": real(w.pub_total, w.p_0163), "実質_きまって": real(w.pub_regular, w.p_0163),
    "実質_総額_コアコア": real(w.pub_total, w.p_0178),
})
tab["伸びの差_総額−きまって"] = (tab["名目_総額"] - tab["名目_きまって"]).round(1)
tab["総額だけ0以上"] = (tab["実質_総額"] >= 0) & (tab["実質_きまって"] < 0)
tab.to_csv(RES / "reask_bonus_2022_2024.csv")
cut = tab[tab["総額だけ0以上"]]
out = dict(cut_months=[str(t)[:7] for t in cut.index],
           cut_detail=cut[["実質_総額", "実質_きまって", "伸びの差_総額−きまって"]].round(2).reset_index().astype(str).to_dict("records"),
           neg_total=int((tab["実質_総額"] < 0).sum()), neg_regular=int((tab["実質_きまって"] < 0).sum()), months=len(tab))
# きまって支給する給与での、物価ごとの最長連続（2022〜2024年）
def longest(neg):
    best = cur = 0; s = bs = be = None
    for t, v in neg.items():
        if v:
            cur += 1; s = t if cur == 1 else s
            if cur > best: best, bs, be = cur, s, t
        else:
            cur = 0
    return best, str(bs)[:7], str(be)[:7]
out["regular_longest_by_cpi"] = {SHORT[k]: longest(real(w.pub_regular, w[f"p_{k}"]) < 0) for k in CPI}
out["total_longest_by_cpi"] = {SHORT[k]: longest(real(w.pub_total, w[f"p_{k}"]) < 0) for k in CPI}
out["wage_switch_gain"] = {n: out["regular_longest_by_cpi"][n][0] - out["total_longest_by_cpi"][n][0] for n in out["total_longest_by_cpi"]}
out["deflator_spread"] = {"total": [min(v[0] for v in out["total_longest_by_cpi"].values()), max(v[0] for v in out["total_longest_by_cpi"].values())], "regular": [min(v[0] for v in out["regular_longest_by_cpi"].values()), max(v[0] for v in out["regular_longest_by_cpi"].values())]}
# 月ごと（暦月）の向きの入れ替わり（2015〜）と賞与の月
f = pd.read_csv(RES / "flip_months.csv", parse_dates=[0], index_col=0)["flip"]
bonus = f.index.month.isin([6, 7, 12])
out["flip_share_bonus_months"] = float(f[bonus].mean()); out["flip_share_other_months"] = float(f[~bonus].mean())
json.dump(out, open(RES / "reask.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
