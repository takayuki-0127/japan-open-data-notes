"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 内閣府「消費動向調査」長期時系列表 2表（二人以上の世帯、季節調整値）・1表（原数値）（e-Stat、2026年10月調査の公表分）
- 内閣府「四半期別GDP速報」2026年7-9月期1次速報 実質季節調整系列（実額、家計最終消費支出の形態別を含む）
- 総務省「家計調査」長期時系列 表2 用途分類（二人以上の世帯、月）（e-Stat）
- 総務省「消費者物価指数」2025年基準 全国 中分類指数（月次、e-Stat）
"""
import pathlib, urllib.request, hashlib, datetime, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
E = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind={}"
QE = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe263/tables/{}"
UA = {"User-Agent": "open-data-notes-fetch (python urllib)"}
FILES = [
    ("cci_t2_sa.xlsx", "消費動向調査 長期時系列表 2表 消費者態度指数・消費者意識指標（二人以上の世帯、季節調整値、1982年6月〜2026年10月）", E.format("000040522411", 0)),
    ("cci_t1_orig.xlsx", "消費動向調査 長期時系列表 1表 消費者態度指数・消費者意識指標（二人以上の世帯、原数値）", E.format("000040522412", 0)),
    ("qe_gaku-jk2631.csv", "四半期別GDP速報 2026年7-9月期1次速報 実質季節調整系列 実額（2020暦年連鎖価格、1994年1-3月期〜）", QE.format("gaku-jk2631.csv")),
    ("qe_kgaku-jk2631.csv", "四半期別GDP速報 2026年7-9月期1次速報 実質季節調整系列 家計最終消費支出の形態別 実額", QE.format("kgaku-jk2631.csv")),
    ("kakei_ts2_youto_monthly.xlsx", "家計調査 長期時系列 表2 用途分類（二人以上の世帯、月・四半期・年、2000年〜）", E.format("000040270657", 4)),
    ("cpi_2025base_middle_class_monthly.csv", "消費者物価指数 2025年基準 全国 中分類指数（月次、1970年1月〜、cp932）", E.format("000040482943", 1)),
]


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 | バイト |", "|---|---|---|---|---|"]
    for name, desc, url in FILES:
        b = get(url)
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} | {len(b)} |")
        time.sleep(0.5)
    lines += ["",
              "- 消費動向調査のファイル一覧：https://www.e-stat.go.jp/stat-search/files?toukei=00100405&tstat=000001014549（長期時系列表は最新月の公表分に入る。月が進むとファイル番号が変わる）",
              "- 四半期別GDP速報：https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe263/gdemenuja.html（CSV は Shift_JIS）",
              "- 家計調査 長期時系列：https://www.e-stat.go.jp/stat-search/files?toukei=00200561",
              "- 消費者物価指数：https://www.e-stat.go.jp/stat-search/files?tstat=000001243876",
              "",
              "出典：内閣府「消費動向調査」、内閣府経済社会総合研究所「四半期別GDP速報」、総務省統計局「家計調査（家計収支編）」「消費者物価指数」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
