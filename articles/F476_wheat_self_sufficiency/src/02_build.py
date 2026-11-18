"""data/raw から、年度の需給表（小麦）と、産年の作物統計（地域別）の長い表を作る。"""
import pathlib, re, csv, io
import openpyxl, xlrd
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
REGIONS = ["全国", "北海道", "都府県", "東北", "北陸", "関東・東山", "東海", "近畿", "中国", "四国", "九州", "沖縄"]


def num(x):
    if x is None:
        return None
    s = str(x).replace(",", "").strip()
    if s in ("", "-", "***", "…", "x"):
        return 0.0 if s == "-" else None
    return float(s)


def fbs():
    text = (RAW / "fbs_wheat_ruinen_r6.csv").read_bytes().decode("cp932")
    rows = list(csv.reader(io.StringIO(text)))
    hi = next(i for i, r in enumerate(rows) if r and r[0] == "品目")
    head = rows[hi]
    col = {name: head.index(name) for name in head}
    want = {"P": "国内生産量【1000トン】", "M": "外国貿易_輸入量【1000トン】", "X": "外国貿易_輸出量【1000トン】",
            "dS": "在庫の増減量【1000トン】", "C": "国内消費仕向量【1000トン】", "feed": "国内消費仕向量の内訳_飼料用【1000トン】",
            "seed": "国内消費仕向量の内訳_種子用【1000トン】", "proc": "国内消費仕向量の内訳_加工用【1000トン】",
            "gross_food": "国内消費仕向量の内訳_粗食料_総数【1000トン】", "pc_kg": "１人当たり供給純食料_１年当たり数量【kg】"}
    out = []
    for r in rows[hi + 1:]:
        if not r or r[0] != "穀類／小麦":
            continue
        fy = int(re.match(r"(\d{4})年度", r[1]).group(1))
        d = {"fy": fy, "source": "累年表（令和6年度確報）"}
        for k, name in want.items():
            d[k] = num(r[col[name]])
        out.append(d)
    df = pd.DataFrame(out)
    # 令和7年度概算の統計表：見出しの文字で列を決め、品目名「小麦」の行を取る
    wb = openpyxl.load_workbook(RAW / "fbs_r7_gaisan.xlsx", data_only=True)
    got = {}
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        title = re.sub(r"\s", "", str(rows[2][9]))
        m = re.search(r"令和(\S)年度食料需給表（(概算値|確定値)）", title)
        fy = 2018 + "０１２３４５６７８９".index(m.group(1))
        h = [re.sub(r"\s", "", str(c)) if c else "" for c in rows[9]]
        cP, cM, cX, cS, cC, cF = h.index("生産量"), h.index("輸入量"), h.index("輸出量"), h.index("増減量"), h.index("仕向量"), h.index("飼料用")
        r = next(r for r in rows if r[2] == "小麦")
        got[fy] = {"fy": fy, "kind": m.group(2), "P": r[cP], "M": r[cM], "X": r[cX], "dS": r[cS], "C": r[cC], "feed": r[cF]}
    # 2024年度：累年表と確定値の照合
    chk = []
    for k in ["P", "M", "X", "dS", "C", "feed"]:
        a = float(df.loc[df.fy == 2024, k].iloc[0]); b = float(got[2024][k])
        chk.append({"fy": 2024, "item": k, "ruinen": a, "r7_sheet": b, "diff": a - b})
    g = got[2025]
    row = {"fy": 2025, "source": "令和7年度概算", **{k: float(g[k]) for k in ["P", "M", "X", "dS", "C", "feed"]}}
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    return df, pd.DataFrame(chk), got[2025]["kind"]


def crop():
    out = []
    for f in sorted(RAW.glob("crop_wheat_*.xls")):
        sh = xlrd.open_workbook(f).sheet_by_index(0)
        rows = [sh.row_values(i) for i in range(sh.nrows)]
        assert rows[2][0] == "小麦", f
        region = str(rows[3][0]).strip()  # 見出しの地域名
        assert region in REGIONS, region
        hi = next(i for i, r in enumerate(rows) if r[0] == "年次")
        h = rows[hi]
        ia, iy, iq = h.index("作付面積"), h.index("10a当たり収量"), h.index("収穫量")
        for r in rows[hi + 2:]:
            m = re.search(r"\((\d{4})\)", str(r[0]))
            if not m:
                continue
            out.append({"region": region, "year": int(m.group(1)), "area_ha": num(r[ia]), "yield_kg10a": num(r[iy]), "harvest_t": num(r[iq])})
    df = pd.DataFrame(out)
    df["region"] = pd.Categorical(df["region"], REGIONS, ordered=True)
    return df.sort_values(["region", "year"]).reset_index(drop=True)


def main():
    f, chk, kind25 = fbs()
    f["ssr"] = f["P"] / f["C"] * 100
    f.to_csv(DATA / "fbs_wheat_fy.csv", index=False, float_format="%.6g")
    chk.to_csv(DATA / "check_fbs_2024.csv", index=False)
    c = crop()
    c.to_csv(DATA / "crop_wheat_region_year.csv", index=False, float_format="%.6g")
    print("fbs", f.fy.min(), f.fy.max(), "2025:", kind25, "crop regions", c.region.nunique(), c.year.min(), c.year.max())
    print(chk)


if __name__ == "__main__":
    main()
