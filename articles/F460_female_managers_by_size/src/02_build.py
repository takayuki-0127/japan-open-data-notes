"""元の Excel から、規模別・役職別の女性割合を取り出して長い表にする。"""
import pathlib, re, unicodedata
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
YEARS = [2003, 2009, 2011, 2013] + list(range(2015, 2026))
SIZES = ["5,000人以上", "1,000~4,999人", "300~999人", "100~299人", "30~99人", "10~29人", "10人以上", "30人以上"]


def norm(s):
    s = unicodedata.normalize("NFKC", str(s))
    return re.sub(r"\s+", "", s).replace("〜", "~").replace("～", "~")


def role_of(h):
    h = norm(h)
    if "課長相当職以上" in h:
        return "kacho_up"
    if "係長相当職以上" in h:
        return "kakari_up"
    if h.startswith("役員"):
        return "yakuin"
    if h.startswith("部長"):
        return "bucho"
    if h.startswith("課長"):
        return "kacho"
    if h.startswith("係長"):
        return "kakari"
    return None


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("nan")


rows = []
for y in YEARS:
    f = next(RAW.glob(f"managers_{y}.xls*"))
    xl = pd.ExcelFile(f)
    sheet = next(s for s in xl.sheet_names if "役職別女性管理職" in norm(xl.parse(s, header=None).iloc[0, 0]))
    d = xl.parse(sheet, header=None)
    if y == 2003:
        cols = {3: "kakari_up", 4: "bucho", 5: "kacho", 6: "kakari"}
    else:
        hdr = next(i for i in range(8) if any(role_of(v) == "bucho" for v in d.iloc[i] if isinstance(v, str)))
        cols = {j: role_of(v) for j, v in enumerate(d.iloc[hdr]) if isinstance(v, str) and role_of(v)}
    seen = set()
    for i in range(len(d)):
        lab = None
        for j in (0, 1):
            v = d.iat[i, j]
            if isinstance(v, str) and norm(v) not in ("", "100"):
                lab = norm(v); break
        if lab is None:
            continue
        lab = lab.replace("(再掲)", "")
        if y == 2003 and lab == "産業・規模計":
            lab = "30人以上"
        if lab not in SIZES or lab in seen:
            continue
        seen.add(lab)
        for j, r in cols.items():
            rows.append({"year": y, "size": lab, "role": r, "pct": num(d.iat[i, j])})
    need = set(SIZES) - ({"10~29人", "10人以上"} if y == 2003 else set())
    assert need <= seen, (y, need - seen)

out = pd.DataFrame(rows).sort_values(["year", "role", "size"], kind="mergesort")
# 30人以上（再掲）は、上の総数行と同じ値のはず（重複行のうち先に出た方を使う）
out.to_csv(ROOT / "data" / "managers_by_size.csv", index=False, float_format="%.4f")
print(len(out), "行", out.year.nunique(), "年")
