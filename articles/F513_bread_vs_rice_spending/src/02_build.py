"""家計調査 第4-6表（2002〜2025年）から、穀類の品目の1世帯当たり年間の支出金額・購入数量・平均価格を取り出す。
data/grain.csv：year, group（平均・年齢階級）, item, freq, amount（円）, qty, price
data/household.csv：year, group, persons（世帯人員）"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
GROUPS = ["平均", "29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
ITEMS = {"食料": "food", "穀類": "grains", "米": "rice", "パン": "bread", "食パン": "plain_bread", "他のパン": "other_bread",
         "めん類": "noodles", "麺類": "noodles"}
PH = {"...", "…", "-", "－", "***", "x", "X"}


def norm(v):
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", str(v)))


def cells_after(row, j):
    """品目名の右の値。先頭の単位（円など）や空欄は飛ばし、数字と「...」のような印だけを順に返す。"""
    out, started = [], False
    for v in row[j + 1:]:
        s = norm(v)
        if s in ("nan", ""):
            if started:
                out.append(None)
            continue
        if s in PH:
            out.append(None); started = True; continue
        try:
            out.append(float(s.replace(",", ""))); started = True
        except ValueError:
            if started:
                break
    return out


def main():
    recs, hh = [], []
    for f in sorted(RAW.glob("kakei_4-6_*")):
        y = int(re.search(r"(\d{4})", f.name).group(1))
        d = pd.read_excel(f, header=None)
        found = set()
        for i in range(len(d)):
            row = d.iloc[i].tolist()
            names = [(j, norm(v)) for j, v in enumerate(row[:15])]
            hit = [(j, n) for j, n in names if n in ITEMS]
            pers = [(j, n) for j, n in names if n.startswith("世帯人員")]
            if pers and y not in [h[0] for h in hh]:
                j = pers[0][0]
                vals = [v for v in cells_after(row, j) if v is not None]
                avg = vals[0]  # 平均の列が最初の数字
                hh.append((y, "平均", avg))
            if not hit:
                continue
            j, n = hit[0]
            key = ITEMS[n]
            if key in found:
                continue
            found.add(key)
            vals = cells_after(row, j)
            # 「パン」は「食パン」「他のパン」より先に出る大分類の行。めん類は名前が年で変わる
            for g, name in enumerate(GROUPS):
                q = vals[4 * g:4 * g + 4]
                recs.append((y, name, key, *q))
        assert {"rice", "bread", "plain_bread", "other_bread", "grains", "food"} <= found, (y, found)
    out = pd.DataFrame(recs, columns=["year", "group", "item", "freq", "amount", "qty", "price"])
    out = out.sort_values(["item", "group", "year"]).reset_index(drop=True)
    out.to_csv(ROOT / "data" / "grain.csv", index=False)
    pd.DataFrame(hh, columns=["year", "group", "persons"]).sort_values("year").to_csv(ROOT / "data" / "household.csv", index=False)


if __name__ == "__main__":
    main()
