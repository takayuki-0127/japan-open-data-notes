"""02_build.py : 家計調査（二人以上の世帯）の年報から、生鮮魚介・鮮魚・生鮮肉の年齢階級別と時系列の表を作る。
- data/by_age.csv : 年、年齢階級、品目、支出金額（円）、購入数量（g）
- data/national.csv : 年、品目、支出金額、購入数量、農林漁家世帯を含むか
"""
import pathlib
import re
import unicodedata

import pandas as pd
import xlrd.formatting as xf

BASE = pathlib.Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
AGES = ["29歳以下", "30〜39歳", "40〜49歳", "50〜59歳", "60〜69歳", "70歳以上"]
OLD_AGE_KEYS = ["～29", "30～39", "40～49", "50～59", "60～69", "70歳～"]
WANT = {"生鮮魚介": "生鮮魚介", "鮮魚": "鮮魚", "生鮮肉": "生鮮肉"}

# 一部の年の .xls は書式の記録に壊れた文字があり xlrd が止まるため、書式（数値の表示形式）だけ読み飛ばす
_orig = xf.handle_format


def handle_format(self, data, rectype=xf.XL_FORMAT):
    try:
        return _orig(self, data, rectype)
    except UnicodeDecodeError:
        return None


xf.handle_format = handle_format


def n(s):
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s)))


def num(x):
    v = pd.to_numeric(x, errors="coerce")
    return None if pd.isna(v) else float(v)


def old_layout(path, sheet):
    v = pd.read_excel(path, sheet_name=sheet, header=None)
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
        jp = re.sub(r"[0-9A-Za-z~･・()&.,/ ]+", "", head)
        if jp in WANT and len(g) == 3:
            cols[WANT[jp]] = (g[0], next(c for c in g if sub[c] == "数量"))
    lab = [n("".join(n(x) for x in v.iloc[r, 0:10])) for r in range(v.shape[0])]
    age_start = next(i for i, l in enumerate(lab) if l.startswith("世帯主の年齢階級"))
    freq_start = next(i for i, l in enumerate(lab) if "購入頻度" in l)
    ts = []
    for r in range(15, freq_start):
        m = re.search(r"((?:19|20)\d{2})(Total)?$", lab[r])
        if m:
            ts.append((int(m.group(1)), r))
    rows = {"平均": next(i for i in range(age_start, len(lab)) if lab[i].startswith("二人以上の世帯平均"))}
    for a, k in zip(AGES, OLD_AGE_KEYS):
        rows[a] = next(i for i in range(age_start, len(lab)) if lab[i].startswith(n(k)))
    return v, cols, rows, ts


def new_layout(path):
    v = pd.read_excel(path, sheet_name="二人", header=None)
    head = [n(v.iat[8, c]) for c in range(v.shape[1])]
    keymap = {n(k): x for k, x in {"平均": "平均", "29歳以下": "29歳以下", "30～39歳": "30〜39歳", "40～49歳": "40〜49歳",
                                    "50～59歳": "50〜59歳", "60～69歳": "60〜69歳", "70歳以上": "70歳以上"}.items()}
    cols = {}
    for c, h in enumerate(head):
        if "・" in h and not h.startswith("(再掲)"):
            a, kind = h.split("・", 1)
            if a in keymap and kind in ("支出金額", "購入数量"):
                cols.setdefault(keymap[a], {})[kind] = c
    assert len(cols) == 7, cols
    names = [n(x) for x in v[11]]
    out = []
    for item in WANT.values():
        r = names.index(item)
        for a, cc in cols.items():
            out.append({"year": 2025, "age": a, "item": item, "amount": num(v.iat[r, cc["支出金額"]]),
                        "qty_g": num(v.iat[r, cc["購入数量"]])})
    return out


def main():
    rows, nat = [], {}
    for y in range(2013, 2025):
        for kind, sheet in [("fish", "魚介類"), ("meat", "肉類")]:
            v, cols, rws, ts = old_layout(RAW / f"fies_{y}_{kind}.xls", sheet)
            need = ["生鮮魚介", "鮮魚"] if kind == "fish" else ["生鮮肉"]
            assert all(k in cols for k in need), (y, kind, cols)
            for a, r in rws.items():
                for item in need:
                    ca, cq = cols[item]
                    rows.append({"year": y, "age": a, "item": item, "amount": num(v.iat[r, ca]), "qty_g": num(v.iat[r, cq])})
            # 1999年以前は農林漁家世帯を除く値。2000年が2行ある表では、前の行が除く値、後の行が含む値
            n2000 = sum(1 for ty, _ in ts if ty == 2000)
            seen = {}
            for ty, r in ts:
                if ty < 2000 or (ty == 2000 and n2000 == 2 and ty not in seen):
                    farm = "除く"
                else:
                    farm = "含む"
                seen[ty] = 1
                for item in need:
                    ca, cq = cols[item]
                    nat[(ty, farm, item, y)] = (num(v.iat[r, ca]), num(v.iat[r, cq]))
    rows += new_layout(RAW / "fies_2025_age_4_6.xlsx")
    d = pd.DataFrame(rows)
    d["age"] = pd.Categorical(d["age"], ["平均"] + AGES, ordered=True)
    d = d.sort_values(["item", "year", "age"]).reset_index(drop=True)
    d.to_csv(BASE / "data" / "by_age.csv", index=False)
    recs = {}
    for (ty, farm, item, src), (a, q) in sorted(nat.items(), key=lambda k: k[0][3]):
        recs[(ty, farm, item)] = {"year": ty, "farm_households": farm, "item": item, "amount": a, "qty_g": q, "source_year": src}
    t = pd.DataFrame(recs.values())
    for _, r in d[(d.year == 2025) & (d.age == "平均")].iterrows():
        t = pd.concat([t, pd.DataFrame([{"year": 2025, "farm_households": "含む", "item": r["item"], "amount": r["amount"],
                                         "qty_g": r["qty_g"], "source_year": 2025}])])
    t = t.sort_values(["item", "farm_households", "year"]).reset_index(drop=True)
    t.to_csv(BASE / "data" / "national.csv", index=False)
    chk = pd.DataFrame([{"year": ty, "farm": f, "item": i, "src": s, "amount": a} for (ty, f, i, s), (a, q) in nat.items()])
    c = chk.pivot_table(index=["year", "farm", "item"], columns="src", values="amount")
    c["n_sources"] = c.notna().sum(axis=1)
    c["max_minus_min"] = c.drop(columns="n_sources").max(axis=1) - c.drop(columns="n_sources").min(axis=1)
    c.to_csv(BASE / "data" / "overlap_check.csv")
    print(t.groupby(["item", "farm_households"]).year.agg(["min", "max", "count"]))
    print("overlap max diff", c["max_minus_min"].max())


if __name__ == "__main__":
    main()
