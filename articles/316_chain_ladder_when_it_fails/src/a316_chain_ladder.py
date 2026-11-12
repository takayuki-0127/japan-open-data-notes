"""316 チェインラダー法は、どんなときに外れるか（架空の支払データ、最終の支払額が分かる）
事故年度10年×経過10年の三角形を、5つの場面で1,000組ずつ作り、支払備金の見積もりの誤差を測る。"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, GREEN, LIGHT, save

SEED, NSIM, N, JF = 316, 1000, 10, 30          # 事故年度10、経過は最長30年まで作る（遅くなる場面の尻尾のため）
SOURCE = "架空のデータ（作成者が乱数で作成、seed 316）"
def G(t):
    """支払いの進み方のもとの曲線（ワイブル型）"""
    return 1 - np.exp(-(np.asarray(t, float) / 3.2) ** 1.1)


BASE_CUM = G(np.arange(1, N + 1)) / G(N)        # 経過1〜10年目までに払う割合（10年目で払い終わる）
CHANGE = 7                                      # 暦年7（直近3本の対角線）から先で場面が変わる
CV = 0.12                                       # 1マスの支払額のばらつき（変動係数）

SCEN = {  # 名前: (変わる前の速さ, 変わった後の速さ, 変わる前のインフレ, 変わった後のインフレ)
    "A 進み方が一定": (1.0, 1.0, 0.00, 0.00),
    "B 支払いが遅くなる": (1.0, 0.8, 0.00, 0.00),
    "B' 支払いが速くなる": (1.0, 1.25, 0.00, 0.00),
    "C1 インフレが一定（年3%）": (1.0, 1.0, 0.03, 0.03),
    "C2 インフレが強まる（年1%→6%）": (1.0, 1.0, 0.01, 0.06),
}


def F(t):
    """進んだ時間 t（年）までに払う割合。10年ぶん進んだら払い終わる"""
    return np.minimum(G(t) / G(N), 1.0)


def simulate(scen, rng, nsim=NSIM):
    v0, v1, g0, g1 = SCEN[scen]
    ncal = N + JF
    speed = np.where(np.arange(ncal) >= CHANGE, v1, v0)
    infl = np.cumprod(np.r_[1.0, 1 + np.where(np.arange(1, ncal) >= CHANGE, g1, g0)])
    prem = 1000 * 1.03 ** np.arange(N)                              # 保険料（百万円）、年3%で増える
    lr = rng.lognormal(np.log(0.65) - 0.5 * np.log(1 + 0.08 ** 2), np.sqrt(np.log(1 + 0.08 ** 2)), (nsim, N))
    U = prem * lr                                                   # 物価が変わらないときの最終の支払額
    share = np.zeros((N, JF)); idx = np.zeros((N, JF))
    for i in range(N):
        tau = np.cumsum(speed[i:i + JF])                            # その事故年度の「進んだ時間」
        share[i] = np.diff(np.r_[0.0, F(tau)])
        idx[i] = infl[i:i + JF]
    noise = rng.gamma(1 / CV ** 2, CV ** 2, (nsim, N, JF))
    return U[:, :, None] * share * idx * noise                      # X[s, 事故年度, 経過]


def chain_ladder(X, last=None):
    """支払額の三角形（経過10年まで）から最終の支払額を見積もる。last=3 なら直近3年分の比だけを使う"""
    C = np.cumsum(X[:, :, :N], axis=2)
    ult = np.empty(C.shape[:2]); f = np.ones((C.shape[0], N - 1))
    for j in range(N - 1):
        rows = np.arange(N - 1 - j)                                 # 経過 j+1 まで見えている事故年度
        if last: rows = rows[-last:]
        f[:, j] = C[:, rows, j + 1].sum(1) / C[:, rows, j].sum(1)
    for i in range(N):
        ult[:, i] = C[:, i, N - 1 - i] * np.prod(f[:, N - 1 - i:], axis=1)
    return ult, f


def truth(X):
    paid = np.stack([X[:, i, :N - i].sum(1) for i in range(N)], axis=1)
    return X.sum(2), paid                                           # 最終の支払額（正解）、いままでに払った額


def main():
    rng = np.random.default_rng(SEED)
    out = {"設定": {"事故年度": N, "回数": NSIM, "ばらつき（変動係数）": CV, "場面が変わる暦年": "直近3年から先",
                   "基本の進み方（累計）": [round(float(x), 4) for x in BASE_CUM]}, "場面": {}}
    ex_rows, f_rows = [], []
    for scen in SCEN:
        X = simulate(scen, rng)
        ult_true, paid = truth(X)
        res_true = (ult_true - paid).sum(1)
        tail = X[:, :, N:].sum((1, 2)) / res_true                   # 三角形の外（経過11年目以降）に残る分
        d = {"正解の支払備金（平均、百万円）": round(float(res_true.mean()), 1),
             "三角形の外に残る割合（平均）": round(float(tail.mean()), 4)}
        for name, last in [("全年度の比", None), ("直近3年の比", 3)]:
            ult, f = chain_ladder(X, last)
            res = (ult - paid).sum(1)
            err = res / res_true - 1
            d[name] = {"誤差の平均（%）": round(100 * float(err.mean()), 1),
                       "誤差の10%点（%）": round(100 * float(np.quantile(err, .1)), 1),
                       "誤差の中央値（%）": round(100 * float(np.median(err)), 1),
                       "誤差の90%点（%）": round(100 * float(np.quantile(err, .9)), 1),
                       "低く見積もった割合（%）": round(100 * float((err < 0).mean()), 1),
                       "誤差の大きさの平均（%）": round(100 * float(np.abs(err).mean()), 1)}
            if last is None:
                ue = ult / ult_true - 1                             # 事故年度ごとの最終の支払額の誤差
                re_amt = (ult - ult_true)
                d["事故年度ごと"] = [{"事故年度": i + 1, "払い終わった割合（正解の平均）": round(float((paid[:, i] / ult_true[:, i]).mean()), 3),
                                    "最終額の誤差の平均（%）": round(100 * float(ue[:, i].mean()), 2),
                                    "最終額の誤差の大きさ（RMSE、%）": round(100 * float(np.sqrt((ue[:, i] ** 2).mean())), 2),
                                    "備金の誤差の大きさ（RMSE、百万円）": round(float(np.sqrt((re_amt[:, i] ** 2).mean())), 1)} for i in range(N)]
                d["誤差の二乗和に占める直近3事故年度の割合（%）"] = round(100 * float((re_amt[:, -3:] ** 2).mean(0).sum() / (re_amt ** 2).mean(0).sum()), 1)
                # 経過1→2年目の比を、事故年度ごとに（気づく手がかり）
                C = np.cumsum(X[:, :, :N], axis=2)
                for j in (0, 1):
                    r = C[:, :N - 1 - j, j + 1] / C[:, :N - 1 - j, j]
                    for i in range(N - 1 - j):
                        f_rows.append({"場面": scen, "経過": f"{j + 1}→{j + 2}年目", "事故年度": i + 1, "比の平均": round(float(r[:, i].mean()), 4)})
                np.save(RES / f"_err_{list(SCEN).index(scen)}.npy", np.stack([err, (chain_ladder(X, 3)[0] - paid).sum(1) / res_true - 1]))
        out["場面"][scen] = d
        C0 = np.cumsum(X[0, :, :N], axis=1)
        for i in range(N):
            for j in range(N - i):
                ex_rows.append({"場面": scen, "事故年度": i + 1, "経過年": j + 1, "累計支払額": round(float(C0[i, j]), 1)})
        ex_rows.append({"場面": scen, "事故年度": "正解", "経過年": "最終", "累計支払額": round(float(X[0].sum()), 1)})
    pd.DataFrame(ex_rows).to_csv(DATA / "example_triangles.csv", index=False)
    pd.DataFrame(f_rows).to_csv(RES / "link_ratio_by_accident_year.csv", index=False)
    json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    figs(out, pd.DataFrame(f_rows))
    for k in range(len(SCEN)): (RES / f"_err_{k}.npy").unlink()
    for s, d in out["場面"].items(): print(s, d["全年度の比"], d["直近3年の比"]["誤差の平均（%）"], d["三角形の外に残る割合（平均）"], d["誤差の二乗和に占める直近3事故年度の割合（%）"])


def figs(out, fdf):
    names = list(SCEN)
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    for k, s in enumerate(names):
        e = np.load(RES / f"_err_{k}.npy") * 100
        for m, (c, lab) in enumerate([(BLUE, "全年度の比で見積もる"), (ORANGE, "直近3年の比で見積もる")]):
            y = len(names) - 1 - k + (0.17 if m == 0 else -0.17)
            q = np.quantile(e[m], [.1, .5, .9])
            ax.plot([q[0], q[2]], [y, y], color=c, lw=5, alpha=.45, solid_capstyle="round")
            ax.plot(e[m].mean(), y, "o", color=c, ms=7, label=lab if k == 0 else None)
            ax.text(q[2] + 1.2, y, f"{e[m].mean():+.0f}%", va="center", fontsize=9.5, color=c)
    ax.axvline(0, color=GRAY, lw=1)
    ax.set_yticks(range(len(names))); ax.set_yticklabels(names[::-1])
    ax.set_xlabel("支払備金の見積もりの誤差（%、マイナスは少なすぎ）")
    ax.set_title("場面ごとの見積もりの誤差（点は平均、帯は1,000組の10〜90%）")
    ax.legend(frameon=False, loc="lower right", fontsize=9.5)
    save(fig, "a316_scenarios.png", SOURCE)

    d = out["場面"]["A 進み方が一定"]["事故年度ごと"]
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
    x = [r["事故年度"] for r in d]
    axs[0].bar(x, [r["最終額の誤差の大きさ（RMSE、%）"] for r in d], color=BLUE)
    for r in d: axs[0].text(r["事故年度"], r["最終額の誤差の大きさ（RMSE、%）"] + .3, f'{r["最終額の誤差の大きさ（RMSE、%）"]:.1f}', ha="center", fontsize=9)
    axs[0].set_title("最終の支払額の誤差の大きさ（%）"); axs[0].set_xlabel("事故年度（10がいちばん新しい）"); axs[0].set_xticks(x)
    axs[1].bar(x, [r["備金の誤差の大きさ（RMSE、百万円）"] for r in d], color=ORANGE)
    axs[1].set_title("備金の誤差の大きさ（百万円）"); axs[1].set_xlabel("事故年度（10がいちばん新しい）"); axs[1].set_xticks(x)
    fig.suptitle("進み方が一定でも、新しい事故年度ほど外れる（場面A、全年度の比）", y=1.02, fontsize=13)
    save(fig, "a316_by_accident_year.png", SOURCE)

    fig, axs = plt.subplots(1, 2, figsize=(10, 4.2), sharey=False)
    for ax, lab in zip(axs, ["1→2年目", "2→3年目"]):
        for s, c in [("A 進み方が一定", GRAY), ("B 支払いが遅くなる", BLUE), ("C2 インフレが強まる（年1%→6%）", ORANGE)]:
            g = fdf[(fdf["場面"] == s) & (fdf["経過"] == lab)]
            ax.plot(g["事故年度"], g["比の平均"], "-o", color=c, ms=4, label=s)
        ax.set_title(f"経過{lab}の比（累計の伸び）"); ax.set_xlabel("事故年度"); ax.set_xticks(range(1, 10))
    axs[0].legend(frameon=False, fontsize=9)
    fig.suptitle("事故年度ごとに比を並べると、変わり目が見える（1,000組の平均）", y=1.02, fontsize=13)
    save(fig, "a316_link_ratios.png", SOURCE)


if __name__ == "__main__":
    main()
