"""375 全角と半角、前後の空白で、キーはどれだけつながらないのか
架空の取引先マスタ（3,000社）と請求データ（30,000行）に表記のゆれを入れ、正規化を1段ずつ足しながら結合する。
つながらない行と、正規化のせいで別の取引先につながる行を数える。結合は DuckDB の SQL で行う。乱数の種は 375。"""
import json, re, unicodedata
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, FIG, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED = 375
SRC = "架空の取引先マスタと請求データ（作成者が乱数で作成、seed 375）"
HALF = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-",
                     "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ０１２３４５６７８９－")
KANA = ["サン", "エー", "マル", "ヤマ", "トー", "ワ", "ミツ", "ハシ", "カワ", "キタ", "ニシ", "フジ", "オカ", "タカ", "ノ", "シマ", "ヒガシ", "ミナミ", "アサヒ", "ダイ"]
KANJI = ["東", "和", "三", "光", "大", "栄", "信", "明", "松", "竹", "中", "央", "北", "南", "富", "士", "日", "本", "共", "立"]
ALPHA = ["ABC", "NK", "JT", "SK", "MT", "TS", "KS", "YM", "AZ", "Neo", "Tec", "Max", "Bio", "Net", "Lab"]
BIZ = ["商事", "工業", "物産", "産業", "建設", "運輸", "電機", "食品", "製作所", "サービス", "システム", "興業", "印刷", "薬品", "不動産"]


def to_hankaku_kana(s):
    out = ""
    for ch in s:
        if "ァ" <= ch <= "ヶ" or ch == "ー":
            h = unicodedata.normalize("NFKC", ch)
            # 全角カナ → 半角カナ（濁点は2文字に分かれる）
            for cand in range(0xFF61, 0xFFA0):
                if unicodedata.normalize("NFKC", chr(cand)) == ch: h = chr(cand); break
            else:
                d = unicodedata.normalize("NFD", ch)
                if len(d) == 2:
                    base = next((chr(c) for c in range(0xFF61, 0xFFA0) if unicodedata.normalize("NFKC", chr(c)) == d[0]), d[0])
                    h = base + {"゙": "ﾞ", "゚": "ﾟ"}[d[1]]
            out += h
        else: out += ch
    return out


def make(rng):
    names, seen = [], set()
    def stem():
        r = rng.random()
        if r < 0.45: return "".join(rng.choice(KANA, rng.integers(2, 4)))
        if r < 0.80: return "".join(rng.choice(KANJI, 2))
        return rng.choice(ALPHA) + rng.choice(["", "ジャパン", "テック"])
    while len(names) < 2880:
        s = stem() + rng.choice(BIZ)
        nm = "株式会社" + s if rng.random() < 0.6 else s + "株式会社"
        if nm not in seen:
            seen.add(nm); names.append(nm)
    stems = {n.replace("株式会社", "") for n in names}
    # わざと入れる「正規化するとぶつかる」別々の取引先（各20組＝40社、計120社）
    pairs = {"大文字小文字だけが違う": [], "中黒の有無だけが違う": [], "前株と後株だけが違う": []}
    k = 0
    while len(pairs["大文字小文字だけが違う"]) < 20:
        s = rng.choice(["Neo", "Tec", "Max", "Bio", "Net", "Lab"]) + rng.choice(KANA) + rng.choice(BIZ)
        a, b = "株式会社" + s, "株式会社" + s.upper()
        if a not in seen and b not in seen and s not in stems and s.upper() not in stems: seen |= {a, b}; stems |= {s, s.upper()}; pairs["大文字小文字だけが違う"].append((a, b))
    while len(pairs["中黒の有無だけが違う"]) < 20:
        p, q, bz = rng.choice(KANA), rng.choice(KANA), rng.choice(BIZ)
        a, b = f"株式会社{p}{q}{bz}", f"株式会社{p}・{q}{bz}"
        if a not in seen and b not in seen and p + q + bz not in stems: seen |= {a, b}; stems |= {p + q + bz, f"{p}・{q}{bz}"}; pairs["中黒の有無だけが違う"].append((a, b))
    while len(pairs["前株と後株だけが違う"]) < 20:
        s = "".join(rng.choice(KANJI, 2)) + rng.choice(BIZ)
        a, b = "株式会社" + s, s + "株式会社"
        if a not in seen and b not in seen and s not in stems: seen |= {a, b}; stems.add(s); pairs["前株と後株だけが違う"].append((a, b))
    for v in pairs.values():
        for a, b in v: names += [a, b]
    master = pd.DataFrame({"取引先コード": [f"T-{i:05d}" for i in rng.choice(np.arange(1, 99999), len(names), replace=False)], "取引先名": names})
    master = master.sample(frac=1, random_state=SEED).reset_index(drop=True); master["取引先ID"] = np.arange(len(master))
    n = 30000
    pick = rng.integers(0, len(master), n)
    inv = pd.DataFrame({"請求番号": np.arange(1, n + 1), "正しい取引先ID": pick, "取引先名": master["取引先名"].to_numpy()[pick],
                        "取引先コード": master["取引先コード"].to_numpy()[pick], "金額": (rng.gamma(2, 60000, n).round(-2)).astype(int)})
    kinds = []
    def vary(nm, code):
        tags = []
        u = rng.random
        if u() < 0.08 and "株式会社" in nm:
            nm = nm.replace("株式会社", rng.choice(["(株)", "（株）", "㈱"])); tags.append("法人格の書き方")
        if u() < 0.06 and re.search("[A-Za-z]", nm): nm = nm.translate(HALF); tags.append("全角の英字")
        if u() < 0.04 and re.search("[ァ-ヶ]", nm): nm = to_hankaku_kana(nm); tags.append("半角カナ")
        if u() < 0.03 and re.search("[A-Za-zＡ-Ｚａ-ｚ]", nm): nm = nm.upper() if u() < 0.5 else nm.lower(); tags.append("大文字小文字")
        if u() < 0.03:
            m = re.search("(商事|工業|物産|産業|建設|運輸|電機|食品|製作所|サービス|システム|興業|印刷|薬品|不動産|ｻｰﾋﾞｽ|ｼｽﾃﾑ)", nm)
            if m: nm = nm[:m.start()] + rng.choice([" ", "　"]) + nm[m.start():]; tags.append("間の空白")
        if u() < 0.05: nm = rng.choice([nm + " ", " " + nm, nm + "　", nm + "  "]); tags.append("前後の空白")
        if u() < 0.02: code = code.translate(HALF); tags.append("コード：全角")
        if u() < 0.01: code = code.lower(); tags.append("コード：小文字")
        if u() < 0.01: code = code + " "; tags.append("コード：後ろの空白")
        return nm, code, "＋".join(tags)
    res = [vary(a, b) for a, b in zip(inv["取引先名"], inv["取引先コード"])]
    inv["取引先名"] = [str(r[0]) for r in res]; inv["取引先コード"] = [str(r[1]) for r in res]; inv["入れたゆれ"] = [r[2] for r in res]
    for c in ["取引先コード", "取引先名"]: master[c] = master[c].map(str).astype(object)
    return master, inv, pairs


def n1(s): return s.strip(" 　\t")
def n2(s): return unicodedata.normalize("NFKC", n1(s))
def n3(s): return n2(s).upper()
def n4(s): return re.sub(r"[ 　]+", "", n3(s))
def n5(s): return n4(s).replace("(株)", "株式会社")
def n6(s): return re.sub(r"[・･\-‐－ｰ]", "", n5(s))            # 中黒・ハイフン類を取る（やりすぎの例）
def n7(s): return n6(s).replace("株式会社", "")                 # 法人格を取る（やりすぎの例）
STEPS = [("0 そのまま", lambda s: s), ("1 前後の空白を取る", n1), ("2 全角と半角をそろえる（NFKC）", n2), ("3 大文字にそろえる", n3),
         ("4 間の空白を取る", n4), ("5 （株）を株式会社にそろえる", n5), ("6 中黒・ハイフンを取る", n6), ("7 「株式会社」を取る", n7)]


def main():
    rng = np.random.default_rng(SEED)
    master, inv, pairs = make(rng)
    master.to_csv(DATA / "customers_master.csv", index=False); inv.to_csv(DATA / "invoices.csv", index=False)
    con = duckdb.connect(); n = len(inv); rows = []
    sql = """
    WITH j AS (
      SELECT i.請求番号, i.正しい取引先ID, i.金額, m.取引先ID
      FROM inv AS i LEFT JOIN mst AS m ON m.k = i.k)
    SELECT COUNT(DISTINCT 請求番号)                                                            AS 請求の行,
           COUNT(*)                                                                          AS 結合後の行,
           COUNT(DISTINCT CASE WHEN 取引先ID IS NULL THEN 請求番号 END)                          AS つながらない行,
           COUNT(DISTINCT CASE WHEN 取引先ID IS NOT NULL AND 取引先ID <> 正しい取引先ID THEN 請求番号 END) AS 別の取引先につながった行,
           SUM(CASE WHEN 取引先ID IS NULL THEN 金額 ELSE 0 END)                                 AS つながらない金額,
           SUM(金額)                                                                         AS 結合後の金額の合計
    FROM j"""
    open(SQL / "01_join_check_duckdb.sql", "w", encoding="utf-8").write("-- 正規化したキー k でつなぎ、つながらない行・別の取引先につながった行・行の増え方を数える（DuckDB）\n" + sql.strip() + ";\n")
    total_amt = int(inv["金額"].sum())
    for key_col, steps in [("取引先名", STEPS), ("取引先コード", STEPS[:5])]:
        for name, f in steps:
            mst = master.assign(k=master[key_col].map(lambda x: str(f(x))).astype(object)); iv = inv.assign(k=inv[key_col].map(lambda x: str(f(x))).astype(object))
            con.register("mst", mst[["取引先ID", "k"]]); con.register("inv", iv[["請求番号", "正しい取引先ID", "金額", "k"]])
            r = con.execute(sql).fetchone()
            # pandas でも同じ数になるか確かめる
            j = iv.merge(mst[["取引先ID", "k"]], on="k", how="left")
            assert len(j) == r[1] and j["取引先ID"].isna().sum() == r[2]
            dupk = int(mst["k"].duplicated(keep=False).sum())
            rows.append({"キー": key_col, "正規化": name, "つながらない行": r[2], "つながらない%": round(r[2] / n * 100, 2), "別の取引先につながった行": r[3],
                         "別の取引先%": round(r[3] / n * 100, 2), "結合後の行": r[1], "増えた行": r[1] - n, "キーが重なったマスタの行": dupk,
                         "つながらない金額%": round(r[4] / total_amt * 100, 2), "合計の差%": round((r[5] / total_amt - 1) * 100, 2)})
    R = pd.DataFrame(rows); R.to_csv(RES / "steps.csv", index=False)
    # ゆれの種類ごとに、どの段でつながるか（取引先名）
    kinds = ["前後の空白", "全角の英字", "半角カナ", "大文字小文字", "間の空白", "法人格の書き方"]
    tab = []
    for kd in kinds:
        sub = inv[inv["入れたゆれ"].str.contains(kd)]
        rec = {"ゆれ": kd, "行": len(sub), "請求に占める割合%": round(len(sub) / n * 100, 1)}
        for name, f in STEPS[:6]:
            keys = set(master["取引先名"].map(f)); rec[name] = round((~sub["取引先名"].map(f).isin(keys)).mean() * 100, 1)
        tab.append(rec)
    T = pd.DataFrame(tab); T.to_csv(RES / "unmatched_by_variation.csv", index=False)
    out = {"seed": SEED, "マスタ": len(master), "請求": n, "ゆれのある行%": round((inv["入れたゆれ"].str.contains("^(?!コード)|＋(?!コード)", regex=True) & (inv["入れたゆれ"] != "")).mean() * 100, 1),
           "名前にゆれのある行": int(inv["入れたゆれ"].map(lambda s: any(k in s for k in kinds)).sum()),
           "コードにゆれのある行": int(inv["入れたゆれ"].str.contains("コード").sum()),
           "わざと入れた、ぶつかる組": {k: len(v) for k, v in pairs.items()},
           "取引先名": {r["正規化"]: {k: r[k] for k in ["つながらない行", "つながらない%", "別の取引先につながった行", "別の取引先%", "増えた行", "キーが重なったマスタの行", "つながらない金額%", "合計の差%"]} for _, r in R[R["キー"] == "取引先名"].iterrows()},
           "取引先コード": {r["正規化"]: {k: r[k] for k in ["つながらない行", "つながらない%", "別の取引先につながった行", "増えた行"]} for _, r in R[R["キー"] == "取引先コード"].iterrows()}}
    out["名前にゆれのある行%"] = round(out["名前にゆれのある行"] / n * 100, 1)
    json.dump(out, open(RES / "a375_main.json", "w"), ensure_ascii=False, indent=1, default=int)

    N = R[R["キー"] == "取引先名"]
    # 図1：段ごとのつながらない行と、別の取引先につながった行
    fig, ax = plt.subplots(figsize=(8.8, 4.6)); y = np.arange(len(N))[::-1]
    ax.barh(y + 0.2, N["つながらない%"], 0.38, color=BLUE, label="つながらない行")
    ax.barh(y - 0.2, N["別の取引先%"], 0.38, color=ORANGE, label="別の取引先につながった行")
    ax.set_yticks(y); ax.set_yticklabels(N["正規化"], fontsize=9)
    for yy, a, b in zip(y, N["つながらない%"], N["別の取引先%"]):
        ax.text(a + 0.2, yy + 0.2, f"{a:.1f}%", va="center", fontsize=8.5); ax.text(b + 0.2, yy - 0.2, f"{b:.1f}%", va="center", fontsize=8.5)
    ax.set_xlabel("請求の行の割合（%）"); ax.legend(frameon=False, loc="center right"); ax.set_xlim(0, N["つながらない%"].max() * 1.15)
    ax.set_title("正規化を1段ずつ足したときの、取引先名での結合")
    save(fig, "a375_steps.png", "出典：" + SRC + "。上から順に正規化を足していった。6・7はやりすぎの例")
    # 図2：ゆれの種類ごとの表
    fig, ax = plt.subplots(figsize=(9.0, 3.4)); ax.axis("off")
    cols = ["ゆれ", "請求に占める割合%"] + [s[0] for s in STEPS[:6]]
    tb = ax.table(cellText=[[r["ゆれ"], f'{r["請求に占める割合%"]}%'] + [f'{r[c]:.0f}%' for c in cols[2:]] for _, r in T.iterrows()],
                  colLabels=["入れたゆれ", "行の割合"] + ["そのまま", "前後の空白", "＋NFKC", "＋大文字", "＋間の空白", "＋（株）"], loc="center", cellLoc="center",
                  colWidths=[0.2, 0.12] + [0.113] * 6)
    tb.auto_set_font_size(False); tb.set_fontsize(9.5); tb.scale(1, 1.6)
    for (r, c), cell in tb.get_celld().items():
        cell.set_edgecolor("#dddddd")
        if r == 0: cell.set_facecolor("#f0f0ee"); cell.set_text_props(weight="bold")
        elif c >= 2 and float(cell.get_text().get_text().rstrip("%")) > 0: cell.set_facecolor("#eef4fc")
    ax.set_title("ゆれの種類ごとの、つながらない行の割合（正規化を左から右へ足していく）")
    save(fig, "a375_by_variation.png", "出典：" + SRC + "。青のセルは、その段ではまだつながらない行が残っている", y=0.04)
    # 図3：名前とコード
    Cd = R[R["キー"] == "取引先コード"]
    fig, ax = plt.subplots(figsize=(8.8, 4.0))
    ax.plot(range(len(N)), N["つながらない%"], "-o", color=BLUE, label="取引先名：つながらない行")
    ax.plot(range(len(N)), N["別の取引先%"], "-o", color=ORANGE, label="取引先名：別の取引先につながった行")
    ax.plot(range(len(Cd)), Cd["つながらない%"], "--s", color=GRAY, label="取引先コード：つながらない行")
    ax.set_xticks(range(len(N))); ax.set_xticklabels([s.split(" ")[0] for s in N["正規化"]]); ax.set_xlabel("正規化の段（0＝そのまま、数字は図1と同じ）"); ax.set_ylabel("請求の行の割合（%）")
    ax.legend(frameon=False, fontsize=9); ax.set_title("コードでつなぐと、正規化は3段目までで足り、別の取引先にはつながらない")
    save(fig, "a375_name_vs_code.png", "出典：" + SRC)
    print(json.dumps(out, ensure_ascii=False, indent=0, default=int)); print(R.to_string()); print(T.to_string())


if __name__ == "__main__":
    main()
