"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 国土交通省「旅客地域流動調査」府県相互間旅客輸送人員表（e-Stat、2000〜2024年度、1年度1ファイル）
  e-Stat では各年度に2つのファイルが出る。機関別のシート（ＪＲ定期外・航空など）がある方の statInfId を下に固定した。
- 気象庁「地域気象観測所一覧」（ame_master.zip）：県庁所在地の観測所の緯度・経度を、県の間の距離の目安に使う"""
import pathlib, urllib.request, hashlib, datetime, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ES = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
IDS = {2000: ("000027676321", "xls"), 2001: ("000027675276", "xls"), 2002: ("000027673929", "xls"), 2003: ("000027673909", "xls"),
       2004: ("000027673664", "xls"), 2005: ("000027672945", "xls"), 2006: ("000027672940", "xls"), 2007: ("000027672556", "xls"),
       2008: ("000027672232", "xls"), 2009: ("000027671736", "xls"), 2010: ("000027669870", "xls"), 2011: ("000027669878", "xls"),
       2012: ("000027644747", "xls"), 2013: ("000031355337", "xls"), 2014: ("000031524092", "xlsx"), 2015: ("000031605975", "xls"),
       2016: ("000031682658", "xls"), 2017: ("000031817433", "xls"), 2018: ("000032021233", "xls"), 2019: ("000032088731", "xlsx"),
       2020: ("000032187226", "xlsx"), 2021: ("000040041762", "xlsx"), 2022: ("000040169489", "xlsx"), 2023: ("000040269187", "xlsx"),
       2024: ("000040442733", "xlsx")}
AME = "https://www.jma.go.jp/jma/kishou/know/amedas/ame_master.zip"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for y, (i, ext) in sorted(IDS.items()):
        b = get(ES.format(i)); time.sleep(1.0)
        name = f"ryokaku_{y}_{i}.{ext}"
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | 旅客地域流動調査 {y}年度 府県相互間旅客輸送人員表（機関別のシート） | {ES.format(i)} | {hashlib.sha256(b).hexdigest()[:12]} |")
    b = get(AME)
    (RAW / "ame_master.zip").write_bytes(b)
    lines.append(f"| ame_master.zip | 気象庁 地域気象観測所一覧（県庁所在地の観測所の緯度・経度だけを使う） | {AME} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "- 旅客地域流動調査の単位は千人。北海道は「北海道」の行と列（道北・道東・道央・道南の合計）を使う。",
              "- 2010年度から、自家用乗用車・自家用バスのシートはない（自動車輸送統計調査の見直しで、自家用の旅客の集計がなくなったため）。",
              "- e-Stat のファイルは政府標準利用規約（第2.0版）、気象庁のファイルは気象庁ホームページの利用規約に従い、出典を示して加工して使う。",
              "", "出典：国土交通省「旅客地域流動調査」、気象庁「地域気象観測所一覧」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
