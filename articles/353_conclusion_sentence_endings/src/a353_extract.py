"""353 結論の言い切り方は、どう変わったか（④ 振り返り R108）— 原稿の結論の文の、文末を数える

使い方: python a353_extract.py <記事の md があるフォルダ>
  結論の文＝①題名の答えの部分（最初の「？」か「。」より後ろ。なければ題名全体）
            ②最初の見出しより前の文（書き出し）
            ③見出しに「分かること」「まとめ」「結論」がある節の文
  文ごとに、いちばん最後の言い方を分ける（終わりのかっこ書きと句点は外す）。出すのは記事ごとの数だけ（data/endings.csv）。
  分け方：unknown＝見えなかった・分からない・言えない／null＝変わらなかった・ほぼ同じ・横ばい／
          hedge＝かもしれない・考えられる・可能性がある・（推測）／question＝「か」「？」で終わる問いの文／
          past＝「〜た」で終わる言い切り／plain＝それ以外（「〜です」「〜ている」、体言止めなど）
  title_any_ は、題名の答えの部分のどこかにその言い方があるか（文末に限らない）
"""
import re, sys, os, csv
from mdlib import load, clean, sentences, folder_like
from common import group_of
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..")
NEG = r"(なかった|ませんでした|ない|ません)"
# 文のいちばん最後の言い方だけを見る（終わりのかっこ書き・かぎかっこ・句点は外す）
UNK = r"(?<!しか)(見え|分から|わから|言え|いえ|確かめられ|区別でき|見分けられ|説明でき|判断でき|読み取れ|決められ)" + NEG + r"$|はっきりし(なかった|ない|ません|ませんでした)$|とは限(らない|りません|らなかった)$|(分から|わから)ないまま(です|でした|だった)?$"
NUL = r"(変わら|変わり|動か|動き)" + NEG + r"$|(ほぼ|ほとんど)(同じ|横ばい|0|ゼロ|変わらず)(だった|でした|です|になった|になりました)?$|横ばい(だった|でした|です)?$|(差|関係|効果|傾向)は(見られ|出|あり)?" + NEG + r"$"
HED = r"かもしれ(ない|ません)$|と考えられ(る|ます)$|と考え(る|ます)$|と思われ(る|ます)$|可能性があ(る|ります)$|可能性が高い(です)?$|だろう$|(と言え|と言って|になり|があり)そうです$|とみられ(る|ます)$|と見られ(る|ます)$|ようです$|ようだ$|推測(です)?$"
UNK_ANY = UNK.replace("$", ""); NUL_ANY = NUL.replace("$", ""); HED_ANY = HED.replace("$", "")
def core(s):
    s = re.sub(r"[。！？?\s]+$", "", s); hedge_mark = bool(re.search(r"[（(]推測[）)]$", s))
    for _ in range(3):
        s2 = re.sub(r"[（(][^（()）]*[）)]$", "", s); s2 = re.sub(r"[」』]$", "", s2).rstrip("。 ")
        if s2 == s: break
        s = s2
    return s, hedge_mark
def cls(s):
    if re.search(r"(か|？|\?)[。！？?\s]*$", s): return "question"
    t, mark = core(s)
    if re.search(UNK, t): return "unknown"
    if re.search(NUL, t): return "null"
    if mark or re.search(HED, t): return "hedge"
    if re.search(r"(た|だった|でした|ました)$", t): return "past"
    return "plain"
def conclusion_sentences(title, lines):
    body = clean(lines, keep_heads=True)
    lead, sec, on, seen = [], [], False, False
    for l in body:
        if l.startswith("#"):
            seen = True; on = bool(re.search(r"分かること|まとめ|結論", l)); continue
        (sec if on else lead if not seen else []).append(l)
    m = re.search(r"[？?。]", title)
    ans = title[m.end():].strip() if m and len(title[m.end():].strip()) >= 8 else title
    return [x for x in re.split(r"(?<=[。])", ans) if len(x.strip()) >= 5], sentences(lead), sentences(sec)
def main(D):
    rows = []
    for i, title, lines in load(D):
        g = group_of(folder_like(i))
        if g is None:
            continue
        ts, ls, ss = conclusion_sentences(title, lines)
        allb = sentences(clean(lines))
        r = dict(id=i, group=g, title_has_q=int(bool(re.search(r"[？?]", title))), n_title=len(ts), n_lead=len(ls), n_sec=len(ss), n_body=len(allb))
        for part, S in (("title", ts), ("lead", ls), ("sec", ss), ("body", allb)):
            c = {"unknown": 0, "null": 0, "hedge": 0, "past": 0, "plain": 0, "question": 0}
            for s in S: c[cls(s)] += 1
            for k, v in c.items(): r[f"{part}_{k}"] = v
        m = re.search(r"[？?]", title); ans = title[m.end():] if m else title
        r["title_any_unknown"] = int(bool(re.search(UNK_ANY, ans))); r["title_any_null"] = int(bool(re.search(NUL_ANY, ans))); r["title_any_hedge"] = int(bool(re.search(HED_ANY, ans)))
        r["tadashi"] = sum(1 for s in ts + ls + ss if re.match(r"ただし|ただ、|一方で|もっとも", s) or re.search(r"、ただし|。ただ", s))
        rows.append(r)
    os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
    with open(os.path.join(OUT, "data", "endings.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print(len(rows), "本")
if __name__ == "__main__":
    main(sys.argv[1])
