"""第2表（各年度分）から、業種×資本金階級×利益・欠損の法人数・事業年度数・営業収入を取り出す。
公表の第6表（PDF を文字にしたもの）から、利益計上法人数・欠損法人数の推移も取り出す。
出力：data/t2_long.csv、data/official_table6.csv"""
import pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"

# 業種シート名 → 業種名（会社標本調査の17区分）
IND = {"農林": "農林水産業", "鉱業": "鉱業", "建設": "建設業", "繊維": "繊維工業", "化学": "化学工業",
       "鉄鋼": "鉄鋼金属工業", "機械": "機械工業", "食料": "食料品製造業", "出版": "出版印刷業",
       "他製造": "その他の製造業", "卸": "卸売業", "卸売": "卸売業", "小売": "小売業", "料理": "料理飲食旅館業",
       "金融": "金融保険業", "不動産": "不動産業", "運輸": "運輸通信公益事業", "サービス": "サービス業"}
SECT = {"(利益計上法人)": "profit", "(欠損法人)": "loss", "(合計)": "total"}


def num(v):
    if v is None:
        return 0.0
    s = str(v).strip().replace(",", "")
    if s in ("", "-", "nan", "None", "△", "x", "X", "…"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def lower_bound(lbl):
    """'100万円'→1、'1,000万円'→10、'1億円'→100、'100億円'→10000（百万円）"""
    s = lbl.replace(",", "").replace(" ", "").replace("　", "")
    m = re.match(r"^(\d+)(万円|億円)$", s)
    if not m:
        return None
    v = int(m.group(1))
    return v / 100 if m.group(2) == "万円" else v * 100


def parse_sheet(df, year, ind):
    out = []
    sect = None
    for i in range(len(df)):
        c1 = str(df.iat[i, 1]).strip() if df.shape[1] > 1 else ""
        c2 = str(df.iat[i, 2]).strip() if df.shape[1] > 2 else ""
        key = c1.replace(" ", "").replace("　", "")
        if key in [k.replace(" ", "") for k in SECT]:
            sect = SECT[[k for k in SECT if k.replace(" ", "") == key][0]]
            continue
        if sect is None:
            continue
        lb = lower_bound(c1)
        row = None
        if lb is not None and c2 in ("以下", "超", "未満", "以上", "〃"):
            first = c2 in ("以下", "未満")
            row = {"kind": "class", "lb": 0.0 if first else lb, "ub_label": c2 if first else "", "label": c1 + c2}
            # 「100万円以下」「100万円未満」は下限0、それ以外は下限 lb
            if first:
                row["lb"] = 0.0
                row["first_ub"] = lb
        elif key.startswith("連結法人"):
            row = {"kind": "renketsu", "label": "連結法人"}
        elif key in ("通算法人",):
            row = {"kind": "tsusan", "label": "通算法人"}
        elif key in ("大通算法人", "中小通算法人"):
            row = {"kind": "tsusan_" + ("large" if key.startswith("大") else "small"), "label": key}
        elif key in ("合計", "計") and c2 in ("", "nan", "None"):
            row = {"kind": "sum", "label": "合計"}
        if row is None:
            continue
        vals = [num(df.iat[i, j]) if j < df.shape[1] else 0.0 for j in range(3, 12)]
        row.update({"year": year, "industry": ind, "section": sect,
                    "n_corp": vals[0], "capital": vals[1], "n_period": vals[2], "sales": vals[3],
                    "n_period_profit": vals[4], "income_profit": vals[5], "n_period_loss": vals[6],
                    "income_loss": vals[8]})
        out.append(row)
    return out


rows = []
for f in sorted(RAW.glob("t2_fy*")):
    year = int(re.search(r"fy(\d{4})", f.name).group(1))
    xl = pd.ExcelFile(f)
    for sh in xl.sheet_names:
        nm = sh.replace(" ", "")
        if nm.startswith("合計"):
            ind = "合計"
        elif nm in IND:
            ind = IND[nm]
        else:
            continue
        df = xl.parse(sh, header=None, dtype=object)
        rows += parse_sheet(df, year, ind)

t = pd.DataFrame(rows)
# 資本金階級の下限（百万円）。最初の階級は 0。
t["lb"] = t["lb"].astype(float)
t["regime"] = t["year"].map(lambda y: "以下・超" if y >= 2011 else "未満・以上")
cols = ["year", "regime", "industry", "section", "kind", "label", "lb", "n_corp", "n_period", "sales",
        "capital", "income_profit", "income_loss"]
t = t[cols].sort_values(["year", "industry", "section", "kind", "lb", "label"], kind="mergesort").reset_index(drop=True)
t.to_csv(OUT / "t2_long.csv", index=False, float_format="%.3f")

# 公表の第6表（PDF の文字）から 利益計上法人・欠損法人・合計・割合 を取り出す
era = {"平成": 1988, "令和": 2018}
off = []
for nm in ["kekka_fy2013", "kekka_fy2024"]:
    txt = (OUT / f"{nm}.txt").read_text(encoding="utf-8")
    i = txt.find("利益計上法人数・欠損法人数の推移")
    seg = txt[i:]
    j = seg.find("内 連結法人")
    seg = seg[:j]
    cur_era, cur_kind = None, None
    pat = re.compile(r"^\s*(平成|令和)?\s*(\d+|元|[１２３４５６７８９])\s*(年度分|年分)?\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)\s*$")
    for line in seg.splitlines():
        m = pat.match(line.replace("　", " "))
        if not m:
            continue
        if m.group(1):
            cur_era = m.group(1)
        if m.group(3):
            cur_kind = "年度分" if m.group(3) == "年度分" else "年分"
        if cur_era is None:
            continue
        g = m.group(2).translate(str.maketrans("１２３４５６７８９", "123456789"))
        n = 1 if g == "元" else int(g)
        nums = m.groups()[3:]
        off.append({"source": nm, "fiscal_year": era[cur_era] + n, "basis": cur_kind,
                    "profit": int(nums[0].replace(",", "")), "loss": int(nums[1].replace(",", "")),
                    "total": int(nums[2].replace(",", "")), "loss_share_pct": float(nums[3])})
o = pd.DataFrame(off).drop_duplicates(["source", "fiscal_year", "basis"]).sort_values(["fiscal_year", "basis", "source"])
o.to_csv(OUT / "official_table6.csv", index=False)
print(len(t), "rows;", len(o), "official rows")
