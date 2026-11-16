"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 日本銀行「全国企業短期経済観測調査（短観）」業況判断DI（日本銀行 API、db=CO）
- 内閣府「四半期別GDP速報」実質季節調整系列（前期比）：最新の公表回（2026年4-6月期2次速報）と、各四半期の1次速報
"""
import pathlib, urllib.request, hashlib, datetime, re, time

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
ESRI = "https://www.esri.cao.go.jp"
TANKAN = ["TK99F0000601GCQ00000", "TK99F1000601GCQ00000", "TK99F2000601GCQ00000", "TK99F1000601GCQ01000", "TK99F2000601GCQ01000",
          "TK99F0000601GCQ01000", "TK99F1000601GCQ11000"]


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    def rec(name, desc, url, b):
        (RAW / name).parent.mkdir(parents=True, exist_ok=True)
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
    url = f"https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=jp&db=CO&code={','.join(TANKAN)}&startDate=197401&endDate=202604"
    rec("tankan_di.json", "短観 業況判断DI（全規模・大企業 × 全産業・製造業・非製造業、実績。大企業製造業の予測）", url, get(url))
    url = f"{ESRI}/jp/sna/data/data_list/sokuhou/files/2026/qe262_2/tables/ritu-jk2622.csv"
    rec("gdp_latest_ritu-jk2622.csv", "四半期別GDP速報 2026年4-6月期2次速報 実質季節調整系列（前期比）", url, get(url))
    n = 0
    for y in range(2004, 2027):
        for q in range(1, 5):
            if y == 2026 and q > 2:
                continue
            page = f"{ESRI}/jp/sna/data/data_list/sokuhou/files/{y}/qe{str(y)[2:]}{q}/gdemenuja.html"
            try:
                html = get(page).decode("utf-8", "ignore")
            except Exception as e:
                lines.append(f"| （取れず）{y}Q{q} 1次速報 | {e} | {page} | - |")
                continue
            m = re.search(r'href="([^"]*ritu[-_]jk[^"]*\.csv)"', html)
            if not m:
                lines.append(f"| （リンクなし）{y}Q{q} 1次速報 | - | {page} | - |")
                continue
            href = m.group(1)
            full = href if href.startswith("http") else (ESRI + href if href.startswith("/") else page.rsplit("/", 1)[0] + "/" + href)
            rec(f"gdp_first/first_{y}Q{q}.csv", f"四半期別GDP速報 {y}年{q}期 1次速報 実質季節調整系列（前期比）", full, get(full))
            n += 1
            time.sleep(0.3)
    lines += ["", f"1次速報の CSV：{n} 回分。", "出典：日本銀行「全国企業短期経済観測調査」（時系列統計データ検索サイトの API）、内閣府経済社会総合研究所「四半期別GDP速報」。GDP の CSV は Shift_JIS（cp932）。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("first releases:", n)


if __name__ == "__main__":
    main()
