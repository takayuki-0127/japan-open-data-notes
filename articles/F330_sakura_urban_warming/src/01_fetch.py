"""01 取得（run_all.sh からは呼ばない）
- 気象庁 生物季節観測累年値「さくらの開花」004.csv
- 気象庁 日本の月平均気温偏差 mon_jpn.csv（都市化の影響が少ない15地点の平均）
- 気象庁 過去の気象データ検索：さくらの観測地点の「月平均気温（年ごと）」の表（monthly_s3.php）
  地点の府県番号（prec_no）は、府県ごとの地点選択ページから block_no=47xxx を探して決める。
"""
import pathlib, re, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "Mozilla/5.0"}
SAKURA = "https://www.data.jma.go.jp/sakura/data/ruinenchi/004.csv"
JPN = "https://www.data.jma.go.jp/cpdinfo/temp/list/csv/mon_jpn.csv"
PREF = "https://www.data.jma.go.jp/stats/etrn/select/prefecture.php?prec_no={p}&block_no=&year=&month=&day=&view="
MON = "https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no={p}&block_no={b}&year=&month=&day=&view=p1"
PRECS = list(range(11, 24)) + list(range(31, 37)) + list(range(40, 47)) + list(range(48, 58)) + \
    list(range(60, 70)) + list(range(71, 75)) + list(range(81, 89)) + [91]


def get(url):
    time.sleep(1.0)
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


def main():
    (RAW / "temp").mkdir(parents=True, exist_ok=True)
    (RAW / "004.csv").write_bytes(get(SAKURA))
    (RAW / "mon_jpn.csv").write_bytes(get(JPN))
    codes = [l.split(",")[0] for l in (RAW / "004.csv").read_bytes().decode("cp932").split("\n")[2:] if l[:1].isdigit()]
    where = {}
    for p in PRECS:
        h = get(PREF.format(p=p)).decode("utf-8", "replace")
        for b in set(re.findall(r"block_no=47(\d{3})", h)):
            where.setdefault(b, p)
    lines = ["block_no,prec_no"]
    for c in codes:
        if c not in where:
            print("no prec", c); continue
        p = where[c]
        (RAW / "temp" / f"47{c}.html").write_bytes(get(MON.format(p=p, b="47" + c)))
        lines.append(f"47{c},{p}")
    (RAW / "station_prec.csv").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
