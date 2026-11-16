"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
厚生労働省「国民生活基礎調査」（e-Stat、CSV）と、総務省「国勢調査」令和7年 第9-1表（e-Stat、Excel）。
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = [
    ("000040473979", 1, "kiso2025_t014_children_by_year.csv", "国民生活基礎調査 令和7年 第14表 世帯数－構成割合－平均児童数，児童の有－児童数－無・年次別（1975〜2025年）"),
    ("000040474054", 1, "kiso2025_t089_children_by_structure.csv", "国民生活基礎調査 令和7年 第89表 児童のいる世帯数，児童数・世帯構造別"),
    ("000025674640", 1, "kiso2013_t075_children_by_structure.csv", "国民生活基礎調査 平成25年 第75表 児童のいる世帯数，児童数・世帯構造別"),
    ("000040474118", 1, "kiso2025_t153_children_by_pref.csv", "国民生活基礎調査 令和7年 第153表 世帯数，児童の有－児童数－無・都道府県別"),
    ("000025674723", 1, "kiso2013_t015_children_by_pref.csv", "国民生活基礎調査 平成25年 第3巻 第15表 世帯数，児童の有－児童数－無・都道府県別"),
    ("000040474120", 1, "kiso2025_t155_children_structure_by_pref.csv", "国民生活基礎調査 令和7年 第155表 児童のいる世帯数，世帯構造・都道府県別"),
    ("000025674725", 1, "kiso2013_t017_children_structure_by_pref.csv", "国民生活基礎調査 平成25年 第3巻 第17表 児童のいる世帯数，世帯構造・都道府県別"),
    ("000040506456", 0, "census2025_t9_1.xlsx", "国勢調査 令和7年 人口等基本集計 第9-1表 世帯の家族類型、世帯員の年齢による世帯の種類別一般世帯数（原数値）"),
]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    rows = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
            "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for sid, kind, name, desc in FILES:
        url = BASE.format(sid, kind)
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        rows.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        print(name, len(b))
    rows += ["", "出典：厚生労働省「国民生活基礎調査」、総務省「国勢調査」（e-Stat）。CSV は Shift_JIS。",
             "児童の定義：2023年以前は「18歳未満の未婚の者」、2024年以降は「18歳未満の者」（厚生労働省「2024（令和6）年 国民生活基礎調査の概況」用語の解説 https://www.mhlw.go.jp/toukei/saikin/hw/k-tyosa/k-tyosa24/dl/10.pdf ）。"]
    (RAW / "SOURCES.md").write_text("\n".join(rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
