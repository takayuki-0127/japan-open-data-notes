"""data/raw から、短観の DI と GDP の前期比（最新・1次速報）の四半期の表を作る（オフライン）。"""
import pathlib, io, csv, json, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
QMAP = {"1- 3.": 1, "4- 6.": 2, "7- 9.": 3, "10-12.": 4}


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except ValueError:
        return np.nan


def parse_ritu(path):
    """前期比の表のいちばん上の四半期の並びだけを読む（GDP は2列目）。"""
    rows = list(csv.reader(io.StringIO(path.read_bytes().decode("cp932", "ignore"))))
    out = {}
    year = None
    started = False
    for r in rows:
        if not r:
            continue
        lab = r[0].strip()
        m = re.match(r"^(\d{4})/\s*(\d{1,2}-\s*\d{1,2}\.)$", lab)
        if m:
            year = int(m.group(1)); qlab = m.group(2).replace(" ", "")
        elif re.match(r"^\d{1,2}-\s*\d{1,2}\.$", lab) and year is not None:
            qlab = lab.replace(" ", "")
        else:
            if started and lab:
                break
            continue
        qlab = {"1-3.": "1- 3.", "4-6.": "4- 6.", "7-9.": "7- 9.", "10-12.": "10-12."}.get(qlab, qlab)
        q = QMAP.get(qlab)
        if q is None:
            continue
        key = (year, q)
        if key in out:
            break
        started = True
        out[key] = num(r[1]) if len(r) > 1 else np.nan
    return out


def main():
    latest = parse_ritu(RAW / "gdp_latest_ritu-jk2622.csv")
    g = pd.DataFrame([{"year": y, "q": q, "gdp_latest": v} for (y, q), v in latest.items()])
    first = []
    for p in sorted((RAW / "gdp_first").glob("first_*.csv")):
        m = re.match(r"first_(\d{4})Q(\d)\.csv", p.name)
        y, q = int(m.group(1)), int(m.group(2))
        d = parse_ritu(p)
        first.append({"year": y, "q": q, "gdp_first": d.get((y, q), np.nan), "gdp_first_prev": d.get((y - (q == 1), 4 if q == 1 else q - 1), np.nan),
                      "n_rows": len(d)})
    f = pd.DataFrame(first)
    j = json.loads((RAW / "tankan_di.json").read_text(encoding="utf-8"))
    tk = []
    for s in j["RESULTSET"]:
        for d, v in zip(s["VALUES"]["SURVEY_DATES"], s["VALUES"]["VALUES"]):
            tk.append({"code": s["SERIES_CODE"], "name": s["NAME_OF_TIME_SERIES_J"], "year": int(d) // 100, "q": int(d) % 100, "di": v})
    t = pd.DataFrame(tk)
    t.to_csv(ROOT / "data" / "tankan_long.csv", index=False)
    tw = t.pivot_table(index=["year", "q"], columns="code", values="di").reset_index()
    out = g.merge(f, on=["year", "q"], how="left").merge(tw, on=["year", "q"], how="left").sort_values(["year", "q"]).reset_index(drop=True)
    out.to_csv(ROOT / "data" / "panel_quarterly.csv", index=False)
    print(out[["year", "q", "gdp_latest", "gdp_first", "n_rows"]].dropna(subset=["gdp_first"]).head(3))
    print(out[["year", "q", "gdp_latest", "gdp_first"]].tail(3), len(out), f["gdp_first"].isna().sum())


if __name__ == "__main__":
    main()
