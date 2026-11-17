"""3回分の表から、全国の 年×国籍（総数・日本人）×男女×配偶関係×年齢×職業 の就業者数（data/national_long.csv）を作る。"""
import csv, pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
OCC = ["総数", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
MAR = {"0000": "総数", "0001": "未婚", "0002": "有配偶", "0003": "死別・離別"}
SEX = {"0000": "総数", "0001": "男", "0002": "女"}
AGE = {"0005": "35～39歳", "0006": "40～44歳", "0007": "45～49歳", "0008": "50～54歳"}


def old_csv(path, year):
    rows = []
    with open(path, encoding="cp932", newline="") as f:
        for r in csv.reader(f):
            r = r[1:]  # 先頭の列は行番号
            if len(r) < 23 or r[1] != "00000" or not r[3].startswith("hai3A"):
                continue
            nat = "総数" if r[0] == "01" else ("日本人" if r[0] == "02" else None)
            mar, sex, age = MAR.get(r[3][-4:]), SEX.get(r[5][-4:]), AGE.get(r[7][-4:])
            if nat is None or mar is None or sex is None or age is None:
                continue
            for k, o in enumerate(OCC):
                rows.append(dict(year=year, nationality=nat, sex=sex, marital=mar, age=age, occ=o, n=int(r[10 + k])))
    return rows


def new_xlsx(path, year):
    d = pd.read_excel(path, header=None)
    hdr = [str(v) for v in d.iloc[7].tolist()]
    cols = {AGE[a]: j for j, h in enumerate(hdr) for a, lab in [("0005", "05_35"), ("0006", "06_40"), ("0007", "07_45"), ("0008", "08_50")] if h.startswith(lab)}
    sub = d[(d.iloc[:, 0] == "a") & (d.iloc[:, 1] == "00000_全国")]
    rows = []
    nm = {"0_国籍総数": "総数", "1_うち日本人": "日本人"}
    mm = {"0_総数": "総数", "1_未婚": "未婚", "2_有配偶": "有配偶", "3_死別・離別": "死別・離別"}
    sm = {"0_総数": "総数", "1_男": "男", "2_女": "女"}
    for _, r in sub.iterrows():
        if r.iloc[2] not in nm or r.iloc[3] not in mm or r.iloc[4] not in sm:
            continue
        o = "総数" if r.iloc[5] == "0_総数" else str(r.iloc[5])[0]
        for a, j in cols.items():
            rows.append(dict(year=year, nationality=nm[r.iloc[2]], sex=sm[r.iloc[4]], marital=mm[r.iloc[3]], age=a, occ=o, n=int(r.iloc[j])))
    return rows


def main():
    rows = old_csv(RAW / "census2010_t3_1_occ_marital.csv", 2010) + old_csv(RAW / "census2015_t9_1_occ_marital.csv", 2015) + \
        new_xlsx(RAW / "census2020_t9_1_occ_marital.xlsx", 2020)
    df = pd.DataFrame(rows).drop_duplicates(["year", "nationality", "sex", "marital", "age", "occ"])
    df = df.sort_values(["year", "nationality", "sex", "marital", "age", "occ"]).reset_index(drop=True)
    df.to_csv(DATA / "national_long.csv", index=False)
    print(df.groupby(["year", "nationality"]).size())


if __name__ == "__main__":
    main()
