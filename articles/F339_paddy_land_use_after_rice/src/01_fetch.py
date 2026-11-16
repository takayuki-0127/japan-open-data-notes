"""元データを e-Stat から取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
農林水産省「作物統計調査（面積調査）」耕地及び作付面積統計・作物統計の Excel を data/raw/ に保存する。
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=0"
FILES = {
    # 名前: (statInfId, 中身)
    "summer_paddy_use_1966_2025.xlsx": ("000040507741", "令和7年 累年統計 3-3 夏期における田本地の利用状況の推移（全国、1966〜2025年）"),
    "summer_paddy_use_region_2025.xlsx": ("000040507740", "令和7年 表2 夏期における田本地の利用状況（全国農業地域・都道府県、2024・2025年）"),
    "summer_paddy_use_region_2004.xls": ("000004578720", "平成16年 表1 夏期における田本地の利用状況（全国農業地域・都道府県、2003・2004年）"),
    "paddy_crops_1967_2016.xls": ("000040405321", "令和6年 累年統計 3-1 農作物作付（栽培）延べ面積 田（1967〜2016年、作物類別）"),
    "paddy_crops_2017_2024.xls": ("000040405324", "令和6年 累年統計 3-2 農作物作付（栽培）延べ面積 田（2017〜2024年）"),
    "paddy_expansion_abandon_1956_2025.xlsx": ("000040506892", "令和7年 累年統計 1(2)イ 耕地の拡張・かい廃面積 田（1956〜2025年）"),
    "land_area_honchi_1956_2025.xlsx": ("000040519967", "長期累年 表1 本地・けい畔別耕地面積累年統計 全国（1956〜2025年）"),
    "rice_suito_longterm.xls": ("000040433903", "作物統計 長期累年 表1 収穫量累年統計 水稲 全国（主食用作付面積を含む）"),
    "feed_rice_wcs_2008_2025.xlsx": ("000040495199", "令和7年 累年統計 2(8)［参考］飼料用米、WCS用稲（2008〜2025年）"),
}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "",
             f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (sid, desc) in FILES.items():
        url = BASE.format(sid)
        p = RAW / name
        with urllib.request.urlopen(url, timeout=60) as r:
            p.write_bytes(r.read())
        h = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
        lines.append(f"| {name} | {desc} | {url} | {h} |")
        print(name, p.stat().st_size)
    lines += ["", "出典：農林水産省「作物統計調査（面積調査）」（耕地及び作付面積統計）、「作物統計調査（作況調査）」。e-Stat（政府統計の総合窓口）で公開されているファイル。",
              "注：ファイルの拡張子は中身の形式に合わせた（e-Stat は旧形式の Excel にも .xlsx の名前を付けて配ることがある）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
