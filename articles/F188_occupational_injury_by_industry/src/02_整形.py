"""02 整形：取得した3つの表を、分析しやすい縦長の表に直す。
入力：data/dosu_kyodo_rate.csv（労働災害動向調査・度数率と強度率）、data/sennin_rate.csv（年千人率）、data/employees_lfs.csv（労働力調査・産業別雇用者数）
出力：data/tidy_dosu.csv, data/tidy_sennin.csv
"""
from pathlib import Path
import pandas as pd

D = Path(__file__).resolve().parents[1] / "data"
NAME = {"total": "調査産業計", "forestry": "林業（農業，林業）", "fishery": "漁業", "mining": "鉱業",
        "constr_gen": "建設業（総合工事業）", "constr_spec": "建設業（職別・設備工事業）", "manuf": "製造業",
        "util": "電気・ガス・水道業", "transport": "運輸業", "trade": "卸売・小売業", "service": "サービス業（一部）"}


def num(x):
    if pd.isna(x):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None  # 「x」秘匿・「-」該当なし・「・」項目なし は欠測


def main():
    w = pd.read_csv(D / "dosu_kyodo_rate.csv", dtype=str)
    rows = []
    for _, r in w.iterrows():
        for k, nm in NAME.items():
            fr, sr = num(r[f"{k}_fr"]), num(r[f"{k}_sr"])
            if fr is None:
                continue
            rows.append(dict(size=r["size"], year=int(r["year"]), old_scope=int(r["old_scope"]), ind=k, ind_ja=nm, fr=fr, sr=sr))
    t = pd.DataFrame(rows).sort_values(["size", "ind", "old_scope", "year"])
    t.to_csv(D / "tidy_dosu.csv", index=False)

    s = pd.read_csv(D / "sennin_rate.csv").melt("year", var_name="ind_ja", value_name="rate")
    s.to_csv(D / "tidy_sennin.csv", index=False)
    print(len(t), len(s))


if __name__ == "__main__":
    main()
