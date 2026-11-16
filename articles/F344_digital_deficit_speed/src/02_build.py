"""data/raw の JSON から縦長の CSV を作る（オフライン）。"""
import pathlib, json
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def load(fname):
    j = json.loads((RAW / fname).read_text(encoding="utf-8"))
    rows = []
    for s in j["RESULTSET"]:
        for d, v in zip(s["VALUES"]["SURVEY_DATES"], s["VALUES"]["VALUES"]):
            rows.append(dict(code=s["SERIES_CODE"], name=s["NAME_OF_TIME_SERIES_J"], unit=s["UNIT_J"], period=int(d),
                             value=pd.to_numeric(v, errors="coerce")))
    return pd.DataFrame(rows)


def main():
    m = load("bop_services_monthly_1996_2026.json")
    m["year"] = m["period"] // 100; m["month"] = m["period"] % 100
    m.sort_values(["code", "period"]).to_csv(ROOT / "data" / "bop_monthly.csv", index=False)
    q = load("bop_digital_by_region_quarterly_2014_2026.json")
    q["year"] = q["period"] // 100; q["quarter"] = q["period"] % 100
    q.sort_values(["code", "period"]).to_csv(ROOT / "data" / "bop_quarterly_region.csv", index=False)
    f = load("boj_usdjpy_monthly.json")
    f["year"] = f["period"] // 100
    f.sort_values("period").to_csv(ROOT / "data" / "usdjpy_monthly.csv", index=False)
    print(len(m), len(q), len(f), sorted(q["quarter"].unique()))


if __name__ == "__main__":
    main()
