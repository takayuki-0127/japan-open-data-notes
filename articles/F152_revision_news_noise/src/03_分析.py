"""速報はあとでどれだけ直されるか、その直し方は「ニュース」型か「ノイズ」型か（Mankiw–Shapiro）、
改定を速報の時点で予測できるかを、GDP の需要項目と毎月勤労統計で調べる"""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from common import DATA, RES, SEED

rng = np.random.default_rng(SEED)
LATEST = "qe262_2"

# ---------------- GDP ----------------
info = pd.read_csv(DATA / "gdp_releases.csv")
v = pd.read_csv(DATA / "gdp_vintages_long.csv.gz")
bc = pd.read_csv(DATA / "f50_base_changes.csv")
big = set(bc.loc[bc["大きな作り直し"], "rid"]) - {"qe022"}  # 最初の比較対象の回は除く
order = {r: i for i, r in enumerate(info.rid)}
first = info[info.stage == 1].set_index("ref").rid
second = info[info.stage == 2].set_index("ref").rid


def crosses(a, b):
    """公表回 a から b のあいだ（b を含む）に大きな作り直しがあるか"""
    ia, ib = order[a], order[b]
    return any(ia < order[x] <= ib for x in big if x in order)


gdp_rows = []
for item, g in v.groupby("item"):
    t = g.pivot(index="rid", columns="q", values="value")
    for ref, rid1 in first.items():
        if ref >= "2026Q2":
            continue
        rec = {"系列": item, "q": ref, "p": t.at[rid1, ref] if ref in t.columns else np.nan}
        rec["v2"] = t.at[second[ref], ref] if ref in second.index else np.nan
        ref4 = str(pd.Period(ref, "Q") + 4)
        if ref4 in second.index:
            rec["v1y"] = t.at[second[ref4], ref]
            rec["またぐ1y"] = crosses(rid1, second[ref4])
        else:
            rec["v1y"], rec["またぐ1y"] = np.nan, np.nan
        rec["vL"] = t.at[LATEST, ref]
        rec["またぐL"] = crosses(rid1, LATEST)
        gdp_rows.append(rec)
G = pd.DataFrame(gdp_rows)
G.to_csv(RES / "gdp_first_and_later.csv", index=False)

# ---------------- 毎月勤労統計 ----------------
M = pd.read_csv(DATA / "maikin_p_r.csv")
items_m = ["給与総額", "きまって支給", "所定内給与", "所定外給与", "特別給与", "総実労働時間", "所定外労働時間", "常用雇用"]
Mp = M[M["段階"] == "速報"].set_index("月")
Mr = M[M["段階"] == "確報"].set_index("月")
months = Mp.index.intersection(Mr.index)
mk_rows = []
for it in items_m:
    for mo in months:
        mk_rows.append({"系列": it, "月": mo, "p": Mp.at[mo, it], "f": Mr.at[mo, it]})
K = pd.DataFrame(mk_rows)
K.to_csv(RES / "maikin_prelim_final.csv", index=False)
lv = (Mr.loc[months, "給与総額_円"] / Mp.loc[months, "給与総額_円"] - 1) * 100


# ---------------- 道具 ----------------
def hac(y, X, lags):
    return sm.OLS(y, sm.add_constant(X)).fit(cov_type="HAC", cov_kwds={"maxlags": lags})


def ms_test(p, f, lags):
    """Mankiw–Shapiro：改定 r=f−p。
    ニュース型なら r は速報 p と無相関（速報は手元の情報を使い切った予測）。
    ノイズ型なら r は確定値 f と無相関（速報＝確定値＋誤差）。"""
    d = pd.DataFrame({"p": p, "f": f}).dropna()
    r = d.f - d.p
    mp = hac(r.values, d.p.values, lags)
    mf = hac(r.values, d.f.values, lags)
    mean = hac(r.values, np.ones((len(r), 0)), lags) if False else sm.OLS(r.values, np.ones(len(r))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return {
        "n": len(d), "改定の平均": r.mean(), "平均のp": mean.pvalues[0], "改定の平均絶対": r.abs().mean(),
        "改定の標準偏差": r.std(), "確定値の標準偏差": d.f.std(), "速報の標準偏差": d.p.std(),
        "ノイズ比": r.std() / d.f.std(),
        "r~p の傾き": mp.params[1], "r~p のp": mp.pvalues[1], "corr(r,p)": np.corrcoef(r, d.p)[0, 1],
        "r~f の傾き": mf.params[1], "r~f のp": mf.pvalues[1], "corr(r,f)": np.corrcoef(r, d.f)[0, 1],
        "符号が逆": int(((np.sign(d.p) * np.sign(d.f)) < 0).sum()),
    }


def verdict(s, a=0.05):
    news_rej, noise_rej = s["r~p のp"] < a, s["r~f のp"] < a
    if noise_rej and not news_rej:
        return "ニュース型"
    if news_rej and not noise_rej:
        return "ノイズ型"
    if news_rej and noise_rej:
        return "どちらでもない（両方退けられる）"
    return "区別できない"


def oos(p, f, start, extra=None):
    """拡大窓で r=a+b·p（＋extra）を推定し、次の期の改定を予測。予測しない（改定0）と比べた二乗誤差の比"""
    d = pd.DataFrame({"p": p, "f": f})
    if extra is not None:
        d["x"] = extra
    d = d.dropna().reset_index(drop=True)
    r = d.f - d.p
    cols = ["p"] + (["x"] if extra is not None else [])
    e_model, e_zero, e_mean = [], [], []
    for i in range(start, len(d)):
        X = sm.add_constant(d.loc[:i - 1, cols].values, has_constant="add")
        b = np.linalg.lstsq(X, r[:i].values, rcond=None)[0]
        xi = np.r_[1.0, d.loc[i, cols].values]
        e_model.append(r[i] - xi @ b)
        e_zero.append(r[i])
        e_mean.append(r[i] - r[:i].mean())
    e_model, e_zero, e_mean = map(np.array, (e_model, e_zero, e_mean))
    # Diebold–Mariano（二乗誤差の差、HAC）
    dl = e_zero ** 2 - e_model ** 2
    dm = sm.OLS(dl, np.ones(len(dl))).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
    return {"予測した期": len(e_model), "RMSE_モデル": np.sqrt((e_model ** 2).mean()),
            "RMSE_改定0": np.sqrt((e_zero ** 2).mean()), "RMSE_過去平均": np.sqrt((e_mean ** 2).mean()),
            "RMSE比（モデル/改定0）": np.sqrt((e_model ** 2).mean() / (e_zero ** 2).mean()), "DMのp（片側）": dm.pvalues[0] / 2 if dm.params[0] > 0 else 1 - dm.pvalues[0] / 2}


def block_boot_slope(p, f, B=2000, L=4):
    """ブロック・ブートストラップで r~p の傾きの95%区間"""
    d = pd.DataFrame({"p": p, "f": f}).dropna().reset_index(drop=True)
    n = len(d)
    out = []
    for _ in range(B):
        idx = np.concatenate([np.arange(s, s + L) % n for s in rng.integers(0, n, n // L + 1)])[:n]
        dd = d.iloc[idx]
        r = dd.f - dd.p
        out.append(np.polyfit(dd.p, r, 1)[0])
    return np.percentile(out, [2.5, 97.5])


# ---------------- 主な結果 ----------------
summ = []
# GDP：1次→1年後（作り直しをまたがない）を基本に、2次・最新も
stages = {"1次→2次": ("v2", None), "1次→1年後": ("v1y", "またぐ1y"), "1次→最新": ("vL", None)}
for item, g in G.groupby("系列"):
    for st, (col, cross) in stages.items():
        gg = g if cross is None else g[g[cross] == False]
        s = ms_test(gg.p.values, gg[col].values, 4)
        s.update({"統計": "GDP", "系列": item, "段階": st, "条件": "基本" if cross else "すべて"})
        summ.append(s)
for it, g in K.groupby("系列"):
    s = ms_test(g.p.values, g.f.values, 12)
    s.update({"統計": "毎月勤労統計", "系列": it, "段階": "速報→確報", "条件": "基本"})
    summ.append(s)
S = pd.DataFrame(summ)
S["判定"] = S.apply(verdict, axis=1)
S.to_csv(RES / "news_noise_tests.csv", index=False)

# 予測できるか（拡大窓）
pred = []
for item, g in G.groupby("系列"):
    g = g.sort_values("q")
    gg = g[g["またぐ1y"] == False]
    pred.append({"統計": "GDP", "系列": item, "段階": "1次→1年後", **oos(gg.p.values, gg.v1y.values, 30)})
    # 2次で分かった改定を足すと、そのあとの改定を予測できるか
    gg2 = gg.dropna(subset=["v2"])
    pred.append({"統計": "GDP", "系列": item, "段階": "2次→1年後（2次の改定を使う）",
                 **oos(gg2.v2.values, gg2.v1y.values, 30, extra=(gg2.v2 - gg2.p).values)})
for it, g in K.groupby("系列"):
    g = g.sort_values("月")
    pred.append({"統計": "毎月勤労統計", "系列": it, "段階": "速報→確報", **oos(g.p.values, g.f.values, 48)})
P = pd.DataFrame(pred)
P.to_csv(RES / "predictability_oos.csv", index=False)

# 毎勤：賞与の月とそれ以外
K["月番号"] = K["月"].str[5:].astype(int)
K["賞与月"] = K["月番号"].isin([6, 7, 12])
K["r"] = K.f - K.p
bonus = K.groupby(["系列", "賞与月"]).r.agg(["count", "mean", lambda x: x.abs().mean(), "std"]).reset_index()
bonus.columns = ["系列", "賞与月", "n", "平均", "平均絶対", "標準偏差"]
bonus.to_csv(RES / "maikin_bonus_months.csv", index=False)
bym = K[K.系列.isin(["給与総額", "特別給与"])].groupby(["系列", "月番号"]).r.apply(lambda x: x.abs().mean()).unstack(0)
bym.to_csv(RES / "maikin_abs_revision_by_month.csv")
lvdf = pd.DataFrame({"月": lv.index, "給与総額_円の改定率%": lv.values})
lvdf.to_csv(RES / "maikin_level_revision.csv", index=False)

# ---------------- 頑健性 ----------------
rob = []
def add(name, stat, item, p, f, lags):
    s = ms_test(p, f, lags)
    s.update({"設定": name, "統計": stat, "系列": item})
    s["判定"] = verdict(s)
    rob.append(s)

for item, g in G.groupby("系列"):
    gg = g[g["またぐ1y"] == False]
    add("基本（1次→1年後、作り直しをまたがない）", "GDP", item, gg.p, gg.v1y, 4)
    add("1次→最新（すべて）", "GDP", item, g.p, g.vL, 4)
    add("1次→最新（作り直しをまたがない＝2021年以降）", "GDP", item, g[g["またぐL"] == False].p, g[g["またぐL"] == False].vL, 4)
    add("2010年までの四半期", "GDP", item, gg[gg.q <= "2010Q4"].p, gg[gg.q <= "2010Q4"].v1y, 4)
    add("2011年以降の四半期", "GDP", item, gg[gg.q >= "2011Q1"].p, gg[gg.q >= "2011Q1"].v1y, 4)
    add("2020年を除く", "GDP", item, gg[~gg.q.str.startswith("2020")].p, gg[~gg.q.str.startswith("2020")].v1y, 4)
    add("2次→1年後", "GDP", item, gg.v2, gg.v1y, 4)
for it, g in K.groupby("系列"):
    add("基本（速報→確報）", "毎月勤労統計", it, g.p, g.f, 12)
    add("2013〜2019年", "毎月勤労統計", it, g[g.月 < "2020"].p, g[g.月 < "2020"].f, 12)
    add("2020年以降", "毎月勤労統計", it, g[g.月 >= "2020"].p, g[g.月 >= "2020"].f, 12)
    add("賞与の月（6・7・12月）を除く", "毎月勤労統計", it, g[~g.賞与月].p, g[~g.賞与月].f, 12)
    q = g.r.abs().quantile(0.95)
    add("改定の大きい上位5%を除く", "毎月勤労統計", it, g[g.r.abs() <= q].p, g[g.r.abs() <= q].f, 12)
R = pd.DataFrame(rob)
R.to_csv(RES / "robustness.csv", index=False)

# ブートストラップの区間（基本）
boot = []
for item, g in G.groupby("系列"):
    gg = g[g["またぐ1y"] == False]
    lo, hi = block_boot_slope(gg.p.values, gg.v1y.values, L=4)
    boot.append({"統計": "GDP", "系列": item, "r~p 傾き 2.5%": lo, "97.5%": hi})
for it, g in K.groupby("系列"):
    lo, hi = block_boot_slope(g.p.values, g.f.values, L=12)
    boot.append({"統計": "毎月勤労統計", "系列": it, "r~p 傾き 2.5%": lo, "97.5%": hi})
pd.DataFrame(boot).to_csv(RES / "bootstrap_slope.csv", index=False)

pd.set_option("display.width", 250)
cols = ["統計", "系列", "段階", "n", "改定の平均", "平均のp", "改定の平均絶対", "ノイズ比", "r~p の傾き", "r~p のp", "r~f の傾き", "r~f のp", "符号が逆", "判定"]
print(S[cols].round(3).to_string())
print(P.round(3).to_string())
print(bonus.round(3).to_string())
print(R[["設定", "統計", "系列", "n", "r~p の傾き", "r~p のp", "r~f のp", "判定"]].round(3).to_string())
print(pd.DataFrame(boot).round(3).to_string())
print("給与総額（円）の改定率", lv.describe().round(3).to_dict())
