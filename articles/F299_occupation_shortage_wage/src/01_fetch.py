"""元データを公式サイト（e-Stat）から取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。"""
import datetime, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = [
    # 厚生労働省「一般職業紹介状況」長期時系列表21 職業別労働市場関係指標（実数）（令和4年4月～）
    ("hw_t21_occupation_2022apr_.xlsx", "000040519001", 0,
     "一般職業紹介状況 長期時系列表21 職業別労働市場関係指標（実数）（令和4年4月～、2026年9月分まで）"),
    # 厚生労働省「賃金構造基本統計調査」一般労働者 職種 第1表（職種（小分類）、性別、産業計）
    ("wage_occ_t1_2022.xlsx", "000040029181", 4, "令和4年賃金構造基本統計調査 一般労働者 職種 第1表"),
    ("wage_occ_t1_2023.xlsx", "000040163741", 4, "令和5年賃金構造基本統計調査 一般労働者 職種 第1表"),
    ("wage_occ_t1_2024.xlsx", "000040247854", 4, "令和6年賃金構造基本統計調査 一般労働者 職種 第1表"),
    ("wage_occ_t1_2025.xlsx", "000040421116", 4, "令和7年賃金構造基本統計調査 一般労働者 職種 第1表"),
]

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "",
             "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|"]
    for name, sid, kind, desc in FILES:
        url = BASE.format(sid, kind)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research script)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            (RAW / name).write_bytes(r.read())
        lines.append(f"| {name} | {desc} | {url} | {today} |")
        print("saved", name)
    lines += ["", "- 統計表の一覧：一般職業紹介状況 https://www.e-stat.go.jp/stat-search/files?toukei=00450222&tstat=000001020327",
              "- 統計表の一覧：賃金構造基本統計調査 https://www.e-stat.go.jp/stat-search/files?toukei=00450091&tstat=000001011429",
              "- いずれも政府統計の総合窓口（e-Stat）から取得。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
