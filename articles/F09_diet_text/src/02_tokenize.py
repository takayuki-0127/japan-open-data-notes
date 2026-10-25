"""02 抜粋を形態素解析し、名詞（一般・固有・サ変）だけを残す。

- fugashi + unidic-lite
- 発言者名の行頭（○委員長 など）、人名（固有名詞・人名）、数字、1文字の語、定型語（ストップワード）を除く
- 出力：data/tokens.jsonl.gz（1発言1行）
"""
import gzip, json, re, unicodedata
from pathlib import Path
import fugashi

ROOT = Path(__file__).resolve().parents[1]
STOP = set("""こと もの ところ これ それ ため よう 方 中 今 今回 問題 状況 関係 必要 大臣 総理 委員 委員長 議員 政府 我が国 日本 国 皆様 先生 質問 答弁 御 議論 認識 お話 意味 部分 前 後 点 形 話 方向 考え 場合 一方 是非 私 私ども 我々 皆さん 当然 本当 大変 非常 全体 具体 一つ 二つ 三つ 年 月 日 年度 時 間 等 化 的 さん 氏 者 側 上 下 内 外 時代 時期 自体 他 以上 以下 程度 現在 現状 結果 対応 検討 実施 推進 取組 取り組み 措置 施策 政策 社会 経済 拡大 引上げ 引き上げ わけ ふう 平成 令和 昭和 辺 感じ つもり はず 中身 次第 委員会 国会 会議 法案 本日 先ほど 白川 黒田 甘利 植田 岩田 福井 速水 三重野 澄田 雨宮 中曽 若田部 麻生 安倍 岸田 石破 菅 竹中 与謝野 茂木""".split())


def clean(s):
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"○\S+?　", " ", s)          # 発言者名
    s = re.sub(r"[0-9０-９,，.．%％]+", " ", s)
    return s


def main():
    tagger = fugashi.Tagger()
    src = gzip.open(ROOT / "data" / "raw" / "contexts_sample.jsonl.gz", "rt", encoding="utf-8")
    out = gzip.open(ROOT / "data" / "tokens.jsonl.gz", "wt", encoding="utf-8")
    n = 0
    for line in src:
        r = json.loads(line)
        toks = []
        for w in tagger(clean(r["ctx"])):
            f = w.feature
            if f.pos1 != "名詞" or f.pos2 in ("数詞", "代名詞") or f.pos2 == "助動詞語幹" or f.pos3 == "人名":
                continue
            lemma = f.lemma if f.lemma and f.pos2 != "固有名詞" else w.surface
            lemma = w.surface if lemma is None else lemma
            if len(w.surface) < 2 or w.surface in STOP or lemma in STOP:
                continue
            toks.append(w.surface)
        out.write(json.dumps({k: r[k] for k in ("y", "k", "id", "meeting", "house")} | {"toks": toks},
                             ensure_ascii=False) + "\n")
        n += 1
    out.close()
    print("speeches", n)


if __name__ == "__main__":
    main()
