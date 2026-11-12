"""306 Google スプレッドシートの申込集計を GAS で自動にする。
架空の申込データに、よくある入力のゆれを1種類ずつ（と全部いっしょに）入れ、
(a) COUNTIFS・SUMIFS をそのまま当てた場合を模した計算 と (b) GAS の集計関数（Node で実行） を正解と比べる。
スプレッドシート本体では動かしていない。(a) は関数の動きを Python で模したもの。
"""
import json, subprocess, unicodedata
from datetime import datetime, timedelta
import numpy as np, pandas as pd
from common import DATA, RES, ROOT

COURSES = ["Excel入門", "SQL入門", "Python入門", "統計入門", "BI入門"]
ZEN = str.maketrans("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                    "０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ")
EDGES = [("space", "コース名の前後に空白"), ("zenkaku", "コース名の全角・半角のゆれ"), ("count_text", "人数が文字（「２」「3名」）"),
         ("count_blank", "人数が空欄（1人とみなす決まり）"), ("dup", "同じメールで二重申込"), ("cancel", "取消の行（「取消」）"),
         ("cancel_word", "取消の書き方のゆれ（「キャンセル」など）"), ("reapply", "取消のあとに申込し直し"), ("blank_row", "空行"),
         ("count_unknown", "人数が「未定」"), ("other_mail", "別のメールで二重申込")]


def make(edges, seed=306):
    """正しい申込600件を作り、指定されたゆれを入れる。返すのは (シートの行, 正解の集計)"""
    rng = np.random.default_rng(seed)
    t0 = datetime(2026, 9, 1, 9, 0)
    base = []
    for i in range(600):
        base.append({"time": t0 + timedelta(minutes=int(rng.integers(0, 60 * 24 * 28))), "name": f"申込者{i+1:04d}",
                     "email": f"user{i+1:04d}@example.jp", "course": COURSES[int(rng.choice(5, p=[.28, .24, .22, .14, .12]))],
                     "count": int(rng.choice([1, 2, 3, 4], p=[.6, .25, .1, .05])), "status": ""})
    idx = rng.permutation(600)
    pick = {k: idx[i * 40:(i + 1) * 40] for i, (k, _) in enumerate(EDGES)}  # ゆれごとに重ならない40件
    rows = [dict(r, show_course=r["course"], show_count=r["count"], valid=True) for r in base]
    extra = []
    def later(r): return r["time"] + timedelta(hours=int(rng.integers(1, 72)))
    for k in edges:
        for j in pick[k]:
            r = rows[j]
            if k == "space": r["show_course"] = rng.choice([" ", "　", ""]) + r["course"] + rng.choice([" ", "　"])
            elif k == "zenkaku": r["show_course"] = r["course"].translate(ZEN)
            elif k == "count_text": r["show_count"] = rng.choice([str(r["count"]).translate(ZEN), f"{r['count']}名", f"{r['count']}人"])
            elif k == "count_blank": r["count"] = 1; r["show_count"] = ""
            elif k == "dup":  # 人数を変えて出し直し。新しいほうが正しい
                n = dict(r, time=later(r)); n["count"] = int(rng.choice([1, 2, 3])); n["show_count"] = n["count"]
                if rng.random() < .5: n["email"] = n["email"].upper()
                r["valid"] = False; extra.append(n)
            elif k == "cancel": r["status"] = "取消"; r["valid"] = False
            elif k == "cancel_word": r["status"] = rng.choice(["キャンセル", "取り消し", "キャンセル済"]); r["valid"] = False
            elif k == "reapply":
                r["status"] = "取消"; r["valid"] = False; n = dict(r, time=later(r), status="", valid=True); extra.append(n)
            elif k == "count_unknown": r["show_count"] = rng.choice(["未定", "?", "2〜3"])  # 正解は元の人数（主催者があとで確かめた、という想定）
            elif k == "other_mail":  # 同じ人が別のメールでもう一度。正しくは1件だが、メールでは見分けられない
                n = dict(r, time=later(r), email=r["email"].replace("@example.jp", "@example.com"), valid=False); extra.append(n)
    rows += extra
    rows.sort(key=lambda r: r["time"])
    sheet = [[r["time"].strftime("%Y-%m-%d %H:%M"), r["name"], r["email"], r["show_course"], r["show_count"], r["status"]] for r in rows]
    if "blank_row" in edges:
        for p in sorted(rng.choice(len(sheet), 40, replace=False), reverse=True): sheet.insert(int(p), ["", "", "", "", "", ""])
    truth = {c: {"applications": 0, "people": 0} for c in COURSES}
    for r in rows:
        if r["valid"]: truth[r["course"]]["applications"] += 1; truth[r["course"]]["people"] += r["count"]
    return sheet, truth


def formula(sheet):
    """COUNTIFS(コース, X, 状態, "<>取消")・SUMIFS(人数, コース, X, 状態, "<>取消") をそのまま当てた場合を模す。
    模した決まり：コース名は文字として一致（大文字小文字は区別しない、空白や全角は別の文字）、数でないセルは足さない。"""
    out = {}
    for c in COURSES:
        hit = [r for r in sheet if str(r[3]).lower() == c.lower() and r[5] != "取消"]
        out[c] = {"applications": len(hit), "people": int(sum(r[4] for r in hit if isinstance(r[4], (int, np.integer))))}
    return out


scen = {"clean": []}
scen.update({k: [k] for k, _ in EDGES}); scen["all"] = [k for k, _ in EDGES]
truths, forms = {}, {}
for name, edges in scen.items():
    sheet, truth = make(edges)
    pd.DataFrame(sheet, columns=["受付日時", "氏名", "メール", "コース", "人数", "状態"]).to_csv(DATA / f"applications_{name}.csv", index=False)
    truths[name], forms[name] = truth, formula(sheet)
subprocess.run(["node", str(ROOT / "test" / "run_node.js")], check=True)
node = json.load(open(RES / "node_output.json"))


def err(a, t): return {m: int(sum(abs(a[c][m] - t[c][m]) for c in COURSES)) for m in ("applications", "people")}


rec = []
for name in scen:
    ef, es = err(forms[name], truths[name]), err(node["scenarios"][name]["summary"], truths[name])
    rec.append({"scenario": name, "label": dict(EDGES).get(name, {"clean": "ゆれなし", "all": "11種類ぜんぶ"}[name] if name in ("clean", "all") else name),
                "truth_app": sum(truths[name][c]["applications"] for c in COURSES), "truth_people": sum(truths[name][c]["people"] for c in COURSES),
                "formula_app_err": ef["applications"], "formula_people_err": ef["people"],
                "script_app_err": es["applications"], "script_people_err": es["people"], "script_review_rows": node["scenarios"][name]["review"]})
df = pd.DataFrame(rec); df.to_csv(RES / "errors_by_scenario.csv", index=False)
byc = pd.DataFrame([{"course": c, "truth_app": truths["all"][c]["applications"], "formula_app": forms["all"][c]["applications"],
                     "script_app": node["scenarios"]["all"]["summary"][c]["applications"], "truth_people": truths["all"][c]["people"],
                     "formula_people": forms["all"][c]["people"], "script_people": node["scenarios"]["all"]["summary"][c]["people"]} for c in COURSES])
byc.to_csv(RES / "all_by_course.csv", index=False)
one = df[~df.scenario.isin(["clean", "all"])]
a = df.set_index("scenario").loc["all"]
summ = {"tests_passed": sum(t["ok"] for t in node["tests"]), "tests_total": len(node["tests"]), "mock": node["mock"],
        "edge_types": len(EDGES), "formula_handles": int(((one.formula_app_err == 0) & (one.formula_people_err == 0)).sum()),
        "script_handles": int(((one.script_app_err == 0) & (one.script_people_err == 0)).sum()),
        "script_not_handled": one.loc[(one.script_app_err > 0) | (one.script_people_err > 0), "label"].tolist(),
        "formula_handled": one.loc[(one.formula_app_err == 0) & (one.formula_people_err == 0), "label"].tolist(),
        "all": {k: int(a[k]) for k in ["truth_app", "truth_people", "formula_app_err", "formula_people_err", "script_app_err", "script_people_err", "script_review_rows"]},
        "all_totals": {"formula_app": int(byc.formula_app.sum()), "formula_people": int(byc.formula_people.sum()), "script_app": int(byc.script_app.sum()), "script_people": int(byc.script_people.sum())}}
json.dump(summ, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(summ, ensure_ascii=False)); print(df.drop(columns=["scenario"]).to_string(index=False))
