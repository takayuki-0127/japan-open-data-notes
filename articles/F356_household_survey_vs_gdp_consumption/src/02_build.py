"""data/raw から data/annual.csv を作る（オフライン）。
家計調査（二人以上：月平均の円、実質増減率%／総世帯：年額の円、世帯人員）、GDP（10億円）、国勢調査の一般世帯数・人員（5年ごと→間は一定の率で補う）。"""
import pathlib, io, csv, re
import numpy as np
import pandas as pd
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except (TypeError, ValueError):
        return np.nan


def label(d, i):
    return "".join(str(v).strip() for v in d.iloc[i, 7:15].tolist() if str(v) != "nan" and not str(v).strip().replace(".", "").isdigit())


def two_plus():
    out = {}
    for sh, key in [("支出金額（年）", "tp_cons_month"), ("実質増減率（年）", "tp_real_growth")]:
        d = pd.read_excel(RAW / "kakei_two_plus_usage_monthly_2000_2026.xlsx", sheet_name=sh, header=None)
        i = [i for i in range(12, len(d)) if label(d, i) == "消費支出"][0]
        for c in range(15, d.shape[1]):
            y = str(d.iat[9, c])
            if y.endswith("年"):
                out.setdefault(int(y[:4]), {})[key] = num(d.iat[i, c])
    return out


def total_households():
    txt = (RAW / "kakei_total_households_items_2000_2025.csv").read_bytes().decode("cp932")
    d = pd.read_csv(io.StringIO(txt), header=None, dtype=str)
    years = [int(str(v).replace("年", "")) for v in d.iloc[1, 6:].tolist() if str(v).endswith("年")]
    out = {}
    for i in range(2, len(d)):
        name = str(d.iat[i, 5]).strip()
        key = {"消費支出": "th_cons_year", "世帯人員(人)": "th_persons"}.get(name)
        if key:
            for k, y in enumerate(years):
                out.setdefault(y, {}).setdefault(key, num(d.iat[i, 6 + k]))
    return out


def gdp():
    out = {}
    for f, kind in [("esri_qe2026q2_2nd_gaku-mcy2622.csv", "nom"), ("esri_qe2026q2_2nd_gaku-jcy2622.csv", "real")]:
        rows = list(csv.reader(io.StringIO((RAW / f).read_bytes().decode("cp932"))))
        c_hh = [i for i, h in enumerate(rows[3]) if h.strip() == "家計最終消費支出"][0]
        c_ex = [i for i, h in enumerate(rows[4]) if h.strip() == "除く持ち家の帰属家賃"][0]
        for r in rows:
            if r and r[0].endswith("/1-12."):
                y = int(r[0][:4])
                out.setdefault(y, {}).update({f"gdp_hh_{kind}": num(r[c_hh]), f"gdp_hh_exrent_{kind}": num(r[c_ex])})
    return out


def census():
    ws = openpyxl.load_workbook(str(RAW / "census_ts_households_t1_1960_2020_000001086170.xlsx"), read_only=True).worksheets[0]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    hdr = rows[5]
    starts = [(j, int(str(x)[:4])) for j, x in enumerate(hdr) if x and re.fullmatch(r"\d{4}年", str(x))]
    out = {}
    for r in rows[9:]:
        a = str(r[0]) if r[0] else ""
        if a.startswith("00000_"):
            for j, y in starts:
                out[y] = dict(gen_h=num(r[j + 2]), gen_p=num(r[j + 3]))
            break
    for key, name in [("gen_h", "census_2025_t12-1_households_000040506465.xlsx"), ("gen_p", "census_2025_t12-2_members_000040506466.xlsx")]:
        ws = openpyxl.load_workbook(str(RAW / name), read_only=True).worksheets[0]
        for r in ws.iter_rows(min_row=11, values_only=True):
            if r[0] == "a" and r[2] == "0_総数" and r[3] == "0_総数" and r[4] == "00_総数" and str(r[1]).startswith("00000_"):
                out.setdefault(2025, {})[key] = float(r[5])
                break
    return out


def interp(points, years, how="geo"):
    ys = sorted(points)
    res = {}
    for y in years:
        lo = max([p for p in ys if p <= y]); hi = min([p for p in ys if p >= y])
        if lo == hi:
            res[y] = points[lo]
        else:
            f = (y - lo) / (hi - lo)
            res[y] = points[lo] * (points[hi] / points[lo]) ** f if how == "geo" else points[lo] + f * (points[hi] - points[lo])
    return res


def main():
    t = two_plus(); h = total_households(); g = gdp(); c = census()
    years = list(range(2000, 2026))
    cz = {y: v for y, v in c.items() if y >= 2000}
    hh = interp({y: v["gen_h"] for y, v in cz.items()}, years); pp = interp({y: v["gen_p"] for y, v in cz.items()}, years)
    hh_lin = interp({y: v["gen_h"] for y, v in cz.items()}, years, "lin")
    rows = []
    for y in years:
        rows.append(dict(year=y, **t.get(y, {}), **h.get(y, {}), **g.get(y, {}), households=hh[y], persons=pp[y], households_linear=hh_lin[y],
                         census_year=y in cz))
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "data" / "annual.csv", index=False)
    print(df.iloc[[0, 10, 20, 25]].T.to_string())


if __name__ == "__main__":
    main()
