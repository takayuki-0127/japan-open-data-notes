"""data/raw から年度のパネル（data/fy_panel.csv）と、労務の重み（data/labor_weights.csv）を作る。"""
import json, pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
CGPI = {"PRCG20_2200000000": "cgpi_all", "PRCG20_2200320001": "wood", "PRCG20_2200620001": "petro", "PRCG20_2200720001": "plastic",
        "PRCG20_2200820001": "ceramic", "PRCG20_2200920001": "steel", "PRCG20_2201020001": "nonferrous", "PRCG20_2201120001": "metalprod"}
DEFL = {"住宅総合/住宅総合/住宅総合/住宅総合": "d_housing", "住宅総合/木造住宅W/木造住宅W/木造住宅W": "d_wood_house",
        "住宅総合/非木造住宅/非木造住宅/非木造住宅": "d_nonwood_house", "非住宅総合/非住宅総合/非住宅総合/非住宅総合": "d_nonres",
        "建築補修/建築補修/建築補修/建築補修": "d_repair"}


def num(v):
    return pd.to_numeric(str(v).replace(",", "").strip(), errors="coerce")


def maikin_fy(path):
    d = pd.read_excel(path, header=None, sheet_name="D")  # D = 建設業
    rows, last = [], 0
    for i in range(9, len(d)):
        y = num(d.iloc[i, 0])
        if pd.isna(y):
            continue
        y = int(y)
        if y < last:
            break  # 指数のブロックの終わり（下は増減率）
        last = y
        rows.append([y] + [num(d.iloc[i, c]) for c in (4, 5, 6, 7)])
    q = pd.DataFrame(rows, columns=["year", "q1", "q2", "q3", "q4"]).set_index("year")
    fy = {}
    for y in q.index:
        if y + 1 in q.index:
            v = [q.loc[y, "q2"], q.loc[y, "q3"], q.loc[y, "q4"], q.loc[y + 1, "q1"]]
            if not any(pd.isna(v)):
                fy[y] = float(np.mean(v))
    return pd.Series(fy)


def main():
    # デフレーター
    d = pd.read_excel(RAW / "deflator_fy2020base.xlsx", header=None)
    hdr = ["/".join(str(d.iloc[i, j]) for i in range(4, 8)) for j in range(d.shape[1])]
    cols = {DEFL[h]: j for j, h in enumerate(hdr) if h in DEFL}
    assert len(cols) == len(DEFL), cols
    rows = []
    for i in range(8, len(d)):
        m = re.match(r"^(\d{4})(年度|$)", str(d.iloc[i, 0]).replace(".0", ""))
        if m:
            rows.append(dict(fy=int(m.group(1)), **{k: num(d.iloc[i, j]) for k, j in cols.items()}))
    panel = pd.DataFrame(rows).set_index("fy")

    # 賃金・労働時間（建設業）
    panel["wage"] = maikin_fy(RAW / "maikin_wage_index.xls")
    panel["hours"] = maikin_fy(RAW / "maikin_hours_index.xls")
    panel["wage_hourly"] = 100 * panel.wage / panel.hours

    # 企業物価（月次→年度平均、4月〜翌3月）
    js = json.loads((RAW / "boj_cgpi2020_monthly.json").read_text(encoding="utf-8"))
    for r in js["RESULTSET"]:
        s = pd.Series(r["VALUES"]["VALUES"], index=r["VALUES"]["SURVEY_DATES"], dtype=float)
        ym = pd.DataFrame({"v": s.values, "y": s.index // 100, "m": s.index % 100})
        ym["fy"] = np.where(ym.m >= 4, ym.y, ym.y - 1)
        g = ym.dropna().groupby("fy").v.agg(["mean", "count"])
        panel[CGPI[r["SERIES_CODE"]]] = g.loc[g["count"] == 12, "mean"]
        # 半年前にずらした年度（前年10月〜当年9月）の平均：頑健性用
        ym["fy6"] = np.where(ym.m >= 10, ym.y + 1, ym.y)
        g6 = ym.dropna().groupby("fy6").v.agg(["mean", "count"])
        panel[CGPI[r["SERIES_CODE"]] + "_lag6"] = g6.loc[g6["count"] == 12, "mean"]
    panel = panel.loc[1980:2025].round(4)
    panel.to_csv(DATA / "fy_panel.csv")

    # 労務の重み（平成23年度基準のウエイト表、賃金・俸給＋社会保険料の行）
    w = pd.read_excel(RAW / "deflator_weights_2011base.xlsx", header=None)
    lab = [i for i in range(len(w)) if "賃金" in str(w.iloc[i, 2])][0]
    tot = [i for i in range(len(w)) if num(w.iloc[i, 3]) and num(w.iloc[i, 3]) > 99990][0]
    out = []
    for j in range(3, 13):
        name = re.sub(r"[\s　\n]", "", str(w.iloc[0, j]))
        out.append(dict(deflator=name, labor_weight=round(num(w.iloc[lab, j]) / num(w.iloc[tot, j]), 5)))
    pd.DataFrame(out).to_csv(DATA / "labor_weights.csv", index=False)
    print(panel.loc[[1990, 2000, 2013, 2019, 2020, 2025]].to_string())
    print(pd.DataFrame(out))


if __name__ == "__main__":
    main()
