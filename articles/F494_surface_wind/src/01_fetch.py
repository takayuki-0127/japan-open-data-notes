"""元データを気象庁から取る（run_all.sh からは呼ばない。一度だけ手で流した）。stations.csv は F490 と同じ地点の表。"""
import hashlib, os, time, urllib.request
import csv

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
URL = "https://www.data.jma.go.jp/stats/etrn/view/annually_s.php?prec_no={}&block_no={}&year=&month=&day=&view=a3"

if __name__ == "__main__":
    for r in csv.DictReader(open(os.path.join(RAW, "stations.csv"), encoding="utf-8")):
        with urllib.request.urlopen(URL.format(r["prec_no"], r["block_no"]), timeout=60) as f:
            b = f.read()
        name = f"jma_a3_{r['block_no']}.html"
        open(os.path.join(RAW, name), "wb").write(b)
        print(name, len(b), hashlib.sha256(b).hexdigest()[:12])
        time.sleep(1)
