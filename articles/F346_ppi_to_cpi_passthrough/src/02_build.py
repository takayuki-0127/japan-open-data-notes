"""data/raw から月次の表 data/prices_monthly.csv を作る（オフライン）。"""
import pathlib, json, io, csv
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
NAMES = {"PRCG15_18K0110000": "素原材料", "PRCG15_18K0210000": "中間財", "PRCG15_18K0310000": "最終財", "PRCG15_18K0322002": "最終財_消費財",
         "PRCG15_18K0321001": "最終財_資本財", "PRCG15_18K0000000": "国内需要財", "PRCG15_18K0121001": "加工用素原材料", "PRCG15_18K0221001": "製品原材料",
         "PRFI20_1I1G00000": "ステージ1_財", "PRFI20_1I2G00000": "ステージ2_財", "PRFI20_1I3G00000": "ステージ3_財", "PRFI20_1I4G00000": "ステージ4_財",
         "PRFI20_1I1A00000": "ステージ1_総合", "PRFI20_1I2A00000": "ステージ2_総合", "PRFI20_1I3A00000": "ステージ3_総合", "PRFI20_1I4A00000": "ステージ4_総合",
         "PRFI20_1FXG00000": "最終需要_財", "PRFI20_1FXA00000": "最終需要_総合", "PRFI20_1FXG00100": "最終需要_食料品", "PRFI20_1FXG00200": "最終需要_エネルギー",
         "PRFI20_1FXG00300": "最終需要_その他財", "PRFI20_1FXSD0000": "最終需要_サービス"}
CPI = {"財": "CPI_財", "生鮮食品を除く財": "CPI_生鮮除く財", "工業製品": "CPI_工業製品", "食料工業製品": "CPI_食料工業製品", "石油製品": "CPI_石油製品",
       "他の工業製品": "CPI_他の工業製品", "総合": "CPI_総合"}


def boj(fname):
    j = json.loads((RAW / fname).read_text(encoding="utf-8"))
    out = {}
    for s in j["RESULTSET"]:
        name = NAMES.get(s["SERIES_CODE"])
        if name is None:
            continue
        out[name] = pd.Series(pd.to_numeric(s["VALUES"]["VALUES"], errors="coerce"), index=[int(x) for x in s["VALUES"]["SURVEY_DATES"]])
    return pd.DataFrame(out)


def cpi():
    rows = list(csv.reader(io.StringIO((RAW / "cpi_goods_services_1970_2026.csv").read_bytes().decode("cp932"))))
    head = rows[0]
    idx = {}
    for k, v in CPI.items():
        if k in head:
            idx[v] = head.index(k)
    data = {}
    for r in rows:
        if r and r[0].strip().isdigit() and len(r[0].strip()) == 6:
            ym = int(r[0])
            data[ym] = {v: pd.to_numeric(r[i], errors="coerce") for v, i in idx.items()}
    return pd.DataFrame.from_dict(data, orient="index")


def main():
    a = boj("boj_stage_2015base.json"); b = boj("boj_fdid_2020base.json"); c = cpi()
    df = a.join(b, how="outer").join(c, how="outer").sort_index()
    df.index.name = "ym"
    df = df[df.index >= 197001]
    df.to_csv(ROOT / "data" / "prices_monthly.csv")
    print(df.shape, df.index.min(), df.index.max())
    print(df.loc[[198001, 202204, 202609]].T.head(30))


if __name__ == "__main__":
    main()
