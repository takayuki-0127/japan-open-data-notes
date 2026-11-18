"""e-Stat から林野庁「木材需給表」長期累年の3表を取得して data/raw/ に保存する。ネットが必要。run_all.sh からは呼ばない。"""
import datetime, hashlib, pathlib, urllib.request

RAW = pathlib.Path(__file__).resolve().parents[1] / "data" / "raw"
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
UA = {"User-Agent": "japan-open-data-notes research script (python-urllib)"}
FILES = [("mokuzai_jukyu_ruinen_total.xlsx", "000040370311", "木材需要（供給）量累年統計（用途別の需要・国内生産・輸入、自給率）1955〜2024年"),
         ("mokuzai_jukyu_ruinen_demand.xlsx", "000040370312", "需要量（国内消費量、輸出量）累年統計 1955〜2024年"),
         ("mokuzai_jukyu_ruinen_supply.xlsx", "000040370313", "供給量（国内生産量、輸入量）累年統計（輸入の丸太・製品の別）1955〜2024年")]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, sid, desc in FILES:
        with urllib.request.urlopen(urllib.request.Request(URL.format(sid), headers=UA), timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        rows.append((name, desc, URL.format(sid), hashlib.sha256(b).hexdigest()[:12]))
    lines = ["# 元データの出典（取得日と URL）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    lines += ["", "- 統計表一覧（木材需給表 長期累年）：https://www.e-stat.go.jp/stat-search/files?page=1&toukei=00501000&tstat=000001021364&cycle=0&tclass1=000001031549",
              "- 単位は丸太に換算した体積（千m3）。2024年は令和6年木材需給表（2025-11-21 公表）の値。",
              "- 出典：林野庁「木材需給表」（e-Stat）。政府標準利用規約（第2.0版）に従い、出典を示して加工して使う。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
