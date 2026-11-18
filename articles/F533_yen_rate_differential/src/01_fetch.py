"""元データの取得（ネットにつなぐのはこのファイルだけ。run_all.sh からは呼ばない）。
- 日本銀行 時系列統計データ検索サイト API：外国為替市況 ドル・円（月中平均・月末）
- 財務省「国債金利情報」：jgbcm_all.csv（日次、1974年〜前月末）
- 米国財務省「Daily Treasury Par Yield Curve Rates」：年ごとの CSV（1990年〜）
"""
import datetime, hashlib, pathlib, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
FILES = {
    "boj_usdjpy_monthly.json": "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=FM08&code=FXERM07,FXERM08",
    "mof_jgbcm_all.csv": "https://www.mof.go.jp/jgbs/reference/interest_rate/data/jgbcm_all.csv",
}
UST = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{y}/all"
       "?type=daily_treasury_yield_curve&field_tdr_date_value={y}&page&_format=csv")
for y in range(1990, 2027):
    FILES[f"ust_par_yield_{y}.csv"] = UST.format(y=y)


def get(url):
    for k in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
        except Exception:
            time.sleep(3)
    raise RuntimeError(url)


rows = []
for name, url in FILES.items():
    b = get(url)
    (RAW / name).write_bytes(b)
    rows.append((name, url, hashlib.sha256(b).hexdigest()[:12], len(b)))
    print(name, len(b))

today = datetime.date.today().isoformat()
lines = ["# SOURCES（元データの取得元）", "", f"取得日：{today}（src/01_fetch.py で取得）", "",
         "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
desc = {"boj_usdjpy_monthly.json": "日本銀行 外国為替市況 東京市場 ドル・円 スポット 17時時点/月中平均（FXERM07）と中心相場/月末（FXERM08）",
        "mof_jgbcm_all.csv": "財務省 国債金利情報（過去の金利情報、日次、1974年9月〜。Shift_JIS、和暦の日付）"}
for name, url, h, n in rows:
    d = desc.get(name, f"米国財務省 Daily Treasury Par Yield Curve Rates {name[14:18]}年（日次）")
    lines.append(f"| {name} | {d} | {url} | {h} |")
lines += ["", "出典：日本銀行「外国為替市況」、財務省「国債金利情報」、U.S. Department of the Treasury \"Daily Treasury Par Yield Curve Rates\"。"]
(RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
