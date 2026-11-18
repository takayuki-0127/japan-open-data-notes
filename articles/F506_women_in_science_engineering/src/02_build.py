"""data/raw の Excel から、分野別・男女別の入学者の表を作る（オフライン）。
- data/entrants.csv：課程（ug＝学部、master＝修士、doctor＝博士）・表（ug は 計／昼間／4年）・年度・分野・学科ごとの入学者（計・男・女）
- data/build_checks.json：表どうしの照合（分野の和＝計、学科の和＝分野、男＋女＝計）
"""
import json
import pandas as pd
from common import RAW, DATA, FIELDS, sheets, sheet_title, parse_entrants

YEARS = range(2000, 2026)


def main():
    rows, checks = [], []
    for y in YEARS:
        for kind in ("ug", "grad"):
            f = sorted(RAW.glob(f"{kind}_entrants_{y}.xls*"))
            assert len(f) == 1, f
            for k, g in enumerate(sheets(f[0])):
                t = sheet_title(g)
                if kind == "ug":
                    table = {0: "計", 1: "昼間", 2: "4年"}[k]
                    assert ("昼間" in t) == (table == "昼間") and ("4年" in t or "４年" in t) == (table == "4年"), (f[0].name, k, t)
                    level = "ug"
                else:
                    if "修士" in t:
                        level = "master"
                    elif "博士" in t:
                        level = "doctor"
                    else:
                        continue
                    table = "計"
                d, yr = parse_entrants(g)
                assert yr == y, (f[0].name, yr)
                for key, (tot, m, w) in d.items():
                    rows.append({"level": level, "table": table, "year": y, "field": key[0],
                                 "sub": key[1] if len(key) > 1 else "", "total": tot, "male": m, "female": w})
                    checks.append(("m_plus_f", level, table, y, "|".join(key), m + w, tot))
                s = sum(d[(fl,)][0] for fl in FIELDS if (fl,) in d)
                checks.append(("fields_sum", level, table, y, "計", s, d[("計",)][0]))
                for fl in FIELDS:
                    subs = [v for kk, v in d.items() if len(kk) == 2 and kk[0] == fl]
                    if subs:
                        for i, nm in enumerate(["total", "male", "female"]):
                            checks.append(("subs_sum", level, table, y, f"{fl}|{nm}", sum(v[i] for v in subs), d[(fl,)][i]))
    df = pd.DataFrame(rows)
    df.to_csv(DATA / "entrants.csv", index=False)
    ck = pd.DataFrame(checks, columns=["check", "level", "table", "year", "item", "computed", "in_table"])
    ck["ok"] = (ck["computed"] - ck["in_table"]).abs() < 0.5
    summary = {"n_checks": int(len(ck)), "n_ok": int(ck["ok"].sum()),
               "by_check": {k: [int(v["ok"].sum()), int(len(v))] for k, v in ck.groupby("check", sort=True)},
               "failed": ck[~ck["ok"]].astype(str).values.tolist()}
    (DATA / "build_checks.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ["n_checks", "n_ok", "by_check"]}, ensure_ascii=False))
    print("failed:", summary["failed"][:12])


if __name__ == "__main__":
    main()
