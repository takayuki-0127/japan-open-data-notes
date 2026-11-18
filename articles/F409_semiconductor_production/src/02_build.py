"""data/raw の元ファイルから、分析に使う CSV を作る（オフライン）。"""
import csv, io, pathlib
import numpy as np
import openpyxl
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, D = ROOT / "data" / "raw", ROOT / "data"

GYO = {1000000000: "mining_mfg", 1105000000: "ecd", 1105001000: "ic", 1103006000: "equip"}
ITEMS = {1105001010: "ic_linear", 1105001020: "ic_mcu", 1105001030: "ic_logic", 1105001040: "ic_memory",
         1105001050: "ic_mos_other", 1105001060: "ic_hybrid", 1103006010: "equip_semi", 1105005010: "si_wafer"}
SHEETS = {"生産": "prod", "出荷": "ship", "在庫": "inv"}


def read_iip(path, codes):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = []
    for sh, var in SHEETS.items():
        rows = list(wb[sh].iter_rows(values_only=True))
        head = rows[2]
        months = [(j, int(h)) for j, h in enumerate(head) if isinstance(h, int) and h > 190000]
        for r in rows[3:]:
            if r[0] in codes:
                for j, ym in months:
                    v = r[j]
                    out.append({"series": codes[r[0]], "var": var, "ym": ym, "weight": r[2],
                                "value": float(v) if isinstance(v, (int, float)) else np.nan})
    return pd.DataFrame(out)


def ym_to_date(ym):
    return pd.to_datetime(ym.astype(str), format="%Y%m")


def build_iip():
    a = read_iip(RAW / "iip2020_gyoshu_sa.xlsx", GYO)
    b = read_iip(RAW / "iip2015_gyoshu_sa.xlsx", GYO)
    a["base"], b["base"] = 2020, 2015
    df = pd.concat([a, b], ignore_index=True)
    df["date"] = ym_to_date(df["ym"])
    df.to_csv(D / "iip_gyoshu_long.csv", index=False)
    it = read_iip(RAW / "iip2020_hinmoku_sa.xlsx", ITEMS)
    it = it[it["var"] == "prod"].copy()
    it["date"] = ym_to_date(it["ym"])
    it.sort_values(["series", "ym"]).to_csv(D / "iip_items_prod.csv", index=False)


def num(s):
    s = (s or "").strip().replace(",", "")
    try:
        return float(s)
    except ValueError:
        return np.nan


def read_customs(path, cols):
    rows = list(csv.reader(io.open(path, encoding="cp932")))
    head, kind = rows[2], rows[5]
    out = []
    for r in rows[6:]:
        if len(r) < 2 or not r[0][:4].isdigit() or "/" not in r[0]:
            continue
        y, m = r[0].split("/")
        rec = {"ym": int(y) * 100 + int(m)}
        for name, (col, label) in cols.items():
            assert head[col].strip() == label, (head[col], label)
            vc = col if kind[col].strip() == "金額" else col + 1  # 品目は「数量」「金額」の2列。金額の列を使う
            assert kind[vc].strip() == "金額"
            rec[name] = num(r[vc])
        out.append(rec)
    return pd.DataFrame(out)


def build_trade():
    ex = read_customs(RAW / "customs_export_monthly.csv",
                      {"ex_total": (1, "総額"), "ex_elec_parts": (66, "半導体等電子部品"), "ex_ic": (68, "（ＩＣ）"), "ex_equip": (48, "半導体等製造装置")})
    im = read_customs(RAW / "customs_import_monthly.csv",
                      {"im_total": (1, "総額"), "im_elec_parts": (78, "半導体等電子部品"), "im_ic": (80, "(ＩＣ)")})
    t = ex.merge(im, on="ym", how="outer").sort_values("ym")
    t = t.dropna(subset=["ex_total"])
    t.to_csv(D / "trade_monthly.csv", index=False)


def build_price():
    raw = (RAW / "boj_price_ic.csv").read_bytes().decode("cp932")
    lines = raw.splitlines()
    k = next(i for i, l in enumerate(lines) if l.startswith("SERIES_CODE,"))
    p = pd.read_csv(io.StringIO("\n".join(lines[k:])), dtype={"SURVEY_DATES": int})
    p["VALUES"] = pd.to_numeric(p["VALUES"], errors="coerce")
    w = p.pivot_table(index="SURVEY_DATES", columns="SERIES_CODE", values="VALUES", aggfunc="first").sort_index()
    out = pd.DataFrame(index=w.index)
    pairs = {"px_ic_yen": ("PRCG15_2400540003", "PRCG20_2400540002"), "px_ic_contract": ("PRCG15_2300540003", "PRCG20_2300540002"),
             "px_mem_contract": ("PRCG15_2300550005", "PRCG20_2300550006"), "pm_ic_yen": ("PRCG15_2600840003", "PRCG20_2600840002")}
    for name, (c15, c20) in pairs.items():
        s15, s20 = w[c15], w[c20]
        yrs = (w.index // 100)
        ratio = s20[yrs == 2020].mean() / s15[yrs == 2020].mean()  # 2020年の平均でつなぐ
        out[name] = s20.where(s20.notna(), s15 * ratio)
        out.loc[(yrs >= 2020) & s20.isna(), name] = np.nan
    out["ppi_ic"] = w["PRCG20_2201550005"]
    out.index.name = "ym"
    out = out[out.index >= 201501]
    out.round(6).to_csv(D / "price_monthly.csv")


if __name__ == "__main__":
    build_iip(); build_trade(); build_price()
    print("ok")
