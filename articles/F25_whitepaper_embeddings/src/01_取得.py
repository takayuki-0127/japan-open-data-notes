"""01 取得：内閣府のサイトから、経済白書（1985〜2000年度）と経済財政白書（2001〜2025年度）の HTML 版の本文ページを集める。

- 入口は https://www5.cao.go.jp/keizai3/keizaiwp/index.html（各年度の HTML 版の目次）と、2024・2025年度の目次
- 各年度の目次から、同じフォルダの中のリンクを3階層までたどる。図表・付図・PDF・電子書籍のページはたどらない
- 1ページごとに0.15秒あける
- 出力 data/raw/pages.json（本文つき）。著作権に配慮して、本文は GitHub に置いていない
  （記事を作るときは同じ処理をブラウザの中の JavaScript で動かした：src/01_取得_browser.js）
"""
import json, re, time
from urllib.parse import urljoin, urldefrag
import requests
from bs4 import BeautifulSoup
from common import RAW

INDEX = "https://www5.cao.go.jp/keizai3/keizaiwp/index.html"
EXTRA = ["https://www5.cao.go.jp/j-j/wp/wp-je25/index.html", "https://www5.cao.go.jp/j-j/wp/wp-je24/index.html"]
FIG_H = re.compile(r"図表|^第?\s*[\d０-９\-－]+\s*[図表]|付図|付表|ウェブアクセシビリティ|電子書籍|PDF版")
FIG_U = re.compile(r"zuhyo|fig|pdf|syoseki|webaccess", re.I)
S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 (research; japan-open-data-notes F25)"


def get(u):
    r = S.get(u, timeout=30)
    b = r.content
    try:
        t = b.decode("utf-8")
        if t.count("�") > 5:
            raise UnicodeDecodeError("x", b, 0, 1, "x")
    except UnicodeDecodeError:
        t = b.decode("cp932", errors="replace")
    return r.status_code, t


def year_of(u):
    y = int(re.search(r"wp-je(\d\d)", u).group(1))
    return 2000 + y if y <= 30 else 1900 + y


def main():
    _, t = get(INDEX)
    soup = BeautifulSoup(t, "html.parser")
    tops = [urljoin(INDEX, a["href"]) for a in soup.select("a[href]") if re.search(r"wp-je\d\d", a["href"])]
    tops = EXTRA + [u for u in tops if year_of(u) >= 1985]
    pages, done = [], set()
    for top in tops:
        Y = year_of(top)
        if Y in done:
            continue
        done.add(Y)
        d = top.rsplit("/", 1)[0] + "/"
        seen, q, n = {top}, [(top, 0)], 0
        while q and n < 500:
            u, dep = q.pop(0); n += 1
            try:
                s, t = get(u)
            except Exception:
                continue
            time.sleep(0.15)
            if s != 200:
                continue
            sp = BeautifulSoup(t, "html.parser")
            h = sp.find(["h1", "h2"])
            h1 = h.get_text(strip=True) if h else ""
            is_fig = bool(FIG_H.search(h1) or FIG_U.search(u))
            if dep < 3 and not is_fig:
                for a in sp.select("a[href]"):
                    at = a.get_text(strip=True)
                    if re.search(r"図|表|CSV|PDF|ＰＤＦ", at) and not re.search(r"第\d+章|節", at):
                        continue
                    v = urldefrag(urljoin(u, a["href"]))[0].split("?")[0]
                    if v.startswith(d) and re.search(r"\.html?$", v) and v not in seen:
                        seen.add(v); q.append((v, dep + 1))
            if is_fig:
                continue
            for x in sp(["script", "style", "noscript"]):
                x.decompose()
            main_ = sp.select_one("#mainContents, #main, main, #contents, .main") or sp.body
            hs = [f"{e.name.upper()}:{' '.join(e.get_text().split())}" for e in main_.find_all(["h1", "h2", "h3", "h4", "h5"])][:120]
            body = re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t\r]+", " ", main_.get_text("\n"))).strip()
            if len(body) >= 200:
                pages.append(dict(year=Y, url=u, title=sp.title.get_text(strip=True) if sp.title else "", h=hs, text=body))
        print(Y, n)
    json.dump(pages, open(RAW / "pages.json", "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
