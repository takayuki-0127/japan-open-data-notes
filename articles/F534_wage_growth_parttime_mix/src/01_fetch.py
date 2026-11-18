"""元データの取得（ネットにつなぐのはこのファイルだけ。run_all.sh からは呼ばない）。
厚生労働省「毎月勤労統計調査」全国調査 実数・指数累積データ 実数（e-Stat、CSV）。
元の CSV は約21MBで1ファイル20MBの上限を超えるため、gzip（時刻を入れない -n 相当）で圧縮して保存する。"""
import datetime, gzip, hashlib, io, pathlib, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
URL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032189776&fileKind=1"


def get(url):
    for k in range(4):
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                return r.read()
        except Exception:
            time.sleep(5)
    raise RuntimeError(url)


b = get(URL)
buf = io.BytesIO()
with gzip.GzipFile(filename="", mode="wb", fileobj=buf, mtime=0, compresslevel=9) as g:
    g.write(b)
out = RAW / "maikin_jissu_cumulative.csv.gz"
out.write_bytes(buf.getvalue())
today = datetime.date.today().isoformat()
(RAW / "SOURCES.md").write_text(f"""# SOURCES（元データの取得元）

取得日：{today}（src/01_fetch.py で取得）

| ファイル | 中身 | URL | sha256 の先頭12字（圧縮前） |
|---|---|---|---|
| maikin_jissu_cumulative.csv.gz | 厚生労働省「毎月勤労統計調査」全国調査 実数・指数累積データ 実数（CSV、Shift_JIS。約{len(b)/1e6:.1f}MB を gzip で圧縮して保存） | {URL} | {hashlib.sha256(b).hexdigest()[:12]} |

- 統計表一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00450071&tstat=000001011791
- 政府統計の総合窓口（e-Stat）から取得。出典を示して加工して使う。
""", encoding="utf-8")
print(len(b), out.stat().st_size)
