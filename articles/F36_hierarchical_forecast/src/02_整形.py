"""02 整形：47都道府県の月次（下の段）から、全国・10地方・47都道府県の58系列を作る。
あわせて、公表の「全国」と47都道府県の合計が一致するか（足し算が合っているか）を確かめる。"""
import pandas as pd
from common import load, all_series, RAW, DATA, REGIONS
if __name__ == "__main__":
    rows = []
    for col in ["total", "japanese", "foreign"]:
        Y, S, names, level = all_series(load(col))
        Y.to_csv(DATA / f"series58_{col}.csv", encoding="utf-8")
        d = pd.read_csv(RAW / "lodging_pref_monthly_2011_2025.csv")
        nat = d[d.pref == "全国"].set_index(pd.to_datetime(dict(year=d[d.pref == "全国"].year, month=d[d.pref == "全国"].month, day=1)))[col]
        diff = (Y["全国"] - nat.reindex(Y.index)).abs()
        rows.append((col, int(diff.max()), float((diff / nat.reindex(Y.index)).max())))
    pd.DataFrame(rows, columns=["系列", "公表の全国との差の最大（人泊）", "差の割合の最大"]).to_csv(DATA / "check_national.csv", index=False)
    pd.DataFrame([(r, p) for r, ps in REGIONS.items() for p in ps], columns=["地方", "都道府県"]).to_csv(DATA / "regions.csv", index=False)
    print(open(DATA / "check_national.csv").read())
