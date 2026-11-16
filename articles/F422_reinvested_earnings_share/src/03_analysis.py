"""03 分析：直接投資収益の受取の内訳、再投資収益を除いた所得収支・経常収支、仮説、頑健性。
出力：results/main.json, results/annual_shares.csv, results/robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)


def main():
    a = pd.read_csv(D / "annual.csv").set_index("year")
    m = pd.read_csv(D / "monthly.csv").set_index("ym")
    s = pd.DataFrame(index=a.index)
    s["reinv_share_rec"] = a.di_reinv_rec / a.di_rec * 100
    s["div_share_rec"] = a.di_div_rec / a.di_rec * 100
    s["int_share_rec"] = a.di_int_rec / a.di_rec * 100
    s["reinv_net"] = (a.di_reinv_rec - a.di_reinv_pay) / 1e4
    di_net = a.di_rec - a.di_pay
    s["reinv_share_net"] = (a.di_reinv_rec - a.di_reinv_pay) / di_net * 100
    s["reinv_share_usd"] = a.di_reinv_rec_usd / a.di_rec_usd * 100
    s["reinv_share_of_primary_rec"] = a.di_reinv_rec / a.primary_rec * 100
    s["primary"] = a.primary / 1e4
    s["primary_ex_reinv"] = (a.primary - (a.di_reinv_rec - a.di_reinv_pay)) / 1e4
    s["trade"] = a.trade / 1e4
    s["ca"] = a.ca / 1e4
    s["ca_ex_reinv"] = (a.ca - (a.di_reinv_rec - a.di_reinv_pay)) / 1e4
    s["usdjpy"] = a.usdjpy
    s["check_fa_minus_reinv_rec"] = (a.fa_reinv_asset - a.di_reinv_rec) / 1e4
    s.round(4).to_csv(R / "annual_shares.csv")
    avg = lambda c, y0, y1: float(s.loc[y0:y1, c].mean())
    y25 = s.loc[2025]
    main = dict(
        reinv_share_1996_2005=avg("reinv_share_rec", 1996, 2005), reinv_share_2021_2025=avg("reinv_share_rec", 2021, 2025),
        div_share_2004_2008=avg("div_share_rec", 2004, 2008), div_share_2010_2014=avg("div_share_rec", 2010, 2014),
        reinv_share_2025=float(y25.reinv_share_rec), div_share_2025=float(y25.div_share_rec),
        reinv_rec_2025=float(a.loc[2025, "di_reinv_rec"] / 1e4), div_rec_2025=float(a.loc[2025, "di_div_rec"] / 1e4), di_rec_2025=float(a.loc[2025, "di_rec"] / 1e4),
        reinv_net_2025=float(y25.reinv_net), primary_2025=float(y25.primary), primary_ex_reinv_2025=float(y25.primary_ex_reinv),
        ca_2025=float(y25.ca), ca_ex_reinv_2025=float(y25.ca_ex_reinv), ca_ex_ratio_2025=float(y25.ca_ex_reinv / y25.ca * 100),
        trade_2025=float(y25.trade), reinv_share_of_primary_rec_2025=float(y25.reinv_share_of_primary_rec),
        reinv_share_max_year=int(s.reinv_share_rec.idxmax()), reinv_share_max=float(s.reinv_share_rec.max()),
        reinv_share_min_year=int(s.reinv_share_rec.idxmin()), reinv_share_min=float(s.reinv_share_rec.min()),
        reinv_rec_1996=float(a.loc[1996, "di_reinv_rec"] / 1e4), reinv_rec_2005=float(a.loc[2005, "di_reinv_rec"] / 1e4),
        fa_check_max_abs=float(s.check_fa_minus_reinv_rec.abs().max()),
    )
    after = s.loc[2005:2025]
    bad = [int(y) for y in after.index if after.loc[y, "primary_ex_reinv"] <= after.loc[y, "trade"]]
    main["years_primary_ex_le_trade"] = bad
    main["H1"] = "支持" if main["reinv_share_2021_2025"] - main["reinv_share_1996_2005"] >= 10 else "外れ"
    main["H2"] = "支持" if main["div_share_2010_2014"] > main["div_share_2004_2008"] else "外れ"
    main["H3"] = "支持" if not bad else "外れ"
    main["H4"] = "支持" if main["ca_ex_ratio_2025"] < 75 else "外れ"
    # 参考：ドル円の前年比と再投資の割合の前年差
    dfx = np.log(s.usdjpy).diff() * 100
    dsh = s.reinv_share_rec.diff()
    ok = dfx.notna() & dsh.notna()
    main["corr_fx_change_vs_share_change"] = float(np.corrcoef(dfx[ok], dsh[ok])[0, 1])
    # 頑健性
    roll = m[["di_rec", "di_reinv_rec", "di_reinv_pay", "di_pay", "ca"]].rolling(12).sum().dropna()
    last = roll.iloc[-1]
    rob = [
        dict(check="受取の割合（本線）", early=main["reinv_share_1996_2005"], late=main["reinv_share_2021_2025"]),
        dict(check="ネット（受取−支払）の割合", early=avg("reinv_share_net", 1996, 2005), late=avg("reinv_share_net", 2021, 2025)),
        dict(check="1996〜2000年 対 2021〜25年", early=avg("reinv_share_rec", 1996, 2000), late=avg("reinv_share_rec", 2021, 2025)),
        dict(check="2006〜10年 対 2016〜20年", early=avg("reinv_share_rec", 2006, 2010), late=avg("reinv_share_rec", 2016, 2020)),
        dict(check="H2 配当金の割合：2003〜07年 対 2010〜14年（2008〜09年の危機を除く）", early=avg("div_share_rec", 2003, 2007), late=avg("div_share_rec", 2010, 2014)),
        dict(check="ドル建ての割合", early=avg("reinv_share_usd", 1996, 2005), late=avg("reinv_share_usd", 2021, 2025)),
        dict(check=f"最新の12か月（{int(roll.index[-1])}まで）の割合", early=np.nan, late=float(last.di_reinv_rec / last.di_rec * 100)),
    ]
    rb = pd.DataFrame(rob); rb["diff"] = rb.late - rb.early
    rb.round(3).to_csv(R / "robustness.csv", index=False)
    main["latest_12m_end"] = int(roll.index[-1]); main["latest_12m_share"] = float(last.di_reinv_rec / last.di_rec * 100)
    main["latest_12m_ca_ex_ratio"] = float((last.ca - (last.di_reinv_rec - last.di_reinv_pay)) / last.ca * 100)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(rb)
    print(s[["reinv_share_rec", "div_share_rec", "reinv_net", "ca", "ca_ex_reinv", "trade", "primary_ex_reinv"]].round(1).to_string())


if __name__ == "__main__":
    main()
