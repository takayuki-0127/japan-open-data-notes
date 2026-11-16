"""03 分析：ひとり暮らしの増加の要因分解（シャープレイ値）、頑健性、問い直し（オフライン）。"""
import json, pathlib, itertools
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
D = pd.read_csv(ROOT / "data" / "alone_pop.csv")
AGES = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64",
        "65-69", "70-74", "75-79", "80-84", "85+"]
OLD = AGES[10:]; YOUNG = AGES[:10]
MAR = ["未婚", "有配偶", "死別", "離別"]
FACT = ["人口の大きさ", "年齢・男女の構成", "配偶関係の構成", "ひとりで暮らす割合"]
def r(x, n=1): return float(round(float(x), n))

def parts(year, ages=None, sexes=("男", "女")):
    q = D[(D.year == year) & D.age.isin(ages or AGES) & D.sex.isin(sexes)].set_index(["sex", "age", "marital"]).sort_index()
    pop = q["pop"].astype(float); alone = q["alone"].astype(float)
    sa = pop.groupby(level=["sex", "age"]).sum()
    N = pop.sum()
    c = sa / N
    m = pop / sa.reindex(pop.index.droplevel("marital")).values
    lam = (alone / pop).fillna(0.0)
    return {"人口の大きさ": N, "年齢・男女の構成": c, "配偶関係の構成": m, "ひとりで暮らす割合": lam}

def L(f):
    c = f["年齢・男女の構成"].reindex(f["配偶関係の構成"].index.droplevel("marital")).values
    return float(f["人口の大きさ"] * np.sum(c * f["配偶関係の構成"].values * f["ひとりで暮らす割合"].values))

def shapley(y0, y1, ages=None, sexes=("男", "女"), factors=FACT, merge_nc=False, order=None):
    a, b = parts(y0, ages, sexes), parts(y1, ages, sexes)
    if merge_nc:  # 人口の大きさと年齢構成をまとめる（3要因）
        for f in (a, b):
            f["人口（大きさと年齢）"] = f["人口の大きさ"] * f["年齢・男女の構成"]
        def L3(sel):
            pa = sel["人口（大きさと年齢）"]
            return float(np.sum(pa.reindex(sel["配偶関係の構成"].index.droplevel("marital")).values * sel["配偶関係の構成"].values * sel["ひとりで暮らす割合"].values))
        fs = ["人口（大きさと年齢）", "配偶関係の構成", "ひとりで暮らす割合"]; LL = L3
    else:
        fs = list(factors); LL = L
    contrib = {k: 0.0 for k in fs}
    orders = [order] if order else list(itertools.permutations(fs))
    for od in orders:
        cur = {k: a[k] for k in fs}
        prev = LL(cur)
        for k in od:
            cur[k] = b[k]
            now = LL(cur); contrib[k] += now - prev; prev = now
    contrib = {k: v / len(orders) for k, v in contrib.items()}
    total = LL({k: b[k] for k in fs}) - LL({k: a[k] for k in fs})
    return LL({k: a[k] for k in fs}), LL({k: b[k] for k in fs}), total, contrib

def row(lab, y0, y1, **kw):
    l0, l1, tot, ct = shapley(y0, y1, **kw)
    d = {"分析": lab, "期間": f"{y0}→{y1}", "始め": int(round(l0)), "終わり": int(round(l1)), "増加": int(round(tot))}
    for k, v in ct.items():
        d[f"{k}_人"] = int(round(v)); d[f"{k}_%"] = r(v / tot * 100)
    return d

M = {}
main = row("全体", 1985, 2020)
M["主結果_1985_2020"] = main
s = {k: main[f"{k}_%"] for k in FACT}
M["H1"] = {"高齢化の寄与_%": s["年齢・男女の構成"], "判定": "支持" if s["年齢・男女の構成"] >= 100 / 3 else "外れ"}
M["H2"] = {"配偶関係の寄与_%": s["配偶関係の構成"], "高齢化の寄与_%": s["年齢・男女の構成"],
           "判定": "支持" if s["配偶関係の構成"] < s["年齢・男女の構成"] else "外れ"}
M["H3"] = {"暮らし方の寄与_%": s["ひとりで暮らす割合"], "判定": "支持" if s["ひとりで暮らす割合"] >= 25 else "外れ"}
old = row("65歳以上", 1985, 2020, ages=OLD); yng = row("15〜64歳", 1985, 2020, ages=YOUNG)
M["H4"] = {"65歳以上": old, "15〜64歳": yng,
           "判定": "支持" if (old["年齢・男女の構成_%"] >= 50 and yng["配偶関係の構成_%"] >= 50) else "外れ"}

# ---- 頑健性
rob = [main, old, yng]
rob.append(row("全体（1985→2005、同じ旧分類）", 1985, 2005))
rob.append(row("全体（1995→2020）", 1995, 2020))
rob.append(row("全体（2005→2020）", 2005, 2020))
rob.append(row("男", 1985, 2020, sexes=("男",)))
rob.append(row("女", 1985, 2020, sexes=("女",)))
fixed = row("全体（決まった順番：人口→年齢→配偶関係→割合）", 1985, 2020, order=tuple(FACT))
rob.append(fixed)
l0, l1, tot3, c3 = shapley(1985, 2020, merge_nc=True)
R = pd.DataFrame(rob)
R.to_csv(RES / "decomposition.csv", index=False)
M["頑健性"] = {d["分析"]: {k: d[k] for k in d if k.endswith("_%")} for d in rob[3:]}
M["頑健性"]["3要因"] = {k: r(v / tot3 * 100) for k, v in c3.items()}
M["頑健性"]["判定"] = {
    "H1": {d["分析"]: ("支持" if d["年齢・男女の構成_%"] >= 100 / 3 else "外れ") for d in rob[3:]},
    "H2": {d["分析"]: ("支持" if d["配偶関係の構成_%"] < d["年齢・男女の構成_%"] else "外れ") for d in rob[3:]},
    "H3": {d["分析"]: ("支持" if d["ひとりで暮らす割合_%"] >= 25 else "外れ") for d in rob[3:]},
}

# ---- 記述：年ごとのひとり暮らしの数と割合、配偶関係別の内訳
g = D.groupby(["year", "marital"], sort=True)[["alone"]].sum().unstack("marital")["alone"][MAR]
tot = D.groupby("year")[["pop", "alone"]].sum()
desc = pd.concat([tot, g], axis=1); desc["ひとり暮らしの割合_%"] = (desc["alone"] / desc["pop"] * 100).round(2)
for mm in MAR: desc[f"{mm}_の割合_%"] = (desc[mm] / desc["alone"] * 100).round(1)
desc.index.name = "year"; desc.to_csv(RES / "alone_by_year_marital.csv")
M["記述"] = {str(y): {"ひとり暮らし": int(desc.loc[y, "alone"]), "15歳以上人口": int(desc.loc[y, "pop"]),
                     "割合_%": float(desc.loc[y, "ひとり暮らしの割合_%"]),
                     **{f"{mm}_の割合_%": float(desc.loc[y, f"{mm}_の割合_%"]) for mm in MAR}} for y in desc.index}
# 年齢帯別のひとりで暮らす割合（未婚・有配偶・死別・離別）
lam = D[D.year.isin([1985, 2020])].copy(); lam["rate"] = lam.alone / lam["pop"] * 100
lam["band"] = np.select([lam.age.isin(AGES[:3]), lam.age.isin(AGES[3:10]), lam.age.isin(OLD)], ["15〜29歳", "30〜64歳", "65歳以上"], default="")
lb = lam.groupby(["year", "band", "marital"], sort=True)[["alone", "pop"]].sum(); lb["rate_%"] = (lb.alone / lb["pop"] * 100).round(2)
lb.to_csv(RES / "alone_rate_by_band_marital.csv")
M["ひとりで暮らす割合"] = {f"{y}|{b}|{m}": float(lb.loc[(y, b, m), "rate_%"]) for y, b, m in lb.index}

# ---- 問い直し（結果を見てから足した）：「配偶関係の構成」と「ひとりで暮らす割合」の寄与は、どの年齢帯・配偶関係で生じたか
#      L は m と λ のそれぞれについて1次式なので、要因の寄与はセルごとに足し算で分けられる。
def cell_contrib(factor, y0=1985, y1=2020):
    a, b = parts(y0), parts(y1)
    idx = a[factor].index
    band = pd.Series(np.select([idx.get_level_values("age").isin(AGES[:3]), idx.get_level_values("age").isin(AGES[3:10])],
                               ["15〜29歳", "30〜64歳"], default="65歳以上"), index=idx)
    out = {}
    for bd in ["15〜29歳", "30〜64歳", "65歳以上"]:
        for mm in MAR:
            sel = (band == bd) & (idx.get_level_values("marital") == mm)
            mixed = b[factor].copy(); mixed[~sel.values] = a[factor][~sel.values]
            # 他の要因は通常どおり、この要因だけ「選んだセルだけ変わる」としてシャープレイ値をとる
            bb = dict(b); bb[factor] = mixed
            contrib = 0.0
            for od in itertools.permutations(FACT):
                cur = {k: a[k] for k in FACT}; prev = L(cur)
                for k in od:
                    cur[k] = bb[k]; now = L(cur)
                    if k == factor: contrib += now - prev
                    prev = now
            out[(bd, mm)] = contrib / 24
    return out
q = []
for fac in ["配偶関係の構成", "ひとりで暮らす割合"]:
    cc = cell_contrib(fac)
    for (bd, mm), v in cc.items():
        q.append((fac, bd, mm, int(round(v)), r(v / main["増加"] * 100)))
# 年齢・男女の構成（c）も1次式なので、年齢帯ごとに分けられる
a0, b0 = parts(1985), parts(2020)
cidx = a0["年齢・男女の構成"].index
for bd, ags in [("15〜29歳", AGES[:3]), ("30〜64歳", AGES[3:10]), ("65歳以上", OLD)]:
    sel = cidx.get_level_values("age").isin(ags)
    mixed = b0["年齢・男女の構成"].copy(); mixed[~sel] = a0["年齢・男女の構成"][~sel]
    bb = dict(b0); bb["年齢・男女の構成"] = mixed; contrib = 0.0
    for od in itertools.permutations(FACT):
        cur = {k: a0[k] for k in FACT}; prev = L(cur)
        for k in od:
            cur[k] = bb[k]; now = L(cur)
            if k == "年齢・男女の構成": contrib += now - prev
            prev = now
    q.append(("年齢・男女の構成", bd, "（すべて）", int(round(contrib / 24)), r(contrib / 24 / main["増加"] * 100)))
Q = pd.DataFrame(q, columns=["要因", "年齢帯", "配偶関係", "寄与_人", "増加に対する_%"])
Q.to_csv(RES / "requestion_cells.csv", index=False)
chk = Q.groupby("要因")["寄与_人"].sum().to_dict()
M["問い直し"] = {"セルの合計（主結果と一致するはず）": chk,
               "セル": {f"{a}|{b}|{c}": {"人": d, "%": e} for a, b, c, d, e in q}}

with open(RES / "main.json", "w", encoding="utf-8") as f:
    json.dump(M, f, ensure_ascii=False, indent=1)
print(json.dumps({k: M[k] for k in ["主結果_1985_2020", "H1", "H2", "H3", "H4", "頑健性", "記述"]}, ensure_ascii=False, indent=1))
print(lb)
