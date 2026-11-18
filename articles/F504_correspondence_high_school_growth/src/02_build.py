"""学校基本調査（年次統計・通信制の表）から、分析用の表を作る。名前は行・列の見出しの文字で付ける。照合は data/build_checks.json。"""
import json, re
import pandas as pd
from common import ROOT, read_nenji, col, sheet_rows, isnum

D = ROOT / "data"
YEARS = [1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025]
AGES = ["15", "16", "17", "18", "19", "20-24", "25-29", "30-39", "40-49", "50-59", "60+"]
chk = {}


def ext(y):
    return "xlsx" if y >= 2015 else "xls"


def clean(c):
    if c is None:
        return ""
    if isnum(c):
        return str(int(c)) if float(c).is_integer() else str(c)
    return re.sub(r"\s+", "", str(c))


# ---- 年次統計 ----
en = read_nenji("nenji_02.xlsx")
sc = read_nenji("nenji_01.xlsx")
sh = read_nenji("nenji_04.xlsx")
ny = pd.DataFrame({
    "tsushin": col(en, "高等学校（通信制）"),
    "fullpart": col(en, "高等学校（全日制・定時制）"),
    "corr_only_schools": col(sc, "高等学校", "通信教育のみを行う学校数（別掲）"),
    "adv_rate": sh["高等学校等への進学率|計"],
    "adv_rate_excl_corr": sh["高等学校等への進学率|通信制課程（本科）への進学者を除く|計"],
}).loc[1948:2025]
ny["direct_to_corr_pt"] = (ny.adv_rate - ny.adv_rate_excl_corr).round(2)
ny.to_csv(D / "nenji_corr.csv")


# ---- 年齢別 ----
def age_label(cells):
    s = "".join(cells)
    if s.startswith("計") and not re.search(r"\d", s):
        return "計"
    if "以上" in s:
        return "60+" if s.startswith("60") or "計60" in s else "65+"
    n = re.findall(r"\d+", s)
    if len(n) == 1:
        return n[0]
    if len(n) == 2:
        return f"{n[0]}-{n[1]}"
    return None


age_rows = []
for y in YEARS:
    rows = sheet_rows(f"tsushin_{y}_age.{ext(y)}")
    got = {}
    for r in rows:
        cs = [clean(c) for c in r]
        # 見出しの終わり：「歳」「〃」「以上」「計」を含む最後のセル
        idx = [j for j, c in enumerate(cs) if re.search(r"歳|〃|以|上", c) or c in ("計", "計計")]
        if not idx:
            continue
        idx6 = [j for j in idx if j < 6]
        if not idx6:
            continue
        j = max(idx6)
        lab = age_label(cs[:j + 1])
        vals = [float(c) for c in r[j + 1:] if isnum(c)]
        if lab is None or len(vals) < 9 or lab in got:
            continue
        got[lab] = vals[:9]
        if lab in ("60+", "65+"):
            break
    if "60-64" in got:   # 1985年度は 60〜64歳と65歳以上に分かれているので足す
        a, b = got.pop("60-64"), got.pop("65+")
        got["60+"] = [x + z for x, z in zip(a, b)]
    assert list(got) == ["計"] + AGES, (y, list(got))
    for lab, v in got.items():
        age_rows.append({"year": y, "age": lab, "total": int(v[0]), "public": int(v[3]), "private": int(v[6])})
age = pd.DataFrame(age_rows)
age.to_csv(D / "age.csv", index=False)
a_tot = age[age.age == "計"].set_index("year")
a_sum = age[age.age != "計"].groupby("year")[["total", "public", "private"]].sum()
chk["age_sum_eq_total"] = bool((a_sum == a_tot[["total", "public", "private"]]).all().all())
chk["age_public_plus_private_eq_total"] = bool(((age.public + age.private) == age.total).all())
chk["age_total_vs_nenji"] = {int(y): [int(a_tot.loc[y, "total"]), int(ny.loc[y, "tsushin"])] for y in YEARS}

# ---- 学校数 ----
sch = []
for y in YEARS:
    rows = sheet_rows(f"tsushin_{y}_schools.{ext(y)}")
    rec = {"year": y}
    for r in rows:
        cs = [clean(c) for c in r]
        lab = "".join(c for c in cs[:6] if c and not re.fullmatch(r"[\d.]+", c))
        for k, key in [("公立", "public"), ("私立", "private")]:
            if k in lab and "内訳" not in lab and key not in rec:
                vals = [float(c) for c in r if isnum(c)]
                rec[f"{key}_independent"], rec[f"{key}_attached"] = int(vals[0]), int(vals[1])
    sch.append(rec)
sch = pd.DataFrame(sch).set_index("year")
sch["independent"] = sch.public_independent + sch.private_independent
sch["attached"] = sch.public_attached + sch.private_attached
sch["schools"] = sch.independent + sch.attached
sch.to_csv(D / "schools.csv")
chk["independent_eq_nenji_corr_only"] = {int(y): [int(sch.loc[y, "independent"]), int(ny.loc[y, "corr_only_schools"])] for y in YEARS}

# ---- 入学者（当該年度・前年度間） ----
ent = []
for y in YEARS[1:]:
    rows = sheet_rows(f"tsushin_{y}_entrants.{ext(y)}")
    jt = jp = None
    for r in rows[:10]:
        for j, c in enumerate(r):
            s = clean(c)
            if jt is None and "当該年度" in s:
                jt = j
            if jp is None and "前年度間" in s and "入学" in s:
                jp = j
    if jp is None:   # 1990年度の形：「当該年度」「前年度間」が2段目に、「入学者」が1段目にある
        for r in rows[:10]:
            for j, c in enumerate(r):
                s = clean(c)
                if s == "当該年度" and jt is None:
                    jt = j
                if s == "前年度間" and jp is None:
                    jp = j
    yr_rows = []
    for r in rows:
        cs = [clean(c) for c in r]
        lab = "".join(c for c in cs[:5] if c)
        if "公立" in lab:
            break
        if isnum(r[jt]) and isnum(r[jp]) and r[jt] > 1000:
            yr_rows.append((float(r[jt]), float(r[jp])))
    assert len(yr_rows) == 2, (y, yr_rows)
    (prev_may, _), (cur_may, cur_year) = yr_rows
    ent.append({"year": y, "may_prev_fy": int(prev_may), "may_this_fy": int(cur_may), "whole_prev_fy": int(cur_year)})
ent = pd.DataFrame(ent).set_index("year")
ent.to_csv(D / "entrants.csv")
json.dump(chk, open(D / "build_checks.json", "w"), ensure_ascii=False, indent=1)
print(age[age.age == "計"]); print(sch); print(ent); print(json.dumps(chk, ensure_ascii=False))
assert chk["age_sum_eq_total"] and chk["age_public_plus_private_eq_total"]
assert all(a == b for a, b in chk["age_total_vs_nenji"].values())
assert all(a == b for a, b in chk["independent_eq_nenji_corr_only"].values())
