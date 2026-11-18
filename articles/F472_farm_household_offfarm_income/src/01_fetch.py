"""元データの取得（ネットが必要。run_all.sh からは呼ばない）。
農林水産省「農業経営統計調査 経営形態別経営統計（個別経営）」（e-Stat、2004〜2018年）。
- 長期累年：全国年次別統計表 (1) 経営の概要と分析指標（2004〜2018年）
- 各年：「農業の主副業別統計表」と「都府県経営耕地規模別統計表」（2016年以降は「全国農業地域別・経営耕地規模別統計表」の都府県）の
  「経営の概要と分析指標」
各年の表は、e-Stat の一覧のページの見出しの文字で選ぶ（表番号は年で変わる）。
"""
import pathlib, re, html, time, json, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "maff"
UA = {"User-Agent": "Mozilla/5.0 (open-data-notes)"}
LIST = ("https://www.e-stat.go.jp/stat-search/files?toukei=00500201&tstat=000001013460&cycle=7&tclass1=000001033169"
        "&tclass2=000001033170&tclass3={t}&layout=datalist&page=1&tclass4val=0&limit=500")
DL = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={i}&fileKind=0"
LONG = "000031978010"  # 長期累年 (1) 経営の概要と分析指標（平成16年〜平成30年）
YEARS = {2004: "000001033171", 2005: "000001036929", 2006: "000001022168", 2007: "000001034991", 2008: "000001040594",
         2009: "000001041884", 2010: "000001050726", 2011: "000001059537", 2012: "000001059443", 2013: "000001072883",
         2014: "000001086076", 2015: "000001101015", 2016: "000001115715", 2017: "000001126722", 2018: "000001138831"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        b = r.read()
    time.sleep(0.8)
    return b


def pick(page):
    """一覧のページを見出し（節）ごとに分け、主副業別と都府県の規模別の『経営の概要と分析指標』の ID を返す。"""
    out, sec = {"shufuku": [], "kibo_tofuken": []}, ""
    for b in re.split(r'stat-dataset_list-item"', page)[1:]:
        t = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", b))).strip()
        ids = re.findall(r"statInfId=(\d+)&fileKind=0", b)
        if not ids:
            sec = t.replace(">", "").strip(); continue
        if "経営の概要と分析指標" not in t:
            continue
        if sec.startswith("農業の主副業別統計表"):
            out["shufuku"].append((t[:80], ids[0]))
        elif sec.startswith("都府県経営耕地規模別統計表") or (sec.startswith("全国農業地域別・経営耕地規模別統計表") and "都府県" in t):
            out["kibo_tofuken"].append((t[:80], ids[0]))
    return out


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "long_1_1.xls").write_bytes(get(DL.format(i=LONG)))
    manifest = {}
    for y, t in YEARS.items():
        p = get(LIST.format(t=t)).decode("utf-8")
        sel = pick(p)
        manifest[y] = sel
        for kind, lst in sel.items():
            for k, (title, i) in enumerate(lst):
                (RAW / f"{kind}_{y}_{k + 1}.xls").write_bytes(get(DL.format(i=i)))
    (RAW / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
