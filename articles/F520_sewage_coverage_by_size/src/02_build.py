"""公共施設状況調（下水道等の抜き出し）と住民基本台帳人口を、市区町村コードでつなぐ。
data/sewage_pop.csv：year（年度、年度末の処理人口）, code, pref, name, kubun, pop（翌年1月1日の住基人口）, ※東京23区は1行にまとめる,
public_sewer, agri, fishery, forest, simple, small, community_plant, johkaso（いずれも人）"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
COLS = ["public_sewer", "agri", "fishery", "forest", "simple", "small", "community_plant", "johkaso"]
PAIRS = [(2019, "jukijin_2020_municipal.xls"), (2024, "jukijin_2025_municipal.xlsx")]


def norm(s):
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", str(s)))


def same(a, b):
    # 名前の照合（字体の違い：ケ/ヶ、梼/檮、恵/惠 をそろえる）
    f = lambda s: s.replace("ヶ", "ケ").replace("檮", "梼").replace("惠", "恵")
    return f(b).endswith(f(a))


def pop(path):
    d = pd.read_excel(path, header=None, dtype=object)
    out = []
    for i in range(len(d)):
        code = norm(d.iloc[i, 0])
        if re.fullmatch(r"\d{6}", code) and code[2:5] != "000":
            out.append((code, norm(d.iloc[i, 2]), float(d.iloc[i, 5])))
    return pd.DataFrame(out, columns=["code", "pname", "pop"]).drop_duplicates("code")


def main():
    s = pd.read_csv(RAW / "sewage_extract.csv", dtype=str)
    s = s[s.kubun.notna()].copy()  # 都道府県ごとの小計行（区分が空）を除く
    for c in COLS:
        s[c] = pd.to_numeric(s[c].replace("-", None), errors="coerce").fillna(0.0)
    s["year"] = s.year.astype(int)
    rows = []
    for y, pf in PAIRS:
        p = pop(RAW / pf)
        z = s[s.year == y].merge(p, on="code", how="left")
        assert z["pop"].notna().all(), z[z["pop"].isna()][["code", "name"]]
        bad = z[[not same(n, pn) for n, pn in zip(z.name, z.pname)]]  # 住基は町村名の前に郡名がつく
        assert len(bad) == 0, bad[["code", "name", "pname"]]
        rows.append(z.drop(columns="pname"))
    out = pd.concat(rows, ignore_index=True)
    # 東京23区の下水道は東京都が一つで運営し、処理人口は千代田区の行にまとめて載っている。23区を1つの単位にまとめる
    k = out[out.kubun == "特別区"]
    assert len(k) == 2 * 23 and (k[k.name != "千代田区"].public_sewer == 0).all()
    agg = k.groupby("year", as_index=False)[["pop"] + COLS].sum()
    agg["code"] = "131008"; agg["pref"] = "東京都"; agg["name"] = "東京23区（まとめて1つ）"; agg["kubun"] = "特別区"
    out = pd.concat([out[out.kubun != "特別区"], agg], ignore_index=True)
    out = out.sort_values(["year", "code"]).reset_index(drop=True)
    out = out[["year", "code", "pref", "name", "kubun", "pop"] + COLS]
    out.to_csv(ROOT / "data" / "sewage_pop.csv", index=False)
    print(out.groupby("year").size(), out.groupby("year")[["pop"] + COLS].sum().T)


if __name__ == "__main__":
    main()
