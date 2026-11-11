"""01 監査：F246〜F251 のコードを「引き継ぐ人の目」で数える（コードは動かさない）。

入力：japan-open-data-notes を git で取った作業コピー（引数1。sparse checkout で F246〜F251 だけ）。
出力：results/A_audit_by_article.csv（回ごと）、results/A_rule_copies.csv（同じ決めごとが書かれている場所）、
      results/A_audit.json（まとめ）
数えるもの：
- 手順の数（README の「再現手順」の python の行）、スクリプトの数と行数
- 前の回への依存（コードに出てくる F2xx のフォルダ名・コミット）と、その取り方（隣のフォルダ／GitHub）
- ネットワークが要る手順（urllib）、ブラウザ（playwright）が要る手順
- 版の固定（requirements.txt の == の数）
- README に書いていない前提（コードのコメントにだけある「先に〜を流しておく」）
- 既存店の判定のように、同じ決めごとが何か所に書かれているか
"""
import json, pathlib, re, sys
import pandas as pd

REPO = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("work/audit")
ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"; RES.mkdir(exist_ok=True)
ARTS = ["F246_kpi_definitions_fictional_retail", "F247_data_mart_fictional_retail",
        "F248_monthly_report_template_fictional_retail", "F249_powerbi_dashboard_fictional_retail",
        "F250_sales_drop_explanation_fictional_retail", "F251_promo_effect_fictional_retail"]


def readme_steps(t):
    m = re.search(r"## 再現手順\s*\n```[^\n]*\n(.*?)```", t, re.S)
    return [l.split("#")[0].split()[1] for l in m.group(1).splitlines() if l.strip().startswith("python ")]


rows, copies = [], []
for a in ARTS:
    d = REPO / "articles" / a
    rd = (d / "README.md").read_text(encoding="utf-8")
    src = sorted((d / "src").glob("*.py"))
    code = {p.name: p.read_text(encoding="utf-8") for p in src}
    alltxt = "\n".join(code.values())
    deps = sorted({x for x in re.findall(r"(F2\d\d)_[a-z_]+", alltxt) if x != a[:4]})
    commits = sorted({c[:7] for c in re.findall(r"[\"'/]([0-9a-f]{7,40})[\"'/]", alltxt)
                      if re.search(r"[a-f]", c) and re.search(r"\d", c)})
    sibling = bool(re.search(r"ROOT\.parent|ART\s*/|\.\./F2", alltxt))
    req = (d / "requirements.txt").read_text(encoding="utf-8").splitlines()
    req = [r.split("#")[0].strip() for r in req if r.split("#")[0].strip()]
    steps = readme_steps(rd)
    # 隣のフォルダを読むのに、GitHub から取る逃げ道がないスクリプト（フォルダだけ渡されると止まる）
    nofb = [n for n, t in code.items() if re.search(r'ROOT\.parent\s*/\s*"F2|ROOT\.parent\s*/\s*art', t) and "urllib" not in t
            and "exists()" not in t]
    # README に書いてない前提：コードのコメントにある「先に」「流しておく」
    hidden = []
    for n, t in code.items():
        for line in t.splitlines():
            if re.search(r"先に.*(流し|作っ)|流しておく必要", line):
                hidden.append(f"{n}: {line.strip()[:80]}")
    in_readme = [h for h in hidden if h.split(": ", 1)[1][:20] in rd]
    rows.append({
        "回": a[:4], "README の手順": len(steps), "スクリプト": len(src),
        "行数": sum(t.count("\n") + 1 for t in code.values()),
        "前の回への依存": " ".join(deps), "固定したコミット": " ".join(commits),
        "隣のフォルダを読む": int(sibling), "逃げ道なしで隣を読む": " ".join(nofb),
        "ネットワーク": int("urllib" in alltxt),
        "ブラウザ（playwright）": int("playwright" in alltxt),
        "版の固定（==）": sum("==" in r for r in req), "版の下限だけ（>=）": sum(">=" in r for r in req),
        "乱数の種を回す": int(bool(re.search(r"range\(20\)|n_seed=20|SEEDS", alltxt))),
        "コードにだけある前提": len(hidden) - len(in_readme),
        "README にもある前提": len(in_readme),
    })
    # 既存店の判定（13か月）を書いている場所
    for n, t in code.items():
        for i, line in enumerate(t.splitlines(), 1):
            s = line.strip()
            if s.startswith("#") or s.startswith('"') or "set_title" in s or "ax.text" in s or "<p>" in s:
                continue
            if re.search(r"age\s*>=\s*(13|months)|DateOffset\(months=13\)", s):
                kind = "暦の月の差（開店月を1か月目と数える）" if "age" in s else "日付で13か月後（開店日から数える）"
                copies.append({"回": a[:4], "ファイル": n, "行": i, "書き方": kind, "コード": s[:110]})

A = pd.DataFrame(rows)
A.to_csv(RES / "A_audit_by_article.csv", index=False, encoding="utf-8-sig")
C = pd.DataFrame(copies)
C.to_csv(RES / "A_rule_copies.csv", index=False, encoding="utf-8-sig")
summary = {
    "articles": len(A), "steps_total": int(A["README の手順"].sum()), "scripts": int(A["スクリプト"].sum()),
    "lines": int(A["行数"].sum()), "network_articles": int(A["ネットワーク"].sum()),
    "browser_articles": int(A["ブラウザ（playwright）"].sum()),
    "pinned_requirements": int(A["版の固定（==）"].sum()), "floor_requirements": int(A["版の下限だけ（>=）"].sum()),
    "hidden_prereq_code_only": int(A["コードにだけある前提"].sum()),
    "sibling_no_fallback": {r["回"]: r["逃げ道なしで隣を読む"] for _, r in A.iterrows() if r["逃げ道なしで隣を読む"]},
    "existing_rule_copies": len(C), "existing_rule_kinds": C["書き方"].value_counts().to_dict(),
}
(RES / "A_audit.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
print(A.to_string(index=False)); print(C.to_string(index=False)); print(summary)
