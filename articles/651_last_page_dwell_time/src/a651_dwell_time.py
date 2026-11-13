"""651 ページの滞在時間を「次のページを開いた時刻との差」で測ると、最後に見たページの分はどれだけ抜け落ちるのか

架空のサイト（8種類のページ）の閲覧ログ。各ページビューに本当の滞在時間（作成者が置いた値）を持たせ、
時刻は「前のページの時刻＋本当の滞在時間」で作る。ログに残るのは時刻だけ。
  D0 本当の滞在時間
  D1 次のページとの時刻の差。最後のページは測れないので除く（NULL を落とす）
  D2 同じ差で、最後のページを0秒とみなす
  D3 同じ差で、最後のページには、そのページの「最後でないとき」の平均を入れる
ページごとの平均・セッションの合計時間・ページの順位を比べる。DuckDB（1スレッド）と pandas の一致を確かめる。seed 651。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from scipy import stats
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

DATA.mkdir(exist_ok=True)
SRC = "出典：架空の閲覧ログ（作成者が乱数で作成、seed 651）"
rng = np.random.default_rng(651)
N_SESS = 20000
PAGES = ["トップ", "一覧", "検索結果", "商品詳細", "記事", "よくある質問", "カート", "完了"]
# 本当の平均滞在時間（秒）と、そのページで離脱する確率
mean_dwell = {"トップ": 25, "一覧": 35, "検索結果": 30, "商品詳細": 90, "記事": 180, "よくある質問": 120, "カート": 60, "完了": 40}
exit_p = {"トップ": 0.30, "一覧": 0.20, "検索結果": 0.25, "商品詳細": 0.30, "記事": 0.65, "よくある質問": 0.60, "カート": 0.25, "完了": 0.95}
# 離脱するときの滞在時間の倍率（記事は読み切ってから閉じる、トップや検索結果はすぐ閉じる）
exit_mult = {"トップ": 0.4, "一覧": 0.7, "検索結果": 0.5, "商品詳細": 1.0, "記事": 1.6, "よくある質問": 1.4, "カート": 1.0, "完了": 1.0}
nxt = {"トップ": ["一覧", "検索結果", "記事", "よくある質問"], "一覧": ["商品詳細", "一覧", "検索結果"],
       "検索結果": ["商品詳細", "検索結果", "記事"], "商品詳細": ["カート", "一覧", "商品詳細", "よくある質問"],
       "記事": ["記事", "商品詳細", "トップ"], "よくある質問": ["よくある質問", "トップ"], "カート": ["完了", "商品詳細"], "完了": ["トップ"]}
rows = []
t0 = pd.Timestamp("2025-06-01").value // 10**9
for s in range(N_SESS):
    page = rng.choice(["トップ", "検索結果", "記事"], p=[0.5, 0.25, 0.25])
    ts = t0 + int(rng.integers(0, 30 * 86400)); seq = 1
    while True:
        last = rng.random() < exit_p[page] or seq >= 30
        m = mean_dwell[page] * (exit_mult[page] if last else 1.0)
        d = int(max(2, round(rng.lognormal(np.log(m) - 0.32, 0.8))))
        rows.append((s + 1, seq, page, ts, d, last))
        if last:
            break
        ts += d; page = rng.choice(nxt[page]); seq += 1
PV = pd.DataFrame(rows, columns=["session_id", "seq", "page", "ts_epoch", "true_dwell", "is_last"])
PV["ts"] = pd.to_datetime(PV.ts_epoch, unit="s")
PV[["session_id", "seq", "page", "ts"]].assign(ts=PV.ts.dt.strftime("%Y-%m-%d %H:%M:%S")).to_csv(DATA / "pageviews.csv", index=False)
PV[["session_id", "seq", "true_dwell"]].to_csv(RES / "true_dwell.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("pageviews", PV[["session_id", "seq", "page", "ts"]])
q = [x for x in (SQL / "02_dwell_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
dw = con.execute(q[0]).df()
con.register("dwell", dw)
bypage_sql = con.execute(q[1]).df().set_index("page")
# pandas
PV = PV.sort_values(["session_id", "seq"]).reset_index(drop=True)
PV["d1"] = PV.groupby("session_id").ts_epoch.shift(-1) - PV.ts_epoch
assert np.allclose(dw.dwell_sec.fillna(-1).values, PV.d1.fillna(-1).values)
assert (PV.d1.dropna() == PV.true_dwell[PV.d1.notna()]).all()  # 最後以外は本当の値と一致
PV["d2"] = PV.d1.fillna(0)
nonlast_mean = PV[PV.d1.notna()].groupby("page").d1.mean()
PV["d3"] = PV.d1.fillna(PV.page.map(nonlast_mean))
g = PV.groupby("page")
bp = pd.DataFrame({"views": g.size(), "exit_share": g.is_last.mean(), "D0_true": g.true_dwell.mean(),
                   "D1_drop_last": g.d1.mean(), "D2_last_zero": g.d2.mean(), "D3_impute": g.d3.mean()}).reindex(PAGES)
assert np.allclose(bp.D1_drop_last, bypage_sql.loc[PAGES, "avg_drop_last"]) and np.allclose(bp.D2_last_zero, bypage_sql.loc[PAGES, "avg_last_as_zero"])
for c in ["D1_drop_last", "D2_last_zero", "D3_impute"]:
    bp[c + "_pct"] = (bp[c] / bp.D0_true - 1) * 100
bp.round(3).to_csv(RES / "by_page.csv")
ss = PV.groupby("session_id").agg(true=("true_dwell", "sum"), d2=("d2", "sum"), d3=("d3", "sum"), n=("seq", "size"))
one_page = float((ss.n == 1).mean() * 100)
share_time_last = float(PV[PV.is_last].true_dwell.sum() / PV.true_dwell.sum() * 100)
rk = lambda c: bp[c].rank(ascending=False).astype(int)
out = {"sessions": N_SESS, "pageviews": len(PV), "one_page_sessions_pct": round(one_page, 1),
       "share_of_true_time_on_last_page_pct": round(share_time_last, 1),
       "session_total_true_mean_sec": round(float(ss.true.mean()), 1), "session_total_last_zero_mean_sec": round(float(ss.d2.mean()), 1),
       "session_total_missing_pct": round(float((1 - ss.d2.sum() / ss.true.sum()) * 100), 1),
       "session_total_impute_pct": round(float((ss.d3.sum() / ss.true.sum() - 1) * 100), 1),
       "by_page": {p: {k: round(float(bp.loc[p, k]), 3 if k == "exit_share" else 1) for k in ["exit_share", "D0_true", "D1_drop_last", "D2_last_zero", "D3_impute",
                                                               "D1_drop_last_pct", "D2_last_zero_pct", "D3_impute_pct"]} for p in PAGES},
       "rank_true": rk("D0_true").to_dict(), "rank_last_zero": rk("D2_last_zero").to_dict(), "rank_drop_last": rk("D1_drop_last").to_dict(),
       "spearman_true_vs_last_zero": round(float(stats.spearmanr(bp.D0_true, bp.D2_last_zero).correlation), 3)}
json.dump(out, open(RES / "a651_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：ページごとの平均滞在時間
fig, ax = plt.subplots(figsize=(8.5, 4))
x = np.arange(len(PAGES)); w = 0.2
for i, (c, col, lab) in enumerate([("D0_true", GRAY, "本当の滞在時間"), ("D1_drop_last", BLUE, "差で測る（最後のページは除く）"),
                                   ("D2_last_zero", ORANGE, "差で測る（最後のページは0秒）"), ("D3_impute", GREEN, "最後のページを平均で補う")]):
    ax.bar(x + (i - 1.5) * w, bp[c], w, color=col, label=lab)
ax.set_xticks(x); ax.set_xticklabels(PAGES, fontsize=9); ax.set_ylabel("平均の滞在時間（秒）")
ax.legend(frameon=False, fontsize=8.5); ax.set_title("離脱の多いページほど、0秒とみなすと短く出る。除いても補っても戻らない")
save(fig, "a651_by_page.png", SRC)
# 図2：離脱の割合と、0秒とみなしたときのずれ
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.scatter(bp.exit_share * 100, bp.D2_last_zero_pct, color=ORANGE, s=40, label="最後のページを0秒")
ax.scatter(bp.exit_share * 100, bp.D1_drop_last_pct, color=BLUE, s=40, marker="s", label="最後のページを除く")
for p in PAGES:
    ax.annotate(p, (bp.loc[p, "exit_share"] * 100, bp.loc[p, "D2_last_zero_pct"]), fontsize=8, xytext=(4, 2), textcoords="offset points")
ax.axhline(0, color=GRAY, lw=0.8); ax.set_xlabel("そのページで離脱した割合（%）"); ax.set_ylabel("本当の平均とのずれ（%）")
ax.legend(frameon=False, fontsize=9); ax.set_title("ずれは、そのページで離脱する割合と比例して大きくなる")
save(fig, "a651_exit_vs_bias.png", SRC)
# 図3：セッションの合計時間
fig, ax = plt.subplots(figsize=(8, 3.8))
bins = np.arange(0, 1500, 30)
ax.hist(ss.true.clip(upper=1490), bins=bins, color=LIGHT, label="本当の合計時間")
ax.hist(ss.d2.clip(upper=1490), bins=bins, histtype="step", color=ORANGE, lw=1.6, label="差で測った合計（最後は0秒）")
ax.set_xlabel("1セッションの合計時間（秒、1,490秒以上はまとめた）"); ax.set_ylabel("セッション数")
ax.legend(frameon=False, fontsize=9); ax.set_title(f"1ページだけのセッション（{one_page:.0f}%）は、測った合計が0秒になる")
save(fig, "a651_session_total.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
