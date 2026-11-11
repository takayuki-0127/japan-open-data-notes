# F255 01 取得：F246〜F254 の結果ファイル・README・コード・requirements を data/in/ に写す
# 隣のフォルダ（articles/Fxxx_*/）があればそこから、なければ GitHub（main）から取る。
# 写したファイルの md5 を data/in/manifest.csv に残す。
import hashlib, csv, shutil, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
ARTS = HERE.parent
OUT = HERE / "data" / "in"
RAW = "https://raw.githubusercontent.com/takayuki-0127/japan-open-data-notes/main/articles/"

FOLDERS = {
    "F246": "F246_kpi_definitions_fictional_retail",
    "F247": "F247_data_mart_fictional_retail",
    "F248": "F248_monthly_report_template_fictional_retail",
    "F249": "F249_powerbi_dashboard_fictional_retail",
    "F250": "F250_sales_drop_explanation_fictional_retail",
    "F251": "F251_promo_effect_fictional_retail",
    "F252": "F252_budget_forecast_fictional_retail",
    "F253": "F253_monthly_data_quality_checks_fictional_retail",
    "F254": "F254_handover_package_fictional_retail",
}
# 数字を取る結果ファイル
RESULTS = {
    "F246": ["results/main.json", "results/C_noise_by_grain.csv"],
    "F247": ["results/main.json"],
    "F248": ["results/main.json", "results/A_noise_widths.csv"],
    "F249": ["results/main.json", "results/D_noise_flags_20seeds.csv", "results/E_bands_company_area.csv"],
    "F250": ["results/main.json"],
    "F251": ["results/main.json"],
    "F252": ["results/main.json"],
    "F253": ["results/summary.json"],
    "F254": ["results/A_audit.json", "results/A_audit_by_article.csv"],
}


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def get(art, rel, rows, required=True):
    dst = OUT / art / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    src = ARTS / FOLDERS[art] / rel
    if src.exists():
        shutil.copyfile(src, dst); how = "隣のフォルダ"
    else:
        try:
            with urllib.request.urlopen(RAW + FOLDERS[art] + "/" + urllib.request.quote(rel), timeout=60) as r:
                dst.write_bytes(r.read())
            how = "GitHub main"
        except Exception as e:
            if required:
                raise
            print("  なし:", art, rel, type(e).__name__); return
    rows.append([art, rel, how, dst.stat().st_size, md5(dst)])


def main():
    rows = []
    for art, rels in RESULTS.items():
        for rel in rels:
            get(art, rel, rows, required=(art != "F254"))  # F254 は同時に作っている回なので、なくても止めない
    # コードの点検用：README・requirements・src/*.py（F246〜F253）
    for art in [a for a in FOLDERS if a != "F254"]:
        get(art, "README.md", rows)
        get(art, "requirements.txt", rows)
        sdir = ARTS / FOLDERS[art] / "src"
        if not sdir.exists():
            sys.exit(f"{art} の src が隣のフォルダにありません。リポジトリを丸ごと clone して実行してください")
        for p in sorted(sdir.glob("*.py")):
            get(art, "src/" + p.name, rows)
    with open(OUT / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["回", "ファイル", "取得元", "バイト", "md5"]); w.writerows(rows)
    print("写したファイル", len(rows))


if __name__ == "__main__":
    main()
