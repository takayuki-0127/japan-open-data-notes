"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 日本銀行「企業物価指数（2015年基準）需要段階別・用途別指数」（1960〜2022年4月）
- 日本銀行「最終需要・中間需要物価指数（2020年基準）」（2015年1月〜）
- 総務省「消費者物価指数（2020年基準）財・サービス分類指数」（全国、1970年1月〜）
"""
import pathlib, urllib.request, hashlib, datetime

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
API = "https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db={db}&code={codes}&startDate={s}&endDate={e}"
STAGE15 = ["PRCG15_18K0110000", "PRCG15_18K0210000", "PRCG15_18K0310000", "PRCG15_18K0322002", "PRCG15_18K0321001", "PRCG15_18K0000000",
           "PRCG15_18K0121001", "PRCG15_18K0221001"]
FDID20 = [f"PRFI20_1I{s}{k}" for s in "1234" for k in ("A00000", "G00000", "LD0000")] + ["PRFI20_1FXA00000", "PRFI20_1FXG00000", "PRFI20_1FXG00100",
                                                                                        "PRFI20_1FXG00200", "PRFI20_1FXG00300", "PRFI20_1FXSD0000"]
REQ = {
    "boj_stage_2015base.json": (API.format(db="PR01", codes=",".join(STAGE15), s="196001", e="202204"), "企業物価指数 2015年基準 需要段階別・用途別指数（素原材料・中間財・最終財など、月次）"),
    "boj_fdid_2020base.json": (API.format(db="PR04", codes=",".join(FDID20), s="201501", e="202609"), "最終需要・中間需要物価指数 2020年基準（ステージ1〜4、最終需要（除く輸出）、月次）"),
    "cpi_goods_services_1970_2026.csv": ("https://www.e-stat.go.jp/stat-search/file-download?statInfId=000032103845&fileKind=1",
                                         "消費者物価指数 2020年基準 財・サービス分類指数（全国、月次、1970年1月〜2026年9月）"),
}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (url, desc) in REQ.items():
        req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
        with urllib.request.urlopen(req, timeout=120) as r:
            (RAW / name).write_bytes(r.read())
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256((RAW / name).read_bytes()).hexdigest()[:12]} |")
        print(name, (RAW / name).stat().st_size)
    lines += ["", "出典：日本銀行「企業物価指数」「最終需要・中間需要物価指数」（時系列統計データ検索サイトの API）、総務省「消費者物価指数」（e-Stat）。CPI の CSV は Shift_JIS（cp932）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
