# F255 06 照合（頑健性）：写した結果ファイルが、GitHub に公開されている各回のファイル（main）と同じかを md5 で確かめる
import csv, hashlib, urllib.request, urllib.parse, json
from pathlib import Path
HERE = Path(__file__).resolve().parents[1]
RAW = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"
FOLD = {"F246": "F246_kpi_definitions_fictional_retail", "F247": "F247_data_mart_fictional_retail", "F248": "F248_monthly_report_template_fictional_retail",
        "F249": "F249_powerbi_dashboard_fictional_retail", "F250": "F250_sales_drop_explanation_fictional_retail", "F251": "F251_promo_effect_fictional_retail",
        "F252": "F252_budget_forecast_fictional_retail", "F253": "F253_monthly_data_quality_checks_fictional_retail", "F254": "F254_handover_package_fictional_retail"}
rows = list(csv.DictReader(open(HERE / "data/in/manifest.csv", encoding="utf-8")))
out = []
for r in rows:
    if not r["ファイル"].startswith("results/"):
        continue
    url = RAW + FOLD[r["回"]] + "/" + urllib.parse.quote(r["ファイル"])
    try:
        with urllib.request.urlopen(url, timeout=60) as f:
            m = hashlib.md5(f.read()).hexdigest()
        res = "一致" if m == r["md5"] else "違う"
    except Exception as e:
        res = "GitHub になし"
    out.append([r["回"], r["ファイル"], res])
with open(HERE / "results/F_github_check.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f); w.writerow(["回", "ファイル", "GitHub（main）と"]); w.writerows(out)
summ = {k: sum(1 for x in out if x[2] == k) for k in ["一致", "違う", "GitHub になし"]}
(HERE / "results/F_github_check.json").write_text(json.dumps(summ, ensure_ascii=False), encoding="utf-8")
print(summ); [print(x) for x in out if x[2] != "一致"]
