"""01 取得（run_all.sh からは呼ばない。data/raw に同梱済み）。
- 気象庁 過去の気象データ検索：気象台・測候所など（地点番号 47xxx）の「年ごとの値」（annually_s.php）を gzip で保存。
  地点と府県番号（prec_no）は、府県ごとの地点選択ページから block_no=47xxx を探して決める（F331 と同じ手順・同じ日に取得）。
- 気象庁「日本の年平均降水量偏差」（51地点平均）の一覧ページ。
"""
import gzip, pathlib, re, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "japan-open-data-notes research script (python urllib)"}
PREF = "https://www.data.jma.go.jp/stats/etrn/select/prefecture.php?prec_no={p}&block_no=&year=&month=&day=&view="
ANN = "https://www.data.jma.go.jp/stats/etrn/view/annually_s.php?prec_no={p}&block_no={b}&year=&month=&day=&view="
NATIONAL = "https://www.data.jma.go.jp/cpdinfo/temp/list/an_jpn_r.html"
PRECS = list(range(11, 24)) + list(range(31, 37)) + list(range(40, 47)) + list(range(48, 58)) + \
    list(range(60, 70)) + list(range(71, 75)) + list(range(81, 89)) + [91]


def get(url):
    time.sleep(1.0)
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


def main():
    (RAW / "annual").mkdir(parents=True, exist_ok=True)
    (RAW / "an_jpn_r_list.html").write_bytes(get(NATIONAL))
    where = {}
    for p in PRECS:
        h = get(PREF.format(p=p)).decode("utf-8", "replace")
        for b in sorted(set(re.findall(r"block_no=(47\d{3})", h))):
            where.setdefault(b, p)
    lines = ["block_no,prec_no"]
    for b, p in sorted(where.items()):
        (RAW / "annual" / f"{b}.html.gz").write_bytes(gzip.compress(get(ANN.format(p=p, b=b)), mtime=0))
        lines.append(f"{b},{p}")
    (RAW / "station_prec.csv").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
