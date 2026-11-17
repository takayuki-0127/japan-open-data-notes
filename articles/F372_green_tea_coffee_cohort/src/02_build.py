"""02_build.py : 家計調査（二人以上の世帯）の年報から、茶・コーヒーの年齢階級別と時系列の表を作る。
- data/by_age.csv : 年、年齢階級、品目、支出金額（円）、購入数量（g）
- data/national.csv : 年、品目、支出金額、購入数量（全国平均、2000〜2025年）
"""
import pathlib
import re
import unicodedata

import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
ITEMS = {"380": "緑茶", "382": "コーヒー", "38X": "茶飲料", "384": "コーヒー飲料", "381": "紅茶", "383": "他の茶葉"}
AGES = ["29歳以下", "30〜39歳", "40〜49歳", "50〜59歳", "60〜69歳", "70歳以上"]
OLD_AGE_KEYS = ["～29", "30～39", "40～49", "50～59", "60～69", "70歳～"]


def n(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s)))


def num(x):
    v = pd.to_numeric(x, errors="coerce")
    return None if pd.isna(v) else float(v)


def old_layout(path):
    v = pd.read_excel(path, sheet_name="飲料", header=None)
    sub = [n(v.iat[14, c]) for c in range(v.shape[1])]
    groups = []
    for c in range(10, v.shape[1]):
        if sub[c] == "金額":
            groups.append([c])
        elif sub[c] in ("数量", "価格") and groups:
            groups[-1].append(c)
    cols = {}
    for g in groups:
        head = "".join(n(v.iat[r, c]) for c in g for r in range(5, 14))
        jp = re.sub(r"[A-Za-z]{2,}|[a-z&().,/]+", " ", head)
        codes = re.findall(r"(?<![0-9A-Z])(38[0-9A-Y])(?![0-9A-Z])", jp)
        if len(codes) == 1 and codes[0] in ITEMS:
            amt = g[0]
            qty = next((c for c in g if sub[c] == "数量"), None)
            cols[codes[0]] = (amt, qty)
    assert set(cols) >= {"380", "382", "38X", "384"}, (path.name, cols)
    lab = [n("".join(n(x) for x in v.iloc[r, 0:10])) for r in range(v.shape[0])]
    # 時系列（農林漁家を含む 2000 年以降。2000年は2行あり、後の行が含む値）
    ts = {}
    age_start = next(i for i, l in enumerate(lab) if l.startswith("世帯主の年齢階級"))
    freq_start = next(i for i, l in enumerate(lab) if "購入頻度" in l)
    for r in range(15, freq_start):
        m = re.search(r"((?:19|20)\d{2})(Total)?$", lab[r])
        if m:
            ts[int(m.group(1))] = r  # 同じ年は後の行で上書き
    rows = {}
    rows["平均"] = next(i for i in range(age_start, len(lab)) if lab[i].startswith("二人以上の世帯平均"))
    for a, k in zip(AGES, OLD_AGE_KEYS):
        rows[a] = next(i for i in range(age_start, len(lab)) if lab[i].startswith(n(k)))
    return v, cols, rows, ts


def new_layout(path):
    v = pd.read_excel(path, sheet_name="二人", header=None)
    head = [n(v.iat[8, c]) for c in range(v.shape[1])]
    keymap = {"平均": "平均", "29歳以下": "29歳以下", "30～39歳": "30〜39歳", "40～49歳": "40〜49歳",
              "50～59歳": "50〜59歳", "60～69歳": "60〜69歳", "70歳以上": "70歳以上"}
    cols = {}
    for c, h in enumerate(head):
        if "・" in h and not h.startswith("(再掲)"):
            a, kind = h.split("・", 1)
            km = {n(k): x for k, x in keymap.items()}
            if a in km and kind in ("支出金額", "購入数量"):
                cols.setdefault(km[a], {})[kind] = c
    code = [n(x) for x in v[10]]
    assert len(cols) == 7, cols
    out = []
    for cd, item in ITEMS.items():
        r = code.index(cd)
        assert n(v.iat[r, 11]) == n(item) or item in n(v.iat[r, 11]), (cd, v.iat[r, 11])
        for a, cc in cols.items():
            out.append({"year": 2025, "age": a, "item": item, "amount": num(v.iat[r, cc["支出金額"]]),
                        "qty_g": num(v.iat[r, cc["購入数量"]])})
    return out


def main():
    rows, nat = [], {}
    files = {2013: "fies_2013_beverages.xls", 2014: "fies_2014_beverages.xls", 2015: "fies_2015_beverages.xls",
             2023: "fies_2023_beverages.xls", 2024: "fies_2024_beverages.xls"}
    for y, f in files.items():
        v, cols, rws, ts = old_layout(RAW / f)
        for a, r in rws.items():
            for cd, (ca, cq) in cols.items():
                rows.append({"year": y, "age": a, "item": ITEMS[cd], "amount": num(v.iat[r, ca]),
                             "qty_g": num(v.iat[r, cq]) if cq is not None else None})
        for ty, r in ts.items():
            if ty < 2000:
                continue
            for cd, (ca, cq) in cols.items():
                nat[(ty, ITEMS[cd], y)] = (num(v.iat[r, ca]), num(v.iat[r, cq]) if cq is not None else None)
    rows += new_layout(RAW / "fies_2025_age_4_6.xlsx")
    d = pd.DataFrame(rows)
    d["age"] = pd.Categorical(d["age"], ["平均"] + AGES, ordered=True)
    d = d.sort_values(["item", "year", "age"]).reset_index(drop=True)
    d.to_csv(BASE / "data" / "by_age.csv", index=False)
    # 全国の時系列：その年を含む最も新しい年報の値を使う（2025年は2025年の表の平均）
    recs = {}
    for (ty, item, src), (a, q) in sorted(nat.items(), key=lambda k: k[0][2]):
        recs[(ty, item)] = {"year": ty, "item": item, "amount": a, "qty_g": q, "source_year": src}
    t = pd.DataFrame(recs.values())
    a25 = d[(d.year == 2025) & (d.age == "平均")]
    for _, r in a25.iterrows():
        t = pd.concat([t, pd.DataFrame([{"year": 2025, "item": r["item"], "amount": r["amount"],
                                         "qty_g": r["qty_g"], "source_year": 2025}])])
    t = t.sort_values(["item", "year"]).reset_index(drop=True)
    t.to_csv(BASE / "data" / "national.csv", index=False)
    # 年報どうしの重なる年の値が同じかを確かめる
    chk = []
    for (ty, item, src), (a, q) in nat.items():
        chk.append({"year": ty, "item": item, "src": src, "amount": a})
    c = pd.DataFrame(chk).pivot_table(index=["year", "item"], columns="src", values="amount")
    c.to_csv(BASE / "data" / "overlap_check.csv")
    print(d[d.item == "緑茶"].head(14))
    print(t[t.item == "緑茶"])


if __name__ == "__main__":
    main()
