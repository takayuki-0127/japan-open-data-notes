"""03b 問い直し：投資信託委託会社等の株式の買い越しが大きいのに、全部門の株式の買い越しがほぼゼロなのはなぜか。
(1) 2024〜25年の株式のネットを部門ごとに並べ、買い越しと売り越しの内訳を出す。
(2) 月次で、投資信託委託会社等と信託勘定の株式のネットの相関（2014年1月〜最新）。
(3) 信託勘定の株式と中長期債のネット（2024〜25年）。
(4) 12か月合計の推移 → results/rolling12.csv
出力：results/requestion.json, results/sector_2024_2025.csv, results/rolling12.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
SEC = ["central_bank", "general_gov", "banks", "trust_banks_own", "trust_accounts", "securities_firms", "life_insurers", "nonlife_insurers", "investment_trusts", "others"]


def main():
    d = pd.read_csv(D / "flows_long.csv")
    d["year"] = d.ym // 100
    p = d[(d.year >= 2024) & (d.year <= 2025)].groupby(["asset", "sector"]).net.sum().unstack(0)[["equity", "longbond", "shortbond", "total"]] / 1e4
    p = p.loc[SEC + ["all"]]
    p.round(4).to_csv(R / "sector_2024_2025.csv")
    eq = p.equity.drop("all")
    buy = float(eq[eq > 0].sum()); sell = float(eq[eq < 0].sum())
    m = d[(d.asset == "equity")].pivot_table(index="ym", columns="sector", values="net")
    mm = m.loc[201401:]
    corr = float(np.corrcoef(mm.investment_trusts, mm.trust_accounts)[0, 1])
    corr24 = float(np.corrcoef(m.loc[202401:].investment_trusts, m.loc[202401:].trust_accounts)[0, 1])
    roll = m[["investment_trusts", "trust_accounts", "others", "all"]].rolling(12).sum() / 1e4
    roll.loc[201001:].round(4).to_csv(R / "rolling12.csv")
    pk = roll.investment_trusts.idxmax()
    out = dict(equity_buy_sectors=buy, equity_sell_sectors=sell, it_equity=float(eq.investment_trusts), ta_equity=float(eq.trust_accounts),
               ta_longbond=float(p.loc["trust_accounts", "longbond"]), ta_total=float(p.loc["trust_accounts", "total"]),
               it_minus_ta=float(eq.investment_trusts + eq.trust_accounts), all_equity=float(p.loc["all", "equity"]),
               corr_it_ta_2014=corr, corr_it_ta_2024=corr24, n_months_2014=int(len(mm)),
               it_roll_peak=float(roll.investment_trusts.max()), it_roll_peak_ym=int(pk), it_roll_last=float(roll.investment_trusts.iloc[-1]),
               ta_roll_last=float(roll.trust_accounts.iloc[-1]), all_roll_last=float(roll["all"].iloc[-1]), last_ym=int(roll.index[-1]),
               ta_equity_sell_months_2024_2025=int((m.loc[202401:202512].trust_accounts < 0).sum()),
               it_equity_buy_months_2024_2025=int((m.loc[202401:202512].investment_trusts > 0).sum()))
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=0)); print(p.round(2).to_string())
    print(roll.loc[202301:].round(1).iloc[::3].to_string())


if __name__ == "__main__":
    main()
