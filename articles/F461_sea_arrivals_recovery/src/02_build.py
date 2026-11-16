"""出入国管理統計の港別の表から、港ごとの入国外国人と特例上陸許可、船舶観光上陸の国籍、海港の入国外国人の国籍を取り出す。"""
import gzip, io, pathlib, re, unicodedata
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"; OUT = ROOT / "data"
YEARS = list(range(2013, 2026))


def norm(s):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s)))


def read(name):
    f = next(RAW.glob(name + ".*"))
    if f.suffix == ".gz":
        return pd.read_excel(io.BytesIO(gzip.open(f).read()), header=None, engine="xlrd")
    return pd.read_excel(f, header=None)


def num(v):
    if isinstance(v, (int, float, np.integer, np.floating)) and not pd.isna(v):
        return float(v)
    s = norm(v).replace(",", "")
    return float(s) if re.fullmatch(r"-?\d+(\.\d+)?", s) else (0.0 if s in ("-", "－", "…") else np.nan)


def era_year(lab):
    m = re.fullmatch(r"(平成|令和)(元|\d+)年", lab)
    if not m:
        return None
    n = 1 if m.group(2) == "元" else int(m.group(2))
    return (1988 if m.group(1) == "平成" else 2018) + n


def is_air(p):
    return "(空港)" in p


# 2023年から「大阪」「神戸」は「大阪(阪神)」「神戸(阪神)」の名前になった。同じ港としてそろえる
NAME_FIX = {"大阪(阪神)": "大阪", "神戸(阪神)": "神戸", "尼崎西宮芦屋(阪神)": "尼崎西宮芦屋"}


def fix(p):
    return NAME_FIX.get(p, p)


# 1. 港別 出入国者（入国外国人）
rows = []
for y in YEARS:
    d = read(f"ports_{y}")
    pc = next(j for i in range(6) for j in range(3) if norm(d.iat[i, j]) == "港")
    fc = next(j for i in range(6) for j in range(d.shape[1]) if norm(d.iat[i, j]) == "外国人")
    total = None
    for i in range(len(d)):
        lab = norm(d.iat[i, pc]) if isinstance(d.iat[i, pc], str) else ""
        if not lab or lab in ("港", "nan"):
            continue
        ey = era_year(lab)
        if ey is not None:
            if ey == y:
                total = num(d.iat[i, fc])
            continue
        if lab.startswith(("1港別", "１港別")) or "出入国者" in lab:
            continue
        v = num(d.iat[i, fc])
        if np.isnan(v):
            continue
        rows.append({"year": y, "port": fix(lab), "air": int(is_air(lab)), "foreign_entries": v, "pref": norm(d.iat[i, 0]) if pc == 1 and isinstance(d.iat[i, 0], str) else ""})
    s = sum(r["foreign_entries"] for r in rows if r["year"] == y)
    assert total is not None and abs(s - total) < 1, (y, s, total)
ports = pd.DataFrame(rows)
PREF_ROWS = ports[["year", "port", "pref"]].copy()
ports = ports.drop(columns="pref")
ports.to_csv(OUT / "ports_foreign_entries.csv", index=False, float_format="%.0f")

# 2. 港別 特例上陸許可（寄港地上陸・通過上陸・船舶観光上陸・乗員上陸）
rows = []
for y in YEARS:
    d = read(f"tokurei_{y}")
    pr, pc = next((i, j) for i in range(8) for j in range(3) if norm(d.iat[i, j]) == "港")
    ds = next(i for i in range(pr + 1, len(d)) if norm(d.iat[i, pc]) == "総数")
    hdr = {j: "".join(norm(d.iat[i, j]) for i in range(pr, ds) if isinstance(d.iat[i, j], str)) for j in range(d.shape[1])}
    tot = next(j for j, h in hdr.items() if "総数" in h)
    kiko = next(j for j, h in hdr.items() if "寄港地" in h)
    tsu = next(j for j, h in hdr.items() if "通過" in h)
    fun = [j for j, h in hdr.items() if "船舶観光" in h]
    crew0 = next(j for j, h in hdr.items() if "乗員上陸" in h)
    emer = next(j for j, h in hdr.items() if "緊急上陸" in h)
    cols = {"total": [tot], "kikochi": [kiko], "tsuka": [tsu, tsu + 1], "funa": [fun[0], fun[0] + 1] if fun else [],
            "crew": list(range(crew0, emer))}
    nat_total = None
    for i in range(ds, len(d)):
        lab = norm(d.iat[i, pc]) if isinstance(d.iat[i, pc], str) else ""
        if not lab:
            continue
        vals = {k: sum(num(d.iat[i, j]) for j in js) if js else 0.0 for k, js in cols.items()}
        if np.isnan(vals["total"]):
            continue
        if lab == "総数":
            nat_total = vals; continue
        rows.append({"year": y, "port": fix(lab), "air": int(is_air(lab)), **vals, "pref": norm(d.iat[i, 0]) if pc == 1 and isinstance(d.iat[i, 0], str) else ""})
    sub = pd.DataFrame([r for r in rows if r["year"] == y])
    for k in cols:
        assert abs(sub[k].sum() - nat_total[k]) < 1, (y, k, sub[k].sum(), nat_total[k])
tok = pd.DataFrame(rows)
PREF_ROWS = pd.concat([PREF_ROWS, tok[["year", "port", "pref"]]])
tok = tok.drop(columns="pref")
tok.to_csv(OUT / "ports_special_landing.csv", index=False, float_format="%.0f")

# 港 → 都道府県（2022年以降の表は都道府県の列がある。上の行と同じ県は空欄なので下へ埋める）
pf = []
for y in range(2022, 2026):
    for name in (f"ports_{y}", f"tokurei_{y}"):
        d = read(name)
        pr, pc = next((i, j) for i in range(8) for j in range(3) if norm(d.iat[i, j]) == "港")
        cur = ""
        for i in range(pr + 1, len(d)):
            if isinstance(d.iat[i, 0], str) and norm(d.iat[i, 0]) not in ("全国",):
                cur = norm(d.iat[i, 0])
            lab = norm(d.iat[i, pc]) if isinstance(d.iat[i, pc], str) else ""
            if lab and cur and not era_year(lab) and lab != "総数":
                pf.append({"port": fix(lab), "pref": cur})
pf = pd.DataFrame(pf).drop_duplicates()
# 同じ名前の港が2つの県にあるもの（勝浦・由良・松島・伊万里）は、先に出た県にする（どれも人数はごく少ない）
pf = pf.drop_duplicates("port", keep="first")
pf.sort_values("port").to_csv(OUT / "port_prefecture.csv", index=False)

# 3. 船舶観光上陸の国籍（総数の列）
rows = []
for y in range(2016, 2026):
    d = read(f"funa_{y}")
    hi, tc = next((i, j) for i in range(6) for j in range(d.shape[1]) if norm(d.iat[i, j]) in ("総数", "総計"))
    for i in range(hi + 1, len(d)):
        labs = [norm(d.iat[i, j]) for j in range(tc) if isinstance(d.iat[i, j], str) and norm(d.iat[i, j])]
        if not labs:
            continue
        v = num(d.iat[i, tc])
        if not np.isnan(v):
            rows.append({"year": y, "nationality": labs[0], "funa": v})
fn = pd.DataFrame(rows).drop_duplicates(["year", "nationality"])
for y in range(2016, 2026):
    assert abs(fn[(fn.year == y) & (fn.nationality == "総数")].funa.sum() - tok[(tok.year == y)].funa.sum()) < 1, y
fn.to_csv(OUT / "funa_by_nationality.csv", index=False, float_format="%.0f")

# 4. 海港の入国外国人の国籍（2013・2019・2025年）
KEEP_NAT = ["総数", "韓国", "中国", "台湾", "米国", "北アメリカ", "ヨーロッパ", "オセアニア"]
rows = []; natport = []
for y in (2013, 2019, 2025):
    d = read(f"nat_{y}")
    hi, tc = next((i, j) for i in range(6) for j in range(d.shape[1]) if norm(d.iat[i, j]) == "総数")
    sea = [j for j in range(tc + 1, d.shape[1]) if isinstance(d.iat[hi, j], str) and norm(d.iat[hi, j]) and not is_air(norm(d.iat[hi, j]))]
    air = [j for j in range(tc + 1, d.shape[1]) if isinstance(d.iat[hi, j], str) and is_air(norm(d.iat[hi, j]))]
    for i in range(hi + 1, len(d)):
        labs = [norm(d.iat[i, j]) for j in range(tc) if isinstance(d.iat[i, j], str) and norm(d.iat[i, j])]
        if not labs:
            continue
        t = num(d.iat[i, tc])
        if np.isnan(t):
            continue
        s = sum(num(d.iat[i, j]) for j in sea); a = sum(num(d.iat[i, j]) for j in air)
        rows.append({"year": y, "nationality": labs[0], "total": t, "sea": s, "air": a})
        if labs[0] in KEEP_NAT:
            for j in sea:
                v = num(d.iat[i, j])
                if v > 0:
                    natport.append({"year": y, "nationality": labs[0], "port": fix(norm(d.iat[hi, j])), "sea_entries": v})
    tt = [r for r in rows if r["year"] == y and r["nationality"] == "総数"][0]
    assert abs(tt["sea"] + tt["air"] - tt["total"]) < 1, (y, tt)
    assert abs(tt["sea"] - ports[(ports.year == y) & (ports.air == 0)].foreign_entries.sum()) < 1, y
nat = pd.DataFrame(rows).drop_duplicates(["year", "nationality"])
nat.to_csv(OUT / "sea_entries_by_nationality.csv", index=False, float_format="%.0f")
pd.DataFrame(natport).drop_duplicates(["year", "nationality", "port"]).to_csv(OUT / "sea_entries_nat_port.csv", index=False, float_format="%.0f")
print("ports", len(ports), "tokurei", len(tok), "funa", len(fn), "nat", len(nat))
