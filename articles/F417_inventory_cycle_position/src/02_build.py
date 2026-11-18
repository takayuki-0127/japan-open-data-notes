"""鉱工業指数（業種別・原指数）の四半期・月次を縦長の表に。景気基準日付を月の表に。
出力：data/iip_quarterly.csv、data/iip_monthly.csv、data/cycle_dates.csv"""
import pathlib, re, html
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"
# 2010年基準の業種コードを、2015・2020年基準の名前にそろえる（同じ区分のものだけ）
NAME_FIX = {"化学工業": "化学工業", "輸送機械工業": "輸送機械工業", "電子部品・デバイス工業": "電子部品・デバイス工業"}


def clean_period(v):
    s = str(v).strip().replace("p", "").replace("P", "").strip()
    return s


def read_q(fname, base):
    xl = pd.ExcelFile(RAW / fname)
    out = []
    for sh, ser in [("出荷計", "shipment"), ("在庫計（期末）", "inventory"), ("生産計", "production")]:
        d = xl.parse(sh, header=None, dtype=object)
        hdr = [clean_period(v) for v in d.iloc[2].tolist()]
        qcols = [j for j, h in enumerate(hdr) if re.fullmatch(r"\d{4}Q[1-4]", h)]
        for i in range(3, len(d)):
            code = str(d.iat[i, 0]).strip()
            name = str(d.iat[i, 1]).strip()
            if not re.fullmatch(r"[0-9A-Z]{10}", code):
                continue
            # 業種の段（2010年基準は 2XX0000000、2015・2020年基準は 11xx000000 など）だけ残す
            if not (code[3:] == "0000000" if base == 2010 else code[4:] == "000000"):
                continue
            for j in qcols:
                v = pd.to_numeric(d.iat[i, j], errors="coerce")
                out.append((base, ser, code, name, hdr[j], v))
    return out


def read_m(fname, base):
    xl = pd.ExcelFile(RAW / fname)
    out = []
    for sh, ser in [("出荷", "shipment"), ("在庫", "inventory"), ("生産", "production")]:
        d = xl.parse(sh, header=None, dtype=object)
        hdr = [clean_period(v) for v in d.iloc[2].tolist()]
        mcols = [j for j, h in enumerate(hdr) if re.fullmatch(r"\d{6}", h)]
        for i in range(3, len(d)):
            code = str(d.iat[i, 0]).strip()
            name = str(d.iat[i, 1]).strip()
            if name not in ("鉱工業", "製造工業"):
                continue
            for j in mcols:
                v = pd.to_numeric(d.iat[i, j], errors="coerce")
                out.append((base, ser, code, name, hdr[j], v))
    return out


q = []
q += read_q("iip_b2010_q_gyoshu_gen.xls", 2010)
q += read_q("iip_b2015_q_gyoshu_gen.xlsx", 2015)
q += read_q("iip_b2020_q_gyoshu_gen.xlsx", 2020)
q = pd.DataFrame(q, columns=["base", "series", "code", "name", "period", "value"])
q = q.dropna(subset=["value"]).sort_values(["base", "series", "code", "period"], kind="mergesort")
q.to_csv(OUT / "iip_quarterly.csv", index=False)

m = []
m += read_m("iip_b2010_m_gyoshu_gen.xls", 2010)
m += read_m("iip_b2015_m_gyoshu_gen.xlsx", 2015)
m += read_m("iip_b2020_m_gyoshu_gen.xlsx", 2020)
m = pd.DataFrame(m, columns=["base", "series", "code", "name", "period", "value"])
m = m.dropna(subset=["value"]).sort_values(["base", "series", "code", "period"], kind="mergesort")
m.to_csv(OUT / "iip_monthly.csv", index=False)

# 景気基準日付（第14〜16循環の山・谷）
t = (RAW / "esri_hiduke.html").read_bytes().decode("utf-8", errors="replace")
t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
txt = html.unescape(re.sub(r"<[^>]+>", " ", t))
txt = re.sub(r"\s+", " ", txt)
rows = []
for k in [14, 15, 16]:
    i = txt.find(f"第{k}循環")
    seg = txt[i:i + 300]
    ms = re.findall(r"(\d{4})年(\d{1,2})月", seg)[:3]
    (ty, tm), (py, pm), (ey, em) = ms
    rows.append({"cycle": k, "trough_start": f"{ty}-{int(tm):02d}", "peak": f"{py}-{int(pm):02d}", "trough_end": f"{ey}-{int(em):02d}"})
pd.DataFrame(rows).to_csv(OUT / "cycle_dates.csv", index=False)
print(len(q), len(m), rows)
