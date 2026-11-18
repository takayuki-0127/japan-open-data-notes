"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 国土交通省「鉄道統計年報」各年度のページから「（２）運輸成績表（延日キロ、人（トン）キロ、平均数）」と「（４）営業キロ及び走行キロ表」の Excel を取る（2012〜2023年度）
- 国土交通省「地域鉄道事業者一覧」（PDF）を取り、pdftotext（poppler-utils）で事業者名・営業キロ・第三セクターの印を抜き出して
  data/raw/chiiki_tetsudo_list.csv にする（抜き出し後の CSV から先はオフラインで再現できる）"""
import pathlib, urllib.request, hashlib, datetime, re, subprocess, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
BASE = "https://www.mlit.go.jp"
PAGES = {2012: "/tetudo/tetudo_tk6_000036.html", 2013: "/tetudo/tetudo_tk2_000027.html", 2014: "/tetudo/tetudo_tk2_000038.html",
         2015: "/tetudo/tetudo_tk2_000040.html", 2016: "/tetudo/tetudo_tk2_000045.html", 2017: "/tetudo/tetudo_tk2_000050.html",
         2018: "/tetudo/tetudo_tk2_000051.html", 2019: "/tetudo/tetudo_tk2_000053.html", 2020: "/tetudo/tetudo_tk2_000057.html",
         2021: "/tetudo/tetudo_tk2_000061.html", 2022: "/tetudo/tetudo_tk2_000079.html", 2023: "/tetudo/tetudo_tk1_000074.html"}
LIST_PDF = BASE + "/tetudo/content/001885901.pdf"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "open-data-notes-fetch"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（src/01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for fy, page in sorted(PAGES.items()):
        html = get(BASE + page).decode("utf-8", "ignore"); time.sleep(1)
        links = re.findall(r'<a[^>]+href="([^"]+\.xlsx?)"[^>]*>(.*?)</a>', html, re.S)
        cand = [h for h, t in links if re.search(r"[（(]\s*[２2]\s*[）)]", re.sub(r"<[^>]+>", "", t)) and "運輸成績" in t]
        assert len(cand) == 1, (fy, cand)
        url = cand[0] if cand[0].startswith("http") else BASE + cand[0]
        b = get(url); time.sleep(1)
        name = f"nenpo_{fy}_t02{pathlib.Path(url).suffix}"
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | 鉄道統計年報 {fy}年度（２）運輸成績表（延日キロ、人（トン）キロ、平均数）（ページ：{BASE + page}） | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        cand4 = [h for h, t in links if re.search(r"[（(]\s*[４4]\s*[）)]", re.sub(r"<[^>]+>", "", t)) and "営業キロ" in t]
        assert len(cand4) == 1, (fy, cand4)
        url4 = cand4[0] if cand4[0].startswith("http") else BASE + cand4[0]
        b = get(url4); time.sleep(1)
        name4 = f"nenpo_{fy}_t04{pathlib.Path(url4).suffix}"
        (RAW / name4).write_bytes(b)
        lines.append(f"| {name4} | 鉄道統計年報 {fy}年度（４）営業キロ及び走行キロ表 | {url4} | {hashlib.sha256(b).hexdigest()[:12]} |")
    b = get(LIST_PDF)
    (RAW / "chiiki_tetsudo_list.pdf").write_bytes(b)
    lines.append(f"| chiiki_tetsudo_list.pdf | 地域鉄道事業者一覧（98社、2026年4月1日現在） | {LIST_PDF} | {hashlib.sha256(b).hexdigest()[:12]} |")
    txt = subprocess.run(["pdftotext", "-layout", str(RAW / "chiiki_tetsudo_list.pdf"), "-"], capture_output=True, check=True).stdout.decode("utf-8")
    pairs = re.findall(r"(●?)([^\s●（）()0-9][^\s]*?(?:\s[^\s0-9]+)?)\s+(\d{1,3}\.\d)\b", txt)
    assert len(pairs) == 98, len(pairs)
    with open(RAW / "chiiki_tetsudo_list.csv", "w", encoding="utf-8") as f:
        f.write("name,km,third_sector\n")
        for mark, name, km in pairs:
            f.write(f"{name},{km},{1 if mark else 0}\n")
    lines.append("| chiiki_tetsudo_list.csv | 上の PDF から pdftotext で抜き出した98社（名前・営業キロ・第三セクターの●印） | （01_fetch.py で作成） | — |")
    lines += ["", "- 鉄道統計年報のページ一覧：https://www.mlit.go.jp/tetudo/tetudo_tk6_000032.html",
              "- 地域鉄道対策（「地域鉄道の現状」へのリンクあり）：https://www.mlit.go.jp/tetudo/tetudo_tk5_000002.html",
              "", "出典：国土交通省「鉄道統計年報」「地域鉄道事業者一覧」。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
