"""01 国会会議録検索システム API から、語ごと・年ごとの発言数と、発言の抜粋を取る。

- API: https://kokkai.ndl.go.jp/api/speech （国立国会図書館。発言単位、JSON）
- アクセス間隔は 1.2 秒以上あける。取得結果は data/raw/cache/ に保存し、2回目以降は再取得しない
- 記事では、同じ手順をブラウザのページ内（fetch）で実行して取得した（2026-10-25 取得）。
  結果は data/counts_by_year.csv と data/raw/contexts_sample.jsonl.gz
"""
import gzip, hashlib, json, os, random, time
from pathlib import Path
import requests

BASE = "https://kokkai.ndl.go.jp/api/speech"
ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data" / "raw" / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

KEYWORDS = ["", "賃上げ", "物価", "少子化", "デフレ", "インフレ", "円安", "物価高", "好循環",
            "非正規", "生産性", "最低賃金", "働き方改革", "賃金引上げ", "賃金の引上げ", "ベースアップ"]
MAIN4 = ["", "賃上げ", "物価", "少子化", "デフレ"]
SCOPES = ["本会議", "予算委員会"]          # nameOfMeeting（部分一致）
YEARS = range(1985, 2027)
LAST_DAY_2026 = "2026-10-24"


def get(params):
    key = hashlib.md5(json.dumps(params, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    f = CACHE / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    for _ in range(3):
        try:
            r = requests.get(BASE, params={**params, "recordPacking": "json"}, timeout=60)
            r.raise_for_status()
            j = r.json()
            f.write_text(json.dumps(j, ensure_ascii=False))
            time.sleep(1.2)
            return j
        except Exception:
            time.sleep(5)
    raise RuntimeError(params)


def span(y):
    return f"{y}-01-01", (LAST_DAY_2026 if y == 2026 else f"{y}-12-31")


def counts():
    rows = []
    for y in YEARS:
        fr, un = span(y)
        jobs = [(k, "") for k in KEYWORDS] + [(k, s) for s in SCOPES for k in MAIN4]
        for k, s in jobs:
            p = {"from": fr, "until": un, "maximumRecords": 1}
            if k:
                p["any"] = k
            if s:
                p["nameOfMeeting"] = s
            rows.append([y, k, s, int(get(p)["numberOfRecords"])])
    with open(ROOT / "data" / "counts_by_year.csv", "w", encoding="utf-8") as f:
        f.write("year,keyword,scope,n\n")
        for y, k, s, n in rows:
            f.write(f"{y},{k},{s},{n}\n")
    return rows


def sample(rows, k_list=("賃上げ", "物価"), per=100, window=150, seed=12345):
    """年×語ごとに、ランダムな位置から連続100件の発言を取り、語の前後150字を抜き出す"""
    rnd = random.Random(seed)
    n_of = {(y, k): n for y, k, s, n in rows if s == ""}
    out = gzip.open(ROOT / "data" / "raw" / "contexts_sample.jsonl.gz", "wt", encoding="utf-8")
    for y in YEARS:
        for k in k_list:
            n = n_of.get((y, k), 0)
            if not n:
                continue
            st = 1 + rnd.randrange(n - per + 1) if n > per else 1
            fr, un = span(y)
            j = get({"from": fr, "until": un, "any": k, "maximumRecords": per, "startRecord": st})
            for r in j.get("speechRecord", []):
                sp = r["speech"]
                ctx, i, c = [], sp.find(k), 0
                while i >= 0 and c < 5:
                    ctx.append(sp[max(0, i - window): i + window]); i = sp.find(k, i + window); c += 1
                out.write(json.dumps({"y": y, "k": k, "id": r["speechID"], "date": r["date"],
                                      "house": r["nameOfHouse"], "meeting": r["nameOfMeeting"],
                                      "len": len(sp), "ctx": " … ".join(ctx)}, ensure_ascii=False) + "\n")
    out.close()


if __name__ == "__main__":
    sample(counts())
