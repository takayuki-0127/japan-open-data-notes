"""ラスパイレス指数の団体別のファイル（4つの年×都道府県・指定都市・市区町村）を1つの表 data/laspeyres.csv にまとめる。
列：year, kubun（1都道府県 2指定都市 3市 4特別区 5町 6村）, code（6桁）, pref, name, ruiji（類似団体の区分）, las（ラスパイレス指数）,
las_ref（2013年は国の特例減額がないとした参考値。他の年は las と同じ）, las_actual（2013年の実際の指数）, las_adj（地域手当補正後。ある年だけ）, pop2025（住基）"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
YEARS = [2008, 2013, 2018, 2025]


def norm(s):
    return re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", str(s)))


def num(v):
    s = norm(v)
    return float("nan") if s in ("", "-", "nan", "…") else float(s)


def read(path):
    d = pd.read_excel(path, header=None, dtype=object)
    h = next(i for i in range(15) if any(norm(v) == "団体区分番号" for v in d.iloc[i]))
    kc = next(j for j, v in enumerate(d.iloc[h]) if norm(v) == "団体区分番号")
    lab = {j: "".join(norm(d.iloc[i, j]) for i in range(h, min(h + 3, len(d))) if norm(d.iloc[i, j]) != "nan") for j in range(d.shape[1])}
    lc = next(j for j in range(kc, d.shape[1]) if lab[j].startswith("ラスパイレス指数"))
    rc = next((j for j in range(lc + 1, d.shape[1]) if lab[j].startswith("参考値")), None)
    ac = next((j for j in range(lc + 1, d.shape[1]) if "地域手当補正後" in lab[j]), None)
    muni = lc - kc == 5  # 市区町村は「都道府県」「団体名」「類似団体」の3列がある
    rows = []
    for i in range(h + 1, len(d)):
        k = norm(d.iloc[i, kc])
        if not re.fullmatch(r"[1-6]", k):
            continue
        rows.append({"kubun": int(k), "code": norm(d.iloc[i, kc + 1]).zfill(6),
                     "pref": norm(d.iloc[i, kc + 2]) if muni else norm(d.iloc[i, kc + 2]),
                     "name": norm(d.iloc[i, kc + 3]) if muni else norm(d.iloc[i, kc + 2]),
                     "ruiji": norm(d.iloc[i, kc + 4]) if muni else "",
                     "las_actual": num(d.iloc[i, lc]), "las_ref": num(d.iloc[i, rc]) if rc is not None else num(d.iloc[i, lc]),
                     "las_adj": num(d.iloc[i, ac]) if ac is not None else float("nan")})
    return pd.DataFrame(rows)


def pop2025():
    d = pd.read_excel(RAW / "jukijin_2025_municipal.xlsx", header=None, dtype=object)
    out = {}
    for i in range(len(d)):
        c = norm(d.iloc[i, 0])
        if re.fullmatch(r"\d{6}", c):
            out.setdefault(c, num(d.iloc[i, 5]))
    return out


def main():
    parts = []
    for y in YEARS:
        for kind in ["pref", "seirei", "muni"]:
            f = next(RAW.glob(f"laspeyres_{y}_{kind}.xls*"))
            t = read(f)
            t.insert(0, "year", y)
            parts.append(t)
    d = pd.concat(parts, ignore_index=True)
    d["las"] = d.las_ref
    p = pop2025()
    d["pop2025"] = d.code.map(p)
    d.loc[d.kubun == 1, "pop2025"] = float("nan")
    d = d[["year", "kubun", "code", "pref", "name", "ruiji", "las", "las_ref", "las_actual", "las_adj", "pop2025"]]
    d.to_csv(ROOT / "data" / "laspeyres.csv", index=False)
    print(d.groupby(["year", "kubun"]).size().unstack()); print(d.groupby("year")[["las", "las_actual", "las_adj"]].median())
    m25 = d[(d.year == 2025) & (d.kubun >= 2)]
    print("2025 人口なし:", m25[m25.pop2025.isna()][["code", "name"]].values.tolist())


if __name__ == "__main__":
    main()
