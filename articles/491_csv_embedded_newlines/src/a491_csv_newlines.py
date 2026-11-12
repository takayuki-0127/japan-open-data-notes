"""491 セルの中に改行がある CSV を素朴に読むと、何行がずれるのか（実務の型）

架空の問い合わせの記録（本文に改行・カンマ・引用符が入る）を、CSV の決まりどおりに書き出し、
5通りの読み方で読み直して、正しく読めた件数・壊れた件数・列の数が合わない行を数える。
"""
import csv, io, json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 491
N = 10_000
CATS = ["配送", "返品", "請求", "会員", "商品", "その他"]
WORDS = ["注文した商品が届いていません", "箱がつぶれていました", "請求額が違うようです", "パスワードを忘れました",
         "サイズを交換したいです", "領収書を発行してください", "ポイントが付いていません", "配送日を変えたいです",
         "色が写真と違いました", "解約の方法を教えてください"]


def make_body(rng, p_nl):
    """本文。p_nl の確率で改行を1〜4個入れる。カンマ・引用符もときどき入る"""
    k = rng.integers(1, 4)
    parts = list(rng.choice(WORDS, size=k))
    if rng.random() < 0.25:
        parts[0] = parts[0] + "、" + "注文番号は A-" + str(rng.integers(1000, 9999)) + ", B-" + str(rng.integers(1000, 9999))
    if rng.random() < 0.10:
        parts[-1] = '「' + parts[-1] + '」と"至急"で書いてありました'
    if rng.random() < p_nl:
        n_nl = int(rng.integers(1, 5))
        out = parts[0]
        for i in range(1, len(parts) + n_nl):
            out += ("\r\n" if rng.random() < 0.3 else "\n") + (parts[i] if i < len(parts) else "よろしくお願いします")
        return out
    return "".join(parts)


def make_df(rng, n, p_nl):
    d0 = pd.Timestamp("2025-01-01")
    df = pd.DataFrame({
        "id": np.arange(1, n + 1),
        "received": [(d0 + pd.Timedelta(minutes=int(m))).strftime("%Y-%m-%d %H:%M") for m in np.sort(rng.integers(0, 525_600, n))],
        "category": rng.choice(CATS, n),
        "body": [make_body(rng, p_nl) for _ in range(n)],
        "amount": rng.integers(0, 30_000, n),
    })
    return df


def to_csv_text(df):
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    return buf.getvalue()


def read_methods(text, truth):
    """5通りで読み、記録ごとに『完全に正しい』かを数える"""
    out = {}
    lines = text.split("\n")                       # 物理的な行
    out["physical_lines"] = len([l for l in lines if l.strip() != ""]) - 1  # 見出しを除く
    ncol = truth.shape[1]
    truth_rows = truth.astype(str).values.tolist()
    truth_set = {tuple(r) for r in truth_rows}

    def score(rows):
        rows = [r for r in rows if any(c != "" for c in r)]
        ok = sum(1 for r in rows if tuple(r) in truth_set)
        bad_cols = sum(1 for r in rows if len(r) != ncol)
        return {"rows": len(rows), "ok": ok, "bad_cols": bad_cols, "wrong": len(rows) - ok}

    # ① 行で分けて、カンマで分ける（いちばん素朴）
    rows = [l.rstrip("\r").split(",") for l in lines[1:]]
    out["naive_split"] = score(rows)
    # ② 行で分けてから、1行ずつ csv モジュールで読む（引用符は分かるが、行をまたげない）
    rows = [next(csv.reader([l.rstrip("\r")])) if l.strip() else [] for l in lines[1:]]
    out["line_then_csv"] = score(rows)
    # ③ csv モジュールでファイル全体を読む（決まりどおり）
    rows = list(csv.reader(io.StringIO(text, newline="")))[1:]
    out["csv_module"] = score(rows)
    # ④ pandas.read_csv（既定）
    df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    out["pandas"] = score(df.values.tolist())
    # ⑤ DuckDB read_csv（既定）
    p = RES / "_tmp491.csv"
    p.write_text(text, encoding="utf-8")
    dd = duckdb.sql(f"SELECT * FROM read_csv('{p}', all_varchar=true)").df()
    p.unlink()
    out["duckdb"] = score(dd.fillna("").values.tolist())
    return out


def write_methods(df):
    """書き出す側の違い：引用符なしで書くと、決まりどおりに読んでも壊れる"""
    res = {}
    # 引用符をつけずに書く（join で自作）
    txt = "id,received,category,body,amount\r\n" + "\r\n".join(
        ",".join(str(x) for x in r) for r in df.astype(str).values.tolist()) + "\r\n"
    rows = list(csv.reader(io.StringIO(txt, newline="")))[1:]
    truth_set = {tuple(r) for r in df.astype(str).values.tolist()}
    res["no_quote_write"] = {"rows": len(rows), "ok": sum(1 for r in rows if tuple(r) in truth_set)}
    # 改行を空白に置き換えてから書く（内容は変わるが、行は壊れない）
    df2 = df.copy(); df2["body"] = df2["body"].str.replace(r"\r?\n", " ", regex=True)
    txt2 = to_csv_text(df2)
    rows2 = [l.rstrip("\r").split(",") for l in txt2.split("\n")[1:] if l.strip()]
    res["replace_newline_then_naive"] = {"rows": len(rows2),
                                         "ok_cols": sum(1 for r in rows2 if len(r) == df.shape[1])}
    return res


def main():
    rng = np.random.default_rng(SEED)
    df = make_df(rng, N, 0.12)
    text = to_csv_text(df)
    (DATA / "fictional_inquiries.csv").write_text(text, encoding="utf-8", newline="")
    n_nl = int(df["body"].str.contains("\n").sum())
    n_comma = int(df["body"].str.contains(",").sum())
    n_quote = int(df["body"].str.contains('"').sum())
    r = read_methods(text, df)
    w = write_methods(df)

    # 改行を含む本文の割合を変える
    sweep = []
    for p_nl in [0.0, 0.01, 0.03, 0.05, 0.1, 0.2, 0.3]:
        rr = np.random.default_rng(SEED + int(p_nl * 1000))
        d = make_df(rr, 5_000, p_nl)
        t = to_csv_text(d)
        m = read_methods(t, d)
        sweep.append({"p_newline": p_nl, "share_records_with_nl": float(d["body"].str.contains("\n").mean()),
                      "physical_lines_per_record": m["physical_lines"] / len(d),
                      "naive_ok_share": m["naive_split"]["ok"] / len(d),
                      "line_then_csv_ok_share": m["line_then_csv"]["ok"] / len(d),
                      "csv_ok_share": m["csv_module"]["ok"] / len(d)})
    sw = pd.DataFrame(sweep)
    sw.to_csv(RES / "sweep_newline_share.csv", index=False)

    # 正しさの確認
    assert r["csv_module"]["ok"] == N and r["pandas"]["ok"] == N and r["duckdb"]["ok"] == N
    lab = {"naive_split": "①行で分けて\nカンマで分ける", "line_then_csv": "②行で分けてから\n1行ずつCSVとして読む",
           "csv_module": "③csvモジュールで\n全体を読む", "pandas": "④pandas\nread_csv", "duckdb": "⑤DuckDB\nread_csv"}
    tab = pd.DataFrame([{"method": k, "rows_read": v["rows"], "ok": v["ok"], "wrong": v["wrong"], "bad_cols": v["bad_cols"]}
                        for k, v in r.items() if k != "physical_lines"])
    tab.to_csv(RES / "methods.csv", index=False)

    main_res = {"records": N, "physical_lines": r["physical_lines"], "records_with_newline": n_nl,
                "records_with_comma": n_comma, "records_with_quote": n_quote,
                "methods": {k: v for k, v in r.items() if k != "physical_lines"}, "write_side": w,
                "sweep": sweep}
    json.dump(main_res, open(RES / "a491_main.json", "w"), ensure_ascii=False, indent=1)

    # 図1：読み方ごとの結果
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    t = tab.set_index("method").loc[list(lab)]
    x = np.arange(len(t))
    ax.bar(x, t["ok"], color=BLUE, label="正しく読めた記録")
    ax.bar(x, t["wrong"], bottom=t["ok"], color=ORANGE, label="壊れた行（中身が元と違う）")
    for i, (ok, wr, rows) in enumerate(zip(t["ok"], t["wrong"], t["rows_read"])):
        ax.text(i, rows + 150, f"{rows:,}行\n正しい {ok:,}", ha="center", fontsize=9, color=INK)
    ax.axhline(N, color=GRAY, lw=1, ls="--", label=f"本当の記録の数（{N:,}件）")
    ax.set_xticks(x, [lab[k] for k in t.index], fontsize=9)
    ax.set_ylim(0, max(t["rows_read"]) * 1.18); ax.set_ylabel("読めた行の数")
    ax.set_title("同じCSV（本文の12%に改行あり）を5通りで読んだ結果")
    ax.legend(loc="upper right", fontsize=9, frameon=False, bbox_to_anchor=(1.0, 0.93))
    save(fig, "a491_methods.png", "架空の問い合わせ1万件（seed 491）で作成")

    # 図2：改行の割合と、素朴な読み方で正しく読める割合
    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    ax.plot(sw["share_records_with_nl"] * 100, sw["naive_ok_share"] * 100, "o-", color=ORANGE, label="①行で分けてカンマで分ける")
    ax.plot(sw["share_records_with_nl"] * 100, sw["line_then_csv_ok_share"] * 100, "s--", color=GREEN, label="②行で分けてから1行ずつCSVとして読む")
    ax.plot(sw["share_records_with_nl"] * 100, sw["csv_ok_share"] * 100, "^-", color=BLUE, label="③〜⑤決まりどおりに読む")
    ax.set_xlabel("本文に改行がある記録の割合（%）"); ax.set_ylabel("正しく読めた記録の割合（%）")
    ax.set_ylim(0, 105); ax.legend(fontsize=9, frameon=False, loc="lower left")
    ax.set_title("改行のある記録が増えると、素朴な読み方はどこまで落ちるか")
    save(fig, "a491_sweep.png", "架空の問い合わせ各5,000件（seed 491〜）で作成")

    # 図3：1件の記録が、物理的な行ではどう見えるか
    ex = df[df["body"].str.count("\n") >= 2].iloc[0]
    one = to_csv_text(pd.DataFrame([ex]))
    phys = one.split("\r\n", 1)[1].rstrip("\r\n").split("\n")
    fig, ax = plt.subplots(figsize=(8.8, 3.6)); ax.axis("off")
    ax.text(0, 1.0, "CSVファイルの中身（物理的な行）", fontsize=11, color=INK, va="top", weight="bold")
    for i, l in enumerate(phys):
        l = l.rstrip("\r")
        ax.text(0.0, 0.86 - i * 0.12, f"{i+1}行目：", fontsize=10, color=GRAY, va="top")
        ax.text(0.12, 0.86 - i * 0.12, l if len(l) < 60 else l[:58] + "…", fontsize=10, color=INK, va="top", family="monospace" if False else None)
        ncols = len(l.split(","))
        ax.text(0.98, 0.86 - i * 0.12, f"カンマで分けると{ncols}列", fontsize=9, color=ORANGE if ncols != 5 else BLUE, va="top", ha="right")
    y = 0.86 - len(phys) * 0.12 - 0.06
    ax.text(0, y, f"→ 決まりどおりに読めば、引用符の中の改行は本文の一部で、これで1件（5列）。行で分けると {len(phys)}行になる。",
            fontsize=10, color=BLUE, va="top")
    save(fig, "a491_example.png", "架空の問い合わせ（seed 491）の1件。列は id, received, category, body, amount", y=0.0)
    print(json.dumps({k: (v if k != "methods" else {m: x["ok"] for m, x in v.items()}) for k, v in main_res.items() if k != "sweep"}, ensure_ascii=False))
    print(sw.round(3).to_string())


if __name__ == "__main__":
    main()
