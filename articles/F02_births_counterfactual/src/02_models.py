"""2010〜2019年で学習した3つのモデルで、2020〜2025年の「コロナがなかった場合」の出生数を予測し、実際との差を区間つきで出す"""
import numpy as np, pandas as pd
from common import monthly, MODELS, to_counts, RES, EVAL_START, EVAL_END


def run(train_start="2010-01", train_end="2019-12", adjust_days=True, models=MODELS):
    d = monthly()
    tr, ev = d.loc[train_start:train_end], d.loc[EVAL_START:EVAL_END]
    h = len(ev)
    y = np.log(tr.births_per_day if adjust_days else tr.births)
    days = ev.days.values if adjust_days else np.ones(h)
    out, sims_all = {}, {}
    for name, fn in models.items():
        mean, sims, _ = fn(y, h)
        out[name] = to_counts(mean, days)
        sims_all[name] = to_counts(sims, days)            # (h, NSIM) 月の出生数
    return ev, out, sims_all


def summarize(ev, out, sims_all, label=""):
    act = ev.births.values
    mrows, crows = [], []
    years = ev.index.year.values
    ym = ev.index.strftime("%Y-%m").values
    for name in list(out) + ["3モデル統合"]:
        S = np.hstack(list(sims_all.values())) if name == "3モデル統合" else sims_all[name]
        mean = S.mean(1) if name == "3モデル統合" else out[name]
        lo, hi = np.percentile(S, [2.5, 97.5], axis=1)
        lo80, hi80 = np.percentile(S, [10, 90], axis=1)
        for i, dt in enumerate(ev.index):
            mrows.append(dict(model=name, date=dt.strftime("%Y-%m"), actual=act[i], cf=mean[i], lo95=lo[i], hi95=hi[i],
                              lo80=lo80[i], hi80=hi80[i], below95=act[i] < lo[i], above95=act[i] > hi[i]))
        # 累積の差（実際 − 反実仮想）：シミュレーションの経路ごとに足してから区間をとる
        for per, mask in [("2020", years == 2020), ("2021", years == 2021), ("2022", years == 2022), ("2023", years == 2023),
                          ("2024", years == 2024), ("2025", years == 2025), ("2020-2022", years <= 2022),
                          ("2020-2025", years <= 2025),
                          ("2020-12〜2021-02", (ym >= "2020-12") & (ym <= "2021-02")),
                          ("2021-03〜2021-06", (ym >= "2021-03") & (ym <= "2021-06"))]:
            g = act[mask].sum() - S[mask].sum(0)
            crows.append(dict(model=name, period=per, actual=act[mask].sum(), cf=mean[mask].sum(),
                              gap=act[mask].sum() - mean[mask].sum(), gap_lo95=np.percentile(g, 2.5),
                              gap_hi95=np.percentile(g, 97.5), gap_pct=(act[mask].sum() / mean[mask].sum() - 1) * 100,
                              p_below=(g < 0).mean(), setting=label))
    return pd.DataFrame(mrows), pd.DataFrame(crows)


if __name__ == "__main__":
    ev, out, sims = run()
    m, c = summarize(ev, out, sims, "基本（2010-19学習・日数調整あり）")
    m.to_csv(RES / "monthly_counterfactual.csv", index=False)
    c.to_csv(RES / "cumulative_gap.csv", index=False)
    # 月ごとの累積差の推移（図2用）
    rows = []
    act = ev.births.values
    for name, S in list(sims.items()) + [("3モデル統合", np.hstack(list(sims.values())))]:
        cg = np.cumsum(act[:, None] - S, axis=0)
        mean = (out[name] if name in out else S.mean(1))
        for i, dt in enumerate(ev.index):
            rows.append(dict(model=name, date=dt.strftime("%Y-%m"), cum_gap=np.cumsum(act - mean)[i],
                             lo95=np.percentile(cg[i], 2.5), hi95=np.percentile(cg[i], 97.5)))
    pd.DataFrame(rows).to_csv(RES / "cumulative_path.csv", index=False)
    pd.set_option("display.width", 200)
    print(c.round(1).to_string())
    print(m.groupby("model")[["below95", "above95"]].sum())
