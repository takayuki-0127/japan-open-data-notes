"""共通：README の読み込みと記事のグループ分け（240〜242 で同じもの）"""
import re, os, glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False

GROUPS = ["000–099", "100–226", "F01–F99", "F100–F199", "F200–F255", "F256–F295（精選）", "227–・T（1000本計画）"]


def group_of(folder):
    m = re.match(r"(F|T)?(\d+)_", folder)
    if not m:
        return None
    p, n = m.group(1), int(m.group(2))
    if p == "T":
        return GROUPS[6]
    if p == "F":
        if n <= 99:
            return GROUPS[2]
        if n <= 199:
            return GROUPS[3]
        if n <= 255:
            return GROUPS[4]
        return GROUPS[5]
    if n < 100:
        return GROUPS[0]
    if n <= 226:
        return GROUPS[1]
    return GROUPS[6]


def readmes(repo):
    """repo/articles/*/README.md を (folder, text) で返す"""
    out = []
    for p in sorted(glob.glob(os.path.join(repo, "articles", "*", "README.md"))):
        folder = os.path.basename(os.path.dirname(p))
        if group_of(folder) is None:
            continue
        out.append((folder, open(p, encoding="utf-8").read()))
    return out


def section(text, pattern):
    """見出しが pattern に合う節の本文（次の同じか上のレベルの見出しまで）を、すべてつないで返す"""
    lines = text.split("\n")
    res, cur, lvl = [], None, None
    for ln in lines:
        m = re.match(r"(#+)\s+(.*)", ln)
        if m:
            l = len(m.group(1))
            if cur is not None and l <= lvl:
                res.append("\n".join(cur)); cur = None
            if cur is None and re.search(pattern, m.group(2)):
                cur, lvl = [], l
                continue
        if cur is not None:
            cur.append(ln)
    if cur is not None:
        res.append("\n".join(cur))
    return res


def items(block):
    """箇条書き（- ・ 1. ）と表の行（ヘッダー・区切りを除く）を1項目ずつ返す"""
    out = []
    for ln in block.split("\n"):
        s = ln.strip()
        if re.match(r"^([-*・]|\d+[.)．])\s+", s):
            out.append(re.sub(r"^([-*・]|\d+[.)．])\s+", "", s))
        elif s.startswith("|") and not re.match(r"^\|[\s:|-]+\|?$", s):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cells and cells[0] in ("#", "指摘", "重さ", "項目"):
                continue
            out.append(" | ".join(cells))
    return [o for o in out if len(o) >= 6]
