"""02 試走（引き継ぎ前）：新しい人の役で、各回の README の「再現手順」だけを見て、きれいなフォルダで流す。

    python src/02_試走_引き継ぎ前.py <作業コピー> <python> <名前>

- 作業コピー：japan-open-data-notes を git で取ったもの（F246〜F251 を sparse checkout）
- python：使う Python。2通りで試した
    同じ版：記事を作ったときと同じライブラリ（pandas 2.3.3 ほか）
    最新版：まっさらな venv に、各回の requirements.txt のとおり `pip install`（下限だけなので、その日の最新が入る）
- やること：生成物を消す → 6回を F246→F251 の順に、README の python の行を上から流す（止まっても次の手順へ進み、
  前の回の成果物が無いことで止まるのか、その回自体で止まるのかを分けて記録する）→ git status で元のファイルと比べる
- 出力：results/B_dryrun_<名前>.json（手順ごとの成否・秒・CPU 秒・エラーの最後の行）、results/B_files_<名前>.csv
"""
import csv, json, pathlib, sys, time
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "handover"))
import dryrun_lib as L  # noqa: E402
from samplemart.verify import vs_published as _same, NUM, LOOK  # noqa: E402
import subprocess  # noqa: E402

repo, py, name = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
classify_only = len(sys.argv) > 4 and sys.argv[4] == "classify"   # 流し終わった作業コピーの比べだけをやり直す
RES = HERE.parent / "results"; RES.mkdir(exist_ok=True)
ARTS = ["F246", "F247", "F248", "F249", "F250", "F251"]
# 手で書いたファイル（生成物のフォルダに混ざっている。clean で消えるので「作られなかった」と分けて数える）
HANDWRITTEN = {"F249_powerbi_dashboard_fictional_retail/powerbi/layout_spec.md",
               "F249_powerbi_dashboard_fictional_retail/powerbi/rls.md",
               "F249_powerbi_dashboard_fictional_retail/powerbi/build_steps.md"}
arts = [a for a in sorted((repo / "articles").glob("F2[45][0-9]_*")) if a.name[:4] in ARTS]
if not classify_only:
    for a in arts:
        L.clean(a)
res = []
for a in ([] if classify_only else arts):
    t0 = time.time(); r = L.run_article(a, py, keep_going=True); r["sec"] = round(time.time() - t0, 1)
    res.append(r)
    (RES / f"B_dryrun_{name}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(a.name[:4], r["sec"], [(s["script"][4:], s["rc"]) for s in r["steps"]], flush=True)

# 元のファイルとの比べ（コミットにあるファイル全部）
rows = []
tracked = subprocess.run(["git", "ls-files", "articles"], cwd=repo, capture_output=True, text=True).stdout.split()
for rel in tracked:
    if "/src/" in rel or rel.split("/")[1][:4] not in ARTS:
        continue
    f = repo / rel
    head = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=repo, capture_output=True).stdout
    suf = f.suffix
    kind = "数字" if (suf in NUM or rel.endswith(".csv.gz")) else ("見た目" if suf in LOOK else "その他")
    if rel.endswith("README.md") or rel.endswith("requirements.txt"):
        continue  # 手順書そのもの（消していない）
    if not f.exists():
        res_ = "手書き（掃除で消えた）" if rel.split("/", 1)[1] in HANDWRITTEN else "作られなかった"
    else:
        res_ = _same(f.read_bytes(), head, f.name)
    rows.append({"回": rel.split("/")[1][:4], "ファイル": rel.split("/", 2)[2], "種類": kind, "結果": res_})
with open(RES / f"B_files_{name}.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=["回", "ファイル", "種類", "結果"]); w.writeheader(); w.writerows(rows)
print("files", len(rows))
