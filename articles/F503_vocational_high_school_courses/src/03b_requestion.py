"""問い直し（結果を見てから足した）：工業と商業の中では、どの小学科が減ったのか（1990・2005・2025年度）。
大学科の計の行の後ろから次の大学科の計の行までを小学科として、見出しの文字で読む。小学科の和＝大学科の計を確かめる。"""
import json, re
import pandas as pd
from common import ROOT, sheet_rows, label_and_first

D, R = ROOT / "data", ROOT / "results"
YEARS = {1990: "xls", 2005: "xls", 2025: "xlsx"}
HEAD = re.compile(r"^(専門(農業|工業|商業|水産|家庭|看護|情報|福祉|その他)計|(農業|工業|商業|水産|家庭|看護|情報|福祉)に関する学科(計)?|"
                  r"普通.*|総合学科.*|その他の学科(計)?)$")


def subs(y, course):
    rows = sheet_rows(f"gakko_{y}_shogakka.{YEARS[y]}")
    out, total, inside = {}, None, False
    for r in rows:
        L, v = label_and_first(r)
        if v is None:
            continue
        is_head = L in (f"{course}に関する学科", f"{course}に関する学科計", f"専門{course}計")
        if is_head:
            inside, total = True, v
            continue
        if inside:
            if HEAD.match(L) and not L.startswith(f"専門{course}"):
                break
            name = L.replace(f"専門{course}", "").replace(f"{course}に関する学科", "")
            out[name] = out.get(name, 0) + v
    return total, out


res, tab = {}, []
for course in ["工業", "商業"]:
    res[course] = {}
    for y in YEARS:
        total, s = subs(y, course)
        res[course][y] = {"total": int(total), "sum_ok": int(sum(s.values())) == int(total),
                          "subs": {k: int(v) for k, v in s.items()}}
        for k, v in s.items():
            tab.append({"course": course, "year": y, "sub": k, "n": int(v), "share_pct": round(100 * v / total, 2)})
tab = pd.DataFrame(tab)
tab.to_csv(R / "requestion_subcourses.csv", index=False)
key = {"工業": ["機械関係", "電子機械関係", "自動車関係", "電気関係", "電子関係", "情報技術関係", "建築関係", "土木関係", "化学工業関係", "デザイン関係"],
       "商業": ["商業関係", "情報処理関係", "会計関係", "流通経済関係", "国際経済関係"]}
summ = {}
for course, ks in key.items():
    summ[course] = {}
    for k in ks:
        rec = {}
        for y in YEARS:
            v = res[course][y]["subs"].get(k)
            rec[str(y)] = None if v is None else {"n": v, "share_pct": round(100 * v / res[course][y]["total"], 1)}
        summ[course][k] = rec
out = {"sum_ok_all": all(res[c][y]["sum_ok"] for c in res for y in YEARS), "key_subcourses": summ,
       "totals": {c: {str(y): res[c][y]["total"] for y in YEARS} for c in res}}
json.dump(out, open(R / "requestion.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))
