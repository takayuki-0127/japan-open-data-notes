"""元データの取得（ネットが必要。run_all.sh からは呼ばない）。
国土交通省「自動車輸送統計年報」（e-Stat）の各年度の「貨物輸送量（トン数・トンキロ・能力トンキロ・実車キロ）」と
「原単位（貨物輸送）」の Excel を data/raw に保存する。"""
import hashlib, pathlib, time, urllib.request, urllib.error, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"; RAW.mkdir(parents=True, exist_ok=True)
# 年度: (貨物輸送量, 原単位)
IDS = {
    2000: ("000031848569", "000031848570"), 2001: ("000031848938", "000031848939"), 2002: ("000031848973", "000031848974"),
    2003: ("000031848904", "000031848905"), 2004: ("000031849049", "000031849050"), 2005: ("000031848750", "000031848751"),
    2006: ("000031848792", "000031848793"), 2007: ("000031848826", "000031848827"), 2008: ("000031848868", "000031848869"),
    2009: ("000031848862", "000031848863"),
    2010: ("000031355570", "000031355571"), 2011: ("000031355484", "000031355485"), 2012: ("000031355578", "000031355579"),
    2013: ("000031355147", "000031355148"), 2014: ("000031355007", "000031355176"), 2015: ("000031460316", "000031460317"),
    2016: ("000031643075", "000031643076"), 2017: ("000031752815", "000031752816"), 2018: ("000031852426", "000031852427"),
    2019: ("000031974551", "000031974552"), 2020: ("000032128419", "000032128420"), 2021: ("000032242419", "000032242420"),
    2022: ("000040108060", "000040108061"), 2023: ("000040214015", "000040214016"), 2024: ("000040328344", "000040328345"),
    2025: ("000040511073", "000040511074"),
}
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
log = []
for fy, (vol, unit) in IDS.items():
    for kind, sid in [("volume", vol), ("unit", unit)]:
        b = None
        for fk in (4, 0):           # 2009年度以前は fileKind=0（xls）、それ以降は 4（xlsx）が多い
            try:
                with urllib.request.urlopen(URL.format(sid, fk), timeout=120) as r:
                    b = r.read()
            except urllib.error.HTTPError:
                b = b""
                continue
            if b[:2] in (b"PK", b"\xd0\xcf"):
                break
        ext = "xlsx" if b[:2] == b"PK" else "xls"
        name = f"fy{fy}_{kind}.{ext}"
        (RAW / name).write_bytes(b)
        log.append((name, sid, len(b), hashlib.sha256(b).hexdigest()[:12]))
        print(datetime.date.today(), name, sid, len(b), hashlib.sha256(b).hexdigest()[:12])
        time.sleep(0.5)
