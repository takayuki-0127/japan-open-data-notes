"""data/raw から整った CSV を作る（オフライン）。"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data"


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except ValueError:
        return np.nan


def sna():
    x = pd.ExcelFile(RAW / "sna_2024_household_accounts.xlsx")
    rows = []
    for sh, kind in [("暦年（４）a", "可処分所得ベース"), ("暦年（４）b", "調整可処分所得ベース")]:
        d = x.parse(sh, header=None)
        years = [int(v) for v in d.iloc[6, 1:].tolist() if str(v).replace(".0", "").isdigit()]
        lab = d[0].astype(str)
        def row(pat):
            i = int(np.where(lab.str.contains(pat, regex=True))[0][0])
            return [num(v) for v in d.iloc[i, 1:1 + len(years)].tolist()]
        rate = row("貯蓄率")
        cons = row(r"^\s*[45]\.1")
        sav = row(r"^\s*[45]\.2")
        inc = row(r"^\s*[45]\.3")
        pen = row(r"^\s*[45]\.4")
        for k, y in enumerate(years):
            rows.append(dict(kind=kind, year=y, saving_rate_pct=rate[k], consumption_bn=cons[k], saving_net_bn=sav[k], disposable_income_bn=inc[k], pension_adj_bn=pen[k]))
    pd.DataFrame(rows).to_csv(OUT / "sna_household_saving.csv", index=False)


def longterm(fname, items):
    d = pd.read_excel(RAW / fname, sheet_name="支出金額（年）", header=None)
    hdr = [str(v) for v in d.iloc[9].tolist()]
    ycols = {int(re.match(r"(\d{4})年", h).group(1)): j for j, h in enumerate(hdr) if re.match(r"^\d{4}年$", h)}
    labels = d.iloc[:, 7:12].astype(str).agg(" ".join, axis=1).str.replace("nan", "").str.replace(r"\s+", "", regex=True)
    out = []
    for key, pat in items.items():
        idx = np.where(labels.str.match(pat))[0]
        if len(idx) == 0:
            continue
        i = int(idx[0])
        for y, j in sorted(ycols.items()):
            out.append(dict(item=key, year=y, value=num(d.iat[i, j])))
    return pd.DataFrame(out)


def by_age(fname, year):
    x = pd.ExcelFile(RAW / fname)
    rows = []
    for sh in x.sheet_names:
        typ = {"二人": "二人以上", "勤労": "勤労者", "無職": "無職"}.get(sh[:2])
        if typ is None:
            continue
        d = x.parse(sh, header=None)
        hi = None
        for i in range(0, 20):
            vals = [str(v).replace("　", "").strip() for v in d.iloc[i].tolist()]
            if "平均" in vals:
                hi = i; break
        hdr = [str(v).replace("　", "").replace(" ", "").strip() for v in d.iloc[hi].tolist()]
        c0 = hdr.index("平均")
        cols = []
        for j in range(c0, len(hdr)):
            h = hdr[j]
            if h in ("nan", ""):
                continue
            if h.startswith("(再掲)") or (j > c0 and re.match(r"^\d+歳～$", h) and "85" not in h and "70" not in h and h != "60歳～"):
                pass
            cols.append((j, h))
        lab = d.astype(str).apply(lambda r: " ".join(r.values), axis=1)
        def find(pat):
            for i in range(len(d)):
                for v in d.iloc[i, :c0].tolist():
                    s = str(v).replace(" ", "").replace("　", "")
                    if re.match(pat, s):
                        return i
            return None
        for key, pat in {"世帯数分布": r"^世帯数分布", "集計世帯数": r"^集計世帯数", "可処分所得": r"^可処分所得$", "黒字": r"^黒字$", "黒字率": r"^黒字率", "消費支出": r"^消費支出$"}.items():
            i = find(pat)
            if i is None:
                continue
            for j, h in cols:
                rows.append(dict(year=year, type=typ, item=key, age=h, value=num(d.iat[i, j])))
    return pd.DataFrame(rows)


def sna_components():
    x = pd.ExcelFile(RAW / "sna_2024_household_accounts.xlsx")
    pats = {"財産所得（支払）": r"^1\.1", "営業余剰・混合所得（純）": r"^1\.3", "うち営業余剰（持ち家）": r"^\s*（１）営業余剰（持ち家）（純）",
            "うち混合所得": r"^\s*（２）混合所得（純）", "雇用者報酬": r"^1\.4", "財産所得（受取）": r"^1\.5",
            "所得・富等に課される経常税": r"^2\.1", "純社会負担": r"^2\.2", "その他の経常移転（支払）": r"^2\.3", "可処分所得（純）": r"^2\.4",
            "社会給付（現物以外）": r"^2\.6", "その他の経常移転（受取）": r"^2\.7"}
    rows = []
    for sh in ["暦年（１）", "暦年（２）"]:
        d = x.parse(sh, header=None)
        years = [int(v) for v in d.iloc[6, 1:].tolist() if str(v).replace(".0", "").isdigit()]
        lab = d[0].astype(str).str.replace("\u3000", " ")
        for key, pat in pats.items():
            idx = np.where(lab.str.match(pat))[0]
            if len(idx) == 0:
                continue
            i = int(idx[0])
            for k, y in enumerate(years):
                rows.append(dict(item=key, year=y, value_bn=num(d.iat[i, 1 + k])))
    pd.DataFrame(rows).to_csv(OUT / "sna_household_income_components.csv", index=False)


def main():
    sna()
    sna_components()
    items = {"世帯数分布": r"^世帯数分布", "集計世帯数": r"^集計世帯数", "世帯人員": r"^世帯人員", "世帯主の年齢": r"^世帯主の年齢", "可処分所得": r"^可処分所得$",
             "黒字率": r"^黒字率", "消費支出": r"^消費支出"}
    a = longterm("kakei_longterm_two_plus.xlsx", items); a["type"] = "二人以上"
    b = longterm("kakei_longterm_workers.xlsx", items); b["type"] = "勤労者"
    pd.concat([a, b]).to_csv(OUT / "kakei_longterm.csv", index=False)
    pd.concat([by_age("kakei_by_age_2025.xlsx", 2025), by_age("kakei_by_age_2019.xls", 2019)]).to_csv(OUT / "kakei_by_age.csv", index=False)
    print(pd.read_csv(OUT / "kakei_longterm.csv").pivot_table(index="year", columns=["type", "item"], values="value").loc[[2000, 2010, 2025]].T)
    ba = pd.read_csv(OUT / "kakei_by_age.csv")
    print(ba[(ba.age == "平均")].pivot_table(index=["year", "type"], columns="item", values="value"))


if __name__ == "__main__":
    main()
