"""474-2 正解が分かっている架空の集計表（結合セル・省略された見出し・小計つき）を Excel に書き出し、
3通りの読み方で「正しい分類に戻せた行」と「部門別・地域別の合計」を比べる。Excel の画面操作はしていない（openpyxl で書いて pandas で読む）。"""
import json
import numpy as np, pandas as pd, matplotlib.pyplot as plt, duckdb, openpyxl
from openpyxl.styles import Alignment
from common import *

rng = np.random.default_rng(474)
DEPTS = ["食品", "飲料", "日用品", "衣料", "家電", "文具", "玩具", "園芸", "寝具", "カー用品", "ペット用品", "サービス"]
CATS = ["定番", "季節", "特売", "新商品", "業務用", "ギフト"]
REG = ["東日本", "西日本"]
MONTHS = ["4月", "5月", "6月"]


def make_truth():
    rows = []
    for d in DEPTS:
        if d == "サービス":                       # 商品区分がもともと無い部門
            cats = [None]
        else:
            cats = list(rng.choice(CATS, size=rng.integers(3, 6), replace=False))
        for c in cats:
            for i in range(rng.integers(2, 6)):
                reg = None if rng.random() < 0.10 else REG[rng.integers(0, 2)]   # 地域は1割が本当に不明
                s = rng.integers(20, 400, 3); q = rng.integers(5, 90, 3)
                rows.append([d, c, f"{d}{len(rows)+1:03d}", reg, *s, *q])
    return pd.DataFrame(rows, columns=["部門", "商品区分", "商品", "地域"] + [f"売上_{m}" for m in MONTHS] + [f"数量_{m}" for m in MONTHS])


def write_excel(t, path):
    """人が見るための表：部門は縦に結合、商品区分は上と同じなら省略、部門ごとに小計と空行、最後に合計、見出しは2段。"""
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "部門別売上"
    ws["A1"] = "部門別売上表（架空）"
    ws.cell(3, 1, "部門"); ws.cell(3, 2, "商品区分"); ws.cell(3, 3, "商品"); ws.cell(3, 4, "地域")
    ws.cell(3, 5, "売上（万円）"); ws.merge_cells(start_row=3, start_column=5, end_row=3, end_column=7)
    ws.cell(3, 8, "数量"); ws.merge_cells(start_row=3, start_column=8, end_row=3, end_column=10)
    for a in range(1, 5): ws.merge_cells(start_row=3, start_column=a, end_row=4, end_column=a)
    for j, m in enumerate(MONTHS): ws.cell(4, 5 + j, m); ws.cell(4, 8 + j, m)
    r = 5; val = [c for c in t.columns if "_" in c]
    for d, g in t.groupby("部門", sort=False):
        top = r; prev = object()
        for _, x in g.iterrows():
            if r == top: ws.cell(r, 1, d)
            if x["商品区分"] is not None and x["商品区分"] != prev: ws.cell(r, 2, x["商品区分"])
            prev = x["商品区分"]
            ws.cell(r, 3, x["商品"])
            if x["地域"] is not None: ws.cell(r, 4, x["地域"])
            for j, c in enumerate(val): ws.cell(r, 5 + j, int(x[c]))
            r += 1
        if r - 1 > top: ws.merge_cells(start_row=top, start_column=1, end_row=r - 1, end_column=1)
        ws.cell(top, 1).alignment = Alignment(vertical="center")
        ws.cell(r, 3, "小計")
        for j, c in enumerate(val): ws.cell(r, 5 + j, int(g[c].sum()))
        r += 2                                   # 小計のあとに空行
    ws.cell(r, 1, "合計")
    for j, c in enumerate(val): ws.cell(r, 5 + j, int(t[c].sum()))
    wb.save(path)


truth = make_truth()
truth.to_csv(DATA / "fictional_truth.csv", index=False, encoding="utf-8-sig")
XL = DATA / "fictional_report.xlsx"; write_excel(truth, XL)
val = [c for c in truth.columns if "_" in c]; sales = [c for c in val if c.startswith("売上")]
N = len(truth); TOT = int(truth[sales].sum().sum())

# ---- 読み方① そのまま読む（見出しは下の段だけ）
raw = pd.read_excel(XL, header=3)
raw.columns = ["部門", "商品区分", "商品", "地域"] + list(raw.columns[4:])
print("①の列名:", list(raw.columns))
a = raw.copy(); a.columns = ["部門", "商品区分", "商品", "地域"] + val   # 列の名前だけは位置で付け直して比べる
# ---- 読み方② 全部の列を下方向に埋める（空行もそのまま）
b = a.ffill()
# ---- 読み方②' 空行を落としてから全部の列を埋める
b2 = a.dropna(how="all").ffill()
# ---- 読み方②" 空行・小計・合計を落としてから全部の列を埋める
b3 = a.dropna(how="all"); b3 = b3[(b3["商品"] != "小計") & (b3["部門"] != "合計")].ffill()
# ---- 読み方③ 列ごとに決める：空行と小計・合計を落とす／部門は結合セルの範囲で埋める／商品区分は部門の中だけで埋める／地域は埋めない
ws = openpyxl.load_workbook(XL).active
c = a.copy(); c["行"] = np.arange(len(c)) + 5
for m in ws.merged_cells.ranges:
    if m.min_col == 1 and m.max_col == 1 and m.min_row >= 5:
        c.loc[(c["行"] >= m.min_row) & (c["行"] <= m.max_row), "部門"] = ws.cell(m.min_row, 1).value
c = c.dropna(how="all", subset=["商品"] + val)
c = c[(c["商品"] != "小計") & (c["部門"] != "合計")]
c = c[c["商品"].notna()]
c["部門"] = c["部門"].ffill()                      # 1行だけの部門（結合なし）は自分の行に書いてある
c["商品区分"] = c.groupby("部門", sort=False)["商品区分"].ffill()
c = c.drop(columns="行")

tk = truth.set_index("商品")


def score(df, name):
    d = df[df["商品"].isin(tk.index)].copy()            # 明細の行（商品名で正解と突き合わせる）
    dup = int(d["商品"].duplicated().sum())
    d1 = d.drop_duplicates("商品").set_index("商品").reindex(tk.index)
    eq = lambda col: ((d1[col] == tk[col]) | (d1[col].isna() & tk[col].isna()))
    ok_d, ok_c, ok_r = eq("部門"), eq("商品区分"), eq("地域")
    wrong_c = int((d1["商品区分"].notna() & ~ok_c).sum()); wrong_r = int((d1["地域"].notna() & ~ok_r).sum())
    by_d = df.groupby("部門")[sales].sum().sum(axis=1)
    td = truth.groupby("部門")[sales].sum().sum(axis=1)
    by_d = by_d.reindex(td.index).fillna(0)
    by_r = df.groupby("地域")[sales].sum().sum(axis=1).reindex(REG).fillna(0)
    tr = truth.groupby("地域")[sales].sum().sum(axis=1).reindex(REG)
    return dict(読み方=name, 行数=len(df), 明細でない行=int(len(df) - len(d)), 重複した明細=dup,
                部門が空=int(d1["部門"].isna().sum()), 商品区分が空=int((d1["商品区分"].isna() & tk["商品区分"].notna()).sum()),
                部門が正しい_pct=round(100 * ok_d.mean(), 1), 商品区分が正しい_pct=round(100 * ok_c.mean(), 1), 地域が正しい_pct=round(100 * ok_r.mean(), 1),
                三つとも正しい_pct=round(100 * (ok_d & ok_c & ok_r).mean(), 1),
                違う商品区分が入った=wrong_c, 違う地域が入った=wrong_r,
                売上の総合計_対正解pct=round(100 * df[sales].sum().sum() / TOT, 1),
                部門別合計のずれ_平均pct=round(float((100 * (by_d - td).abs() / td).mean()), 1),
                部門別に集計できた売上_pct=round(100 * by_d.sum() / TOT, 1),
                地域別合計のずれ_平均pct=round(float((100 * (by_r - tr).abs() / tr).mean()), 1),
                東日本_対正解pct=round(100 * by_r["東日本"] / tr["東日本"], 1), 西日本_対正解pct=round(100 * by_r["西日本"] / tr["西日本"], 1))


S = pd.DataFrame([score(a, "①そのまま"), score(b, "②全部の列を下に埋める"), score(b2, "②'空行を落としてから全部埋める"), score(b3, "②''空行と小計・合計を落としてから全部埋める"), score(c, "③列ごとに決める")])
S.to_csv(RES / "fictional_three_ways.csv", index=False, encoding="utf-8-sig")
print(S.T.to_string())

# ---- T-SQL 形の「下方向に埋める」（部門の中だけ）を DuckDB で実行し、pandas と一致することを確かめる
t0 = a.copy(); t0["row_no"] = np.arange(len(t0)); t0 = t0.rename(columns={"部門": "dept", "商品区分": "cat", "商品": "item", "地域": "region"})[["row_no", "dept", "cat", "item", "region"]]
con = duckdb.connect(); con.register("sheet_rows", t0)
q = open(SQL / "01_filldown_tsql.sql", encoding="utf-8").read()
sq = con.execute(q).df()
pc = c.reset_index(drop=True)
assert len(sq) == len(pc) and (sq["dept"].values == pc["部門"].values).all() and (sq["cat"].fillna("") == pc["商品区分"].fillna("").values).all() and (sq["region"].fillna("") == pc["地域"].fillna("").values).all()
print("SQL 一致", len(sq))

# ---- 繰り返し：表を300回作り直す（Excel は介さず、同じ規則をデータの上で再現）
sw = []
for miss in [0, 0.02, 0.05, 0.10, 0.20, 0.30]:
    res = []
    for s in range(300):
        r = np.random.default_rng(10000 + s)
        n = int(sum(r.integers(2, 6) for d in range(12) for _ in range(1 if d == 11 else r.integers(3, 6))))
        isna = r.random(n) < miss; reg = r.integers(0, 2, n)
        ser = pd.Series(np.where(isna, np.nan, reg)); f = ser.ffill()
        wrong = (isna & f.notna()).sum()
        # 地域別の件数のずれ（東日本）
        res.append([n, wrong, 100 * wrong / n, 100 * ((f == 0).sum() / max((ser == 0).sum(), 1) - 1)])
    res = np.array(res)
    sw.append(dict(本当に空の割合_pct=100 * miss, 平均行数=round(res[:, 0].mean(), 1), 違う地域が入る行_平均pct=round(res[:, 2].mean(), 1), 東日本の件数の水増し_平均pct=round(res[:, 3].mean(), 1), 東日本の件数の水増し_最大pct=round(res[:, 3].max(), 1)))
SW = pd.DataFrame(sw); SW.to_csv(RES / "sweep_true_missing.csv", index=False, encoding="utf-8-sig"); print(SW.to_string())

J = dict(rows_truth=N, depts=len(DEPTS), sheet_rows=int(len(a)), merged_ranges=len(ws.merged_cells.ranges), total_sales=TOT,
         true_missing_region=int(truth["地域"].isna().sum()), omitted_category_cells=int(S.loc[0, "商品区分が空"]), blank_dept_cells=int(S.loc[0, "部門が空"]),
         columns_as_read=list(map(str, raw.columns)), ways=S.to_dict(orient="records"), sweep=sw)
json.dump(J, open(RES / "a474_fictional.json", "w"), ensure_ascii=False, indent=1)

# ---- 図3
fig, axs = plt.subplots(1, 2, figsize=(12, 4.8))
lab = ["①そのまま\n読む", "②全部の列を\n下に埋める", "②'空行を落とし\nてから埋める", "②''小計・合計も\n落として埋める", "③列ごとに\n決める"]
x = np.arange(5); w = 0.26
for k, (col, colr, nm) in enumerate([("部門が正しい_pct", BLUE, "部門"), ("商品区分が正しい_pct", ORANGE, "商品区分"), ("地域が正しい_pct", GREEN, "地域")]):
    axs[0].bar(x + (k - 1) * w, S[col], w, color=colr, label=nm)
    for i, v in enumerate(S[col]): axs[0].text(i + (k - 1) * w, v + 1.5, f"{v:.0f}", ha="center", fontsize=8)
axs[0].set_xticks(x); axs[0].set_xticklabels(lab, fontsize=8); axs[0].set_ylim(0, 122); axs[0].set_ylabel("正しい分類に戻せた明細の行（%）")
axs[0].legend(ncol=3, fontsize=9, frameon=False, loc="upper left"); axs[0].set_title("分類が正しく戻った行の割合", loc="left", fontsize=11)
axs[1].bar(x - 0.2, S["売上の総合計_対正解pct"], 0.4, color=GRAY, label="表全体を合計した売上")
axs[1].bar(x + 0.2, S["部門別に集計できた売上_pct"], 0.4, color=BLUE, label="部門別に集計したときの売上の合計")
for i in range(5):
    axs[1].text(i - 0.2, S["売上の総合計_対正解pct"][i] + 4, f"{S['売上の総合計_対正解pct'][i]:.0f}", ha="center", fontsize=8)
    axs[1].text(i + 0.2, S["部門別に集計できた売上_pct"][i] + 4, f"{S['部門別に集計できた売上_pct'][i]:.0f}", ha="center", fontsize=8)
axs[1].axhline(100, color=INK, lw=0.8, ls="--"); axs[1].set_xticks(x); axs[1].set_xticklabels(lab, fontsize=8)
axs[1].set_ylim(0, S["売上の総合計_対正解pct"].max() * 1.3); axs[1].set_ylabel("正解を100としたとき"); axs[1].legend(fontsize=8.5, frameon=False, loc="upper right")
axs[1].set_title("合計は正解の何%になるか", loc="left", fontsize=11)
fig.suptitle(f"架空の集計表（明細{N}行）を、読み方を変えて読んだとき", x=0.01, ha="left", fontsize=13); fig.tight_layout()
save(fig, "a474_fictional_three_ways.png", "架空データ（乱数の種474）。結合セル・省略された見出し・小計・空行のある Excel を openpyxl で作り、pandas で読んだ結果")
