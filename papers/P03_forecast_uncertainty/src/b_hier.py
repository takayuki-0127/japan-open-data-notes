"""P03 後半：階層予測の整合（Wickramasuriya, Athanasopoulos & Hyndman 2019, MinT）を、
都道府県×月の延べ宿泊者数（全国1・地方10・都道府県47＝58系列）で試し、整合した予測にコンフォーマル区間を付ける。
入力：data/lodging_pref_monthly_2011_2025.csv（F36 と同じ表）
出力：results/b_*.csv・b_main.json、figures/p03_04・05
"""
import json
import numpy as np, pandas as pd
from joblib import Parallel, delayed
from common import DATA, RES, BLUE, ORANGE, GRAY, GREEN, PURPLE, RED, conformal_q, save, plt

SRC = "出典：観光庁「宿泊旅行統計調査」をもとに作成"
REGIONS = {
    "北海道": ["北海道"], "東北": ["青森", "岩手", "宮城", "秋田", "山形", "福島"],
    "関東": ["茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川", "山梨"],
    "北陸信越": ["新潟", "富山", "石川", "長野"], "中部": ["福井", "岐阜", "静岡", "愛知", "三重"],
    "近畿": ["滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山"], "中国": ["鳥取", "島根", "岡山", "広島", "山口"],
    "四国": ["徳島", "香川", "愛媛", "高知"], "九州": ["福岡", "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島"],
    "沖縄": ["沖縄"],
}
PREFS = [p for r in REGIONS.values() for p in r]
H = 12


def short(p):
    p = p[2:] if p[:2].isdigit() else p
    return p if p == "北海道" else p[:-1]


d = pd.read_csv(DATA / "lodging_pref_monthly_2011_2025.csv")
d = d[d.pref != "全国"].copy()
d["p"] = d.pref.map(short)
d["date"] = pd.to_datetime(dict(year=d.year, month=d.month, day=1))
bottom = d.pivot(index="date", columns="p", values="total")[PREFS].astype(float)
rows, names, level = [np.ones(len(PREFS))], ["全国"], ["全国"]
for r, ps in REGIONS.items():
    rows.append(np.array([1.0 if p in ps else 0.0 for p in PREFS])); names.append(r + "地方" if r in ("北海道", "沖縄") else r); level.append("地方")
for p in PREFS:
    rows.append(np.array([1.0 if q == p else 0.0 for q in PREFS])); names.append(p); level.append("都道府県")
S = np.vstack(rows); level = np.array(level)
Y = pd.DataFrame(bottom.values @ S.T, index=bottom.index, columns=names)


def fit_one(y):
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    ly = np.log(y.clip(lower=1.0))
    m = ExponentialSmoothing(ly.values, trend="add", damped_trend=True, seasonal="add", seasonal_periods=12,
                             initialization_method="estimated").fit(optimized=True)
    return np.exp(m.forecast(H)), np.exp(m.fittedvalues)


def base_at(origin):
    """origin（その月まで学習）で58系列を予測。返り値：予測 H×58、当てはめの残差 T×58（水準）"""
    tr = Y.loc[:origin]
    out = [fit_one(tr.iloc[:, k]) for k in range(tr.shape[1])]
    F = np.column_stack([o[0] for o in out])
    E = tr.values - np.column_stack([o[1] for o in out])
    return F, E


def shrink_cov(E):
    """Schäfer–Strimmer 型の縮小推定（相関を0へ縮める）"""
    E = E - E.mean(0); T = E.shape[0]
    W = E.T @ E / T
    sd = np.sqrt(np.diag(W)); sd[sd == 0] = 1e-12
    R = W / np.outer(sd, sd); Es = E / sd
    v = np.zeros_like(R)
    for i in range(E.shape[1]):
        v[i] = ((Es[:, [i]] * Es) ** 2).mean(0) - R[i] ** 2
    v = v * T / (T - 1) ** 2
    off = ~np.eye(len(R), dtype=bool)
    lam = float(np.clip(v[off].sum() / max((R[off] ** 2).sum(), 1e-12), 0, 1))
    Rs = (1 - lam) * R; np.fill_diagonal(Rs, 1.0)
    return Rs * np.outer(sd, sd), lam


def G_of(method, E):
    n, m = S.shape
    if method == "bu":
        return np.hstack([np.zeros((m, n - m)), np.eye(m)]), None
    if method == "ols":
        Wi = np.eye(n)
    elif method == "wls_s":
        Wi = np.diag(1.0 / S.sum(1))
    elif method == "wls_v":
        Wi = np.diag(1.0 / np.var(E, axis=0))
    elif method == "mint_shrink":
        W, lam = shrink_cov(E); Wi = np.linalg.pinv(W)
        return np.linalg.solve(S.T @ Wi @ S, S.T @ Wi), lam
    elif method == "mint_sample":
        Ec = E - E.mean(0); W = Ec.T @ Ec / len(E); Wi = np.linalg.pinv(W)
    return np.linalg.solve(S.T @ Wi @ S, S.T @ Wi), None


METHODS = ["base", "bu", "ols", "wls_s", "wls_v", "mint_shrink", "mint_sample"]
LABEL = {"base": "整合なし", "bu": "ボトムアップ", "ols": "OLS", "wls_s": "WLS（構造）", "wls_v": "WLS（分散）",
         "mint_shrink": "MinT（縮小）", "mint_sample": "MinT（標本の共分散）"}

test_origins = pd.date_range("2017-12-01", "2018-12-01", freq="MS")
cal_origins = pd.date_range("2015-12-01", "2017-11-01", freq="MS")
all_origins = list(cal_origins) + list(test_origins)
res = Parallel(n_jobs=2)(delayed(base_at)(o) for o in all_origins)
base = dict(zip(all_origins, res))

# 尺度：学習期間（2011〜起点）の季節ナイーブの平均絶対誤差（MASE の分母）
rec, lamb, conds = [], [], []
for o in all_origins:
    F, E = base[o]
    tr = Y.loc[:o].values
    scale = np.mean(np.abs(tr[12:] - tr[:-12]), axis=0)
    fut = Y.loc[o + pd.DateOffset(months=1): o + pd.DateOffset(months=H)].values
    hh = len(fut)
    Ec = E[12:]                                   # 最初の1年は当てはめが不安定なので除く
    conds.append(np.linalg.cond(Ec.T @ Ec / len(Ec)))
    for mth in METHODS:
        if mth == "base":
            P = F
        else:
            G, lam = G_of(mth, Ec)
            P = (S @ G @ F.T).T
            if lam is not None:
                lamb.append(lam)
        for h in range(hh):
            for j in range(S.shape[0]):
                rec.append((o, mth, h + 1, j, level[j], fut[h, j], P[h, j], scale[j]))
R = pd.DataFrame(rec, columns=["origin", "method", "h", "j", "level", "y", "yhat", "scale"])
R["ae_scaled"] = (R.y - R.yhat).abs() / R.scale
R["se"] = (R.y - R.yhat) ** 2
R["logerr"] = np.log(R.y / R.yhat)
R["set"] = np.where(R.origin.isin(test_origins), "test", "cal")

T = R[R.set == "test"]
mase = T.groupby(["method", "level"]).ae_scaled.mean().unstack()[["全国", "地方", "都道府県"]]
mase["58系列"] = T.groupby("method").ae_scaled.mean()
trace = T.groupby("method").se.sum() / T[T.method == "base"].se.sum()     # 誤差の2乗の合計（共分散の対角和）を整合なしで割る
mase["誤差の2乗の合計（整合なし＝1）"] = trace
mase = mase.loc[METHODS]
mase.index = [LABEL[m] for m in mase.index]
mase.round(4).to_csv(RES / "b_accuracy_test.csv", encoding="utf-8")

# 整合なしの予測の、全国と47都道府県の合計のずれ
gap = []
for o in test_origins:
    F, _ = base[o]
    gap.append((F[:, 0] / F[:, 11:].sum(1) - 1) * 100)
gap = np.concatenate(gap)

# ---------- コンフォーマル区間（1か月先、80%）：較正 24 起点 → 試す 13 起点 ----------
ALPHA = 0.2
ci = []
for mth in ("base", "mint_shrink"):
    c1 = R[(R.method == mth) & (R.h == 1)]
    for j in range(S.shape[0]):
        cs = c1[(c1.set == "cal") & (c1.j == j)].logerr.abs().values
        q = conformal_q(cs, ALPHA)
        tt = c1[(c1.set == "test") & (c1.j == j)]
        ci.append({"method": LABEL[mth], "j": j, "name": names[j], "level": level[j], "q": q,
                   "width_pct": (np.exp(q) - np.exp(-q)) * 100, "n_cal": len(cs),
                   "covered": int((tt.logerr.abs() <= q).sum()), "n_test": len(tt)})
CI = pd.DataFrame(ci)
CI.to_csv(RES / "b_conformal_by_series.csv", index=False, encoding="utf-8")
cov = CI.groupby(["method", "level"]).apply(lambda g: pd.Series({"coverage": g.covered.sum() / g.n_test.sum(),
                                                                 "width_pct_median": g.width_pct.median()}))
cov = cov.unstack("level")
cov.round(4).to_csv(RES / "b_conformal_by_level.csv", encoding="utf-8")

# 区間の端は足し算が合うか（MinT の点予測に付けた区間、試す13起点の1か月先）
co = []
cim = CI[CI.method == LABEL["mint_shrink"]].set_index("j")
for o in test_origins:
    P = R[(R.origin == o) & (R.method == "mint_shrink") & (R.h == 1)].sort_values("j").yhat.values
    up = P * np.exp(cim.q.values)
    co.append({"origin": o, "national_upper": up[0], "sum_pref_upper": up[11:].sum(),
               "ratio_pct": (up[11:].sum() / up[0] - 1) * 100})
CO = pd.DataFrame(co); CO.to_csv(RES / "b_interval_coherence.csv", index=False, encoding="utf-8")

# ---------- 図 4：段ごとの精度 ----------
show = ["整合なし", "ボトムアップ", "OLS", "WLS（構造）", "WLS（分散）", "MinT（縮小）", "MinT（標本の共分散）"]
rel = mase[["全国", "地方", "都道府県"]].div(mase.loc["整合なし", ["全国", "地方", "都道府県"]]) * 100 - 100
fig, axs = plt.subplots(1, 2, figsize=(12, 4.4), gridspec_kw={"width_ratios": [3, 1.3]})
x = np.arange(3); wbar = 0.12
cols = [GRAY, "#9bb7cf", "#d8b48a", GREEN, "#7fbf9f", BLUE, PURPLE]
for i, (m, c) in enumerate(zip(show, cols)):
    axs[0].bar(x + (i - 3) * wbar, rel.loc[m].values, width=wbar, color=c, label=m)
axs[0].axhline(0, color="#555", lw=.8)
axs[0].set_xticks(x, ["全国（1）", "地方（10）", "都道府県（47）"])
axs[0].set_ylabel("MASE の変化（整合なしに対する%）")
axs[0].set_title("段ごとの精度（2018〜19年、1〜12か月先、13起点）", fontsize=11)
axs[0].legend(fontsize=7.5, ncol=2, loc="upper left")
tv = (mase["誤差の2乗の合計（整合なし＝1）"].loc[show] * 100 - 100)
axs[1].barh(range(len(show)), tv.values, color=cols)
axs[1].set_yticks(range(len(show)), show, fontsize=8); axs[1].invert_yaxis()
axs[1].axvline(0, color="#555", lw=.8)
axs[1].set_title("誤差の2乗の合計\n（MinT が小さくする量、整合なしに対する%）", fontsize=10)
fig.tight_layout()
save(fig, "p03_04_reconciliation.png", SRC)

# ---------- 図 5：整合した予測に付けたコンフォーマル区間 ----------
fig, axs = plt.subplots(1, 2, figsize=(11, 4))
lv = ["全国", "地方", "都道府県"]
for i, (m, c) in enumerate(((LABEL["base"], GRAY), (LABEL["mint_shrink"], BLUE))):
    axs[0].bar(np.arange(3) + (i - .5) * .35, [cov.loc[m, ("coverage", l)] * 100 for l in lv], width=.35, color=c, label=m)
    axs[1].bar(np.arange(3) + (i - .5) * .35, [cov.loc[m, ("width_pct_median", l)] for l in lv], width=.35, color=c, label=m)
axs[0].axhline(80, color="#555", ls="--", lw=1)
axs[0].set_xticks(range(3), lv); axs[0].set_ylabel("区間に入った割合（%）、目標80%")
axs[0].set_title("1か月先の区間の当たり方（13起点。全国は13点だけ）", fontsize=11); axs[0].legend(fontsize=8)
axs[1].set_xticks(range(3), lv); axs[1].set_ylabel("区間の幅（予測に対する%、中央値）")
axs[1].set_title("区間の幅", fontsize=11)
fig.suptitle(f"整合した予測にも区間は付けられる。ただし区間の端は足し算が合わない（県の上端の合計は全国の上端より平均{CO.ratio_pct.mean():.0f}%大きい）", fontsize=11)
fig.tight_layout()
save(fig, "p03_05_reconciled_intervals.png", SRC)

gm = lambda m, c: float(mase.loc[m, c])
main = {
    "n_series": int(S.shape[0]), "n_test_origins": len(test_origins), "n_cal_origins": len(cal_origins),
    "gap_abs_median_pct": float(np.median(np.abs(gap))), "gap_abs_max_pct": float(np.abs(gap).max()),
    "shrink_lambda_mean": float(np.mean(lamb)), "shrink_lambda_min": float(np.min(lamb)), "shrink_lambda_max": float(np.max(lamb)),
    "resid_cov_condition_median": float(np.median(conds)),
    "resid_T_first_origin": int(len(Y.loc[:all_origins[0]]) - 12),
}
for m in show:
    for c in ("全国", "地方", "都道府県", "58系列", "誤差の2乗の合計（整合なし＝1）"):
        main[f"{m}|{c}"] = gm(m, c)
for m in (LABEL["base"], LABEL["mint_shrink"]):
    for l in lv:
        main[f"conf|{m}|{l}|coverage"] = float(cov.loc[m, ("coverage", l)])
        main[f"conf|{m}|{l}|width"] = float(cov.loc[m, ("width_pct_median", l)])
main["upper_sum_ratio_mean_pct"] = float(CO.ratio_pct.mean())
json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()},
          open(RES / "b_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(mase.round(3).to_string()); print(cov.round(3).to_string()); print(json.dumps(main, ensure_ascii=False, indent=0)[:1500])
