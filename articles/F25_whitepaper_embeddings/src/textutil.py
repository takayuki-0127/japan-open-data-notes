"""名詞の取り出し（fugashi＋unidic-lite）。テーマの名前づけと、比較用の TF-IDF に使う"""
import re
from functools import lru_cache

STOP = set("こと もの ため よう これ それ 場合 傾向 状況 動き 要因 影響 変化 推移 水準 程度 前年 年度 比較 一方 以下 以上 全体 部分 必要 可能 指摘 背景 関係 観点 結果 内容 方向 面 点 中 等 的 化 性 率 年 月 日 期 図 表 第 節 章 項 我が国 わが国 日本 経済 国 分析 本 当 今回 近年 最近 今後 現在 時期 期間 特徴 状態 見通し 期待 課題 考え 方".split())


@lru_cache(maxsize=1)
def _tagger():
    from fugashi import Tagger
    return Tagger()


def nouns(text):
    t = _tagger()
    out = []
    for w in t(text):
        f = w.feature
        if getattr(f, "pos1", "") == "名詞" and getattr(f, "pos2", "") in ("普通名詞", "固有名詞"):
            s = w.surface
            if len(s) >= 2 and s not in STOP and not re.fullmatch(r"[\d０-９\.,％%]+", s):
                out.append(s)
    return out
