"""data/cache/ の品別国別表（輸出、16部 84-85類）から、産業用ロボットの行だけを抜き出す。
HS 8479.50（産業用ロボット（他の項に属しないもの））と HS 8428.70（産業用ロボット（持ち上げ・荷扱い用。2017年の HS 改正で新設））。
出力：data/raw/customs_export_robots.csv（年・HS・国コード・単位・数量・金額（千円）。年の合計と12か月）。
ネットにはつながない。ただし data/cache/ は同梱しないので、run_all.sh からは呼ばない（01_fetch.py のあとに一度だけ流す）。"""
import csv, hashlib, io, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE, RAW = ROOT / "data" / "cache", ROOT / "data" / "raw"
CODES = ("'847950", "'842870")


def main():
    meta = json.loads((CACHE / "cache_meta.json").read_text(encoding="utf-8"))
    out = []
    header = None
    for y in range(2009, 2026):
        name = f"customs_export_hs84_85_{y}.csv"
        b = (CACHE / name).read_bytes()
        assert hashlib.sha256(b).hexdigest() == meta[name]["sha256"], name
        rd = csv.reader(io.StringIO(b.decode("cp932")))
        h = [c.strip() for c in next(rd)]
        h = [c.replace("-Apl", "-Apr") for c in h if c]  # 行末の空の列を除く。2016年以前は4月が「Apl」と書かれている
        if header is None:
            header = h
        assert h == header, (name, "列の並びが違う")
        n = 0
        for r in rd:
            if r[2].startswith(CODES):
                assert int(r[1]) == y, (name, r[:3])
                out.append([c.strip() for c in r][:len(header)])
                n += 1
        print(y, n)
    out.sort(key=lambda r: (int(r[1]), r[2], int(r[3])))
    with open(RAW / "customs_export_robots.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(out)


if __name__ == "__main__":
    main()
