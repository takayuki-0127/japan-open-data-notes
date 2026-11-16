"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
文部科学省「学校教員統計調査」の大学の「年齢別 職名別 性別 本務教員数」（1998〜2022年度）と、
2025年度の「年齢別 職名別 本務教員数（大学）」、年次統計「本務教員の平均年齢」。e-Stat の Excel。"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = [
    ("age_pos_1998", "000001196387", "1998年度 大学 年齢別 職名別 性別 本務教員数"),
    ("age_pos_2001", "000001195721", "2001年度 同"),
    ("age_pos_2004", "000001194055", "2004年度 同（表166）"),
    ("age_pos_2007", "000002847693", "2007年度 同（表170）"),
    ("age_pos_2010", "000012922026", "2010年度 同（表178）"),
    ("age_pos_2013", "000028981467", "2013年度 同（表178）"),
    ("age_pos_2016", "000031687631", "2016年度 同（表205）"),
    ("age_pos_2019", "000032071363", "2019年度 同（表214）"),
    ("age_pos_2022", "000040168153", "2022年度 同（表190）"),
    ("age_pos_2025", "000040477655", "2025年度 年齢別 職名別 本務教員数（大学 計 国立 公立 私立 外国人）（表26）"),
    ("ts_mean_age", "000040477668", "年次統計 学校種別 本務教員の平均年齢（表39、2025年度公表）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, sid, desc in FILES:
        url = BASE.format(sid)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = r.read()
        ext = ".xlsx" if b[:2] == b"PK" else ".xls"
        (RAW / (name + ext)).write_bytes(b)
        lines.append(f"| {name}{ext} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "出典：文部科学省「学校教員統計調査」（e-Stat https://www.e-stat.go.jp/stat-search/files?toukei=00400003&tstat=000001016172）。",
              "調査は3年ごと、10月1日時点。本務教員（その大学に籍のある常勤の教員）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
