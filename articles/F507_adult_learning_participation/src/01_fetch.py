"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
総務省統計局「社会生活基本調査」（e-Stat の Excel）と、2021年の結果の要約（PDF、照合用）。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [
    ("ssb_timeseries_t1_learning.xlsx", BASE.format("000032229292"),
     "時系列統計表 第1表 男女、年齢、学習・自己啓発・訓練の種類別行動者率の推移（10歳以上）（昭和61年～令和３年）"),
    ("ssb2021_t1-4_purpose_rate.xlsx", BASE.format("000032222678"),
     "令和3年 生活行動 第1-4表 男女,ふだんの健康状態,目的,年齢,学習・自己啓発・訓練の種類別行動者率(10歳以上)－全国"),
    ("ssb2016_t1-4_purpose_rate.xlsx", BASE.format("000031592873"),
     "平成28年 生活行動 第1-4表 男女,ふだんの健康状態,目的,年齢,学習・自己啓発・訓練の種類別行動者率(10歳以上)－全国"),
    ("ssb2021_youyakua.pdf", "https://www.stat.go.jp/data/shakai/2021/pdf/youyakua.pdf",
     "令和3年社会生活基本調査 生活行動に関する結果 結果の要約（照合用）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, url, desc in FILES:
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "出典：総務省統計局「社会生活基本調査」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00200533）。",
              "各回の調査は10月20日時点で、行動者率は過去1年間に1回以上その活動をした人の割合。",
              "結果の要約：https://www.stat.go.jp/data/shakai/2021/kekka.html"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
