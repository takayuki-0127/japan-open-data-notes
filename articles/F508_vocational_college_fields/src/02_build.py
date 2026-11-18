"""学科別生徒数の表から、課程ごとに分野の計と小区分（学科）の値を抜き出す。年次統計から進学率と18歳人口の目安を抜き出す。"""
import json, re
import pandas as pd
from common import RAW, DATA, YEARS, FIELDS, sheets, label_nums, field_of, clean

checks = {"sum_check": [], "fields_found": {}}
COURSES = {"計": "all", "専門課程": "senmon"}


def course_of(rows):
    """シートの先頭5行のうち「1 計」「3 専門課程」のようなセルで課程を決める。"""
    found = set()
    for r in rows[:5]:
        for c in r:
            m = re.fullmatch(r"[0-9０-９]+[\.．]?(計|高等課程|専門課程|一般課程|専門課程（うち高度専門士）)", clean(c))
            if m:
                found.add(m.group(1))
    assert len(found) == 1, found
    return COURSES.get(found.pop())


def is_start(lab):
    """分野のかたまりの最初の行（分野の計の行）か。"""
    if lab == "計":
        return True
    f = field_of(lab)
    if f is None:
        return False
    core = re.sub(r"^.*?年度", "", lab)
    return core.endswith("計") or core.endswith("関係") or core.endswith("関係）") or re.search(r"関係（[^）]*）$", core) is not None


recs, subs = [], []
for y in YEARS:
    fname = f"senshu_{y}_gakka_seito." + ("xlsx" if y >= 2015 else "xls")
    for rows in sheets(fname):
        c = course_of(rows)
        if c is None:
            continue
        parsed = [label_nums(r) for r in rows]
        idx = [i for i, (lab, nums) in enumerate(parsed) if nums and is_start(lab)]
        # 全体の計：最初のかたまりより前で数がある最後の行。先頭の数が年度の番号（100未満）なら次の数
        pre = [parsed[i] for i in range(idx[0]) if parsed[i][1]]
        nums = pre[-1][1]
        total = nums[1] if nums[0] < 100 else nums[0]
        blocks = []
        for k, i in enumerate(idx):
            end = idx[k + 1] if k + 1 < len(idx) else len(parsed)
            labs = [parsed[j][0] for j in range(i, end)]
            fs = {field_of(l) for l in labs} - {None}
            assert len(fs) == 1, (y, c, labs[:3], fs)
            f = fs.pop()
            v = parsed[i][1][0]
            blocks.append((f, v))
            for j in range(i + 1, end):
                lab, nn = parsed[j]
                if not nn:
                    continue
                name = re.sub(r"^.*?年度", "", lab)  # 見出しから年度・分野の名前を除いて学科の名前にする
                if field_of(name):
                    p = name.index("関係")
                    key = next(k for kk, k, _, _ in FIELDS if kk == field_of(name))
                    if name[:p].endswith(key) or (key == "福祉" and "福祉" in name[:p]):
                        name = re.sub(r"^（[^）]*）", "", name[p + 2:])
                    else:
                        name = name[p + 2 + len(key):]
                subs.append({"year": y, "course": c, "field": f, "sub": name.replace("･", "・"), "students": nn[0]})
        assert len(blocks) == 8 and len({b[0] for b in blocks}) == 8, (y, c, blocks)
        for f, v in blocks:
            recs.append({"year": y, "course": c, "field": f, "students": v})
        recs.append({"year": y, "course": c, "field": "total", "students": total})
        s = sum(v for _, v in blocks)
        checks["sum_check"].append({"year": y, "course": c, "total": total, "sum_fields": s, "diff": s - total})
        checks["fields_found"][f"{y}_{c}"] = [b[0] for b in blocks]

df = pd.DataFrame(recs).sort_values(["course", "year", "field"]).reset_index(drop=True)
df.to_csv(DATA / "fields_by_year.csv", index=False)
sd = pd.DataFrame(subs).sort_values(["course", "year", "field", "sub"]).reset_index(drop=True)
sd.to_csv(DATA / "subfields_by_year.csv", index=False)
# 小区分の和＝分野の計
g = sd.groupby(["year", "course", "field"], sort=True).students.sum().reset_index()
mg = g.merge(df, on=["year", "course", "field"], suffixes=("_sub", "_field"))
checks["sub_sum_max_abs_diff"] = float((mg.students_sub - mg.students_field).abs().max())

# ---- 年次統計 ----
def nenji(fname):
    rows = sheets(fname)[0]
    head = [r for r in rows if r and clean(r[0]) == "区分"]
    names = []
    for j in range(max(len(r) for r in rows)):
        parts = []
        for h in head:
            v = clean(h[j]) if j < len(h) else ""
            if v and (not parts or parts[-1] != v):
                parts.append(v)
        names.append("|".join(parts))
    out = {}
    for r in rows:
        if len(r) > 1 and re.fullmatch(r"(19|20)\d\d", clean(r[1])):
            out[int(clean(r[1]))] = {names[j]: r[j] for j in range(2, len(r)) if j < len(names)}
    return out

ny = nenji("nenji_koto_nyugaku.xlsx")
def pick(d, *keys):
    c = [k for k in d if all(x in k.split("|") for x in keys)]
    assert len(c) == 1, (keys, c)
    return c[0]
k_rate = pick(ny[2025], "進学率", "専修学校(専門課程)")
k_ent = pick(ny[2025], "専修学校(専門課程)入学者")
k_coh = pick(ny[2025], "3年前の中学校等卒業者")
k_univ = pick(ny[2025], "進学率", "大学")
en = pd.DataFrame([{"year": y, "cohort18": float(v[k_coh]), "senmon_entrants": float(v[k_ent]), "senmon_rate": float(v[k_rate]),
                    "univ_rate": float(v[k_univ])} for y, v in sorted(ny.items()) if isinstance(v[k_rate], (int, float))])
en.to_csv(DATA / "entry_rate.csv", index=False)
checks["entry_rate_keys"] = [k_rate, k_ent, k_coh, k_univ]
checks["entry_rate_recalc_max_abs_diff"] = round(float((en.senmon_entrants / en.cohort18 * 100 - en.senmon_rate).abs().max()), 3)

zs = nenji("nenji_senshu_zaiseki.xlsx")
k_z = pick(zs[2025], "在籍者数", "計")
z = {y: float(zs[y][k_z]) for y in YEARS}
a = df[(df.course == "all") & (df.field == "total")].set_index("year").students
checks["all_total_vs_nenji_zaiseki"] = {y: {"table": a[y], "nenji": z[y], "diff": a[y] - z[y]} for y in YEARS}
json.dump(checks, open(DATA / "build_checks.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(checks, ensure_ascii=False, indent=0)[:3000])
