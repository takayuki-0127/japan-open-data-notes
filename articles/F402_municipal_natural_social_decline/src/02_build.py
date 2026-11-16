"""data/raw の Excel から、市区町村 × 年の人口動態の CSV を作る（オフライン）。
- data/muni.csv : kind（total/japanese）、survey（調査年：1月1日人口の年）、year（人口動態の年＝survey−1）、code、pref、name、ward（政令市の行政区か）、
                  pop（1月1日人口）、in_dom, in_abr, birth, oth_in, out_dom, out_abr, death, oth_out, change, natural, social
"""
import pathlib, re
import openpyxl, xlrd
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
COLS = {"pop": 5, "in_dom": 7, "in_abr": 8, "birth": 10, "oth_in": 11, "out_dom": 13, "out_abr": 14, "death": 16, "oth_out": 17,
        "change": 19, "natural": 21, "social": 23}
WARD = re.compile(r".+市.+区$")


def rows_of(p):
    if p.suffix == ".xls":
        s = xlrd.open_workbook(p).sheet_by_index(0)
        return [s.row_values(i) for i in range(s.nrows)]
    return [list(r) for r in openpyxl.load_workbook(p, read_only=True).worksheets[0].iter_rows(values_only=True)]


LABELS = [("in_dom", "転入者数（国内）"), ("in_abr", "転入者数（国外）"), ("birth", "出生者数"), ("out_dom", "転出者数（国内）"),
          ("out_abr", "転出者数（国外）"), ("death", "死亡者数"), ("change", "増減数(Ａ)-(Ｂ)"), ("natural", "自然増減数"), ("social", "社会増減数")]


def find_cols(R):
    """見出し（上の7行）から列の位置を決める。"""
    lab = {}
    for j in range(len(R[6])):
        lab[j] = [str(R[i][j]).strip() for i in range(7) if j < len(R[i]) and R[i][j] not in (None, "")]
    cols = {}
    for k, t in LABELS:
        cols[k] = min(j for j, v in lab.items() if t in v)
    cols["pop"] = min(j for j, v in lab.items() if "計" in v and j < cols["in_dom"])
    oth = sorted(j for j, v in lab.items() if "その他（計）" in v)
    cols["oth_in"], cols["oth_out"] = oth[0], oth[1]
    return cols


def parse(p, kind, survey):
    out = []
    R = rows_of(p)
    COLS = find_cols(R)
    for r in R:
        code = str(r[0]).strip() if r[0] is not None else ""
        if not re.fullmatch(r"\d{6}", code) or code[2:5] == "000":
            continue
        name = str(r[2]).strip()
        if name.endswith("郡") or name == "島しょ":
            continue   # 郡の小計、東京都島しょ部の小計の行
        ward = bool(WARD.match(re.sub(r"（[^）]*）$", "", name)))
        if any(str(r[j]).strip() == "***" for j in COLS.values()):
            assert ward, (p.name, code)   # 浜松市の行政区の再編（2024年）で、片方の欄が空の行。行政区は主な分析では使わない
            continue
        d = dict(kind=kind, survey=survey, year=survey - 1, code=code, pref=int(code[:2]), name=name, ward=ward)
        for k, j in COLS.items():
            d[k] = int(round(float(r[j])))
        assert d["change"] == d["natural"] + d["social"], (p.name, code)
        assert d["natural"] == d["birth"] - d["death"], (p.name, code)
        assert d["social"] == d["in_dom"] + d["in_abr"] + d["oth_in"] - d["out_dom"] - d["out_abr"] - d["oth_out"], (p.name, code)
        if d["pop"] == 0 and d["in_dom"] == 0 and d["out_dom"] == 0:
            continue   # 北方領土の6村（人口0）
        out.append(d)
    return out


def main():
    rows = []
    for p in sorted(RAW.glob("jumin_*")):
        m = re.match(r"jumin_(\d{4})_(total|japanese)\.xlsx?$", p.name)
        if m:
            rows += parse(p, m.group(2), int(m.group(1)))
    df = pd.DataFrame(rows).sort_values(["kind", "survey", "code"])
    df.to_csv(ROOT / "data" / "muni.csv", index=False)
    print(df.groupby(["kind", "survey"]).agg(n=("code", "size"), wards=("ward", "sum"), change=("change", "sum")).to_string())


if __name__ == "__main__":
    main()
