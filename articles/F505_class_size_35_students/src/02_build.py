"""data/raw の Excel から、分析に使う表を作る（オフライン）。
- data/grade_panel.csv：学校種・年・区分（計・国立・公立・私立・都道府県＝公立）・学年ごとの単式学級の数と児童生徒数
- data/sizebins.csv：学校種・年・区分ごとの収容人員別学級数（人数の幅ごとの学級の数）
- data/build_checks.json：表どうしの照合の結果
"""
import json
import pandas as pd
from common import RAW, DATA, PREFS, parse_table, entity

YEARS = range(2008, 2026)
GRADES = {"es": 6, "jh": 3}


def load(kind, school, year):
    f = sorted(RAW.glob(f"{school}_{kind}_{year}.xls*"))
    assert len(f) == 1, (kind, school, year, f)
    t = parse_table(f[0])
    cur = {}
    prev = {}
    for (y, key), vals in t.items():
        e = entity(key)
        if e is None:
            raise ValueError(f"区分を読めない行：{f[0].name} {key}")
        if y == year:
            cur[e] = vals
        elif y == year - 1:
            prev[e] = vals
        else:
            raise ValueError(f"年が合わない：{f[0].name} {y}")
    missing = set(PREFS) - set(cur)
    assert not missing, (f[0].name, missing)
    return cur, prev


def main():
    rows, bins, checks = [], [], []
    for school, ng in GRADES.items():
        prev_store = {}
        for y in YEARS:
            cl, cl_prev = load("classes", school, y)
            pu, pu_prev = load("pupils", school, y)
            sb, sb_prev = load("sizebins", school, y)
            ents = ["計", "国立", "公立", "私立"] + PREFS
            for e in ents:
                for g in range(1, ng + 1):
                    c = f"単式学級|{g}学年"
                    rows.append({"school": school, "year": y, "entity": e, "grade": g,
                                 "classes": cl[e][c], "pupils": pu[e][c]})
                rows.append({"school": school, "year": y, "entity": e, "grade": 0,
                             "classes": cl[e]["単式学級|計"], "pupils": pu[e]["単式学級|計"],
                             "classes_all": cl[e]["計"], "pupils_all": pu[e]["計"]})
            for e, vals in sb.items():
                for b, n in vals.items():
                    if b.startswith("再掲"):
                        continue
                    bins.append({"school": school, "year": y, "entity": e, "bin": b, "n": n})
            # 照合1：国立＋公立＋私立＝計（単式学級の各学年・全体の学級数）
            for tab, name in [(cl, "classes"), (pu, "pupils")]:
                for c in [f"単式学級|{g}学年" for g in range(1, ng + 1)] + ["計"]:
                    s = tab["国立"][c] + tab["公立"][c] + tab["私立"][c]
                    checks.append(("setter_sum", school, y, name, c, s, tab["計"][c]))
                    # 照合2：都道府県（公立の内訳）の和＝公立
                    sp = sum(tab[p][c] for p in PREFS)
                    checks.append(("pref_sum", school, y, name, c, sp, tab["公立"][c]))
            # 照合3：収容人員別の幅の和＝計、公立の単式学級の計＝編制方式別の単式学級数
            for e in ["計", "公立", "公立|単式学級"] + PREFS:
                v = sb[e]
                s = sum(n for b, n in v.items() if b != "計" and not b.startswith("再掲"))
                checks.append(("bins_sum", school, y, "sizebins", e, s, v["計"]))
            checks.append(("bins_vs_classes", school, y, "sizebins", "公立|単式学級", sb["公立|単式学級"]["計"], cl["公立"]["単式学級|計"]))
            checks.append(("bins_vs_classes", school, y, "sizebins", "計", sb["計"]["計"], cl["計"]["計"]))
            # 照合4：次の年の表にある「前の年」の行＝その年の表の値（後から直していないか）
            if y - 1 in prev_store:
                for c in [f"単式学級|{g}学年" for g in range(1, ng + 1)]:
                    if "計" in cl_prev:
                        checks.append(("prev_year_row", school, y, "classes", c, cl_prev["計"][c], prev_store[y - 1]["cl"]["計"][c]))
                    if "計" in pu_prev:
                        checks.append(("prev_year_row", school, y, "pupils", c, pu_prev["計"][c], prev_store[y - 1]["pu"]["計"][c]))
            prev_store[y] = {"cl": cl, "pu": pu}
    gp = pd.DataFrame(rows)
    gp.to_csv(DATA / "grade_panel.csv", index=False)
    pd.DataFrame(bins).to_csv(DATA / "sizebins.csv", index=False)
    ck = pd.DataFrame(checks, columns=["check", "school", "year", "table", "item", "computed", "in_table"])
    ck["ok"] = (ck["computed"] - ck["in_table"]).abs() < 0.5
    summary = {"n_checks": int(len(ck)), "n_ok": int(ck["ok"].sum()),
               "by_check": {k: [int(v["ok"].sum()), int(len(v))] for k, v in ck.groupby("check", sort=True)},
               "failed": ck[~ck["ok"]].astype(str).values.tolist()}
    (DATA / "build_checks.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ["n_checks", "n_ok", "by_check"]}, ensure_ascii=False))
    print("failed:", summary["failed"][:10])


if __name__ == "__main__":
    main()
