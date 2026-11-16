"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
文部科学省「公立学校教員採用選考試験の実施状況」の参考資料（PDF）と、学校基本調査の年次統計。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
M = "https://www.mext.go.jp"
FILES = {
    "mext_r7_kyoin_saiyo_sankou1_tables1_23.pdf": (M + "/content/20261001-kyoikushokuin-000046447_2.pdf", "令和7年度 実施状況 参考資料1（第1〜23表。第7表 長期的推移、第5表 新卒・既卒）"),
    "mext_kyoin_saiyo_2024_tables.pdf": (M + "/content/20250124-mxt_kyoikujinzai01-000039457_2.pdf", "令和6年度 参考資料1"),
    "mext_kyoin_saiyo_2023_tables.pdf": (M + "/content/20241226-mxt_kyoikujinzai01-000033218_22.pdf", "令和5年度 参考資料1"),
    "mext_kyoin_saiyo_2022_tables.pdf": (M + "/content/20231225-mxt_kyoikujinzai02-000024926_2.pdf", "令和4年度 参考資料1"),
    "mext_kyoin_saiyo_2020_tables.pdf": (M + "/content/20220131-mxt_kyoikujinzai01-000012429-1.pdf", "令和2年度 参考資料1"),
    "mext_kyoin_saiyo_2019_tables.pdf": (M + "/content/20191223-mxt_000003296_222.pdf", "令和元年度 参考資料1"),
    "mext_kyoin_saiyo_2018_tables.pdf": (M + "/content/20191226_mxt_kyoikujinzai01_100002845_11.pdf", "平成30年度 第1〜8表"),
    "mext_kyoin_saiyo_2017_tables.pdf": (M + "/a_menu/shotou/senkou/__icsFiles/afieldfile/2018/02/07/1401021_001.pdf", "平成29年度 第1〜8表"),
    "mext_kyoin_saiyo_2016_tables.pdf": (M + "/a_menu/shotou/senkou/__icsFiles/afieldfile/2017/02/17/1381770_1.pdf", "平成28年度 第1〜8表"),
    "mext_kyoin_saiyo_2015_tables.pdf": (M + "/a_menu/shotou/senkou/__icsFiles/afieldfile/2016/02/03/1366695_01.pdf", "平成27年度 第1〜8表"),
    "mext_kyoin_saiyo_2014_tables.pdf": (M + "/a_menu/shotou/senkou/__icsFiles/afieldfile/2015/01/30/1354821_1_1.pdf", "平成26年度 第1〜8表"),
    "mext_kyoin_saiyo_2013_tables.pdf": (M + "/a_menu/shotou/senkou/__icsFiles/afieldfile/2014/01/22/1343166_01.pdf", "平成25年度 第1〜8表"),
    "gakkou_kihon_nenji_13_graduates_1948_2025.xlsx": ("https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031852313&fileKind=0", "学校基本調査 年次統計 表13 卒業者数"),
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (url, desc) in FILES.items():
        p = RAW / name
        with urllib.request.urlopen(url, timeout=60) as r:
            p.write_bytes(r.read())
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(p.read_bytes()).hexdigest()[:12]} |")
    lines += ["", "出典：文部科学省「公立学校教員採用選考試験の実施状況」（各年度）、文部科学省「学校基本調査」（e-Stat）。",
              "令和3年度の参考資料は新卒・既卒の表の字が取り出せなかったので使わず、令和3年度の値は令和4年度の表の前年度の欄から取った。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
