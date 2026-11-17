"""data/raw の14年分の表を、年×地域×用途の縦長の表（data/conversion_long.csv）にする。単位 ha。"""
import pathlib, re
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
KEY = {("総数", ""): "total", ("住宅用地", "総数"): "housing", ("公的施設用地", "総数"): "public",
       ("工鉱業（工場）用地", ""): "factory", ("商業サービス等用地", "総数"): "commerce", ("その他の業務用地", "総数"): "other_business",
       ("その他の業務用地", "農林漁業用施設"): "agri_facility", ("その他の業務用地", "駐車場・資材置場"): "parking",
       ("その他の業務用地", "土石等採取用地"): "quarry", ("その他の業務用地", "再エネ発電設備"): "renewable",
       ("その他の業務用地", "その他"): "ob_other", ("植林", ""): "forest", ("その他分類不能不明", ""): "unknown"}
BLOCKS = ["北海道", "東北", "関東", "北陸", "東山", "東海", "近畿", "中国", "四国", "九州", "沖縄"]


def z(s):
    return "" if str(s) == "nan" else re.sub(r"[\s　\n]", "", str(s))


def main():
    rows = []
    for f in sorted(RAW.glob("conv_use_*.xls*")):
        year = int(re.search(r"(\d{4})", f.name).group(1))
        d = pd.read_excel(f, header=None)
        grp, cols = "", {}
        for j in range(1, d.shape[1]):
            g, s = z(d.iloc[6, j]), z(d.iloc[7, j])
            if g:
                grp = g
            k = KEY.get((grp, s))
            if k and k not in cols:
                cols[k] = j
        assert {"total", "housing", "other_business", "ob_other"} <= set(cols), (f.name, cols)
        seen = {}
        for i in range(8, len(d)):
            name = z(d.iloc[i, 0])
            if not name or name.startswith("注") or "資料" in name:
                continue
            seen[name] = seen.get(name, 0) + 1
            if name in ("北海道", "沖縄"):
                level = "block" if seen[name] == 1 else "pref"
            elif name in ("全国", "都府県"):
                level = "national" if name == "全国" else "subtotal"
            elif name in BLOCKS:
                level = "block"
            else:
                level = "pref"
            for k, j in cols.items():
                v = pd.to_numeric(str(d.iloc[i, j]).replace(",", ""), errors="coerce")
                if str(d.iloc[i, j]).strip() in ("-", "－"):
                    v = 0.0
                rows.append(dict(year=year, level=level, region=name, use=k, ha=v))
    df = pd.DataFrame(rows)
    # 北海道・沖縄は「ブロック」の行しかない年もあるので、都道府県にも入れる
    for y in df.year.unique():
        for nm in ("北海道", "沖縄"):
            if not ((df.year == y) & (df.level == "pref") & (df.region == nm)).any():
                add = df[(df.year == y) & (df.level == "block") & (df.region == nm)].copy()
                add["level"] = "pref"
                df = pd.concat([df, add])
    df = df.sort_values(["year", "level", "region", "use"], kind="mergesort").reset_index(drop=True)
    df.to_csv(DATA / "conversion_long.csv", index=False)
    print(df.groupby(["year", "level"]).region.nunique().unstack())


if __name__ == "__main__":
    main()
