"""元データを気象庁から取る（run_all.sh からは呼ばない。一度だけ手で流した）。"""
import hashlib, os, time, urllib.request

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
ETRN = "https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no={}&block_no={}&year=&month=&day=&view=a1"
ST = [("網走", 17, 47409), ("根室", 18, 47420), ("寿都", 16, 47421), ("山形", 35, 47588), ("石巻", 34, 47592),
      ("伏木", 55, 47606), ("飯田", 48, 47637), ("銚子", 45, 47648), ("境", 69, 47742), ("浜田", 68, 47755),
      ("彦根", 60, 47761), ("宮崎", 87, 47830), ("多度津", 72, 47890), ("名瀬", 88, 47909), ("石垣島", 91, 47918)]
FILES = [
    ("nino3idx.html", "https://www.data.jma.go.jp/cpd/db/elnino/index/nino3idx.html", "エルニーニョ監視速報 監視指数 NINO.3 の基準値との差（月平均）"),
    ("elnino_table.html", "https://www.data.jma.go.jp/cpd/db/elnino/learning/faq/elnino_table.html", "過去のエルニーニョ現象・ラニーニャ現象の発生期間"),
    ("ssn_jpn.csv", "https://www.data.jma.go.jp/cpdinfo/temp/list/csv/ssn_jpn.csv", "日本の季節平均気温偏差（15地点平均）"),
] + [(f"etrn_m_{b}.html", ETRN.format(p, b), f"過去の気象データ検索 {n} 日平均気温の月平均値") for n, p, b in ST]

if __name__ == "__main__":
    os.makedirs(RAW, exist_ok=True)
    for name, url, _ in FILES:
        with urllib.request.urlopen(url, timeout=60) as r:
            b = r.read()
        open(os.path.join(RAW, name), "wb").write(b)
        print(name, len(b), hashlib.sha256(b).hexdigest()[:12])
        time.sleep(1)
