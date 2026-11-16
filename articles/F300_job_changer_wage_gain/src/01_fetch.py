"""元データを公式サイト（e-Stat）から取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。"""
import datetime, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = [
    ("koyo_hyo11_wage_change_by_age.xls", "000040490267", 4, "厚生労働省「雇用動向調査」年次別推移 第11表 転職入職者の年齢階級別賃金変動状況（1991〜2025年）"),
    ("koyo_hyo04_2_job_change_rate_by_age.xls", "000040490259", 4, "厚生労働省「雇用動向調査」年次別推移 第4-2表 性、年齢階級別転職入職率（1991〜2025年）"),
    ("lfs_t3_3_employed_by_age5.xlsx", "000001082684", 0, "総務省「労働力調査」長期時系列 基本集計 表3-3 年齢階級（5歳階級）別就業者数及び就業率（1968〜2025年）"),
    ("hw_t1_labor_market.xlsx", "000040518981", 0, "厚生労働省「一般職業紹介状況」長期時系列表1 労働市場関係指標（有効求人倍率など）"),
]

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|"]
    for name, sid, kind, desc in FILES:
        url = BASE.format(sid, kind)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research script)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            (RAW / name).write_bytes(r.read())
        lines.append(f"| {name} | {desc} | {url} | {today} |")
        print("saved", name)
    lines += ["", "- 雇用動向調査の統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00450073",
              "- 労働力調査の長期時系列：https://www.stat.go.jp/data/roudou/longtime/03roudou.html",
              "- 一般職業紹介状況の統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00450222&tstat=000001020327",
              "- いずれも政府統計の総合窓口（e-Stat）から取得。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
