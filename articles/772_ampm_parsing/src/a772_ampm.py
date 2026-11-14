"""772 「12:30 AM」のような午前午後の表記を読み違えると、時間帯別の件数はどれだけずれるのか

架空の受付ログ5万件（1日の中で、昼12時台と夜21時台に山があり、深夜0時台も少しある）。時刻は「hh:mm AM/PM」の12時間表記の文字で持つ。
3つの読み方で時間帯（0〜23時）ごとの件数を出す：
 正しい読み（12:xx AM は0時、12:xx PM は12時）／PM なら12を足すだけ（12:xx AM は12時、12:xx PM は24時になる）／AM・PM を見ない。
DuckDB（1スレッド）の結果と Python の結果の一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空の受付ログ（作成者が乱数で作成、seed 772）"
rng = np.random.default_rng(772)
N = 50_000
h = np.arange(24)
w = .3 + 1.6 * np.exp(-((h - 12.3) ** 2) / 3) + 2.2 * np.exp(-((h - 21) ** 2) / 4) + .6 * np.exp(-((h - 0) ** 2) / 1.5) + .6 * np.exp(-((h - 24) ** 2) / 1.5)
w /= w.sum()
hh = rng.choice(24, N, p=w); mm = rng.integers(0, 60, N)
h12 = np.where(hh % 12 == 0, 12, hh % 12); ap = np.where(hh < 12, "AM", "PM")
txt = [f"{a:02d}:{b:02d} {c}" for a, b, c in zip(h12, mm, ap)]
L = pd.DataFrame({"recv_id": np.arange(1, N + 1), "recv_time": txt})
DATA.mkdir(exist_ok=True); L.to_csv(DATA / "logs.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("logs", L)
q = "\n".join(l for l in (SQL / "02_hour_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
Q = con.execute(q).df()
# Python 側
ph = L.recv_time.str.slice(0, 2).astype(int); pm = L.recv_time.str.endswith("PM")
ok = np.where(ph == 12, 0, ph) + np.where(pm, 12, 0)
naive = ph + np.where(pm, 12, 0)
noap = ph
assert (ok == hh).all()
chk = pd.DataFrame({"hour_ok": ok, "hour_naive": naive, "hour_no_ampm": noap}).value_counts().sort_index()
qq = Q.set_index(["hour_ok", "hour_naive", "hour_no_ampm"]).n.sort_index()
assert (chk.to_numpy() == qq.to_numpy()).all() and (chk.index == qq.index).all()

H = pd.DataFrame({"hour": np.arange(25)})
for k, v in [("ok", ok), ("naive", naive), ("no_ampm", noap)]:
    H[k] = [int((v == x).sum()) for x in H.hour]
H.to_csv(RES / "by_hour.csv", index=False)
wrong_naive = int((naive != ok).sum()); wrong_noap = int((noap != ok).sum())
out = {"rows": N, "wrong_naive": wrong_naive, "wrong_naive_share": wrong_naive / N,
       "wrong_no_ampm": wrong_noap, "wrong_no_ampm_share": wrong_noap / N,
       "h0_ok": int(H.ok[0]), "h0_naive": int(H.naive[0]), "h12_ok": int(H.ok[12]), "h12_naive": int(H.naive[12]), "h24_naive": int(H.naive[24]),
       "h12_share_ok": float(H.ok[12] / N), "h12_share_naive": float(H.naive[12] / N),
       "peak_ok": int(H.ok[:24].idxmax()), "peak_no_ampm": int(H.no_ampm[:24].idxmax()),
       "evening_18_23_ok": int(H.ok[18:24].sum()), "evening_18_23_no_ampm": int(H.no_ampm[18:24].sum()),
       "am_share_ok": float(H.ok[:12].sum() / N), "am_share_no_ampm": float(H.no_ampm[:13].sum() / N),
       "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a772_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：PM に12を足すだけ
fig, ax = plt.subplots(figsize=(10, 4.6)); x = H.hour; w_ = .4
ax.bar(x - w_ / 2, H.ok, w_, color=BLUE, label="正しい読み")
ax.bar(x + w_ / 2, H.naive, w_, color=ORANGE, label="PM なら12を足すだけ")
for xx in [0, 12, 24]:
    ax.text(xx - w_ / 2, H.ok[xx] + 80, f"{H.ok[xx]:,}", ha="center", fontsize=8, color=BLUE)
    ax.text(xx + w_ / 2, H.naive[xx] + 80, f"{H.naive[xx]:,}", ha="center", fontsize=8, color=ORANGE)
ax.set_xticks(range(0, 25, 2)); ax.set_xlabel("時（24 はありえない時刻）"); ax.set_ylabel("件数"); ax.legend(frameon=False)
ax.set_title("12:xx AM が12時に、12:xx PM が「24時」に移る")
save(fig, "a772_naive.png", SRC)
# 図2：AM/PM を見ない
fig, ax = plt.subplots(figsize=(10, 4.6))
ax.plot(H.hour[:24], H.ok[:24], "o-", color=BLUE, label="正しい読み（0〜23時）")
ax.plot(H.hour[:13], H.no_ampm[:13], "s-", color=ORANGE, label="AM・PM を見ない（1〜12時）")
ax.set_xticks(range(0, 24, 2)); ax.set_xlabel("時"); ax.set_ylabel("件数"); ax.legend(frameon=False)
ax.set_title(f"AM・PM を見ないと、夜の山（{out['peak_ok']}時）が朝の{out['peak_no_ampm']}時に重なる")
save(fig, "a772_no_ampm.png", SRC)
# 図3：読み違えた件数
fig, ax = plt.subplots(figsize=(9, 4.6))
vals = [wrong_naive / N * 100, wrong_noap / N * 100]
b = ax.bar(["PM なら12を足すだけ\n（12時台だけ誤る）", "AM・PM を見ない\n（午後すべてと0時台を誤る）"], vals, color=[ORANGE, GREEN])
for bb, v, n in zip(b, vals, [wrong_naive, wrong_noap]): ax.text(bb.get_x() + bb.get_width() / 2, v + 1, f"{n:,}件（{v:.1f}%）", ha="center")
ax.set_ylabel("時を読み違えた件数の割合（%）"); ax.set_title("どちらの読み違いも、エラーにはならない")
save(fig, "a772_wrong.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
