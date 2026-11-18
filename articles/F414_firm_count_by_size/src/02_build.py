"""5年分の経済センサスの表から、大分類×規模（11区分）×経営組織の企業等数と常用雇用者数の長い表を作る（オフライン）。
出力：data/firms_long.csv（year, survey, ind, ind_name, size（1〜11、0＝総数）, org, firms, reg_emp）"""
import pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ORGS = ["total", "company", "other_corp", "individual"]
TOP = re.compile(r"^([A-Z](?:～[A-Z])?)$")


def num(v):
    v = str(v).strip().replace(",", "")
    return 0 if v in ("-", "", "nan", "…", "...", "X", "x") else int(float(v))


out = []

# 2012・2016（CSV、各経営組織10列。先頭が企業等数、3列目が常用雇用者数（海外を含む））
for year, fn in ((2012, "census2012_t2_firms.csv"), (2016, "census2016_t1_firms.csv")):
    d = pd.read_csv(RAW / fn, encoding="cp932", header=None, dtype=str)
    labels = {d.iloc[10, j]: j for j in range(9, d.shape[1]) if pd.notna(d.iloc[10, j])}
    col = {"total": labels["総数(経営組織)"], "company": labels["(法人)会社企業"],
           "other_corp": labels["(法人)会社以外の法人"], "individual": labels["個人"]}
    body = d.iloc[12:]
    cur = None
    for _, r in body.iterrows():
        lab = str(r[8]).strip()
        size_code = int(str(r[6]).split(".")[-1])
        if size_code == 0:
            head = lab.split(" ")[0].replace("　", "")
            cur = (head, lab[len(head):].strip()) if TOP.match(head) else None
        if cur is None:
            continue
        for o in ORGS:
            out.append({"year": year, "survey": "活動調査", "ind": cur[0], "ind_name": cur[1], "size": size_code, "org": o,
                        "firms": num(r[col[o]]), "reg_emp": num(r[col[o] + 2])})

# 2014（xls、横に並んだ表）：企業等数 総数12・個人20・会社28・会社以外の法人72、常用雇用者数 14・22・36・74
x = pd.read_excel(RAW / "census2014_t1_firms.xls", header=None, dtype=str)
C14 = {"total": (12, 14), "individual": (20, 22), "company": (28, 36), "other_corp": (72, 74)}
cur = None; k = 0
for i in range(19, len(x)):
    r = x.iloc[i]
    if pd.isna(r[5]) or not str(r[5]).strip().isdigit():
        continue
    if pd.notna(r[7]) and TOP.match(str(r[7]).strip()):
        cur = (str(r[7]).strip(), str(r[9]).strip()); k = 0
    elif pd.notna(r[8]):
        cur = None; continue
    elif cur is not None:
        k += 1
    if cur is None:
        continue
    for o, (cf, ce) in C14.items():
        out.append({"year": 2014, "survey": "基礎調査", "ind": cur[0], "ind_name": cur[1], "size": k, "org": o,
                    "firms": num(r[cf]), "reg_emp": num(r[ce])})

# 2021・2024（長い形の xlsx）。「...」（個人経営の農林漁業は調べていない）は0とする
ORGMAP = {"0_総数": "total", "11_会社企業": "company", "12_会社以外の法人": "other_corp", "2_個人": "individual", "2_個人（雇用者あり）": "individual"}
for year, fn, survey, ecol in ((2021, "census2021_t1_firms.xlsx", "活動調査", "常用雇用者数（海外を含む）"),
                               (2024, "census2024_t1_firms.xlsx", "基礎調査（雇用者のいない個人経営を除く）", "従業者数_うち常用雇用者")):
    e = pd.read_excel(RAW / fn, header=None, dtype=str)
    hdr_row = [i for i in range(12) if e.iloc[i, 6] == "企業等数"][0]
    hdr = e.iloc[hdr_row].tolist()
    jf, je = hdr.index("企業等数"), hdr.index(ecol)
    body = e[e[0] == "00_全国"]
    body = body[body[1].isin(["1", "2"]) | (body[2] == "AB")]
    for _, r in body.iterrows():
        code, name = str(r[3]).split("_", 1)
        if not TOP.match(code.replace("AR", "A～R").replace("AB", "A～B").replace("CR", "C～R")):
            continue
        if r[4] not in ORGMAP:
            continue
        code = {"AR": "A～R", "AB": "A～B", "CR": "C～R"}.get(code, code)
        out.append({"year": year, "survey": survey, "ind": code, "ind_name": name.replace("S_", "S"),
                    "size": int(str(r[5]).split("_")[0]), "org": ORGMAP[r[4]], "firms": num(r[jf]), "reg_emp": num(r[je])})

df = pd.DataFrame(out).drop_duplicates(["year", "ind", "size", "org"])
df = df.sort_values(["year", "ind", "org", "size"]).reset_index(drop=True)
# 確かめ：規模の合計＝総数、経営組織の合計＝総数（企業等数）
bad = 0
for (y, ind, o), g in df.groupby(["year", "ind", "org"]):
    if g[g["size"] > 0].firms.sum() != g[g["size"] == 0].firms.sum():
        bad += 1
for (y, ind, s), g in df.groupby(["year", "ind", "size"]):
    t = g.set_index("org").firms
    if t["total"] != t["company"] + t["other_corp"] + t["individual"]:
        bad += 1
print("checks failed:", bad)
df.to_csv(ROOT / "data" / "firms_long.csv", index=False)
print(df.groupby("year").size().to_dict())
print(df[(df.ind == "A～R") & (df["size"] == 0)].pivot(index="year", columns="org", values="firms"))
print(sorted(df.ind.unique()))
