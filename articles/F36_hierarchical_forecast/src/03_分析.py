"""03 分析：58系列（全国・10地方・47都道府県）を別々に予測し、6通りの整合で精度（MASE）を比べる。
ローリング予測：予測の起点を1か月ずつずらし、起点までのデータだけで当てはめ直す（拡張窓）。
"""
import sys, json, time
from multiprocessing import Pool
import numpy as np, pandas as pd
from common import (load, all_series, fit_forecast, G_matrix, METHODS, RES, PREFS, REGIONS)

H = 12


def one_origin(args):
    col, start, origin, model, end = args
    bottom = load(col)
    Y, S, names, level = all_series(bottom)
    tr = Y.loc[start:origin]
    te = Y.loc[origin + pd.offsets.MonthBegin(1):end]
    n = Y.shape[1]
    F = np.zeros((H, n)); R = []
    for j in range(n):
        yj = tr.iloc[:, j]
        f, fit = fit_forecast(yj, H, model)
        F[:, j] = f
        R.append(yj.values - fit)
    R = np.array(R).T[13:]                                   # 最初の1年は当てはめ値が不安定なので除く
    # トップダウン：直近36か月の「全国に占める割合」の平均
    share = (tr.iloc[-36:, 11:].div(tr.iloc[-36:, 0], axis=0)).mean().values
    rec = {"base": F}
    for m in ["bu", "td", "ols", "wlsv", "mint"]:
        G = G_matrix(S, m, resid=R, props=share)
        rec[m] = (S @ G @ F.T).T
    # MASE の分母：学習期間の季節ナイーブ（12か月前）の平均絶対誤差
    scale = (tr - tr.shift(12)).abs().iloc[12:].mean().values
    rows = []
    for h in range(1, min(H, len(te)) + 1):
        a = te.iloc[h - 1].values
        for m, M in rec.items():
            e = np.abs(M[h - 1] - a)
            for j in range(n):
                rows.append((origin.strftime("%Y-%m"), h, names[j], level[j], m, e[j], scale[j], a[j], M[h - 1][j]))
    # 整合なしの「足し算のずれ」：47都道府県の予測の合計 − 全国の予測
    gap = [(origin.strftime("%Y-%m"), h, F[h - 1, 0], F[h - 1, 11:].sum()) for h in range(1, H + 1)]
    return rows, gap


def run(tag, col="total", start="2011-01", origins=None, model="ets", end="2019-12", procs=2):
    t0 = time.time()
    args = [(col, pd.Timestamp(start), o, model, pd.Timestamp(end)) for o in origins]
    with Pool(procs) as p:
        out = p.map(one_origin, args)
    rows = [r for o in out for r in o[0]]
    gaps = [g for o in out for g in o[1]]
    df = pd.DataFrame(rows, columns=["origin", "h", "series", "level", "method", "abs_err", "scale", "actual", "fc"])
    df.to_csv(RES / f"errors_{tag}.csv.gz", index=False, compression="gzip")
    pd.DataFrame(gaps, columns=["origin", "h", "national_fc", "sum_pref_fc"]).to_csv(RES / f"gap_{tag}.csv", index=False)
    print(tag, len(df), f"{time.time()-t0:.0f}s", flush=True)
    return df


def summary(df):
    df = df.assign(ase=df.abs_err / df.scale)
    s = df.groupby(["level", "method"]).ase.mean().unstack()
    s.loc["全体"] = df.groupby("method").ase.mean()
    return s


if __name__ == "__main__":
    which = sys.argv[1:] or ["main", "start2014", "japanese", "foreign", "arima", "post", "covid"]
    pre = list(pd.date_range("2017-12-01", "2018-12-01", freq="MS"))
    if "main" in which:
        run("main", origins=pre)
    if "start2014" in which:
        run("start2014", start="2014-01", origins=pre)
    if "japanese" in which:
        run("japanese", col="japanese", origins=pre)
    if "foreign" in which:
        run("foreign", col="foreign", origins=pre)
    if "arima" in which:
        run("arima", model="arima", origins=pre[::3])
    if "snaive" in which:
        run("snaive", model="snaive", origins=pre)
    if "post" in which:          # コロナ後：2023年1月から学習、起点 2024/12〜2025/11、評価は 2025/12 まで
        run("post", start="2023-01", origins=list(pd.date_range("2024-12-01", "2025-11-01", freq="MS")), end="2025-12")
    if "covid" in which:         # コロナ直前の起点（2019/12）から2020年を予測：どの手法でも当たらないことの確認
        run("covid", origins=[pd.Timestamp("2019-12-01")], end="2020-12", procs=1)
