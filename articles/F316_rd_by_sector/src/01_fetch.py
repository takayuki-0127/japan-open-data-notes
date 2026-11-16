"""元データを取得して data/raw に保存する（ネットが必要。同梱済みなので通常は不要）。
総務省「科学技術研究調査」各年の総括 第1表（研究関係従業者数）・第2表（研究費）、2002〜2025年調査。"""
import datetime, json, pathlib, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
UA = {"User-Agent": "Mozilla/5.0 (research script)"}
IDS = json.loads((ROOT / "src" / "rd_file_ids.json").read_text(encoding="utf-8"))
def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    L = ["# 元データの出典（取得日と URL）", "", "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|"]
    for y in sorted(IDS):
        for n, lab in (("1", "研究主体、組織別研究関係従業者数"), ("2", "研究主体、組織別内部使用研究費、受入研究費及び外部支出研究費")):
            sid, kind = IDS[y][n]
            url = f"https://www.e-stat.go.jp/stat-search/file-download?statInfId={sid}&fileKind={kind}"
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                b = r.read()
            ext = "xlsx" if b[:2] == b"PK" else "xls"
            name = f"rd_{y}_t{n}.{ext}"
            (RAW / name).write_bytes(b)
            L.append(f"| {name} | 総務省「科学技術研究調査」{y}年調査 総括 第{n}表 {lab} | {url} | {today} |")
            time.sleep(0.3)
    L += ["", "- 科学技術研究調査（e-Stat）：https://www.e-stat.go.jp/stat-search/files?toukei=00200543&tstat=000001032090",
          "- 各年の統計表の statInfId は src/rd_file_ids.json（e-Stat の一覧ページから 2026-11-16 に取得）。",
          "- 政府統計の総合窓口（e-Stat）から取得。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(L) + "\n", encoding="utf-8")
if __name__ == "__main__":
    main()
