"""速報（1次・2次）と、1年後・最新の値を比べて、改定の大きさ・偏り・符号の入れ替わりを調べる"""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from common import DATA, RES, recession_quarters

info = pd.read_csv(DATA / "releases.csv")
LATEST = "qe262_2"


def load(k):
    return pd.read_csv(DATA / f"vintages_{k}.csv", index_col=0)


def build(k):
    """対象四半期ごとに、1次・2次・1年後（4四半期あとの2次速報）・最新の値を並べる"""
    v = load(k)
    first = info[info.stage == 1].set_index("ref").rid
    second = info[info.stage == 2].set_index("ref").rid
    rows = []
    for ref, rid1 in first.items():
        p = pd.Period(ref, "Q")
        r = {"q": ref, "v1": v.loc[rid1, ref]}
        r["v2"] = v.loc[second[ref], ref] if ref in second.index else np.nan
        ref4 = str(p + 4)
        r["v1y"] = v.loc[second[ref4], ref] if ref4 in second.index else np.nan
        r["rid1"], r["rid1y"] = rid1, second.get(ref4, None)
        r["vL"] = v.loc[LATEST, ref] if ref != str(pd.Period("2026Q2", "Q")) or True else np.nan
        rows.append(r)
    df = pd.DataFrame(rows)
    df = df[df.q != "2026Q2"].copy()  # 最新値＝2次速報なので比べない
    df["r2"] = df.v2 - df.v1
    df["r1y"] = df.v1y - df.v1
    df["rL"] = df.vL - df.v1
    return df


def hac_mean(x, lags=4):
    """平均が0かの検定（隣り合う四半期の改定が似ていることを考えて Newey–West の標準誤差）"""
    x = pd.Series(x).dropna()
    m = sm.OLS(x.values, np.ones(len(x))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return m.params[0], m.bse[0], m.pvalues[0], len(x)


def summarize(df, cols=("r2", "r1y", "rL")):
    out = []
    for c in cols:
        x = df[c].dropna()
        mu, se, p, n = hac_mean(x)
        out.append({"改定": c, "n": n, "平均": mu, "標準誤差": se, "p": p,
                    "平均絶対": x.abs().mean(), "標準偏差": x.std(),
                    "上方の割合": (x > 0).mean(), "下方の割合": (x < 0).mean(),
                    "0.5pt以上": (x.abs() >= 0.5).mean()})
    return pd.DataFrame(out)


def base_changes(k="jk"):
    """前の公表回と比べて、5年以上前の四半期までまとめて書き換わった回（基準改定など）を探す"""
    v = load(k)
    rows = []
    rids = list(v.index)
    for a, b in zip(rids[:-1], rids[1:]):
        ref = pd.Period(info.set_index("rid").loc[b, "ref"], "Q")
        old = [c for c in v.columns if pd.Period(c, "Q") <= ref - 20 and pd.Period(c, "Q") >= pd.Period("1995Q1", "Q")]
        d = (v.loc[b, old] - v.loc[a, old]).abs()
        rows.append({"rid": b, "前の回": a, "5年以上前の平均の変化": d.mean(), "比べた四半期": d.notna().sum()})
    bc = pd.DataFrame(rows)
    # 内閣府が公表している基準改定（2005・2011・2016・2020年の12月、各年7-9月期の2次速報）と、
    # データで見て5年以上前まで平均0.15ポイント超えて書き換わった回（推計方法の見直しなど）
    official = {"qe053_2": "2000年基準へ", "qe113_2": "2005年基準へ", "qe163_2": "2011年基準・2008SNAへ", "qe203_2": "2015年基準へ"}
    bc["基準改定（公表）"] = bc.rid.map(official).fillna("")
    bc["大きな作り直し"] = (bc["5年以上前の平均の変化"] > 0.15) | (bc["基準改定（公表）"] != "")
    return bc


res = {}
dfj = build("jk")
dfm = build("mk")
dfg = build("jg")
dfj.to_csv(RES / "revisions_real_qoq.csv", index=False)
dfm.to_csv(RES / "revisions_nominal_qoq.csv", index=False)
dfg.to_csv(RES / "revisions_real_yoy.csv", index=False)

s = summarize(dfj)
s.to_csv(RES / "summary_real_qoq.csv", index=False)
print(s.round(3).to_string())

# 基準改定
bc = base_changes()
bc.to_csv(RES / "base_changes.csv", index=False)
big = bc[bc["大きな作り直し"]]
print("大きな作り直しの回:", big[["rid", "5年以上前の平均の変化", "基準改定（公表）"]].round(3).to_string())

# 符号の入れ替わり（1次と最新）
d = dfj.dropna(subset=["v1", "vL"])
neg1 = d[d.v1 < 0]
pos1 = d[d.v1 > 0]
sign = {
    "対象四半期": len(d),
    "1次がマイナス": len(neg1),
    "1次マイナス→最新プラス": int((neg1.vL > 0).sum()),
    "1次マイナス→最新0.0": int((neg1.vL == 0).sum()),
    "1次プラス": len(pos1),
    "1次プラス→最新マイナス": int((pos1.vL < 0).sum()),
    "1次0.0": int((d.v1 == 0).sum()),
    "符号が逆になった（0を除く）": int(((d.v1 * d.vL) < 0).sum()),
    "2次で符号が逆": int(((dfj.v1 * dfj.v2) < 0).sum()),
    "1年後で符号が逆": int(((dfj.v1 * dfj.v1y) < 0).sum()),
}
flips = d[(d.v1 * d.vL) < 0][["q", "v1", "v2", "v1y", "vL"]]
flips.to_csv(RES / "sign_flips.csv", index=False)
print(sign)
print(flips.to_string())
res["sign"] = sign

# Mincer–Zarnowitz：最新 = a + b × 1次
X = sm.add_constant(d.v1.values)
mz = sm.OLS(d.vL.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
w = mz.wald_test("const = 0, x1 = 1", use_f=True, scalar=True)
res["mz"] = {"a": mz.params[0], "b": mz.params[1], "se_a": mz.bse[0], "se_b": mz.bse[1], "joint_p": float(w.pvalue), "r2": mz.rsquared}
# ニュースかノイズか
res["news_noise"] = {"corr(改定, 1次)": d.rL.corr(d.v1), "corr(改定, 最新)": d.rL.corr(d.vL),
                     "var(1次)": d.v1.var(), "var(最新)": d.vL.var()}
print(res["mz"], res["news_noise"])

# 景気局面
rq = recession_quarters()
dfj["後退期"] = [int(rq.get(pd.Period(q, "Q"), 0)) for q in dfj.q]
ph = []
for f, g in dfj.groupby("後退期"):
    for c in ["r2", "r1y", "rL"]:
        mu, se, p, n = hac_mean(g[c])
        ph.append({"後退期": f, "改定": c, "n": n, "平均": mu, "p": p, "平均絶対": g[c].abs().mean()})
ph = pd.DataFrame(ph)
ph.to_csv(RES / "by_phase.csv", index=False)
print(ph.round(3).to_string())
# 差の検定（最新への改定、後退期ダミーの回帰）
mm = sm.OLS(dfj.rL.values, sm.add_constant(dfj["後退期"].values), missing="drop").fit(cov_type="HAC", cov_kwds={"maxlags": 4})
res["phase_diff"] = {"差": mm.params[1], "p": mm.pvalues[1]}
# 1次の大きさとの関係（大きく動いた四半期ほど改定も大きいか）
dfj["abs_v1"] = dfj.v1.abs()
res["abs_corr"] = {"corr(|1次|, |最新への改定|)": dfj.abs_v1.corr(dfj.rL.abs())}

# 改定を予測できるか（1次の値・2次での改定・後退期）：1つ抜きの予測と、平均だけの予測を比べる
dd = dfj.dropna(subset=["rL", "v1", "r2"]).reset_index(drop=True)
Xf = sm.add_constant(dd[["v1", "r2", "後退期"]].values)
full = sm.OLS(dd.rL.values, Xf).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
loo, loo0 = [], []
for i in range(len(dd)):
    m = np.ones(len(dd), bool); m[i] = False
    b = np.linalg.lstsq(Xf[m], dd.rL.values[m], rcond=None)[0]
    loo.append(dd.rL.values[i] - Xf[i] @ b)
    loo0.append(dd.rL.values[i] - dd.rL.values[m].mean())
res["predict"] = {"係数": dict(zip(["const", "v1", "r2", "後退期"], full.params)), "p": dict(zip(["const", "v1", "r2", "後退期"], full.pvalues)),
                  "R2": full.rsquared, "LOO_RMSE": float(np.sqrt(np.mean(np.square(loo)))), "平均だけのLOO_RMSE": float(np.sqrt(np.mean(np.square(loo0)))), "n": len(dd)}
print(res["predict"])

# 頑健性
rob = []
def add(name, df, col="rL"):
    mu, se, p, n = hac_mean(df[col])
    rob.append({"設定": name, "改定": col, "n": n, "平均": mu, "p": p, "平均絶対": df[col].abs().mean(),
                "符号が逆": int(((df.v1 * (df.v1 + df[col])) < 0).sum())})
for c in ["r2", "r1y", "rL"]:
    add("基本（実質・前期比）", dfj, c)
    add("名目・前期比", dfm, c)
    add("実質・前年同期比（原系列）", dfg, c)
# 基準改定をまたがない：1年後の値が、1次と同じ基準の回で出ているものだけ
bigset = set(big.rid)
order = list(load("jk").index)
def crosses(rid_a, rid_b):
    if rid_b is None or pd.isna(rid_b):
        return True
    ia, ib = order.index(rid_a), order.index(rid_b)
    return any(x in bigset for x in order[ia + 1: ib + 1])
nb = dfj[[not crosses(a, b) for a, b in zip(dfj.rid1, dfj.rid1y)]]
add("基準改定をまたがない（1年後）", nb, "r1y")
last_big = max(order.index(x) for x in bigset) if bigset else 0
after = dfj[[order.index(a) > last_big for a in dfj.rid1]]
add("最後の基準改定より後の四半期（最新）", after, "rL")
add("2020年を除く", dfj[~dfj.q.str.startswith("2020")], "rL")
add("2011年以降の四半期", dfj[dfj.q >= "2011Q1"], "rL")
add("2010年までの四半期", dfj[dfj.q < "2011Q1"], "rL")
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False)
print(rob.round(3).to_string())

res["summary"] = s.to_dict("records")
res["n_releases"] = len(info)
res["targets"] = [dfj.q.min(), dfj.q.max(), len(dfj)]
res["base_change_releases"] = big[["rid", "5年以上前の平均の変化", "基準改定（公表）"]].to_dict("records")
res["after_last_base"] = [after.q.min(), after.q.max(), len(after)]
json.dump(res, open(RES / "key_numbers.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
