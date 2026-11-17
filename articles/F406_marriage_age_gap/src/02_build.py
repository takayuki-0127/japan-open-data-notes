"""data/raw の CSV（Shift_JIS）から、分析用の表を data/ に作る。
- data/gap_dist.csv：初婚夫妻の年齢差の区分別件数（第9.14表、実数）
- data/mean_age.csv：初婚・全婚姻の夫妻の平均婚姻年齢（第9.11表）
- data/cross_first.csv：初婚どうしの夫の年齢×妻の年齢の件数（1995・2005・2015・2025年、各歳のみ）
"""
import csv, pathlib, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"


def norm(s):
    return unicodedata.normalize("NFKC", str(s)).replace(" ", "").strip()


def num(s):
    s = norm(s)
    if s in ("-", ""):
        return 0.0 if s == "-" else float("nan")
    return pd.to_numeric(s, errors="coerce")


def read(name):
    with open(RAW / name, encoding="cp932", newline="") as f:
        return [r for r in csv.reader(f)]


def gap_dist():
    rows = read("vs2025_t9_14_first_marriage_age_gap.csv")
    head = None
    out = []
    for r in rows:
        if head is None and len(r) > 2 and norm(r[1]) == "1970":
            head = [int(norm(x)) for x in r[1:] if norm(x)]
            continue
        if head is None:
            continue
        lab = norm(r[0])
        if lab == "百分率":
            break
        if lab in ("実数", ""):
            continue
        for y, v in zip(head, r[1:]):
            out.append(dict(year=y, cat=lab, n=num(v)))
    df = pd.DataFrame(out)
    # 「１歳」など同じ名前が妻年上・夫年上の両方にあるので、出てきた順に親の区分をつける
    parent, labs = None, []
    for r in rows:
        lab = norm(r[0]) if r else ""
        if lab == "百分率":
            break
        if lab in ("総数", "妻年上", "夫妻同年齢", "夫年上"):
            parent = lab
            labs.append((lab, "計"))
        elif lab.endswith("歳") or lab.endswith("以上"):
            labs.append((parent, lab))
    df["parent"] = [p for p, c in labs for _ in head]
    df["sub"] = [c for p, c in labs for _ in head]
    df = df[["year", "parent", "sub", "n"]]
    df.to_csv(DATA / "gap_dist.csv", index=False)
    return df


def mean_age():
    rows = read("vs2025_t9_11_mean_marriage_age.csv")
    out = []
    for r in rows:
        y = norm(r[0]) if r else ""
        if y.isdigit() and len(r) >= 7:
            out.append(dict(year=int(y), all_h=num(r[1]), all_w=num(r[2]), first_h=num(r[3]), first_w=num(r[4]),
                            gap_all=num(r[5]), gap_first=num(r[6])))
    df = pd.DataFrame(out)
    df.to_csv(DATA / "mean_age.csv", index=False)
    return df


def age_of(lab):
    s = norm(lab).replace("歳", "")
    return int(s) if s.isdigit() else None


def cross(name, year):
    rows = read(name)
    start = None
    for i, r in enumerate(rows):
        lab = norm(r[0]) if r else ""
        if lab in ("夫-初婚*妻-初婚", "初婚の夫と初婚の妻"):
            start = i
            break
    # 夫の年齢の見出しの行（「夫総数」または「総数」で始まる列見出し）
    hdr = None
    for r in rows[:10]:
        if len(r) > 5 and norm(r[0]) == "" and norm(r[1]) in ("夫総数", "総数"):
            hdr = [age_of(x) for x in r[1:]]
    out = []
    for r in rows[start + 1:]:
        lab = norm(r[0]) if r else ""
        if lab in ("不詳",):
            break
        w = age_of(lab)
        if w is None:
            continue
        for h, v in zip(hdr, r[1:]):
            if h is None:
                continue
            n = num(v)
            if n and n > 0:
                out.append(dict(year=year, wife_age=w, husband_age=h, n=int(n)))
    return pd.DataFrame(out)


def main():
    g = gap_dist()
    m = mean_age()
    c = pd.concat([cross("vs1995_m4_age_cross_1995.csv", 1995), cross("vs2005_m4_age_cross_2005.csv", 2005),
                   cross("vs2015_m5_age_cross_2015.csv", 2015), cross("vs2025_m5_age_cross_2025.csv", 2025)])
    c = c.sort_values(["year", "wife_age", "husband_age"]).reset_index(drop=True)
    c.to_csv(DATA / "cross_first.csv", index=False)
    print(g.year.nunique(), m.year.min(), m.year.max(), c.groupby("year").n.sum().to_dict())


if __name__ == "__main__":
    main()
