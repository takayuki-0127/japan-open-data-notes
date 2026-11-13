"""692 文字数の上限を len() で確かめると、絵文字や結合文字を含む文は何件が見た目と違う数になるのか

架空の入力文（ニックネームやひとこと、2万件）。7種類を混ぜる：
  ふつうの文字だけ／ふつうの絵文字（😀 など1文字）／肌の色つき（👍🏽）／家族などの合成（👨‍👩‍👧）／
  国旗（🇯🇵）／異体字セレクタつき（❤️）／濁点が分かれた文字（Mac のファイル名などで起きる「か＋゛」）
文字数を4通りで数える：
  見た目の文字数（書記素、regex の \\X）／Python の len（コードポイント）／UTF-16 の単位（JavaScript の length など）／
  NFC で正規化してからの len
上限20文字の判定がどれだけ食い違うか、20コードポイントで切ったときに文字が壊れる件数を数える。
"""
import json, unicodedata
import numpy as np
import pandas as pd
import regex
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, LIGHT, INK, GREEN

SRC = "出典：架空の入力文（作成者が乱数で作成、seed 692）"
rng = np.random.default_rng(692)
DATA.mkdir(exist_ok=True)
N, LIMIT = 20000, 20
BASE = list("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん") + list("今日明晴雨雪花月星空海山川駅店茶")
DAK = list("かきくけこさしすせそたちつてとはひふへほ")
EMO = {
    "simple": ["😀", "🎉", "🍙", "🐱", "✨", "🌸"],
    "skin": ["👍🏽", "👋🏻", "🙏🏿", "👏🏼"],
    "zwj": ["👨‍👩‍👧", "👩‍💻", "🧑‍🍳", "👨‍👩‍👧‍👦"],
    "flag": ["🇯🇵", "🇫🇷", "🇧🇷"],
    "vs16": ["❤️", "☀️", "✌️"],
}
KINDS = ["plain", "simple", "skin", "zwj", "flag", "vs16", "nfd"]
P = [0.55, 0.15, 0.06, 0.06, 0.04, 0.07, 0.07]


def make(kind):
    L = int(rng.integers(8, 23))
    s = [rng.choice(BASE) for _ in range(L)]
    if kind == "nfd":
        for _ in range(int(rng.integers(2, 6))):
            s[int(rng.integers(0, L))] = unicodedata.normalize("NFD", unicodedata.normalize("NFC", rng.choice(DAK) + "゙"))
    elif kind != "plain":
        for _ in range(int(rng.integers(1, 4))):
            s[int(rng.integers(0, L))] = rng.choice(EMO[kind])
    return "".join(s)


kinds = rng.choice(KINDS, N, p=P)
texts = [make(k) for k in kinds]
D = pd.DataFrame({"kind": kinds, "text": texts})
D["graphemes"] = D.text.map(lambda t: len(regex.findall(r"\X", t)))
D["len"] = D.text.map(len)
D["utf16"] = D.text.map(lambda t: len(t.encode("utf-16-le")) // 2)
D["nfc_len"] = D.text.map(lambda t: len(unicodedata.normalize("NFC", t)))


def broken_cut(t, n=LIMIT):
    """先頭 n コードポイントで切ったとき、最後の文字（書記素）が途中で切れるか"""
    cut = t[:n]
    if len(t) <= n:
        return False
    g = regex.findall(r"\X", t); acc = 0
    for x in g:
        acc += len(x)
        if acc == n:
            return False
        if acc > n:
            return True
    return False


D["cut_broken"] = D.text.map(broken_cut)
D.to_csv(DATA / "texts.csv", index=False)
for m in ["len", "utf16", "nfc_len"]:
    D[f"over_{m}"] = D[m] > LIMIT
D["over_true"] = D.graphemes > LIMIT
K = D.groupby("kind").agg(n=("text", "size"), graphemes=("graphemes", "mean"), len=("len", "mean"), utf16=("utf16", "mean"),
                          nfc_len=("nfc_len", "mean"), diff_len=("len", lambda v: 0)).drop(columns="diff_len")
K["mismatch_len_pct"] = D.groupby("kind").apply(lambda g: (g["len"] != g["graphemes"]).mean() * 100, include_groups=False)
K["false_over_len_pct"] = D.groupby("kind").apply(lambda g: ((g["over_len"]) & (~g["over_true"])).mean() * 100, include_groups=False)
K["false_over_utf16_pct"] = D.groupby("kind").apply(lambda g: ((g["over_utf16"]) & (~g["over_true"])).mean() * 100, include_groups=False)
K["cut_broken_pct"] = D.groupby("kind").apply(lambda g: g["cut_broken"].mean() * 100, include_groups=False)
K = K.reindex(KINDS); K.round(2).to_csv(RES / "by_kind.csv")
tot = {"n": N, "limit": LIMIT,
       "mismatch_len": int((D["len"] != D.graphemes).sum()), "mismatch_utf16": int((D.utf16 != D.graphemes).sum()),
       "mismatch_nfc": int((D.nfc_len != D.graphemes).sum()),
       "true_over": int(D.over_true.sum()),
       "over_len": int(D.over_len.sum()), "over_utf16": int(D.over_utf16.sum()), "over_nfc": int(D.over_nfc_len.sum()),
       "false_over_len": int((D.over_len & ~D.over_true).sum()), "false_over_utf16": int((D.over_utf16 & ~D.over_true).sum()),
       "false_over_nfc": int((D.over_nfc_len & ~D.over_true).sum()),
       "cut_broken": int(D.cut_broken.sum()),
       "max_len_per_grapheme": {"family": len("👨‍👩‍👧‍👦"), "family_utf16": len("👨‍👩‍👧‍👦".encode("utf-16-le")) // 2},
       "by_kind": K.round(2).to_dict(orient="index")}
json.dump(tot, open(RES / "a692_main.json", "w"), ensure_ascii=False, indent=1)

lab = {"plain": "ふつうの文字だけ", "simple": "ふつうの絵文字", "skin": "肌の色つき", "zwj": "合成の絵文字", "flag": "国旗", "vs16": "異体字セレクタつき", "nfd": "濁点が分かれた文字"}
# 図1：見た目1文字あたりの数え方
ex = [("か", "か"), ("が（NFC）", "が"), ("が（濁点が分かれた）", "が"), ("😀", "😀"), ("❤️", "❤️"), ("🇯🇵", "🇯🇵"), ("👍🏽", "👍🏽"), ("👨‍👩‍👧‍👦", "👨‍👩‍👧‍👦")]
fig, ax = plt.subplots(figsize=(9, 4))
x = np.arange(len(ex)); w = 0.38
l1 = [len(t) for _, t in ex]; l2 = [len(t.encode("utf-16-le")) // 2 for _, t in ex]
ax.bar(x - w / 2, l1, w, color=ORANGE, label="Python の len（コードポイント）"); ax.bar(x + w / 2, l2, w, color=BLUE, label="UTF-16 の単位（JavaScript の length など）")
for i in range(len(ex)):
    ax.text(i - w / 2, l1[i], str(l1[i]), ha="center", va="bottom", fontsize=9); ax.text(i + w / 2, l2[i], str(l2[i]), ha="center", va="bottom", fontsize=9)
ax.axhline(1, color=INK, ls="--", lw=0.8)
ax.set_xticks(x); ax.set_xticklabels([n for n, _ in ex], fontsize=8.5, rotation=20, ha="right")
ax.set_ylabel("数えた文字数"); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("見た目はどれも1文字（点線）。家族の絵文字は len で7、UTF-16 で11")
save(fig, "a692_per_char.png", SRC)

# 図2：種類ごとの「上限20を超える」と誤って判定した割合
fig, ax = plt.subplots(figsize=(9, 4))
ks = KINDS[1:]; x = np.arange(len(ks))
ax.bar(x - w / 2, K.loc[ks, "false_over_len_pct"], w, color=ORANGE, label="len で判定")
ax.bar(x + w / 2, K.loc[ks, "false_over_utf16_pct"], w, color=BLUE, label="UTF-16 で判定")
for i, k in enumerate(ks):
    ax.text(i - w / 2, K.loc[k, "false_over_len_pct"], f"{K.loc[k, 'false_over_len_pct']:.0f}", ha="center", va="bottom", fontsize=8.5)
    ax.text(i + w / 2, K.loc[k, "false_over_utf16_pct"], f"{K.loc[k, 'false_over_utf16_pct']:.0f}", ha="center", va="bottom", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([lab[k] for k in ks], fontsize=9); ax.set_ylabel("見た目は20文字以内なのに「超え」とした割合（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("見た目では上限内でも、数え方で「長すぎる」と断る文が出る")
save(fig, "a692_false_over.png", SRC)

# 図3：全体の件数
fig, ax = plt.subplots(figsize=(8.5, 3.6))
items = [("見た目と len が違う", tot["mismatch_len"]), ("見た目と UTF-16 が違う", tot["mismatch_utf16"]), ("NFC にしても違う", tot["mismatch_nfc"]),
         ("len で誤って上限超え", tot["false_over_len"]), ("UTF-16 で誤って上限超え", tot["false_over_utf16"]), ("20コードポイントで切ると壊れる", tot["cut_broken"])]
ax.barh(range(len(items)), [v for _, v in items], color=[ORANGE, BLUE, GRAY, ORANGE, BLUE, INK])
for i, (_, v) in enumerate(items):
    ax.text(v, i, f" {v:,}件（{v / N * 100:.1f}%）", va="center", fontsize=9)
ax.set_yticks(range(len(items))); ax.set_yticklabels([n for n, _ in items]); ax.invert_yaxis()
ax.set_xlabel(f"件数（全{N:,}件）"); ax.set_title("2万件のうち、数え違いと切れた文字の件数")
save(fig, "a692_totals.png", SRC)
print(json.dumps({k: v for k, v in tot.items() if k != "by_kind"}, ensure_ascii=False, indent=1))
