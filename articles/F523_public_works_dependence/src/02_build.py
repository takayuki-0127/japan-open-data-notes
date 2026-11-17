"""建設総合統計の年度報（表2・表4）と県内総生産から、都道府県×年度の表 data/pref_year.csv を作る（百万円、名目）。
列：year, code, pref, total（建設の出来高の総計）, private（民間）, public（公共）, public4（表4の公共の合計）, disaster（表4の災害復旧）, gdp（県内総生産）"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PREFS = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
         "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
         "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
         "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]
STEM = {(p if p == "北海道" else p[:-1]): p for p in PREFS}
FILES = {1996: "nendo_1996.xls", 2005: "nendo_2005.xls", 2015: "nendo_2015.xlsx", 2023: "nendo_2023.xlsx"}


def norm(s):
    return re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", str(s)))


def pref_of(s):
    t = re.sub(r"^\d+\.", "", norm(s))
    if t in STEM:  # 「京都」「東京」のように、末尾の字を取らずにそのまま当たる名前
        return STEM[t]
    return STEM.get(re.sub(r"[都府県]$", "", t))


def table2(path):
    d = pd.read_excel(path, sheet_name="表２", header=None, dtype=object)
    # 年度計の列：見出しの行（2〜4行目）に「年度計」または「計」とある最初の列
    col = next(j for j in range(d.shape[1]) if any(norm(d.iloc[i, j]) in ("計",) or "年度計" in norm(d.iloc[i, j]) for i in range(2, 5)))
    out, cur = {}, None
    for i in range(5, len(d)):
        c0, c1 = norm(d.iloc[i, 0]), norm(d.iloc[i, 1])
        p = pref_of(c0)
        if p:
            cur = p
            out[p] = {}
            if c1 in ("nan", "総計"):
                out[p]["total"] = float(d.iloc[i, col])
            continue
        if cur is None:
            continue
        lab = c1
        if lab == "総計":
            out[cur]["total"] = float(d.iloc[i, col])
        elif lab == "民間" and "private" not in out[cur]:
            out[cur]["private"] = float(d.iloc[i, col])
        elif lab == "公共" and "public" not in out[cur]:
            out[cur]["public"] = float(d.iloc[i, col])
    t = pd.DataFrame(out).T
    assert len(t) == 47 and t.notna().all().all(), t
    assert ((t.private + t.public - t.total).abs() <= 2).all(), (t.private + t.public - t.total).abs().max()
    return t


def table4(path):
    d = pd.read_excel(path, sheet_name="表４", header=None, dtype=object)
    out = {}
    hdr = None
    for i in range(len(d)):
        row = [norm(v) for v in d.iloc[i].tolist()]
        ps = {j: pref_of(v) for j, v in enumerate(row) if pref_of(v)}
        if len(ps) >= 3:
            hdr = ps
            for p in ps.values():
                out.setdefault(p, {})
            continue
        if hdr is None:
            continue
        lab = "".join(x for x in row[:3] if x != "nan" and not x.isdigit())
        key = "public4" if lab.endswith("合計") else ("disaster" if "災害復旧" in lab else None)
        if key:
            for j, p in hdr.items():
                if key not in out[p]:
                    out[p][key] = float(d.iloc[i, j])
    t = pd.DataFrame(out).T
    assert len(t) == 47 and t.notna().all().all(), t
    return t


def gdp():
    rows = []
    for f, ys in [("gdp_1996_2009.xls", [1996, 2005]), ("gdp_2011_2023.xlsx", [2015, 2023])]:
        d = pd.read_excel(RAW / f, sheet_name=0, header=None, dtype=object)
        yrow = next(i for i in range(10) if any(norm(v) == str(ys[0]) for v in d.iloc[i]))
        cols = {int(norm(v)): j for j, v in enumerate(d.iloc[yrow]) if re.fullmatch(r"\d{4}", norm(v))}
        for i in range(yrow + 1, len(d)):
            p = pref_of(d.iloc[i, 1])
            if p and re.fullmatch(r"\d{2}", norm(d.iloc[i, 0])):
                for y in ys:
                    rows.append({"year": y, "pref": p, "gdp": float(d.iloc[i, cols[y]])})
    g = pd.DataFrame(rows).drop_duplicates(["year", "pref"])
    assert len(g) == 47 * 4
    return g


def main():
    parts = []
    for y, f in FILES.items():
        t = table2(RAW / f).join(table4(RAW / f))
        t["year"] = y
        parts.append(t.rename_axis("pref").reset_index())
    d = pd.concat(parts).merge(gdp(), on=["year", "pref"], validate="1:1")
    d["code"] = d.pref.map({p: f"{i + 1:02d}" for i, p in enumerate(PREFS)})
    d = d[["year", "code", "pref", "total", "private", "public", "public4", "disaster", "gdp"]].sort_values(["year", "code"])
    d.to_csv(ROOT / "data" / "pref_year.csv", index=False, float_format="%.0f")
    print(d.groupby("year")[["total", "public", "public4", "disaster", "gdp"]].sum())


if __name__ == "__main__":
    main()
