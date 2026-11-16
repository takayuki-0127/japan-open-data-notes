"""01 取得（run_all.sh からは呼ばない）
国土交通省「宅配便の再配達率サンプル調査」各回の報道発表（2017年10月期〜2026年4月期）の PDF を取る。
一覧：https://www.mlit.go.jp/seisakutokatsu/freight/re_delivery_research.html
"""
import pathlib, re, time, urllib.parse, urllib.request

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "Mozilla/5.0"}
PAGES = {
    "2017-10": "https://www.mlit.go.jp/report/press/tokatsu01_hh_000364.html",
    "2018-04": "https://www.mlit.go.jp/report/press/re_delivery_1804.html",
    "2018-10": "https://www.mlit.go.jp/report/press/re_delivery_1810.html",
    "2019-04": "https://www.mlit.go.jp/report/press/re_delivery_1904.html",
    "2019-10": "https://www.mlit.go.jp/report/press/tokatsu01_hh_000484.html",
    "2020-04": "https://www.mlit.go.jp/report/press/tokatsu01_hh_000513.html",
    "2020-10": "https://www.mlit.go.jp/report/press/tokatsu01_hh_000529.html",
    "2021-04": "https://www.mlit.go.jp/report/press/tokatsu01_hh_000561.html",
    "2021-10": "https://www.mlit.go.jp/report/press/tokatsu01_hh_000581.html",
    "2022-04": "https://www.mlit.go.jp/report/press/tokatsu01_hh_000613.html",
    "2022-10": "https://www.mlit.go.jp/report/press/tokatsu01_hh_000645.html",
    "2023-04": "https://www.mlit.go.jp/report/press/tokatsu01_hh_000694.html",
    "2023-10": "https://www.mlit.go.jp/report/press/tokatsu01_hh_000736.html",
    "2024-04": "https://www.mlit.go.jp/report/press/tokatsu01_hh_000791.html",
    "2024-10": "https://www.mlit.go.jp/report/press/tokatsu01_hh_000846.html",
    "2025-04": "https://www.mlit.go.jp/report/press/tokatsu01_hh_000908.html",
    "2025-10": "https://www.mlit.go.jp/report/press/tokatsu01_hh_000956.html",
    "2026-04": "https://www.mlit.go.jp/report/press/tokatsu01_hh_001025.html",
}


def get(url):
    time.sleep(1.0)
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    for k, u in PAGES.items():
        h = get(u).decode("utf-8", "replace")
        pdfs = re.findall(r'href="([^"]+\.pdf)"', h)
        if not pdfs:
            print(k, "PDF なし"); continue
        for j, p in enumerate(pdfs[:2]):
            p = urllib.parse.urljoin(u, p)
            try:
                (RAW / f"press_{k}_{j + 1}.pdf").write_bytes(get(p))
                print(k, j + 1, p)
            except Exception as e:
                print(k, j + 1, p, "取れない", e)


if __name__ == "__main__":
    main()
