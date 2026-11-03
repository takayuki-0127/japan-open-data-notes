"""02 行ごとに「作り手」「経路」「再利用か」を判定し、記事×作り手の表にまとめる"""
import re, gzip
import pandas as pd
from common import DATA, OWNERS, REUSE, ROUTE_ORDER, routes_of

ART_REUSE = r"新しいデータは取らず|これまでの記事の ?(data|データ)|README（`articles/|記事の README を|新しく(は)?(取得|取っ)|新しい(データの)?取得はな|新規の取得はな|新しいデータは(取って|ありません)|新しく取ったデータはありません"
BOILER = r"^\W{0,4}出典|を加工して作成|をもとに作成|をもとに作成者が加工"
EVID = r"取得|ダウンロード|https?://|data/raw|元の(?:表|ファイル|Excel|CSV)|元データ"
ESTAT = r"e-Stat|e-stat|statInfId|file-download|stat-search/files|ssdsview|政府統計の総合窓口"

OTHER_ART = r"(?<![A-Za-z0-9_])F\d{1,3}(?![0-9])|記事 ?\d{3}|\b\d{3}_[a-z]"

def classify_line(t, self_art=""):
    owners = [o for o, rx in OWNERS if re.search(rx, t)]
    routes_all = routes_of(t)
    refs = {m for m in re.findall(r"(?<![A-Za-z0-9_])F\d{1,3}(?![0-9])", t)} - {self_art.split("_")[0]}
    reuse = bool(re.search(REUSE, t)) or bool(refs) or bool(re.search(r"記事 ?\d{3}", t))
    return owners, (routes_all[0] if routes_all else None), routes_all, reuse, bool(re.search(ESTAT, t))

def main():
    L = pd.read_csv(DATA / "source_lines.csv.gz")
    art_reuse = L.groupby("article")["text"].apply(lambda s: any(re.search(ART_REUSE, x) for x in s.astype(str)))
    rows = []
    for r in L.itertuples():
        owners, route, routes_all, reuse, estat = classify_line(str(r.text), r.article)
        for o in owners:
            rows.append(dict(article=r.article, owner=o, file=r.file, route=route or "", routes_all="|".join(routes_all),
                             reuse=reuse, estat=estat, text=str(r.text)[:300]))
    LL = pd.DataFrame(rows)
    LL.to_csv(DATA / "owner_lines.csv.gz", index=False)
    order = ROUTE_ORDER
    out = []
    for (a, o), g in LL.groupby(["article", "owner"]):
        allr = set(sum([x.split("|") for x in g["routes_all"].fillna("") if x], []))
        rs = sorted(allr - {"_page"}, key=order.index)
        page_only = (not rs) and ("_page" in allr)
        # 出典の定型文（「〜を加工して作成」）はどの記事にもあるので、新規かどうかの判定には使わない。
        # 他の記事を指していない行のうち、取得の手がかり（経路・URL・「取得」など）がある行があれば「新規」
        boiler = g["text"].str.contains(BOILER, regex=True)
        evid = g["text"].str.contains(EVID, regex=True) | (g["routes_all"].fillna("") != "")
        cand = g[~boiler & ~g["reuse"] & evid]
        if art_reuse.get(a, False):
            new = False
        elif len(cand):
            new = True
        else:
            new = not g["reuse"].any()   # 他の記事への言及がなく、手がかりもない → 新規（経路は記録なし）
        out.append(dict(article=a, owner=o, n_lines=len(g), new=new,
                        route=rs[0] if rs else ("ページURLのみ" if page_only else "記録なし"),        # いちばん機械向きの経路
                        route_hard=rs[-1] if rs else ("ページURLのみ" if page_only else "記録なし"),  # いちばん手間のかかる経路
                        **{"any_" + k: (k in allr) for k in order if k != "_page"},
                        via_estat=bool(g["estat"].any()),
                        F=a.startswith("F"), num=int(re.sub(r"\D.*", "", a.lstrip("F")) or -1)))
    D = pd.DataFrame(out)
    D.to_csv(DATA / "article_owner.csv", index=False)
    print(len(D), "組（記事×作り手）", D["article"].nunique(), "記事", "新規", int(D["new"].sum()))
    print("記事として再利用だけ:", int(art_reuse.sum()))

if __name__ == "__main__":
    main()
