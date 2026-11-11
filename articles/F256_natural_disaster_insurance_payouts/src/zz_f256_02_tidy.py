"""02 整形：PDF・Excel・CSV から分析用の表を作る。

出力 data/processed/
  events.csv     2012〜2025年度に協会が調査した事故ごとの件数・保険金（千円）
  top10.csv      協会「過去の主な風水災等」上位10事故（億円・件）
  deflator.csv   年度別 物価（建設工事費デフレーター住宅総合・建設総合、CPI総合・持家の帰属家賃を除く総合、2020年度=100）
  dwellings.csv  住宅数（住宅・土地統計調査、全国、各10月1日）
"""
import csv, json, re, subprocess, pathlib, io
import pandas as pd, openpyxl, pdfplumber

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
COLS = ["veh_n", "veh_k", "fire_n", "fire_k", "misc_n", "misc_k", "tot_n", "tot_k"]

# 画像で作られていて文字が取れないPDF（2件）と、合計行がない1県だけのPDF（1件）は、
# PDF を目で読んで入れた。各行とも「車両+火災+新種=合計」が件数・金額とも一致する（金額は丸めで±2千円まで）ことを下で確かめる。
MANUAL = {
    "2021_01": [3423, 3815136, 16166, 35567572, 2029, 3498280, 21618, 42880988],
    "2021_02": [1557, 1670077, 5376, 6502377, 726, 1391590, 7659, 9564044],
    "2016_w02": [15, 10984, 127, 1261140, 0, 0, 142, 1272124],  # 糸魚川の大火（新種の欄がない表。自然災害でないので分析から除く）
    "2014_w02": [1730, 1424536, 1589, 3793575, 131, 134043, 3450, 5352154],  # 広島県のみの表
}

def nums(s):
    return [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", s)]

def total_rows(path):
    t = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True).stdout
    rows = [nums(l) for l in t.splitlines() if re.match(r"^\s*合\s*計", l)]
    rows = [r for r in rows if len(r) in (2, 8)]
    if not any(len(r) == 8 for r in rows):  # フォント埋め込みが壊れたPDFは pdfplumber で読む
        with pdfplumber.open(path) as p:
            t = "\n".join(pg.extract_text() or "" for pg in p.pages)
        rows = [nums(l) for l in t.splitlines() if re.match(r"^\s*合\s*計", l)]
        rows = [r for r in rows if len(r) in (2, 8)]
    return rows

meta = pd.read_csv(ROOT / "data" / "events_meta.csv", dtype=str)
recs = []
for _, m in meta.iterrows():
    rows = total_rows(RAW / "giaj_events" / f"{m.file}.pdf")
    main = [r for r in rows if len(r) == 8]
    marine = [r for r in rows if len(r) == 2]
    if m.file in MANUAL:
        v, src = MANUAL[m.file], "目視"
    else:
        v, src = main[0], "PDF文字"
    d = dict(zip(COLS, v))
    d["marine_n"], d["marine_k"] = (marine[0] if marine else (0, 0))
    d.update(file=m.file, title=m.title, event_ym=m.event_ym, peril=m.peril, natural=int(m.natural), read_by=src)
    assert d["veh_n"] + d["fire_n"] + d["misc_n"] == d["tot_n"], m.file
    assert abs(d["veh_k"] + d["fire_k"] + d["misc_k"] - d["tot_k"]) <= 2, m.file  # 元表の千円未満の丸めで1千円ずれる表がある
    recs.append(d)
ev = pd.DataFrame(recs)
y, mo = ev.event_ym.str[:4].astype(int), ev.event_ym.str[5:7].astype(int)
ev["fy"] = y - (mo <= 3)
ev["all_n"] = ev.tot_n + ev.marine_n
ev["all_k"] = ev.tot_k + ev.marine_k
ev.to_csv(OUT / "events.csv", index=False)
print(ev[["file", "fy", "peril", "all_n", "all_k", "read_by"]].to_string())

# 上位10事故（PDFの表を文字で読み、数字は千万円単位で四捨五入された億円）
t = subprocess.run(["pdftotext", "-layout", str(RAW / "giaj_fusuigai_top10.pdf"), "-"], capture_output=True, text=True).stdout
names = {1: ("平成30年台風21号", "2018-09"), 2: ("令和元年台風19号", "2019-10"), 3: ("平成3年台風19号", "1991-09"),
         4: ("令和元年台風15号", "2019-09"), 5: ("平成16年台風18号", "2004-09"), 6: ("平成26年2月雪害", "2014-02"),
         7: ("平成11年台風18号", "1999-09"), 8: ("平成30年台風24号", "2018-09"), 9: ("平成30年7月豪雨", "2018-06"),
         10: ("平成27年台風15号", "2015-08")}
top = []
for l in t.splitlines():
    m = re.match(r"^\s*(\d{1,2})\s+.*?([\d,]{5,})\s+([\d,]+)\s+([\d,]+)\s+([\d,]+|－)\s+([\d,]+)\s*$", l)
    if m and int(m.group(1)) in names:
        r = int(m.group(1)); n, ym = names[r]
        mar = 0 if m.group(5) == "－" else int(m.group(5).replace(",", ""))
        top.append(dict(rank=r, name=n, event_ym=ym, n=int(m.group(2).replace(",", "")),
                        fire_oku=int(m.group(3).replace(",", "")), auto_oku=int(m.group(4).replace(",", "")),
                        marine_oku=mar, tot_oku=int(m.group(6).replace(",", ""))))
top = pd.DataFrame(top).sort_values("rank")
assert len(top) == 10, top
y, mo = top.event_ym.str[:4].astype(int), top.event_ym.str[5:7].astype(int)
top["fy"] = y - (mo <= 3)
top.to_csv(OUT / "top10.csv", index=False)
print(top.to_string())

# 物価：建設工事費デフレーター（年度）
ws = openpyxl.load_workbook(RAW / "mlit_deflator_nendo.xlsx", data_only=True).active
hdr = [c.value for c in ws[10]]
dfl = []
for r in ws.iter_rows(min_row=11, values_only=True):
    m = re.match(r"^(\d{4})", str(r[0]))  # 2018年度以降は「2018年度」「2024年度（暫定）」のような文字列
    if m and isinstance(r[3], (int, float)):
        dfl.append(dict(fy=int(m.group(1)), defl_const=r[1], defl_house=r[3], provisional="暫定" in str(r[0])))
dfl = pd.DataFrame(dfl)
assert hdr[1] == "建設総合" and hdr[3] == "住宅総合"
# CPI 年度平均（4月〜翌3月）
cpi = pd.read_csv(RAW / "cpi_monthly_from_F101.csv", parse_dates=["month"])
cpi["fy"] = cpi.month.dt.year - (cpi.month.dt.month <= 3)
c = cpi.groupby("fy").agg(n=("cpi_all", "size"), cpi_all=("cpi_all", "mean"), cpi_ex_rent=("cpi_ex_rent", "mean"))
c = c[c.n == 12].drop(columns="n").reset_index()
pr = dfl.merge(c, on="fy", how="left")
for k in ["defl_const", "defl_house", "cpi_all", "cpi_ex_rent"]:
    pr[k] = pr[k] / pr.loc[pr.fy == 2020, k].iloc[0] * 100
pr.to_csv(OUT / "deflator.csv", index=False)
print(pr[pr.fy.isin([1991, 1999, 2004, 2012, 2018, 2020, 2024, 2025])].round(1).to_string())

# 住宅数（住宅・土地統計調査 第3表 全国）
txt = json.load(open(RAW / "hlts_timeseries_from_F127.json"))["t3__003"]
rows = list(csv.reader(io.StringIO(txt)))
yrs = next(r for r in rows if "1958" in r)
i0 = yrs.index("1958")
# 「全国」は2行ある（1973年以降の現行の行と、1)注つきの1968年までの行）。1973年以降の行を使う
nat = [r for r in rows if r[1].strip() == "全国"]
years = [int(x) for x in yrs[i0:i0 + 14]]
vals = [next((int(r[i0 + j]) for r in nat if r[i0 + j].strip().isdigit()), None) for j in range(14)]
dw = pd.DataFrame(dict(year=years, dwellings=vals))
dw = dw[dw.year >= 1973]
dw.to_csv(OUT / "dwellings.csv", index=False)
print(dw.to_string())
