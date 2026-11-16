"""元データを公式サイト（e-Stat）から取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。"""
import datetime, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [("lfs_detail_10-2_emptype_by_age5.xlsx", "000031575450",
          "総務省「労働力調査」詳細集計 長期時系列 表10-2 年齢階級（5歳階級）別就業者数及び年齢階級（5歳階級）、雇用形態別雇用者数 年平均（2002年〜）"),
         ("lfs_basic_3-1_population_by_age5.xlsx", "000001082682",
          "総務省「労働力調査」基本集計 長期時系列 表3-1 年齢階級（5歳階級）別15歳以上人口（1968年〜）")]

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    lines = ["# 元データの出典（取得日と URL）", "", "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|"]
    for name, sid, desc in FILES:
        url = BASE.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (research script)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            (RAW / name).write_bytes(r.read())
        lines.append(f"| {name} | {desc} | {url} | {today} |")
        print("saved", name)
    lines += ["", "- 統計表一覧（長期時系列）：https://www.stat.go.jp/data/roudou/longtime/03roudou.html",
              "- 政府統計の総合窓口（e-Stat）から取得。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
