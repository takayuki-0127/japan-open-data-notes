"""03 分析：部門×資産の年ごとのネット取得、2024〜25年と2014〜23年の比較、仮説、頑健性。
出力：results/main.json, results/annual_net.csv, results/robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
KEY = ["central_bank", "general_gov", "banks", "trust_banks_own", "trust_accounts", "securities_firms", "life_insurers", "nonlife_insurers", "investment_trusts", "others"]


def main():
    d = pd.read_csv(D / "flows_long.csv")
    d["year"] = d.ym // 100
    full = d[d.year <= 2025]
    a = full.groupby(["year", "asset", "sector"])[["acq", "disp", "net"]].sum().reset_index()
    a.to_csv(R / "annual_net.csv", index=False)
    net = a.pivot_table(index=["asset", "year"], columns="sector", values="net")
    cho = lambda x: float(x / 1e4)
    eq = net.loc["equity"]; lb = net.loc["longbond"]; tot = net.loc["total"]
    it24_25 = eq.loc[2024:2025, "investment_trusts"].sum(); it14_23 = eq.loc[2014:2023, "investment_trusts"].sum()
    eq_all_24_25 = eq.loc[2024:2025, "all"].sum()
    share = it24_25 / eq_all_24_25 * 100
    main = dict(it_equity_2024=cho(eq.loc[2024, "investment_trusts"]), it_equity_2025=cho(eq.loc[2025, "investment_trusts"]),
                it_equity_2024_2025=cho(it24_25), it_equity_2014_2023=cho(it14_23), it_equity_2023=cho(eq.loc[2023, "investment_trusts"]),
                all_equity_2024_2025=cho(eq_all_24_25), it_share_equity_2024_2025=float(share),
                banks_longbond_2022=cho(lb.loc[2022, "banks"]), banks_longbond_2023=cho(lb.loc[2023, "banks"]),
                banks_longbond_2024=cho(lb.loc[2024, "banks"]), banks_longbond_2025=cho(lb.loc[2025, "banks"]),
                all_longbond_2024_2025=cho(lb.loc[2024:2025, "all"].sum()), all_equity_2024=cho(eq.loc[2024, "all"]), all_equity_2025=cho(eq.loc[2025, "all"]),
                all_total_2024=cho(tot.loc[2024, "all"]), all_total_2025=cho(tot.loc[2025, "all"]), all_total_2022=cho(tot.loc[2022, "all"]),
                life_longbond_2024_2025=cho(lb.loc[2024:2025, "life_insurers"].sum()), others_equity_2024_2025=cho(eq.loc[2024:2025, "others"].sum()),
                trust_acc_equity_2024_2025=cho(eq.loc[2024:2025, "trust_accounts"].sum()))
    main["H1"] = "支持" if it24_25 > it14_23 else "外れ"
    main["H2"] = ("支持" if share >= 50 else "外れ") if eq_all_24_25 > 0 else "判定できない（全部門の合計が売り越し）"
    pos = eq.loc[2024:2025].drop(columns="all").sum(); pos = pos[pos > 0].sum()
    main["it_share_of_buying_sectors"] = float(it24_25 / pos * 100)
    main["it_ratio_vs_2014_2023"] = float(it24_25 / it14_23 * 100)
    main["banks_longbond_2022_2023"] = cho(lb.loc[2022:2023, "banks"].sum())
    main["H3"] = "支持" if lb.loc[2022:2023, "banks"].sum() < 0 else "外れ"
    main["H4"] = "支持" if lb.loc[2024:2025, "all"].sum() < eq_all_24_25 else "外れ"
    # 頑健性
    m = d.set_index("ym")
    rob = []
    last = int(d.ym.max())
    x = d[(d.ym >= 202401) & (d.asset == "equity")].groupby("sector").net.sum()
    rob.append(dict(check=f"株式 2024年1月〜{last}：投資信託委託会社等（兆円）", value=cho(x["investment_trusts"])))
    rob.append(dict(check=f"株式 2024年1月〜{last}：信託勘定（兆円）", value=cho(x["trust_accounts"])))
    rob.append(dict(check=f"株式 2024年1月〜{last}：全部門の合計（兆円）", value=cho(x["all"])))
    g = full[(full.asset == "equity") & (full.sector == "investment_trusts")].groupby("year").acq.sum()
    rob.append(dict(check="株式の取得（買いの総額）投資信託委託会社等 2023→2025年（兆円）", value=f"{cho(g.loc[2023]):.1f}→{cho(g.loc[2025]):.1f}"))
    t = net.loc["total"]
    rob.append(dict(check="株式 2024〜25年：買い越した部門の合計に占める投資信託委託会社等の割合（%）", value=main["it_share_of_buying_sectors"]))
    rob.append(dict(check="全資産 投資信託委託会社等 2024〜25年（兆円）", value=cho(t.loc[2024:2025, "investment_trusts"].sum())))
    rob.append(dict(check="株式 その他（事業会社・個人など）2024〜25年（兆円）", value=main["others_equity_2024_2025"]))
    rob.append(dict(check="株式 信託勘定 2024〜25年（兆円）", value=main["trust_acc_equity_2024_2025"]))
    rob.append(dict(check="株式 投資信託委託会社等 2023年 → 2024年（兆円）", value=f"{main['it_equity_2023']:.1f}→{main['it_equity_2024']:.1f}"))
    pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(pd.read_csv(R / "robustness.csv").to_string())
    print((eq.loc[2014:2025, KEY + ["all"]] / 1e4).round(1).to_string())
    print((lb.loc[2014:2025, KEY + ["all"]] / 1e4).round(1).to_string())


if __name__ == "__main__":
    main()
