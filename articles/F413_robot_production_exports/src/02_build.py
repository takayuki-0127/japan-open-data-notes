"""産業用ロボットの生産（生産動態統計）と輸出（貿易統計）を、年と国の表にする。"""
import datetime as dt
import html, pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, OUT = ROOT / "data" / "raw", ROOT / "data"


def norm(x):
    return re.sub(r"[\s　]", "", str(x))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan  # 「x」（秘匿）や「…」


# 旧様式（機械統計の時系列表その１、シート「08」）
OLD = ["mach2012_ts1.xls", "mach2017_ts1.xls", "mach2020_ts1.xls"]
LABELS = {"産業用ロボット": "value_total", "シーケンスロボット": "seq", "プレイバックロボット": "playback",
          "数値制御ロボット": "nc", "知能ロボット": "intelligent", "部品・付帯装置": "parts"}


def year_of(row):
    for v in row[:4]:
        if isinstance(v, (dt.datetime, pd.Timestamp)) and v.month == 1:
            return v.year
        m = re.search(r"\((\d{4})CY\)", str(v))
        if m:
            return int(m.group(1))
    return None


def parse_old():
    rec = []
    for fname in OLD:
        d = pd.read_excel(RAW / fname, "08", header=None)
        pos = {}
        for i in range(0, 7):
            for j in range(80, d.shape[1]):
                v = norm(d.iat[i, j])
                for lab, key in LABELS.items():
                    if v == lab and key not in pos:
                        pos[key] = j
        assert len(pos) == 6, (fname, pos)
        for i in range(8, 20):
            y = year_of(list(d.iloc[i]))
            if y is None:
                continue
            row = d.iloc[i]
            r = {"source": fname, "year": y, "value_total": num(row[pos["value_total"]]), "parts_value": num(row[pos["parts"]])}
            for k in ["seq", "playback", "nc", "intelligent"]:
                r[f"{k}_qty"] = num(row[pos[k]]); r[f"{k}_value"] = num(row[pos[k] + 1])
            rec.append(r)
    return pd.DataFrame(rec)


def parse_new():
    rec = []
    items = {"シーケンスロボット": "seq", "知能ロボット": "intelligent", "シーケンスロボット・知能ロボット": "seqint",
             "プレイバックロボット": "playback", "数値制御ロボット": "nc", "産業用ロボット部品・付帯装置": "parts",
             "産業用ロボット計": "total"}
    must = {"playback_qty", "playback_value", "nc_qty", "nc_value", "parts_value"}
    for y in range(2021, 2026):
        fname = f"nenpo{y}.xlsx"
        d = pd.read_excel(RAW / fname, "実数表", header=None, dtype=object)
        hdr = [str(x) for x in d.iloc[1].tolist()]
        if f"{y}年(CY)" in hdr:
            cols = [hdr.index(f"{y}年(CY)")]
        else:
            cols = [k for k, h in enumerate(hdr) if re.fullmatch(rf"{y}(0[1-9]|1[0-2])", h)]
            assert len(cols) == 12
        b = d.iloc[2:]
        b = b[b[0].astype(str).str.strip() == "2080"]
        r = {"source": fname, "year": y}
        for hin, key in items.items():
            for item, suf in [("生産数量", "qty"), ("生産金額", "value")]:
                z = b[(b[5].astype(str).str.strip() == hin) & (b[6].astype(str).str.strip() == item)]
                if len(z) == 0:
                    continue
                vals = [num(v) for v in z.iloc[0, cols]]
                r[f"{key}_{suf}"] = float(sum(vals))  # 秘匿（X）が1か月でもあれば NaN
        assert all(k in r and not np.isnan(r[k]) for k in must), (fname, r)
        if "total_value" in r and not np.isnan(r["total_value"]):
            r["value_total"] = r.pop("total_value")  # 年報に「産業用ロボット計」の行がある年（2021年版）
        else:
            other = r.get("seqint_value", np.nan)
            assert not np.isnan(other), (fname, "シーケンス・知能の金額が秘匿")
            r["value_total"] = other + r["playback_value"] + r["nc_value"] + r["parts_value"]
        r.pop("total_value", None)
        rec.append(r)
    return pd.DataFrame(rec)


def parse_country():
    t = (RAW / "customs_country_code_e.htm").read_bytes().decode("utf-8", "ignore")
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    t = re.sub(r"\s+", " ", t)
    body = t[t.find("Country code Geographical Zone Code Country") + 44:]
    zones = ["Asia", "Middle East", "Central and East Europe, Russia etc.", "Western Europe", "North America",
             "Central and South America", "Africa", "Oceania"]
    pat = re.compile(r"(" + "|".join(re.escape(z) for z in zones) + r")|(\d{3}) ")
    rows, zone, last_end, last_code = [], None, None, None
    for mt in pat.finditer(body):
        if last_code is not None:
            rows.append((last_code, body[last_end:mt.start()].strip(), zone_at_code))
            last_code = None
        if mt.group(1):
            zone = mt.group(1)
        else:
            last_code, last_end, zone_at_code = int(mt.group(2)), mt.end(), zone
        if len(rows) > 300:
            break
    df = pd.DataFrame(rows, columns=["code", "name_en", "zone"]).drop_duplicates("code")
    df["name_en"] = df["name_en"].str.replace(r"\s*Note.*$", "", regex=True)
    return df


def main():
    old, new = parse_old(), parse_new()
    prod_src = pd.concat([old, new], ignore_index=True)
    prod_src.to_csv(OUT / "production_by_source.csv", index=False, float_format="%.1f")
    pri = {"mach2012_ts1.xls": 1, "mach2017_ts1.xls": 2, "mach2020_ts1.xls": 3}
    prod_src["pri"] = prod_src["source"].map(pri).fillna(9)
    prod = prod_src.sort_values(["year", "pri"]).groupby("year").tail(1).drop(columns="pri").set_index("year").sort_index()
    prod.to_csv(OUT / "production_annual.csv", float_format="%.1f")

    ex = pd.read_csv(RAW / "customs_export_robots.csv", dtype=str)
    ex["year"] = ex["Year"].astype(int)
    ex["hs"] = ex["HS"].str.strip("'").str[:6]
    ex["country"] = ex["Country"].astype(int)
    ex["value_kyen"] = ex["Value-Year"].astype(float)
    # 台数：8479.50 は Unit2 が NO（Quantity2）、8428.70 は Unit1 が NO（Quantity1）
    ex["units"] = np.where(ex["Unit2"].str.strip() == "NO", ex["Quantity2-Year"].astype(float),
                           np.where(ex["Unit1"].fillna("").str.strip() == "NO", ex["Quantity1-Year"].astype(float), np.nan))
    cc = parse_country()
    cc.to_csv(OUT / "country_codes.csv", index=False)
    ex = ex.merge(cc, left_on="country", right_on="code", how="left")
    assert ex["name_en"].notna().all(), ex[ex["name_en"].isna()]["country"].unique()
    ex[["year", "hs", "country", "name_en", "zone", "units", "value_kyen"]].sort_values(["year", "hs", "country"]).to_csv(
        OUT / "exports_by_country.csv", index=False, float_format="%.1f")
    # 月別（世界計）
    mon = []
    for (y, hs), z in ex.groupby(["year", "hs"], sort=True):
        for k, mname in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1):
            mon.append({"year": y, "month": k, "hs": hs, "value_kyen": z[f"Value-{mname}"].astype(float).sum()})
    pd.DataFrame(mon).to_csv(OUT / "exports_monthly.csv", index=False, float_format="%.1f")
    print(prod[["value_total", "parts_value", "playback_qty", "nc_qty"]].to_string())
    print(ex.groupby(["year", "hs"])["value_kyen"].sum().unstack() / 1e5)


if __name__ == "__main__":
    main()
