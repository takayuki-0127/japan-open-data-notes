"""日本銀行 API の JSON を表にする（各記事の src/ に写して使う）。"""
import json
import pandas as pd


def load(path):
    d = json.load(open(path, encoding="utf-8"))
    out = {}
    for r in d["RESULTSET"]:
        v = r["VALUES"]
        out[r["SERIES_CODE"]] = pd.Series([float(x) if x is not None else float("nan") for x in v["VALUES"]],
                                          index=[int(x) for x in v["SURVEY_DATES"]])
    return pd.DataFrame(out)
