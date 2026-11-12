"""手元の原稿（note 下書きのもとの md）を読むための共通部品。本文そのものは外に出さない"""
import re, os

def load(D):
    """(id, 題名, 本文の行) を返す。ファイル名が 番号_／F番号_／T番号_ で始まる md だけ"""
    out = []
    for fn in sorted(os.listdir(D)):
        m = re.match(r"(F\d+|T\d+|\d{1,3})_.*\.md$", fn)
        if not m:
            continue
        t = open(os.path.join(D, fn), encoding="utf-8", errors="replace").read()
        lines = t.split("\n"); title = ""
        for i, l in enumerate(lines):
            if l.startswith("# "):
                title = l[2:].strip(); lines = lines[i + 1:]; break
        out.append((m.group(1), title, lines))
    return out

def folder_like(i):
    return (i if i[0] in "FT" else "%03d" % int(i)) + "_x"

def clean(lines, keep_heads=False):
    """コード・表・図の行・URL・出典・下書きの注記を除いた行を返す。見出しは keep_heads のときだけ '## ' つきで残す"""
    body, incode = [], False
    for l in lines:
        if l.strip().startswith("```"):
            incode = not incode; continue
        if incode:
            continue
        s = l.strip()
        if not s:
            body.append(""); continue
        if s.startswith("#"):
            body.append(s if keep_heads else ""); continue
        if s.startswith("（note 下書き") or s.startswith("|") or s.startswith("![") or s.startswith("<") and not s.startswith("<b>"):
            body.append(""); continue
        s = re.sub(r"https?://\S+", "", s); s = re.sub(r"^[-・*]\s*", "", s); s = re.sub(r"[*`]|</?b>", "", s)
        if s.startswith("出典"):
            body.append(""); continue
        body.append(s)
    return body

def sentences(lines):
    out = []
    for s in lines:
        if not s or s.startswith("#"):
            continue
        for x in re.split(r"(?<=[。！？?])", s):
            x = x.strip()
            if len(x) >= 5:
                out.append(x)
    return out
