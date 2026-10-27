"""データの取得。

感染症発生動向調査（IDWR 速報データ）の「定点把握疾患 都道府県別 報告数・定点当たり報告数」
（*-teiten.csv、Shift_JIS）を、2012年〜2026年の週ごとに取り、インフルエンザの列だけを抜き出す。

- 2012〜2022年：https://id-info.jihs.go.jp/niid/ja/idwr/rapid/{年}.html から各週のデータページをたどり、
  そのページにある「-teiten.csv」を取る
- 2023年〜：https://id-info.jihs.go.jp/surveillance/idwr/provisional/{年}/{週}/{年}-{週}-teiten.csv

記事ではブラウザのページの中で同じ手順を実行し（アクセスの間隔は0.25秒以上）、
結果を data/raw/f52_teiten_flu.json に保存した。このスクリプトは同じことを Python で行う。

隣接・距離（F33）、都道府県間の移動者数（F10）、人口（F10）は、それぞれの記事のデータを
data/raw/ にコピーして使っている。
"""
import json, re, time, csv, io
from urllib.parse import urljoin
import requests
from common import RAW

BASE = "https://id-info.jihs.go.jp"
S = requests.Session()


def get(url):
    r = S.get(url, timeout=60)
    time.sleep(0.3)
    return r


def parse(txt, src):
    R = list(csv.reader(io.StringIO(txt)))
    hi = next(i for i, r in enumerate(R) if "インフルエンザ" in r)
    ci = R[hi].index("インフルエンザ")
    per = R[1][0] if len(R) > 1 and R[1] else ""
    out = []
    for r in R[hi + 2:]:
        if r and r[0]:
            out.append([src, per, r[0], r[ci], r[ci + 1]])
    return out


def main():
    urls = []
    for y in range(2012, 2023):
        page = f"{BASE}/niid/ja/idwr/rapid/{y}.html"
        html = get(page).text
        for h in sorted(set(re.findall(r'href="([^"]*data/\d+-idwr-sokuho-data[^"]*)"', html))):
            dp = urljoin(page, h)
            m = re.search(r'href="([^"]*-teiten\.csv)"', get(dp).text)
            if m:
                urls.append(urljoin(dp, m.group(1)))
    for y in range(2023, 2027):
        for w in range(1, 54):
            urls.append(f"{BASE}/surveillance/idwr/provisional/{y}/{w:02d}/{y}-{w:02d}-teiten.csv")
    rows = []
    for u in urls:
        r = get(u)
        if r.status_code != 200 or r.content[:1] == b"<":
            continue
        rows += parse(r.content.decode("cp932", errors="replace"), u.split("/")[-1])
    json.dump({"rows": rows}, open(RAW / "f52_teiten_flu.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(len(rows))


if __name__ == "__main__":
    main()
