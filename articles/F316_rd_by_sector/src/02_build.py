"""科学技術研究調査 総括 第1表・第2表（2002〜2025年調査）から、年×組織の表を作る（オフライン）。
出力：data/rd_by_sector.csv（year, sector, n_org, staff_total, researchers, expenditure_mil）
表の形は年によって違うので、組織の行を名前で探し、名前の後ろの数値を順に読む（第1表：研究実施数、研究関係従業者数の総数、研究者／第2表：研究実施数、内部使用研究費の総額）。"""
import glob, pathlib, re, warnings
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW, DATA = ROOT / "data" / "raw", ROOT / "data"
SECT = [("total", r"^総数"), ("business", r"^企業(等)?$"), ("nonprofit", r"^非営利団体$"), ("public", r"^公的機関$"), ("university", r"^大学等$"),
        ("univ_national", r"^(大学等_)?国立$"), ("univ_public", r"^(大学等_)?公立$"), ("univ_private", r"^(大学等_)?私立$")]
def norm(s): return re.sub(r"[\s　\d.()（）]", "", str(s)) if pd.notna(s) else ""
def isnum(x):
    try:
        float(str(x).replace(",", "")); return str(x).strip() not in ("", "nan")
    except ValueError:
        return False
def read(path, nvals):
    v = list(pd.read_excel(path, sheet_name=None, header=None).values())[0]
    db = any("時間軸コード" in str(x) for x in v.iloc[:16].values.ravel())
    skip = None
    if db:
        hdr_row = next(i for i in range(v.shape[0]) if "管理番号" in [str(x).strip() for x in v.iloc[i].tolist()])
        skip = [str(x).strip() for x in v.iloc[hdr_row].tolist()].index("管理番号")
    found = {}
    for i in range(v.shape[0]):
        cells = v.iloc[i].tolist()
        for j, c in enumerate(cells):
            lab = norm(c)
            if not lab: continue
            for key, pat in SECT:
                if key in found or not re.match(pat, lab): continue
                vals = [cells[k] for k in range(j + 1, len(cells)) if k != skip and isnum(cells[k])]
                if db: vals = [cells[k] for k in range(skip + 1, len(cells)) if isnum(cells[k])]
                if len(vals) >= nvals:
                    found[key] = [float(str(x).replace(",", "")) for x in vals[:nvals]]
    return found
recs = []
for y in range(2002, 2026):
    t1 = read(glob.glob(str(RAW / f"rd_{y}_t1.*"))[0], 3)
    t2 = read(glob.glob(str(RAW / f"rd_{y}_t2.*"))[0], 2)
    for key, _ in SECT:
        a, b = t1.get(key), t2.get(key)
        recs.append(dict(year=y, sector=key, n_org=a[0] if a else None, staff_total=a[1] if a else None, researchers=a[2] if a else None,
                         n_org_t2=b[0] if b else None, expenditure_mil=b[1] if b else None))
d = pd.DataFrame(recs)
d.to_csv(DATA / "rd_by_sector.csv", index=False)
p = d.pivot(index="year", columns="sector", values="researchers")
print(p[["total", "business", "nonprofit", "public", "university"]].to_string())
q = d.pivot(index="year", columns="sector", values="expenditure_mil")
print(q[["total", "business", "nonprofit", "public", "university"]].to_string())
chk = (p.business + p.nonprofit + p.public + p.university - p.total)
print("sum check researchers", chk.abs().max())
print("org check", (d.n_org - d.n_org_t2).abs().max())
