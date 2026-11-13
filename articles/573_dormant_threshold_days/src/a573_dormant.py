"""573 会員の「休眠」を最終購入から90日で切るか180日で切るかで、休眠の人数と「復活」の割合はどれだけ変わるのか（架空の会員、seed 573）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

rng = np.random.default_rng(573)
SRC = "架空の会員と購入履歴（作成者が乱数で作成、seed 573）"
START, EVAL, END = pd.Timestamp("2023-01-01"), pd.Timestamp("2025-06-30"), pd.Timestamp("2025-12-31")
N = 30000
# 会員ごとの買う間隔（平均日数）：よく買う人〜たまに買う人。離れる時点（見えない）も持たせる
cyc = rng.choice(["30日ごと", "60日ごと", "120日ごと"], N, p=[.35, .4, .25])
mean_gap = pd.Series(cyc).map({"30日ごと": 30, "60日ごと": 60, "120日ごと": 120}).values * rng.uniform(.7, 1.3, N)
join = START + pd.to_timedelta(rng.integers(0, 700, N), "D")
life = rng.exponential(900, N)                         # 入会から離れるまでの日数（平均900日）
churn_at = join + pd.to_timedelta(life.round(), "D")
rows = []
for i in range(N):
    t = join[i]; stop = min(churn_at[i], END)
    while t <= stop:
        rows.append((i + 1, t)); t = t + pd.Timedelta(days=max(1, round(rng.gamma(2.0, mean_gap[i] / 2.0))))
buy = pd.DataFrame(rows, columns=["member_id", "bought_on"])
buy.to_csv(DATA / "purchases.csv", index=False, date_format="%Y-%m-%d")
mem = pd.DataFrame({"member_id": np.arange(1, N + 1), "cycle": cyc, "joined_on": join, "left_on": churn_at})
mem[["member_id", "cycle", "joined_on"]].to_csv(DATA / "members.csv", index=False, date_format="%Y-%m-%d")

past = buy[buy.bought_on <= EVAL]
last = past.groupby("member_id").bought_on.max()
mem = mem.set_index("member_id").join(last.rename("last_buy"))
mem = mem[mem.last_buy.notna()].copy()        # 判定日までに1回以上買った会員
mem["days_since"] = (EVAL - mem.last_buy).dt.days
mem["gone"] = mem.left_on <= EVAL             # 本当にもう離れている（見えない正解）
fut = buy[(buy.bought_on > EVAL) & (buy.bought_on <= EVAL + pd.Timedelta(days=180))].member_id.unique()
mem["back"] = mem.index.isin(fut)            # 判定日のあと180日以内に買った
# 本人の買う間隔の中央値（判定日までの履歴から）
g = past.sort_values(["member_id", "bought_on"]).groupby("member_id").bought_on.diff().dt.days
med = g.groupby(past.sort_values(["member_id", "bought_on"]).member_id).median()
mem["own_med"] = med.reindex(mem.index)

TH = [30, 60, 90, 120, 180, 270, 365]
out = []
for th in TH:
    d = mem.days_since > th
    out.append({"days": th, "dormant": int(d.sum()), "dormant_pct": round(d.mean() * 100, 2),
                "revive_pct": round(mem.loc[d, "back"].mean() * 100, 2),
                "false_dormant": int((d & ~mem.gone).sum()), "missed_gone": int((~d & mem.gone).sum())})
T = pd.DataFrame(out); T.to_csv(RES / "by_threshold.csv", index=False)
# 本人の間隔の3倍（履歴が2回以上の人。1回だけの人は180日）で切る
own_th = (mem.own_med * 3).fillna(180).clip(lower=30)
dp = mem.days_since > own_th
own = {"dormant": int(dp.sum()), "revive_pct": round(mem.loc[dp, "back"].mean() * 100, 2),
       "false_dormant": int((dp & ~mem.gone).sum()), "missed_gone": int((~dp & mem.gone).sum())}
seg = []
for c in ["30日ごと", "60日ごと", "120日ごと"]:
    m = mem[mem.cycle == c]
    for lab, d in [("90日", m.days_since > 90), ("180日", m.days_since > 180), ("本人の間隔×3", m.days_since > own_th[m.index])]:
        seg.append({"cycle": c, "rule": lab, "members": len(m), "dormant_pct": round(d.mean() * 100, 2),
                    "false_dormant_pct_of_active": round((d & ~m.gone).sum() / (~m.gone).sum() * 100, 2),
                    "missed_pct_of_gone": round((~d & m.gone).sum() / max(1, m.gone.sum()) * 100, 2),
                    "revive_pct": round(m.loc[d, "back"].mean() * 100, 2)})
SG = pd.DataFrame(seg); SG.to_csv(RES / "by_cycle.csv", index=False)

# SQL（DuckDB、1スレッド）：90日と180日の休眠人数を出して Python と突き合わせる
con = duckdb.connect(); con.execute("SET threads=1")
con.execute(f"CREATE TABLE purchases AS SELECT * FROM read_csv_auto('{DATA/'purchases.csv'}')")
sq = con.execute((SQL / "02_dormant_duckdb.sql").read_text()).df()
chk = bool(int(sq.dormant_90[0]) == T.set_index("days").loc[90, "dormant"] and int(sq.dormant_180[0]) == T.set_index("days").loc[180, "dormant"])
sq.to_csv(RES / "sql_check.csv", index=False)

t = T.set_index("days")
row = lambda k: {c: (float(v) if c.endswith("pct") else int(v)) for c, v in t.loc[k].items()}
res = {"members_with_purchase": len(mem), "purchases": len(buy), "gone_at_eval": int(mem.gone.sum()),
       "d90": row(90), "d180": row(180), "d60": row(60), "d365": row(365),
       "ratio_90_180": round(t.loc[90, "dormant"] / t.loc[180, "dormant"], 2), "own_rule": own, "sql_match": chk}
res = json.loads(json.dumps(res, default=lambda x: x.item() if hasattr(x, "item") else str(x)))
json.dump(res, open(RES / "a573_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False)); print(SG.to_string())

# 図1：区切りの日数ごとの休眠人数と復活率
fig, ax = plt.subplots(figsize=(8, 4)); ax2 = ax.twinx()
ax.bar([str(x) for x in TH], T.dormant / 1000, color=LIGHT, label="休眠の人数（左）")
ax2.plot([str(x) for x in TH], T.revive_pct, color=ORANGE, marker="o", label="休眠のうち180日以内に買った割合（右）")
for x, v in zip(TH, T.revive_pct): ax2.text(str(x), v + 1.5, f"{v:.0f}%", color=ORANGE, ha="center", fontsize=9)
ax.set_xlabel("最終購入から何日で休眠とするか"); ax.set_ylabel("休眠の人数（千人）"); ax2.set_ylabel("復活の割合（%）"); ax2.set_ylim(0, 100)
ax2.spines["right"].set_visible(True)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels(); ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=9, loc="upper right")
ax.set_title(f"90日なら{t.loc[90,'dormant']:,}人・復活{t.loc[90,'revive_pct']:.0f}%、180日なら{t.loc[180,'dormant']:,}人・復活{t.loc[180,'revive_pct']:.0f}%")
save(fig, "a573_threshold.png", "出典：" + SRC + "。判定日は2025年6月30日")
# 図2：誤判定（まだ離れていないのに休眠／もう離れているのに休眠でない）
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot([str(x) for x in TH], T.false_dormant, color=ORANGE, marker="o", label="まだ離れていないのに休眠に入った人")
ax.plot([str(x) for x in TH], T.missed_gone, color=BLUE, marker="o", label="もう離れているのに休眠に入らなかった人")
ax.axhline(own["false_dormant"], color=ORANGE, ls=":", lw=1); ax.axhline(own["missed_gone"], color=BLUE, ls=":", lw=1)
ax.text(6.1, own["false_dormant"], "本人の間隔×3", color=ORANGE, fontsize=8, va="bottom", ha="right"); ax.text(6.1, own["missed_gone"], "本人の間隔×3", color=BLUE, fontsize=8, va="bottom", ha="right")
ax.set_xlabel("最終購入から何日で休眠とするか"); ax.set_ylabel("人数"); ax.legend(frameon=False, fontsize=9)
ax.set_title("短く切ると入れすぎ、長く切ると取りこぼす")
save(fig, "a573_errors.png", "出典：" + SRC + "。「離れた」は作成者が置いた見えない時点。点線は本人の買う間隔の3倍で切った場合")
# 図3：買う間隔ごとの休眠の割合
fig, ax = plt.subplots(figsize=(8, 4))
cs = ["30日ごと", "60日ごと", "120日ごと"]; rules = ["90日", "180日", "本人の間隔×3"]; col = [ORANGE, BLUE, GREEN]
x = np.arange(3)
for k, (r, c) in enumerate(zip(rules, col)):
    v = [SG[(SG.cycle == s) & (SG.rule == r)].false_dormant_pct_of_active.iloc[0] for s in cs]
    b = ax.bar(x + (k - 1) * .27, v, .27, color=c, label=r)
    for xx, vv in zip(x + (k - 1) * .27, v): ax.text(xx, vv + .5, f"{vv:.0f}", ha="center", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels(["30日ごとに買う人", "60日ごと", "120日ごと"]); ax.set_ylabel("まだ離れていない人のうち休眠に入った割合（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("90日で切ると、たまに買う人の多くが休眠に入る")
save(fig, "a573_by_cycle.png", "出典：" + SRC)
