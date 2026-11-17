"""03b_requestion.py : 問い直し（結果を見てから足した）。
ボーナスの月に積んだ預貯金は、ほかの月に取り崩されているのか。月ごとの預貯金純増・黒字・消費支出の形を見る（オフライン）。"""
import json
import numpy as np
import pandas as pd
from common import RES, BONUS, load_wide

COLS = ["可処分所得", "消費支出", "黒字", "預貯金純増"]


def main():
    w, _ = load_wide()
    w = w.loc[2000:2025, COLS].copy()
    prof = []
    for (a, b) in [(2000, 2009), (2016, 2025), (2000, 2025)]:
        g = w.loc[a:b].groupby(level="month").mean()
        for m, r in g.iterrows():
            prof.append({"period": f"{a}-{b}", "month": int(m), **{c: round(r[c], 0) for c in COLS}})
    prof = pd.DataFrame(prof)
    prof.to_csv(RES / "monthly_profile.csv", index=False)
    yr = []
    for y in range(2000, 2026):
        g = w.loc[y]
        bon = g.loc[list(BONUS), "預貯金純増"].sum()
        non = g.loc[[m for m in range(1, 13) if m not in BONUS], "預貯金純増"].sum()
        neg_months = int((g["預貯金純増"] < 0).sum())
        yr.append({"year": y, "deposit_bonus_months": bon, "deposit_other_months": non, "deposit_year": bon + non,
                   "drawdown_ratio": round(-non / bon, 4), "n_negative_months": neg_months,
                   "surplus_other_months": g.loc[[m for m in range(1, 13) if m not in BONUS], "黒字"].sum()})
    yr = pd.DataFrame(yr)
    yr.to_csv(RES / "deposit_drawdown_by_year.csv", index=False)
    p = prof[prof.period == "2016-2025"].set_index("month")
    Q = {
        "drawdown_ratio_mean_2000_2009": round(yr[yr.year <= 2009].drawdown_ratio.mean(), 4),
        "drawdown_ratio_mean_2016_2025": round(yr[yr.year >= 2016].drawdown_ratio.mean(), 4),
        "deposit_bonus_months_mean_2016_2025": round(yr[yr.year >= 2016].deposit_bonus_months.mean(), 0),
        "deposit_other_months_mean_2016_2025": round(yr[yr.year >= 2016].deposit_other_months.mean(), 0),
        "deposit_bonus_months_mean_2000_2009": round(yr[yr.year <= 2009].deposit_bonus_months.mean(), 0),
        "deposit_other_months_mean_2000_2009": round(yr[yr.year <= 2009].deposit_other_months.mean(), 0),
        "negative_deposit_months_mean_2016_2025": round(yr[yr.year >= 2016].n_negative_months.mean(), 2),
        "negative_deposit_months_mean_2000_2009": round(yr[yr.year <= 2009].n_negative_months.mean(), 2),
        "surplus_other_months_mean_2016_2025": round(yr[yr.year >= 2016].surplus_other_months.mean(), 0),
        "consumption_cv_by_month_2016_2025": round(p["消費支出"].std(ddof=0) / p["消費支出"].mean(), 4),
        "disposable_cv_by_month_2016_2025": round(p["可処分所得"].std(ddof=0) / p["可処分所得"].mean(), 4),
        "deposit_by_month_2016_2025": {int(m): float(v) for m, v in p["預貯金純増"].items()},
    }
    (RES / "requestion.json").write_text(json.dumps(Q, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(Q, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
