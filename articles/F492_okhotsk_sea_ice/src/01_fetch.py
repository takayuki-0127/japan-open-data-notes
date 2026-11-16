"""元データを気象庁から取る（run_all.sh からは呼ばない。一度だけ手で流した）。"""
import hashlib, os, time, urllib.request

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
B = "https://www.data.jma.go.jp/kaiyou/data/"
FILES = [
    ("okhotsk_alldata.txt", B + "db/seaice/okhotsk/data/okhotsk_alldata.txt", "オホーツク海の半旬ごとの海氷域面積（万km²）"),
    ("longterm_okhotsk_latest.txt", B + "shindan/a_1/series_okhotsk/longterm_okhotsk_latest.txt", "オホーツク海の最大海氷域面積（万km²）"),
] + [
    (f"station_{s}.txt", B + f"db/seaice/hokkaido/data/statistical/{s}.txt", f"北海道沿岸の海氷に関する初終日（{j}）")
    for s, j in [("wakkanai", "稚内"), ("omu", "雄武"), ("monbetsu", "紋別"), ("abashiri", "網走"), ("nemuro", "根室"), ("kushiro", "釧路")]
] + [
    ("etrn_monthly_temp_47409.html",
     "https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no=17&block_no=47409&year=&month=&day=&view=a1",
     "過去の気象データ検索 網走 日平均気温の月平均値（観測開始からの毎月の値）"),
]

if __name__ == "__main__":
    os.makedirs(RAW, exist_ok=True)
    for name, url, _ in FILES:
        with urllib.request.urlopen(url, timeout=60) as r:
            b = r.read()
        open(os.path.join(RAW, name), "wb").write(b)
        print(name, len(b), hashlib.sha256(b).hexdigest()[:12])
        time.sleep(1)
