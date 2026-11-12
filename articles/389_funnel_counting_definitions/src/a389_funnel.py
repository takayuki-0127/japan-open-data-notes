"""389 申込みまでの通過率は、数え方でどれだけ変わるのか
架空のアクセスログ（4万人・28日）。重複、順番の逆転、日またぎ、途中からの再開を入れてある。乱数の種は389。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

STEPS = ["商品ページ", "カート", "入力フォーム", "申込み完了"]; P_NEXT = [0.30, 0.55, 0.60]
DAY0 = pd.Timestamp("2026-03-01")


def make(seed, n_users=40_000, dup=True, skew=True, cross=True, resume=True):
    """人の動きは、どの場面でも同じ（同じ乱数）。違うのは記録のされ方だけ。
    resume=False のときは、途中から入った訪問にも、手前の段の記録が残っているものとする"""
    r = np.random.default_rng(seed); ev = []                 # (user, session, 秒, step)
    for u in range(1, n_users + 1):
        nv = 1 + r.binomial(2, 0.25); days = np.sort(r.choice(28, nv, replace=False)); reached = 0; done = False
        for v, dday in enumerate(days):
            a1, a2, a3, a4 = r.random(4); hour_late, hour = r.uniform(23.6, 23.98), r.uniform(8, 23.5)
            if done and a1 > 0.03: break                       # 申込みが済んだ人は、ほぼ来ない
            late = cross and a2 < 0.06                         # 日付が変わる直前に来る人
            t = dday * 86400 + (hour_late if late else hour) * 3600
            sid = u * 10 + v
            if reached >= 1 and a3 < 0.5: s = 1                # メールのリンクなどから、カートに直接戻る
            elif a4 < 0.04: s = 2                              # 入力フォームに直接来る
            else: s = 0
            nview = r.poisson(1.2); gaps = np.maximum(20, r.exponential(120, 8))
            if s == 0:
                for i in range(nview):                         # 商品ページを何枚か見る
                    ev.append((u, sid, t, 0)); t += gaps[i % 8]
            elif not resume:                                   # 手前の段の記録も残っている場合
                for q in range(s):
                    ev.append((u, sid, t, q)); t += gaps[q]
            while True:
                ev.append((u, sid, t, s)); reached = max(reached, s)
                if s == 3: done = True; break
                if r.random() > P_NEXT[s]: break
                s += 1; t += max(20, r.exponential(180))
    e = pd.DataFrame(ev, columns=["user_id", "session_id", "sec", "step"])
    r2, r3 = np.random.default_rng(seed + 1000), np.random.default_rng(seed + 2000)
    if dup:                                                    # 二重に記録された行：同じ時刻の写しと、数秒後の再読み込み
        p = np.where(e["step"] == 3, 0.03, 0.08); m = r2.random(len(e)) < p
        d = e[m].copy(); re = r2.random(len(d)) < 0.5
        d.loc[re, "sec"] += r2.uniform(3, 60, re.sum()); e = pd.concat([e, d], ignore_index=True)
    if skew:                                                   # 記録の時刻のずれ（前後に最大90秒）
        m = r3.random(len(e)) < 0.03; e.loc[m, "sec"] += r3.uniform(-90, 90, m.sum())
    e["sec"] = e["sec"].round(0)
    e["ts"] = DAY0 + pd.to_timedelta(e["sec"], unit="s"); e["step_name"] = e["step"].map(dict(enumerate(STEPS)))
    return e.sort_values(["ts", "user_id", "step"]).reset_index(drop=True)


def ordered(e, key):
    """key ごとに、商品ページ→カート→入力フォーム→申込み完了 の順で起きたか（前の段より後の時刻のものだけ数える）"""
    t = e[e.step == 0].groupby(key)["sec"].min().rename("t0").to_frame(); n = [len(t)]
    for s in (1, 2, 3):
        x = e[e.step == s].merge(t[[f"t{s-1}"]], left_on=key, right_index=True)
        x = x[x.sec > x[f"t{s-1}"]].groupby(key)["sec"].min().rename(f"t{s}")
        t = t.join(x, how="inner"); n.append(len(t))
    return n


def count_all(e):
    """6つの数え方で、4つの段の数を出す"""
    out = {}
    out["回数（記録のまま）"] = [int((e.step == s).sum()) for s in range(4)]
    ex = e.drop_duplicates(["user_id", "session_id", "sec", "step"])
    out["回数（同じ時刻の写しを除く）"] = [int((ex.step == s).sum()) for s in range(4)]
    out["人（順番を問わない）"] = [int(e[e.step == s].user_id.nunique()) for s in range(4)]
    out["人（順番を問う）"] = ordered(e, "user_id")
    out["訪問（順番を問う）"] = ordered(e, "session_id")
    d = e.assign(ud=e.user_id.astype(str) + "_" + (e.sec // 86400).astype(int).astype(str))
    out["人×日（順番を問う、同じ日のうち）"] = ordered(d, "ud")
    return out


def table(cnt):
    rows = []
    for k, n in cnt.items():
        rows.append({"数え方": k, **{STEPS[i]: n[i] for i in range(4)}, "全体の通過率%": round(100 * n[3] / n[0], 2),
                     "商品ページ→カート%": round(100 * n[1] / n[0], 1), "カート→入力フォーム%": round(100 * n[2] / n[1], 1),
                     "入力フォーム→申込み完了%": round(100 * n[3] / n[2], 1)})
    return pd.DataFrame(rows)


e = make(389)
e[["user_id", "session_id", "ts", "step_name"]].to_csv(DATA / "access_log.csv", index=False)
cnt = count_all(e); tb = table(cnt); tb.to_csv(RES / "funnel_by_definition.csv", index=False)

# ---- SQL（DuckDB）で「人・順番を問わない」と「人・順番を問う」を出して、同じ数か ----
con = duckdb.connect(); con.execute("SET threads=1")
con.execute("CREATE TABLE access_log AS SELECT * FROM read_csv_auto(?)", [str(DATA / "access_log.csv")])
sq = con.execute((ROOT / "src" / "01_funnel_duckdb.sql").read_text(encoding="utf-8")).df()
assert sq.loc[0, ["n1", "n2", "n3", "n4"]].astype(int).tolist() == cnt["人（順番を問わない）"]
assert sq.loc[1, ["n1", "n2", "n3", "n4"]].astype(int).tolist() == cnt["人（順番を問う）"]
sq.to_csv(RES / "sql_check_duckdb.csv", index=False)

# ---- どの「汚れ」が、どの数え方を動かすか ----
SC = {"汚れなし": dict(dup=False, skew=False, cross=False, resume=False), "＋二重の記録": dict(dup=True, skew=False, cross=False, resume=False),
      "＋時刻のずれ": dict(dup=False, skew=True, cross=False, resume=False), "＋日またぎ": dict(dup=False, skew=False, cross=True, resume=False),
      "＋途中から入る訪問": dict(dup=False, skew=False, cross=False, resume=True), "全部入り": dict(dup=True, skew=True, cross=True, resume=True)}
sc = []
for name, kw in SC.items():
    c = count_all(make(389, **kw))
    sc.append({"場面": name, **{k: round(100 * n[3] / n[0], 2) for k, n in c.items()}})
sc = pd.DataFrame(sc); sc.to_csv(RES / "scenarios.csv", index=False)

# 日ごとの通過率（回数で数える／人×日で順番を問う）
e["day"] = (e.sec // 86400).astype(int)
dly = e.groupby(["day", "step"]).size().unstack(fill_value=0)
dd = e.assign(ud=e.user_id.astype(str) + "_" + e.day.astype(str)); rows = []
for dnum, g in dd[dd.day < 28].groupby("day"):
    n = ordered(g, "ud"); rows.append({"日": dnum + 1, "回数で数える%": round(100 * dly.loc[dnum, 3] / dly.loc[dnum, 0], 2), "人×日・順番を問う%": round(100 * n[3] / n[0], 2)})
daily = pd.DataFrame(rows); daily.to_csv(RES / "daily_rates.csv", index=False)

# ---- 図 ----
SRC = "架空のアクセスログ（作成者が乱数で作成、seed 389）。4万人・28日"
fig, ax = plt.subplots(figsize=(8.8, 4.4)); t = tb.iloc[::-1]
ax.barh(t["数え方"], t["全体の通過率%"], color=[BLUE if "人（" in k else (ORANGE if "回数" in k else GREEN) for k in t["数え方"]])
for i, v in enumerate(t["全体の通過率%"]): ax.text(v + 0.1, i, f"{v:.1f}%", va="center", fontsize=9)
ax.set_xlim(0, t["全体の通過率%"].max() * 1.18); ax.set_xlabel("商品ページから申込み完了までの通過率（%）")
ax.set_title("同じログでも、数え方で通過率は変わる")
save(fig, "a389_overall.png", SRC)

fig, axs = plt.subplots(1, 3, figsize=(12, 4.4), sharey=True)
for a, c in zip(axs, ["商品ページ→カート%", "カート→入力フォーム%", "入力フォーム→申込み完了%"]):
    a.barh(t["数え方"], t[c], color=LIGHT)
    for i, v in enumerate(t[c]): a.text(v + 0.5, i, f"{v:.0f}", va="center", fontsize=8.5)
    a.set_title(c.replace("%", ""), fontsize=10.5); a.set_xlim(0, max(110, t[c].max() * 1.12)); a.axvline(100, color=GRAY, lw=0.8, ls=":")
    a.tick_params(axis="y", labelsize=8.5)
fig.suptitle("段ごとの通過率（%）", y=1.02)
save(fig, "a389_steps.png", SRC + "。点線は100%")

fig, ax = plt.subplots(figsize=(10.5, 4.4)); M = sc.set_index("場面"); base = M.loc["汚れなし"]
D = (M - base).to_numpy(); im = ax.imshow(D, cmap="RdBu_r", vmin=-4, vmax=4, aspect="auto")
for i in range(D.shape[0]):
    for j in range(D.shape[1]):
        ax.text(j, i, f"{M.iloc[i, j]:.1f}", ha="center", va="center", fontsize=9)
ax.set_xticks(range(M.shape[1])); ax.set_xticklabels([c.replace("（", "\n（") for c in M.columns], fontsize=8); ax.set_yticks(range(M.shape[0])); ax.set_yticklabels(M.index)
ax.set_title("ログの汚れを1つずつ入れたときの、全体の通過率（%）。色は「汚れなし」との差")
save(fig, "a389_scenarios.png", SRC)

v = tb.set_index("数え方")["全体の通過率%"]
main = {"人数": int(e.user_id.nunique()), "行": len(e), "同じ時刻の写しの行": int(len(e) - len(e.drop_duplicates(["user_id", "session_id", "sec", "step"]))),
        "全体の通過率%": v.to_dict(), "最大と最小の差（ポイント）": round(float(v.max() - v.min()), 2),
        "日ごとの幅": {c: [float(daily[c].min()), float(daily[c].max())] for c in daily.columns[1:]}, "duckdb": duckdb.__version__}
json.dump(main, open(RES / "a389_main.json", "w"), ensure_ascii=False, indent=1)
print(tb.to_string()); print(sc.to_string()); print(daily.describe().round(2).to_string()); print(main)
