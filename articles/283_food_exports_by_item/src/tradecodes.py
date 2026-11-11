"""財務省「貿易統計」（普通貿易統計、e-Stat）の取得と、コード表（概況品・国名・税関）の読み込み

取得元
- 統計表のCSV：e-Stat https://www.e-stat.go.jp/stat-search/file-download?statInfId=<ID>&fileKind=1
- 概況品コード表：https://www.customs.go.jp/toukei/sankou/code/GH202501i.html（輸入）・GH202501e.html（輸出）
- 統計国名符号表：https://www.customs.go.jp/toukei/sankou/dgorder/a1.htm
- 税関符号表：https://www.customs.go.jp/toukei/sankou/dgorder/a2.htm
金額の単位は千円。
"""
import re, html
from pathlib import Path
import pandas as pd

ESTAT = "https://www.e-stat.go.jp/stat-search/file-download?statInfId={}&fileKind=1"
CODE_PAGES = {
    "GH202501i.html": "https://www.customs.go.jp/toukei/sankou/code/GH202501i.html",
    "GH202501e.html": "https://www.customs.go.jp/toukei/sankou/code/GH202501e.html",
    "a1.html": "https://www.customs.go.jp/toukei/sankou/dgorder/a1.htm",
    "a2.html": "https://www.customs.go.jp/toukei/sankou/dgorder/a2.htm",
}


def download(files, raw):
    """files: {保存名: statInfId}。ネットワークにつながる環境で使う"""
    import requests
    raw = Path(raw); raw.mkdir(parents=True, exist_ok=True)
    for name, sid in files.items():
        (raw / name).write_bytes(requests.get(ESTAT.format(sid), timeout=120).content)
    for name, url in CODE_PAGES.items():
        (raw / name).write_bytes(requests.get(url, timeout=60).content)


def _rows(path):
    s = Path(path).read_bytes().decode("cp932", errors="replace")
    out = []
    for t in re.findall(r"<tr[^>]*>(.*?)</tr>", s, flags=re.S):
        out.append([html.unescape(re.sub(r"<[^>]+>", "", x)).strip()
                    for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", t, flags=re.S)])
    return out


def _jname(s):
    s = s.replace("　", " ").strip()
    m = re.search(r"[A-Z][A-Z0-9 ,.()\-&'/;:]*$", s)
    return s[:m.start()].strip() if m and m.start() > 0 else s


def _ranges(spec):
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "～" in part:
            a, b = [x.strip() for x in part.split("～", 1)]
            da = re.sub(r"[^0-9]", "", a)
            if b.startswith("-"):
                db = re.sub(r"[^0-9]", "", a.rsplit("-", 1)[0]) + re.sub(r"[^0-9]", "", b)
            else:
                db = re.sub(r"[^0-9]", "", b)
            out.append((da, db))
        else:
            d = re.sub(r"[^0-9]", "", part); out.append((d, d))
    return out


def gaikyo(raw, kind):
    """概況品コード表（kind='i' 輸入, 'e' 輸出）：code, unit, name, hs（統計品目番号の範囲）"""
    f = Path(raw) / {"i": "GH202501i.html", "e": "GH202501e.html"}[kind]
    rs = [r for r in _rows(f) if len(r) >= 4 and re.fullmatch(r"\d+", r[0])]
    return pd.DataFrame([(r[0], r[1], _jname(r[2]), r[3]) for r in rs], columns=["code", "unit", "name", "hs"])


def _hit(h, ranges):
    for a, b in ranges:
        if a <= h[:len(a)] and h[:len(b)] <= b:
            return True
    return False


def finest_gaikyo(hs_codes, raw, kind):
    """9桁の統計品目番号を、範囲に入るいちばん細かい概況品に割り当てる（見つからなければ空）"""
    g = gaikyo(raw, kind)
    g = g.assign(depth=g.code.str.len(), rg=g.hs.map(_ranges)).sort_values(["depth", "code"], ascending=[False, True])
    g = g[g.depth > 1]
    out = []
    for h in hs_codes:
        hit = next(((c, n) for c, n, rg in zip(g.code, g["name"], g.rg) if _hit(h, rg)), ("", ""))
        out.append((h,) + hit)
    return pd.DataFrame(out, columns=["HS", "gaikyo", "gaikyo_name"])


def countries(raw):
    d = {}
    for r in _rows(Path(raw) / "a1.html"):
        for i, x in enumerate(r):
            if re.fullmatch(r"\d{3}", x) and i + 1 < len(r):
                d[x] = r[i + 1]
    return pd.Series(d, name="country_name").rename_axis("Country").reset_index()


def customs(raw):
    """税関符号表。統計表の3桁の税関コードは4桁の符号の上3桁（出張所などを含むまとまり）。名前は上3桁が同じ最初の符号のもの"""
    d = {}
    for r in _rows(Path(raw) / "a2.html"):
        if len(r) >= 2 and re.fullmatch(r"\d{4}", r[0]):
            d[r[0]] = r[1].strip()
    d3 = {}
    for k in sorted(d):
        d3.setdefault(k[:3], d[k])
    return pd.Series(d3, name="custom_name").rename_axis("Custom").reset_index()


def hinbetu(path):
    """統計品別表（9桁×世界）：HS, unit1, unit2, q1, q2, value（千円）"""
    d = pd.read_csv(path, dtype=str); d.columns = [c.strip() for c in d.columns]
    d["HS"] = d["HS"].str.strip("' ")
    out = pd.DataFrame({"HS": d["HS"], "unit1": d["Unit1"].str.strip(), "unit2": d["Unit2"].str.strip(),
                        "q1": pd.to_numeric(d["Quantity1-Year"]), "q2": pd.to_numeric(d["Quantity2-Year"]),
                        "value": pd.to_numeric(d["Value-Year"])})
    return out


def long_table(paths, key):
    """概況品別国別表・概況品別税関一覧表：key（Country か Custom）, Commodity, value（千円）"""
    d = pd.concat([pd.read_csv(p, dtype=str) for p in paths], ignore_index=True)
    d.columns = [c.strip() for c in d.columns]
    return pd.DataFrame({key: d[key].str.strip(), "Commodity": d["Commodity"].str.strip("' ").str.strip(),
                         "value": pd.to_numeric(d["Value-Year"])})
