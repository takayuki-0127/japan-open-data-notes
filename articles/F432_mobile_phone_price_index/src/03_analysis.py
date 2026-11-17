"""03 分析：年平均の指数、期間の変化、ドル円との相関、通信料の段差、頑健性。
出力：results/main.json, results/annual.csv, results/robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)


def corr_yoy(d, a, b, lead=0):
    y = (d.phone_device / d.phone_device.shift(12) - 1) * 100
    f = (np.log(d.usdjpy) - np.log(d.usdjpy.shift(12))) * 100
    f = f.shift(lead)
    s = pd.concat([y, f], axis=1).loc[a:b].dropna()
    return float(np.corrcoef(s.iloc[:, 0], s.iloc[:, 1])[0, 1]), len(s)


def main():
    d = pd.read_csv(D / "monthly.csv").set_index("ym")
    ann = d.groupby(d.index // 100).mean()
    ann = ann.loc[:2025]
    ann.round(4).to_csv(R / "annual.csv")
    ch = lambda c, a, b: float((ann.loc[b, c] / ann.loc[a, c] - 1) * 100)
    c0, n0 = corr_yoy(d, 201301, 202609)
    main = dict(device_2005=float(ann.loc[2005, "phone_device"]), device_2019=float(ann.loc[2019, "phone_device"]), device_2023=float(ann.loc[2023, "phone_device"]),
                device_2025=float(ann.loc[2025, "phone_device"]), device_latest=float(d.phone_device.iloc[-1]),
                device_2005_2019=ch("phone_device", 2005, 2019), device_2019_2023=ch("phone_device", 2019, 2023), device_2019_2025=ch("phone_device", 2019, 2025),
                device_min_year=int(ann.phone_device.idxmin()), device_min=float(ann.phone_device.min()),
                fee_2019=float(ann.loc[2019, "mobile_fee"]), fee_latest=float(d.mobile_fee.iloc[-1]), fee_drop_vs_2019=float((d.mobile_fee.iloc[-1] / ann.loc[2019, "mobile_fee"] - 1) * 100),
                fee_2000=float(ann.loc[2000, "mobile_fee"]), fee_2000_2019=ch("mobile_fee", 2000, 2019),
                fee_step_202103_202104=float((d.loc[202104, "mobile_fee"] / d.loc[202103, "mobile_fee"] - 1) * 100),
                fee_step_202109_202110=float((d.loc[202110, "mobile_fee"] / d.loc[202109, "mobile_fee"] - 1) * 100),
                all_2019_latest=float((d["all"].iloc[-1] / ann.loc[2019, "all"] - 1) * 100),
                corr_2013_2026=c0, corr_n=n0, usdjpy_2019=float(ann.loc[2019, "usdjpy"]), usdjpy_2023=float(ann.loc[2023, "usdjpy"]))
    main["H1"] = "支持" if main["device_2005_2019"] <= -30 else "外れ"
    main["H2"] = "支持" if main["device_2019_2023"] > 0 else "外れ"
    main["H3"] = "支持" if c0 >= 0.3 else "外れ"
    main["H4"] = "支持" if main["fee_drop_vs_2019"] <= -40 else "外れ"
    rob = []
    for a, b in [(2010, 2019), (2015, 2019), (2019, 2024), (2019, 2025)]:
        rob.append(dict(check=f"携帯電話機 {a}→{b}年（年平均）", value=ch("phone_device", a, b)))
    for a, b, lead in [(201301, 201912, 0), (202001, 202609, 0), (201301, 202609, 6), (201301, 202609, 12)]:
        c, n = corr_yoy(d, a, b, lead)
        rob.append(dict(check=f"相関 {a}〜{b}、ドル円を{lead}か月先行（n={n}）", value=c))
    ma = d.phone_device.rolling(12).mean()
    rob.append(dict(check="12か月移動平均：2019年12月→2023年12月", value=float((ma.loc[202312] / ma.loc[201912] - 1) * 100)))
    pd.DataFrame(rob).round(4).to_csv(R / "robustness.csv", index=False)
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(pd.read_csv(R / "robustness.csv").to_string()); print(ann[["phone_device", "mobile_fee", "usdjpy"]].round(1).loc[2005:].to_string())


if __name__ == "__main__":
    main()
