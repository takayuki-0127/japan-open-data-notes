"""322 書いた記事は、何か月で「古い数字」になるのか（④ 振り返り R102）— その2：集計と図

使い方: python a322.py
  記事が使った統計の「次の公表の目安」と、(1) フォルダを作った日、(2) 予定表の公開予定日 を並べる。
  公開予定日が次の公表より後なら「公開のときには、もう次の数字が出ている」と数える。
  次の公表の目安は、例年の時期からの見込みを多く含む（data/candidates.csv の next 列に「推測」とあるもの）
"""
import os, re, json, datetime
import pandas as pd
import matplotlib.pyplot as plt
from common import group_of
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "..")
P = lambda *a: os.path.join(OUT, *a)
C = pd.read_csv(P("data", "candidates.csv"), dtype=str)
N = pd.read_csv(P("data", "new_articles_release.csv"), dtype=str).fillna("")
extra = []
for _, r in N.iterrows():
    for i in range(int(r.id_from), int(r.id_to) + 1):
        extra.append([str(i), r.stat, r.freq, r.next, ""])
C = pd.concat([C, pd.DataFrame(extra, columns=C.columns)], ignore_index=True).drop_duplicates("id")
F = pd.read_csv(P("data", "first_commit.csv"), dtype=str)
S = pd.read_csv(P("data", "schedule.csv"), dtype=str).fillna("")
D = C.merge(F, on="id", how="left").merge(S, on="id", how="left").fillna("")

def klass(r):
    if r.next.startswith("毎") and "年の値" not in r.next: return "毎月・毎週・毎日"
    f = r.freq
    if re.search(r"\d年ごと|数年ごと", f): return "数年ごと"
    if "四半期" in f or "年2回" in f: return "四半期・年2回"
    return "年に1回"
def next_date(s):
    """次の公表の目安 → 日付（月の初め。末・下旬は月末側に寄せる）。年しか分からないものは None"""
    if s.startswith("毎") and "年の値は1月" in s: return datetime.date(2027, 1, 15)
    if s.startswith("毎"): return None
    s = re.sub(r"（[^）]*）", "", s).split("・")[0]          # かっこの中（何年分か）と、2つ目の公表は見ない
    m = re.search(r"(20\d\d)年(\d+)(?:〜\d+)?月(末|下旬)?", s)
    if m:
        return datetime.date(int(m.group(1)), int(m.group(2)), 25 if m.group(3) else 1)
    m = re.search(r"(20\d\d)年春", s)
    if m: return datetime.date(int(m.group(1)), 4, 1)
    return None
D["klass"] = D.apply(klass, axis=1)
D["next_date"] = D.next.map(next_date)
D["guess"] = D.next.str.contains("推測")
dt = lambda s: datetime.date.fromisoformat(s) if s else None
D["first"] = D.first_commit.map(dt)
D["months_from_write"] = D.apply(lambda r: round((r.next_date - r["first"]).days / 30.44, 1) if r.next_date and r["first"] else None, axis=1)
D.loc[(D.klass == "毎月・毎週・毎日"), "months_from_write"] = 1.0      # 遅くとも1か月以内に次の数字が出る
D["group"] = D.id.map(lambda s: group_of((s if s[0] in "FT" else "%03d" % int(s)) + "_x"))
D.drop(columns=["first"]).to_csv(P("results", "articles.csv"), index=False)

ORDER = ["毎月・毎週・毎日", "四半期・年2回", "年に1回", "数年ごと"]
g = D.groupby("klass")
tab = pd.DataFrame({"記事": g.size(), "次の公表の月が分かる": g.next_date.apply(lambda x: x.notna().sum()) ,
                    "書いてから次の数字まで（月、中央値）": g.months_from_write.median(),
                    "6か月以内": g.months_from_write.apply(lambda x: (x.dropna() <= 6).mean()),
                    "12か月以内": g.months_from_write.apply(lambda x: (x.dropna() <= 12).mean())}).reindex(ORDER).round(3)
tab.loc["毎月・毎週・毎日", "次の公表の月が分かる"] = tab.loc["毎月・毎週・毎日", "記事"]
tab.to_csv(P("results", "by_frequency.csv"))
known = D[D.months_from_write.notna()]
bins = [-100, 1.5, 3, 6, 9, 12, 24, 1000]; labels = ["1か月以内", "〜3か月", "〜6か月", "〜9か月", "〜12か月", "〜24か月", "24か月超"]
dist = pd.cut(known.months_from_write, bins=bins, labels=labels).value_counts().reindex(labels)
dist.rename("記事").to_csv(P("results", "months_distribution.csv"))

# 公開の予定日と比べる（未公開で、次の公表の月が分かる記事）
def stale(plan, r):
    if not plan: return None
    if r.klass == "毎月・毎週・毎日": return None
    if r.next_date is None: return None
    return dt(plan) > r.next_date
U = D[(D.published == "") & ((D.plan_before != "") | (D.plan_after != ""))].copy()
U["stale_before"] = U.apply(lambda r: stale(r.plan_before, r), axis=1)
U["stale_after"] = U.apply(lambda r: stale(r.plan_after, r), axis=1)
U["held"] = (U.plan_after == "") & (U.plan_before != "")
U["lead_before"] = U.apply(lambda r: (r.next_date - dt(r.plan_before)).days if r.next_date and r.plan_before else None, axis=1)
U["lead_after"] = U.apply(lambda r: (r.next_date - dt(r.plan_after)).days if r.next_date and r.plan_after else None, axis=1)
cmpb = U[U.stale_before.notna()]
res = {"比べた記事（並べ替え前）": int(len(cmpb)), "並べ替え前：公開が次の公表より後": int(cmpb.stale_before.sum()),
       "うち保留にした記事": int(cmpb[cmpb.held].stale_before.sum()), "保留にした記事（比べた中）": int(cmpb.held.sum()),
       "並べ替え後も予定表にある記事": int(U[U.stale_after.notna()].shape[0]), "並べ替え後：公開が次の公表より後": int(U[U.stale_after.notna()].stale_after.sum())}
both = U[U.stale_before.notna() & U.stale_after.notna()]
res["両方にある記事"] = int(len(both)); res["両方にある記事：前に後だった"] = int(both.stale_before.sum()); res["両方にある記事：後も後"] = int(both.stale_after.sum())
res["両方にある記事：公開が早まった日数（中央値）"] = float((both.lead_after - both.lead_before).median())
res["年に1回の統計：並べ替え前の割合"] = round(float(cmpb[cmpb.klass == "年に1回"].stale_before.mean()), 3)
still = both[both.stale_after == True][["id", "stat", "next", "plan_before", "plan_after"]]
still.to_csv(P("results", "still_after_release.csv"), index=False)
U.drop(columns=["first"]).to_csv(P("results", "schedule_compare.csv"), index=False)
bk = cmpb.groupby("klass").stale_before.agg(["size", "sum", "mean"]).reindex(ORDER[1:]).round(3)
ak = U[U.stale_after.notna()].groupby("klass").stale_after.agg(["size", "sum", "mean"]).reindex(ORDER[1:]).round(3)
bk.join(ak, lsuffix="_前", rsuffix="_後").to_csv(P("results", "stale_by_frequency.csv"))
summary = dict(articles=int(len(D)), with_known_month=int(known.shape[0]), guess_share=round(float(D.guess.mean()), 3),
               klass={k: int(v) for k, v in D.klass.value_counts().items()}, months_median_all=float(known.months_from_write.median()),
               within6=round(float((known.months_from_write <= 6).mean()), 3), within12=round(float((known.months_from_write <= 12).mean()), 3),
               annual_median=float(tab.loc["年に1回", "書いてから次の数字まで（月、中央値）"]), schedule=res)
json.dump(summary, open(P("results", "summary.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1)); print(tab.to_string()); print(dist.to_string()); print(bk.join(ak, lsuffix="_前", rsuffix="_後")); print(still.to_string())

plt.rcParams["font.size"] = 10
# 図1：書いてから次の数字が出るまで
fig, ax = plt.subplots(figsize=(8.4, 4.2))
col = {"毎月・毎週・毎日": "#d04a3a", "四半期・年2回": "#f0a030", "年に1回": "#2c6fb7", "数年ごと": "#8a8a8a"}
bottom = pd.Series(0, index=labels)
for k in ORDER:
    v = pd.cut(known[known.klass == k].months_from_write, bins=bins, labels=labels).value_counts().reindex(labels).fillna(0)
    ax.bar(labels, v, bottom=bottom, color=col[k], label=k); bottom = bottom + v
for i, l in enumerate(labels): ax.text(i, bottom[l] + 2, str(int(bottom[l])), ha="center")
ax.set_ylabel("記事の数"); ax.legend(title="統計の公表の頻度", fontsize=9, frameon=False)
ax.set_title(f"記事を作ってから、使った統計の次の数字が出るまで（{len(known)}本）", fontsize=11)
fig.tight_layout(); fig.savefig(P("figures", "a322_months.png"), dpi=150); plt.close(fig)

# 図2：公開の予定日と次の公表（年に1回・数年ごと・四半期）
fig, axes = plt.subplots(1, 2, figsize=(10, 4.3), sharey=True)
for ax, col_, ttl in zip(axes, ["lead_before", "lead_after"], ["並べ替えの前（2026-11-12 朝の予定表）", "並べ替えの後"]):
    x = U[U[col_].notna() & (U.klass != "毎月・毎週・毎日")][col_] / 30.44
    x = x.clip(-9, 30)
    ax.hist(x[x < 0], bins=range(-9, 1), color="#d04a3a", label="公開のときには次の数字が出ている")
    ax.hist(x[x >= 0], bins=range(0, 31), color="#2c6fb7", label="公開のあとに次の数字が出る")
    ax.axvline(0, color="k", lw=0.8); ax.set_title(f"{ttl}\n次の数字が出たあとの公開：{int((x < 0).sum())}本 ／ {len(x)}本", fontsize=10)
    ax.set_xlabel("公開の予定日から次の公表までの月数（マイナスは公開が後）")
axes[0].set_ylabel("記事の数"); axes[1].legend(fontsize=8, frameon=False)
fig.tight_layout(); fig.savefig(P("figures", "a322_schedule.png"), dpi=150); plt.close(fig)

# 図3：頻度ごとの表
rows = [[k, str(int(tab.loc[k, "記事"])), ("1か月以内" if k == ORDER[0] else f"{tab.loc[k, '書いてから次の数字まで（月、中央値）']:.1f}か月"),
         ("—" if k == ORDER[0] else f"{tab.loc[k, '6か月以内'] * 100:.0f}%"), ("—" if k == ORDER[0] else f"{tab.loc[k, '12か月以内'] * 100:.0f}%")] for k in ORDER]
fig, ax = plt.subplots(figsize=(9, 2.6)); ax.axis("off")
tb = ax.table(cellText=rows, colLabels=["統計の公表の頻度", "記事", "作ってから次の数字まで（中央値）", "6か月以内に出る", "12か月以内に出る"], loc="center", cellLoc="center", colWidths=[0.22, 0.1, 0.3, 0.19, 0.19])
tb.auto_set_font_size(False); tb.set_fontsize(10); tb.scale(1, 1.8)
for (r_, c_), cell in tb.get_celld().items():
    if r_ == 0: cell.set_facecolor("#dfe8f3"); cell.set_text_props(weight="bold")
ax.set_title("統計の公表の頻度ごとに見た「次の数字が出るまで」", fontsize=11)
fig.tight_layout(); fig.savefig(P("figures", "a322_table.png"), dpi=150); plt.close(fig)
