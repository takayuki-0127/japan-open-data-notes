"""03b 問い直し：減少が5年ごとにまとまるなら、どの階層がその年に減っているのか。
2001〜2025年を「波の年」（2001〜03、06〜08、11〜13、16〜18、21〜23年）とそれ以外に分け、
階層ごとの増減の合計を比べる。
出力：results/requestion.json, results/wave_by_class.csv
"""
import json, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
WAVE = [y for b in (2001, 2006, 2011, 2016, 2021) for y in (b, b + 1, b + 2)]


def main():
    cap = pd.read_csv(D / "capital_long.csv")
    w = cap.pivot(index="year", columns="cls", values="firms")
    w["total"] = w.sum(axis=1)
    dw = w.diff().loc[2001:2025]
    dw["wave"] = dw.index.isin(WAVE)
    g = dw.groupby("wave").sum().T
    g.columns = ["other_years", "wave_years"]
    g["n_wave_years"] = len(WAVE); g["n_other_years"] = 25 - len(WAVE)
    g.to_csv(R / "wave_by_class.csv")
    out = dict(
        wave_years=WAVE,
        total_wave=int(g.loc["total", "wave_years"]), total_other=int(g.loc["total", "other_years"]),
        individual_wave=int(g.loc["individual", "wave_years"]), individual_other=int(g.loc["individual", "other_years"]),
        c10m50m_wave=int(g.loc["10m_50m", "wave_years"]), c10m50m_other=int(g.loc["10m_50m", "other_years"]),
        lt2m_wave=int(g.loc["lt2m", "wave_years"]), lt2m_other=int(g.loc["lt2m", "other_years"]),
    )
    out["wave_share_of_net"] = out["total_wave"] / (out["total_wave"] + out["total_other"]) * 100
    json.dump({k: (round(v, 2) if isinstance(v, float) else v) for k, v in out.items()}, open(R / "requestion.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(out); print(g)


if __name__ == "__main__":
    main()
