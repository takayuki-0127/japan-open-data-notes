"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省「通信利用動向調査」世帯全体編「問２ 自宅でインターネットを利用する世帯の接続回線」（2019〜2025年、e-Stat の CSV）と、
総務省「情報通信統計データベース」ブロードバンドサービス等の契約数の推移（四半期）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
EST = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=1"
IDS = {2019: "000031951243", 2020: "000032097923", 2021: "000032203927", 2022: "000040057133",
       2023: "000040185390", 2024: "000040278927", 2025: "000040458866"}
BB = "https://www.soumu.go.jp/johotsusintokei/field/data/gt010103.xls"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for y, sid in IDS.items():
        url = EST.format(sid); b = get(url)
        name = f"tsushin_{y}_lines.csv"; (RAW / name).write_bytes(b)
        lines.append(f"| {name} | 通信利用動向調査 {y}年 世帯全体編 問２ 自宅でインターネットを利用する世帯の接続回線（CSV、Shift_JIS） | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    b = get(BB); (RAW / "gt010103.xls").write_bytes(b)
    lines.append(f"| gt010103.xls | ブロードバンドサービス等の契約数の推移（四半期、2023年6月末〜2026年6月末） | {BB} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "- 通信利用動向調査：https://www.e-stat.go.jp/stat-search/files?toukei=00200356",
              "- 情報通信統計データベース：https://www.soumu.go.jp/johotsusintokei/field/tsuushin02.html",
              "", "出典：総務省「通信利用動向調査」「情報通信統計データベース」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
