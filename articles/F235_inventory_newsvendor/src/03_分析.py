# 03 分析：予測の外れの分布から発注量を決める（ニュースベンダー問題）
# 架空の小売チェーンが「業態全体の販売額と同じ動きをする需要」を持つとみなし、毎月の仕入れ量を決める練習。
# 損の比（足りない1単位の損 cu ÷ 余る1単位の損 co）は例として置いた値で、実在の費用ではない。
import json, numpy as np, pandas as pd
from scipy.stats import norm
rng = np.random.default_rng(235)
f = pd.read_csv("data/forecasts_h1to3.csv")
RATIOS = [1, 2, 4, 9, 19]                     # cu/co（例）
TAUS = [r / (1 + r) for r in RATIOS]          # 目標のサービス率（臨界比）= cu/(cu+co)
MODELS = ["季節ナイーブ", "ETS", "SARIMA"]
MIN_PAST = 8

def decisions(f, h=1, window=None, pooled=False, covid_out=True, taus=TAUS):
    """起点ごとに、その時点で分かっている過去の外れだけを使って倍率を決める。"""
    g = f[f.h == h].copy()
    rows = []
    for (mdl), gm in g.groupby("モデル"):
        for t in sorted(gm.起点.unique()):
            cur = gm[gm.起点 == t]
            for _, x in cur.iterrows():
                if covid_out and x.コロナ期: continue
                past = gm[(gm.対象月 <= t) & (gm.起点 < t)]                 # 起点 t の時点で答えが出ている外れ
                if covid_out: past = past[~past.コロナ期]
                if not pooled: past = past[past.業態 == x.業態]
                if window: past = past.sort_values("対象月").tail(window)
                if len(past) < MIN_PAST: continue
                r = past.比.values; e = r - 1
                for tau in taus:
                    z = norm.ppf(tau)
                    m = {"点予測そのまま": 1.0, "一律＋5%": 1.05,
                         "正規近似の安全在庫": 1 + z * e.std(ddof=1),
                         "過去の外れの分位点": np.quantile(r, tau)}
                    if mdl == "SARIMA" and np.isfinite(x.上80): m["SARIMA の80%区間の上端"] = x.上80 / x.予測
                    for k, v in m.items():
                        rows.append((mdl, x.業態, t, x.対象月, tau, k, v, x.予測, x.実績, len(past)))
    d = pd.DataFrame(rows, columns=["モデル", "業態", "起点", "対象月", "tau", "決め方", "倍率", "予測", "実績", "n_past"])
    d["発注"] = d.予測 * d.倍率
    d["不足"] = np.maximum(d.実績 - d.発注, 0) / d.実績 * 100     # 需要100あたり
    d["余り"] = np.maximum(d.発注 - d.実績, 0) / d.実績 * 100
    d["ratio"] = (d.tau / (1 - d.tau)).round(0)
    d["損"] = d.ratio * d.不足 + 1 * d.余り                          # co=1 として需要100あたりの損
    d["欠品なし"] = (d.実績 <= d.発注).astype(float)
    return d

def summarize(d):
    return d.groupby(["モデル", "決め方", "ratio"]).agg(損=("損", "mean"), サービス率=("欠品なし", "mean"),
                                                      余り=("余り", "mean"), 不足=("不足", "mean"),
                                                      倍率中央=("倍率", "median"), n=("損", "size")).reset_index()

def boot_diff(d, a, b, ratio, B=1000):
    """起点を単位にしたブートストラップで、損の差 (a − b) の95%区間"""
    x = d[d.ratio == ratio]
    pa = x[(x.モデル == a[0]) & (x.決め方 == a[1])].groupby("起点").損.mean()
    pb = x[(x.モデル == b[0]) & (x.決め方 == b[1])].groupby("起点").損.mean()
    j = pa.index.intersection(pb.index); dif = (pa[j] - pb[j]).values
    bs = [rng.choice(dif, len(dif)).mean() for _ in range(B)]
    return float(dif.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), int(len(dif))

out = {}
d1 = decisions(f, h=1); d1.to_csv("results/decisions_h1.csv.gz", index=False)
S1 = summarize(d1); S1.to_csv("results/A_summary_h1.csv", index=False)
# 最適（その月の外れが前もって分かっていた場合の損＝0）ではなく、「過去の外れの分位点」を基準に比べる
out["A"] = S1.round(3).to_dict("records")
# 目標と実際のサービス率（キャリブレーション）：細かい τ で
TAUG = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95]
dg = decisions(f, h=1, taus=TAUG)
cal = dg[dg.決め方.isin(["正規近似の安全在庫", "過去の外れの分位点"])].groupby(["モデル", "決め方", "tau"]).agg(
    サービス率=("欠品なし", "mean"), 余り=("余り", "mean"), 不足=("不足", "mean"), 倍率中央=("倍率", "median")).reset_index()
cal.to_csv("results/B_calibration_h1.csv", index=False); out["B"] = cal.round(4).to_dict("records")
dgp = decisions(f, h=1, taus=TAUG, pooled=True)
calp = dgp[dgp.決め方 == "過去の外れの分位点"].groupby(["モデル", "tau"]).agg(サービス率=("欠品なし", "mean"), 余り=("余り", "mean")).reset_index()
calp.to_csv("results/B2_calibration_pooled_h1.csv", index=False); out["B2"] = calp.round(4).to_dict("records")
# ブートストラップ
bd = {}
for r in [4, 9, 19]:
    bd[f"SARIMA 分位点 − SARIMA 点予測 r={r}"] = boot_diff(d1, ("SARIMA", "過去の外れの分位点"), ("SARIMA", "点予測そのまま"), r)
    bd[f"SARIMA 分位点 − SARIMA 正規近似 r={r}"] = boot_diff(d1, ("SARIMA", "過去の外れの分位点"), ("SARIMA", "正規近似の安全在庫"), r)
    bd[f"SARIMA 分位点 − 季節ナイーブ 分位点 r={r}"] = boot_diff(d1, ("SARIMA", "過去の外れの分位点"), ("季節ナイーブ", "過去の外れの分位点"), r)
    bd[f"SARIMA 分位点 − SARIMA 一律5% r={r}"] = boot_diff(d1, ("SARIMA", "過去の外れの分位点"), ("SARIMA", "一律＋5%"), r)
out["boot"] = bd
# 業態別（r=9、分位点）
bt = d1[(d1.ratio == 9) & (d1.決め方 == "過去の外れの分位点")].groupby(["業態", "モデル"]).agg(
    損=("損", "mean"), サービス率=("欠品なし", "mean"), 倍率中央=("倍率", "median"), 余り=("余り", "mean")).reset_index()
bt.to_csv("results/C_by_type_r9.csv", index=False); out["C"] = bt.round(3).to_dict("records")
# 頑健性
rob = {}
for name, kw in {"h=3（3か月前に発注）": dict(h=3), "直近12個の外れだけで決める": dict(window=12),
                 "6業態の外れをまとめて使う": dict(pooled=True), "コロナ期も入れる": dict(covid_out=False)}.items():
    s = summarize(decisions(f, **kw)); s.to_csv(f"results/D_rob_{name.split('（')[0].replace('=','').replace(' ','')}.csv", index=False)
    rob[name] = s[s.ratio.isin([4, 9, 19])].round(3).to_dict("records")
out["rob"] = rob
# 固定の分け方（2017〜2019年の外れで倍率を決め、2022年以降に当てはめる）— SQL でも同じ計算をする
g = f[(f.h == 1) & ~f.コロナ期]
cal_s = g[g.対象月 <= "2019-12"]; tst = g[g.対象月 >= "2022-01"]
fx = []
for (mdl, ty), c in cal_s.groupby(["モデル", "業態"]):
    q = np.quantile(c.比.values, 0.9)   # PERCENTILE_CONT(0.9) と同じ線形補間
    t = tst[(tst.モデル == mdl) & (tst.業態 == ty)]
    Q = t.予測 * q; sh = np.maximum(t.実績 - Q, 0) / t.実績 * 100; ex = np.maximum(Q - t.実績, 0) / t.実績 * 100
    fx.append((mdl, ty, q, len(c), len(t), (9 * sh + ex).mean(), (t.実績 <= Q).mean()))
FX = pd.DataFrame(fx, columns=["モデル", "業態", "倍率q90", "n_cal", "n_test", "損", "サービス率"])
FX.to_csv("results/E_fixed_split_q90.csv", index=False); out["E"] = FX.round(5).to_dict("records")
json.dump(out, open("results/main.json", "w"), ensure_ascii=False, indent=1)
# 画面表示用
p = S1[S1.ratio.isin([1, 4, 9, 19])].pivot_table(index=["モデル", "決め方"], columns="ratio", values=["損", "サービス率"]).round(3)
pd.set_option("display.width", 250); print(p); print(json.dumps(bd, ensure_ascii=False, indent=0)); print(bt.round(3)); print(FX.round(4))
for k, v in rob.items():
    x = pd.DataFrame(v); print(k); print(x[x.ratio == 9][["モデル", "決め方", "損", "サービス率", "倍率中央"]])
