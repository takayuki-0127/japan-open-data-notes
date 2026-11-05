# F205 電力需要の予測を実務で回す（前編）：決めること・誤差の値段・作り直す時
# 新しいデータは取らない。F157・F92・F22 の結果と整形済みデータを使う。
import json, numpy as np, pandas as pd
from pathlib import Path
B = Path(__file__).resolve().parents[1]
DA, RE = B/"data", B/"results"
RE.mkdir(exist_ok=True)
rng = np.random.default_rng(205)
out = {}

# ---------------- A. 何で測るか（指標と粒度で、どのモデルが「いちばん」かが変わるか）
P = pd.read_csv(DA/"f157_pred_tokyo_2025_26.csv.gz", parse_dates=["ts"])
P["date"] = P.ts.dt.normalize()
M = ["固定（開始前に1回）", "四半期ごと", "毎月", "毎週", "監視ルールで",
     "毎月・直近3年だけで学習", "固定・1年前に学習したまま", "固定・2年前に学習したまま",
     "線形回帰・毎日"]

def metrics(df, cols):
    rows = []
    g = df.groupby("date")
    act_sum = g.actual.sum(); act_pk = g.actual.max()
    for c in cols:
        e = df[c] - df.actual
        s = g[c].sum(); pk = g[c].max()
        rows.append(dict(model=c,
            時間ごとのMAPE=(e.abs()/df.actual).mean()*100,
            時間ごとのRMSE=np.sqrt((e**2).mean()),
            日量のMAPE=((s-act_sum).abs()/act_sum).mean()*100,
            ピークのMAPE=((pk-act_pk).abs()/act_pk).mean()*100,
            ピーク下振れ3超の日数=int(((act_pk-pk)/act_pk > 0.03).sum()),
            悪い日95点=( (e.abs()/df.actual).groupby(df.date).mean().quantile(.95)*100 )))
    return pd.DataFrame(rows).set_index("model")

mt = metrics(P, M)
rank = mt.rank(method="min")
mt.round(4).to_csv(RE/"A_metrics_tokyo.csv"); rank.to_csv(RE/"A_ranks_tokyo.csv")
from scipy.stats import kendalltau
cols = list(mt.columns)
tau = pd.DataFrame([[kendalltau(rank[a], rank[b])[0] for b in cols] for a in cols], index=cols, columns=cols)
tau.round(3).to_csv(RE/"A_rank_kendall.csv")
best = {c: mt[c].idxmin() for c in cols}
out["A_best_by_metric"] = best

# 差の区間：いちばん良いモデル vs 固定（日ごとの値を1週間ずつ引き直す）
def daily_err(df, c):
    g = df.groupby("date")
    return pd.DataFrame({
        "h": ((df[c]-df.actual).abs()/df.actual).groupby(df.date).mean()*100,
        "e": ((g[c].sum()-g.actual.sum()).abs()/g.actual.sum())*100,
        "p": ((g[c].max()-g.actual.max()).abs()/g.actual.max())*100})
base = daily_err(P, "固定（開始前に1回）")
nb = len(base)//7
diffs = []
for c in M[1:]:
    d = daily_err(P, c) - base
    arr = d.values[:nb*7].reshape(nb, 7, 3)
    bs = np.array([arr[rng.integers(0, nb, nb)].reshape(-1, 3).mean(0) for _ in range(1000)])
    for j, k in enumerate(["時間ごと", "日量", "ピーク"]):
        diffs.append(dict(model=c, 指標=k, 差=d.values[:, j].mean(), lo=np.percentile(bs[:, j], 2.5), hi=np.percentile(bs[:, j], 97.5)))
pd.DataFrame(diffs).round(4).to_csv(RE/"A_diff_vs_fixed.csv", index=False)

# 頑健性：関西・2024/25年度の東京でも順位が入れ替わるか
K = pd.read_csv(DA/"f157_pred_kansai_2025_26.csv.gz", parse_dates=["ts"]); K["date"] = K.ts.dt.normalize()
mk = metrics(K, ["固定（開始前に1回）", "四半期ごと", "毎月", "毎週", "監視ルールで"])
mk.round(4).to_csv(RE/"A_metrics_kansai.csv")
Q = pd.read_csv(DA/"f157_pred_tokyo_2024_25.csv.gz", parse_dates=["ts"]); Q["date"] = Q.ts.dt.normalize()
mq = metrics(Q, ["固定（開始前に1回）", "四半期ごと", "毎月", "毎週", "監視ルールで", "固定・1年前に学習したまま", "固定・2年前に学習したまま"])
mq.round(4).to_csv(RE/"A_metrics_tokyo_2024_25.csv")
out["A_best_kansai"] = {c: mk[c].idxmin() for c in mk.columns}
out["A_best_tokyo_2024_25"] = {c: mq[c].idxmin() for c in mq.columns}

# ---------------- A2. いつまでに出すか（締め切りで外れ方がどれだけ変わるか）
H = pd.read_csv(DA/"hourly_tokyo_demand.csv", parse_dates=["ts"]).set_index("ts").demand
ev = (H.index >= "2025-10-01") & (H.index < "2026-10-01")
lead = []
for d in [1, 2, 3, 7, 14]:
    f = H.shift(24*d)
    m = ((f-H).abs()/H)[ev].mean()*100
    lead.append(dict(手法=f"{d}日前の同じ時刻", 何日前に出せるか=d, MAPE=m))
lead.append(dict(手法="モデル（前日の夜に予測・毎月学習し直し）", 何日前に出せるか=1, MAPE=mt.loc["毎月", "時間ごとのMAPE"]))
pd.DataFrame(lead).round(3).to_csv(RE/"A2_leadtime.csv", index=False)
out["A2_leadtime"] = lead

# ---------------- B. 外れの値段（下振れと上振れの値段が違うとき、どの予測を出すか）
F = pd.read_csv(DA/"f92_peak_quantiles_tokyo.csv", parse_dates=["date"])
F = F[F.fold != "fold"]
TAUS = [0.5, 0.8, 0.9, 0.95, 0.975, 0.99]
RATIOS = [1, 2, 4, 9, 19, 49]
def cost(f, a, r):  # 足りない1MWの値段 r、余る1MWの値段 1（例として置いた比）
    return np.where(a > f, (a-f)*r, (f-a)*1.0)
cand = {"点予測（そのまま）": F.point}
for m in [3, 5, 8]: cand[f"点予測＋{m}%"] = F[f"fixed{m}"]
for t in TAUS: cand[f"分位点{t}（コンフォーマル）"] = F[f"conf_{t}"]
rows = []
for r in RATIOS:
    base_c = cost(F.point, F.actual, r).mean()
    for k, f in cand.items():
        rows.append(dict(比=r, 出す予測=k, 一日あたりの値段=cost(f, F.actual, r).mean(), 指数=cost(f, F.actual, r).mean()/base_c*100))
Bc = pd.DataFrame(rows); Bc.round(3).to_csv(RE/"B_cost_by_option.csv", index=False)
bestB = Bc.loc[Bc.groupby("比").指数.idxmin()][["比", "出す予測", "指数"]]
bestB.round(2).to_csv(RE/"B_best_option.csv", index=False)
out["B_best"] = bestB.round(2).to_dict("records")

# 前の年度で「上乗せ幅」を決め、次の年度に使う（実務で回せる形）
folds = [f for f in F.fold.unique()]
rowsR = []
grid = np.linspace(-0.02, 0.15, 171)
for r in RATIOS:
    tau_star = r/(1+r)
    for i in range(1, len(folds)):
        tr = F[F.fold.isin(folds[:i])]; te = F[F.fold == folds[i]]
        cs = [cost(tr.point*(1+g), tr.actual, r).mean() for g in grid]
        g = grid[int(np.argmin(cs))]
        c_point = cost(te.point, te.actual, r).mean()
        c_g = cost(te.point*(1+g), te.actual, r).mean()
        # 理屈どおりの分位点（τ*に近い利用可能な分位点）
        tn = min(TAUS, key=lambda t: abs(t-tau_star))
        c_q = cost(te[f"conf_{tn}"], te.actual, r).mean()
        c_l = cost(te[f"lgbq_{tn}"], te.actual, r).mean()
        rowsR.append(dict(比=r, 理屈の分位点=round(tau_star, 3), 使った分位点=tn, 評価の年度=folds[i], 上乗せ幅=g,
                          上乗せの指数=c_g/c_point*100, コンフォーマルの指数=c_q/c_point*100, LightGBM分位点の指数=c_l/c_point*100))
R = pd.DataFrame(rowsR); R.round(4).to_csv(RE/"B_rolling_margin.csv", index=False)
Rs = R.groupby("比")[["上乗せ幅", "上乗せの指数", "コンフォーマルの指数", "LightGBM分位点の指数"]].agg(["median", "min", "max"])
Rs.round(3).to_csv(RE/"B_rolling_summary.csv")
out["B_rolling_median"] = R.groupby("比")[["上乗せ幅", "上乗せの指数", "コンフォーマルの指数", "LightGBM分位点の指数"]].median().round(3).to_dict("index")

# ---------------- C. いつ作り直すか（ずれを何日で気づけるか、空振りは何回か）
def daily_frame(df, col):
    g = df.groupby("date")
    return pd.DataFrame({"act": g.actual.apply(list), "f": g[col].apply(list)})

def run_rules(df, col, delta=0.0, start=None):
    a = df.actual.values.astype(float).copy()
    if delta and start is not None:
        a[df.date.values >= np.datetime64(start)] *= (1+delta)
    f = df[col].values
    dd = df.date.values
    days = np.unique(dd)
    ape = pd.Series(np.abs(f-a)/a).groupby(dd).mean().values*100
    bias = pd.Series((f-a)/a).groupby(dd).mean().values*100   # +:上に外れ
    return days, ape, bias

def alarms(days, ape, bias, rule, thr, gap=14):
    s_ape = pd.Series(ape).rolling(14).mean().values
    s_b = pd.Series(bias).rolling(7).mean().values
    al = []; last = -999; cus_p = cus_n = 0.0
    k = 0.5
    for i in range(len(days)):
        if rule == "MAPE14日":
            hit = s_ape[i] > thr
        elif rule == "ずれ7日":
            hit = abs(s_b[i]) > thr
        else:  # CUSUM（ずれの累積）
            cus_p = max(0, cus_p + (-bias[i]) - k)   # 下振れ（需要が予測より大）を累積
            cus_n = max(0, cus_n + (bias[i]) - k)
            hit = max(cus_p, cus_n) > thr
        if hit and i - last >= gap and not np.isnan(s_ape[i] if rule == "MAPE14日" else (s_b[i] if rule == "ずれ7日" else 0)):
            al.append(i); last = i
            cus_p = cus_n = 0.0
    return al

RULES = {"MAPE14日": [2.0, 2.5, 3.0, 3.5, 4.0], "ずれ7日": [0.75, 1.0, 1.5, 2.0, 2.5], "CUSUM": [3, 5, 8, 12, 16]}
DELTAS = [0.01, 0.02, 0.03, 0.05]
def drift_study(df, col, label):
    days, ape0, b0 = run_rules(df, col)
    starts = pd.date_range("2025-11-15", "2026-07-15", freq="14D") if label != "東京2024" else pd.date_range("2024-11-15", "2025-07-15", freq="14D")
    rows = []
    for rule, thrs in RULES.items():
        for thr in thrs:
            fa = len(alarms(days, ape0, b0, rule, thr))   # ずれを入れない1年の警報＝空振り
            for de in DELTAS:
                delays = []
                for s in starts:
                    d2, ape, b = run_rules(df, col, de, s)
                    al = alarms(d2, ape, b, rule, thr)
                    si = int(np.searchsorted(d2, np.datetime64(s)))
                    after = [x - si for x in al if x >= si]
                    delays.append(after[0] if after else np.nan)
                delays = np.array(delays, float)
                rows.append(dict(データ=label, ルール=rule, しきい値=thr, 空振り_年=fa, ずれ=de,
                                 気づくまでの日数_中央値=np.nanmedian(delays) if np.isfinite(delays).any() else np.nan,
                                 三十日以内に気づいた割合=np.mean(np.nan_to_num(delays, nan=999) <= 30)))
    return pd.DataFrame(rows)

C = pd.concat([drift_study(P, "固定（開始前に1回）", "東京2025"),
               drift_study(K, "固定（開始前に1回）", "関西2025"),
               drift_study(Q, "固定（開始前に1回）", "東京2024")])
C.round(3).to_csv(RE/"C_drift_detection.csv", index=False)

# 気づいたあと：学習し直す代わりに「直近14日の比で割り戻す」だけでどこまで戻るか（ずれ+3%・2026-02-01から）
days, ape, b = run_rules(P, "固定（開始前に1回）", 0.03, "2026-02-01")
a = P.actual.values*np.where(P.date.values >= np.datetime64("2026-02-01"), 1.03, 1.0)
f = P["固定（開始前に1回）"].values.copy()
dd = P.date.values
ratio = pd.Series(a/f).groupby(dd).mean()
corr = ratio.rolling(14).mean().shift(1).reindex(dd).values  # 前日までの14日平均の比
after = dd >= np.datetime64("2026-02-01")
mape_none = (np.abs(f-a)/a)[after].mean()*100
f2 = np.where(np.isnan(corr), f, f*corr)
mape_corr = (np.abs(f2-a)/a)[after].mean()*100
mape_nodrift = (np.abs(f - P.actual.values)/P.actual.values)[after].mean()*100
out["C_recal"] = dict(ずれなしのMAPE=mape_nodrift, 何もしない=mape_none, 比で割り戻す=mape_corr)
ex = pd.DataFrame({"date": days, "ape": ape, "bias": b,
                   "ape14": pd.Series(ape).rolling(14).mean(), "bias7": pd.Series(b).rolling(7).mean()})
ex.round(4).to_csv(RE/"C_example_drift3_20260201.csv", index=False)
out["C_example_alarms"] = {r: [str(days[i])[:10] for i in alarms(days, ape, b, r, t)] for r, t in [("MAPE14日", 3.0), ("ずれ7日", 1.5), ("CUSUM", 8)]}

json.dump(out, open(RE/"main.json", "w"), ensure_ascii=False, indent=1, default=str)
print(json.dumps(out, ensure_ascii=False, indent=1, default=str)[:4000])
