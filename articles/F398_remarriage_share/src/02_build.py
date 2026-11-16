"""data/raw の CSV（Shift_JIS）から、婚姻件数の組み合わせ別（data/combo.csv）と、初婚・再婚×夫妻×年齢（data/age.csv）を作る。"""
import csv, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
AGES = ["総数", "19歳以下", "20～24歳", "25～29歳", "30～34歳", "35～39歳", "40～44歳", "45～49歳", "50～54歳", "55～59歳",
        "60～64歳", "65～69歳", "70～74歳", "75～79歳", "80歳以上", "不詳"]


def num(s):
    s = str(s).strip().replace(" ", "")
    if s in ("-", "－"):
        return 0.0
    return pd.to_numeric(s, errors="coerce")


def main():
    rows = []
    with open(RAW / "vs2025_t9_5_marriage_first_re.csv", encoding="cp932", newline="") as f:
        for r in csv.reader(f):
            if r and r[0].strip().isdigit() and len(r) > 6:
                rows.append(dict(year=int(r[0]), total=num(r[1]), first_both=num(r[2]), any_re=num(r[3]), re_both=num(r[4]),
                                 husband_re_wife_first=num(r[5]), husband_first_wife_re=num(r[6])))
    pd.DataFrame(rows).drop_duplicates("year").to_csv(DATA / "combo.csv", index=False)
    rows = []
    for kind, fn in (("初婚", "vs2025_t9_7_1_first_by_age.csv"), ("再婚", "vs2025_t9_7_2_re_by_age.csv")):
        sex = None
        with open(RAW / fn, encoding="cp932", newline="") as f:
            for r in csv.reader(f):
                if not r:
                    continue
                if r[0].strip() in ("夫", "妻"):
                    sex = r[0].strip(); continue
                if sex and r[0].strip().isdigit():
                    for k, a in enumerate(AGES):
                        rows.append(dict(kind=kind, sex=sex, year=int(r[0]), age=a, n=num(r[1 + k])))
    pd.DataFrame(rows).to_csv(DATA / "age.csv", index=False)
    print("ok")


if __name__ == "__main__":
    main()
