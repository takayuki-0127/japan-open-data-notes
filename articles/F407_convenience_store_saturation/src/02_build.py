"""data/raw の4ファイルから、分析に使う表を data/ に作る（オフライン）。"""
import pathlib
import numpy as np
import pandas as pd
import openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"

NAT_COLS = ["total", "goods", "ff_daily", "processed", "nonfood", "service", "stores"]
NOTE_NAT = ["合計", "商品販売額", "FF･日配食品", "加工食品", "非食品", "サービス売上高", "店舗数"]
REGIONS = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]
REG_EN = ["hokkaido", "tohoku", "kanto", "chubu", "kinki", "chugoku", "shikoku", "kyushu_okinawa"]


def num(x):
    if x is None:
        return np.nan
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return np.nan


def read_links(wb):
    """注2 のリンク係数（2012-01, 2017-01, 2021-03）。空欄は1。"""
    ws = wb["注2"]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    links = {}
    i = 0
    while i < len(rows):
        r = rows[i]
        if len(r) > 4 and r[3] == "年月" and r[4] == "合計":
            head = r[4:27]
            val = rows[i + 1][4:27]
            ym = {0: "2012-01", 1: "2017-01", 2: "2021-03"}[len(links)]
            links[ym] = {h: (num(v) if num(v) == num(v) else 1.0) for h, v in zip(head, val)}
            i += 2
        else:
            i += 1
    return links


def main():
    wb = openpyxl.load_workbook(RAW / "meti_cvs_timeseries.xlsx", read_only=True, data_only=True)
    links = read_links(wb)
    lk = []
    for ym, d in links.items():
        for k, v in d.items():
            lk.append({"link_month": ym, "column": k, "coef": v})
    pd.DataFrame(lk).to_csv(OUT / "link_coefficients.csv", index=False)

    # 全国 月次
    ws = wb["販売額(value)月次(Monthly)"]
    rec = []
    for r in ws.iter_rows(min_row=9, values_only=True):
        code = r[1]
        if code is None or not str(code).strip().isdigit():
            continue
        y, m = int(str(code)[:4]), int(str(code)[6:8])
        rec.append([y, m] + [num(v) for v in r[3:10]])
    nat = pd.DataFrame(rec, columns=["year", "month"] + NAT_COLS).dropna(subset=["total"])
    nat["ym"] = nat["year"] * 100 + nat["month"]
    for c, nc in zip(NAT_COLS, NOTE_NAT):
        f = np.ones(len(nat))
        for ym, d in links.items():
            yy, mm = map(int, ym.split("-"))
            f = f * np.where(nat["ym"] < yy * 100 + mm, d[nc], 1.0)
        nat[c + "_link"] = nat[c] * f
    nat = nat.drop(columns="ym").sort_values(["year", "month"]).reset_index(drop=True)
    nat.to_csv(OUT / "national_monthly.csv", index=False, float_format="%.4f")

    # 経済産業局別 月次（九州＋沖縄 を使う）
    ws = wb["局別販売額(月次)"]
    rec = []
    for r in ws.iter_rows(min_row=11, values_only=True):
        code = r[1]
        if code is None or not str(code).strip().isdigit():
            continue
        y, m = int(str(code)[:4]), int(str(code)[6:8])
        vals = [num(v) for v in r[3:19]]
        for j, (rj, re_) in enumerate(zip(REGIONS, REG_EN)):
            rec.append([y, m, re_, rj, vals[2 * j], vals[2 * j + 1]])
    reg = pd.DataFrame(rec, columns=["year", "month", "region", "region_ja", "sales", "stores"]).dropna(subset=["stores"])
    ym = reg["year"] * 100 + reg["month"]
    for col, suf in [("sales", ""), ("stores", "店舗数")]:
        f = np.ones(len(reg))
        for lm, d in links.items():
            yy, mm = map(int, lm.split("-"))
            co = reg["region_ja"].map(lambda x: d.get(x + suf, 1.0)).to_numpy()
            f = f * np.where(ym < yy * 100 + mm, co, 1.0)
        reg[col + "_link"] = reg[col] * f
    reg = reg.sort_values(["region", "year", "month"], key=lambda s: s.map({e: i for i, e in enumerate(REG_EN)}) if s.name == "region" else s).reset_index(drop=True)
    reg.to_csv(OUT / "region_monthly.csv", index=False, float_format="%.4f")

    # 物価（総合・食料、暦年の年平均）を 2025=100 に
    # レビュー（2026-11-18）で、年度平均の表（cpi_item_annual.csv）から暦年の表に替えた
    cpi = pd.read_csv(RAW / "cpi_annual_middle_class.csv", encoding="cp932", header=None, dtype=str)
    head = [str(x).strip() for x in cpi.iloc[0]]
    assert head[1] == "総合" and head[7] == "食料", head[:8]
    body = cpi.iloc[6:, [0, 1, 7]].copy()
    body.columns = ["year", "cpi_all", "cpi_food"]
    body = body[body["year"].str.strip().str.isdigit()]
    body["year"] = body["year"].astype(int)
    for c in ["cpi_all", "cpi_food"]:
        body[c] = body[c].astype(float)
        body[c] = body[c] / body.loc[body["year"] == 2025, c].iloc[0] * 100
    body.to_csv(OUT / "cpi_annual.csv", index=False, float_format="%.4f")

    # 人口（都道府県 → 経済産業局の区域）
    pref_to_reg = {}
    for code in range(1, 48):
        if code == 1: r = "hokkaido"
        elif code <= 7: r = "tohoku"
        elif code in (8, 9, 10, 11, 12, 13, 14, 15, 19, 20, 22): r = "kanto"
        elif code in (16, 17, 21, 23, 24): r = "chubu"
        elif code in (18, 25, 26, 27, 28, 29, 30): r = "kinki"
        elif code <= 35: r = "chugoku"
        elif code <= 39: r = "shikoku"
        else: r = "kyushu_okinawa"
        pref_to_reg[code] = r
    pop = {}
    wb1 = openpyxl.load_workbook(RAW / "pop_pref_2000_2020.xlsx", read_only=True, data_only=True)
    for sheet in ["総人口（2000年～2015年）", "総人口 (2015年～2020年)"]:
        rows = [list(r) for r in wb1[sheet].iter_rows(values_only=True)]
        years = []
        for x in rows[8][4:]:
            if x is None:
                years.append(None)
            else:
                s = str(x).replace("年", "").strip()
                years.append(int(s) if s.isdigit() else None)
        for r in rows[11:]:
            if r[1] is None or not str(r[1]).strip().isdigit():
                continue
            pc = int(r[1])
            for yv, v in zip(years, r[4:]):
                if yv is not None and num(v) == num(v):
                    pop[(pc, yv)] = num(v)
    wb2 = openpyxl.load_workbook(RAW / "pop_pref_2020_2024.xlsx", read_only=True, data_only=True)
    rows = [list(r) for r in wb2.worksheets[0].iter_rows(values_only=True)]
    hdr = rows[6]
    ycols = [(j, int(str(h).replace("年", ""))) for j, h in enumerate(hdr) if h is not None and str(h).endswith("年") and str(h)[:4].isdigit()]
    for r in rows[7:]:
        if r[7] != "総人口" or r[8] != "男女計" or r[9] is None:
            continue
        pc = int(str(r[9])[:2])
        if pc == 0:
            continue
        for j, yv in ycols:
            if num(r[j]) == num(r[j]):
                pop[(pc, yv)] = num(r[j])
    pp = pd.DataFrame([{"pref": k[0], "year": k[1], "pop_thousand": v} for k, v in sorted(pop.items())])
    pp["region"] = pp["pref"].map(pref_to_reg)
    rp = pp.groupby(["region", "year"], sort=False)["pop_thousand"].sum().reset_index()
    rp["order"] = rp["region"].map({e: i for i, e in enumerate(REG_EN)})
    rp = rp.sort_values(["order", "year"]).drop(columns="order").reset_index(drop=True)
    rp.to_csv(OUT / "region_population.csv", index=False, float_format="%.1f")
    print("national", nat.shape, "region", reg.shape, "pop", rp.shape, "links", list(links))


if __name__ == "__main__":
    main()
