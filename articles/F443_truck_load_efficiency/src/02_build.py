"""年報の Excel（2000〜2025年度）から、営業用・自家用・車種別の輸送トンキロ・能力トンキロ・実車キロ・走行キロ・実車率・
（2020年度以降は公表の）積載効率を取り出し、data/fy_long.csv（年度×区分の縦長の表）を作る（オフライン）。"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

VOL_COLS = {
    "A": ["total", "biz_total", "biz_ordinary", "biz_small", "biz_special", "biz_kei", "own_total", "own_ordinary", "own_small", "own_special", "own_kei"],
    "B": ["total", "biz_total", "biz_ordinary", "biz_small", "biz_special", "biz_kei", "own_total", "own_ordinary", "own_small", "own_special"],
    "C": ["total", "biz_total", "biz_ordinary", "biz_lt3", "biz_3to6_5", "biz_6_5to11", "biz_11to16", "biz_16plus", "biz_small", "biz_special", "biz_kei",
          "own_total", "own_ordinary", "own_small", "own_special"],
}
UNIT_COLS = {
    "A": ["biz_ordinary", "biz_small", "biz_special", "biz_kei", "own_ordinary", "own_small", "own_special", "own_kei"],
    "B": ["biz_ordinary", "biz_small", "biz_special", "biz_kei", "own_ordinary", "own_small", "own_special"],
    "C": ["biz_ordinary", "biz_lt3", "biz_3to6_5", "biz_6_5to11", "biz_11to16", "biz_16plus", "biz_small", "biz_special", "biz_kei",
          "own_ordinary", "own_small", "own_special"],
}
LABELS = {"tonkm": ["輸送トンキロ", "トンキロ"], "cap_tonkm": ["能力トンキロ"], "run_km": ["走行キロ"], "loaded_km": ["実車キロ"],
          "tons": ["輸送トン数", "トン数"], "loaded_ratio": ["実車率"], "eff_pub": ["積載効率"]}


def era(fy):
    return "A" if fy <= 2009 else "B" if fy <= 2019 else "C"


def clean(x):
    return re.sub(r"[\s　]", "", str(x))


def rows(path):
    d = pd.read_excel(path, sheet_name=0, header=None)
    out = {}
    for r in d.itertuples(index=False):
        cells = [c for c in r if pd.notna(c)]
        if not cells:
            continue
        lab = clean(cells[0])
        nums = []
        for c in cells[1:]:
            try:
                nums.append(float(str(c).replace(",", "")))
            except ValueError:
                pass
        for key, names in LABELS.items():
            if lab in names and key not in out:
                out[key] = nums
    return out


def main():
    recs = []
    for fy in range(2000, 2026):
        e = era(fy)
        vol = next(RAW.glob(f"fy{fy}_volume.*")); unit = next(RAW.glob(f"fy{fy}_unit.*"))
        rv = rows(vol); ru = rows(unit)
        for key in ["tons", "tonkm", "cap_tonkm", "loaded_km", "run_km"]:
            if key not in rv:
                continue
            vals = rv[key]
            assert len(vals) == len(VOL_COLS[e]), (fy, key, len(vals))
            for c, v in zip(VOL_COLS[e], vals):
                recs.append({"fy": fy, "era": e, "group": c, "var": key, "value": v})
        for key in ["loaded_ratio", "eff_pub"]:
            if key not in ru:
                continue
            vals = ru[key]
            assert len(vals) == len(UNIT_COLS[e]), (fy, key, len(vals))
            for c, v in zip(UNIT_COLS[e], vals):
                recs.append({"fy": fy, "era": e, "group": c, "var": key, "value": v})
    df = pd.DataFrame(recs).sort_values(["fy", "group", "var"]).reset_index(drop=True)
    df.to_csv(ROOT / "data" / "fy_long.csv", index=False)
    print(df.shape, df.groupby("era").fy.agg(["min", "max"]).to_dict())
    print(df.pivot_table(index="fy", columns="var", values="value", aggfunc="count").to_string())


if __name__ == "__main__":
    main()
