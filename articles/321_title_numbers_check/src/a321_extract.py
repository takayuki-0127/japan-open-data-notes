"""321 題名に書いた数字は、結果のファイルと合っているか（④ 振り返り R101）— その1：突き合わせ

使い方: python a321_extract.py <リポジトリのルート>
  data/titles.csv（記事の番号と note の題名。手元の原稿 md の1行目）を読み、題名の数字を1つずつ拾って、
  その記事のフォルダの README.md と results/ の json・csv・txt に同じ数字があるかを確かめる。
  結果は data/tokens.csv（数字1つが1行）と data/articles_checked.csv（突き合わせた記事）。集計と図は a321.py
"""
import os, re, sys, glob, math, csv
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..")
REPO = sys.argv[1]
T = pd.read_csv(os.path.join(OUT, "data", "titles.csv"), dtype={"id": str})
norm = lambda s: s if s[0] in "FT" else str(int(s))
folders = {}
for f in sorted(os.listdir(os.path.join(REPO, "articles"))):
    m = re.match(r"((?:F|T)?\d+)_", f)
    if m: folders[norm(m.group(1))] = f

NUM = re.compile(r"(?<![0-9A-Za-z.\-])(\d[\d,]*(?:\.\d+)?)")
PERIOD = re.compile(r"^(年間|年分|年で|年ぶり|年に|年後|年前|年|か月|カ月|ヶ月|週間|週|日間|日分|日|時間|分|四半期|シーズン|世代|回分|回|月)")
COUNT = re.compile(r"^(都道府県|市区町村|市町村|都府県|道県|都市|県|区|品目|業種|産業|業態|地点|か所|カ所|か国|社|本|個|件の記事|つ|種類|通り|項目|組|分類|手法|指標|タイプ|グループ|店|駅|港|点|位|番目|次|表|問|枚|段|層|章|列|行)")
RATE = re.compile(r"^(%|％|ポイント|pt|割|倍|分の)")
UNIT1 = re.compile(r"^(人|つ|日|時間|戸|本|件|kg|L|畳|店|社|回|か月|年|世帯|施設|㎡|枚|度|歳|a|km|m|g|円|ドル|月|期|か所|頭|台|kWh|位|番|等|級|次)")

def tokens(title):
    out = []
    for m in NUM.finditer(title):
        s = m.group(1).rstrip(","); after = title[m.end(1):m.end(1) + 6]; before = title[max(0, m.start(1) - 2):m.start(1)]
        raw = s.replace(",", "")
        if not re.match(r"^\d+(\.\d+)?$", raw): continue
        v = float(raw); dec = len(raw.split(".")[1]) if "." in raw else 0
        if dec == 0 and "," not in s and 1850 <= v <= 2100 and len(raw) == 4: continue          # 年
        if re.search(r"(18|19|20)\d\d[〜～\-–]$", title[max(0, m.start(1) - 5):m.start(1)]) and after.startswith("年"): continue   # 「2023〜25年」の 25
        if before.endswith("第") or before.endswith("令和") or before.endswith("平成") or before.endswith("昭和"): continue
        if dec == 0 and v == 1 and UNIT1.match(after) and not RATE.match(after): continue     # 「1人あたり」「1日」などの単位
        rg = re.match(r"^(?:〜|～|・|→|から|、)\s*[+＋\-−]?\d[\d,]*(?:\.\d+)?", after)
        if rg and not (RATE.match(after) or PERIOD.match(after) or COUNT.match(after)):
            after = title[m.end(1) + rg.end():m.end(1) + rg.end() + 6]      # 単位は後ろの数字のもの
        if RATE.match(after): kind = "率"
        elif PERIOD.match(after): kind = "期間"
        elif COUNT.match(after): kind = "個数"
        else: kind = "量"
        scale = 1.0
        mm = re.match(r"^(万|億|兆|千)", after)
        if mm: scale = {"千": 1e3, "万": 1e4, "億": 1e8, "兆": 1e12}[mm.group(1)]
        sig = len(raw.replace(".", "").lstrip("0")) if v != 0 else 1
        out.append(dict(token=s, value=v, dec=dec, sig=sig, kind=kind, unit=after[:3], scale=scale, wari=after.startswith("割")))
    return out

FLOAT = re.compile(r"(?<![0-9A-Za-z_.])-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
def load(folder):
    base = os.path.join(REPO, "articles", folder)
    readme = open(os.path.join(base, "README.md"), encoding="utf-8", errors="replace").read()
    res = []
    for p in sorted(glob.glob(os.path.join(base, "results", "*"))):
        if p.rsplit(".", 1)[-1] in ("json", "csv", "txt") and os.path.getsize(p) < 3_000_000:
            res.append(open(p, encoding="utf-8", errors="replace").read())
    return readme, "\n".join(res)

def has_exact(text, s):
    raw = s.replace(",", "")
    pats = {re.escape(s), re.escape(raw)}
    if "," not in s and len(raw.split(".")[0]) > 3:      # 1234 → 1,234 も見る
        i = raw.split(".")[0]; c = f"{int(i):,}" + (("." + raw.split(".")[1]) if "." in raw else "")
        pats.add(re.escape(c))
    return any(re.search(r"(?<![0-9.,])" + p + r"(?![0-9]|\.[0-9]|,[0-9])", text) for p in pats)

def rnd(x, d):                      # 四捨五入（0.5 は切り上げ）
    q = 10 ** d; return math.floor(abs(x) * q + 0.5 + 1e-9) / q
def trunc(x, d):
    q = 10 ** d; return math.floor(abs(x) * q + 1e-9) / q

def unit_near(text, t):
    """同じ単位（%・倍・万…）のついた、もっと細かい数字を丸めると一致するか。割は % を10で割って比べる"""
    u = t["unit"][:1]
    if t["wari"]:
        cand = [float(z) / 10 for z in re.findall(r"(\d+(?:\.\d+)?)\s*[%％]", text)]
    elif u in "%％":
        cand = [float(z) for z in re.findall(r"(\d+(?:\.\d+)?)\s*[%％]", text)]
    elif u:
        cand = [float(z) for z in re.findall(r"(\d+(?:\.\d+)?)\s*" + re.escape(u), text.replace(",", ""))]
    else:
        cand = []
    v, d = t["value"], t["dec"]; hit = None
    for y in cand:
        if abs(rnd(y, d) - v) < 1e-9: return "round"
        if abs(trunc(y, d) - v) < 1e-9 or abs(math.ceil(y * 10 ** d - 1e-9) / 10 ** d - v) < 1e-9: hit = "trunc"
    return hit

def near(nums, t):
    """丸めると一致する値があるか。倍率は 割合→%（×100）、万・億・兆、千 を試す。戻り値: round / trunc / None"""
    v, d = t["value"], t["dec"]; hit = None
    ks = (1, 100, 1e-3, 1e-4, 1e-8, 1e-12, 1e-6) if (t["sig"] >= 3 or d >= 1) else (1 / t["scale"], 1e3 / t["scale"], 1e6 / t["scale"])
    for x in nums:
        for k in ks:
            y = x * k
            if abs(y) > v * 2 + 1 or abs(y) < v / 2 - 1: continue
            if abs(rnd(y, d) - v) < 1e-9: return "round"
            if abs(trunc(y, d) - v) < 1e-9: hit = "trunc"
    return hit

rows = []
for _, r in T.iterrows():
    k = norm(r.id)
    if k not in folders or not isinstance(r.title, str): continue
    readme, res = load(folders[k])
    # README に題名そのものが書いてある行（1行目・記事の一覧の表など）は、突き合わせの相手から外す
    phr = [p for p in re.split(r"[。？?、：:]", r.title) if len(p.strip()) >= 10]
    kept = [ln for ln in readme.split("\n") if not any(p.strip() in ln for p in phr)]
    title_lines = len(readme.split("\n")) - len(kept)
    readme = "\n".join(kept)
    nums = None
    for t in tokens(r.title):
        in_readme = has_exact(readme, t["token"]); in_res = has_exact(res, t["token"])
        nr = None
        if not (in_readme or in_res) and (t["sig"] >= 3 or t["dec"] >= 1 or t["scale"] > 1):
            if nums is None:
                nums = []
                for z in FLOAT.findall(res + "\n" + readme.replace(",", "")):
                    try:
                        f = float(z)
                        if math.isfinite(f): nums.append(f)
                    except ValueError: pass
                nums = list(set(nums))
            nr = near(nums, t)
        if not (in_readme or in_res) and nr is None:
            nr = unit_near(readme, t)
            if nr: nr = "u" + nr
        yd = False
        if not (in_readme or in_res) and nr is None and t["kind"] == "期間" and t["unit"].startswith("年"):
            for src_ in (r.title, readme):
                ys = sorted({int(y) for y in re.findall(r"(?<![0-9.,])((?:18|19|20)\d\d)(?![0-9])", src_)})
                if any((b - a) in (t["value"], t["value"] - 1) for a in ys for b in ys if b > a): yd = True; break
        if in_readme: cls = "A README に同じ数字"
        elif in_res: cls = "B 結果ファイルに同じ数字"
        elif nr == "round": cls = "C 四捨五入すると一致"
        elif nr == "trunc": cls = "D 切り捨て・切り上げると一致"
        elif nr == "uround": cls = "C 四捨五入すると一致"
        elif nr == "utrunc": cls = "D 切り捨て・切り上げると一致"
        elif yd: cls = "F 年の差から数えられる"
        else: cls = "E 見つからない"
        rows.append(dict(id=r.id, folder=folders[k], has_results=bool(res), **{x: t[x] for x in ("token", "kind", "unit", "dec", "sig", "wari")}, in_readme=in_readme, in_results=in_res, title_lines=title_lines, cls=cls))
pd.DataFrame(rows).to_csv(os.path.join(OUT, "data", "tokens.csv"), index=False, quoting=csv.QUOTE_NONNUMERIC)
T.assign(folder=T.id.map(lambda s_: folders.get(norm(s_))))[lambda d: d.folder.notna()][["id", "folder"]].to_csv(os.path.join(OUT, "data", "articles_checked.csv"), index=False)
print(len(rows), "tokens;", T.id.map(norm).isin(folders).sum(), "articles")
