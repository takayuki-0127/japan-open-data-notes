"""434 残った店だけで平均を取ると、成績はどれだけ良く見えるのか（架空の店1,000店の10年）"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, GREEN, save

SEED = 434
NS, NY, NSIM = 1000, 10, 200
SD_STORE, SD_YEAR = 0.02, 0.08        # 店ごとの実力の差（年2%）、年ごとの当たり外れ（8%）
SRC = "架空の店の売上（作成者が乱数で作成、seed 434）。本当の平均の伸びは年0%"


def simulate(rng, base=0.05, slope=6.0, ns=NS, ny=NY):
    """売上の対数 s（年×店）と、開いているか alive を返す。閉まる確率は、直近の成績が悪いほど高い"""
    mu = rng.normal(0, SD_STORE, ns)
    g = mu[None, :] + rng.normal(0, SD_YEAR, (ny, ns))          # 年ごとの伸び（対数）
    s = np.vstack([np.zeros(ns), g.cumsum(axis=0)])              # 0年目を100として対数で持つ
    alive = np.ones((ny + 1, ns), bool)
    a0 = np.log(base / (1 - base)) if base > 0 else -np.inf
    for y in range(1, ny + 1):
        perf = s[y] - s[max(y - 2, 0)]                           # 直近2年の伸び
        pclose = 1 / (1 + np.exp(-(a0 - slope * perf))) if base > 0 else np.zeros(ns)
        close = rng.random(ns) < pclose
        alive[y] = alive[y - 1] & ~close
    return s, g, alive, mu


def summarize(s, g, alive):
    ny = g.shape[0]
    surv = alive[-1]
    out = dict(残った割合=surv.mean())
    # (a) 残った店だけの、10年の年平均の伸び
    out["残った店だけ"] = (np.exp(s[-1, surv].mean() / ny) - 1) * 100 if surv.any() else np.nan
    # (b) 全部の店（閉まった店も、閉まらなかったとしたら）の本当の値
    out["全部の店（閉まらなかったとして）"] = (np.exp(s[-1].mean() / ny) - 1) * 100
    # (c) 開いていた年だけを全部の店から集めた、年ごとの伸びの平均（閉まる直前の年まで入る）
    obs = alive[1:]                                              # y年の終わりに開いている店の y年の伸び
    out["開いていた年を全部"] = (np.exp(g[obs].mean()) - 1) * 100
    # (d) 既存店の比べ（その年もその前の年も開いていた店の、前年比の平均を年ごとに取り、平均）
    out["既存店の前年比"] = np.mean([(np.exp(g[y - 1][alive[y]].mean()) - 1) * 100 for y in range(1, ny + 1) if alive[y].any()])
    # (e) 残った店の実力（本当の伸び）
    return out, surv


def main():
    rng = np.random.default_rng(SEED)
    rows = []
    grid = [(b, sl) for b in (0.0, 0.02, 0.05, 0.10, 0.15) for sl in (0.0, 3.0, 6.0, 12.0)]
    for base, slope in grid:
        acc = []
        for _ in range(NSIM if base > 0 else 40):
            s, g, alive, mu = simulate(rng, base, slope)
            o, surv = summarize(s, g, alive)
            o["残った店の実力"] = (np.exp(mu[surv].mean()) - 1) * 100 if surv.any() else np.nan
            acc.append(o)
        m = pd.DataFrame(acc).mean()
        rows.append(dict(閉まる割合_年=base, 成績との結びつき=slope, **m.to_dict()))
    T = pd.DataFrame(rows); T.round(4).to_csv(RES / "bias_by_closure.csv", index=False)

    # 基本の場面（年5%・結びつき6）：年ごとの平均売上（0年目=100）
    idx = []
    for _ in range(NSIM):
        s, g, alive, mu = simulate(rng)
        surv = alive[-1]
        idx.append(dict(all=np.exp(s.mean(axis=1)) * 100, surv=np.exp(s[:, surv].mean(axis=1)) * 100,      # 幾何平均（対数の平均を戻す）
                        open_=np.array([np.exp(s[y, alive[y]].mean()) * 100 for y in range(NY + 1)]), n=alive.mean(axis=1)))
    I = {k: np.mean([d[k] for d in idx], axis=0) for k in ("all", "surv", "open_", "n")}
    pd.DataFrame({"年": np.arange(NY + 1), "全部の店_閉まらなかったとして": I["all"], "最後まで残った店だけ": I["surv"],
                  "その年に開いている店": I["open_"], "開いている店の割合": I["n"]}).round(3).to_csv(RES / "index_by_year.csv", index=False)

    # 開いた年ごと（どの年にも500店ずつ開いたとする。10年目の時点で残っている店の、開いてからの年平均の伸び）
    coh = []
    for _ in range(NSIM):
        for age in range(1, NY + 1):                             # 開いてから age 年
            s, g, alive, mu = simulate(rng, ns=500, ny=age)
            sv = alive[-1]
            coh.append(dict(開いてからの年数=age, 残った割合=sv.mean(), 年平均の伸び_残った店=(np.exp(s[-1, sv].mean() / age) - 1) * 100 if sv.any() else np.nan,
                            直近1年の伸び_残った店=(np.exp(g[-1, sv].mean()) - 1) * 100 if sv.any() else np.nan,
                            実力_残った店=(np.exp(mu[sv].mean()) - 1) * 100 if sv.any() else np.nan))
    C = pd.DataFrame(coh).groupby("開いてからの年数").mean().reset_index(); C.round(4).to_csv(RES / "by_store_age.csv", index=False)

    # 当たり外れの大きさを変える
    vol = []
    for sd in (0.04, 0.08, 0.16):
        global SD_YEAR
        keep = SD_YEAR; SD_YEAR = sd
        acc = [summarize(*simulate(rng)[:3])[0] for _ in range(NSIM)]
        SD_YEAR = keep
        m = pd.DataFrame(acc).mean(); vol.append(dict(年ごとの当たり外れ=sd, **m.to_dict()))
    V = pd.DataFrame(vol); V.round(4).to_csv(RES / "by_volatility.csv", index=False)

    b = T[(T.閉まる割合_年 == 0.05) & (T.成績との結びつき == 6.0)].iloc[0]
    main_ = {"基本の場面（年5%・結びつき6）": {k: round(float(v), 3) for k, v in b.items()},
             "10年目の売上の幾何平均（0年目=100）": {"全部の店": round(float(I["all"][-1]), 1), "最後まで残った店だけ": round(float(I["surv"][-1]), 1)}}
    json.dump(main_, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    s, g, alive, mu = simulate(np.random.default_rng(SEED + 1))
    pd.DataFrame({"店": np.arange(NS), "実力_年の伸び": mu, "10年目の売上_0年目を100": np.exp(s[-1]) * 100, "閉まった年": np.where(alive[-1], 0, (~alive).argmax(axis=0))}).round(4).to_csv(DATA / "example_stores.csv", index=False)

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
    yrs = np.arange(NY + 1)
    ax[0].plot(yrs, I["all"], color=INK, lw=2.2, label="全部の店（閉まらなかったとして）")
    ax[0].plot(yrs, I["open_"], color=BLUE, lw=2, ls="--", label="その年に開いている店")
    ax[0].plot(yrs, I["surv"], color=ORANGE, lw=2.2, label="最後まで残った店だけ")
    ax[0].axhline(100, color=GRAY, lw=.6); ax[0].set_xlabel("年"); ax[0].set_ylabel("1店あたりの売上（幾何平均、0年目=100）"); ax[0].set_title("本当の伸びは0でも、残った店は伸びて見える"); ax[0].legend(frameon=False, fontsize=9)
    ex_s = np.exp(s[-1]) * 100
    bins = np.linspace(20, 260, 49)
    ax[1].hist(ex_s[~alive[-1]], bins=bins, color=GRAY, alpha=.8, label="途中で閉まった店（開いていたとしたら）")
    ax[1].hist(ex_s[alive[-1]], bins=bins, color=ORANGE, alpha=.7, label="最後まで残った店")
    ax[1].set_xlabel("10年目の売上（0年目=100）"); ax[1].set_ylabel("店の数"); ax[1].set_title("1回分の例：1,000店の10年目"); ax[1].legend(frameon=False, fontsize=9)
    save(fig, "a434_index_survivors_vs_all.png", SRC, y=-0.03)

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
    for sl, c in ((0.0, GRAY), (3.0, GREEN), (6.0, BLUE), (12.0, ORANGE)):
        d = T[T.成績との結びつき == sl]
        ax[0].plot(d.閉まる割合_年 * 100, d["残った店だけ"], "o-", color=c, label=f"成績との結びつき {sl:.0f}")
    ax[0].axhline(0, color=INK, lw=.8, ls=":"); ax[0].set_xlabel("1年に閉まる店の割合（成績がふつうの店、%）"); ax[0].set_ylabel("残った店だけの年平均の伸び（%）"); ax[0].set_title("閉まる店が多く、成績と結びつくほど上にずれる"); ax[0].legend(frameon=False, fontsize=9)
    d = T[T.成績との結びつき == 6.0]; w = .2; xs = np.arange(len(d))
    for i, (col, c) in enumerate((("残った店だけ", ORANGE), ("開いていた年を全部", BLUE), ("既存店の前年比", GREEN), ("残った店の実力", GRAY))):
        ax[1].bar(xs + (i - 1.5) * w, d[col], w, color=c, label=col)
    ax[1].set_xticks(xs); ax[1].set_xticklabels([f"{v*100:.0f}%" for v in d.閉まる割合_年]); ax[1].axhline(0, color=INK, lw=.8, ls=":")
    ax[1].set_xlabel("1年に閉まる店の割合（結びつき6）"); ax[1].set_ylabel("年平均の伸び（%）"); ax[1].set_title("数え方ごとの上振れ（本当は0%）"); ax[1].legend(frameon=False, fontsize=9)
    save(fig, "a434_bias_by_closure_rate.png", SRC, y=-0.03)

    fig, ax = plt.subplots(1, 2, figsize=(12, 4.3))
    ax[0].plot(C.開いてからの年数, C.年平均の伸び_残った店, "o-", color=ORANGE, lw=2, label="開いてからの年平均の伸び")
    ax[0].plot(C.開いてからの年数, C.直近1年の伸び_残った店, "s--", color=BLUE, lw=1.8, label="直近1年の伸び")
    ax[0].plot(C.開いてからの年数, C.実力_残った店, "^:", color=GRAY, lw=1.8, label="本当の実力")
    ax[0].axhline(0, color=INK, lw=.8, ls=":"); ax[0].set_xlabel("開いてからの年数（いま残っている店）"); ax[0].set_ylabel("伸び（%）"); ax[0].set_title("開いた年ごとに分けると"); ax[0].legend(frameon=False, fontsize=9)
    ax[1].bar(C.開いてからの年数, C.残った割合 * 100, color=GRAY)
    ax[1].set_xlabel("開いてからの年数"); ax[1].set_ylabel("残っている店の割合（%）"); ax[1].set_title("古い年に開いた店ほど、残った店は少ない")
    save(fig, "a434_by_store_age.png", SRC, y=-0.03)
    print(json.dumps(main_, ensure_ascii=False, indent=1)); print(T.round(2).to_string()); print(C.round(2).to_string()); print(V.round(2).to_string())
    print(pd.read_csv(RES / "index_by_year.csv").to_string())


if __name__ == "__main__":
    main()
