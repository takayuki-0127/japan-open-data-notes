"""03 分析：60歳・65歳の就業率の段差を、年×男女ごとに回帰不連続で推定する。
基本：左右5歳ずつ（例：60歳なら55〜59歳と60〜64歳）、左右で傾きが違う1次式、三角カーネル、HC1 標準誤差。
年齢は1歳刻みで点が少ないため、HC1 の区間は目安にとどめ、「段差のない年齢」での推定（偽の境界）の分布と比べて判断する。"""
import numpy as np, pandas as pd
from common import DATA, RES, YEARS, SEXES, CUTOFFS, H, rd

df = pd.read_csv(DATA / "lfs_single_age.csv")
jp = pd.read_csv(DATA / "lfs_single_age_2015_japanese.csv")
pr = pd.read_csv(DATA / "lfs_single_age_2020_pref.csv")
g = lambda y, s, d=df: d[(d.year == y) & (d.sex == s)]

# 1. 基本の推定
main = []
for y in YEARS:
    for s in SEXES:
        for c in CUTOFFS:
            r = rd(g(y, s), c); r.update(year=y, sex=s, cutoff=c)
            sub = g(y, s).set_index("age")
            r["rate_left"] = sub.loc[c - 1, "emp_rate"] * 100; r["rate_right"] = sub.loc[c, "emp_rate"] * 100
            r["raw_diff"] = r["rate_right"] - r["rate_left"]
            main.append(r)
main = pd.DataFrame(main)
main.to_csv(RES / "rd_main.csv", index=False, encoding="utf-8")

# 2. 偽の境界（段差がないはずの年齢）。
# 窓が本物の境界（60・65歳）をまたぐと本物の段差を拾ってしまうので、窓（c-3〜c+2歳）が 60・65 をまたがない年齢だけを使う。
# 本物の境界も同じ窓の幅（h=3）で推定し直して比べる。
HP = 3
def crosses(c, h=HP):
    return any(c - h < k <= c + h - 1 for k in CUTOFFS)
PLAC_CUTS = [c for c in range(45, 81) if c not in CUTOFFS and not crosses(c)]
plac = []
for y in YEARS:
    for s in SEXES:
        d = g(y, s)
        for c in PLAC_CUTS:
            if c + HP - 1 > d.age.max(): continue
            r = rd(d, c, h=HP); r.update(year=y, sex=s, cutoff=c); plac.append(r)
plac = pd.DataFrame(plac)
plac.to_csv(RES / "rd_placebo.csv", index=False, encoding="utf-8")
rank = []
for y in YEARS:
    for s in SEXES:
        p = plac[(plac.year == y) & (plac.sex == s)]["jump"].values
        for c in CUTOFFS:
            j = rd(g(y, s), c, h=HP)["jump"]
            rank.append(dict(year=y, sex=s, cutoff=c, jump_h3=j, placebo_min=p.min(), placebo_max=p.max(),
                             placebo_sd=p.std(ddof=1), share_placebo_le=(p <= j).mean(), n_placebo=len(p)))
pd.DataFrame(rank).to_csv(RES / "rd_vs_placebo.csv", index=False, encoding="utf-8")

# 3. 頑健性：バンド幅・次数・カーネル・人口の重み・日本人のみ・結果変数
rob = []
for y in YEARS:
    for c in CUTOFFS:
        d = g(y, "総数")
        for h in range(3, 9):
            for p in [1, 2]:
                if p == 2 and h < 4: continue
                r = rd(d, c, h=h, p=p); r.update(year=y, cutoff=c, spec=f"h={h}, {p}次"); rob.append(r)
        for lab, kw in [("一様カーネル", dict(kernel="uni")), ("人口で重み", dict(weight_pop=True)),
                        ("労働力率", dict(y="lf_rate"))]:
            r = rd(d, c, **kw); r.update(year=y, cutoff=c, spec=lab); rob.append(r)
for c in CUTOFFS:
    r = rd(jp[jp.sex == "総数"], c); r.update(year=2015, cutoff=c, spec="日本人のみ"); rob.append(r)
rob = pd.DataFrame(rob)
rob.to_csv(RES / "rd_robustness.csv", index=False, encoding="utf-8")

# 4. 完全失業率の段差（仕事を探す人が増えるか）
un = []
for y in YEARS:
    for s in ["男", "女"]:
        for c in CUTOFFS:
            r = rd(g(y, s), c, y="unemp_rate"); r.update(year=y, sex=s, cutoff=c); un.append(r)
pd.DataFrame(un).to_csv(RES / "rd_unemployment.csv", index=False, encoding="utf-8")

# 5. 2020年 都道府県ごと（男女計）
pf = []
for pref, d in pr[pr.sex == "総数"].groupby("pref"):
    for c in CUTOFFS:
        r = rd(d, c); r.update(pref=pref, cutoff=c); pf.append(r)
pf = pd.DataFrame(pf)
pf.to_csv(RES / "rd_pref2020.csv", index=False, encoding="utf-8")

# 表示
pd.set_option("display.width", 200)
print(main[main.sex == "総数"][["year", "cutoff", "jump", "lo", "hi", "raw_diff", "rate_left", "rate_right"]].round(2))
print(main[main.sex != "総数"].pivot_table(index=["cutoff", "sex"], columns="year", values="jump").round(1))
print(pd.read_csv(RES / "rd_vs_placebo.csv").query("sex=='総数'").round(2))
print(rob.pivot_table(index=["cutoff", "spec"], columns="year", values="jump").round(1))
print(pd.DataFrame(un).pivot_table(index=["cutoff", "sex"], columns="year", values="jump").round(2))
print(pf.groupby("cutoff").jump.describe().round(2))
