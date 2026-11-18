"""元データの取得（ネットにつなぐのはこのファイルだけ。run_all.sh からは呼ばない）。
総務省「国勢調査」の e-Stat のファイル（Excel）を statInfId で取る。"""
import datetime, hashlib, pathlib, time, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)
DL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = {
    "ts05_age3_pref_1920_2020.xlsx": ("000012993808", "時系列データ 第5表 年齢（3区分）別人口及び年齢別割合－全国、都道府県（1920〜2020年）。2015・2020年は不詳補完値（※）の行もある"),
    "ts04_marital_national_1920_2020.xlsx": ("000001085974", "時系列データ 第4表 配偶関係（4区分）、年齢（5歳階級）、男女別15歳以上人口－全国（1920〜2020年）。2015・2020年は不詳補完値（※）の行もある"),
    "r7_t2-3_age_pref_original.xlsx": ("000040506427", "令和7年国勢調査 人口等基本集計 第2-3表 男女、年齢（5歳階級及び3区分）別人口－全国、都道府県ほか【原数値】"),
    "r7_t2-3_age_pref_imputed.xlsx": ("000040506655", "令和7年国勢調査 人口等基本集計 第2-3表（同上）【不詳補完値】"),
    "r2retro_t2-3_age_pref_imputed.xlsx": ("000040317622", "令和7年国勢調査の公表に合わせた 令和2年国勢調査の不詳補完値（遡及集計）第2-3表"),
    "r7_t4-1_marital_pref_original.xlsx": ("000040506436", "令和7年国勢調査 人口等基本集計 第4-1表 男女、年齢（各歳）、配偶関係別人口（15歳以上）－全国、都道府県ほか【原数値】"),
}


def get(url):
    for k in range(4):
        try:
            with urllib.request.urlopen(url, timeout=300) as r:
                return r.read()
        except Exception:
            time.sleep(5)
    raise RuntimeError(url)


rows = []
for name, (sid, desc) in FILES.items():
    url = DL.format(sid)
    b = get(url)
    (RAW / name).write_bytes(b)
    rows.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    print(name, len(b))
today = datetime.date.today().isoformat()
(RAW / "SOURCES.md").write_text("\n".join([
    "# SOURCES（元データの取得元）", "", f"取得日：{today}（src/01_fetch.py で取得）", "",
    "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|", *rows, "",
    "- 統計表一覧：国勢調査 https://www.e-stat.go.jp/stat-search/files?toukei=00200521",
    "- 出典：総務省統計局「国勢調査」（e-Stat）。出典を示して加工して使う。"]) + "\n", encoding="utf-8")
