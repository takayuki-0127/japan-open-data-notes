"""読み取りの正確さを、正解の表とセル単位で比べる。
- ページごとに「表の数を左上から順に並べた列」を作り、正解の列と並べ合わせる（difflib の SequenceMatcher）。
  一致＝正しく読めた／置き換え＝違う値として読んだ（誤読）／正解側だけにある＝読み落とし（欠落）／読み側だけにある＝余分。
- 行の再現：正解の1行の数が、読み取った1行の中にそのままの順で続いて現れれば「行として読めた」とする。
数の取り出しは common.numbers（careful=True）。素朴なやり方（careful=False）は頑健性で比べる。"""
import difflib, sys
from common import *

GTR = pd.read_json(GT / "ground_truth_rows.json")
def tok(v):
    return "-" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{float(v):g}"

def contains(hay, needle):
    n = len(needle)
    return any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))

def evaluate(tool, careful=True, ext=None, signs=None):
    ext = ext or json.load(open(EXT / f"{tool}.json", encoding="utf-8"))
    out = []
    for tid, T in TABLES.items():
        c = dict(correct=0, misread=0, missing=0, extra=0, gt=0, rows_ok=0, rows=0)
        for p in T["pages"]:
            rows = ext[tid][str(p)]
            sg = (tid == "T4") if signs is None else signs
            ex_rows = [[tok(x) for cell in r for x in numbers(cell, careful, sg)] for r in rows]
            stream = [x for r in ex_rows for x in r]
            g = GTR[(GTR.table == tid) & (GTR.page == p)]
            gs = [tok(x) for v in g.vals for x in v]
            sm = difflib.SequenceMatcher(None, gs, stream, autojunk=False)
            for op, i1, i2, j1, j2 in sm.get_opcodes():
                a, b = i2 - i1, j2 - j1
                if op == "equal": c["correct"] += a
                elif op == "replace":
                    m = min(a, b); c["misread"] += m; c["missing"] += a - m; c["extra"] += b - m
                elif op == "delete": c["missing"] += a
                elif op == "insert": c["extra"] += b
            c["gt"] += len(gs)
            for v in g.vals:
                need = [tok(x) for x in v]; c["rows"] += 1
                c["rows_ok"] += any(contains(r, need) for r in ex_rows)
        out.append(dict(tool=tool, table=tid, **c))
    return out

if __name__ == "__main__":
    tools = [p.stem for p in sorted(EXT.glob("*.json"))]
    res = pd.DataFrame([r for t in tools for r in evaluate(t)])
    for k in ["correct", "misread", "missing"]: res[k + "_rate"] = res[k] / res["gt"]
    res["extra_per_gt"] = res.extra / res["gt"]
    res["row_rate"] = res.rows_ok / res.rows
    res.to_csv(RES / "accuracy_by_tool_table.csv", index=False)
    tot = res.groupby("tool")[["correct", "misread", "missing", "extra", "gt", "rows_ok", "rows"]].sum()
    tot["correct_rate"] = tot.correct / tot["gt"]; tot["misread_rate"] = tot.misread / tot["gt"]; tot["missing_rate"] = tot.missing / tot["gt"]
    tot["row_rate"] = tot.rows_ok / tot.rows
    tot.sort_values("correct_rate", ascending=False).to_csv(RES / "accuracy_by_tool.csv")
    pd.set_option("display.width", 200)
    print(res.pivot(index="tool", columns="table", values="correct_rate").round(3))
    print(res.pivot(index="tool", columns="table", values="row_rate").round(3))
    print(tot.sort_values("correct_rate", ascending=False).round(3))
    # 頑健性：数の取り出しを素朴にした場合（全角・符号・カンマを処理しない）
    nv = pd.DataFrame([r for t in tools for r in evaluate(t, careful=False)])
    nv["correct_rate"] = nv.correct / nv["gt"]; nv["row_rate"] = nv.rows_ok / nv.rows
    nv.to_csv(RES / "accuracy_naive_parse.csv", index=False)
    # 頑健性：符号の扱いを全部の表で同じにした場合（「- 675」を -675 と読んでしまう）
    sg = pd.DataFrame([r for t in tools for r in evaluate(t, signs=True)])
    sg["correct_rate"] = sg.correct / sg["gt"]; sg.to_csv(RES / "accuracy_signs_everywhere.csv", index=False)
    print("signs everywhere\n", sg.pivot(index="tool", columns="table", values="correct_rate").round(4))
    print("naive parse\n", nv.pivot(index="tool", columns="table", values="correct_rate").round(3))
