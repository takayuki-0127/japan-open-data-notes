"""03 分析：6つの物価で実質賃金の前年同月比を作り、「連続マイナス」の長さと向きの入れ替わりを数える。"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, CPI, SHORT

m = pd.read_csv(DATA / "monthly.csv", parse_dates=["month"]).set_index("month")
K = list(CPI)
for k in K:
    m[f"p_{k}"] = (m[f"cpi_{k}"] / m[f"cpi_{k}"].shift(12) - 1) * 100
# 名目の伸び：公表の伸び率（段差を直した値）と、指数から計算した値
m["n_pub_total"] = m["pub_total"]
m["n_pub_regular"] = m["pub_regular"]
m["n_idx_total"] = (m["idx_total"] / m["idx_total"].shift(12) - 1) * 100


def real(n, p):
    return ((1 + n / 100) / (1 + p / 100) - 1) * 100


def runs(neg):
    """True が続く区間のリスト [(開始, 終了, 長さ)]"""
    out, start, prev = [], None, None
    for t, v in neg.items():
        if v and start is None:
            start = t
        if not v and start is not None:
            out.append((start, prev, int(((prev.year - start.year) * 12 + prev.month - start.month) + 1)))
            start = None
        prev = t
    if start is not None:
        out.append((start, prev, int(((prev.year - start.year) * 12 + prev.month - start.month) + 1)))
    return out


def summarize(nom="n_pub_total", start="2015-01-01", rounding=True, ma=False):
    rows, signs = [], {}
    for k in K:
        r = real(m[nom], m[f"p_{k}"])
        if ma:
            r = r.rolling(3).mean()
        r = r.loc[start:"2026-08-01"].dropna()
        if rounding:
            r = r.round(1)
        neg = r < 0
        signs[k] = np.sign(r)
        rs = runs(neg)
        long = max(rs, key=lambda x: x[2]) if rs else (None, None, 0)
        rw = runs(neg.loc["2022-01-01":"2024-12-01"])
        ep = max(rw, key=lambda x: x[2]) if rw else (None, None, 0)
        last = r.iloc[-1]
        # 直近の同じ向きの連続
        cur = 1
        for v in r.iloc[::-1].iloc[1:]:
            if np.sign(v) == np.sign(last) and v != 0:
                cur += 1
            else:
                break
        rows.append(dict(cpi=k, name=SHORT[k], months=len(r), neg_months=int(neg.sum()),
                         longest=long[2], longest_from=str(long[0])[:7], longest_to=str(long[1])[:7],
                         ep2023=ep[2], ep_from=str(ep[0])[:7], ep_to=str(ep[1])[:7],
                         last=float(last), last_streak=cur, mean=float(r.mean())))
    df = pd.DataFrame(rows)
    sg = pd.DataFrame(signs)
    dis = (sg.nunique(axis=1) > 1)
    dis_off = (sg.ne(sg["0163"], axis=0)).any(axis=1)
    return df, sg, dis, dis_off


res = {}
main, sg, dis, dis_off = summarize()
main.to_csv(RES / "streaks_main.csv", index=False)
res["main"] = main.to_dict("records")
res["flip_months"] = int(dis.sum()); res["months"] = int(len(dis)); res["flip_share"] = float(dis.mean())
flip = dis[dis]
res["flip_by_calmonth"] = flip.groupby(flip.index.month).size().reindex(range(1, 13), fill_value=0).tolist()
res["flip_by_year"] = flip.groupby(flip.index.year).size().to_dict()
# 向きの数え方を3通り：マイナス・0・プラスの3区分（本文の主な数え方）／プラスとマイナスの両方がある月（0は数えない）／マイナスと0以上に分かれる月
strict = (sg > 0).any(axis=1) & (sg < 0).any(axis=1)
negnn = (sg < 0).any(axis=1) & (sg >= 0).any(axis=1)
bonus = sg.index.month.isin([6, 7, 12])
res["flip_def"] = {"three_way": int(dis.sum()), "strict_plus_minus": int(strict.sum()), "neg_vs_nonneg": int(negnn.sum()),
                   "bonus_months": int(bonus.sum()), "three_way_bonus": int(dis[bonus].sum()), "three_way_other": int(dis[~bonus].sum()),
                   "strict_bonus": int(strict[bonus].sum()), "strict_other": int(strict[~bonus].sum())}
pd.DataFrame({"flip": dis, "flip_strict": strict, "flip_neg_vs_nonneg": negnn}).to_csv(RES / "flip_months.csv")

# 公表の実質と、公表と同じ物価で作った値の照合
r0 = real(m["n_pub_total"], m["p_0163"]).round(1)
chk = pd.DataFrame({"mine": r0, "pub": m["pub_real_total"]}).loc["2000-01-01":"2026-08-01"].dropna()
d = (chk.mine - chk.pub).abs()
pr = chk.pub.loc["2015-01-01":]
rp = runs(pr < 0)
lp = max(rp, key=lambda x: x[2])
res["pub_longest"] = dict(len=lp[2], start=str(lp[0])[:7], end=str(lp[1])[:7])
res["check"] = dict(months=int(len(chk)), exact=int((d < 0.05).sum()), within01=int((d <= 0.1001).sum()),
                    maxdiff=float(d.max()), sign_mismatch=int((np.sign(chk.mine) != np.sign(chk.pub)).sum()))
chk.to_csv(RES / "check_official.csv")

# 頑健性
rob = []
for lab, kw in [("主（現金給与総額・公表の伸び率・丸め・2015年〜）", {}),
                ("きまって支給する給与", dict(nom="n_pub_regular")),
                ("名目を指数から計算", dict(nom="n_idx_total")),
                ("丸めない（0未満）", dict(rounding=False)),
                ("2000年〜", dict(start="2000-01-01")),
                ("3か月移動平均", dict(ma=True))]:
    df, sgx, dx, dox = summarize(**kw)
    for rr in df.to_dict("records"):
        rob.append(dict(case=lab, **rr, flip_share=float(dx.mean())))
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False)
res["robust"] = rob[["case", "name", "longest", "longest_from", "longest_to", "ep2023", "ep_from", "ep_to", "flip_share"]].to_dict("records")

# 物価の伸びの差（2022〜2024年の平均）
p = m.loc["2022-04-01":"2024-05-01", [f"p_{k}" for k in K]].mean()
res["cpi_mean_2022_04_2024_05"] = {SHORT[k]: round(float(p[f"p_{k}"]), 2) for k in K}
json.dump(res, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=str)
m.to_csv(DATA / "monthly_calc.csv")
print(main.to_string())
print(json.dumps({k: res[k] for k in ["flip_months", "months", "flip_share", "flip_by_calmonth", "check", "cpi_mean_2022_04_2024_05"]}, ensure_ascii=False))
print(rob.pivot_table(index="name", columns="case", values="longest").to_string())
print(rob.pivot_table(index="name", columns="case", values="ep2023").to_string())
