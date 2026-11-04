"""国債イールドカーブの主成分分析（水準・傾き・曲率）と、日銀の政策決定日の前後比較。

主の設定: 1992-01-06〜2026-11-02、年限 1,2,3,5,7,10,15,20年、日次の変化（bp）、共分散行列の主成分。
"""
import pathlib, json
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
d = pd.read_csv(ROOT / "data" / "jgb_yields_daily.csv", parse_dates=["date"]).set_index("date")
MAIN = ["y1", "y2", "y3", "y5", "y7", "y10", "y15", "y20"]
REG = {"1992〜2013/3": ("1992-01-01", "2013-04-03"),
       "量的・質的緩和 2013/4〜2016/9": ("2013-04-04", "2016-09-20"),
       "長短金利操作 2016/9〜2024/3": ("2016-09-21", "2024-03-18"),
       "操作の終了後 2024/3〜": ("2024-03-19", "2026-12-31")}
EVENTS = [("2013-04-04", "量的・質的金融緩和の導入"), ("2014-10-31", "量的・質的緩和の拡大"),
          ("2016-01-29", "マイナス金利の導入決定"), ("2016-09-21", "長短金利操作の導入"),
          ("2018-07-31", "長期金利の変動幅の拡大（±0.2%程度）"), ("2021-03-19", "変動幅の明確化（±0.25%程度）"),
          ("2022-12-20", "変動幅の拡大（±0.5%程度）"), ("2023-07-28", "長短金利操作の柔軟化"),
          ("2023-10-31", "1%を上限のめどに"), ("2024-03-19", "マイナス金利と長短金利操作の終了"),
          ("2024-07-31", "政策金利の引き上げ（0.25%程度）"), ("2025-01-24", "政策金利の引き上げ（0.5%程度）")]

def pca(X, k=5, corr=False):
    X = X - X.mean()
    if corr: X = X / X.std()
    C = np.cov(X.values.T)
    w, V = np.linalg.eigh(C); o = np.argsort(w)[::-1]; w, V = w[o], V[:, o]
    # 符号: PC1 は全年限プラス、PC2 は長い年限ほどプラス、PC3 は中間がマイナス
    if V[:, 0].sum() < 0: V[:, 0] *= -1
    if V[-1, 1] - V[0, 1] < 0: V[:, 1] *= -1
    mid = len(V) // 2
    if V[mid, 2] > 0: V[:, 2] *= -1
    return w / w.sum(), V[:, :k], X.values @ V[:, :k]

def dchg(cols, start="1992-01-01", end="2026-12-31", h=1):
    x = d.loc[start:end, cols].dropna()
    if h == 1: return x.diff().dropna() * 100
    x = x.resample({5: "W-FRI", 21: "ME"}[h]).last()
    return x.diff().dropna() * 100

out = {}
# 1) 主の結果
X = dchg(MAIN); sh, V, S = pca(X)
out["main"] = {"n_days": len(X), "start": str(X.index.min().date()), "end": str(X.index.max().date()),
               "share": sh[:5].round(4).tolist(), "cum3": float(sh[:3].sum().round(4))}
pd.DataFrame(V[:, :3], index=MAIN, columns=["水準", "傾き", "曲率"]).round(4).to_csv(RES / "loadings_main.csv")
scores = pd.DataFrame(S[:, :3], index=X.index, columns=["level", "slope", "curv"])
scores.to_csv(RES / "scores_main.csv")
# 水準（金利そのもの）の主成分
L = d.loc["1992":, MAIN].dropna() * 100
shL, _, _ = pca(L)
out["levels_share"] = shL[:3].round(4).tolist()
# 10年−2年の差と傾きの因子
sp = (d.loc["1992":, "y10"] - d.loc["1992":, "y2"]).diff().dropna() * 100
out["corr_spread_slope"] = float(np.corrcoef(sp.loc[scores.index], scores.slope)[0, 1].round(3))
out["corr_10y_level"] = float(np.corrcoef(X.y10, scores.level)[0, 1].round(3))
# 上位1%の日の寄与
s2 = scores.level ** 2; top = s2.sort_values(ascending=False)
out["top1pct_level_var_share"] = float((top.iloc[: int(len(top) * 0.01)].sum() / top.sum()).round(4))

# 2) 期間別
rows = []
for name, (a, b) in REG.items():
    Xr = dchg(MAIN, a, b); shr, Vr, _ = pca(Xr)
    sd = Xr.std()
    rows.append({"期間": name, "日数": len(Xr), "PC1": shr[0], "PC2": shr[1], "PC3": shr[2],
                 **{f"sd_{m}": sd[m] for m in MAIN},
                 **{f"L1_{m}": Vr[i, 0] for i, m in enumerate(MAIN)},
                 "corr_2y_20y": Xr.y2.corr(Xr.y20), "corr_10y_20y": Xr.y10.corr(Xr.y20), "corr_2y_10y": Xr.y2.corr(Xr.y10)})
reg = pd.DataFrame(rows); reg.round(4).to_csv(RES / "by_regime.csv", index=False)

# 3) 頑健性: 年限・期間・変化の幅・標準化
SETS = {"主（1〜20年の8年限）": MAIN, "短中期（1〜10年）": ["y1", "y2", "y3", "y4", "y5", "y6", "y7", "y8", "y9", "y10"],
        "超長期まで（1〜40年の11年限）": ["y1", "y2", "y3", "y5", "y7", "y10", "y15", "y20", "y25", "y30", "y40"],
        "代表5年限（2,5,10,20,30年）": ["y2", "y5", "y10", "y20", "y30"]}
rb = []
for sname, cols in SETS.items():
    for h, hn in [(1, "日次"), (5, "週次"), (21, "月次")]:
        for corr in (False, True):
            Xs = dchg(cols, "2007-11-06" if "y40" in cols else ("1999-09-02" if "y30" in cols else "1992-01-01"), h=h)
            s_, _, _ = pca(Xs, corr=corr)
            rb.append({"年限": sname, "変化の幅": hn, "標準化": "相関" if corr else "共分散", "開始": str(Xs.index.min().date()),
                       "n": len(Xs), "PC1": s_[0], "PC2": s_[1], "PC3": s_[2], "PC1-3": s_[:3].sum()})
rb = pd.DataFrame(rb); rb.round(4).to_csv(RES / "robustness.csv", index=False)
out["robust_PC1_range"] = [float(rb.PC1.min().round(4)), float(rb.PC1.max().round(4))]
out["robust_cum3_range"] = [float(rb["PC1-3"].min().round(4)), float(rb["PC1-3"].max().round(4))]

# 4) 主成分の数: 1つ前の期間で決めた負荷量で、次の期間の変化をどれだけ再現できるか
names = list(REG); recon = []
for i in range(len(names) - 1):
    Xa = dchg(MAIN, *REG[names[i]]); Xb = dchg(MAIN, *REG[names[i + 1]])
    _, Va, _ = pca(Xa, k=8)
    Xb0 = (Xb - Xb.mean()).values; tot = (Xb0 ** 2).sum()
    _, Vb, _ = pca(Xb, k=8)
    for k in range(1, 6):
        P = Va[:, :k]; e = Xb0 - Xb0 @ P @ P.T
        Q = Vb[:, :k]; e2 = Xb0 - Xb0 @ Q @ Q.T
        recon.append({"学習": names[i], "評価": names[i + 1], "k": k,
                      "説明率_前の期間の負荷量": 1 - (e ** 2).sum() / tot, "説明率_同じ期間": 1 - (e2 ** 2).sum() / tot})
recon = pd.DataFrame(recon); recon.round(4).to_csv(RES / "n_components_oos.csv", index=False)

# 5) 出来事の前後（前日→当日の変化を、前後250営業日の標準偏差で割る）
ev = []
for day, lab in EVENTS:
    t = pd.Timestamp(day)
    if t not in scores.index:
        t = scores.index[scores.index.searchsorted(t)]
    i = scores.index.get_loc(t)
    win = scores.iloc[max(0, i - 250): i + 251].drop(index=t)
    two = scores.iloc[i: i + 2].sum()  # 当日＋翌日
    ev.append({"日付": str(t.date()), "出来事": lab,
               "10年_bp": X.y10.iloc[i], "2年_bp": X.y2.iloc[i], "20年_bp": X.y20.iloc[i],
               **{f"z_{c}": scores[c].iloc[i] / win[c].std() for c in ["level", "slope", "curv"]},
               **{f"z2_{c}": two[c] / (win[c].std() * np.sqrt(2)) for c in ["level", "slope", "curv"]},
               "rank_abs_level_in_window": int((win.level.abs() > abs(scores.level.iloc[i])).sum()) + 1})
ev = pd.DataFrame(ev); ev.round(3).to_csv(RES / "events.csv", index=False)
out["events_absz_level_gt2"] = int((ev.z_level.abs() > 2).sum())
out["events_absz_any_gt2"] = int((ev[["z_level", "z_slope", "z_curv"]].abs() > 2).any(axis=1).sum())
# 並べ替え: 同じ数の日を無作為に選んだときの |z水準| の平均
rng = np.random.default_rng(192)
sdl = scores.level.rolling(501, center=True, min_periods=200).std()
zall = (scores.level / sdl).dropna()
obs = ev.z_level.abs().mean(); sims = np.array([zall.sample(len(ev), random_state=int(s)).abs().mean() for s in rng.integers(0, 1e9, 5000)])
out["events_mean_absz_level"] = float(round(obs, 3)); out["perm_p_level"] = float(((sims >= obs).sum() + 1) / (len(sims) + 1))
for c in ["slope", "curv"]:
    sdc = scores[c].rolling(501, center=True, min_periods=200).std(); zc = (scores[c] / sdc).dropna()
    o = ev[f"z_{c}"].abs().mean(); sm = np.array([zc.sample(len(ev), random_state=int(s)).abs().mean() for s in rng.integers(0, 1e9, 5000)])
    out[f"events_mean_absz_{c}"] = float(round(o, 3)); out[f"perm_p_{c}"] = float(((sm >= o).sum() + 1) / (len(sm) + 1))
# 最大の動きの日
big = scores.assign(z=scores.level / sdl).dropna().z.abs().sort_values(ascending=False).head(10)
out["top10_level_days"] = [[str(i.date()), round(float(v), 2)] for i, v in big.items()]

json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
print(reg.round(3).to_string())
print(ev.round(2).to_string())
print(recon.round(3).to_string())
print(rb.round(3).to_string())
