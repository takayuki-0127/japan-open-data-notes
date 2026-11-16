"""data/raw から分析用の表を作る（オフライン）。
- data/admission_by_field.csv：年度×課程×分野（計）×設置者の入学志願者・入学者（男女）
- data/admission_total.csv：年度×課程の合計（各表の前年度の行も使い、2009年度から）
- data/graduates.csv：各年3月の卒業者（大学・修士・博士・専門職）
- data/enrollment.csv：大学院の在籍者（1950〜）"""
import pathlib, re
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
FIELDS = ["人文科学", "社会科学", "理学", "工学", "農学", "保健", "商船", "家政", "教育", "芸術", "その他"]
COURSE = [("修士", "修士"), ("博士", "博士"), ("専門職", "専門職")]
SECT = ["計", "国立", "公立", "私立"]
VARS = ["applicants", "applicants_m", "applicants_f", "entrants", "entrants_m", "entrants_f"]


def norm(s):
    return re.sub(r"\s", "", str(s)).replace("　", "")


def num(x):
    try:
        return float(str(x).replace(",", "").strip())
    except ValueError:
        return np.nan


def nums(row):
    """行の数字だけを左から24個（4つの設置者 × 志願者・入学者 × 計・男・女）取る。区分の列（年度の数字など）は除く。"""
    vals = []
    for v in row[3:]:
        if isinstance(v, (int, float)) and not (isinstance(v, float) and np.isnan(v)):
            vals.append(float(v))
        elif str(v).strip() in ("-", "－", "…"):
            vals.append(0.0)
    return vals[:24]


def parse_file(path, year):
    x = pd.ExcelFile(path)
    out_f, out_t = [], []
    for sh in x.sheet_names:
        d = x.parse(sh, header=None)
        head = norm(" ".join(str(v) for v in d.iloc[:4, :].values.ravel() if str(v) != "nan"))
        course = next((c for k, c in COURSE if k in head), None)
        assert course is not None, (path, sh, head[:80])
        # 合計の2行（前年度・今年度）：分野の行より前で、数字が24個ある最初の2行
        first_field = None
        rows_num = []
        for i in range(4, len(d)):
            c1 = norm(d.iat[i, 1])
            if c1 in FIELDS and first_field is None:
                first_field = i
                break
            v = nums(d.iloc[i].tolist())
            if len(v) == 24:
                rows_num.append(v)
        assert len(rows_num) >= 2, (path, sh)
        for yy, v in [(year - 1, rows_num[0]), (year, rows_num[1])]:
            for k, s in enumerate(SECT):
                out_t.append(dict(year=yy, course=course, sector=s, **{VARS[j]: v[k * 6 + j] for j in range(6)}, file_year=year))
        stop = next((i for i in range(first_field, len(d)) if "再掲" in norm(d.iat[i, 1])), len(d))
        for i in range(first_field, stop):
            c1, c2 = norm(d.iat[i, 1]), norm(d.iat[i, 2])
            if c1 in FIELDS and c2 in ("計", "nan", ""):
                v = nums(d.iloc[i].tolist())
                if len(v) < 24:
                    continue
                for k, s in enumerate(SECT):
                    out_f.append(dict(year=year, course=course, field=c1, sector=s, **{VARS[j]: v[k * 6 + j] for j in range(6)}))
        # 専門職の（再掲）法科大学院・教職大学院：見出しの行から下で、数字が24個ある最初の2行（前年度・今年度）
        i = stop
        while i < len(d):
            lab = norm(d.iat[i, 1])
            if "再掲" in lab:
                kind = "法科大学院" if "法科" in lab else ("教職大学院" if "教職" in lab else lab)
                got = []
                for j in range(i, min(i + 6, len(d))):
                    v = nums(d.iloc[j].tolist())
                    if len(v) == 24:
                        got.append(v)
                    if len(got) == 2:
                        break
                for yy, v in zip([year - 1, year], got):
                    out_t.append(dict(year=yy, course=f"専門職のうち{kind}", sector="計", **{VARS[j]: v[j] for j in range(6)}, file_year=year))
            i += 1
    return out_f, out_t


def main():
    F, Tt = [], []
    for y in range(2010, 2026):
        p = RAW / (f"gakkou_kihon_{y}_grad_admission_by_field." + ("xls" if y <= 2014 else "xlsx"))
        f, t = parse_file(p, y)
        F += f; Tt += t
    af = pd.DataFrame(F)
    at = pd.DataFrame(Tt)
    # 同じ年度の合計が2つの表（今年度の表と翌年度の表の前年度の行）にあるとき、今年度の表を使い、差を記録する
    chk = at.pivot_table(index=["year", "course", "sector"], columns=at.file_year == at.year, values="entrants", aggfunc="first").dropna()
    chk.columns = ["from_next_file", "from_own_file"]
    chk["diff"] = chk.from_next_file - chk.from_own_file
    chk.reset_index().to_csv(ROOT / "data" / "admission_total_crosscheck.csv", index=False)
    at = at.sort_values(["year", "course", "sector", "file_year"]).assign(own=lambda q: q.year == q.file_year)
    at = at.sort_values("own").groupby(["year", "course", "sector"], as_index=False).last().drop(columns=["own"])
    at = at.sort_values(["course", "sector", "year"])
    af.to_csv(ROOT / "data" / "admission_by_field.csv", index=False)
    at.to_csv(ROOT / "data" / "admission_total.csv", index=False)
    # 分野の合計と合計の行が合うか
    s = af[af.sector == "計"].groupby(["year", "course"]).entrants.sum().rename("sum_fields").reset_index()
    s = s.merge(at[at.sector == "計"][["year", "course", "entrants"]], on=["year", "course"])
    s["diff"] = s.sum_fields - s.entrants
    s.to_csv(ROOT / "data" / "field_sum_check.csv", index=False)

    g = pd.read_excel(RAW / "gakkou_kihon_nenji_13_graduates_1948_2025.xlsx", header=None)
    col = {}
    for c in range(g.shape[1]):
        h = "|".join(norm(g.iat[r, c]) for r in range(2, 5))
        if h == "大学|大学|大学":
            col["univ_grad"] = c
        elif h.startswith("大学院|修士"):
            col["master_grad"] = c
        elif h.startswith("大学院|博士"):
            col["doctor_grad"] = c
        elif h.startswith("大学院|専門職"):
            col["prof_grad"] = c
    rows = []
    for i in range(5, len(g)):
        y = num(g.iat[i, 1])
        if np.isnan(y) or y < 1900:
            continue
        rows.append(dict(year=int(y), **{k: num(g.iat[i, c]) for k, c in col.items()}))
    pd.DataFrame(rows).to_csv(ROOT / "data" / "graduates.csv", index=False)

    e = pd.read_excel(RAW / "gakkou_kihon_nenji_k11_grad_enrollment_1950_2025.xlsx", header=None)
    rows = []
    for i in range(4, len(e)):
        y = num(e.iat[i, 1])
        if np.isnan(y) or y < 1900:
            continue
        rows.append(dict(year=int(y), enrolled=num(e.iat[i, 6]), enrolled_m=num(e.iat[i, 10]), enrolled_f=num(e.iat[i, 11])))
    pd.DataFrame(rows).to_csv(ROOT / "data" / "enrollment.csv", index=False)
    print(af.shape, at.shape, "field-sum max abs diff", s["diff"].abs().max(), "crosscheck max abs diff", chk["diff"].abs().max(), col)


if __name__ == "__main__":
    main()
