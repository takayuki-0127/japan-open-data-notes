"""F2：家計は「値上がりした後に買う」のか「値上がりしたら売る」のか。
投資信託と上場株式について、四半期の純購入（フロー÷前期末残高）を、直前の値動き（調整÷前期末残高）に回帰する"""
from common import *
import statsmodels.api as sm

st, fl, adj = load()
res, rows = {}, []
for it in ["A318", "A331"]:
    d = pd.DataFrame({"flow": fl[it] / st[it].shift(1) * 100, "ret": adj[it] / st[it].shift(1) * 100})
    d["ret_l1"] = d.ret.shift(1); d["ret_l2"] = d.ret.shift(2); d["ret_4q"] = d.ret.shift(1).rolling(4).sum()
    d["nisa14"] = ((d.index >= pd.Period("2014Q1", "Q")) & (d.index < pd.Period("2024Q1", "Q"))).astype(float)
    d["nisa24"] = (d.index >= pd.Period("2024Q1", "Q")).astype(float)
    for k in [2, 3, 4]: d[f"q{k}"] = (d.index.quarter == k).astype(float)
    d = d.dropna()
    for spec, xs in [("同じ期", ["ret"]), ("1〜2期前", ["ret_l1", "ret_l2"]), ("過去1年", ["ret_4q"])]:
        X = sm.add_constant(d[xs + ["nisa14", "nisa24", "q2", "q3", "q4"]])
        m = sm.OLS(d.flow, X).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
        for x in xs + ["nisa14", "nisa24"]:
            rows.append(dict(item=ITEMS[it], spec=spec, var=x, coef=m.params[x], lo=m.conf_int().loc[x, 0], hi=m.conf_int().loc[x, 1], p=m.pvalues[x], r2=m.rsquared, n=int(m.nobs)))
    res[it] = d
    d.round(3).to_csv(RES / f"f2_{'fund' if it == 'A318' else 'listed'}.csv", encoding="utf-8-sig")
t = pd.DataFrame(rows); t.round(4).to_csv(RES / "f2_regressions.csv", index=False, encoding="utf-8-sig"); print(t.round(3).to_string())

# 期間ごとの平均の純購入率
per = []
for it, d in res.items():
    for lab, a, b in [("1998〜2013", "1998", "2013"), ("2014〜2023", "2014", "2023"), ("2024〜", "2024", "2026")]:
        x = d.loc[a:b]; per.append(dict(item=ITEMS[it], period=lab, mean_flow_pct=x.flow.mean(), mean_ret_pct=x.ret.mean()))
per = pd.DataFrame(per); per.round(3).to_csv(RES / "f2_periods.csv", index=False, encoding="utf-8-sig"); print(per.round(2))

note = "\n（純購入率＝四半期のフロー÷前期末残高、値動き＝調整÷前期末残高。どちらも%）"
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
for ax, (it, c) in zip(axes, [("A318", GREEN), ("A331", BLUE)]):
    d = res[it]; nisa = d.index >= pd.Period("2024Q1", "Q")
    ax.scatter(d.ret_4q[~nisa], d.flow[~nisa], s=14, color=c, alpha=0.6, label="1999〜2023年")
    ax.scatter(d.ret_4q[nisa], d.flow[nisa], s=30, color=ORANGE, marker="D", label="2024年〜（新NISA）")
    r = t[(t["item"] == ITEMS[it]) & (t.spec == "過去1年") & (t["var"] == "ret_4q")].iloc[0]
    ax.axhline(0, color=GRAY, lw=0.6); ax.axvline(0, color=GRAY, lw=0.6)
    ax.set_title(f"{ITEMS[it]}：過去1年の値動き1%あたり {r.coef:+.3f}%（95%区間 {r.lo:+.3f}〜{r.hi:+.3f}）", fontsize=10)
    ax.set_xlabel("過去1年（4四半期）の値動きの合計（%）"); ax.set_ylabel("その期の純購入率（%）"); ax.legend(frameon=False, fontsize=8.5)
fig.suptitle("投資信託は値上がりの後に買われる。上場株式は過去1年の値動きとはほぼ無関係", y=1.03)
fig.text(0.01, -0.07, SOURCE + note + "\n回帰は季節（四半期）と2014年・2024年のNISA期間のダミーを含む。HAC標準誤差", fontsize=7, color="#8a8984")
fig.savefig(FIG / "f2_chasing.png"); plt.close(fig)

fig, ax = plt.subplots(figsize=(10, 4.2))
for it, c in [("A318", GREEN), ("A331", BLUE)]:
    d = res[it]; ax.plot(d.index.to_timestamp(), d.flow.rolling(4).mean(), color=c, lw=2, label=f"{ITEMS[it]}（4四半期移動平均）")
ax.axhline(0, color=GRAY, lw=0.8)
for y, lab in [("2014-01-01", "NISA開始"), ("2024-01-01", "新NISA")]:
    ax.axvline(pd.Timestamp(y), color=GRAY, ls="--", lw=0.8); ax.text(pd.Timestamp(y), ax.get_ylim()[1] * 0.9, " " + lab, fontsize=8.5)
ax.set_ylabel("純購入率（%／四半期）"); ax.legend(frameon=False, fontsize=9, loc="lower left")
ax.set_title("投資信託は2021年ごろから買い越しが続き、上場株式は売り越しが基本")
fig.text(0.01, -0.06, SOURCE + note, fontsize=7, color="#8a8984"); fig.savefig(FIG / "f2_flows.png"); plt.close(fig)
