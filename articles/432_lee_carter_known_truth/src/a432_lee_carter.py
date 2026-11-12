"""432 死亡率の将来の下がり方を過去から延ばす方法（リー・カーター）は、正解の分かるデータでどれだけ当たるか"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, GREEN, save

SEED = 432
AGES = np.arange(40, 100)            # 40〜99歳
T_ALL, T_FIT, H = 60, 40, 20         # 60年分。前半40年で当てはめ、後半20年を当てる
NSIM, NPATH = 300, 500
SRC = "架空の年齢別死亡率（作成者が置いた数字、seed 432）"
A0 = np.log(0.0012) + 0.095 * (AGES - 40)            # はじめの年の対数死亡率（ゴンペルツの形）
RATE_YOUNG, RATE_OLD = 0.020, 0.007                  # 1年あたりの下がり方：40歳で2.0%、99歳で0.7%
BASE_RATE = RATE_YOUNG + (RATE_OLD - RATE_YOUNG) * (AGES - 40) / 59


SIG_W = 0.8                                           # 年ごとの当たり外れ（下がり方の何年分ぶれるか）


def truth(scn, rng):
    """対数死亡率の正解（年×年齢）。全年齢に共通の年ごとの当たり外れ（ランダムウォーク）を入れる"""
    yrs = np.arange(T_ALL)
    W = np.concatenate([[0.0], rng.standard_normal(T_ALL - 1).cumsum() * SIG_W])
    if scn == "一定":
        return A0[None, :] - np.outer(yrs + W, BASE_RATE)
    if scn == "途中で鈍る":                         # 31年目から下がり方が半分
        cum = np.where(yrs <= 30, yrs, 30 + 0.5 * (yrs - 30))
        return A0[None, :] - np.outer(cum + W, BASE_RATE)
    if scn == "年齢で違ってくる":                   # 若い側の下がり方が鈍り、高齢の側が速まる（60年かけて入れ替わる）
        out = np.zeros((T_ALL, len(AGES))); cur = A0.copy()
        for y in yrs:
            out[y] = cur
            f = y / (T_ALL - 1)
            rate = (1 - f) * BASE_RATE + f * BASE_RATE[::-1]
            cur = cur - rate
        return out - np.outer(W, BASE_RATE)
    raise ValueError


def e65(logm):
    """65歳から100歳までの平均生存年数（100歳で打ち切り）。logm は (..., 年齢)"""
    m = np.exp(logm[..., 25:])                      # 65〜99歳
    q = 1 - np.exp(-m)
    l = np.concatenate([np.ones(m.shape[:-1] + (1,)), np.cumprod(1 - q, axis=-1)], axis=-1)
    return ((l[..., :-1] + l[..., 1:]) / 2).sum(axis=-1)


def fit_lc(logm):
    a = logm.mean(axis=0)
    U, s, Vt = np.linalg.svd(logm - a, full_matrices=False)
    b = Vt[0]; k = U[:, 0] * s[0]
    sc = b.sum(); b = b / sc; k = k * sc             # b の合計を1にそろえる
    return a, b, k


def forecast(a, b, k, rng):
    d = np.diff(k); drift = d.mean(); sig = d.std(ddof=1); n = len(d)
    hs = np.arange(1, H + 1)
    kc = k[-1] + drift * hs                          # 中心の予測
    z = rng.standard_normal((NPATH, H)).cumsum(axis=1) * sig
    dd = rng.standard_normal((NPATH, 1)) * sig / np.sqrt(n)        # 下がり方（ドリフト）の見積もりの誤差
    kp = k[-1] + (drift + dd) * hs + z
    return kc, kp


def run(scn, expo, window, rng):
    rec = []
    for _ in range(NSIM):
        tr = truth(scn, rng); mt = np.exp(tr)
        deaths = rng.poisson(mt[:T_FIT] * expo)
        obs = np.log((deaths + 0.5) / expo)          # 0件でも対数が取れるように0.5を足す
        a, b, k = fit_lc(obs[T_FIT - window:])
        kc, kp = forecast(a, b, k, rng)
        cen = a + b * kc[-1]                         # 20年先の対数死亡率（中心）
        paths = a[None, :] + kp[:, -1:] * b[None, :]
        err_m = np.exp(cen - tr[-1]) - 1
        ec, et = e65(cen), e65(tr[-1])
        ep = e65(paths)
        lo, hi = np.quantile(ep, [0.025, 0.975])
        l70, h70 = np.quantile(paths[:, 30], [0.025, 0.975])
        rec.append(dict(mape=np.abs(err_m).mean() * 100, bias_m=err_m.mean() * 100,
                        err_m_45=err_m[5] * 100, err_m_70=err_m[30] * 100, err_m_90=err_m[50] * 100,
                        e65_err=ec - et, e65_cover=float(lo <= et <= hi), e65_width=hi - lo,
                        m70_cover=float(l70 <= tr[-1][30] <= h70)))
    R = pd.DataFrame(rec)
    return dict(シナリオ=scn, 人口_各年齢=expo, 当てはめの年数=window,
                死亡率の誤差_絶対値の平均_pct=R.mape.mean(), 死亡率の偏り_pct=R.bias_m.mean(),
                偏り45歳_pct=R.err_m_45.mean(), 偏り70歳_pct=R.err_m_70.mean(), 偏り90歳_pct=R.err_m_90.mean(),
                e65の偏り_年=R.e65_err.mean(), e65の誤差RMSE_年=float(np.sqrt((R.e65_err ** 2).mean())),
                e65の95pct区間が正解を含む_pct=R.e65_cover.mean() * 100, e65の区間の幅_年=R.e65_width.mean(),
                m70の95pct区間が正解を含む_pct=R.m70_cover.mean() * 100), R


def main():
    rng = np.random.default_rng(SEED)
    scns = ["一定", "途中で鈍る", "年齢で違ってくる"]
    rows, keep = [], {}
    for scn in scns:
        for expo in (200_000, 20_000):
            for window in (40, 20):
                r, R = run(scn, expo, window, rng)
                rows.append(r); keep[(scn, expo, window)] = R
    T = pd.DataFrame(rows); T.round(3).to_csv(RES / "forecast_errors.csv", index=False)
    # 正解の表（確認用）
    tt = []
    for scn in scns:
        tr = np.mean([truth(scn, np.random.default_rng(i)) for i in range(400)], axis=0)   # 当たり外れをならした平均の道
        for y in (0, 20, 39, 59):
            tt.append(dict(シナリオ=scn, 年=y + 1, m45=np.exp(tr[y, 5]), m70=np.exp(tr[y, 30]), m90=np.exp(tr[y, 50]), e65=float(e65(tr[y]))))
    pd.DataFrame(tt).round(5).to_csv(DATA / "truth_summary.csv", index=False)

    # 図のための1回分（人口20万、40年で当てはめ）
    rng2 = np.random.default_rng(SEED + 1)
    ex = {}
    for scn in scns:
        tr = truth(scn, rng2); deaths = rng2.poisson(np.exp(tr[:T_FIT]) * 200_000); obs = np.log((deaths + 0.5) / 200_000)
        a, b, k = fit_lc(obs); kc, kp = forecast(a, b, k, rng2)
        cen = a[None, :] + np.outer(kc, b)
        pe = e65(a[None, None, :] + kp[:, :, None] * b[None, None, :])
        ex[scn] = dict(truth_e=e65(tr), cen_e=e65(cen), lo=np.quantile(pe, 0.025, axis=0), hi=np.quantile(pe, 0.975, axis=0),
                       err_age=np.exp(cen[-1] - tr[-1]) - 1, b=b)
    pd.DataFrame({"年": np.arange(1, T_ALL + 1), **{f"正解_{s}": ex[s]["truth_e"] for s in scns}}).round(4).to_csv(DATA / "truth_e65_by_year.csv", index=False)

    main_ = {"設定": dict(年齢="40〜99歳", 当てはめ="1〜40年目", 予測="41〜60年目", くり返し=NSIM, 道の数=NPATH, 年ごとの当たり外れ=SIG_W),
             "20年先（人口20万・40年で当てはめ）": {r["シナリオ"]: {k: round(float(v), 3) for k, v in r.items() if k not in ("シナリオ",)} for r in rows if r["人口_各年齢"] == 200_000 and r["当てはめの年数"] == 40}}
    json.dump(main_, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

    cols = dict(zip(scns, (BLUE, ORANGE, GREEN)))
    fig, ax = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
    yrs = np.arange(1, T_ALL + 1)
    for a_, scn in zip(ax, scns):
        e = ex[scn]
        a_.plot(yrs, e["truth_e"], color=INK, lw=2, label="正解")
        a_.plot(yrs[T_FIT:], e["cen_e"], color=cols[scn], lw=2, ls="--", label="予測（中心）")
        a_.fill_between(yrs[T_FIT:], e["lo"], e["hi"], color=cols[scn], alpha=.25, label="予測の95%の幅")
        a_.axvline(T_FIT + .5, color=GRAY, lw=.8, ls=":"); a_.set_title(f"下がり方が「{scn}」"); a_.set_xlabel("年")
    ax[0].set_ylabel("65歳からの平均生存年数（100歳まで）"); ax[0].legend(frameon=False, fontsize=9, loc="upper left")
    fig.suptitle("1〜40年目で当てはめ、41〜60年目を予測した例（各年齢20万人）", y=1.03)
    save(fig, "a432_e65_forecast_examples.png", SRC, y=-0.03)

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
    pos = 0; ticks = []; labs = []
    for scn in scns:
        for window, alpha in ((40, 1.0), (20, .45)):
            R = keep[(scn, 200_000, window)]
            bp = ax[0].boxplot(R.e65_err, positions=[pos], widths=.6, patch_artist=True, showfliers=False)
            for b_ in bp["boxes"]: b_.set(facecolor=cols[scn], alpha=alpha)
            for m_ in bp["medians"]: m_.set(color=INK)
            ticks.append(pos); labs.append(scn.replace("年齢で違ってくる", "年齢で\n違ってくる") + f"\n{window}年"); pos += 1
        pos += .5
    ax[0].axhline(0, color=GRAY, lw=.8); ax[0].set_xticks(ticks); ax[0].set_xticklabels(labs, fontsize=8)
    ax[0].set_ylabel("予測 − 正解（年）"); ax[0].set_title("20年先の平均生存年数の誤差（当てはめに使う年数：40年／直近20年）")
    for scn in scns:
        ax[1].plot(AGES, ex[scn]["err_age"] * 100, color=cols[scn], lw=2, label=scn)
    ax[1].axhline(0, color=GRAY, lw=.8); ax[1].set_xlabel("年齢"); ax[1].set_ylabel("20年先の死亡率の誤差（%）"); ax[1].set_title("年齢ごとの外れ方（1回分の例）"); ax[1].legend(frameon=False)
    save(fig, "a432_error_by_scenario_and_age.png", SRC, y=-0.03)

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
    w = .2; xs = np.arange(3)
    combos = [(200_000, 40, BLUE, "各年齢20万人・40年"), (200_000, 20, "#a9c9ef", "各年齢20万人・直近20年"), (20_000, 40, ORANGE, "各年齢2万人・40年"), (20_000, 20, "#f5b89e", "各年齢2万人・直近20年")]
    for i, (expo, window, c, lab) in enumerate(combos):
        v = [float(T[(T.シナリオ == s) & (T.人口_各年齢 == expo) & (T.当てはめの年数 == window)].iloc[0]["e65の95pct区間が正解を含む_pct"]) for s in scns]
        ax[0].bar(xs + (i - 1.5) * w, v, w, color=c, label=lab)
        v2 = [float(T[(T.シナリオ == s) & (T.人口_各年齢 == expo) & (T.当てはめの年数 == window)].iloc[0]["死亡率の誤差_絶対値の平均_pct"]) for s in scns]
        ax[1].bar(xs + (i - 1.5) * w, v2, w, color=c, label=lab)
    ax[0].axhline(95, color=INK, lw=.8, ls=":"); ax[0].set_xticks(xs); ax[0].set_xticklabels(scns); ax[0].set_ylabel("正解を含んだ割合（%）"); ax[0].set_title("95%の幅が、20年先の正解を含んだ割合"); ax[0].set_ylim(0, 105)
    fig.legend(*ax[0].get_legend_handles_labels(), frameon=False, fontsize=9, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.06))
    ax[1].set_xticks(xs); ax[1].set_xticklabels(scns); ax[1].set_ylabel("誤差の絶対値の平均（%）"); ax[1].set_title("20年先の年齢別死亡率の誤差")
    save(fig, "a432_coverage_and_error.png", SRC, y=-0.07)
    print(T.round(2).to_string()); print(pd.DataFrame(tt).round(4).to_string())


if __name__ == "__main__":
    main()
