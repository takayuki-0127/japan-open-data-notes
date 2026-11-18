"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
気象庁の日本・世界の年平均気温偏差の CSV、季節別の CSV、全球平均の海面水温、公表の上昇率が書かれた解説ページを保存する。"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
FILES = {
    "an_jpn.csv": "https://www.data.jma.go.jp/cpdinfo/temp/list/csv/an_jpn.csv",
    "an_wld.csv": "https://www.data.jma.go.jp/cpdinfo/temp/list/csv/an_wld.csv",
    "ssn_jpn.csv": "https://www.data.jma.go.jp/cpdinfo/temp/list/csv/ssn_jpn.csv",
    "ssn_wld.csv": "https://www.data.jma.go.jp/cpdinfo/temp/list/csv/ssn_wld.csv",
    "sst_global.txt": "https://ds.data.jma.go.jp/gmd/kaiyou/data/shindan/a_1/glb_warm/global.txt",
    "page_an_jpn.html": "https://www.data.jma.go.jp/cpdinfo/temp/an_jpn.html",
    "page_an_wld.html": "https://www.data.jma.go.jp/cpdinfo/temp/an_wld.html",
    "page_land_an_wld.html": "https://www.data.jma.go.jp/cpdinfo/temp/land/land_an_wld.html",
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | URL | sha256 の先頭12字 |", "|---|---|---|"]
    for fn, url in FILES.items():
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch (python urllib)"}), timeout=60) as r:
            b = r.read()
        (RAW / fn).write_bytes(b)
        lines.append(f"| {fn} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        time.sleep(0.4)
    lines += ["", "CSV は Shift_JIS（cp932）。偏差の基準は1991〜2020年の平均。",
              "page_*.html は、気象庁が公表している上昇率（100年あたり）を照合するために保存した解説ページ。",
              "世界の陸上のみの年平均気温は、気象庁のページに図と上昇率の文章はあるが、数値の表（CSV）は見つからなかった。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
