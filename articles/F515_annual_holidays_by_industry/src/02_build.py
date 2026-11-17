"""就労条件総合調査の表（2002〜2025年）から、産業大分類・企業規模ごとの「労働者1人平均年間休日総数」と
「120日以上の労働者の割合」を取り出す。data/holidays.csv：year, kind（industry/size/total）, code, name, mean_days, share_120plus"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
SIZES = {"1,000人以上": "1000+", "300～999人": "300-999", "100～299人": "100-299", "30～99人": "30-99"}


def norm(v):
    return re.sub(r"\s", "", unicodedata.normalize("NFKC", str(v)))


def nums(row):
    out = []
    for v in row:
        s = norm(v)
        if s in ("-", "－"):
            out.append(0.0)
            continue
        try:
            out.append(float(s))
        except ValueError:
            pass
    return out


def main():
    recs = []
    for f in sorted(RAW.glob("holidays_worker_*")):
        y = int(re.search(r"(\d{4})", f.name).group(1))
        d = pd.read_excel(f, header=None)
        in_total = False
        for i in range(len(d)):
            row = d.iloc[i].tolist()
            cells = [norm(v) for v in row if norm(v) not in ("nan", "")]
            if not cells:
                continue
            first = cells[0]
            # 2022年の表は「Ｃ 鉱業…」「＜Ｔ 調査産業計＞」のように記号と名前が1つの欄にある
            m = re.fullmatch(r"<?([C-RT])([^\dA-Za-z].*?)>?", first)
            if m and len(m.group(2)) > 1:
                cells = [m.group(1), m.group(2)] + cells[1:]
                first = m.group(1)
            v = nums(row)
            # 数字の並び：100（計）、8つの階級、（不明など）、平均。最後が平均、9〜10番目までが階級
            if first == "T" and len(cells) > 1:
                in_total = True
                k = v.index(100.0)
                cl = v[k + 1:k + 9]
                recs.append((y, "total", "T", "調査計", v[-1], sum(cl[6:8]), sum(cl[0:4])))
                continue
            name = norm(cells[0])
            if in_total and name in {norm(s) for s in SIZES}:
                k = v.index(100.0)
                cl = v[k + 1:k + 9]
                recs.append((y, "size", SIZES[[s for s in SIZES if norm(s) == name][0]], name, v[-1], sum(cl[6:8]), sum(cl[0:4])))
                continue
            if re.fullmatch(r"[C-RD-R]", first) and len(cells) > 1:
                in_total = False
                k = v.index(100.0)
                cl = v[k + 1:k + 9]
                recs.append((y, "industry", first, re.sub(r"[　 ]", "", cells[1]), v[-1], sum(cl[6:8]), sum(cl[0:4])))
    out = pd.DataFrame(recs, columns=["year", "kind", "code", "name", "mean_days", "share_120plus", "share_under100"])
    out = out.drop_duplicates(["year", "kind", "code"], keep="first").sort_values(["kind", "code", "year"]).reset_index(drop=True)
    out.to_csv(ROOT / "data" / "holidays.csv", index=False)


if __name__ == "__main__":
    main()
