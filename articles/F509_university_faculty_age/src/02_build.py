"""data/raw の Excel から、年度×設置者×職名×年齢の人数の表（data/faculty_age.csv）と、
公表の平均年齢の表（data/official_mean_age.csv）、年次統計の大学の平均年齢（data/ts_mean_age.csv）を作る。"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
YEARS = list(range(1998, 2026, 3))
SETTERS = ["計", "国立", "公立", "私立"]
POS_MAP = {"計": "計", "学長": "学長", "副学長": "副学長", "教授": "教授", "助教授": "准教授", "准教授": "准教授",
           "講師": "講師", "助教": "助教", "助手": "助手"}


def norm(s):
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", str(s)))


def num(v):
    s = norm(v)
    if s in ("nan", "-", "－", "−", "…", ""):
        return 0.0
    return float(s.replace(",", ""))


def parse_sheet(d):
    # 職名の見出しの行
    hdr = next(i for i in range(12) if "教授" in [norm(v) for v in d.iloc[i].tolist()])
    names = []
    for v in d.iloc[hdr].tolist():
        s = norm(v)
        if s in POS_MAP and (not names or names[-1] != s):
            names.append(s)
    # 「本務教員の計」の行と、その直前の「計・男・女」の行
    tot, lc = next((i, c) for i in range(hdr, hdr + 8) for c in range(3) if "本務教員の計" in norm(d.iloc[i, c]))
    sub = None
    for i in range(tot - 1, hdr - 1, -1):
        row = [norm(v) for v in d.iloc[i].tolist()]
        if row.count("男") >= 3:
            sub = i
            break
    subrow = [norm(v) for v in d.iloc[sub].tolist()]
    cols = [j for j, v in enumerate(subrow) if v == "計" and j > lc + 1]
    # 学長・副学長は表によって列の数が違う（国立の表は「計」だけ）ので、
    # 先頭の「計」（全体）と、末尾の教授〜助手の「計」だけを使い、学長・副学長は全体との差で出す
    staff = [nm for nm in names if nm in ("教授", "助教授", "准教授", "講師", "助教", "助手")]
    names = ["計"] + staff
    cols = [cols[0]] + cols[-len(staff):]
    recs, mean = [], {}
    for i in range(tot, len(d)):
        c0, c1 = norm(d.iloc[i, lc]), norm(d.iloc[i, lc + 1])
        if re.fullmatch(r"\d+歳|70歳以上|25歳未満", c1):
            lab = c1
        else:
            lab = c0
        if not mean and (c0.startswith("平均年齢") or c1.startswith("平均年齢") or c1 == "(歳)"):
            for nm, j in zip(names, cols):
                mean[POS_MAP[nm]] = num(d.iloc[i, j])
            continue
        if re.fullmatch(r"\d+歳", lab):
            age = int(lab[:-1])
        elif lab == "25歳未満":
            age = 24
        elif lab == "70歳以上":
            age = 70
        else:
            continue
        for nm, j in zip(names, cols):
            recs.append((POS_MAP[nm], age, num(d.iloc[i, j])))
    # 本務教員の計の行（検算用）
    totals = {POS_MAP[nm]: num(d.iloc[tot, j]) for nm, j in zip(names, cols)}
    return recs, mean, totals


def main():
    rows, means = [], []
    for y in YEARS:
        f = next(RAW.glob(f"age_pos_{y}.*"))
        book = pd.read_excel(f, sheet_name=None, header=None)
        sheets = list(book.values())[:4]
        for s, d in zip(SETTERS, sheets):
            head = norm(" ".join(str(v) for v in d.iloc[:6].values.ravel()))
            key = {"計": "1.計", "国立": "うち国立", "公立": "うち公立", "私立": "うち私立"}[s]
            assert key in head and (s != "計" or not any(k in head for k in ("うち国立", "うち公立", "うち私立"))), (y, s, head[:200])
            recs, mean, totals = parse_sheet(d)
            df = pd.DataFrame(recs, columns=["position", "age", "n"])
            w = df.pivot_table(index="age", columns="position", values="n", aggfunc="sum")
            lead = w["計"] - w[[c for c in w.columns if c != "計"]].sum(axis=1)
            assert (lead >= 0).all(), (y, s)
            df = pd.concat([df, pd.DataFrame({"position": "学長・副学長", "age": lead.index, "n": lead.values})], ignore_index=True)
            totals["学長・副学長"] = totals["計"] - sum(v for k, v in totals.items() if k != "計")
            # 検算：職名ごとの各歳の和（25歳未満・各歳・70歳以上）＝本務教員の計
            sm = df.groupby("position", sort=False)["n"].sum()
            for p, t in totals.items():
                assert abs(sm[p] - t) < 0.5, (y, s, p, sm[p], t)
            df.insert(0, "setter", s)
            df.insert(0, "year", y)
            rows.append(df)
            for p, m in mean.items():
                means.append((y, s, p, m))
    out = pd.concat(rows, ignore_index=True)
    out["n"] = out["n"].astype(int)
    out.to_csv(ROOT / "data" / "faculty_age.csv", index=False)
    pd.DataFrame(means, columns=["year", "setter", "position", "official_mean_age"]).to_csv(
        ROOT / "data" / "official_mean_age.csv", index=False)

    # 年次統計：大学の平均年齢（計・男・女）
    d = pd.read_excel(RAW / "ts_mean_age.xlsx", header=None)
    start = next(i for i in range(len(d)) if any(norm(v) == "大学" for v in d.iloc[i].tolist()))
    j = [k for k, v in enumerate(d.iloc[start].tolist()) if norm(v) == "大学"][0]
    era = {"昭和": 1925, "平成": 1988, "令和": 2018}
    ts, cur = [], None
    for i in range(start + 2, len(d)):
        lab = norm(d.iloc[i, 2])
        m = re.match(r"(昭和|平成|令和)?(元|\d+)年", lab)
        if not m:
            if ts:
                break
            continue
        if m.group(1):
            cur = era[m.group(1)]
        n = 1 if m.group(2) == "元" else int(m.group(2))
        ts.append((cur + n, num(d.iloc[i, j]), num(d.iloc[i, j + 1]), num(d.iloc[i, j + 2])))
    pd.DataFrame(ts, columns=["year", "mean_all", "mean_male", "mean_female"]).to_csv(ROOT / "data" / "ts_mean_age.csv", index=False)


if __name__ == "__main__":
    main()
