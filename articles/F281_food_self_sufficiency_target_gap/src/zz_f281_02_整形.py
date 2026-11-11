"""F281 02 整形：取得した表を、分析で使う形の CSV にする。

入力（data/raw）
- estat/e798.csv など：食料需給表 令和6年度確報の累年表（e-Stat、CSV）
- fbs_r7.xlsx：令和7年度食料需給表（概算）。1枚目が令和7年度、2枚目が令和6年度
- zk_012-7.xls：食料自給率の推移（品目別・総合・飼料自給率、1965〜2025年度）
- maff_r7_jikyuritsu_item_table.txt：「令和7年度食料自給率について」の品目別の国産熱量・供給熱量（pdftotext）
出力（data/processed）
- series_long.csv：年度×品目の 国内生産量・国内消費仕向量・純食料(kg)・供給熱量(kcal)（1960〜2024 は累年表、2025 は概算）
- ssr_series.csv：年度×指標の自給率（品目別・総合・飼料）
- fbs_items_2025.csv / fbs_items_2024.csv：品目ごとの1年分（概算・確報の表から）
- maff_item_kcal_2025.csv：農林水産省の品目別 国産熱量・供給熱量（2025年度と前年度差から2024年度）
"""
import io, re, json, pathlib
import pandas as pd
import openpyxl, xlrd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)


def num(x):
    if x is None:
        return None
    s = str(x).replace(",", "").replace("△", "-").replace("▲", "-").strip()
    if s in ("", "-", "…", "***", "x", "nan"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


# ---------- 1. 累年表（e-Stat CSV）----------
def read_estat(i):
    t = (RAW / "estat" / f"e{i}.csv").read_bytes().decode("cp932")
    lines = t.splitlines()
    hdr = [k for k, l in enumerate(lines) if l.startswith(("食料需給_項目", "需給品目", "自給率"))][0]
    return pd.read_csv(io.StringIO("\n".join(lines[hdr:])), dtype=str)

frames = []
for i, var in [(798, "prod"), (801, "use"), (806, "kg"), (808, "kcal")]:
    df = read_estat(i)
    df = df.rename(columns={"類別・品目別": "item"}).drop(columns=["食料需給_項目"])
    long = df.melt(id_vars="item", var_name="fy", value_name="value")
    long["fy"] = long["fy"].str.extract(r"(\d{4})").astype(int)
    long["value"] = long["value"].map(num)
    long["var"] = var
    frames.append(long)
series = pd.concat(frames)

# ---------- 2. 令和7年度（概算）・令和6年度の表 ----------
COLS = {4: "prod", 5: "imp", 6: "exp", 7: "stock", 8: "use", 9: "feed", 18: "net_food", 19: "kg", 21: "kcal"}
LABELS = {  # 表の品目名（空白を除いたもの）→ 分析で使う名前
    "米": "米", "小麦": "小麦", "大麦": "大麦", "はだか麦": "はだか麦", "かんしょ": "かんしょ", "ばれいしょ": "ばれいしょ",
    "大豆": "大豆", "牛肉": "牛肉", "豚肉": "豚肉", "鶏肉": "鶏肉",
}
TOPS = {"野": "野菜", "果": "果実", "鶏": "鶏卵", "牛": "牛乳及び乳製品", "魚": "魚介類", "で": "でん粉", "砂": "砂糖類", "油": "油脂類"}


def read_fbs_sheet(ws, fy):
    rows = []
    for r in ws.iter_rows(min_row=13, max_row=ws.max_row, values_only=True):
        r = list(r)
        lab1 = str(r[1] or "").replace(" ", "").replace("　", "")
        lab2 = str(r[2] or "").replace(" ", "").replace("　", "")
        name = None
        if lab2 in LABELS and str(r[1] or "").strip() not in ("",):
            name = LABELS[lab2]
        elif re.match(r"^\s*\d+[\.．]", str(r[0] or "")) and lab1[:1] in TOPS:
            name = TOPS[lab1[:1]]
        if name is None or num(r[4]) is None:
            continue
        rec = {"fy": fy, "item": name}
        for c, k in COLS.items():
            rec[k] = num(r[c])
        rows.append(rec)
    df = pd.DataFrame(rows).drop_duplicates("item", keep="first")
    return df

wb = openpyxl.load_workbook(RAW / "fbs_r7.xlsx", data_only=True)
fbs25 = read_fbs_sheet(wb.worksheets[0], 2025)
fbs24 = read_fbs_sheet(wb.worksheets[1], 2024)
# 合計の供給熱量
def total_kcal(ws):
    for r in ws.iter_rows(min_row=13, values_only=True):
        if "合" in str(r[0] or "") + str(r[1] or "") and num(r[21]) and num(r[21]) > 1500:
            return num(r[21])
S25, S24 = total_kcal(wb.worksheets[0]), total_kcal(wb.worksheets[1])
fbs25.to_csv(OUT / "fbs_items_2025.csv", index=False)
fbs24.to_csv(OUT / "fbs_items_2024.csv", index=False)

# 2025年度を累年の形に足す（主な品目）
MAP_SERIES = {"米": "穀類_米", "小麦": "穀類_小麦", "大麦": "穀類_大麦", "はだか麦": "穀類_はだか麦", "かんしょ": "いも類_かんしょ",
              "ばれいしょ": "いも類_ばれいしょ", "大豆": "豆類_大豆", "野菜": "野菜", "果実": "果実", "牛肉": "肉類_牛肉",
              "豚肉": "肉類_豚肉", "鶏肉": "肉類_鶏肉", "鶏卵": "鶏卵", "牛乳及び乳製品": "牛乳及び乳製品", "魚介類": "魚介類"}
add = []
for _, r in fbs25.iterrows():
    if r["item"] in MAP_SERIES:
        for v in ["prod", "use", "kg", "kcal"]:
            add.append({"item": MAP_SERIES[r["item"]], "fy": 2025, "value": r[v], "var": v})
add.append({"item": "合計", "fy": 2025, "value": S25, "var": "kcal"})
series = pd.concat([series, pd.DataFrame(add)])
series.to_csv(OUT / "series_long.csv", index=False)

# ---------- 3. 自給率の推移（1965〜2025年度）----------
s = xlrd.open_workbook(RAW / "zk_012-7.xls").sheet_by_index(0)
rows = []
prev = None
for r in range(5, 45):
    v = s.row_values(r)
    lab = re.sub(r"\s+", "", "".join(str(x) for x in v[:3]))
    lab = re.sub(r"^(品|目|別|自|給|率)", "", lab)
    if not lab:
        lab = (prev or "") + "（飼料自給率考慮）"
    else:
        prev = lab
    for j in range(3, 64):
        val = num(v[j])
        if val is not None:
            rows.append({"indicator": lab, "fy": 1962 + j, "value": val})
ssr = pd.DataFrame(rows)
ssr.to_csv(OUT / "ssr_series.csv", index=False)

# ---------- 4. 品目別の国産熱量・供給熱量（2025年度、前年度差から2024年度）----------
txt = (RAW / "maff_r7_jikyuritsu_item_table.txt").read_text(encoding="utf-8")
items = []
for line in txt.splitlines():
    m = re.match(r"^\s{1,4}(米|小麦|いも類|でん粉|大豆|野菜|果実|畜産物|魚介類|砂糖類|油脂類|その他|合計)\s+([\d,]+)kcal\s+([▲+]?[\d,]+)kcal\s+([\d,]+)kcal\s+([▲+]?[\d,]+)kcal", line)
    if m:
        n, dn, sk, ds = [num(x.replace("+", "")) for x in m.groups()[1:]]
        items.append({"item": m.group(1), "N_2025": n, "N_2024": n - dn, "S_2025": sk, "S_2024": sk - ds})
mi = pd.DataFrame(items)
mi.to_csv(OUT / "maff_item_kcal_2025.csv", index=False)

meta = {"S_2025_fbs": S25, "S_2024_fbs": S24, "n_items_fbs25": len(fbs25), "n_maff_items": len(mi),
        "maff_N_sum": float(mi.loc[mi.item != "合計", "N_2025"].sum()), "maff_N_total": float(mi.loc[mi.item == "合計", "N_2025"].iloc[0])}
(OUT / "meta_02.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
print(json.dumps(meta, ensure_ascii=False))
print(fbs25[["item", "prod", "use", "kg", "kcal"]].to_string())
print(mi.to_string())
