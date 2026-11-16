"""02_build.py : data/raw の元ファイルから、分析用の CSV を data/ に作る（オフライン）。"""
import json
import pathlib

import openpyxl
import pandas as pd
import xlrd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"

# 対象の中分類（列の中分類符号 → 短い名前, 大分類, 家計向けか）
TARGET = [
    ("37", "通信業", "情報通信", "B"), ("38", "放送業", "情報通信", "B"),
    ("39", "情報サービス業", "情報通信", "B"), ("40", "インターネット附随サービス業", "情報通信", "B"),
    ("41", "映像・音声・文字情報制作業", "情報通信", "B"),
    ("42", "鉄道業", "運輸・郵便", "B"), ("43", "道路旅客運送業", "運輸・郵便", "H"),
    ("44", "道路貨物運送業", "運輸・郵便", "B"), ("45", "水運業", "運輸・郵便", "B"),
    ("47", "倉庫業", "運輸・郵便", "B"), ("48", "運輸に附帯するサービス業", "運輸・郵便", "B"),
    ("4*", "航空運輸業・郵便業", "運輸・郵便", "B"),
    ("68", "不動産取引業", "不動産・物品賃貸", "B"), ("69", "不動産賃貸業・管理業", "不動産・物品賃貸", "B"),
    ("70", "物品賃貸業", "不動産・物品賃貸", "B"),
    ("72", "専門サービス業", "専門・技術サービス", "B"), ("73", "広告業", "専門・技術サービス", "B"),
    ("74", "技術サービス業", "専門・技術サービス", "B"),
    ("75", "宿泊業", "宿泊・飲食", "H"), ("76", "飲食店", "宿泊・飲食", "H"),
    ("77", "持ち帰り・配達飲食サービス業", "宿泊・飲食", "H"),
    ("78", "洗濯・理容・美容・浴場業", "生活関連・娯楽", "H"),
    ("79", "その他の生活関連サービス業", "生活関連・娯楽", "H"), ("80", "娯楽業", "生活関連・娯楽", "H"),
    ("82", "その他の教育・学習支援業", "教育・学習支援", "H"),
    ("88", "廃棄物処理業", "その他のサービス", "B"), ("89", "自動車整備業", "その他のサービス", "B"),
    ("90", "機械等修理業", "その他のサービス", "B"), ("91", "職業紹介・労働者派遣業", "その他のサービス", "B"),
    ("92", "その他の事業サービス業", "その他のサービス", "B"), ("95", "その他のサービス業", "その他のサービス", "B"),
]
CODES = [t[0] for t in TARGET]


def build_sales():
    wb = openpyxl.load_workbook(RAW / "mbss_ts_t1_aj10.xlsx", read_only=True, data_only=True)
    rows = list(wb["月次・実数"].iter_rows(values_only=True))
    level = rows[13]
    code = rows[15]
    col = {}
    for j in range(12, 61):
        c = str(code[j]).strip() if code[j] is not None else ""
        # 82 は「その他の教育」(階層4) だけを使う（うち〜 は階層5）
        if c in CODES and c not in col and level[j] in (4,):
            col[c] = j
    assert len(col) == len(CODES), sorted(set(CODES) - set(col))
    recs = []
    for r in rows[18:]:
        y, m = r[9], r[10]
        if not isinstance(y, int) or not isinstance(m, int):
            continue
        flag = (r[11] or "").strip() if isinstance(r[11], str) else ""
        for c, name, div, kind in TARGET:
            recs.append({"ym": y * 100 + m, "year": y, "month": m, "code": c, "industry": name,
                         "division": div, "kind": kind, "sales_mil_yen": float(r[col[c]]),
                         "prelim": int(flag == "p")})
        # 照合用：統計表の「サービス産業計」
        recs.append({"ym": y * 100 + m, "year": y, "month": m, "code": "SV", "industry": "サービス産業計（統計表）",
                     "division": "-", "kind": "-", "sales_mil_yen": float(r[13]), "prelim": int(flag == "p")})
    df = pd.DataFrame(recs).sort_values(["ym", "code"], kind="mergesort")
    df.to_csv(OUT / "sales_monthly.csv", index=False)
    return df


def build_prices():
    d = json.loads((RAW / "boj_sppi2020_monthly.json").read_bytes())
    sp = {}
    for s in d["RESULTSET"]:
        code = s["SERIES_CODE"].replace("PRCS20_", "")
        dates = s["VALUES"]["SURVEY_DATES"]
        vals = s["VALUES"]["VALUES"]
        sp["SPPI_" + code] = pd.Series([float(v) if v is not None else float("nan") for v in vals],
                                       index=[int(x) for x in dates])
    sppi = pd.DataFrame(sp)
    names = {"SPPI_" + s["SERIES_CODE"].replace("PRCS20_", ""): s["NAME_OF_TIME_SERIES_J"] for s in d["RESULTSET"]}

    def read_cpi(fname, want):
        lines = (RAW / fname).read_bytes().decode("cp932").splitlines()
        head = lines[0].split(",")
        codes = lines[2].split(",")
        idx = {c: i for i, c in enumerate(codes)}
        out = {}
        for c in want:
            i = idx[c]
            ser = {}
            for ln in lines:
                p = ln.split(",")
                if p[0].isdigit() and len(p[0]) == 6 and 201301 <= int(p[0]) <= 202612:
                    ser[int(p[0])] = float(p[i]) if p[i] else float("nan")
            out["CPI_" + c] = pd.Series(ser)
            names["CPI_" + c] = head[i]
        return pd.DataFrame(out)

    cpi1 = read_cpi("cpi2025_monthly_chubunrui_zmi2025s.csv", ["0042", "0138", "0146", "0121"])
    cpi3 = read_cpi("cpi2025_monthly_hinmoku_zmi2025a.csv", ["0139"])
    cpi2 = read_cpi("cpi2025_monthly_zaisa_zmi2025b.csv", ["0220", "0242"])
    pr = sppi.join(cpi1, how="outer").join(cpi2, how="outer").join(cpi3, how="outer").sort_index()
    pr = pr.loc[(pr.index >= 201301) & (pr.index <= 202612)]
    pr.index.name = "ym"
    pr.to_csv(OUT / "prices_monthly.csv")
    pd.DataFrame({"series": list(names), "name": [names[k] for k in names]}).to_csv(
        OUT / "price_series_names.csv", index=False)
    return pr


def build_size():
    labels = ["総数", "10人未満", "10〜29人", "30〜99人", "100〜299人", "300人以上"]
    recs = []
    for y in (2018, 2019, 2023):
        sh = xlrd.open_workbook(RAW / f"mssi_annual_t3_{y}_a030.xls").sheet_by_index(0)
        for i in range(17, sh.nrows):
            r = sh.row_values(i)
            if str(r[0]).strip() != "020":
                continue
            code = str(r[9]).strip()  # 中分類の符号の列だけを使う
            if code not in CODES:  # 対象の31業種だけ
                continue
            name = str(r[13]).replace("\n", "").strip()
            for k, lab in enumerate(labels):
                v = r[17 + k]
                recs.append({"year": y, "code": code, "name": name, "size": lab,
                             "sales_mil_yen_monthly_avg": float(v) if isinstance(v, float) else float("nan")})
    df = pd.DataFrame(recs)
    df.to_csv(OUT / "size_annual.csv", index=False)
    return df


if __name__ == "__main__":
    s = build_sales()
    p = build_prices()
    z = build_size()
    print("sales", s.shape, s.ym.min(), s.ym.max())
    print("prices", p.shape)
    print("size", z.shape)
