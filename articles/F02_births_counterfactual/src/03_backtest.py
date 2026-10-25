"""モデルの当たり方（2015〜2019年のバックテスト）と、設定を変えたときの頑健性"""
import importlib
import numpy as np, pandas as pd
from common import monthly, MODELS, to_counts, RES

m02 = importlib.import_module("02_models")
d = monthly()


def backtest(train_start, train_end, test_start, test_end):
    tr, te = d.loc[train_start:train_end], d.loc[test_start:test_end]
    h = len(te); y = np.log(tr.births_per_day); act = te.births.values
    rows, allS = [], []
    for name, fn in MODELS.items():
        mean, sims, _ = fn(y, h)
        f, S = to_counts(mean, te.days.values), to_counts(sims, te.days.values)
        allS.append(S)
        rows.append((name, f, S))
    S = np.hstack(allS); rows.append(("3モデル統合", S.mean(1), S))
    out = []
    for name, f, S in rows:
        lo, hi = np.percentile(S, [2.5, 97.5], axis=1)
        out.append(dict(model=name, train=f"{train_start[:4]}-{train_end[:4]}", test=f"{test_start[:4]}-{test_end[:4]}",
                        mape=np.mean(np.abs(f / act - 1)) * 100, total_err_pct=(f.sum() / act.sum() - 1) * 100,
                        coverage95=np.mean((act >= lo) & (act <= hi)) * 100,
                        last_year_err_pct=(f[-12:].sum() / act[-12:].sum() - 1) * 100))
    return out


if __name__ == "__main__":
    bt = backtest("2010-01", "2014-12", "2015-01", "2019-12")
    for y in range(2015, 2020):                              # 1年先だけを当てる（学習期間を1年ずつのばす）
        bt += backtest("2010-01", f"{y-1}-12", f"{y}-01", f"{y}-12")
    bt = pd.DataFrame(bt); bt.to_csv(RES / "backtest.csv", index=False)
    print(bt.round(2).to_string())

    # 頑健性：学習期間・日数調整
    rob, winrows = [], []
    for label, kw in [("基本：2010-19学習・日数調整あり", {}),
                      ("学習期間 2005-19", dict(train_start="2005-01")),
                      ("学習期間 2012-19", dict(train_start="2012-01")),
                      ("日数調整なし", dict(adjust_days=False))]:
        ev, out, sims = m02.run(**kw)
        mon, cum = m02.summarize(ev, out, sims, label)
        w = cum[cum.period == "2020-12〜2021-02"][["setting", "model", "actual", "cf", "gap", "gap_lo95", "gap_hi95"]]
        winrows.append(w)
        for model in cum.model.unique():
            mm = mon[mon.model == model].set_index("date")
            cc = cum[cum.model == model].set_index("period")
            win = mm.loc["2020-12":"2021-02"]
            rob.append(dict(setting=label, model=model,
                            jan2021_gap_pct=(mm.loc["2021-01", "actual"] / mm.loc["2021-01", "cf"] - 1) * 100,
                            jan2021_below95=bool(mm.loc["2021-01", "below95"]),
                            dec20_feb21_gap=(win.actual - win.cf).sum(),
                            months_below95=int(mm.below95.sum()), months_above95=int(mm.above95.sum()),
                            gap_2020_2022=cc.loc["2020-2022", "gap"], gap_2020_2022_lo=cc.loc["2020-2022", "gap_lo95"],
                            gap_2020_2022_hi=cc.loc["2020-2022", "gap_hi95"],
                            gap_2020_2025=cc.loc["2020-2025", "gap"], gap_2020_2025_lo=cc.loc["2020-2025", "gap_lo95"],
                            gap_2020_2025_hi=cc.loc["2020-2025", "gap_hi95"]))
    rob = pd.DataFrame(rob); rob.to_csv(RES / "robustness.csv", index=False)
    pd.concat(winrows).to_csv(RES / "robustness_window.csv", index=False)
    pd.set_option("display.width", 250); print(rob.round(1).to_string())
