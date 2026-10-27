"""03b シミュレーション：答え（本当の山と谷）が分かっている人工データで、4つの見方の「早さ」と「空振り」を比べる
- 傾き：拡張期は月 +0.25%、後退期は月 −1.2%（鉱工業生産の典型的な動きに近い値）
- 長さ：拡張期 30〜80か月、後退期 8〜20か月（一様分布）
- 季節：鉱工業生産の原数値と季節調整値の差から作った12か月の型（固定）
- 不規則な動き：平均0の正規分布。標準偏差は鉱工業生産から推定した 1.2% を基準に、0.5倍・1倍・2倍
- 季節調整の誤差：季節調整値に標準偏差 0.3% の誤差を足す
- 前年比と前年比の前月差は原数値から、ほかは季節調整値から作る（実データと同じ）
（3か月平均の前月比は、対数で見ると3か月前比の1/3と同じになるので、ここでは入れていない）
各設定 300 回（1回 600か月）。乱数の種は固定。"""
import numpy as np
import pandas as pd
from common import DATA, RES, SEED, IND

G_EXP, G_REC = 0.25, -1.2
SD_BASE, SA_ERR = 1.2, 0.3
NREP, T = 300, 600
KS = (1, 2, 3, 4)
GUARD = 6


def seasonal_pattern():
    lv = pd.read_csv(DATA / "levels.csv", parse_dates=["date"])
    d = lv[lv.series == "鉱工業生産"].set_index("date")
    sf = (np.log(d.nsa) - np.log(d.sa)) * 100
    p = sf.groupby(sf.index.month).mean()
    return (p - p.mean()).values


def simulate(rng, sd, seas):
    phase, tps = np.empty(T), []
    t, state = 0, 1
    while t < T:
        L = int(rng.integers(30, 81)) if state == 1 else int(rng.integers(8, 21))
        phase[t:t + L] = state
        t += L
        if t < T:
            tps.append((t - 1, "peak" if state == 1 else "trough"))   # 最後の月が山（谷）
        state = -state
    g = np.where(phase == 1, G_EXP, G_REC)
    trend = np.cumsum(g)
    s = np.tile(seas, T // 12 + 1)[:T]
    irr = rng.normal(0, sd, T)
    nsa = trend + s + irr                      # 対数×100
    sa = trend + irr + rng.normal(0, SA_ERR, T)
    yoy = pd.Series(nsa).diff(12)
    ind = pd.DataFrame({
        "前年比": yoy,
        "前月比": pd.Series(sa).diff(1),
        "3か月前比": pd.Series(sa).diff(3),
        "前年比の前月差": yoy.diff(),
    })
    # 局面：山の翌月〜谷を後退にそろえる（実データと同じ定義）
    ph = np.ones(T)
    tp_idx = [i for i, _ in tps]
    for (i, ty), nxt in zip(tps, tps[1:] + [(T - 1, None)]):
        if ty == "peak":
            ph[i + 1:nxt[0] + 1] = -1
    dist = np.array([min([abs(t - i) for i in tp_idx]) if tp_idx else T for t in range(T)])
    return ind, tps, ph, dist


def lag_of(sig, i, direction, k, after=24):
    run = 0
    for t in range(i, min(i + after + 1, len(sig))):
        v = sig[t]
        if np.isnan(v):
            run = 0
            continue
        run = run + 1 if np.sign(v) == direction else 0
        if run >= k:
            return t - i
    return np.nan


def alarms(sig, ph, dist, k):
    n, run, cnt = 0, 0, 0
    for t in range(len(sig)):
        if np.isnan(sig[t]):
            continue
        cnt += 1
        wrong = (np.sign(sig[t]) == -ph[t]) and dist[t] >= GUARD
        run = run + 1 if wrong else 0
        if run == k:
            n += 1
    return n, cnt / 12


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    seas = seasonal_pattern()
    rows = []
    for mult in (0.5, 1.0, 2.0):
        sd = SD_BASE * mult
        for rep in range(NREP):
            ind, tps, ph, dist = simulate(rng, sd, seas)
            for i_name in IND:
                sig = ind[i_name].values
                for k in KS:
                    lags = [lag_of(sig, i, -1 if ty == "peak" else 1, k) for i, ty in tps if i >= 24 and i + 24 < T]
                    n, yrs = alarms(sig, ph, dist, k)
                    rows.append({"ノイズ倍率": mult, "rep": rep, "見方": i_name, "k": k,
                                 "遅れの平均": np.nanmean(lags), "見逃し率": np.mean(np.isnan(lags)) * 100,
                                 "空振り（10年あたり）": n / yrs * 10})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "simulation_reps.csv", index=False)
    s = df.groupby(["ノイズ倍率", "見方", "k"]).agg(遅れ=("遅れの平均", "mean"), 見逃し率=("見逃し率", "mean"),
                                                   空振り=("空振り（10年あたり）", "mean")).reset_index()
    s.to_csv(RES / "simulation_summary.csv", index=False)
    print(s[s["ノイズ倍率"] == 1.0].round(2).to_string())
    print(s[s.k == 2].pivot(index="見方", columns="ノイズ倍率", values=["遅れ", "空振り"]).round(2))
