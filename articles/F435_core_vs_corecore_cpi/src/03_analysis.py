"""03 分析：コアとコアコアの前年比の差、振れ、12か月先の総合の予測の誤差、補助の時期、頑健性。
出力：results/main.json, results/yoy.csv, results/forecast.csv, results/robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
TAX = [(199704, 199803), (201404, 201503), (201910, 202009)]
MEAS = ["headline", "core", "corecore", "us_core"]


def tax_mask(idx):
    m = pd.Series(False, index=idx)
    for a, b in TAX:
        m |= (idx >= a) & (idx <= b)
    return m


def forecast(yoy, a, b, h=12, drop_tax=False):
    out = {}
    target = yoy.headline.shift(-h)
    for k in MEAS:
        e = (target - yoy[k]).loc[a:b].dropna()
        if drop_tax:
            # 予測の元の月か、当てる先の月のどちらかが税の影響を受ける月を除く
            tgt = pd.Index([((i // 100) + ((i % 100 + h - 1) // 12)) * 100 + ((i % 100 + h - 1) % 12 + 1) for i in e.index])
            bad = tax_mask(e.index).values | tax_mask(tgt).values
            e = e[~bad]
        out[k] = float(np.sqrt((e ** 2).mean()))
    return out


def main():
    d = pd.read_csv(D / "cpi.csv").set_index("ym")
    w = pd.read_csv(D / "weights.csv", index_col=0).weight_per_10000
    yoy = (d / d.shift(12) - 1) * 100
    yoy["gap"] = yoy.core - yoy.corecore
    yoy["energy_contrib"] = yoy.energy * w["energy"] / w["core"]
    yoy.round(4).to_csv(R / "yoy.csv")
    mom = (d / d.shift(1) - 1) * 100
    g = yoy.gap.loc[202201:202609]
    sub = yoy.loc[202301:202412]
    fc = forecast(yoy, 200001, 202509)
    pd.DataFrame([dict(check="2000〜2025年、12か月先（本線）", **fc)]).to_csv(R / "forecast.csv", index=False)
    main = dict(gap_abs_mean_2022_2026=float(g.abs().mean()), gap_max=float(g.max()), gap_max_month=int(g.idxmax()), gap_min=float(g.min()), gap_min_month=int(g.idxmin()),
                gap_abs_mean_2000_2021=float(yoy.gap.loc[200001:202112].abs().mean()),
                sd_mom_core=float(mom.core.loc[200001:].std()), sd_mom_corecore=float(mom.corecore.loc[200001:].std()), sd_mom_headline=float(mom.headline.loc[200001:].std()),
                sd_mom_us_core=float(mom.us_core.loc[200001:].std()),
                rmse_headline=fc["headline"], rmse_core=fc["core"], rmse_corecore=fc["corecore"], rmse_us_core=fc["us_core"],
                months_core_below_2023_2024=int((sub.core < sub.corecore).sum()), months_2023_2024=int(len(sub)),
                core_latest=float(yoy.core.iloc[-1]), corecore_latest=float(yoy.corecore.iloc[-1]), headline_latest=float(yoy.headline.iloc[-1]),
                us_core_latest=float(yoy.us_core.iloc[-1]),
                core_peak=float(yoy.core.loc[202201:].max()), core_peak_month=int(yoy.core.loc[202201:].idxmax()),
                corecore_peak=float(yoy.corecore.loc[202201:].max()), corecore_peak_month=int(yoy.corecore.loc[202201:].idxmax()),
                core_mean_2022_2026=float(yoy.core.loc[202201:].mean()), corecore_mean_2022_2026=float(yoy.corecore.loc[202201:].mean()))
    main["H1"] = "支持" if main["gap_abs_mean_2022_2026"] >= 0.5 else "外れ"
    main["H2"] = "支持" if main["sd_mom_corecore"] < main["sd_mom_core"] else "外れ"
    main["H3"] = "支持" if main["rmse_corecore"] < main["rmse_core"] else "外れ"
    main["H4"] = "支持" if main["months_core_below_2023_2024"] > main["months_2023_2024"] / 2 else "外れ"
    rob = []
    for lab, a, b, h, dt in [("2000〜2025年、12か月先、消費税の月を除く", 200001, 202509, 12, True), ("2000〜2019年、12か月先", 200001, 201912, 12, False),
                             ("2013〜2025年、12か月先", 201301, 202509, 12, False), ("2000〜2025年、6か月先", 200001, 202603, 6, False),
                             ("2000〜2024年、24か月先", 200001, 202409, 24, False)]:
        rob.append(dict(check=lab, **forecast(yoy, a, b, h, dt)))
    pd.DataFrame(rob).round(4).to_csv(R / "robustness.csv", index=False)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(pd.read_csv(R / "robustness.csv").to_string())


if __name__ == "__main__":
    main()
