"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
JU = "https://www.esri.cao.go.jp/jp/stat/juchu/2026/{}"
QE = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe263/tables/{}"
FILES = [
    (JU.format("2608chouki-1.xlsx"), "juchu_chouki1_2608.xlsx", "内閣府「機械受注統計調査」長期系列(1) 主要需要者別受注・販売・残高（季調・原系列、月次・四半期、2005年4月〜2026年8月）"),
    (QE.format("gaku-mk2631.csv"), "qe_nominal_sa_2631.csv", "内閣府「四半期別GDP速報」2026年7-9月期 1次速報 名目季節調整系列（年率、10億円、1994年1-3月期〜）"),
    (QE.format("gaku-jk2631.csv"), "qe_real_sa_2631.csv", "同 実質季節調整系列（連鎖方式、年率、10億円）"),
    (QE.format("def-qk2631.csv"), "qe_deflator_sa_2631.csv", "同 四半期デフレーター 季節調整系列"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 | バイト数 |", "|---|---|---|---|---|"]
    for url, name, desc in FILES:
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        rows.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} | {len(b)} |")
        print(name, len(b))
    rows += ["", "- 機械受注統計の一覧と長期系列：https://www.esri.cao.go.jp/jp/stat/juchu/juchu.html",
             "- 四半期別GDP速報の統計表一覧（2026年7-9月期 1次速報、2026年11月16日公表）：https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe263/gdemenuja.html",
             "- 機械受注の長期系列は2026年8月分（2026年10月公表）が取得時点の最新。季節調整は公表のたびにかけ直されるので、取り直すと過去の値も少し変わる。",
             "", "出典：内閣府「機械受注統計調査」「四半期別GDP速報（国民経済計算）」。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
