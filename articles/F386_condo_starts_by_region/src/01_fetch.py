"""元データを公式サイト（e-Stat）から取得して data/raw/ に保存する（ネットが必要。run_all.sh からは呼ばない）。
- 国土交通省「建築着工統計調査」住宅着工統計 時系列表
  【住宅】利用関係別 構造別 建て方別 都道府県別 戸数（年計、1988〜2025年）
  利用関係別－新設住宅の戸数、床面積の合計（年計、1948〜2025年）"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
UA = {"User-Agent": "f3-research-script/1.0 (python urllib)"}
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [("starts_pref_tenure_struct_type_annual.xls", "000040405974",
          "建築着工統計調査 住宅着工統計 時系列表【住宅】利用関係別 構造別 建て方別 都道府県別 戸数・床面積（年計、1988〜2025年、シートは年ごと）"),
         ("starts_tenure_national_annual.xls", "000040405973",
          "建築着工統計調査 住宅着工統計 時系列表 利用関係別－新設住宅の戸数、床面積の合計（年計、1948〜2025年、分譲住宅のうちマンション・一戸建の再掲つき）")]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, sid, lab in FILES:
        url = EST.format(sid)
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        rows.append((name, lab, url, hashlib.sha256(b).hexdigest()[:12]))
        print("saved", name, len(b))
    L = ["# 元データの出典（取得日と URL）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
         "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"] + [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    L += ["", "- 建築着工統計調査 住宅着工統計 ファイル一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00600120&tstat=000001016966",
          "- e-Stat のファイルは政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
