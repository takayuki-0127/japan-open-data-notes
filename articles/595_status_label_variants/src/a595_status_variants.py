"""595 「完了」「済」「済み」のように表記の揺れたステータス列をそのまま GROUP BY すると、何%の行が別のグループに分かれるのか。
架空の案件表（2024〜2025年、表記ゆれ・全角半角・空白を混ぜる。seed 595）"""
import json
import unicodedata
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from common import DATA, SQL, RES, save, BLUE, ORANGE, GRAY, INK, GREEN

SRC = "出典：架空の案件表（作成者が乱数で作成、seed 595）"
rng = np.random.default_rng(595)
N = 24_000
created = pd.to_datetime("2024-01-01") + pd.to_timedelta(rng.integers(0, 731, N), unit="D")
age = (pd.Timestamp("2026-01-01") - created).days.values
# 本当の状態（古い案件ほど完了している）
p_done = np.clip(0.35 + age / 731 * 0.55, 0, 0.92)
u = rng.random(N)
true = np.where(u < p_done, "完了", np.where(u < p_done + 0.05, "取消", np.where(u < p_done + 0.09, "保留",
                np.where(u < p_done + 0.09 + (1 - p_done - 0.09) * 0.6, "対応中", "未着手"))))
# 表記ゆれ：2025年7月から入力画面が変わり、完了を「済」で入れる人が増えた
new_ui = created >= "2025-07-01"
VAR = {"完了": (["完了", "完了済み", "済", "済み", "完了 ", "完了　"], [0.86, 0.04, 0.03, 0.02, 0.03, 0.02],
                [0.25, 0.03, 0.55, 0.12, 0.03, 0.02]),
       "対応中": (["対応中", "作業中", "対応中 ", "進行中"], [0.85, 0.07, 0.04, 0.04], None),
       "未着手": (["未着手", "新規", "未対応", "未着手　"], [0.82, 0.08, 0.07, 0.03], None),
       "保留": (["保留", "保留中", "ﾎﾘｭｳ"], [0.9, 0.08, 0.02], None),
       "取消": (["取消", "取り消し", "キャンセル", "ｷｬﾝｾﾙ", "取消 "], [0.6, 0.12, 0.18, 0.06, 0.04], None)}
status = np.empty(N, dtype=object)
for k, (vs, p_old, p_new) in VAR.items():
    idx = np.where(true == k)[0]
    for i in idx:
        p = p_new if (p_new is not None and new_ui[i]) else p_old
        status[i] = vs[rng.choice(len(vs), p=p)]
tasks = pd.DataFrame({"task_id": np.arange(1, N + 1), "created_on": created, "status": status})
tasks = tasks.sort_values(["created_on", "task_id"]).reset_index(drop=True)
tasks["task_id"] = np.arange(1, N + 1)
tasks.to_csv(DATA / "tasks.csv", index=False, date_format="%Y-%m-%d")
# 対応表（空白を除いた後の表記 → 正規の名前）。半角カナもここで受ける
smap = pd.DataFrame([(v.strip().replace("　", ""), k) for k, (vs, _, _) in VAR.items() for v in vs], columns=["variant", "canonical"]).drop_duplicates()
smap.to_csv(DATA / "status_map.csv", index=False)

# ---- 段階的にそろえる ----
canon = tasks.status.map(lambda s: s.replace("　", " ").strip())
tasks["s0"] = tasks.status
tasks["s1"] = canon                                          # 空白を除く
tasks["s2"] = tasks.s1.map(lambda s: unicodedata.normalize("NFKC", s))   # 全角・半角をそろえる（NFKC）
mp = dict(zip(smap.variant, smap.canonical)); mp.update({unicodedata.normalize("NFKC", k): v for k, v in mp.items()})
tasks["s3"] = tasks.s2.map(lambda s: mp.get(s, s))           # 同じ意味の別表記を対応表でそろえる
truth = tasks.s3                                              # 対応表は全部の表記を持つので、これが正解
steps = {"s0": "そのまま", "s1": "空白を除く", "s2": "＋全角・半角をそろえる", "s3": "＋対応表で同じ意味をまとめる"}
CANON = ["未着手", "対応中", "保留", "完了", "取消"]
rows = []
for s, lab in steps.items():
    rows.append({"step": lab, "n_groups": int(tasks[s].nunique()),
                 "rows_not_canonical_pct": round(float((~tasks[s].isin(CANON)).mean() * 100), 2),
                 "done_rate_pct": round(float((tasks[s] == "完了").mean() * 100), 2)})
st = pd.DataFrame(rows); st.to_csv(RES / "by_step.csv", index=False)

tasks["month"] = tasks.created_on.dt.to_period("M")
mon = tasks.groupby("month").apply(lambda x: pd.Series({"done_raw": (x.s0 == "完了").mean() * 100, "done_true": (x.s3 == "完了").mean() * 100, "n": len(x)}))
mon.to_csv(RES / "monthly_done_rate.csv", float_format="%.3f")
counts = tasks.groupby(["s3", "s0"]).size().rename("rows").reset_index().rename(columns={"s3": "canonical", "s0": "raw"})
counts.to_csv(RES / "variant_counts.csv", index=False)
pre = mon[mon.index < pd.Period("2025-07", "M")]; post = mon[mon.index >= pd.Period("2025-07", "M")]
res = {"n_rows": N, "steps": rows,
       "done_true_pct": round(float((truth == "完了").mean() * 100), 2),
       "done_rows_by_variant": counts[counts.canonical == "完了"].set_index("raw").rows.to_dict(),
       "monthly_gap_pt": {"before_2025_07_mean": round(float((pre.done_true - pre.done_raw).mean()), 1),
                          "from_2025_07_mean": round(float((post.done_true - post.done_raw).mean()), 1),
                          "max": round(float((mon.done_true - mon.done_raw).max()), 1)},
       "raw_done_rate_2025_06_vs_07": [round(float(mon.loc[pd.Period("2025-06", "M"), "done_raw"]), 1), round(float(mon.loc[pd.Period("2025-07", "M"), "done_raw"]), 1)],
       "true_done_rate_2025_06_vs_07": [round(float(mon.loc[pd.Period("2025-06", "M"), "done_true"]), 1), round(float(mon.loc[pd.Period("2025-07", "M"), "done_true"]), 1)],
       "looks_same_but_differs": {"完了 (末尾半角空白)": int((tasks.s0 == "完了 ").sum()), "完了　(末尾全角空白)": int((tasks.s0 == "完了　").sum()),
                                  "ﾎﾘｭｳ・ｷｬﾝｾﾙ (半角カナ)": int(tasks.s0.isin(["ﾎﾘｭｳ", "ｷｬﾝｾﾙ"]).sum())}}

# ---- SQL（DuckDB、1スレッド） ----
con = duckdb.connect(); con.execute("SET threads=1")
con.execute(f"CREATE TABLE tasks AS SELECT * FROM read_csv('{DATA / 'tasks.csv'}', header=true, all_varchar=true)")
con.execute(f"CREATE TABLE status_map AS SELECT * FROM read_csv('{DATA / 'status_map.csv'}', header=true, all_varchar=true)")
sq = con.execute((SQL / "02_status_duckdb.sql").read_text()).df()
sq.to_csv(RES / "sql_summary.csv", index=False, float_format="%.6f")
r = sq.iloc[0]
res["sql"] = {k: (int(r[k]) if "groups" in k or "unmapped" in k else round(float(r[k]) * 100, 2)) for k in sq.columns}
res["sql_match_python"] = bool(r.groups_raw == rows[0]["n_groups"] and r.groups_cleaned == rows[1]["n_groups"] and r.groups_mapped == 5
                               and abs(r.done_rate_raw * 100 - rows[0]["done_rate_pct"]) < 0.01 and abs(r.done_rate_mapped * 100 - rows[3]["done_rate_pct"]) < 0.01
                               and int(r.unmapped_rows) == 0)
json.dump(res, open(RES / "a595_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))

# ---- 図 ----
fig, ax = plt.subplots(figsize=(8.5, 4.4))
x = np.arange(len(st))
b = ax.bar(x, st.n_groups, color=[ORANGE, GRAY, GRAY, BLUE])
for i, r_ in st.iterrows():
    ax.text(i, r_.n_groups + 0.4, f"{r_.n_groups}グループ\n正規の名前でない行 {r_.rows_not_canonical_pct:.1f}%", ha="center", va="bottom", fontsize=9)
ax.set_xticks(x, ["そのまま", "空白を除く", "＋全角・半角を\nそろえる", "＋対応表で\n同じ意味をまとめる"]); ax.set_ylim(0, st.n_groups.max() * 1.35)
ax.set_ylabel("GROUP BY で出てくるグループの数")
ax.set_title("ステータスは5種類なのに、そのまま数えると22グループに分かれる")
save(fig, "a595_groups.png", SRC)

dv = counts[counts.canonical == "完了"].sort_values("rows")
fig, ax = plt.subplots(figsize=(8, 4.2))
labels = [s.replace(" ", "␣").replace("　", "□") for s in dv.raw]
ax.barh(range(len(dv)), dv.rows, color=[BLUE if s == "完了" else ORANGE for s in dv.raw])
ax.set_yticks(range(len(dv)), labels)
for i, v in enumerate(dv.rows):
    ax.text(v + 60, i, f"{v:,}行", va="center", fontsize=9)
ax.set_xlabel("行数"); ax.set_xlim(0, dv.rows.max() * 1.18)
ax.set_title("「完了」の意味で入っている表記（␣は半角空白、□は全角空白）")
save(fig, "a595_done_variants.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.2))
xm = mon.index.to_timestamp()
ax.plot(xm, mon.done_true, color=BLUE, lw=2.4, label="表記をそろえて数えた完了率")
ax.plot(xm, mon.done_raw, color=ORANGE, lw=2, label="「完了」とぴったり同じ行だけ数えた完了率")
ax.axvline(pd.Timestamp("2025-07-01"), color=GRAY, ls="--", lw=1)
ax.text(pd.Timestamp("2025-07-08"), 92, "入力画面の変更\n（「済」が増えた）", fontsize=9, color=INK, va="top")
ax.set_ylabel("登録月ごとの完了率（%）"); ax.set_ylim(0, 100)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y/%-m"))
ax.set_title("表記が変わった月から、完了率が急に下がったように見える")
ax.legend(frameon=False, fontsize=9, loc="lower left")
save(fig, "a595_monthly.png", SRC)
