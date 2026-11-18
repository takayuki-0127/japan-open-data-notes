"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
気象庁の CO2 濃度の月平均（綾里・南鳥島・与那国島）、気象庁の解説ページ、エルニーニョ監視指数（NINO.3）、
国立環境研究所 温室効果ガスインベントリオフィスの「日本の温室効果ガス排出量データ」（Excel）を保存する。"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
FILES = {
    "co2_monthave_ryo.csv": "https://www.data.jma.go.jp/ghg/kanshi/obs/co2_monthave_ryo.csv",
    "co2_monthave_mnm.csv": "https://www.data.jma.go.jp/ghg/kanshi/obs/co2_monthave_mnm.csv",
    "co2_monthave_yon.csv": "https://www.data.jma.go.jp/ghg/kanshi/obs/co2_monthave_yon.csv",
    "page_co2_trend.html": "https://www.data.jma.go.jp/ghg/kanshi/ghgp/co2_trend.html",
    "nino3idx.html": "https://www.data.jma.go.jp/cpd/db/elnino/index/nino3idx.html",
    "L5-7gas_2026_gioweb_ver1.0.xlsx": "https://www.nies.go.jp/gio/archive/ghgdata/k6efli000007q2e2-att/L5-7gas_2026_gioweb_ver1.0.xlsx",
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | URL | sha256 の先頭12字 |", "|---|---|---|"]
    for fn, url in FILES.items():
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch (python urllib)"}), timeout=120) as r:
            b = r.read()
        (RAW / fn).write_bytes(b)
        lines.append(f"| {fn} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        time.sleep(0.4)
    lines += ["", "CO2 の CSV は Shift_JIS（cp932）。単位は ppm。与那国島は2024年3月末で観測を終えた（気象庁の解説ページ）。",
              "排出量の Excel は国立環境研究所 温室効果ガスインベントリオフィス「日本の温室効果ガス排出量データ（1990〜2024年度）確報値」（https://www.nies.go.jp/gio/archive/ghgdata/index.html）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
