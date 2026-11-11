"""277 製造工業生産予測調査の見込みは、どれくらい当たるのか"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, setup_font

setup_font()
f = pd.read_csv(DATA / "production_forecast_survey.csv")
f = f.sort_values(["sector", "year", "month"]).reset_index(drop=True)
f["t"] = f.year * 12 + f.month
# 実現率：その月の調査の「前月実績」÷前の月の調査の「当月見込」−1（%）。公表の値をそのまま使う
x = f[f.real.notna()].copy()
x["covid"] = x.year.eq(2020) | ((x.year == 2021) & (x.month <= 3))
IND = ["鉄鋼業", "非鉄金属工業", "金属製品工業", "生産用機械工業", "汎用・業務用機械工業", "電子部品・デバイス工業", "電気機械工業", "情報通信機械工業",
       "輸送機械工業", "化学工業", "石油製品工業", "パルプ・紙・紙加工品工業", "その他"]
def summ(df):
    return pd.Series({"n": len(df), "mean": df.real.mean(), "median": df.real.median(), "sd": df.real.std(), "mae": df.real.abs().mean(),
                      "share_within2": (df.real.abs() <= 2).mean() * 100, "share_negative": (df.real < 0).mean() * 100})
tab = x[~x.covid].groupby("sector")[["real"]].apply(summ).round(2)
tab_all = x.groupby("sector")[["real"]].apply(summ).round(2)
tab.to_csv(RES / "a277_realization_by_sector_excl_covid.csv"); tab_all.to_csv(RES / "a277_realization_by_sector_all.csv")
# 方向：前の月の調査で「当月見込」の前月比（sa_mom_this）が示した向きと、実際の前月比（次の調査の sa_mom_last）が同じだったか
dirs = []
for s, g in f.groupby("sector"):
    g = g.set_index("t")
    for t in g.index:
        if t + 1 in g.index:
            fc, ac = g.loc[t, "sa_mom_this"], g.loc[t + 1, "sa_mom_last"]
            pl = g.loc[t + 1, "sa_last"]  # 実績
            if pd.notna(fc) and pd.notna(ac):
                dirs.append({"sector": s, "t": t, "year": int(g.loc[t, "year"]), "month": int(g.loc[t, "month"]), "fc_mom": fc, "act_mom": ac})
dd = pd.DataFrame(dirs); dd["covid"] = dd.year.eq(2020) | ((dd.year == 2021) & (dd.month <= 3))
dd["same_sign"] = np.sign(dd.fc_mom) == np.sign(dd.act_mom)
# 単純な比べ相手：「前月比0（先月と同じ）」と比べて、見込みの前月比のほうが実際に近いか
dd["err_fc"] = (dd.act_mom - dd.fc_mom).abs(); dd["err_naive"] = dd.act_mom.abs()
mfg = dd[(dd.sector == "製造工業") & ~dd.covid]
dir_tab = dd[~dd.covid].groupby("sector").agg(n=("same_sign", "size"), same_sign_pct=("same_sign", lambda v: v.mean() * 100),
                                             mae_fc=("err_fc", "mean"), mae_naive=("err_naive", "mean")).round(2)
dir_tab.to_csv(RES / "a277_direction_by_sector_excl_covid.csv")
# 補正：過去の平均の外れ（実現率の平均）だけ見込みを下げると、前月比の誤差はどれだけ減るか（前の年までの平均を使う＝その時点で分かる値だけ）
m = f[f.sector == "製造工業"].set_index("t")
rows = []
for t in m.index:
    if t + 1 not in m.index: continue
    past = x[(x.sector == "製造工業") & (x.t <= t) & (x.year < m.loc[t, "year"]) & ~x.covid].real
    if len(past) < 12: continue
    adj = past.mean()
    fc_lvl = m.loc[t, "sa_this"]; act_lvl = m.loc[t + 1, "sa_last"]; prev = m.loc[t, "sa_last"]
    if pd.isna(fc_lvl) or pd.isna(act_lvl) or pd.isna(prev): continue
    rows.append({"t": t, "year": int(m.loc[t, "year"]), "err_raw": (act_lvl / fc_lvl - 1) * 100, "err_adj": (act_lvl / (fc_lvl * (1 + adj / 100)) - 1) * 100,
                 "err_naive": (act_lvl / prev - 1) * 100})
adjd = pd.DataFrame(rows); adjd["month"] = adjd.t - adjd.year * 12; adjd = adjd[~(adjd.year.eq(2020) | ((adjd.year == 2021) & (adjd.month <= 3)))]
adj_res = {"n": len(adjd), "mae_raw": round(adjd.err_raw.abs().mean(), 2), "mae_adj": round(adjd.err_adj.abs().mean(), 2), "mae_naive_same_as_last_month": round(adjd.err_naive.abs().mean(), 2),
           "mean_raw": round(adjd.err_raw.mean(), 2), "mean_adj": round(adjd.err_adj.mean(), 2)}
# 年ごとの平均（製造工業）
yr = x[x.sector == "製造工業"].groupby("year").real.agg(["mean", "count"]).round(2); yr.to_csv(RES / "a277_mfg_realization_by_year.csv")
r = tab.loc["製造工業"]
main = {"period": f"{int(x.year.min())}-{int(x[x.year==x.year.min()].month.min()):02d}..{int(x.year.max())}-{int(x[x.year==x.year.max()].month.max()):02d}",
        "mfg_excl_covid": r.to_dict(), "mfg_all": tab_all.loc["製造工業"].to_dict(),
        "n_ind_negative_mean": int((tab.loc[IND]["mean"] < 0).sum()), "n_ind": len(IND),
        "ind_most_negative": tab.loc[IND]["mean"].idxmin(), "ind_least": tab.loc[IND]["mean"].idxmax(),
        "mfg_direction_same_sign_pct": round(mfg.same_sign.mean() * 100, 1), "mfg_dir_n": len(mfg),
        "mfg_mae_fc_mom": round(mfg.err_fc.mean(), 2), "mfg_corr_fc_act_mom": round(float(mfg.fc_mom.corr(mfg.act_mom)), 2), "mfg_share_fc_positive": round(float((mfg.fc_mom > 0).mean() * 100), 1), "mfg_share_act_positive": round(float((mfg.act_mom > 0).mean() * 100), 1), "mfg_same_sign_when_fc_negative": round(float(mfg[mfg.fc_mom < 0].same_sign.mean() * 100), 1), "mfg_n_fc_negative": int((mfg.fc_mom < 0).sum()), "mfg_mae_naive_mom": round(mfg.err_naive.mean(), 2),
        "adjust": adj_res, "mfg_years": yr["mean"].to_dict(),
        "median_by_ind": tab.loc[IND]["median"].to_dict()}
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)

short = lambda s: s.replace("工業", "").replace("・紙加工品", "")
# 図1：製造工業の実現率の分布
v = x[(x.sector == "製造工業") & ~x.covid].real
fig, ax = plt.subplots(figsize=(8, 4))
ax.hist(v, bins=np.arange(-10, 5, 0.5), color="#2e86ab", edgecolor="white")
ax.axvline(0, color="#333", lw=1); ax.axvline(v.mean(), color="#d1495b", ls="--", lw=1.5)
ax.text(v.mean() - 0.2, ax.get_ylim()[1] * 0.92, f"平均 {v.mean():.1f}%", color="#d1495b", ha="right", fontsize=9)
ax.text(0.3, ax.get_ylim()[1] * 0.92, f"0以上は{(v>=0).mean()*100:.0f}%", fontsize=9)
ax.set_xlabel("実現率（実績÷前の月に答えた当月の見込み−1、%）"); ax.set_ylabel("月の数")
ax.set_title("製造工業：前の月に答えた見込みより、実績はほとんどの月で低かった", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "a277_hist.png", dpi=150); plt.close()

# 図2：業種別の平均の実現率とばらつき
ti = tab.loc[IND].sort_values("mean")
fig, ax = plt.subplots(figsize=(8.5, 5.2))
yy = np.arange(len(ti))
ax.errorbar(ti["mean"], yy, xerr=ti["sd"], fmt="o", color="#d1495b", ecolor="#bbb", capsize=3)
for i, (mval, w2) in enumerate(zip(ti["mean"], ti["share_within2"])):
    ax.text(6, i, f"平均{mval:.1f}%・±2%以内{w2:.0f}%", va="center", fontsize=8)
ax.axvline(0, color="#333", lw=0.8); ax.set_yticks(yy); ax.set_yticklabels([short(n) for n in ti.index]); ax.set_xlim(-14, 14)
ax.set_xlabel("実現率の平均（点）と標準偏差（横線）、%"); ax.set_title("機械の業種ほど、見込みが実績より高く出やすい", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "a277_by_sector.png", dpi=150); plt.close()

# 図3：前月比の見込みと実際（製造工業）
fig, ax = plt.subplots(figsize=(6.2, 5.4))
mm = mfg
ax.scatter(mm.fc_mom, mm.act_mom, s=14, color="#2e86ab", alpha=0.8)
lim = [min(mm.fc_mom.min(), mm.act_mom.min()) - 1, max(mm.fc_mom.max(), mm.act_mom.max()) + 1]
ax.plot(lim, lim, color="#999", lw=0.8, ls="--"); ax.axhline(0, color="#ccc", lw=0.8); ax.axvline(0, color="#ccc", lw=0.8)
ax.set_xlabel("前の月の調査で答えた当月の前月比（見込み、%）"); ax.set_ylabel("実際の前月比（%）")
ax.set_title(f"向きが合ったのは{main['mfg_direction_same_sign_pct']:.0f}%の月（製造工業、2020年1月〜21年3月を除く）", fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "a277_direction.png", dpi=150); plt.close()
print(tab.loc[["製造工業"] + IND].to_string()); print(dir_tab.loc[["製造工業"] + IND].to_string()); print({k: v for k, v in main.items() if k not in ("median_by_ind",)})
