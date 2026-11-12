"""385 図には、軸の名前・単位・出典がそろっているか（④ 振り返り R115）— 図を作るコードを読む

使い方: python a385_extract.py <japan-open-data-notes のルート>
  articles/*/ の .py から「図を保存する所」を探し、その手前のコード（前の保存の次の行から）を図1枚分とみなして、
  軸の名前・題名・凡例・単位・出典を書き込む命令があるかを 0/1 で data/figure_code.csv に出す。コードの中身は出さない。
  図を保存する所 ＝ .savefig( の行と、savefig を中に持つ自作の関数（save など）を呼ぶ行。
  画像そのものは見ていない。関数の中で描いて何回も呼ぶ図は1枚に数える。
"""
import csv, glob, os, re, sys
from common import group_of
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..", "data")
SRC = r"出典|資料[:：]|\b(?:SOURCE|SRC|source|src|NOTE_SRC)\b|データ[:：]|架空の|合成データ"
TXT = r"\.text\(|figtext\(|\.annotate\(|\.set_xlabel\(|\.xlabel\("
EL = {"xlabel": r"set_xlabel\(|\.xlabel\(|xlabel\s*=", "ylabel": r"set_ylabel\(|\.ylabel\(|ylabel\s*=", "title": r"set_title\(|plt\.title\(|suptitle\(|\btitle\s*=",
      "legend": r"\.legend\(", "source": SRC, "no_axes": r"axis\(\s*[\"']off|\.table\(|set_axis_off\(", "barh": r"\.barh\(", "grid_image": r"imshow\(|pcolormesh\(|heatmap\(",
      "datelike_x": r"to_datetime|date_range|DateFormatter|\.year\b|年度?[\"']", "note_text": r"fig\.text\(|figtext\(|\.annotate\(|ax\w*\.text\("}
LAB = r"(?:set_[xy]label|\.[xy]label)\(\s*f?[\"']([^\"']*)[\"']"
def helpers(text):
    """savefig を中に持つ関数（名前 → 出典を書き込むか）と、出典を書き込むだけの関数の名前"""
    out, src = {}, set()
    for m in re.finditer(r"^def (\w+)\((.*?)\):\n((?:[ \t]+.*\n|\n)+)", text, re.M):
        writes = int(bool(re.search(TXT, m.group(3)) and re.search(SRC, m.group(2) + m.group(3))))
        if ".savefig(" in m.group(3): out[m.group(1)] = writes
        elif writes: src.add(m.group(1))
    return out, src
def has_source(seg, srccall, savecall=None):
    """図1枚分のコードに、出典を書き込む行（文字を書く命令と出典の文が同じ行）か、出典を書く自作の関数の呼び出しか、保存の関数に出典の文を渡す行があるか。
    出典 ＝「出典」「資料：」「データ：」と、架空・合成のデータであることの注記"""
    for ln in seg.split("\n"):
        if ln.lstrip().startswith(("def ", "#", "from ", "import ")): continue
        if re.search(TXT, ln) and re.search(SRC, ln): return 1
        if srccall and srccall.search(ln): return 1
        if savecall and savecall.search(ln) and re.search(SRC, ln): return 1  # save(fig, 名前, "出典：…") の形
    return 0
def main(repo):
    rows = []
    for d in sorted(glob.glob(os.path.join(repo, "articles", "*"))):
        folder = os.path.basename(d); g = group_of(folder)
        if g is None or not os.path.isdir(d): continue
        texts = {p: open(p, encoding="utf-8").read() for p in sorted(glob.glob(os.path.join(d, "**", "*.py"), recursive=True))}
        H, S = {}, set()
        for t in texts.values():
            h, sc = helpers(t); H.update(h); S |= sc
        srccall = re.compile(r"(?<![\w.])(?:\w+\.)?(" + "|".join(map(re.escape, S)) + r")\(") if S else None
        call = re.compile(r"(?<![\w.])(?:\w+\.)?(" + "|".join(map(re.escape, H)) + r")\(") if H else None
        for p, t in texts.items():
            lines = t.split("\n"); seg = []; indef = None; k = 0
            for ln in lines:
                m = re.match(r"def (\w+)\(", ln)
                if m: indef = m.group(1) if m.group(1) in H else None
                elif ln and not ln[0].isspace(): indef = None
                seg.append(ln)
                if indef: continue  # 自作の保存関数の中は、呼ぶ側で数える
                hit = None
                if ".savefig(" in ln: hit = ("savefig", 0)
                elif call and call.search(ln) and not ln.lstrip().startswith("def "): hit = ("helper", H[call.search(ln).group(1)])
                if not hit: continue
                s = "\n".join(seg); seg = []; k += 1
                labs = re.findall(LAB, s)
                pm = re.search(r"[\"']([^\"']*?([\w\-]+\.png))[\"']", ln)
                r = dict(folder=folder, group=g, file=os.path.relpath(p, d), k=k, via=hit[0], png=pm.group(2) if pm else "", lines=s.count("\n") + 1)
                for name, pat in EL.items(): r[name] = int(bool(re.search(pat, s)))
                r["source"] = int(has_source(s, srccall, call) or hit[1])
                r["n_labels"] = len(labs); r["unit_in_label"] = int(any(re.search(r"[（(\[][^）)\]]{1,14}[）)\]]|[%％]", l) for l in labs))
                rows.append(r)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "figure_code.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(len(rows), "枚分のコード", len({r["folder"] for r in rows}), "記事")
if __name__ == "__main__":
    main(sys.argv[1])
