"""元データを取得して data/raw に保存する（ネットが必要。同梱済みなので通常は不要）。
観光庁「宿泊旅行統計調査」年確定値の集計結果（Excel）のうち、8年分（2012・2015・2018・2019・2022〜2025年）。"""
import datetime, json, pathlib, time, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
IDS = json.loads((ROOT / "src" / "stay_file_ids.json").read_text())
def main():
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    L = ["# 元データの出典（取得日と URL）", "", "| ファイル | 中身 | URL | 取得日 |", "|---|---|---|---|"]
    for y in sorted(IDS):
        sid, kind = IDS[y]
        u = f"https://www.e-stat.go.jp/stat-search/file-download?statInfId={sid}&fileKind={kind}"
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (research script)"}), timeout=300) as r:
            b = r.read()
        ext = "xlsx" if b[:2] == b"PK" else "xls"
        (RAW / f"shukuhaku_{y}.{ext}").write_bytes(b)
        L.append(f"| shukuhaku_{y}.{ext} | 観光庁「宿泊旅行統計調査」{y}年 年確定値 集計結果 | {u} | {today} |")
        time.sleep(0.3)
    L += ["", "- 宿泊旅行統計調査（年確定値、e-Stat）：https://www.e-stat.go.jp/stat-search/files?toukei=00601020&tstat=000001079598",
          "- 同梱の上限（30MB）のため8年分に絞った。", "- 政府統計の総合窓口（e-Stat）から取得。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。", ""]
    (RAW / "SOURCES.md").write_text("\n".join(L) + "\n", encoding="utf-8")
if __name__ == "__main__":
    main()
