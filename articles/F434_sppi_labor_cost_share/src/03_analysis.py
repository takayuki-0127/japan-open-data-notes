"""03 分析：高人件費率と低人件費率の比較（期間の年率、2021年からの上昇、振れ、差の転換点）、頑健性。
出力：results/main.json, results/annual.csv, results/yoy.csv, results/robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)


def main():
    e = pd.read_csv(D / "extax.csv").set_index("ym")
    t = pd.read_csv(D / "intax.csv").set_index("ym")
    ae = e.groupby(e.index // 100).mean().loc[:2025]; ae.index.name = "year"
    ae.round(4).to_csv(R / "annual.csv")
    yoy = (e / e.shift(12) - 1) * 100
    yoy.round(4).to_csv(R / "yoy.csv")
    last = int(e.index[-1])
    since = lambda c, b: float((e.loc[last, c] / ae.loc[b, c] - 1) * 100)
    cagr = lambda d, c, a, b: float(((d.loc[b, c] / d.loc[a, c]) ** (1 / (b - a)) - 1) * 100)
    ay = (ae / ae.shift(1) - 1) * 100
    gap = (yoy.high_labor - yoy.low_labor).dropna()
    # 差が12か月続けてプラスになった最初の月（2015年以降）
    pos = (gap > 0).astype(int).rolling(12).sum()
    turn = [int(i) for i in pos.index if i >= 201501 and pos.loc[i] == 12]
    turn_first = int(turn[0]) - 11 * 1 if turn else None
    idx = list(gap.index)
    turn_start = idx[idx.index(turn[0]) - 11] if turn else None
    main = dict(last=last, high_since2021=since("high_labor", 2021), low_since2021=since("low_labor", 2021), all_since2021=since("all", 2021),
                high_cagr_2000_2020=cagr(ae, "high_labor", 2000, 2020), low_cagr_2000_2020=cagr(ae, "low_labor", 2000, 2020),
                high_cagr_2013_2020=cagr(ae, "high_labor", 2013, 2020), low_cagr_2013_2020=cagr(ae, "low_labor", 2013, 2020),
                sd_high=float(yoy.high_labor.std()), sd_low=float(yoy.low_labor.std()),
                high_yoy_2025=float(ay.loc[2025, "high_labor"]), low_yoy_2025=float(ay.loc[2025, "low_labor"]), all_yoy_2025=float(ay.loc[2025, "all"]),
                high_yoy_latest=float(yoy.high_labor.iloc[-1]), low_yoy_latest=float(yoy.low_labor.iloc[-1]),
                gap_turn_start=turn_start, gap_mean_2023_2026=float(gap.loc[202301:].mean()),
                **{f"{k}_since2021": since(k, 2021) for k in ["finance", "real_estate", "transport", "ict", "leasing", "advertising", "other_services"]})
    main["H1"] = "支持" if main["high_since2021"] > main["low_since2021"] else "外れ"
    main["H2"] = "支持" if main["high_cagr_2000_2020"] < main["low_cagr_2000_2020"] else "外れ"
    main["H3"] = "支持" if main["sd_high"] < main["sd_low"] else "外れ"
    main["H4"] = "支持" if main["high_yoy_2025"] >= 3 else "外れ"
    rob = []
    at = t.groupby(t.index // 100).mean()
    lt = int(t.index[-1])
    rob.append(dict(check="消費税を含む：2021年平均→最新", high=float((t.loc[lt, "high_labor"] / at.loc[2021, "high_labor"] - 1) * 100), low=float((t.loc[lt, "low_labor"] / at.loc[2021, "low_labor"] - 1) * 100)))
    rob.append(dict(check="消費税を含む：1985→2020年の年率", high=cagr(at, "high_labor", 1985, 2020), low=cagr(at, "low_labor", 1985, 2020)))
    for b in (2019, 2022):
        rob.append(dict(check=f"消費税を除く：{b}年平均→最新", high=since("high_labor", b), low=since("low_labor", b)))
    mom = (e / e.shift(1) - 1) * 100
    rob.append(dict(check="前月比の標準偏差（2000〜2026年）", high=float(mom.high_labor.std()), low=float(mom.low_labor.std())))
    rob.append(dict(check="前年比の標準偏差（2000〜2026年）", high=main["sd_high"], low=main["sd_low"]))
    pd.DataFrame(rob).round(4).to_csv(R / "robustness.csv", index=False)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(pd.read_csv(R / "robustness.csv").to_string()); print(ay[["all", "high_labor", "low_labor"]].round(2).loc[2013:].to_string())


if __name__ == "__main__":
    main()
