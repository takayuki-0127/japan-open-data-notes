"""data/raw の CSV（日銀 API の応答）を読み、月次の横長の表 data/monthly.csv にする。"""
import io, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
NAMES = {
    "PRCS20_5200000000": "all", "PRCS20_52B0000000": "all_ex_intl", "PRCS20_5200630002": "road",
    "PRCS20_5200650002": "parcel", "PRCS20_5200650003": "truck_food", "PRCS20_5200650004": "truck_chem",
    "PRCS20_5200650005": "truck_metal", "PRCS20_5200650006": "truck_misc", "PRCS20_5200630001": "rail",
    "PRCS20_5200730002": "coastal", "PRCS20_5200930001": "warehouse", "PRCG20_2200650005": "diesel",
}


def read(code):
    txt = (RAW / f"{code}.csv").read_bytes().decode("cp932")
    lines = txt.splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith("SERIES_CODE"))
    d = pd.read_csv(io.StringIO("\n".join(lines[i:])))
    d = d[d.SERIES_CODE == code]
    s = pd.Series(pd.to_numeric(d.VALUES, errors="coerce").values, index=d.SURVEY_DATES.astype(int).values, name=NAMES[code])
    return s


df = pd.concat([read(c) for c in NAMES], axis=1).sort_index()
df.index.name = "ym"
df = df.loc[198501:]
df.to_csv(ROOT / "data" / "monthly.csv", float_format="%.4f")
print(df.tail(3).T)
