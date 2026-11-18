"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 農林水産省「食料需給表」確報 令和6年度 品目別累年表 小麦（e-Stat CSV、1960〜2024年度）
- 農林水産省「食料需給表」令和7年度（概算）の統計表 Excel（2025年度の値と2024年度の確定値）
- 農林水産省「作物統計」収穫量累年統計 小麦（全国・北海道・都府県・9地方、e-Stat Excel）"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "open-data-notes-fetch (python urllib)"}
E = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
FILES = {
    "fbs_wheat_ruinen_r6.csv": (E.format("000040422813", 1), "食料需給表 確報 令和6年度 品目別累年表 穀類／小麦（1960〜2024年度、CSV・Shift_JIS）"),
    "fbs_r7_gaisan.xlsx": ("https://www.maff.go.jp/j/zyukyu/fbs/attach/xls/index-4.xlsx", "食料需給表 令和7年度（概算）統計表（シート1：令和7年度概算、シート2：令和6年度確定）"),
}
# 作物統計 収穫量累年統計 小麦。名前は取得後に表の4行目（地域名）で確かめる（02_build.py）
CROP = [("000040383862", "全国"), ("000040383863", "北海道"), ("000040383864", "都府県"),
        ("000040383865", "東北"), ("000040383866", "北陸"), ("000040383867", "関東・東山"),
        ("000040383868", "東海"), ("000040383869", "近畿"), ("000040383870", "中国"),
        ("000040383871", "四国"), ("000040383872", "九州"), ("000040383873", "沖縄")]
for sid, name in CROP:
    FILES[f"crop_wheat_{sid}.xls"] = (E.format(sid, 0), f"作物統計 収穫量累年統計 小麦 {name}（Excel）")


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (url, desc) in FILES.items():
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            b = r.read()
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        time.sleep(0.5)
    lines += ["", "- 食料需給表の掲載ページ：https://www.maff.go.jp/j/zyukyu/fbs/ （令和6年度確報の e-Stat：https://www.e-stat.go.jp/stat-search/files?page=1&layout=datalist&toukei=00500300&tstat=000001017950&cycle=8&tclass1=000001032890&tclass2=000001241316 ）",
              "- 作物統計 長期累年の一覧：https://www.e-stat.go.jp/stat-search/files?page=1&toukei=00500215&tstat=000001013427&cycle=0&tclass1=000001032288&tclass2=000001034728&layout=datalist",
              "- 食料需給表は「年度」（4月〜翌3月）。作物統計は「産年」（その年に収穫した麦）。小麦は初夏に収穫するため、需給表の t 年度の国内生産量は t 年産の収穫量と同じ値になる（02_build.py で照合）。",
              "", "出典：農林水産省「食料需給表」「作物統計」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
