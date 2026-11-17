"""data/raw の時系列表を CSV にする。
- tenure_japan.csv：全国の所有の関係別住宅数（1963〜2023年）
- tenure_pref.csv：都道府県の総数・借家・公営の借家（1983〜2023年）
- tenure_age.csv：全国の所有の関係×年齢の主世帯数（1968〜2023年）
- rent.csv：全国の家賃（1か月当たり・1畳当たり、1973〜2023年）
"""
import pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
COLS = ["total", "owned", "rented", "public", "ur", "private", "issued"]


def num(v):
    return pd.to_numeric(str(v).replace(",", "").strip(), errors="coerce")


def z(s):
    return re.sub(r"[\s　\n]", "", str(s))


def main():
    # 第9-1表
    d = pd.read_excel(RAW / "ts09_1_tenure_japan.xlsx", header=None)
    rows = {}
    for i in range(16, len(d)):
        if "割合" in z(d.iloc[i, 1]):
            break  # 下は割合（%）の表
        y = num(d.iloc[i, 2])
        if pd.isna(y) or not (1960 < y < 2030):
            continue
        y = int(y)
        rec = dict(year=y, okinawa_excluded=z(d.iloc[i, 3]).startswith("3)"), **{c: num(d.iloc[i, 4 + k]) for k, c in enumerate(COLS)})
        if y in rows and rec["okinawa_excluded"]:
            continue
        rows[y] = rec
    pd.DataFrame([rows[k] for k in sorted(rows)]).to_csv(DATA / "tenure_japan.csv", index=False)

    # 第21-1表
    d = pd.read_excel(RAW / "ts21_1_tenure_age_japan.xlsx", header=None)
    rows, year = [], None
    for i in range(18, len(d)):
        lab, c2 = z(d.iloc[i, 1]), d.iloc[i, 2]
        if re.match(r"^(昭和|平成|令和)", lab) and not pd.isna(num(c2)):
            year = int(num(c2)); continue
        if year and lab and not pd.isna(num(d.iloc[i, 4])):
            rows.append(dict(year=year, age=lab, **{c: num(d.iloc[i, 4 + k]) for k, c in enumerate(COLS)}))
    pd.DataFrame(rows).to_csv(DATA / "tenure_age.csv", index=False)

    # 第10表（シートごとに列の位置を見出しから探す）
    xs = pd.read_excel(RAW / "ts10_tenure_pref.xlsx", header=None, sheet_name=None)
    rows = []
    for name, d in xs.items():
        m = re.search(r"Part\s*\d+\.\s*(\d{4})", " ".join(str(v) for v in d.iloc[:8, :4].values.ravel()))
        year = int(m.group(1))
        hdr = {}
        for i in range(6, 12):
            for j in range(d.shape[1]):
                v = z(d.iloc[i, j])
                if v == "総数" and "total" not in hdr and i == 7:
                    hdr["total"] = j
                if v == "借家" and "rented" not in hdr:
                    hdr["rented"] = j
                if v == "公営の借家" and "public" not in hdr:
                    hdr["public"] = j
        if "total" not in hdr:  # 見出しの「総数」が1つ上の行にある形
            for j in range(d.shape[1]):
                if z(d.iloc[7, j]).startswith("総数"):
                    hdr["total"] = j; break
        assert len(hdr) == 3, (name, hdr)
        for i in range(12, len(d)):
            s = str(d.iloc[i, 1]).strip()
            mm = re.match(r"^(\d{2})(?![\s　]*\d)", s)
            if not mm:
                continue
            code = int(mm.group(1))
            if code == 0:
                continue
            rows.append(dict(year=year, pref=code, total=num(d.iloc[i, hdr["total"]]), rented=num(d.iloc[i, hdr["rented"]]),
                             public=num(d.iloc[i, hdr["public"]])))
    pr = pd.DataFrame(rows).sort_values(["year", "pref"])
    assert pr.groupby("year").size().eq(47).all(), pr.groupby("year").size()
    pr.to_csv(DATA / "tenure_pref.csv", index=False)

    # 第34-1表（家賃）：列 3=総数, 4=専用住宅総数, 5=公営の借家
    d = pd.read_excel(RAW / "ts34_1_rent_japan.xlsx", header=None)
    rows, part = [], None
    for i in range(18, len(d)):
        lab = z(d.iloc[i, 1])
        if "月当たり家賃" in lab:
            part = "monthly"
        elif "畳当たり家賃" in lab:
            part = "per_tatami"
        elif "増減" in lab:
            part = None
        y = num(d.iloc[i, 2])
        if part and not pd.isna(y) and 1970 < y < 2030:
            rows.append(dict(kind=part, year=int(y), all=num(d.iloc[i, 3]), dedicated=num(d.iloc[i, 4]), public=num(d.iloc[i, 5])))
    pd.DataFrame(rows).to_csv(DATA / "rent.csv", index=False)
    print("ok")


if __name__ == "__main__":
    main()
