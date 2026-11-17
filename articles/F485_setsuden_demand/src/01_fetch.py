"""元データを取る（ネットにつなぐのはこのスクリプトだけ。run_all.sh からは呼ばない）。
- 九州電力送配電「エリア需給実績データ」2018〜2023年度（1時間値、四半期ファイル）、2024年度（30分値、月ファイル）
- 気象庁「過去の気象データ検索」日ごとの値（福岡・鹿児島、2018年4月〜2025年3月）。HTML の表から日平均気温を抜き出して CSV に保存
- 内閣府「国民の祝日」CSV"""
import pathlib, urllib.request, hashlib, datetime, time, re, html

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
UA = {"User-Agent": "open-data-notes-fetch (python urllib)"}
K = "https://www.kyuden.co.jp/td_area_jukyu/"
FILES = {}
for fy in range(2018, 2024):
    tag = "H30" if fy == 2018 else str(fy)
    for q in range(1, 5):
        n = f"area_jyukyu_jisseki_{tag}_{q}Q.csv"
        FILES[n] = (K + "csv_area_jyukyu_jisseki/" + n, f"九州 {fy}年度 第{q}四半期 1時間値")
for y, m in [(2024, m) for m in range(4, 13)] + [(2025, m) for m in range(1, 4)]:
    n = f"eria_jukyu_{y}{m:02d}_09.csv"
    FILES[n] = (K + "csv/" + n, f"九州 {y}年{m}月 30分値")
FILES["syukujitsu.csv"] = ("https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv", "内閣府 国民の祝日")
STATIONS = {"fukuoka": (82, 47807), "kagoshima": (88, 47827)}
J = "https://www.data.jma.go.jp/stats/etrn/view/daily_s1.php?prec_no={}&block_no={}&year={}&month={}&day=&view="


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def jma_month(prec, block, y, m):
    """日ごとの値の表から、日と日平均気温（7列目＝気温の平均）を取る。"""
    s = get(J.format(prec, block, y, m)).decode("utf-8", "replace")
    out = []
    for tr in re.findall(r"<tr class=\"mtx\"[^>]*>(.*?)</tr>", s, flags=re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S)]
        if cells and cells[0].isdigit():
            out.append((int(cells[0]), cells[6]))
    return out


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    lines = ["# SOURCES（元データの取得元）", "", f"取得日：{datetime.date.today().isoformat()}（01_fetch.py で取得）", "",
             "| ファイル | 中身 | URL | sha256 の先頭12字 |", "|---|---|---|---|"]
    for name, (url, desc) in FILES.items():
        b = get(url)
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | {desc} | {url} | {hashlib.sha256(b).hexdigest()[:12]} |")
        time.sleep(0.3)
    for st, (prec, block) in STATIONS.items():
        rows = ["date,temp_mean_raw"]
        for y, m in [(y, m) for y in range(2018, 2026) for m in range(1, 13)]:
            if (y, m) < (2018, 4) or (y, m) > (2025, 3):
                continue
            for d, v in jma_month(prec, block, y, m):
                rows.append(f"{y:04d}-{m:02d}-{d:02d},{v}")
            time.sleep(0.3)
        b = ("\n".join(rows) + "\n").encode("utf-8")
        name = f"jma_daily_{st}.csv"
        (RAW / name).write_bytes(b)
        lines.append(f"| {name} | 気象庁 {st} の日平均気温（2018年4月〜2025年3月、日ごとの値のページから抜き出し） | {J.format(prec, block, 'YYYY', 'M')} | {hashlib.sha256(b).hexdigest()[:12]} |")
    lines += ["", "出典：九州電力送配電「エリア需給実績データ」、気象庁「過去の気象データ検索」、内閣府「国民の祝日について」。",
              "気象庁の値の「]」「)」などの記号（資料不足値・準正常値）は文字のまま残し、02_build.py で数字だけを取り出す。"]
    (RAW / "SOURCES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
