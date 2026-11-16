"""02 整形：地域×年の表（平年比、梅雨入り・明けの日付、期間の長さ）"""
import pathlib
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
REG = ["沖縄", "奄美", "九州南部", "九州北部", "四国", "中国", "近畿", "東海", "関東甲信", "北陸", "東北南部", "東北北部"]


def main():
    L = [l.rstrip("\r").split(",") for l in (RAW / "tsuyu_prec.csv").read_bytes().decode("cp932").split("\n")]
    rows = []
    for c in L[2:]:
        if c and c[0].isdigit():
            for i, r in enumerate(REG):
                v = c[1 + i].strip()
                rows.append((int(c[0]), r, float(v) if v not in ("", "-9999") else np.nan))
    p = pd.DataFrame(rows, columns=["year", "region", "ratio"])
    L = [l.rstrip("\r").split(",") for l in (RAW / "tsuyu_iriake.csv").read_bytes().decode("cp932").split("\n")]
    rows = []
    for c in L[3:]:
        if c and c[0].isdigit():
            y = int(c[0])
            for i, r in enumerate(REG):
                m0, d0, m1, d1 = [int(x) for x in c[1 + 4 * i: 5 + 4 * i]]
                s = pd.Timestamp(y, m0, d0) if m0 > 0 else pd.NaT
                e = pd.Timestamp(y, m1, d1) if m1 > 0 else pd.NaT
                rows.append((y, r, s, e))
    q = pd.DataFrame(rows, columns=["year", "region", "start", "end"])
    q["length"] = (q.end - q.start).dt.days
    q["start_doy"] = q.start.dt.dayofyear
    q["end_doy"] = q.end.dt.dayofyear
    d = p.merge(q[["year", "region", "start_doy", "end_doy", "length"]], on=["year", "region"], how="left")
    d["region"] = pd.Categorical(d.region, REG, ordered=True)
    d.sort_values(["region", "year"]).to_csv(ROOT / "data" / "panel.csv", index=False)
    print(len(d), d.year.min(), d.year.max(), d.ratio.isna().sum(), d.length.isna().sum())


if __name__ == "__main__":
    main()
