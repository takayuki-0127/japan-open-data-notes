"""406 SQL の見直しの観点10個を、自分の記事の SQL に当てると何件引っかかるか（その1：機械で探す）
使い方： python a406_scan.py <記事フォルダの親（articles/）>   → data/sql_files.csv, data/hits.csv を作る
引数なしなら、data/ にある結果をそのまま使う（a406_count.py が読む）。"""
import re, sys, csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; DATA = ROOT / "data"; DATA.mkdir(exist_ok=True)

CHECKS = [  # (番号, 名前, 何が心配か)
    ("C01", "SELECT *", "列が増えたり並びが変わったりすると、後ろの処理が黙って変わる"),
    ("C02", "TOP・LIMIT に ORDER BY がない", "どの行が返るかが決まらない"),
    ("C03", "= NULL・<> NULL", "いつも「不明」になり、1行も当てはまらない"),
    ("C04", "NOT IN (SELECT …)", "サブクエリに NULL が1件あると、0行になる"),
    ("C05", "日付に BETWEEN", "時刻つきの列だと、最終日の0時より後が落ちる"),
    ("C06", "割り算の分母を守っていない", "分母が0や NULL のとき、エラーか NULL になる"),
    ("C07", "ROW_NUMBER の並びが1列だけ", "同じ値があると、番号が実行のたびに変わりうる"),
    ("C08", "カンマでつなぐ結合", "条件を書き忘れると、全部の組み合わせになる"),
    ("C09", "SELECT DISTINCT", "結合で増えた行を、理由を確かめずに消していることがある"),
    ("C10", "UNION（ALL なし）", "同じ内容の行が黙って1行にまとめられる"),
]


def strip_comments(s):
    """コメントを空白に置き換える（行番号は保つ）。文字列の中の -- は消さない程度に簡単に扱う"""
    s = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), s, flags=re.S)
    out = []
    for line in s.split("\n"):
        q = False; cut = len(line)
        for i, ch in enumerate(line):
            if ch == "'": q = not q
            if not q and line[i:i + 2] == "--": cut = i; break
        out.append(line[:cut])
    return "\n".join(out)


def statements(s):
    """; で文に分ける。（開始行, 文）を返す"""
    res = []; start = 0; line = 1
    for m in re.finditer(r";", s):
        st = s[start:m.start()]
        if st.strip(): res.append((line + (len(st) - len(st.lstrip("\n "))) and line + st[: len(st) - len(st.lstrip())].count("\n"), st))
        line += s[start:m.end()].count("\n"); start = m.end()
    st = s[start:]
    if st.strip(): res.append((line + st[: len(st) - len(st.lstrip())].count("\n"), st))
    return res


def lineno(st_line, st, pos):
    lead = len(st) - len(st.lstrip())
    return st_line + st[lead:pos].count("\n") if pos >= lead else st_line


def scan_statement(st):
    """1つの文から、観点ごとの該当箇所（文の中の位置）を返す"""
    hits = []; U = st.upper()
    for m in re.finditer(r"SELECT\s+(DISTINCT\s+)?(TOP\s*\(?\s*\d+\s*\)?\s+)?(\w+\.)?\*", U): hits.append(("C01", m.start()))
    for m in re.finditer(r"\bTOP\s*\(?\s*\d+|\bLIMIT\s+\d+|\bFETCH\s+(FIRST|NEXT)\b", U):
        if "WITH TIES" in U[m.start(): m.start() + 40]: continue
        # 同じ SELECT の中（その位置より後ろ、かっこの深さが戻るまで）に ORDER BY があるか
        depth = 0; tail = ""
        if U[m.start():m.start() + 3] == "TOP":
            for ch in U[m.start():]:
                if ch == "(": depth += 1
                if ch == ")":
                    depth -= 1
                    if depth < 0: break
                tail += ch
            ok = bool(re.search(r"\bORDER\s+BY\b", re.sub(r"OVER\s*\([^()]*\)", "", tail)))
        else:                                        # LIMIT・FETCH は、手前に ORDER BY があるか
            head = U[: m.start()]; i = len(head); depth = 0; seg = ""
            for ch in reversed(head):
                if ch == ")": depth += 1
                if ch == "(":
                    depth -= 1
                    if depth < 0: break
                seg = ch + seg
            ok = bool(re.search(r"\bORDER\s+BY\b", re.sub(r"OVER\s*\([^()]*\)", "", seg)))
        if not ok: hits.append(("C02", m.start()))
    for m in re.finditer(r"(=|<>|!=)\s*NULL\b", U):
        pre = U[: m.start()]
        if re.search(r"\bSET\s+[^;]*$", pre) and not re.search(r"\bWHERE\b[^;]*$", pre[pre.rfind("SET"):]): continue   # UPDATE … SET x = NULL は代入
        hits.append(("C03", m.start()))
    for m in re.finditer(r"\bNOT\s+IN\s*\(\s*SELECT\b", U): hits.append(("C04", m.start()))
    for m in re.finditer(r"\bBETWEEN\b", U):
        ctx = st[max(0, m.start() - 60): m.start() + 90]
        if re.search(r"'\d{4}-\d{2}-\d{2}|日|DATE|月初|月末|期間|開始|終了|[_\s]D\b|_AT\b|YMD", ctx, flags=re.I) and not re.search(r"ROWS\s+$|RANGE\s+$", U[max(0, m.start() - 8): m.start()]):
            hits.append(("C05", m.start()))
    nostr = re.sub(r"'[^']*'", lambda q: "'" + " " * (len(q.group(0)) - 2) + "'", st)      # 文字列の中の / は数えない
    for m in re.finditer(r"/\s*(?=[A-Za-z_぀-鿿(\"\[])", nostr):
        after = U[m.end(): m.end() + 40]
        if re.match(r"NULLIF\b", after) or re.match(r"\(?\s*\d", after): continue
        if st[m.start() - 1: m.start()] == "*" or st[m.end(): m.end() + 1] == "*": continue
        k = "件数（COUNT）" if after.startswith("COUNT") else "前の期の値（LAG）" if after.startswith("LAG") else \
            "集計した値（SUM など）" if re.match(r"(SUM|MAX|MIN|AVG)\b", after) else "式（かっこ）" if after.startswith("(") else "列・変数"
        g = bool(re.search(r"NULLIF|(>|<>|!=)\s*0\b|=\s*0\s+THEN|IS\s+NOT\s+NULL", U))
        hits.append(("C06", m.start(), k + "｜" + ("守りあり" if g else "守りなし")))
    for m in re.finditer(r"ROW_NUMBER\s*\(\s*\)\s*OVER\s*\(", U):
        depth = 1; i = m.end(); body = ""
        while i < len(U) and depth:
            if U[i] == "(": depth += 1
            if U[i] == ")": depth -= 1
            if depth: body += U[i]
            i += 1
        ob = re.search(r"ORDER\s+BY\s+(.*)$", body, flags=re.S)
        if ob:
            keys = re.sub(r"\([^()]*\)", "", ob.group(1)); keys = re.split(r"\bROWS\b|\bRANGE\b", keys)[0]
            if keys.count(",") == 0: hits.append(("C07", m.start()))
    for m in re.finditer(r"\bFROM\s+[\w.\[\]\"#぀-鿿]+(\s+(AS\s+)?\w+)?\s*,\s*[\w.\[\]\"#぀-鿿]+", U):
        if "UNNEST" in U[m.start(): m.end() + 20] or "VALUES" in U[m.start(): m.end() + 20]: continue
        hits.append(("C08", m.start()))
    for m in re.finditer(r"\bSELECT\s+DISTINCT\b", U): hits.append(("C09", m.start()))
    for m in re.finditer(r"\bUNION\b(?!\s+ALL\b)", U): hits.append(("C10", m.start()))
    return hits


if __name__ == "__main__" and len(sys.argv) > 1:
    base = Path(sys.argv[1]); files = []; hits = []
    for f in sorted(base.glob("*/**/*.sql")):
        art = f.relative_to(base).parts[0]
        if art.startswith("406_") or "/target/" in str(f): continue      # dbt が作る写し（target/）は数えない
        raw = f.read_text(encoding="utf-8", errors="replace"); s = strip_comments(raw); sts = statements(s)
        rawl = raw.split("\n")
        files.append({"記事": art, "ファイル": str(f.relative_to(base / art)), "行": len(rawl), "文": len(sts), "バイト": len(raw.encode())})
        for st_line, st in sts:
            for cid, pos, *extra in scan_statement(st):
                ln = lineno(st_line, st, pos)
                prev = next((rawl[k].strip() for k in range(ln - 2, max(ln - 6, -1), -1) if rawl[k].strip().startswith("--")), "")
                text = rawl[ln - 1].strip()[:160] if 0 < ln <= len(rawl) else ""
                hits.append({"記事": art, "ファイル": str(f.relative_to(base / art)), "行番号": ln, "観点": cid, "該当行": text, "補足": extra[0] if extra else "", "直前のコメント": prev[:120]})
    with open(DATA / "sql_files.csv", "w", newline="", encoding="utf-8") as fo:
        w = csv.DictWriter(fo, fieldnames=list(files[0])); w.writeheader(); w.writerows(files)
    with open(DATA / "hits.csv", "w", newline="", encoding="utf-8") as fo:
        w = csv.DictWriter(fo, fieldnames=list(hits[0])); w.writeheader(); w.writerows(hits)
    print("files", len(files), "articles", len({f["記事"] for f in files}), "statements", sum(f["文"] for f in files), "lines", sum(f["行"] for f in files), "hits", len(hits))
    from collections import Counter
    print(sorted(Counter(h["観点"] for h in hits).items()))
