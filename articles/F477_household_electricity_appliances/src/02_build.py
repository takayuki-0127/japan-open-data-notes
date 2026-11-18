"""data/raw の Excel から、使う区分の行だけを長い表（CSV）にする。
列は見出しの文字（エネルギー種別・用途と「世帯数分布（抽出率調整）」「集計世帯数」「平均」）で決める。"""
import pathlib, re
import openpyxl
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
YEARS = range(2017, 2024)
WAREKI = {"平成29年度": 2017, "平成30年度": 2018, "平成31年度": 2019, "令和2年度": 2020, "令和3年度": 2021, "令和4年度": 2022, "令和5年度": 2023}
G622 = ["全国", "冷蔵庫（1台目）の製造時期別", "エアコン（1台目）の製造時期別", "テレビ（1台目）の製造時期別",
        "世帯類型別・冷蔵庫（1台目）の製造時期別", "使用している照明の種類（住宅全体）別", "冷蔵庫の使用台数別", "エアコンの使用台数別"]
G711 = ["全国", "世帯人数別（6区分）", "世帯類型別（8区分）"]


def num(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    return None if s in ("", "-", "Q", "…", "x") else float(s.replace(",", ""))


def columns(rows):
    """見出しの行（種別の行と「平均」の行）を探し、種別ごとに (分布, 集計世帯数, 平均) の列番号を返す。"""
    hi = next(i for i, r in enumerate(rows) if any(isinstance(c, str) and c.startswith("平均") for c in r))
    kinds, cur = {}, None
    for j, c in enumerate(rows[hi - 1]):
        if c is not None:
            cur = str(c).strip()
        lab = rows[hi][j]
        if cur and isinstance(lab, str):
            d = kinds.setdefault(cur, {})
            if lab.startswith("世帯数分布\n（抽出率調整）") and "w" not in d:
                d["w"] = j
            elif lab.startswith("集計世帯数") and "n" not in d:
                d["n"] = j
            elif lab.startswith("平均") and "mean" not in d:
                d["mean"] = j
    return kinds, hi


def read_table(path, groups, want_kinds, year):
    ws = openpyxl.load_workbook(path, data_only=True, read_only=True).worksheets[0]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    fy = WAREKI[str(rows[0][0]).strip()]
    assert fy == year, (path, rows[0][0])
    assert str(rows[2][0]).strip() == "全国", path
    kinds, hi = columns(rows)
    out, grp, l1 = [], None, None
    for r in rows[hi + 1:]:
        if r[1] is not None and str(r[1]).strip() not in ("属性",):
            grp, l1 = str(r[1]).strip(), None
            if grp == "全国":
                for k in want_kinds:
                    c = kinds[k]
                    out.append({"fy": fy, "group": "全国", "cat1": "", "cat2": "", "kind": k,
                                "w": num(r[c["w"]]), "n": num(r[c["n"]]), "mean": num(r[c["mean"]])})
            continue
        if grp not in groups:
            continue
        if r[2] is not None:
            l1 = str(r[2]).strip()
        l2 = str(r[3]).strip() if r[3] is not None else ""
        if l1 is None:
            continue
        for k in want_kinds:
            c = kinds[k]
            out.append({"fy": fy, "group": grp, "cat1": l1, "cat2": l2, "kind": k,
                        "w": num(r[c["w"]]), "n": num(r[c["n"]]), "mean": num(r[c["mean"]])})
    return out


def ts2():
    ws = openpyxl.load_workbook(RAW / "ts2_energy_by_attr_2017_2023.xlsx", data_only=True, read_only=True).worksheets[0]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    kinds, hi = columns(rows)
    out, grp, cat = [], None, None
    for r in rows[hi + 1:]:
        if r[1] is not None:
            grp = str(r[1]).strip(); cat = "" if grp == "全国" else None
        if r[2] is not None:
            cat = str(r[2]).strip()
        if r[4] is None or not isinstance(r[4], (int, float)):
            continue
        for k in ["電気", "エネルギー消費量合計（電気、都市ガス、LPガス、灯油）"]:
            c = kinds[k]
            out.append({"fy": int(r[4]), "group": grp, "cat": cat, "kind": "電気" if k == "電気" else "合計",
                        "w": num(r[c["w"]]), "n": num(r[c["n"]]), "mean": num(r[c["mean"]])})
    return pd.DataFrame(out)


def sokuhou():
    ws = openpyxl.load_workbook(RAW / "r7_sokuhou_fig1_3.xlsx", data_only=True, read_only=True).worksheets[0]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    hi = next(i for i, r in enumerate(rows) if r[0] is None and "電気" in [str(c) for c in r])
    head = [str(c) if c else "" for c in rows[hi]]
    je = head.index("電気")  # 最初の「電気」＝GJ/世帯・年の列
    jt = head.index("合計")
    out = []
    for r in rows[hi + 1:]:
        lab = next((str(c) for c in r if isinstance(c, str) and re.search(r"\(\d{4}\)", c)), None)
        if lab:
            jn = head.index("集計世帯数")
            out.append({"fy": int(re.search(r"\((\d{4})\)", lab).group(1)), "elec_gj": num(r[je]), "total_gj": num(r[jt]), "n": num(r[jn])})
    return pd.DataFrame(out)


def main():
    a, b = [], []
    for y in YEARS:
        a += read_table(RAW / f"t6_2_2_{y}.xlsx", G622, ["電気"], y)
        b += read_table(RAW / f"t7_1_1_{y}.xlsx", G711, ["暖房", "冷房", "給湯", "台所用コンロ", "照明・家電製品等"], y)
    a = pd.DataFrame(a).dropna(subset=["w"])
    a.to_csv(DATA / "t622_long.csv", index=False)
    pd.DataFrame(b).to_csv(DATA / "t711_long.csv", index=False)
    t = ts2(); t.to_csv(DATA / "ts2_long.csv", index=False)
    s = sokuhou(); s.to_csv(DATA / "sokuhou_trend.csv", index=False)
    print(a.groupby(["fy", "group"]).size().unstack().T)
    print(s)
    print(t[(t.group == "全国")])


if __name__ == "__main__":
    main()
