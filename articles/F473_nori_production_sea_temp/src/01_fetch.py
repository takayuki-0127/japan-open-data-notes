"""元データの取得（ネットが必要。run_all.sh からは呼ばない）。
- 農林水産省「漁業・養殖業生産統計」（e-Stat）：各年の海面養殖業 都道府県別 のり類収獲量（2004〜2024年）と、
  長期累年 養殖魚種別収獲量累年統計（全国、1956〜2024年）
  各年の表は、一覧のページの節（海面養殖業の部）と表の題（「のり類」を含み、都道府県別の表）の文字で選ぶ
- 気象庁「海面水温の長期変化傾向（日本近海）」の海域平均海面水温の平年差（季節別）
"""
import pathlib, re, html, time, json, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
UA = {"User-Agent": "Mozilla/5.0 (open-data-notes)"}
LIST = ("https://www.e-stat.go.jp/stat-search/files?toukei=00500216&tstat=000001015174&cycle=7&tclass1=000001015175"
        "&tclass2={t}&layout=datalist&page=1&tclass3val=0&limit=300")
DL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={i}&fileKind=0"
LONG = "000040416372"  # 表番号6 養殖魚種別収獲量累年統計 全国（昭和31年〜令和6年）
YEARS = {2004: "000001015877", 2005: "000001018046", 2006: "000001022526", 2007: "000001036359", 2008: "000001040095",
         2009: "000001043685", 2010: "000001049476", 2011: "000001056058", 2012: "000001056059", 2013: "000001068028",
         2014: "000001077817", 2015: "000001093555", 2016: "000001110615", 2017: "000001124915", 2018: "000001136043",
         2019: "000001148733", 2020: "000001162470", 2021: "000001201760", 2022: "000001214760", 2023: "000001226201",
         2024: "000001240977"}
SST = {"C": "東シナ海北部", "N": "四国・東海沖", "M": "関東の南", "K": "三陸沖", "all": "全海域平均"}
# 頑健性用：のりの産地の近くの気象台の月平均気温（全年の表）
STATIONS = {"佐賀": (85, 47813), "高松": (72, 47891), "名古屋": (51, 47636), "千葉": (45, 47682), "仙台": (34, 47590)}
ST_URL = "https://www.data.jma.go.jp/stats/etrn/view/monthly_s3.php?prec_no={p}&block_no={b}&year=2024&month=&day=&view="
SST_URL = "https://www.data.jma.go.jp/kaiyou/data/shindan/a_1/japan_warm/cfig/data/area{a}_SST.txt"


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        b = r.read()
    time.sleep(0.8)
    return b


def ext(b):
    return "xlsx" if b[:2] == b"PK" else "xls"


def pick(page):
    sec, out = "", []
    for blk in re.split(r'stat-dataset_list-item"', page)[1:]:
        t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", blk))).strip()
        ids = re.findall(r"statInfId=(\d+)&fileKind=0", blk)
        if not ids:
            sec = t; continue
        if "海面養殖業" in sec and "のり類" in t and "都道府県" in t and "種苗" not in t.split("のり類")[-1][:6]:
            out.append((t[:120], ids[0]))
    return out


def main():
    (RAW / "maff").mkdir(parents=True, exist_ok=True); (RAW / "jma").mkdir(parents=True, exist_ok=True)
    b = get(DL.format(i=LONG)); (RAW / "maff" / f"long_yoshoku_national.{ext(b)}").write_bytes(b)
    man = {}
    for y, t in YEARS.items():
        sel = pick(get(LIST.format(t=t)).decode("utf-8"))
        man[y] = sel
        assert len(sel) >= 1, (y, sel)
        b = get(DL.format(i=sel[0][1]))
        (RAW / "maff" / f"nori_{y}.{ext(b)}").write_bytes(b)
    (RAW / "maff" / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    for a in SST:
        (RAW / "jma" / f"area{a}_SST.txt").write_bytes(get(SST_URL.format(a=a)))
    for name, (p, b) in STATIONS.items():
        (RAW / "jma" / f"station_{b}.html").write_bytes(get(ST_URL.format(p=p, b=b)))


if __name__ == "__main__":
    main()
