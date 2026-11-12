"""372 CSV を Excel で開いて保存すると、何セルが変わってしまうのか
Excel（日本語の設定・「標準」の表示形式）が CSV を開くときの自動変換のうち、公開されている決まり8つを Python で再現し、
架空の顧客 CSV・商品 CSV を「開いて、そのまま CSV で保存した」あとと比べる。
Excel 本体では動かしていない（未検証）。乱数の種は 372。"""
import json, re, csv
from decimal import Decimal
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED = 372
SRC = "架空の顧客・商品 CSV（作成者が乱数で作成、seed 372）。Excel の動きは公開されている決まりを Python で再現したもの"
RULES = ["変わらない", "先頭の0が落ちる", "16桁以上で指数表記になり、下の桁が消える", "12桁以上で指数表記になる", "日付になる（1-2、1/2 など）",
         "日付の書き方が変わる（2025-04-01）", "指数と読まれる（12E3 など）", "小数の末尾の0が落ちる", "TRUE・FALSE になる"]


def fmt_general(d: Decimal) -> str:
    """「標準」の表示：有効15桁に丸め、整数部が12桁以上なら指数表記（小数5桁）"""
    if d == 0: return "0"
    d = +d.quantize(Decimal(1).scaleb(d.adjusted() - 14))          # 有効15桁
    if d.adjusted() >= 11:                                          # 整数部12桁以上
        m = d.scaleb(-d.adjusted()).quantize(Decimal("0.00001"))
        e = d.adjusted()
        if m >= 10: m, e = m / 10, e + 1
        return f"{m.normalize():f}E+{e:02d}"
    s = format(d.normalize(), "f")
    return s


def excel_open_save(s: str):
    """1セルの文字が、開いて保存したあとにどうなるか（このデータに出てくる書き方だけを扱う）。（保存後の文字, 当てはまった決まり）を返す"""
    t = s.strip()
    if t == "": return s, "変わらない"
    if t.upper() in ("TRUE", "FALSE"):
        return t.upper(), ("変わらない" if t == t.upper() else "TRUE・FALSE になる")
    # 日付：yyyy-mm-dd / yyyy/mm/dd
    m = re.fullmatch(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", t)
    if m and 1 <= int(m[2]) <= 12 and 1 <= int(m[3]) <= 31 and 1900 <= int(m[1]) <= 9999:
        o = f"{int(m[1])}/{int(m[2])}/{int(m[3])}"
        return o, ("変わらない" if o == s else "日付の書き方が変わる（2025-04-01）")
    # 日付：m-d / m/d（年なし）→ 「1月2日」
    m = re.fullmatch(r"(\d{1,2})[-/](\d{1,2})", t)
    if m and 1 <= int(m[1]) <= 12 and 1 <= int(m[2]) <= 31:
        return f"{int(m[1])}月{int(m[2])}日", "日付になる（1-2、1/2 など）"
    # 指数と読まれる文字（12E3、1e5）
    m = re.fullmatch(r"(\d+(?:\.\d+)?)[Ee]([+-]?\d{1,3})", t)
    if m:
        d = Decimal(t)
        mm = d.scaleb(-d.adjusted()).quantize(Decimal("0.01"))
        return f"{mm}E{'+' if d.adjusted() >= 0 else '-'}{abs(d.adjusted()):02d}", "指数と読まれる（12E3 など）"
    # 数字だけ（小数を含む）
    if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", t):
        d = Decimal(t)
        o = fmt_general(d)
        if o == s: return o, "変わらない"
        digits = len(t.lstrip("+-").split(".")[0].lstrip("0") or "0")
        if "E+" in o:
            return o, ("16桁以上で指数表記になり、下の桁が消える" if digits >= 16 else "12桁以上で指数表記になる")
        if "." in t and Decimal(o) == d and not t.lstrip("+-").startswith("0" * 2) and not re.match(r"[+-]?0\d", t):
            return o, "小数の末尾の0が落ちる"
        return o, "先頭の0が落ちる"
    return s, "変わらない"


def recoverable(col_kind, orig, new, rule):
    """保存後の文字だけから、元の文字を1通りに戻せるか"""
    if rule == "変わらない": return True
    if rule == "先頭の0が落ちる":
        return col_kind.startswith("fixed")             # 桁数が決まっている列なら0を足して戻せる
    if rule in ("日付の書き方が変わる（2025-04-01）", "TRUE・FALSE になる", "小数の末尾の0が落ちる", "日付になる（1-2、1/2 など）"):
        return True      # 月・日などの中身は残る。列の書き方が1つに決まっていれば、決まりで戻せる
    return False         # 桁が消える・元の書き方が1通りに決まらない


def make_data(rng):
    n = 5000
    cust = pd.DataFrame({
        "顧客コード": [f"{i:06d}" for i in rng.choice(np.arange(1, 400000), n, replace=False)],      # 6桁、先頭0あり
        "氏名": [f"顧客{i:05d}" for i in range(n)],
        "郵便番号": [f"{rng.integers(0, 9999999):07d}"[:3] + "-" + f"{rng.integers(0, 9999):04d}" for _ in range(n)],  # ハイフンあり→変わらない
        "電話番号": ["0" + str(rng.choice([90, 80, 70])) + f"{rng.integers(0, 99999999):08d}" for _ in range(n)],     # 11桁、ハイフンなし
        "会員番号": ["".join(map(str, rng.integers(1, 10, 1))) + "".join(map(str, rng.integers(0, 10, 15))) for _ in range(n)],  # 16桁
        "登録日": pd.to_datetime("2020-01-01") + pd.to_timedelta(rng.integers(0, 2100, n), unit="D"),
        "部屋番号": [rng.choice([f"{rng.integers(1, 13)}-{rng.integers(1, 29)}", f"{rng.integers(101, 999)}", ""],
                               p=[0.3, 0.6, 0.1]) for _ in range(n)],
        "ポイント": rng.integers(0, 50000, n).astype(str),
        "メール可": rng.choice(["true", "false"], n),
    })
    cust["登録日"] = cust["登録日"].dt.strftime("%Y-%m-%d")
    m = 2000
    def kata():
        r = rng.random()
        if r < 0.10: return f"{rng.integers(1, 99)}E{rng.integers(1, 9)}"            # 12E3 型
        if r < 0.25: return f"{rng.integers(1, 13)}-{rng.integers(1, 29)}"            # 1-10 型
        return f"{rng.choice(list('ABCDKSTX'))}{rng.choice(list('ABHNRZ'))}-{rng.integers(100, 9999)}"
    prod = pd.DataFrame({
        "商品コード": [f"{i:05d}" for i in rng.choice(np.arange(1, 99999), m, replace=False)],
        "JANコード": ["49" + f"{rng.integers(0, 99999999999):011d}" for _ in range(m)],       # 13桁
        "型番": [kata() for _ in range(m)],
        "サイズ": [rng.choice(["1/2", "3/4", "1/4", "10", "25", "S", "M", "L"], p=[.1, .08, .07, .15, .1, .2, .2, .1]) for _ in range(m)],
        "単価": [f"{rng.integers(50, 30000)}.{rng.choice(['00', '50', '80', '25'])}" for _ in range(m)],   # 小数2桁で固定
        "在庫数": rng.integers(0, 900, m).astype(str),
        "商品名": [f"商品{i:04d}" for i in range(m)],
    })
    return cust, prod


KIND = {"顧客コード": "fixed6", "氏名": "text", "郵便番号": "text", "電話番号": "fixed11", "会員番号": "num16", "登録日": "date",
        "部屋番号": "free", "ポイント": "int", "メール可": "flag", "商品コード": "fixed5", "JANコード": "num13", "型番": "free",
        "サイズ": "free", "単価": "fixed_dec", "在庫数": "int", "商品名": "text"}


def main():
    rng = np.random.default_rng(SEED)
    cust, prod = make_data(rng)
    cust.to_csv(DATA / "customers.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    prod.to_csv(DATA / "products.csv", index=False)
    # 決まりの確かめ（公開されている例と同じ結果になるか）
    tests = {"00123": "123", "09012345678": "9012345678", "4901234567894": "4.90123E+12", "1234567890123456": "1.23457E+15",
             "123456789012": "1.23457E+11", "12345678901": "12345678901", "1-2": "1月2日", "1/2": "1月2日", "2025-04-01": "2025/4/1",
             "12E3": "1.20E+04", "1200.50": "1200.5", "0.50": "0.5", "true": "TRUE",
             "AB-123": "AB-123", "100": "100"}
    for k, v in tests.items():
        assert excel_open_save(k)[0] == v, (k, excel_open_save(k), v)
    pd.DataFrame([{"元の文字": k, "開いて保存したあと": v, "決まり": excel_open_save(k)[1]} for k, v in tests.items()]).to_csv(RES / "rule_examples.csv", index=False)

    out = {"seed": SEED}; cells = []
    for name, df in [("顧客", cust), ("商品", prod)]:
        saved = df.copy()
        for c in df.columns:
            res = [excel_open_save(x) for x in df[c]]
            saved[c] = [r[0] for r in res]
            for o, (nw, rule) in zip(df[c], res):
                cells.append((name, c, o, nw, rule, recoverable(KIND[c], o, nw, rule)))
        saved.to_csv(DATA / f"{'customers' if name == '顧客' else 'products'}_after_excel.csv", index=False)
    C = pd.DataFrame(cells, columns=["表", "列", "元", "保存後", "決まり", "戻せる"])
    C["変わった"] = C["元"] != C["保存後"]
    bycol = C.groupby(["表", "列"], sort=False).agg(セル数=("変わった", "size"), 変わった=("変わった", "sum"),
                                                 戻せない=("戻せる", lambda s: int((~s).sum()))).reset_index()
    bycol["変わった割合%"] = (bycol["変わった"] / bycol["セル数"] * 100).round(1)
    bycol["戻せない割合%"] = (bycol["戻せない"] / bycol["セル数"] * 100).round(1)
    bycol.to_csv(RES / "changed_by_column.csv", index=False)
    byrule = C[C["変わった"]].groupby("決まり").agg(セル数=("変わった", "size"), 戻せない=("戻せる", lambda s: int((~s).sum()))).reindex(RULES[1:]).fillna(0).astype(int).reset_index()
    byrule.to_csv(RES / "changed_by_rule.csv", index=False)
    for name in ["顧客", "商品"]:
        s = C[C["表"] == name]
        out[name] = {"行": int(len(s) / s["列"].nunique()), "列": int(s["列"].nunique()), "セル": int(len(s)), "変わったセル": int(s["変わった"].sum()),
                     "変わった割合%": round(s["変わった"].mean() * 100, 1), "戻せないセル": int((~s["戻せる"]).sum()),
                     "戻せない割合%": round((~s["戻せる"]).mean() * 100, 1),
                     "変わった列数": int((s.groupby("列")["変わった"].sum() > 0).sum())}
        rows = s.assign(r=np.tile(np.arange(out[name]["行"]), out[name]["列"]) if False else s.groupby("列").cumcount())
        out[name]["1セル以上変わった行の割合%"] = round(rows.groupby("r")["変わった"].any().mean() * 100, 1)
        out[name]["戻せないセルがある行の割合%"] = round(rows.groupby("r")["戻せる"].apply(lambda x: (~x).any()).mean() * 100, 1)
    tot = C
    out["合計"] = {"セル": int(len(tot)), "変わったセル": int(tot["変わった"].sum()), "変わった割合%": round(tot["変わった"].mean() * 100, 1),
                 "戻せないセル": int((~tot["戻せる"]).sum()), "戻せない割合%": round((~tot["戻せる"]).mean() * 100, 1)}
    out["決まり別"] = {r["決まり"]: {"セル": int(r["セル数"]), "戻せない": int(r["戻せない"])} for _, r in byrule.iterrows()}
    # キーとして使えなくなる：保存後に同じ値になってしまう組
    dup = {}
    for name, df, col in [("顧客", cust, "会員番号"), ("商品", prod, "JANコード"), ("顧客", cust, "顧客コード"), ("商品", prod, "商品コード")]:
        after = [excel_open_save(x)[0] for x in df[col]]
        dup[col] = {"元の種類": int(df[col].nunique()), "保存後の種類": int(len(set(after)))}
    out["キーの種類"] = dup
    # 型番：何割が別の文字になったか
    t = C[C["列"] == "型番"]; out["型番"] = {"変わった割合%": round(t["変わった"].mean() * 100, 1), "内訳": t[t["変わった"]]["決まり"].value_counts().to_dict()}
    json.dump(out, open(RES / "a372_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：決まりごとの例（表）
    ex = [("00123", "顧客コード"), ("09012345678", "電話番号"), ("4901234567894", "JAN コード（13桁）"), ("1234567890123456", "会員番号（16桁）"),
          ("1-2", "部屋番号"), ("1/2", "サイズ"), ("2025-04-01", "登録日"), ("12E3", "型番"), ("1200.50", "単価"), ("true", "メール可")]
    fig, ax = plt.subplots(figsize=(8.6, 4.2)); ax.axis("off")
    tb = ax.table(cellText=[[b, a, excel_open_save(a)[0], excel_open_save(a)[1].split("（")[0]] for a, b in ex],
                  colLabels=["列", "CSV の文字", "開いて保存したあと", "当てはまった決まり"], loc="center", cellLoc="left", colWidths=[0.2, 0.22, 0.2, 0.38])
    tb.auto_set_font_size(False); tb.set_fontsize(9.5); tb.scale(1, 1.5)
    for (r, c), cell in tb.get_celld().items():
        cell.set_edgecolor("#dddddd")
        if r == 0: cell.set_facecolor("#f0f0ee"); cell.set_text_props(weight="bold")
        elif c == 2: cell.set_text_props(color=ORANGE)
    ax.set_title("開いて保存するだけで、こう変わる（再現した決まり）")
    save(fig, "a372_rule_examples.png", "出典：" + SRC, y=0.02)
    # 図2：列ごとの変わった割合
    b = bycol.iloc[::-1]
    fig, ax = plt.subplots(figsize=(8.4, 5.2))
    ax.barh(range(len(b)), b["変わった割合%"], color=LIGHT, label="変わったセル")
    ax.barh(range(len(b)), b["戻せない割合%"], color=ORANGE, label="うち、元に戻せないセル")
    ax.set_yticks(range(len(b))); ax.set_yticklabels([f"{t}：{c}" for t, c in zip(b["表"], b["列"])], fontsize=9)
    for i, (v, w) in enumerate(zip(b["変わった割合%"], b["戻せない割合%"])): ax.text(v + 1, i, f"{v:.0f}%" + (f"（戻せない {w:.0f}%）" if w > 0 else ""), va="center", fontsize=8.5)
    ax.set_xlim(0, 135); ax.set_xlabel("セルの割合（%）"); ax.legend(frameon=False, loc="lower right")
    ax.set_title("列ごとの、変わったセルと戻せないセル")
    save(fig, "a372_changed_by_column.png", "出典：" + SRC)
    # 図3：決まりごとの件数
    r = byrule.iloc[::-1]
    fig, ax = plt.subplots(figsize=(8.4, 4.0))
    ax.barh(range(len(r)), r["セル数"], color=LIGHT, label="変わったセル"); ax.barh(range(len(r)), r["戻せない"], color=ORANGE, label="うち、元に戻せないセル")
    ax.set_yticks(range(len(r))); ax.set_yticklabels(r["決まり"], fontsize=9)
    for i, (v, w) in enumerate(zip(r["セル数"], r["戻せない"])): ax.text(v + 60, i, f"{v:,}（戻せない {w:,}）", va="center", fontsize=8.5)
    ax.set_xlim(0, r["セル数"].max() * 1.35); ax.set_xlabel("セル数"); ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.45, -0.16), ncol=2)
    ax.set_title("決まりごとの、変わったセルの数")
    save(fig, "a372_changed_by_rule.png", "出典：" + SRC, y=-0.1)
    print(json.dumps(out, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
