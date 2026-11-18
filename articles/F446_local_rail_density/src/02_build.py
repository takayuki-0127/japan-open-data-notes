"""02 整形：鉄道統計年報（２）から、事業者×年度の旅客人キロ（定期・定期外・合計）と平均通過数量（旅客）を抜き出し、
地域鉄道事業者一覧（98社）と名前で合わせる。出力：data/operator_year.csv（全事業者）、data/chiiki_panel.csv（98社のうち合ったもの）"""
import pathlib, re, unicodedata
import numpy as np, pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
BUREAUS = ["北海道", "東北", "北陸信越", "関東", "中部", "近畿", "中国", "四国", "九州", "沖縄"]
# 年報の名前 → 一覧の名前（名前の変化・表記ゆれ）
ALIAS = {"東海交通事業": "JR東海交通事業", "北近畿タンゴ鉄道": "WILLERTRAINS", "WILLERTRAINS": "WILLERTRAINS"}


def norm(x):
    return re.sub(r"[\s　]", "", unicodedata.normalize("NFKC", str(x)))


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return np.nan


def parse(fy):
    d = pd.read_excel(RAW / f"nenpo_{fy}_t02.xlsx", sheet_name=0, header=None)
    rows, bureau = [], None
    for _, r in d.iterrows():
        if pd.isna(r[0]):
            continue
        lab = norm(r[0])
        m = re.match(r"(.+?)運輸局$", lab)
        if m:
            bureau = m.group(1); continue
        if lab == "沖縄総合事務局":
            bureau = "沖縄"; continue
        if lab.startswith("(") or "計" in lab or lab in ("事業者名",) or "運輸成績表" in lab:
            continue
        if np.isnan(num(r[2])):
            continue
        rows.append({"fy": fy, "bureau_in_table": bureau, "name": lab, "pk_pass": num(r[6]), "pk_nonpass": num(r[7]),
                     "pk_total": num(r[8]), "density": num(r[12])})
    return pd.DataFrame(rows)


def parse_km(fy):
    """（４）から年度末営業キロ（旅客）。事業者の行（1列目に名前がある行）だけを使う"""
    d = pd.read_excel(RAW / f"nenpo_{fy}_t04.xlsx", sheet_name=0, header=None)
    rows = []
    for _, r in d.iterrows():
        if pd.isna(r[0]):
            continue
        lab = norm(r[0])
        if lab.endswith("運輸局") or lab.startswith("(") or "計" in lab or lab in ("事業者名", "沖縄総合事務局") or "営業キロ" in lab:
            continue
        v = num(r[2])
        if np.isnan(v):
            continue
        rows.append({"fy": fy, "name": lab, "km_end": v})
    return pd.DataFrame(rows).drop_duplicates(["fy", "name"])


def main():
    lst = pd.read_csv(RAW / "chiiki_tetsudo_list.csv")
    lst["key"] = lst["name"].map(norm)
    allrows = pd.concat([parse(fy) for fy in range(2012, 2024)], ignore_index=True)
    km = pd.concat([parse_km(fy) for fy in range(2012, 2024)], ignore_index=True)
    allrows = allrows.merge(km, on=["fy", "name"], how="left", validate="many_to_one")
    days = allrows["fy"].map(lambda y: 366 if (y + 1) % 4 == 0 else 365)  # 年度に2月29日を含む年
    allrows["density_calc"] = allrows["pk_total"] * 1000 / (allrows["km_end"] * days)
    allrows.to_csv(ROOT / "data" / "operator_year.csv", index=False, encoding="utf-8")
    allrows["key"] = allrows["name"].map(lambda s: ALIAS.get(s, s))
    m = allrows.merge(lst[["key", "km", "third_sector"]], on="key", how="inner")
    # 同じ事業者が同じ年度に2行あるとき（名前の変化の重なりなど）は人キロの大きい行を使う
    m = m.sort_values(["key", "fy", "pk_total"], ascending=[True, True, False]).drop_duplicates(["key", "fy"])
    # 運輸局：一覧には運輸局がないので、年報の運輸局の見出しから（2012・2013年度の表には見出しがないので、ほかの年度の値を使う）
    b = m.dropna(subset=["bureau_in_table"]).groupby("key")["bureau_in_table"].agg(lambda s: s.mode().iloc[0])
    m["bureau"] = m["key"].map(b)
    m = m[["key", "third_sector", "km", "bureau", "fy", "pk_pass", "pk_nonpass", "pk_total", "km_end", "density", "density_calc"]].sort_values(["key", "fy"])
    m.to_csv(ROOT / "data" / "chiiki_panel.csv", index=False, encoding="utf-8")
    miss = sorted(set(lst["key"]) - set(m["key"]))
    print("一覧98社のうち年報で見つかった事業者：", m["key"].nunique(), " 見つからない：", miss)
    print(m.groupby("fy").size().to_dict())


if __name__ == "__main__":
    main()
