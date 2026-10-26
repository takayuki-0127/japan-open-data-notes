"""増税の前後の「駆け込み」と「反動」をイベントスタディで測る。

方法：系列ごとに、増税の48〜13か月前（推定期間）で
  log(実質支出) = 定数 + 傾き×月 + 月のダミー（季節） [+ 2018年1月以降の段差]
を推定し、増税の12か月前〜12か月後に延ばした値を「増税がなかった場合」とする。
実際の値との差を、増税の月を 0 とした月ごとに並べる。
不確かさ：増税と関係のない年に同じ計算をした「偽の増税月」（プラセボ）の分布で幅を付ける。
"""
import json
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from common import DATA, RES, EVENTS

df = pd.read_csv(DATA / "kakei_monthly_long.csv")
df["date"] = pd.PeriodIndex(df["date"], freq="M")
W = df.pivot_table(index="date", columns="item", values="real_amount")
N = df.pivot_table(index="date", columns="item", values="amount")

def grp(T):
    g = pd.DataFrame(index=T.index)
    g["消費支出"] = T["消費支出"]
    g["耐久財"] = T["家庭用耐久財"] + T["教養娯楽用耐久財"] + T["自動車等購入"] + T["自転車購入"]
    g["被服及び履物"] = T["被服及び履物"]
    g["日用品"] = T["家事用消耗品"] + T["理美容用品"] + T["医薬品"] + T["保健医療用品・器具"]
    g["食料（酒類・外食を除く）"] = T["食料"] - T["酒類"] - T["外食"]
    g["外食"] = T["外食"]
    g["酒類"] = T["酒類"]
    return g

G = grp(W)
GN = grp(N)
GROUPS = list(G.columns)
G.to_csv(RES / "group_real_monthly.csv")

def fit_cf(y, ev, est=(48, 13), step2018=True, horizon=12, norm=True):
    """y: 実質支出の月次系列。ev: 増税の月 (Period)。戻り値：k=-12..+12 の実際・予測"""
    ev = pd.Period(ev, freq="M")
    t0, t1 = ev - est[0], ev - est[1]
    s = y.loc[t0: ev + horizon].dropna()
    est_idx = s.index[(s.index >= t0) & (s.index <= t1)]
    def X(idx):
        t = np.array([(p - ev).n for p in idx], float)
        cols = [np.ones(len(idx)), t]
        for m in range(2, 13):
            cols.append(np.array([p.month == m for p in idx], float))
        if step2018:
            cols.append(np.array([p >= pd.Period("2018-01", "M") for p in idx], float))
        return np.column_stack(cols)
    Xe = X(est_idx)
    ye = np.log(s.loc[est_idx].values)
    if step2018 and Xe[:, -1].std() == 0:  # 推定期間に段差がなければ外す
        return fit_cf(y, ev, est, False, horizon, norm)
    beta, *_ = np.linalg.lstsq(Xe, ye, rcond=None)
    resid_sd = np.std(ye - Xe @ beta, ddof=Xe.shape[1])
    win = [ev + k for k in range(-12, horizon + 1) if ev + k in s.index]
    pred = np.exp(X(win) @ beta)
    out = pd.DataFrame({"k": [(p - ev).n for p in win], "date": [str(p) for p in win],
                        "actual": s.loc[win].values, "cf": pred})
    raw = out["actual"] / out["cf"] - 1
    ref = raw[(out.k >= -12) & (out.k <= -7)].mean() if norm else 0.0
    out["gap_pct_raw"] = raw
    out["cf"] = out["cf"] * (1 + ref)   # 基準期間（12〜7か月前）のずれをそろえる
    out["gap"] = out["actual"] - out["cf"]
    out["gap_pct"] = out["actual"] / out["cf"] - 1
    return out, resid_sd

def summarize(out, pre=(-6, -1), post=(0, 4)):
    a = out[(out.k >= pre[0]) & (out.k <= pre[1])]["gap"].sum()
    b = out[(out.k >= post[0]) & (out.k <= post[1])]["gap"].sum()
    base = out[(out.k >= pre[0]) & (out.k <= pre[1])]["cf"].mean()
    return dict(pull=a, payback=b, net=a + b, base=base,
                pull_months=a / base, payback_months=b / base,
                payback_ratio=(-b / a if a > 0 else np.nan))

# ---- 1. グループ別のイベントスタディ ----
rows, paths = [], []
for name, ev in EVENTS.items():
    for g in GROUPS:
        out, sd = fit_cf(G[g], ev)
        out["event"] = name; out["group"] = g; out["resid_sd"] = sd
        paths.append(out)
        for post in [(0, 4), (0, 11)]:
            r = summarize(out, post=post)
            r.update(event=name, group=g, post=f"{post[0]}..+{post[1]}")
            rows.append(r)
paths = pd.concat(paths)
paths.to_csv(RES / "event_paths.csv", index=False)
summ = pd.DataFrame(rows)

# ---- 2. プラセボ（増税のない年の4月・10月を偽の増税月に）----
plac_months = [f"{y}-{m:02d}" for y in list(range(2005, 2013)) + [2016, 2017] for m in (4, 10)]
plac_months = [p for p in plac_months if not (pd.Period(p, "M") + 12 >= pd.Period("2014-04", "M") - 6 and pd.Period(p, "M") - 13 <= pd.Period("2015-03", "M"))]
plac, band = [], []
for g in GROUPS:
    for p in plac_months:
        try:
            out, _ = fit_cf(G[g], p, step2018=False)
        except Exception:
            continue
        if out.k.max() < 4:
            continue
        r = summarize(out); r.update(group=g, month=p)
        r["last_month"] = out.loc[out.k == -1, "gap_pct"].iloc[0]
        plac.append(r)
        band.append(out[["k", "gap_pct"]].assign(group=g, month=p))
plac = pd.DataFrame(plac)
band = pd.concat(band).groupby(["group", "k"])["gap_pct"].quantile([.025, .975]).unstack().reset_index()
band.columns = ["group", "k", "lo", "hi"]
band.to_csv(RES / "placebo_band.csv", index=False)
plac.to_csv(RES / "placebo.csv", index=False)
ci = plac.groupby("group").agg(pull_lo=("pull", lambda x: np.quantile(x, .025)), pull_hi=("pull", lambda x: np.quantile(x, .975)),
                              pay_lo=("payback", lambda x: np.quantile(x, .025)), pay_hi=("payback", lambda x: np.quantile(x, .975)),
                              last_lo=("last_month", lambda x: np.quantile(x, .025)), last_hi=("last_month", lambda x: np.quantile(x, .975)),
                              n=("pull", "size"))
summ = summ.merge(ci, left_on="group", right_index=True, how="left")
last = paths[paths.k == -1][["event", "group", "gap_pct"]].rename(columns={"gap_pct": "last_month_actual"})
last["event"] = last["event"].astype(str)
summ = summ.merge(last, on=["event", "group"], how="left")
summ.to_csv(RES / "pull_payback_summary.csv", index=False)

# ---- 3. 軽減税率：食料（対象の近似）と日用品の差、2014年と2019年の比較（差の差の差）----
did = []
for name, ev in EVENTS.items():
    a, _ = fit_cf(G["食料（酒類・外食を除く）"], ev)
    b, _ = fit_cf(G["日用品"], ev)
    m = a[["k", "gap_pct"]].merge(b[["k", "gap_pct"]], on="k", suffixes=("_food", "_daily"))
    m["diff"] = m["gap_pct_food"] - m["gap_pct_daily"]
    m["event"] = name
    did.append(m)
did = pd.concat(did)
did.to_csv(RES / "reduced_rate_did.csv", index=False)
def avg(d, lo, hi, col): return d[(d.k >= lo) & (d.k <= hi)][col].mean()
did_tab = {}
for name in EVENTS:
    d = did[did.event == name]
    did_tab[name] = {"pre_food": avg(d, -3, -1, "gap_pct_food"), "pre_daily": avg(d, -3, -1, "gap_pct_daily"),
                     "pre_diff": avg(d, -3, -1, "diff"), "post_diff": avg(d, 0, 4, "diff"),
                     "post_food": avg(d, 0, 4, "gap_pct_food"), "post_daily": avg(d, 0, 4, "gap_pct_daily")}
did_tab["ddd_pre"] = did_tab["2019"]["pre_diff"] - did_tab["2014"]["pre_diff"]
did_tab["ddd_post"] = did_tab["2019"]["post_diff"] - did_tab["2014"]["post_diff"]
# プラセボでの「食料−日用品」の3か月平均の差の幅
pd_ = []
for p in plac_months:
    try:
        a, _ = fit_cf(G["食料（酒類・外食を除く）"], p, step2018=False)
        b, _ = fit_cf(G["日用品"], p, step2018=False)
    except Exception:
        continue
    m = a[["k", "gap_pct"]].merge(b[["k", "gap_pct"]], on="k")
    pd_.append(avg(m.assign(diff=m.gap_pct_x - m.gap_pct_y), -3, -1, "diff"))
did_tab["placebo_pre_diff_95"] = [float(np.quantile(pd_, .025)), float(np.quantile(pd_, .975))]
json.dump(did_tab, open(RES / "reduced_rate_did.json", "w"), ensure_ascii=False, indent=1)

# ---- 4. 小分類の品目別の駆け込み（増税の3か月前〜前月、平常の1か月分の何か月分か）----
items = df[["no", "item"]].drop_duplicates()
small = [it for no, it in items.values if 13 <= no <= 127 and it not in ("こづかい(使途不明)", "仕送り金", "贈与金", "学校給食", "家賃地代")]
irows = []
for name, ev in EVENTS.items():
    for it in small:
        y = W[it]
        if y.loc[pd.Period(ev, "M") - 48: pd.Period(ev, "M") + 12].isna().any() or (y.loc[pd.Period(ev, "M") - 48: pd.Period(ev, "M") + 12] <= 0).any():
            continue
        out, sd = fit_cf(y, ev)
        r = summarize(out, pre=(-3, -1), post=(0, 4))
        r.update(event=name, item=it, base_yen=out[out.k < 0]["cf"].mean())
        irows.append(r)
it = pd.DataFrame(irows)
it.to_csv(RES / "items_pull.csv", index=False)

# ---- 5. 頑健性 ----
rob = []
def add(label, **kw):
    for name, ev in EVENTS.items():
        for g in ["消費支出", "耐久財", "日用品", "食料（酒類・外食を除く）"]:
            out, _ = fit_cf(G[g] if not kw.get("nominal") else GN[g], ev, est=kw.get("est", (48, 13)), step2018=kw.get("step", True), norm=kw.get("norm", True))
            r = summarize(out, pre=kw.get("pre", (-6, -1)), post=kw.get("post", (0, 4)))
            r.update(spec=label, event=name, group=g)
            rob.append(r)
add("基本（推定48〜13か月前・駆け込み6か月・反動5か月）")
add("推定期間を短く（36〜13か月前）", est=(36, 13))
add("推定期間を長く（72〜13か月前、2019年は2014年の増税期を含む）", est=(72, 13))
add("駆け込みを3か月に", pre=(-3, -1))
add("反動を3か月に", post=(0, 2))
add("2018年の段差を入れない", step=False)
add("名目のまま（実質化しない）", nominal=True)
add("基準期間でそろえない", norm=False)
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False)

# 2019年の反動を12か月（コロナを含む）にした場合
cov = summ[(summ.event == "2019") & (summ.post == "0..+11")][["group", "payback", "payback_months"]]
cov.to_csv(RES / "covid_window_2019.csv", index=False)

pd.set_option("display.width", 220)
print(summ[summ.post == "0..+4"][["event", "group", "pull", "payback", "pull_months", "payback_months", "payback_ratio", "pull_lo", "pull_hi", "pay_lo", "pay_hi"]].round(3).to_string())
print(summ[(summ.post == "0..+11")][["event", "group", "pull", "payback", "payback_ratio"]].round(2).to_string())
print(json.dumps(did_tab, ensure_ascii=False, indent=1))
for name in EVENTS:
    print(name, it[it.event == name].sort_values("pull_months", ascending=False).head(10)[["item", "pull_months", "payback_months", "base_yen"]].round(2).to_string())
print(rob.pivot_table(index=["spec"], columns=["event", "group"], values="pull_months").round(2).to_string())
print(rob.pivot_table(index=["spec"], columns=["event", "group"], values="payback_months").round(2).to_string())
