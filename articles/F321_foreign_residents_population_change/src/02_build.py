"""02 整形：人口推計の表（data/raw）を縦長の CSV にする（オフライン）。
- data/stock.csv ：年×都道府県の総人口・日本人人口（千人、10月1日）
- data/flows.csv ：期間（前年10月〜当年9月）×都道府県×国籍×要素（出生・死亡・県間転入・県間転出・入国・出国、人）"""
import pathlib, re
import pandas as pd, xlrd, openpyxl

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"

def sheet_rows(p):
    if p.suffix == ".xls":
        s = xlrd.open_workbook(str(p)).sheet_by_index(0)
        return [s.row_values(i) for i in range(s.nrows)]
    ws = openpyxl.load_workbook(str(p), read_only=True).worksheets[0]
    return [list(r) for r in ws.iter_rows(values_only=True)]

def clean(x):
    return re.sub(r"\s", "", str(x)) if x is not None else ""

def num(x):
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).strip().replace(",", ""))
    except ValueError:
        return None

def pref_and_nums(r):
    """データ行なら (都道府県コード, 数値の並び) を返す。全国は0。"""
    if not re.fullmatch(r"\d{5}", clean(r[0])):
        return None
    for j in range(3, min(len(r), 11)):
        c = clean(r[j])
        if j >= 4 and re.fullmatch(r"\d{2}", c) and 1 <= int(c) <= 47:
            code, start = int(c), j + 1
            break
        if c.startswith("全") and c.endswith("国") or c == "全国":
            code, start = 0, j + 1
            break
    else:
        return None
    nums = [num(x) for x in r[start:] if num(x) is not None]
    return code, nums

def parse_ref(p, kind, year):
    names = {"ref6": ("出生", "死亡"), "ref7": ("県間転入", "県間転出"), "ref8": ("入国", "出国")}[kind]
    nat, out = None, []
    for r in sheet_rows(p):
        t = "".join(clean(x) for x in r)
        if pr := pref_and_nums(r):
            if nat is None:
                raise ValueError(p)
            code, nums = pr
            out.append((year, code, nat, names[0], nums[0]))
            out.append((year, code, nat, names[1], nums[1]))
        elif "Foreigners" in t or "外国人" in t[:12]:
            nat = "外国人" if not t.startswith(("ただし", "注", "＊", "*")) else nat
        elif "Japanese" in t or t.startswith("日本人"):
            nat = "日本人" if not t.startswith(("ただし", "注", "＊", "*")) else nat
    return out

def parse_t5_xls(p):
    block, out, years = None, [], None
    for r in sheet_rows(p):
        t = "".join(clean(x) for x in r)
        if pr := pref_and_nums(r):
            if block in ("総人口", "日本人人口"):
                code, nums = pr
                for y, v in zip(years, nums[:5]):
                    out.append((y, code, block, v))
        elif "男女計" in t and ("総人口" in t or "日本人人口" in t):
            block = "総人口" if "総人口" in t else "日本人人口"
        elif ("男" in t or "女" in t) and ("総人口" in t or "日本人人口" in t):
            block = None
        elif re.fullmatch(r"(Prefectures)?(\d{4}(\.0)?年?){5}.*", t) and years is None:
            years = [int(x) for x in re.findall(r"(\d{4})(?:\.0)?年?", t)[:5]]
    return out

def parse_t5_xlsx(p):
    rows = sheet_rows(p)
    hdr = next(r for r in rows if "人口区分" in [clean(x) for x in r])
    yc = [(j, int(clean(x)[:4])) for j, x in enumerate(hdr) if re.fullmatch(r"\d{4}年", clean(x))]
    out = []
    for r in rows:
        if clean(r[0]) and clean(r[8]) == "男女計" and clean(r[7]) in ("総人口", "日本人人口"):
            code = int(clean(r[9])[:2])
            for j, y in yc:
                out.append((y, code, clean(r[7]), float(r[j])))
    return out

def main():
    flows, stock = [], []
    for p in sorted(RAW.glob("suikei_*")):
        _, kind, y, _ = p.stem.split("_")
        y = int(y)
        if kind == "t5":
            stock += parse_t5_xls(p) if p.suffix == ".xls" else parse_t5_xlsx(p)
        else:
            flows += parse_ref(p, kind, y)
    S = pd.DataFrame(stock, columns=["year", "pref", "kind", "pop_thousand"]).drop_duplicates()
    S = S.pivot_table(index=["year", "pref"], columns="kind", values="pop_thousand", aggfunc="first").reset_index()
    S.columns.name = None
    S = S.rename(columns={"総人口": "total_k", "日本人人口": "japanese_k"})
    S["foreign_k"] = S["total_k"] - S["japanese_k"]
    S = S.sort_values(["year", "pref"]).reset_index(drop=True)
    S.to_csv(ROOT / "data" / "stock.csv", index=False)
    Fl = pd.DataFrame(flows, columns=["year", "pref", "nat", "item", "persons"])
    assert not Fl.duplicated(["year", "pref", "nat", "item"]).any()
    Fl["persons"] = Fl.persons.astype(int)
    Fl = Fl.sort_values(["year", "pref", "nat", "item"]).reset_index(drop=True)
    Fl.to_csv(ROOT / "data" / "flows.csv", index=False)
    # 確かめ：全国＝47都道府県の合計、県間転入と転出の全国の合計は等しい
    w = Fl.pivot_table(index=["year", "nat", "item"], columns=Fl.pref.eq(0), values="persons", aggfunc="sum")
    print("全国と県の合計の差の最大", (w[True] - w[False]).abs().max())
    print("stock 年", sorted(S.year.unique()), "県数", S.groupby("year").pref.nunique().min())
    print("flows 年", sorted(Fl.year.unique()), Fl.groupby(["year", "nat"]).pref.nunique().min())

if __name__ == "__main__":
    main()
