"""data/raw の第3-11表（2000〜2025年）と第2-4表（2018〜2025年）から長い表を作る。ネットにはつながない。"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

# 第3-11表の31の区分（列の順。どの年も同じ並び）。使うものだけに名前をつける
GROUPS = {0: "dual_all", 12: "dual_nuc", 15: "dual_nuc_wlow", 16: "dual_nuc_whigh",
          18: "dual_couple", 19: "dual_kid1", 20: "dual_kid2",
          27: "single_all", 28: "single_couple", 29: "single_kid1", 30: "single_kid2"}
ITEMS = ["集計世帯数", "世帯人員", "世帯主の年齢", "実収入", "消費支出", "食料", "生鮮魚介", "生鮮肉", "牛乳", "卵", "生鮮野菜",
         "生鮮果物", "調理食品", "主食的調理食品", "他の調理食品", "外食", "一般外食"]


def norm(s):
    s = re.sub(r"\s+", "", str(s))
    s = re.sub(r"^[0-9.]+", "", s)
    return re.sub(r"\((歳|人|%)\)$", "", s)


def num(v):
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return np.nan


def read_table(path, sheet=0):
    x = pd.read_excel(path, sheet_name=sheet, header=None, dtype=str).fillna("")
    base = next(j for j in range(x.shape[1]) if str(x.iat[0, j]).strip() == "1")   # 最初の区分の列
    new = [c for c in range(7, base) if any(str(x.iat[r, c]).strip() == "用途分類" for r in range(16))]
    if new:   # 2020年以降の様式：「用途分類」の列だけが名前
        labels = [norm(x.iat[i, new[0]]) for i in range(len(x))]
    else:     # 2019年までの様式：名前が階層ごとに別の列に入っている
        labels = [norm("".join(str(c) for c in x.iloc[i, 7:base])) for i in range(len(x))]
    return x, base, labels


def first_row(labels, item, start):
    for i in range(start, len(labels)):
        if labels[i] == item or labels[i].endswith(item) and labels[i][: -len(item)] in ("", "人", "円"):
            return i
    raise KeyError(item)


rows = []
for p in sorted(RAW.glob("kakei_3-11_*")):
    y = int(re.search(r"(\d{4})", p.name).group(1))
    x, base, labels = read_table(p)
    start = next(i for i, l in enumerate(labels) if l.startswith("世帯数分布"))
    for item in ITEMS:
        i = first_row(labels, item, start)     # 最初に出てくる行（交際費の中の「食料」より前）
        for k, g in GROUPS.items():
            rows.append({"year": y, "group": g, "item": item, "value": num(x.iat[i, base + k])})
d = pd.DataFrame(rows).sort_values(["group", "item", "year"]).reset_index(drop=True)
d.to_csv(ROOT / "data" / "type_items.csv", index=False)

# 第2-4表：年間収入五分位（勤労者世帯・全国 と 二人以上の世帯・全国）
q = []
for p in sorted(RAW.glob("kakei_2-4_*")):
    y = int(re.search(r"(\d{4})", p.name).group(1))
    for sheet, tag in [("勤労・全国", "worker"), ("二人・全国", "all")]:
        x, base, labels = read_table(p, sheet)
        # base は「平均」の列。五分位 I〜V はその右の5列
        start = next(i for i, l in enumerate(labels) if l.startswith("世帯数分布"))
        for item in ["世帯人員", "実収入", "消費支出", "食料", "生鮮魚介", "生鮮肉", "牛乳", "卵", "生鮮野菜", "生鮮果物",
                     "調理食品", "主食的調理食品", "他の調理食品", "一般外食"]:
            try:
                i = first_row(labels, item, start)
            except KeyError:
                continue
            for k in range(1, 6):
                q.append({"year": y, "sample": tag, "quintile": k, "item": item, "value": num(x.iat[i, base + k])})
q = pd.DataFrame(q).sort_values(["sample", "item", "year", "quintile"]).reset_index(drop=True)
q.to_csv(ROOT / "data" / "quintile_items.csv", index=False)
print("type rows", len(d), "missing", int(d.value.isna().sum()), "| quintile rows", len(q), "missing", int(q.value.isna().sum()))
print(q.groupby(["sample", "item"]).size().to_string())
