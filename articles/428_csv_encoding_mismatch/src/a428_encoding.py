"""428 文字コードを取り違えて CSV を読むと、何行が壊れ、何行が黙って通るのか
架空の顧客表2万行（氏名・会社名・住所・メモ）を cp932・UTF-8・BOM つき UTF-8 で保存し、読み方を変えて比べる。乱数の種は428。"""
import csv, io, json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import *

rng = np.random.default_rng(428)
N = 20_000
SRC = "出所：架空のデータ（作成者が乱数で作成、seed 428）"
SEI = ["佐藤", "鈴木", "高橋", "田中", "伊藤", "渡辺", "山本", "中村", "小林", "加藤", "吉田", "山田", "松本", "井上", "木村", "林", "斎藤", "清水", "山崎", "森"]
SEI_EXT = ["髙橋", "山﨑", "濵田", "德永", "栁澤", "﨑山", "髙木", "桒原"]     # cp932 にはあるが、shift_jis（JIS X 0208 だけ）にはない字
SEI_OUT = ["𠮷田", "森鷗", "葛\U000E0100城", "辻\U000E0100本"]                  # cp932 でも書けない字（𠮷・鷗・異体字セレクタつきの葛と辻）
MEI = ["太郎", "花子", "一郎", "美咲", "健", "陽子", "大輔", "由美", "翔", "恵", "誠", "直子", "拓也", "愛", "学", "里奈"]
KEN = ["東京都千代田区", "大阪府大阪市北区", "愛知県名古屋市中区", "福岡県福岡市博多区", "北海道札幌市中央区", "宮城県仙台市青葉区", "広島県広島市中区", "神奈川県横浜市西区"]
CO = ["商事", "工業", "システム", "物産", "運輸", "食品", "建設", "サービス"]
MEMO = ["電話で確認済み", "再送の依頼あり", "", "", "", "請求書は郵送", "担当：営業一課", "折り返し待ち", "10:00～12:00に連絡", "ｶﾀｶﾅ表記あり"]


def make():
    rows = []
    for i in range(N):
        u = rng.random()
        sei = SEI_EXT[rng.integers(len(SEI_EXT))] if u < 0.04 else SEI[rng.integers(len(SEI))]
        name = sei + " " + MEI[rng.integers(len(MEI))]
        co = "あおば" + CO[rng.integers(len(CO))]
        v = rng.random()
        if v < 0.10:
            co = "㈱" + co                         # NEC 特殊文字
        elif v < 0.14:
            co = co + "（第" + "ⅠⅡⅢ"[rng.integers(3)] + "事業部）"   # ローマ数字
        else:
            co = "株式会社" + co
        addr = KEN[rng.integers(len(KEN))] + f"{rng.integers(1, 9)}-{rng.integers(1, 30)}-{rng.integers(1, 20)}"
        w = rng.random()
        if w < 0.05:
            addr += " ハイツ" + "①②③④⑤"[rng.integers(5)] + "号棟"       # 丸数字
        elif w < 0.08:
            addr += "、" + "第2ビル" + f"{rng.integers(1, 9)}階"
        memo = MEMO[rng.integers(len(MEMO))]
        rows.append([f"C{i + 1:06d}", name, co, addr, memo])
    return pd.DataFrame(rows, columns=["customer_id", "name", "company", "address", "memo"])


df = make()
NC = df.shape[1]


def to_bytes(d, enc, errors="strict"):
    buf = io.StringIO(); d.to_csv(buf, index=False, lineterminator="\r\n")
    return buf.getvalue().encode(enc, errors)


B = {"cp932": to_bytes(df, "cp932"), "utf-8": to_bytes(df, "utf-8"), "utf-8-sig": to_bytes(df, "utf-8-sig")}
(DATA / "customers_cp932.csv").write_bytes(B["cp932"]); (DATA / "customers_utf8.csv").write_bytes(B["utf-8"]); (DATA / "customers_utf8_bom.csv").write_bytes(B["utf-8-sig"])

MOJI = set("縺繧譁蜷菴螟荳譛驛逕髮鬮闕髟蝣雋")     # UTF-8 の日本語を cp932 で読んだときによく出る字


def is_jp(ch):
    o = ord(ch)
    return 0x3040 <= o <= 0x30FF or 0x4E00 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF


def allowed(ch):
    """この表に出てきてよい字：英数字と記号（ASCII）、かな、漢字、全角の記号、半角カタカナ、丸数字・ローマ数字・㈱"""
    o = ord(ch)
    return o < 0x7F or is_jp(ch) or 0x3000 <= o <= 0x303F or 0xFF00 <= o <= 0xFFEF or ch in "①②③④⑤ⅠⅡⅢ㈱"


def read(b, enc, errors):
    """戻り値：(状態, 表 or None, 止まった行)。止まったら、その手前まで読めた行数を返す"""
    try:
        txt = b.decode(enc, errors)
    except UnicodeDecodeError as e:
        upto = b[:e.start].count(b"\n")       # 見出しを1行と数える
        return "止まる", None, max(upto - 1, 0)
    rows = list(csv.reader(io.StringIO(txt, newline="")))
    return "通る", rows, None


def evaluate(file_enc, enc, errors):
    st, rows, stop = read(B[file_enc], enc, errors)
    r = {"ファイル": file_enc, "読み方": enc, "エラーの扱い": errors, "状態": st}
    if st == "止まる":
        r.update({"止まるまでに読めた行の割合": round(stop / N * 100, 2), "止まった行": stop + 1})
        return r, None
    head, body = rows[0], rows[1:]
    r["読めた行数"] = len(body); r["行数が同じ"] = len(body) == N
    r["見出しが同じ"] = head == list(df.columns)
    ncol_bad = sum(1 for x in body if len(x) != NC)
    r["列の数が変わった行"] = ncol_bad
    changed = key_ok = fffd = moji = odd = nojp = 0
    colchg = {c: 0 for c in df.columns}
    orig = df.values.tolist()
    for i in range(min(len(body), N)):
        x = body[i]; o = orig[i]
        if x != o:
            changed += 1
            for j, c in enumerate(df.columns):
                if j >= len(x) or x[j] != o[j]:
                    colchg[c] += 1
        if x and x[0] == o[0]:
            key_ok += 1
        s = "".join(x)
        if "�" in s:
            fffd += 1
        if MOJI & set(s):
            moji += 1
        if any(not allowed(ch) for ch in s):
            odd += 1
        if len(x) > 1 and not any(is_jp(ch) for ch in x[1]):
            nojp += 1
    changed += abs(len(body) - N)
    r.update({"中身が変わった行": changed, "中身が変わった行の割合": round(changed / N * 100, 2), "キーが元と同じ行の割合": round(key_ok / N * 100, 2),
              "置き換え文字のある行": fffd, "文字化けによく出る字のある行": moji,
              **{f"変わった行：{c}": v for c, v in colchg.items()}})
    # 検査で気づけるか
    r["検査：行数"] = not r["行数が同じ"]
    r["検査：見出しの名前"] = not r["見出しが同じ"]
    r["検査：キーの突き合わせ"] = key_ok < N
    r["検査：列の数"] = ncol_bad > 0
    r["検査：置き換え文字を探す"] = fffd > 0
    r["検査：文字化けの字を探す"] = moji > 0
    r["検査：想定外の字を探す"] = odd > 0
    r["検査：氏名に漢字・かながあるか"] = nojp > 0
    r["想定外の字のある行"] = odd; r["氏名に漢字・かながない行"] = nojp
    try:
        back = "\r\n".join(",".join(x) for x in rows)   # 引用符のない表なので、単純につなげば元のバイト列に戻るはず
        r["検査：元のバイト列に戻るか"] = (back + "\r\n").encode(enc if errors == "strict" else enc, "strict") != B[file_enc]
    except (UnicodeEncodeError, LookupError):
        r["検査：元のバイト列に戻るか"] = True
    return r, body


CASES = [("cp932", "cp932", "strict"), ("utf-8", "utf-8", "strict"), ("utf-8-sig", "utf-8-sig", "strict"),
         ("cp932", "utf-8", "strict"), ("cp932", "utf-8", "ignore"), ("cp932", "utf-8", "replace"),
         ("utf-8", "cp932", "strict"), ("utf-8", "cp932", "ignore"), ("utf-8", "cp932", "replace"),
         ("cp932", "shift_jis", "strict"), ("cp932", "shift_jis", "ignore"), ("cp932", "shift_jis", "replace"),
         ("utf-8-sig", "utf-8", "strict"), ("utf-8-sig", "cp932", "ignore"),
         ("utf-8", "latin-1", "strict"), ("cp932", "latin-1", "strict")]
res = []; bodies = {}
for c in CASES:
    r, body = evaluate(*c)
    res.append(r); bodies[c] = body
R = pd.DataFrame(res)
R.to_csv(RES / "read_cases.csv", index=False)

# ---- cp932 を shift_jis で読むと、どの字で止まるか
ext_rows = {"旧字の姓（髙・﨑・濵 など）": int(df.name.str.contains("[髙﨑濵德栁桒]").sum()),
            "㈱": int(df.company.str.contains("㈱").sum()), "ローマ数字（Ⅰ・Ⅱ・Ⅲ）": int(df.company.str.contains("[ⅠⅡⅢ]").sum()),
            "丸数字（①〜⑤）": int(df.address.str.contains("[①②③④⑤]").sum()), "全角の「～」": int(df.memo.str.contains("～").sum()),
            "半角カタカナ": int(df.memo.str.contains("[ｦ-ﾟ]").sum())}


def sj_ok(ch):
    try:
        ch.encode("cp932").decode("shift_jis"); return True
    except UnicodeDecodeError:
        return False


chars = sorted(set("".join(df.name) + "".join(df.company) + "".join(df.address) + "".join(df.memo)))
bad_chars = [c for c in chars if not sj_ok(c)]
any_ext = int(df.apply(lambda r: any(c in bad_chars for c in "".join(r.values)), axis=1).sum())
# 「〜」は cp932 と shift_jis で別の字として読まれる（黙って変わる）
wave = {"cp932 で読む": "～".encode("cp932").decode("cp932"), "shift_jis で読む": "～".encode("cp932").decode("shift_jis")}
wave_changed = wave["cp932 で読む"] != wave["shift_jis で読む"]

# ---- 書き出すとき：cp932 で書けない字
df2 = df.copy()
idx = rng.choice(N, size=400, replace=False)
for k, i in enumerate(idx):
    df2.loc[i, "name"] = SEI_OUT[k % len(SEI_OUT)] + " " + df2.loc[i, "name"].split(" ")[1]
emo = rng.choice(np.setdiff1d(np.arange(N), idx), size=200, replace=False)
for i in emo:
    df2.loc[i, "memo"] = "対応済み👍"
try:
    to_bytes(df2, "cp932"); wstop = None
except UnicodeEncodeError as e:
    wstop = e.object[:e.start].count("\n")
b_rep = to_bytes(df2, "cp932", "replace")
back = pd.read_csv(io.BytesIO(b_rep), encoding="cp932", dtype=str, keep_default_na=False)
w_changed = int((back.values != df2.values).any(axis=1).sum())
w_q = int(back.apply(lambda r: "?" in "".join(r.values), axis=1).sum())
w_key_ok = int((back.customer_id == df2.customer_id).sum())
b_ign = to_bytes(df2, "cp932", "ignore")
back2 = pd.read_csv(io.BytesIO(b_ign), encoding="cp932", dtype=str, keep_default_na=False)
w_changed_ign = int((back2.values != df2.values).any(axis=1).sum())
names_before = df2.name.nunique(); names_after = back.name.nunique(); names_after_ign = back2.name.nunique()
vs_rows = int(df2.name.str.contains("\U000E0100").sum())
write = {"書けない字のある行": 600, "strict で止まる行": None if wstop is None else int(wstop), "replace で中身が変わった行": w_changed, "「?」が入った行": w_q,
         "キーが同じ行": w_key_ok, "ignore で中身が変わった行": w_changed_ign, "氏名の種類：前": int(names_before), "氏名の種類：replace の後": int(names_after), "氏名の種類：ignore の後": int(names_after_ign),
         "異体字セレクタのある行": vs_rows, "ignore で氏名が空になった行": int((back2.name.str.split(" ").str[0] == "").sum())}

# ---- BOM：見出しの1列目
st, rows, _ = read(B["utf-8-sig"], "utf-8", "strict")
bom_head = rows[0][0]
pd_head = pd.read_csv(io.BytesIO(B["utf-8-sig"]), encoding="utf-8", dtype=str).columns[0]
bom = {"csv モジュールで読んだ1列目の見出し": repr(bom_head), "customer_id と同じか": bom_head == "customer_id",
       "pandas（encoding='utf-8'）で読んだ1列目の見出し": repr(pd_head), "pandas では同じか": pd_head == "customer_id"}

main = {"n": N, "bytes": {k: len(v) for k, v in B.items()}, "cases": json.loads(R.to_json(orient="records", force_ascii=False)),
        "ext_rows": ext_rows, "rows_with_any_non_sjis_char": any_ext, "non_sjis_chars": "".join(bad_chars), "wave_dash": {**{k: f"U+{ord(v):04X}" for k, v in wave.items()}, "変わる": wave_changed},
        "write": write, "bom": bom}
json.dump(main, open(RES / "a428_main.json", "w"), ensure_ascii=False, indent=1)

# 文字化けの例
ex = []
for c in [("utf-8", "cp932", "replace"), ("cp932", "utf-8", "replace"), ("cp932", "utf-8", "ignore"), ("cp932", "shift_jis", "ignore"), ("utf-8", "latin-1", "strict")]:
    b_ = bodies[c]
    for i in [0, 1, 2]:
        ex.append({"ファイル": c[0], "読み方": c[1], "エラーの扱い": c[2], "元の行": " | ".join(df.values.tolist()[i]), "読んだ行": " | ".join(b_[i])})
pd.DataFrame(ex).to_csv(RES / "mojibake_examples.csv", index=False)

# ---- 図1：取り違えの結果
lab = {("cp932", "utf-8", "strict"): "cp932 のファイルを UTF-8 で読む", ("cp932", "utf-8", "ignore"): "同上（読めない所は捨てる）", ("cp932", "utf-8", "replace"): "同上（読めない所は置き換える）",
       ("utf-8", "cp932", "strict"): "UTF-8 のファイルを cp932 で読む", ("utf-8", "cp932", "ignore"): "同上（読めない所は捨てる）", ("utf-8", "cp932", "replace"): "同上（読めない所は置き換える）",
       ("cp932", "shift_jis", "strict"): "cp932 のファイルを shift_jis で読む", ("cp932", "shift_jis", "ignore"): "同上（読めない所は捨てる）",
       ("utf-8-sig", "utf-8", "strict"): "BOM つき UTF-8 を UTF-8 で読む", ("utf-8", "latin-1", "strict"): "UTF-8 のファイルを latin-1 で読む"}
fig, ax = plt.subplots(figsize=(9.2, 4.8))
ys = []
for i, (c, l) in enumerate(lab.items()):
    r = R[(R["ファイル"] == c[0]) & (R["読み方"] == c[1]) & (R["エラーの扱い"] == c[2])].iloc[0]
    if r["状態"] == "止まる":
        ax.barh(i, 100, color="#eeeeee")
        ax.text(101, i, f"止まる（{int(r['止まった行']):,}行目）", va="center", fontsize=9, color=INK)
    else:
        v = r["中身が変わった行の割合"]
        ax.barh(i, v, color=ORANGE)
        t = f"黙って通る：{v:.1f}%の行が変わる" if v > 0 else "黙って通る：行は同じ、見出しの1列目だけ違う"
        if r["列の数が変わった行"] > 0:
            t += f"（列の数が変わる行 {int(r['列の数が変わった行']):,}）"
        ax.text(max(v, 0) + 1, i, t, va="center", fontsize=9, color=INK)
ax.set_yticks(range(len(lab))); ax.set_yticklabels(list(lab.values()), fontsize=9); ax.invert_yaxis()
ax.set_xlim(0, 170); ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xlabel("中身が変わった行の割合（%）。灰色の行は、読み込みが止まる")
ax.set_title("文字コードを取り違えると、止まるか、黙って通るか（2万行）")
save(fig, "a428_cases.png", SRC)

# ---- 図2：shift_jis で読めない字のある行
fig, ax = plt.subplots(figsize=(8.4, 4))
ks = list(ext_rows); vs = [ext_rows[k] for k in ks]
okc = [not sj_ok(ch) for ch in ["髙", "㈱", "Ⅰ", "①", "～", "ｶ"]]
cols = [ORANGE if o else (LIGHT if "～" in k else BLUE) for o, k in zip(okc, ks)]
ax.barh(ks, vs, color=cols); ax.invert_yaxis()
for i, (v, o, k) in enumerate(zip(vs, okc, ks)):
    ax.text(v + 30, i, f"{v:,}行　" + ("shift_jis では読めない" if o else ("読めるが、別の字（〜）になる" if "～" in k else "読める")), va="center", fontsize=9)
ax.set_xlim(0, max(vs) * 1.6); ax.set_xlabel("その字を含む行の数（2万行中）")
ax.set_title(f"cp932 のファイルを shift_jis で読むと、{any_ext:,}行（{any_ext / N * 100:.1f}%）の字が読めない")
save(fig, "a428_shift_jis_chars.png", SRC)

# ---- 図3：どの検査で気づけるか
chk = [c for c in R.columns if c.startswith("検査：")]
sil = [c for c in lab if R[(R["ファイル"] == c[0]) & (R["読み方"] == c[1]) & (R["エラーの扱い"] == c[2])].iloc[0]["状態"] == "通る"]
M = np.array([[bool(R[(R["ファイル"] == c[0]) & (R["読み方"] == c[1]) & (R["エラーの扱い"] == c[2])].iloc[0][k]) for k in chk] for c in sil])
fig, ax = plt.subplots(figsize=(11, 4.4))
ax.imshow(np.where(M, 1.0, 0.0), cmap=plt.matplotlib.colors.ListedColormap(["#f1f1ef", BLUE]), aspect="auto", vmin=0, vmax=1)
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        ax.text(j, i, "気づく" if M[i, j] else "気づかない", ha="center", va="center", fontsize=8.5, color="white" if M[i, j] else GRAY)
ax.set_xticks(range(len(chk))); ax.set_xticklabels([c.replace("検査：", "").replace("元のバイト列に戻るか", "元のバイト列\nに戻るか").replace("文字化けの字を探す", "文字化けの字\nを探す").replace("置き換え文字を探す", "置き換え文字\nを探す").replace("キーの突き合わせ", "キーの\n突き合わせ").replace("想定外の字を探す", "想定外の字\nを探す").replace("氏名に漢字・かながあるか", "氏名に漢字・\nかながあるか") for c in chk], fontsize=8.5)
ax.set_yticks(range(len(sil))); ax.set_yticklabels([lab[c] if not lab[c].startswith("同上") else {"cp932": "cp932→", "utf-8": "UTF-8→"}[c[0]] + c[1] + "（" + {"ignore": "捨てる", "replace": "置き換える"}[c[2]] + "）" for c in sil], fontsize=8.5)
for s_ in ax.spines.values():
    s_.set_visible(False)
ax.set_title("黙って通った読み方に、どの検査で気づけるか")
save(fig, "a428_checks.png", SRC, y=-0.04)
pd.DataFrame(M, index=[f"{c[0]}→{c[1]}（{c[2]}）" for c in sil], columns=chk).to_csv(RES / "checks_matrix.csv")
print(R[["ファイル", "読み方", "エラーの扱い", "状態", "止まるまでに読めた行の割合", "止まった行", "読めた行数", "列の数が変わった行", "中身が変わった行の割合", "キーが元と同じ行の割合", "置き換え文字のある行", "文字化けによく出る字のある行", "想定外の字のある行", "氏名に漢字・かながない行"]].to_string())
print(ext_rows, any_ext, bad_chars, main["wave_dash"]); print(write, bom)
print(pd.DataFrame(M, index=[f"{c[0]}→{c[1]}（{c[2]}）" for c in sil], columns=[c[3:7] for c in chk]).to_string())
for e in ex[:16:3]: print(e["読み方"], e["エラーの扱い"], "::", e["読んだ行"][:110])
