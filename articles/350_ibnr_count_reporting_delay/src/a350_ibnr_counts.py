"""A350 まだ報告されていない事故の件数は、報告の遅れからどこまで当てられるのか（架空の事故、seed 350）"""
import json
import numpy as np, pandas as pd
from scipy import stats
import matplotlib.pyplot as plt
from common import *

SEED = 350
REPS = 1000
MU = 200          # 1か月に起きる事故の件数（平均）
LMAX = 36         # 報告の遅れの上限（か月）
R = 2.0           # 遅れの分布：負の二項分布（形2）。平均は場面ごとに変える
BASE = 48         # 遅れが伸びる前の月数
TMAX = 72

def delay_p(mean):
    p = stats.nbinom.pmf(np.arange(LMAX + 1), R, R / (R + mean)); return p / p.sum()

def simulate(rng, mean_after=None, change_at=BASE, freq_after=1.0, tmax=TMAX):
    """発生月×遅れ の件数表。change_at か月目より後に起きた事故は、遅れの平均が mean_after、件数が freq_after 倍"""
    p0 = delay_p(2.5); p1 = delay_p(mean_after) if mean_after else p0
    tri = np.zeros((tmax, LMAX + 1), int)
    for m in range(tmax):
        late = m >= change_at
        n = rng.poisson(MU * (freq_after if late else 1.0))
        tri[m] = rng.multinomial(n, p1 if late else p0)
    return tri

def chain_ladder(tri, T, recent=None):
    """T か月目の終わりに見えている分から、発生月ごとの最終件数を見積もる。recent=直近の何本の対角線で進み方を出すか"""
    C = np.cumsum(tri[:T], axis=1).astype(float)
    obs = T - 1 - np.arange(T)                       # 発生月 m の、見えている最後の遅れ
    f = np.ones(LMAX)
    for d in range(LMAX):
        hi = T - d - 2                               # 遅れ d+1 まで見えている最後の発生月
        if hi < 0: continue
        lo = 0 if recent is None else max(0, hi - recent + 1)
        a = C[lo:hi + 1, d].sum(); b = C[lo:hi + 1, d + 1].sum()
        f[d] = b / a if a > 0 else 1.0
    tail = np.concatenate([np.cumprod(f[::-1])[::-1], [1.0]])     # 遅れ d から最後までの倍率
    o = np.minimum(obs, LMAX)
    rep = C[np.arange(T), o]
    return rep, rep * tail[o]

def main():
    rng = np.random.default_rng(SEED)
    p0 = delay_p(2.5)
    # 1) 遅れが変わらないとき（60か月目の終わりに見積もる）
    T = 60; rows = []; by_age = {k: [] for k in range(12)}
    for r in range(REPS):
        tri = simulate(rng, tmax=T)
        true_ult = tri.sum(axis=1)
        for name, rec in (("全期間", None), ("直近12か月", 12)):
            rep, ult = chain_ladder(tri, T, rec)
            ibnr_t = (true_ult - rep).sum(); ibnr_e = (ult - rep).sum()
            rows.append(dict(method=name, ibnr_true=ibnr_t, ibnr_est=ibnr_e, err=ibnr_e / ibnr_t - 1))
            if rec is None:
                for k in range(12): by_age[k].append(ult[T - 1 - k] / true_ult[T - 1 - k] - 1)
    d0 = pd.DataFrame(rows)
    stable = [dict(method=m, ibnr_true_mean=float(g.ibnr_true.mean()), bias_pct=float(g.err.mean() * 100),
                   rmse_pct=float(np.sqrt((g.err ** 2).mean()) * 100), p10=float(g.err.quantile(0.1) * 100), p90=float(g.err.quantile(0.9) * 100))
              for m, g in d0.groupby("method", sort=False)]
    age = [dict(months_ago=k, reported_share=float(p0[:k + 1].sum()), rmse_pct=float(np.sqrt(np.mean(np.square(v))) * 100),
                p10=float(np.quantile(v, 0.1) * 100), p90=float(np.quantile(v, 0.9) * 100)) for k, v in by_age.items()]
    pd.DataFrame(stable).to_csv(RES / "stable_ibnr_error.csv", index=False); pd.DataFrame(age).to_csv(RES / "stable_by_month.csv", index=False)

    # 2) 途中で遅れが伸びたとき（49か月目に起きた事故から）
    chg = []
    for mean_after in (3.0, 4.0):
        errs = {(k, n): [] for k in (1, 3, 6, 12, 24) for n in ("全期間", "直近12か月")}
        for r in range(REPS):
            tri = simulate(rng, mean_after); true_ult = tri.sum(axis=1)
            for k in (1, 3, 6, 12, 24):
                T = BASE + k
                for name, rec in (("全期間", None), ("直近12か月", 12)):
                    rep, ult = chain_ladder(tri, T, rec)
                    errs[(k, name)].append((ult - rep).sum() / (true_ult[:T] - rep).sum() - 1)
        for (k, name), v in errs.items():
            v = np.array(v); chg.append(dict(mean_after=mean_after, months_since=k, method=name, bias_pct=float(v.mean() * 100),
                                             p10=float(np.quantile(v, 0.1) * 100), p90=float(np.quantile(v, 0.9) * 100)))
    dchg = pd.DataFrame(chg); dchg.to_csv(RES / "after_change_ibnr_error.csv", index=False)

    # 3) 遅れが伸びたことに、何か月で気づけるか
    #    見張りA：その月に起きて、その月のうちに報告された件数（直前24か月の平均と比べる。ポアソンの下側2.5%）
    #    見張りB：遅れ2か月までに報告された件数のうち、発生した月に報告された割合。直近3つの発生月をまとめる（その前の24か月と比べる。二項の下側2.5%）
    #    どちらも「2か月続けて外れたら知らせる」
    def monitor(tri, start=BASE, horizon=24):
        a_flag = []; b_flag = []
        for t in range(start, start + horizon):          # t：見張る月（0始まりの発生月の番号）
            base = tri[t - 24:t, 0].mean()
            a_flag.append(stats.poisson.cdf(tri[t, 0], base) < 0.025)
            # B は、遅れ2か月まで見えた直近3つの発生月（t-4〜t-2）をまとめて、t 月末に分かる
            ms_ = np.arange(t - 4, t - 1); x = tri[ms_, 0].sum(); n = tri[ms_, :3].sum()
            bs = np.arange(ms_[0] - 24, ms_[0]); pb = tri[bs, 0].sum() / tri[bs, :3].sum()
            b_flag.append(stats.binom.cdf(x, n, pb) < 0.025)
        def first2(fl):
            for i in range(1, len(fl)):
                if fl[i] and fl[i - 1]: return i + 1          # 伸び始めてから何か月目の終わりか
            return np.nan
        return first2(a_flag), first2(b_flag)
    det = []
    scen = {"遅れの平均 2.5→3.0か月": dict(mean_after=3.0), "遅れの平均 2.5→4.0か月": dict(mean_after=4.0),
            "変化なし": dict(), "遅れは同じで、事故が2割減った": dict(freq_after=0.8)}
    detail = {}
    for name, kw in scen.items():
        A = []; B = []
        for r in range(REPS):
            a, b = monitor(simulate(rng, **kw)); A.append(a); B.append(b)
        A = np.array(A); B = np.array(B); detail[name] = (A, B)
        for lab, v in (("A：当月の報告件数", A), ("B：当月に報告された割合", B)):
            det.append(dict(scenario=name, monitor=lab, detected_24m=float(np.isfinite(v).mean()),
                            within3=float((v <= 3).mean()), within6=float((v <= 6).mean()), within12=float((v <= 12).mean()),
                            median_months=float(np.nanmedian(v)) if np.isfinite(v).any() else float("nan")))
    ddet = pd.DataFrame(det); ddet.to_csv(RES / "detection.csv", index=False)

    # 例のデータ（遅れが変わらない場合の60か月分、発生月×遅れ0〜12か月と最終件数）
    r2 = np.random.default_rng(SEED + 1); tri = simulate(r2, tmax=60); rep, ult = chain_ladder(tri, 60)
    ex = pd.DataFrame(tri[:, :13], columns=[f"lag{d}" for d in range(13)]); ex.insert(0, "occ_month", np.arange(1, 61))
    ex["true_ultimate"] = tri.sum(axis=1); ex["reported_by_month60"] = rep.astype(int); ex["estimated_ultimate"] = np.round(ult, 1)
    ex.to_csv(DATA / "example_triangle_60m.csv", index=False)
    json.dump(dict(seed=SEED, reps=REPS, mu=MU, delay_mean=2.5, delay_p=[float(x) for x in p0[:13]], stable=stable, stable_by_month=age,
                   after_change=dchg.to_dict("records"), detection=ddet.to_dict("records")), open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

    src = "架空のデータ（作成者が乱数で作成、seed 350）。事故は月200件、報告の遅れは平均2.5か月"
    # 図1：直近12か月の例
    fig, ax = plt.subplots(figsize=(8, 4.4))
    k = np.arange(48, 60); x = np.arange(12)
    ax.bar(x, rep[k], 0.6, color=BLUE, label="60か月目の終わりまでに報告された件数")
    ax.bar(x, ult[k] - rep[k], 0.6, bottom=rep[k], color=LIGHT, label="まだ報告されていないと見積もった件数")
    ax.plot(x, ex.true_ultimate.values[k], "o", color=INK, ms=5, label="本当の最終件数")
    ax.set_xticks(x); ax.set_xticklabels([f"{60-i-1}か月前" if 60 - i - 1 else "当月" for i in k], fontsize=8.5)
    ax.set_xlabel("事故が起きた月"); ax.set_ylabel("件数"); ax.legend(fontsize=9, frameon=False, loc="lower left")
    ax.set_title("新しい月ほど、報告済みの件数が少なく、見積もりの幅が広い（1回分の例）")
    save(fig, "a350_recent_months_example.png", src)

    # 図2：遅れが伸びた後の、未報告件数の見積もりのずれ
    fig, ax = plt.subplots(figsize=(8, 4.4))
    for ma, ls in ((3.0, "--"), (4.0, "-")):
        for name, c in (("全期間", BLUE), ("直近12か月", ORANGE)):
            d = dchg[(dchg.mean_after == ma) & (dchg.method == name)]
            ax.plot(d.months_since, d.bias_pct, marker="o", color=c, ls=ls, label=f"{name}の進み方で見積もる（遅れ2.5→{ma:.1f}か月）")
            ax.text(d.months_since.iloc[-1] + 0.4, d.bias_pct.iloc[-1], f"{d.bias_pct.iloc[-1]:.0f}%", fontsize=9, color=c, va="center")
    ax.axhline(0, color=GRAY, lw=0.8); ax.set_xticks([1, 3, 6, 12, 24]); ax.set_xlim(0, 26.5)
    ax.set_xlabel("報告の遅れが伸び始めてからの月数"); ax.set_ylabel("未報告の件数の見積もりのずれ（%、平均）")
    ax.set_ylim(-98, 6); ax.legend(fontsize=8.5, frameon=False, loc="lower left"); ax.set_title("遅れが伸びると、未報告の件数を少なく見積もり続ける")
    save(fig, "a350_error_after_change.png", src)

    # 図3：気づくまでの月数
    fig, ax = plt.subplots(figsize=(8, 4.4)); ms = np.arange(2, 25)
    for name, c in (("遅れの平均 2.5→3.0か月", BLUE), ("遅れの平均 2.5→4.0か月", ORANGE)):
        A, B = detail[name]
        ax.plot(ms, [np.mean(A <= m) * 100 for m in ms], color=c, ls="-", label=f"見張りA（当月の報告件数）：{name}")
        ax.plot(ms, [np.mean(B <= m) * 100 for m in ms], color=c, ls="--", label=f"見張りB（当月に報告された割合）：{name}")
    A, B = detail["変化なし"]
    ax.plot(ms, [np.mean(A <= m) * 100 for m in ms], color=GRAY, ls="-", label="見張りA：変化なし（空振り）")
    ax.plot(ms, [np.mean(B <= m) * 100 for m in ms], color=GRAY, ls="--", label="見張りB：変化なし（空振り）")
    ax.set_xlabel("報告の遅れが伸び始めてからの月数"); ax.set_ylabel("それまでに知らせが出た割合（%）"); ax.set_ylim(0, 103); ax.set_xticks([2, 3, 6, 9, 12, 18, 24])
    ax.legend(fontsize=8, frameon=False, loc="center right"); ax.set_title("遅れが1.5か月伸びれば半年でほぼ気づくが、0.5か月の伸びは2年たっても見逃すことが多い", fontsize=12)
    save(fig, "a350_detection_months.png", src)
    print(pd.DataFrame(stable).round(2).to_string()); print(pd.DataFrame(age).round(2).to_string()); print(dchg.round(1).to_string()); print(ddet.round(3).to_string())

if __name__ == "__main__":
    main()
