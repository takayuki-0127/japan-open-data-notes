"""04 傾向スコアマッチング＋差の差、作成時期ごとの効果（Callaway–Sant'Anna 型）、頑健性チェック
結果：results/*.csv"""
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import statsmodels.api as sm
from sklearn.neighbors import NearestNeighbors
from common import DATA, RES, SEED

rng = np.random.default_rng(SEED)
did = pd.read_csv(DATA / "did_muni.csv", dtype={"code5": str})
pl = pd.read_csv(DATA / "plans.csv", dtype=str)
df = did.merge(pl[["code", "first_pub", "R0207"]], on="code", how="left")
Y = [2005, 2010, 2015, 2020]
df = df.dropna(subset=[f"pop{y}" for y in Y]).copy()
df["総人口"] = pd.to_numeric(df["総人口"])
for a, b in [(2005, 2010), (2010, 2015), (2015, 2020)]:
    df[f"d_dens_{b}"] = 100 * (np.log(df[f"dens{b}"]) - np.log(df[f"dens{a}"]))   # 人口密度の変化（対数×100 ≒ %）
    df[f"d_pop_{b}"] = 100 * (np.log(df[f"pop{b}"]) - np.log(df[f"pop{a}"]))
    df[f"d_area_{b}"] = 100 * (np.log(df[f"area{b}"]) - np.log(df[f"area{a}"]))
# 境界の引き直しなどで極端な値（±200%など）が出る市町村があるので、変化は上下1%で丸める（winsorize）
DCOLS = [c for c in df.columns if c.startswith("d_")]
df["n_winsor"] = 0
for c in DCOLS:
    lo, hi = df[c].quantile([0.01, 0.99])
    df["n_winsor"] += ((df[c] < lo) | (df[c] > hi)).astype(int)
    df[c] = df[c].clip(lo, hi)
df["group"] = np.where(df.first_pub.notna(), "作成", np.where(df.R0207.notna(), "作成中", "未作成"))
df["cohort"] = df.first_pub
# 計画前（2010年以前）の共変量
df["x_lpop"] = np.log(df.pop2010); df["x_ldens"] = np.log(df.dens2010); df["x_larea"] = np.log(df.area2010)
df["x_trend"] = df.d_dens_2010; df["x_ptrend"] = df.d_pop_2010; df["x_ndid"] = np.log(df.n_did2010)
df["x_ltot"] = np.log(df["総人口"])   # 市町村の総人口（2020年国勢調査、規模の代わり）
X = ["x_lpop", "x_ldens", "x_trend", "x_ptrend", "x_ndid", "x_ltot"]
XN = {"x_lpop": "DID人口（2010・対数）", "x_ldens": "DID人口密度（2010・対数）", "x_larea": "DID面積（2010・対数）",
      "x_trend": "DID密度の変化（2005→10）", "x_ptrend": "DID人口の変化（2005→10）", "x_ndid": "DIDの数（2010・対数）",
      "x_ltot": "市町村の総人口（対数）"}
# 東京都区部（区ごとに市町村扱い）は計画の対象外なので除く
df = df[~df.code5.str.startswith("131")].copy()
df.to_csv(DATA / "analysis.csv", index=False, encoding="utf-8-sig")
print(df.group.value_counts())

def pscore(d, treat):
    m = sm.Logit(treat.astype(float), sm.add_constant(d[X])).fit(disp=0)
    return m.predict(sm.add_constant(d[X])), m

def smd(a, b):
    return (a.mean() - b.mean()) / np.sqrt((a.var() + b.var()) / 2)

def match(d, ps, treat, k=1, caliper=0.2):
    """傾向スコア（ロジット）の最近傍マッチング（復元抽出・キャリパー＝ロジットの標準偏差×caliper）"""
    lg = np.log(ps / (1 - ps)); cal = caliper * lg.std() if caliper else np.inf
    t = d[treat].index; c = d[~treat].index
    nn = NearestNeighbors(n_neighbors=k).fit(lg[c].values.reshape(-1, 1))
    dist, idx = nn.kneighbors(lg[t].values.reshape(-1, 1))
    pairs = []
    for i, ti in enumerate(t):
        for j in range(k):
            if dist[i, j] <= cal: pairs.append((ti, c[idx[i, j]], 1 / k))
    return pd.DataFrame(pairs, columns=["t", "c", "w"])

def att_matched(d, pairs, y):
    pt = pairs.groupby("t").w.sum()
    cw = pairs.groupby("t").apply(lambda g: np.average(d.loc[g.c, y], weights=g.w), include_groups=False)
    return float((d.loc[pt.index, y] - cw).mean()), pt.index

def boot(fun, d, B=500):
    vals = []
    for b in range(B):
        idx = rng.choice(d.index, len(d), replace=True)
        db = d.loc[idx].reset_index(drop=True)
        try: vals.append(fun(db))
        except Exception: pass
    return np.percentile(vals, [2.5, 97.5])

def est_psm(d, treat_mask, y, k=1, caliper=0.2):
    d = d.reset_index(drop=True); tr = treat_mask.reset_index(drop=True)
    ps, _ = pscore(d, tr); pairs = match(d, ps, tr, k, caliper)
    return att_matched(d, pairs, y)[0]

def est_ipw(d, treat_mask, y):
    d = d.reset_index(drop=True); tr = treat_mask.reset_index(drop=True)
    ps, _ = pscore(d, tr); ps = ps.clip(0.01, 0.99)
    w = ps / (1 - ps)
    return float(d.loc[tr, y].mean() - np.average(d.loc[~tr, y], weights=w[~tr]))

def est_dr(d, treat_mask, y):
    """回帰調整つきの IPW（二重頑健）"""
    d = d.reset_index(drop=True); tr = treat_mask.reset_index(drop=True)
    ps, _ = pscore(d, tr); ps = ps.clip(0.01, 0.99)
    ols = sm.OLS(d.loc[~tr, y], sm.add_constant(d.loc[~tr, X])).fit()
    mu0 = ols.predict(sm.add_constant(d[X]))
    w = ps / (1 - ps)
    return float((d.loc[tr, y] - mu0[tr]).mean() - np.average(d.loc[~tr, y] - mu0[~tr], weights=w[~tr]))

# ---- 1. 本推定：作成（2020年7月までに公表）vs 未作成（取組もなし）
base = df[df.group.isin(["作成", "未作成"])].reset_index(drop=True)
T = base.group == "作成"
ps, logit = pscore(base, T); base["ps"] = ps
pairs = match(base, ps, T)
pairs.to_csv(RES / "pairs.csv", index=False)
open(RES / "pscore_model.txt", "w").write(str(logit.summary()))
bal = []
mt = base.loc[pairs.t]; mc = base.loc[pairs.c]
for x in X + ["d_dens_2015"]:
    bal.append({"変数": XN.get(x, "DID密度の変化（2010→15）※マッチングに使っていない"), "マッチング前": smd(base.loc[T, x], base.loc[~T, x]),
                "マッチング後": smd(mt[x], mc[x])})
pd.DataFrame(bal).round(3).to_csv(RES / "balance.csv", index=False, encoding="utf-8-sig")
base[["code", "市区町村", "group", "ps"]].to_csv(RES / "pscore.csv", index=False, encoding="utf-8-sig")
print("作成", int(T.sum()), "未作成", int((~T).sum()), "マッチできた作成", pairs.t.nunique(), "使った対照", pairs.c.nunique())

rows = []
for per, y in [("2005→10（計画前）", "d_dens_2010"), ("2010→15（計画前）", "d_dens_2015"), ("2015→20（計画後）", "d_dens_2020")]:
    raw = base.loc[T, y].mean() - base.loc[~T, y].mean()
    att = est_psm(base, T, y)
    lo, hi = boot(lambda d: est_psm(d, d.group == "作成", y), base)
    rows.append({"期間": per, "作成の平均": base.loc[T, y].mean(), "未作成の平均": base.loc[~T, y].mean(), "単純な差": raw,
                 "マッチング後の差": att, "95%下": lo, "95%上": hi})
ev = pd.DataFrame(rows); ev.round(3).to_csv(RES / "event_psm.csv", index=False, encoding="utf-8-sig"); print(ev.round(2))

# 差の差：計画後の変化 − 計画前（2010→15）の変化
base["dd"] = base.d_dens_2020 - base.d_dens_2015
dd = est_psm(base, T, "dd"); lo, hi = boot(lambda d: est_psm(d, d.group == "作成", "dd"), base)
# 内訳：DID 人口と DID 面積
comp = []
for nm, y in [("人口密度", "d_dens_2020"), ("DID人口", "d_pop_2020"), ("DID面積", "d_area_2020")]:
    a = est_psm(base, T, y); l, h = boot(lambda d: est_psm(d, d.group == "作成", y), base, 300)
    comp.append({"指標（2015→20の変化）": nm, "作成の平均": base.loc[T, y].mean(), "未作成の平均": base.loc[~T, y].mean(), "マッチング後の差": a, "95%下": l, "95%上": h})
pd.DataFrame(comp).round(3).to_csv(RES / "components.csv", index=False, encoding="utf-8-sig")
print(pd.DataFrame(comp).round(2))

# ---- 2. 作成時期ごと（Callaway–Sant'Anna 型：時期ごとに作成市町村と未作成を比べ、市町村数で重みづけて平均）
coh = []
for g, sub in base[T].groupby("cohort"):
    dg = pd.concat([sub, base[~T]]).reset_index(drop=True); tg = dg.group == "作成"
    for per, y in [("2010→15（計画前）", "d_dens_2015"), ("2015→20（計画後）", "d_dens_2020")]:
        a = est_dr(dg, tg, y); l, h = boot(lambda d: est_dr(d, d.group == "作成", y), dg, 300)
        coh.append({"公表の時点": g, "市町村数": len(sub), "期間": per, "効果": a, "95%下": l, "95%上": h,
                    "国勢調査（2020年10月）までの年数": round((pd.Timestamp("2020-10-01") - pd.Timestamp(g)).days / 365.25, 1)})
coh = pd.DataFrame(coh); coh.round(3).to_csv(RES / "cohort_att.csv", index=False, encoding="utf-8-sig"); print(coh.round(2))
post = coh[coh.期間.str.contains("計画後")]
agg = np.average(post.効果, weights=post.市町村数)
lo_a, hi_a = boot(lambda d: np.average([est_dr(pd.concat([s, d[d.group != "作成"]]).reset_index(drop=True),
                                         (pd.concat([s, d[d.group != "作成"]]).group == "作成").reset_index(drop=True), "d_dens_2020")
                                        for _, s in d[d.group == "作成"].groupby("cohort")],
                                       weights=[len(s) for _, s in d[d.group == "作成"].groupby("cohort")]), base, 200)

# ---- 3. 人口規模別
size = []
base["規模"] = pd.cut(base["総人口"], [0, 1e5, 3e5, 1e8], labels=["10万人未満", "10万〜30万人", "30万人以上"])
for s, sub in base.groupby("規模", observed=True):
    sub = sub.reset_index(drop=True); ts = sub.group == "作成"
    if ts.sum() < 5 or (~ts).sum() < 5: continue
    a = est_dr(sub, ts, "d_dens_2020"); l, h = boot(lambda d: est_dr(d, d.group == "作成", "d_dens_2020"), sub, 300)
    size.append({"規模": s, "作成": int(ts.sum()), "未作成": int((~ts).sum()), "効果": a, "95%下": l, "95%上": h})
size = pd.DataFrame(size); size.round(3).to_csv(RES / "size_att.csv", index=False, encoding="utf-8-sig"); print(size.round(2))

# ---- 4. 頑健性チェック
rob = []
def add(name, d, tr, f, y="d_dens_2020", B=300):
    a = f(d, tr, y)
    gname = d.loc[tr].group.iloc[0]
    l, h = boot(lambda db: f(db, db.group == gname, y), d, B)
    rob.append({"設定": name, "作成": int(tr.sum()), "対照": int((~tr).sum()), "効果": a, "95%下": l, "95%上": h})
add("本推定：最近傍1対1（キャリパー0.2）", base, T, est_psm)
add("キャリパー0.05", base, T, lambda d, t, y: est_psm(d, t, y, 1, 0.05))
add("最近傍1対3", base, T, lambda d, t, y: est_psm(d, t, y, 3, 0.2))
add("IPW（傾向スコアの重み）", base, T, est_ipw)
add("二重頑健（IPW＋回帰調整）", base, T, est_dr)
ny = df[df.group.isin(["作成", "作成中"])].reset_index(drop=True)
add("対照＝2020年7月に作成中の市町村（まだ作っていない）", ny, ny.group == "作成", est_dr)
ex = base[~base.code5.isin([c for c in base.code5 if c[2:] in ("100", "130", "140", "150")])].reset_index(drop=True)
add("政令市を除く", ex, ex.group == "作成", est_dr)
early = base[(base.group == "未作成") | (base.cohort <= "2018-12-31")].reset_index(drop=True)
add("2018年までに公表した市町村だけ", early, early.group == "作成", est_dr)
add("差の差（計画後−計画前の変化）", base, T, est_dr, y="dd")
add("計画前（2010→15）にあてはめた偽の効果", base, T, est_dr, y="d_dens_2015")
rob = pd.DataFrame(rob); rob.round(3).to_csv(RES / "robustness.csv", index=False, encoding="utf-8-sig"); print(rob.round(2))

summ = {"作成": int(T.sum()), "未作成": int((~T).sum()), "マッチできた作成": int(pairs.t.nunique()),
        "差の差": dd, "差の差95%": (lo, hi), "時期別の加重平均": agg, "時期別の加重平均95%": (lo_a, hi_a)}
pd.Series({k: str(v) for k, v in summ.items()}).to_csv(RES / "summary.csv", header=False, encoding="utf-8-sig")
print(summ)
