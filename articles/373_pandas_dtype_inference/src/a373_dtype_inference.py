"""373 pandas で型を指定せずに読むと、何列が意図と違う型になるのか
(1) 公的統計の CSV 10本（手元の写し）を pd.read_csv(ファイル) だけで読み、数字のはずの列が何列、文字になるかを数える
(2) 正解の型を決めた架空の CSV（24列×3,000行）で、型が変わる列と、値そのものが変わるセルを数える
乱数の種は 373。"""
import json, csv, re, io, warnings
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

warnings.filterwarnings("ignore")
SEED = 373
SRC = "公的統計の CSV 10本（手元の写し）と架空の CSV（作成者が乱数で作成、seed 373）"
SYM = {"-", "－", "‐", "―", "…", "...", "***", "X", "x", "Ｘ", "△", "*", "＊", "・", "−"}
STEPS = ["a_何も指定しない", "b_文字コードだけ", "c_＋見出しの行を指定", "d_＋欠測の記号を指定", "e_＋桁区切りを指定", "f_＋途中と末尾の文字の行を除く"]
NUM = re.compile(r"[+-]?\d+(?:\.\d+)?")
NUMC = re.compile(r"[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?")


def kind(c):
    c = c.strip().replace("　", "")
    if c == "": return "empty"
    if NUM.fullmatch(c): return "num"
    if NUMC.fullmatch(c): return "comma"
    if c in SYM: return "sym"
    return "text"


def read_grid(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp932"):
        try:
            txt = raw.decode(enc); break
        except UnicodeDecodeError:
            continue
    rows = list(csv.reader(io.StringIO(txt)))
    w = max(len(r) for r in rows)
    return enc, [r + [""] * (w - len(r)) for r in rows], [len(r) for r in rows]


def public_part():
    recs, colrecs = [], []
    for f in sorted((DATA / "public").glob("*.csv")):
        enc, G, lens = read_grid(f)
        K = [[kind(c) for c in r] for r in G]
        # データの行：空でないセルの半分以上が、数字・コンマつき数字・記号の行
        isdata = [sum(k in ("num", "comma", "sym") for k in r) >= max(2, 0.5 * sum(k != "empty" for k in r)) for r in K]
        drows = [i for i, d in enumerate(isdata) if d]
        w = len(G[0])
        intended = []
        for j in range(w):
            ks = [K[i][j] for i in drows if K[i][j] != "empty"]
            if len(ks) >= 5 and sum(k in ("num", "comma", "sym") for k in ks) >= 0.8 * len(ks) and sum(k in ("num", "comma") for k in ks) >= 0.5 * len(ks):
                intended.append(j)
        # コードの列（先頭に0のある、桁のそろった数字）
        codecols = []
        for j in intended:
            ks = [G[i][j].strip() for i in drows if G[i][j].strip()]
            if ks and all(NUM.fullmatch(x) and x.isdigit() for x in ks) and len({len(x) for x in ks}) == 1 and any(x.startswith("0") and len(x) > 1 for x in ks):
                codecols.append(j)
        # (a) 何も指定しない
        res = {"ファイル": f.name, "文字コード": enc, "列": w, "行": len(G), "データの行": len(drows), "最初のデータ行": drows[0] + 1, "途中と末尾の文字の行": int(sum(1 for i in range(drows[0], len(G)) if i not in set(drows) and any(k != "empty" for k in K[i]))),
               "数字のはずの列": len(intended) - len(codecols), "コードの列": len(codecols)}
        tries = {"a_何も指定しない": {}, "b_文字コードだけ": {"encoding": enc},
                 "c_＋見出しの行を指定": {"encoding": enc, "header": None, "skiprows": drows[0]},
                 "d_＋欠測の記号を指定": {"encoding": enc, "header": None, "skiprows": drows[0], "na_values": sorted(SYM)},
                 "e_＋桁区切りを指定": {"encoding": enc, "header": None, "skiprows": drows[0], "na_values": sorted(SYM), "thousands": ","},
                 "f_＋途中と末尾の文字の行を除く": {"encoding": enc, "header": None, "skiprows": [i for i in range(len(G)) if i not in set(drows)],
                                        "na_values": sorted(SYM), "thousands": ","}}
        numcols = [j for j in intended if j not in codecols]
        for name, kw in tries.items():
            try:
                df = pd.read_csv(f, **kw)
                if df.shape[1] != w:
                    res[name] = f"列の数が違う（{df.shape[1]}列）"; res[name + "_数字で読めた列"] = 0; continue
                ok = sum(pd.api.types.is_numeric_dtype(df.iloc[:, j]) for j in numcols)
                res[name] = "読めた"; res[name + "_数字で読めた列"] = int(ok)
                if name == "a_何も指定しない":
                    for j in numcols:
                        col = df.iloc[:, j]
                        if pd.api.types.is_numeric_dtype(col): cause = "数字で読めた"
                        else:
                            ks = [kind(str(x)) for x in col.dropna()]
                            if any(k == "text" for k in ks): cause = "見出し・注の行が混ざる"
                            elif any(k == "sym" for k in ks): cause = "欠測などの記号"
                            elif any(k == "comma" for k in ks): cause = "桁区切りのコンマ"
                            else: cause = "その他"
                        colrecs.append({"ファイル": f.name, "列": j, "結果": cause})
                    zl = 0
                    for j in codecols:
                        if pd.api.types.is_numeric_dtype(df.iloc[:, j]):
                            zl += sum(G[i][j].strip().startswith("0") for i in drows)
                    res["先頭の0が落ちたセル"] = int(zl)
            except UnicodeDecodeError:
                res[name] = "エラー（文字コード）"; res[name + "_数字で読めた列"] = 0
            except pd.errors.ParserError:
                res[name] = "エラー（列の数がそろわない）"; res[name + "_数字で読めた列"] = 0
        if "先頭の0が落ちたセル" not in res: res["先頭の0が落ちたセル"] = 0
        if not res["a_何も指定しない"].startswith("読めた"):
            for j in numcols: colrecs.append({"ファイル": f.name, "列": j, "結果": "読み込みがエラー" if "エラー" in res["a_何も指定しない"] else "列がずれる"})
        recs.append(res)
    P = pd.DataFrame(recs); Cc = pd.DataFrame(colrecs)
    P.to_csv(RES / "public_files.csv", index=False); Cc.groupby(["ファイル", "結果"]).size().unstack(fill_value=0).to_csv(RES / "public_columns_by_cause.csv")
    return P, Cc


SPEC = [  # 列名, 正解の型, 何が起きるかの見込み
    ("市区町村コード", "文字（5桁）"), ("店舗コード", "文字（4桁）"), ("郵便番号", "文字（7桁）"), ("電話番号", "文字"), ("会員番号", "文字（20桁）"),
    ("国コード", "文字"), ("年", "整数"), ("来店回数", "整数"), ("家族の人数", "整数（空欄あり）"), ("従業者数", "整数（「-」あり）"),
    ("売上高", "整数（桁区切り）"), ("利益率", "小数（%つき）"), ("前年比", "小数（▲つき）"), ("客単価", "小数"), ("面積", "小数（「…」あり）"),
    ("登録日", "日付"), ("最終来店日", "日付（2025/4/1）"), ("メール可", "真偽（空欄あり）"), ("退会", "真偽"), ("年齢", "整数（全角まじり）"),
    ("区分", "文字"), ("氏名", "文字"), ("メモ", "文字"), ("在庫数", "整数")]


def make_fake(rng, n=3000):
    d = {}
    d["市区町村コード"] = [f"{rng.choice([1, 2, 4, 13, 14, 23, 27, 40, 47]):02d}{rng.integers(100, 700):03d}" for _ in range(n)]
    d["店舗コード"] = [f"{rng.integers(1, 9999):04d}" for _ in range(n)]
    d["郵便番号"] = [f"{rng.integers(10000, 9999999):07d}" for _ in range(n)]
    d["電話番号"] = [f"0{rng.choice([3, 6, 90, 80])}{rng.integers(10000000, 99999999)}" for _ in range(n)]
    d["会員番号"] = ["".join(map(str, rng.integers(1, 10, 1))) + "".join(map(str, rng.integers(0, 10, 19))) for _ in range(n)]
    d["国コード"] = rng.choice(["JP", "US", "CN", "KR", "NA", "DE"], n, p=[.6, .1, .1, .1, .04, .06])     # NA＝ナミビア
    d["年"] = rng.integers(2015, 2026, n).astype(str)
    d["来店回数"] = rng.integers(0, 60, n).astype(str)
    d["家族の人数"] = [str(rng.integers(1, 7)) if rng.random() > 0.08 else "" for _ in range(n)]
    d["従業者数"] = [str(rng.integers(1, 500)) if rng.random() > 0.05 else "-" for _ in range(n)]
    d["売上高"] = [f"{rng.integers(1000, 90000000):,}" for _ in range(n)]
    d["利益率"] = [f"{rng.normal(8, 4):.1f}%" for _ in range(n)]
    d["前年比"] = [(lambda v: f"▲{abs(v):.1f}" if v < 0 else f"{v:.1f}")(rng.normal(1, 6)) for _ in range(n)]
    d["客単価"] = [f"{rng.gamma(4, 600):.1f}" for _ in range(n)]
    d["面積"] = [f"{rng.gamma(3, 40):.1f}" if rng.random() > 0.04 else "…" for _ in range(n)]
    dt = pd.to_datetime("2019-01-01") + pd.to_timedelta(rng.integers(0, 2500, n), unit="D")
    d["登録日"] = dt.strftime("%Y-%m-%d")
    d["最終来店日"] = [f"{x.year}/{x.month}/{x.day}" for x in dt + pd.to_timedelta(rng.integers(0, 300, n), unit="D")]
    d["メール可"] = [rng.choice(["True", "False"]) if rng.random() > 0.1 else "" for _ in range(n)]
    d["退会"] = rng.choice(["True", "False"], n, p=[.1, .9])
    d["年齢"] = [str(a) if rng.random() > 0.01 else str(a).translate(str.maketrans("0123456789", "０１２３４５６７８９")) for a in rng.integers(18, 90, n)]
    d["区分"] = rng.choice(["A", "B", "C"], n)
    d["氏名"] = [f"顧客{i:05d}" for i in range(n)]
    d["メモ"] = rng.choice(["", "電話希望", "法人", "要確認"], n, p=[.7, .1, .1, .1])
    d["在庫数"] = rng.integers(0, 900, n).astype(str)
    return pd.DataFrame(d)[[s[0] for s in SPEC]]


def fake_part(rng):
    T = make_fake(rng)          # すべて文字で持った「正解」
    T.to_csv(DATA / "fake_customers.csv", index=False)
    D = pd.read_csv(DATA / "fake_customers.csv")                       # 何も指定しない
    S = pd.read_csv(DATA / "fake_customers.csv", dtype=str, keep_default_na=False)   # 文字のまま（確かめ用）
    assert (S.values == T.values).all()
    rows = []
    for name, want in SPEC:
        got = str(D[name].dtype); col = D[name]
        # 値が変わったセル：文字に直して元と比べる（数として同じなら同じとみなす。欠測は空欄と同じとみなす）
        def same(o, v):
            if pd.isna(v): return o == ""
            if isinstance(v, (bool, np.bool_)): return o == str(v)
            if isinstance(v, (int, np.integer)): return o == str(v)
            if isinstance(v, (float, np.floating)):
                try: return float(o) == float(v) and not (o.isdigit() and len(o) > 15) and not (o.startswith("0") and len(o) > 1 and o.isdigit())
                except ValueError: return False
            return o == str(v)
        changed = sum(not same(o, v) for o, v in zip(T[name], col))
        w = want.split("（")[0]
        ok = {"文字": got in ("object", "str", "string"), "整数": got.startswith("int"), "小数": got.startswith("float"), "日付": "datetime" in got, "真偽": got == "bool"}[w]
        rows.append({"列": name, "正解の型": want, "読み込み後の型": got, "型が合う": bool(ok), "値が変わったセル": int(changed)})
    R = pd.DataFrame(rows)
    def cls(r):
        if r["型が合う"] and r["値が変わったセル"] == 0: return "意図どおり"
        if r["値が変わったセル"] > 0: return "値が黙って変わる"
        if r["読み込み後の型"] in ("object", "str", "string"): return "文字のまま残る"
        return "型だけ違う（値は同じ）"
    R["分類"] = R.apply(cls, axis=1)
    R.to_csv(RES / "fake_columns.csv", index=False)
    # 型と欠測の記号を指定して読む
    conv = {"dtype": {c: str for c in ["市区町村コード", "店舗コード", "郵便番号", "電話番号", "会員番号", "国コード", "区分", "氏名", "メモ"]},
            "keep_default_na": False, "na_values": {c: ["", "-", "…"] for c in ["家族の人数", "従業者数", "面積", "メール可"]}, "thousands": ","}
    F = pd.read_csv(DATA / "fake_customers.csv", **conv)
    F["利益率"] = F["利益率"].str.rstrip("%").astype(float)
    F["前年比"] = F["前年比"].str.replace("▲", "-").astype(float)
    F["年齢"] = F["年齢"].astype(str).str.normalize("NFKC").astype(int)
    for c in ["登録日", "最終来店日"]: F[c] = pd.to_datetime(F[c])
    for c in ["家族の人数", "従業者数"]: F[c] = F[c].astype("Int64")
    F["メール可"] = F["メール可"].map({"True": True, "False": False}).astype("boolean")
    okfix = 0
    for name, want in SPEC:
        g = str(F[name].dtype); w = want.split("（")[0]
        okfix += {"文字": g in ("object", "str", "string"), "整数": g.lower().startswith("int"), "小数": g.startswith("float"), "日付": "datetime" in g, "真偽": g in ("bool", "boolean")}[w]
    assert (F["市区町村コード"] == T["市区町村コード"]).all() and (F["会員番号"] == T["会員番号"]).all() and (F["国コード"] == T["国コード"]).all()
    return R, okfix, len(T)


def main():
    rng = np.random.default_rng(SEED)
    P, Cc = public_part()
    R, okfix, n = fake_part(rng)
    out = {"seed": SEED}
    numtot = int(P["数字のはずの列"].sum())
    out["公的統計"] = {"ファイル": len(P), "数字のはずの列": numtot,
                    "何も指定しないで読めたファイル": int((P["a_何も指定しない"] == "読めた").sum()),
                    "何も指定しない結果": P["a_何も指定しない"].value_counts().to_dict(),
                    "数字で読めた列": {k: int(P[k + "_数字で読めた列"].sum()) for k in STEPS},
                    "原因別の列（何も指定しない）": Cc["結果"].value_counts().to_dict(),
                    "先頭の0が落ちたセル": int(P["先頭の0が落ちたセル"].sum()), "コードの列": int(P["コードの列"].sum())}
    out["公的統計"]["数字で読めた割合%"] = {k: round(v / numtot * 100, 1) for k, v in out["公的統計"]["数字で読めた列"].items()}
    out["架空"] = {"行": n, "列": len(R), "分類": R["分類"].value_counts().to_dict(), "型が合わない列": int((~R["型が合う"]).sum()),
                 "値が変わったセル": int(R["値が変わったセル"].sum()), "値が変わった列": R[R["値が変わったセル"] > 0][["列", "読み込み後の型", "値が変わったセル"]].to_dict("records"),
                 "型と記号を指定したあとに意図どおりの列": int(okfix)}
    json.dump(out, open(RES / "a373_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：公的統計　読み方ごとに、数字で読めた列の割合
    steps = STEPS
    v = [out["公的統計"]["数字で読めた割合%"][k] for k in steps]
    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    ax.barh(range(6), v[::-1], color=[BLUE] * 5 + [ORANGE])
    ax.set_yticks(range(6)); ax.set_yticklabels([s.split("_")[1] for s in steps[::-1]])
    for i, x in enumerate(v[::-1]): ax.text(x + 1, i, f"{x:.1f}%", va="center")
    ax.set_xlim(0, 112); ax.set_xlabel(f"数字のはずの列（{numtot}列）のうち、数字として読めた割合（%）")
    ax.set_title("公的統計の CSV 10本：指定を足すごとに、数字で読める列が増える")
    save(fig, "a373_public_steps.png", "出典：" + SRC)
    # 図2：公的統計　原因
    cs = Cc["結果"].value_counts()
    order = [c for c in ["数字で読めた", "見出し・注の行が混ざる", "欠測などの記号", "桁区切りのコンマ", "読み込みがエラー", "列がずれる", "その他"] if c in cs.index]
    fig, ax = plt.subplots(figsize=(8.2, 3.6))
    ax.barh(range(len(order)), [cs[c] for c in order][::-1], color=[GRAY if c == "数字で読めた" else ORANGE for c in order][::-1])
    ax.set_yticks(range(len(order))); ax.set_yticklabels(order[::-1])
    for i, c in enumerate(order[::-1]): ax.text(cs[c] + 2, i, f"{cs[c]}列", va="center")
    ax.set_xlim(0, cs.max() * 1.15); ax.set_xlabel("列の数")
    ax.set_title("何も指定しないで読んだとき、数字のはずの列はどうなったか")
    save(fig, "a373_public_causes.png", "出典：" + SRC)
    # 図3：架空の24列（表）
    fig, ax = plt.subplots(figsize=(9.0, 7.4)); ax.axis("off")
    tb = ax.table(cellText=R[["列", "正解の型", "読み込み後の型", "値が変わったセル", "分類"]].values.tolist(),
                  colLabels=["列", "正解の型", "読み込み後の型", "値が変わったセル", "分類"], loc="center", cellLoc="left", colWidths=[0.17, 0.22, 0.15, 0.14, 0.32])
    tb.auto_set_font_size(False); tb.set_fontsize(9); tb.scale(1, 1.32)
    for (r, c), cell in tb.get_celld().items():
        cell.set_edgecolor("#dddddd")
        if r == 0: cell.set_facecolor("#f0f0ee"); cell.set_text_props(weight="bold")
        elif R.iloc[r - 1]["分類"] == "値が黙って変わる": cell.set_facecolor("#fde9df")
        elif R.iloc[r - 1]["分類"].startswith("文字のまま"): cell.set_facecolor("#eef4fc")
    ax.set_title("架空の CSV（24列×3,000行）を、何も指定しないで読んだ結果")
    save(fig, "a373_fake_columns.png", "出典：" + SRC + "。橙は値が黙って変わる列、青は文字のまま残る列", y=0.06)
    print(json.dumps(out, ensure_ascii=False, indent=0)); print(P.iloc[:, :12].to_string()); print(R.to_string())


if __name__ == "__main__":
    main()
