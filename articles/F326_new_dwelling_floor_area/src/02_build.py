"""02 整形：利用関係別の新設住宅の戸数・床面積の合計（年計）を縦長の CSV にする（オフライン）。
表の行は1948年（昭和23年）から1年ずつ並ぶ。元号の切り替わりの行で年を確かめる。"""
import pathlib
import pandas as pd, xlrd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
TYPES = ["総計", "持家", "貸家", "給与住宅", "分譲住宅", "分譲マンション", "分譲一戸建"]

def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

def main():
    sh = xlrd.open_workbook(str(RAW / "chakko_ts_riyou_000040405973.xls")).sheet_by_index(0)
    out = []
    for i in range(7, sh.nrows):
        r = sh.row_values(i)
        if num(r[1]) is None:
            break
        y = 1948 + (i - 7)
        lab = str(r[0])
        if lab.startswith("昭和23"): assert y == 1948
        if lab.startswith("平成元"): assert y == 1989
        if lab.startswith("令和元"): assert y == 2019
        for k, t in enumerate(TYPES):
            u, a = num(r[1 + 2 * k]), num(r[2 + 2 * k])
            if u is not None and a is not None:
                out.append((y, t, int(u), a))
    D = pd.DataFrame(out, columns=["year", "type", "units", "floor_m2"])
    D.to_csv(ROOT / "data" / "starts_by_type.csv", index=False)
    chk = D[D.type.isin(["持家", "貸家", "給与住宅", "分譲住宅"])].groupby("year")[["units", "floor_m2"]].sum()
    tot = D[D.type == "総計"].set_index("year")[["units", "floor_m2"]]
    j = chk.join(tot, rsuffix="_tot").dropna()
    print("4区分の合計と総計の差（戸）の最大", int((j.units - j.units_tot).abs().max()), "年", D.year.min(), "-", D.year.max())

if __name__ == "__main__":
    main()
