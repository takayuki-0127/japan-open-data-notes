"""03 分析：切り替わりの年と月、その後の逆転の有無、2025年の構成、第一次所得収支の内訳、頑健性。
出力：results/main.json, results/annual_table.csv, results/primary_breakdown.csv, results/robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
CHO = 1e4  # 億円 → 兆円


def first_cross(s_income, s_trade):
    above = s_income > s_trade
    yrs = above[above].index
    return int(yrs[0]) if len(yrs) else None


def reversals(s_income, s_trade, after):
    x = (s_trade > s_income)
    return [int(y) for y in x[x].index if y > after]


def main():
    a = pd.read_csv(D / "annual.csv").set_index("year")
    m = pd.read_csv(D / "monthly.csv").set_index("ym")
    t = a[["ca", "trade", "services", "trade_services", "primary", "secondary"]] / CHO
    t.round(3).to_csv(R / "annual_table.csv")
    y_cross = first_cross(a.primary, a.trade)
    rev = reversals(a.primary, a.trade, y_cross)
    first_trade_deficit = int(a.index[(a.trade < 0)][0])
    # 月次 後ろ12か月
    roll = m[["trade", "primary", "trade_services"]].rolling(12).sum().dropna()
    above = roll.primary > roll.trade
    ym_cross = int(above[above].index[0])
    rev_m = [int(i) for i in roll.index[(roll.trade > roll.primary) & (roll.index > ym_cross)]]
    # 内訳（ネット）
    comp = ["comp_employees", "di_dividends", "di_reinvested", "di_interest", "pf_dividends", "pf_bond_interest", "other_invest_income", "other_primary"]
    b = a.loc[1996:2025, comp + ["di_income", "portfolio_income", "primary"]].fillna(0) / CHO
    b.round(4).to_csv(R / "primary_breakdown.csv")
    di_over_pf = b.di_income > b.portfolio_income
    y_di_over = int(di_over_pf[di_over_pf].index[0]) if di_over_pf.any() else None
    y25 = a.loc[2025]
    main = dict(
        first_year_primary_gt_trade=y_cross, reversal_years_after=rev,
        first_trade_deficit_year=first_trade_deficit,
        first_month_primary_gt_trade_12m=ym_cross, reversal_months_after=len(rev_m),
        trade_1985=float(a.loc[1985, "trade"] / CHO), primary_1985=float(a.loc[1985, "primary"] / CHO),
        trade_y_cross=float(a.loc[y_cross, "trade"] / CHO), primary_y_cross=float(a.loc[y_cross, "primary"] / CHO),
        trade_2025=float(y25.trade / CHO), services_2025=float(y25.services / CHO), primary_2025=float(y25.primary / CHO),
        secondary_2025=float(y25.secondary / CHO), ca_2025=float(y25.ca / CHO),
        primary_over_ca_2025=float(y25.primary / y25.ca * 100),
        di_2025=float(y25.di_income / CHO), pf_2025=float(y25.portfolio_income / CHO),
        di_reinvested_2025=float(y25.di_reinvested / CHO), di_dividends_2025=float(y25.di_dividends / CHO),
        di_share_primary_2025=float(y25.di_income / y25.primary * 100), pf_share_primary_2025=float(y25.portfolio_income / y25.primary * 100),
        di_1996=float(a.loc[1996, "di_income"] / CHO), pf_1996=float(a.loc[1996, "portfolio_income"] / CHO),
        first_year_di_gt_pf=y_di_over,
        primary_max_year=int(a.primary.idxmax()), trade_max_year=int(a.trade.idxmax()), trade_max=float(a.trade.max() / CHO),
    )
    main["H1"] = "支持" if 2003 <= y_cross <= 2007 else "外れ"
    main["H2"] = "支持" if len(rev) == 0 else "外れ"
    main["H3"] = "支持" if y25.primary > y25.ca else "外れ"
    main["H4"] = "支持" if y25.di_income > y25.portfolio_income else "外れ"
    # 頑健性
    rob = [dict(check="暦年・貿易収支（本線）", first=y_cross, reversals=",".join(map(str, rev)) or "なし")]
    rob.append(dict(check="月次・後ろ12か月の合計", first=ym_cross, reversals=f"{len(rev_m)}か月"))
    yts = first_cross(a.primary, a.trade_services)
    rob.append(dict(check="貿易・サービス収支と比べる", first=yts, reversals=",".join(map(str, reversals(a.primary, a.trade_services, yts))) or "なし"))
    yus = first_cross(a.primary_usd, a.trade_usd)
    rob.append(dict(check="ドル建て", first=yus, reversals=",".join(map(str, reversals(a.primary_usd, a.trade_usd, yus))) or "なし"))
    ov = pd.read_csv(D / "overlap_check.csv")
    rob.append(dict(check="1996〜2013年 組替の年次と月次の合計の差（最大、億円）", first=float((ov.trade - ov.trade_m).abs().max().round(3)),
                    reversals=float((ov.primary - ov.primary_m).abs().max().round(3))))
    pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
    main["first_year_ts"] = yts; main["first_year_usd"] = yus
    above_ts = (a.primary > a.trade_services).loc[1985:2025]
    main["stable_from_ts"] = int(min(y for y in above_ts.index if above_ts.loc[y:].all()))
    main["primary_1996"] = float(a.loc[1996, "primary"] / CHO); main["trade_1996"] = float(a.loc[1996, "trade"] / CHO)
    main["primary_2005_2025_mult"] = float(a.loc[2025, "primary"] / a.loc[2005, "primary"])
    main["di_share_primary_2025_usd"] = float(a.loc[2025, "di_income_usd"] / a.loc[2025, "primary_usd"] * 100)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(pd.DataFrame(rob))


if __name__ == "__main__":
    main()
