"""04 図：ずれの大きさ・家電の分類変更・時間帯・移動平均・テストの表・ダッシュボード。"""
import os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import lib

ROOT = lib.ROOT; RES = os.path.join(ROOT, "results"); FIG = os.path.join(ROOT, "figures")
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False
C_PUB, C_SIM, C_GOOD, C_BAD = "#2b6cb0", "#d97706", "#2f855a", "#c53030"

mag = pd.read_csv(os.path.join(RES, "B_error_magnitude.csv"))
short = {"A1": "品目の合計行まで足す", "A2": "分類変更の前後を両方足す", "A3": "祝日の表をそのまま JOIN", "A4": "前年比を整数で割る",
         "A5": "年度を暦年で切る", "A6": "12か月そろわない月も出す", "B1": "支払いを JOIN して足す", "B2": "支払い＋発送を JOIN",
         "B3": "値引き NULL を引く", "B4": "値引きの平均で NULL を除く", "B5": "NOT IN と NULL", "B6": "日ごとの人数を足す",
         "B7": "明細行を人数として数える", "B8": "UTC のまま月に分ける", "B9": "BETWEEN で 12/31 を落とす", "B10": "LAST_VALUE の既定の範囲",
         "B11": "行のない日を飛ばした移動平均", "B12": "購入率を整数で割る", "B13": "日ごとの率を平均する", "B14": "返品を注文番号だけで JOIN",
         "B15": "キャンセルを除き忘れ"}
json.dump(short, open(os.path.join(RES, "short_labels.json"), "w"), ensure_ascii=False, indent=1)

# 図1 ずれの大きさ
m = mag.copy(); m["lab"] = [f"{i} {short[i]}" for i in m.id]
m["show"] = m.total_err_pct
m = m.iloc[::-1]
fig, ax = plt.subplots(figsize=(10, 8.4))
cols = [C_PUB if p == "公開" else C_SIM for p in m.part]
ax.barh(m.lab, m.show, color=cols)
for y, (v, kw) in enumerate(zip(m.show, m.keys_wrong_or_missing_pct)):
    ax.text(v + (4 if v >= 0 else -4), y, f"{v:+.1f}%", va="center", ha="left" if v >= 0 else "right", fontsize=9)
ax.axvline(0, color="#333", lw=0.8)
ax.set_xlim(-140, 370)
ax.set_xlabel("誤り版の合計 ÷ 正しい合計 − 1（%）　※率・平均・日数はその値の合計で比べた")
ax.set_title("21個の「よくある誤り」で、集計の合計はどれだけずれるか\n青＝公開データ（商業動態統計）、橙＝架空のネット書店の注文データ（SQLite）", fontsize=12)
ax.grid(axis="x", alpha=0.3)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig1_error_magnitude.png"), dpi=150); plt.close()

# 図2 家電大型専門店：分類の変更
a2 = pd.read_csv(os.path.join(RES, "G_A2_appliance_series.csv"), index_col=0)
a2.index = pd.to_datetime(a2.index + "-01")
fig, ax = plt.subplots(figsize=(10, 4.8))
ax.plot(a2.index, a2.naive / 1e3, color=C_BAD, lw=1.6, label="誤り：「商品販売額」以外の品目をすべて足す")
ax.plot(a2.index, a2.correct / 1e3, color=C_GOOD, lw=2.2, label="正しい：いちばん細かい単位（旧分類6品目）だけ足す")
ax.plot(a2.index, a2.published_total / 1e3, color="#222", lw=1, ls="--", label="公表の「商品販売額」")
ax.axvline(pd.Timestamp("2021-01-01"), color="#888", ls=":")
ax.text(pd.Timestamp("2021-03-01"), 255, "2021年1月から細かい分類が加わる（旧分類と並んで公表される）", fontsize=9, va="bottom")
ax.set_ylabel("販売額（十億円）"); ax.set_title("家電大型専門店の月次販売額：分類が増えた月から、単純に足すと約1.6倍になる", fontsize=12)
ax.legend(fontsize=9, loc="upper left"); ax.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig2_classification_change.png"), dpi=150); plt.close()

# 図3 時間帯
b8 = pd.read_csv(os.path.join(RES, "G_B8_month_utc_vs_jst.csv"), index_col=0)
b8 = b8.fillna(0)
diff = (b8.utc - b8.jst) / b8.jst.replace(0, np.nan) * 100
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw=dict(width_ratios=[2.2, 1]))
ax = axs[0]
idx = [i for i in b8.index]
vals = [(b8.utc[i] - b8.jst[i]) / 1e6 for i in idx]
ax.bar(idx, vals, color=[C_BAD if v < 0 else C_SIM for v in vals])
ax.axhline(0, color="#333", lw=0.8)
ax.set_ylabel("UTC で分けた売上 − 日本時間で分けた売上（百万円）")
ax.set_title("UTC のまま月に分けると、月初の0〜9時（日本時間）の注文が前の月に入る", fontsize=11)
ax.tick_params(axis="x", rotation=60, labelsize=8); ax.grid(axis="y", alpha=0.3)
s = json.load(open(os.path.join(RES, "summary.json")))
ax = axs[1]
ax.bar(["BETWEEN\n'12-01' AND '12-31'", "＞＝'12-01' AND\n＜'2026-01-01'"], [s["b9"]["bad"] / 1e6, s["b9"]["good"] / 1e6], color=[C_BAD, C_GOOD])
for x, v in enumerate([s["b9"]["bad"] / 1e6, s["b9"]["good"] / 1e6]):
    ax.text(x, v, f"{v:.1f}", ha="center", va="bottom", fontsize=10)
ax.set_ylim(55, 67); ax.set_ylabel("12月の売上（百万円）")
ax.set_title("時刻つきの列に BETWEEN を使うと\n12/31 の0時以降が抜ける", fontsize=11)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig3_timezone_boundary.png"), dpi=150); plt.close()

# 図4 移動平均と行のない日
b11 = pd.read_csv(os.path.join(RES, "G_B11_moving_average.csv"), index_col=0)
b11.index = pd.to_datetime(b11.index)
fig, axs = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True)
for ax, (a, b, t) in zip(axs, [("2025-03-08", "2025-03-30", "3/15・3/16 に注文なし"), ("2025-07-01", "2025-07-20", "7/8 に注文なし")]):
    x = b11.loc[a:b]
    ax.plot(x.index, x.rows_based / 1e6, "o-", color=C_BAD, ms=3, label="誤り：ある行だけで ROWS 6 PRECEDING")
    ax.plot(x.index, x.calendar_based / 1e6, "o-", color=C_GOOD, ms=3, label="正しい：日付の表に LEFT JOIN して 0 を入れる")
    ax.set_title(t, fontsize=11); ax.grid(alpha=0.3); ax.tick_params(axis="x", rotation=45, labelsize=8)
axs[0].set_ylabel("日次売上の7日移動平均（百万円）")
axs[1].legend(fontsize=8.5, loc="lower left")
fig.suptitle("注文のない日は行ができない。行の数で7日を数えると、止まった日が「なかったこと」になる", fontsize=12)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig4_window_missing_days.png"), dpi=150); plt.close()

# 図5 テストの表
cm = pd.read_csv(os.path.join(RES, "A_catch_matrix_sqlite.csv"), index_col=0)
pl = pd.read_csv(os.path.join(RES, "D_catch_matrix_plain_fixture.csv"), index_col=0)
cm["T5'：境目のない答え合わせデータ"] = pl[lib.TESTS[4]]
def code(x):
    if isinstance(x, str):
        return 1 if x == "True" else (0 if x == "False" else -1)
    if x is None or (isinstance(x, float) and np.isnan(x)): return -1
    return 1 if bool(x) else 0
M = cm.map(code)
fig, ax = plt.subplots(figsize=(11.5, 8.8))
cmap = matplotlib.colors.ListedColormap(["#e2e8f0", "#fde7e7", "#2f855a"])
ax.imshow(M.values + 1, cmap=cmap, vmin=0, vmax=2, aspect="auto")
XL = ["T1\n照合", "T2\n粒度\n（キーの重複）", "T3\nNULL", "T4\n期間・キー\nの網羅", "T5\n小さなデータで\n答え合わせ", "T6\n値の範囲・型", "T7\nエンジン間\nの一致", "T5'\n境目のない\n答え合わせデータ"]
ax.set_xticks(range(M.shape[1])); ax.set_xticklabels(XL, fontsize=8.5)
ax.set_yticks(range(M.shape[0])); ax.set_yticklabels([f"{i} {short[i]}" for i in M.index], fontsize=8.5)
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        v = M.values[i, j]
        ax.text(j, i, "見つけた" if v == 1 else ("—" if v == -1 else "×"), ha="center", va="center", fontsize=7.5, color="white" if v == 1 else "#555")
ax.axvline(6.5, color="#333", lw=1.5)
ax.set_title("どのテストで誤りが見つかったか（主は SQLite、他のエンジンは DuckDB）\n緑＝見つけた、×＝見つからない、—＝使えない（足し上げられない指標は照合しない）", fontsize=11.5)
plt.tight_layout(); plt.savefig(os.path.join(FIG, "fig5_test_catch_matrix.png"), dpi=150); plt.close()
print("figs done")
