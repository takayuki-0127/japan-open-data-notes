"""元データの取得（ネットにつなぐのはこのファイルだけ。run_all.sh からは呼ばない）。
e-Stat の「特用林産物生産統計調査」各年（2005〜2025年）の一覧ページから、表題の文字で表を選んで取る。"""
import hashlib, pathlib, re, urllib.request, datetime, html

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
LIDS = {2025: "000001489412", 2024: "000001465288", 2023: "000001442522", 2022: "000001418184", 2021: "000001301056",
        2020: "000001279719", 2019: "000001252200", 2018: "000001237553", 2017: "000001230403", 2016: "000001191364",
        2015: "000001172683", 2014: "000001149816", 2013: "000001129283", 2012: "000001116813", 2011: "000001105433",
        2010: "000001085178", 2009: "000001067299", 2008: "000001059520", 2007: "000001036288", 2006: "000001036871",
        2005: "000001044766"}
LIST = "https://www.e-stat.go.jp/stat-search/files?page=1&layout=datalist&lid={}"
DL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
# key: (表題に含む文字のどれか, 含まない文字)
PATTERNS = {
    "kinoko": (["きのこ類の生産量（合計）", "1-2 きのこ類の生産量"], []),
    "shiitake": (["しいたけの生産量（合計）", "しいたけ しいたけの生産量 合計", "2-1 しいたけ しいたけの生産量 調査"], ["上半期", "下半期"]),
    "producers": (["原木栽培及び菌床栽培別"], []),
    "balance": (["主要特用林産物需給総括表"], []),
    "logs_beds": (["原木伏込量及び菌床数の推移"], []),
}
UA = {"User-Agent": "Mozilla/5.0"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA)) as r:
        return r.read(), r.headers.get("Content-Disposition", "")


rows = []
for y, lid in sorted(LIDS.items()):
    page = get(LIST.format(lid))[0].decode("utf-8", "ignore")
    page = re.sub(r"<script.*?</script>", "", page, flags=re.S)
    items = re.split(r"表番号&nbsp;", page)[1:]
    for key, (inc, exc) in PATTERNS.items():
        if key == "logs_beds" and y != 2025:
            continue
        if key == "balance" and y not in (2007, 2010, 2013, 2016, 2019, 2022, 2025):
            continue
        hit = None
        for it in items:
            txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", it)))
            ids = re.findall(r"statInfId=(\d+)&fileKind=0", it)
            if ids and any(k in txt for k in inc) and not any(k in txt for k in exc):
                hit = (ids[0], txt[:80].strip()); break
        if hit is None:
            print("not found", y, key); continue
        b, cd = get(DL.format(hit[0]))
        ext = ".xlsx" if b[:2] == b"PK" else ".xls"
        name = f"{y}_{key}{ext}"
        (RAW / name).write_bytes(b)
        rows.append(f"| {name} | {hit[1]} | {DL.format(hit[0])} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print(name, hit[1][:60])
(RAW / "SOURCES.md").write_text(
    "# SOURCES（元データの取得元）\n\n"
    f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）\n\n"
    "農林水産省（林野庁）「特用林産物生産統計調査」（特用林産基礎資料）各年の表。e-Stat の各年の一覧ページから表題の文字で選んだ。\n\n"
    "| ファイル | 表題（e-Stat の一覧の先頭） | URL | sha256 の先頭12字 |\n|---|---|---|---|\n" + "\n".join(rows) + "\n\n"
    "- 調査のページ：https://www.maff.go.jp/j/tokei/kouhyou/tokuyo_rinsan/index.html\n"
    "- 各年の一覧（例：2025年）：https://www.e-stat.go.jp/stat-search/files?page=1&layout=datalist&lid=000001489412\n\n"
    "出典：農林水産省「特用林産物生産統計調査」。\n", encoding="utf-8")
