"""棚卸し・実行・比較の結果をまとめ、判定と頑健性チェックを results/ に書く。
使い方: python src/05_集計.py   （記事フォルダの直下で実行）
"""
import json
import numpy as np, pandas as pd
from pathlib import Path
D, R = Path("data"), Path("results"); R.mkdir(exist_ok=True)
inv = pd.read_csv(D / "inventory.csv"); smp = pd.read_csv(D / "sample.csv")
runA = pd.read_csv(D / "run_clean_env.csv"); cmpA = pd.read_csv(D / "compare_clean_env_by_article.csv")
fileA = pd.read_csv(D / "compare_clean_env_by_file.csv")
runB = pd.read_csv(D / "run_authoring_env.csv"); cmpB = pd.read_csv(D / "compare_authoring_env_by_article.csv")
fileB = pd.read_csv(D / "compare_authoring_env_by_file.csv")
ORDER = ["完全一致", "1e-6以内", "1e-3以内", "1e-2以内", "ずれ", "形が違う", "作られない"]
ROW_ORDER_ONLY = {("F113_price_index_formulas", "items_2005_2024.csv")}  # 並べ替えると一致（同順位の並び）

def worst(files, tol_idx, ignore_order=False):
    out = {}
    for f, g in files.groupby("folder"):
        lv = [("完全一致" if ignore_order and (f, r.file) in ROW_ORDER_ONLY else r.level) for r in g.itertuples()]
        lv = [l for l in lv if l in ORDER]
        out[f] = all(ORDER.index(l) <= tol_idx for l in lv)
    return pd.Series(out)

def verdict(run, files, tol_idx=2, ignore_order=False):
    m = worst(files, tol_idx, ignore_order)
    rows = []
    for r in run.itertuples():
        match = bool(m.get(r.folder, True))
        if r.steps_ok == r.n_steps: steps = "全部動いた"
        elif r.net_fail_fetch_only == 1: steps = "取得だけ通信で止まった"
        else: steps = "途中で止まった手順がある"
        if not match: v = "数字がずれた"
        elif steps == "全部動いた": v = "そのまま再現"
        elif steps == "取得だけ通信で止まった": v = "取得以外は再現"
        else: v = "手順が止まったが数字は一致"
        rows.append(dict(folder=r.folder, steps=steps, match=match, verdict=v))
    return pd.DataFrame(rows)

vA = verdict(runA, fileA).merge(smp[["folder", "kind", "stratum", "N_stratum"]], on="folder")
vA["weight"] = vA.N_stratum / vA.groupby("stratum").folder.transform("size")
vA.to_csv(R / "verdict_clean_env.csv", index=False)
CATS = ["そのまま再現", "取得以外は再現", "手順が止まったが数字は一致", "数字がずれた"]
tab = vA.pivot_table(index="verdict", columns="kind", values="folder", aggfunc="count", fill_value=0).reindex(CATS, fill_value=0)
tab["計"] = tab.sum(axis=1); tab.to_csv(R / "verdict_table.csv")
print(tab)

# 母集団（379本）への重み付き推定と、層別の標準誤差
def wshare(df, cond):
    est, var = 0.0, 0.0; Ntot = df.groupby("stratum").N_stratum.first().sum()
    for s, g in df.groupby("stratum"):
        N, n = g.N_stratum.iloc[0], len(g); p = cond(g).mean()
        est += N / Ntot * p; var += (N / Ntot) ** 2 * (1 - n / N) * p * (1 - p) / max(n - 1, 1)
    return est, np.sqrt(var)
est = {}
for name, cond in [("数字が一致（1e-3以内）", lambda g: g.match), ("そのまま再現", lambda g: g.verdict == "そのまま再現"),
                   ("数字がずれた", lambda g: g.verdict == "数字がずれた")]:
    e, se = wshare(vA, cond)
    est[name] = dict(unweighted=round(cond(vA).mean(), 3), weighted=round(e, 3), se=round(se, 3),
                     lo=round(max(0, e - 1.96 * se), 3), hi=round(min(1, e + 1.96 * se), 3))
    for k in ["看板", "通常"]:
        g = vA[vA.kind == k]; e2, se2 = wshare(g, cond)
        est[name][k] = dict(n=len(g), share=round(cond(g).mean(), 3), weighted=round(e2, 3), se=round(se2, 3))

# 頑健性1：一致とみなす許容誤差
rob = []
for i, lab in [(1, "1e-6"), (2, "1e-3（主）"), (3, "1e-2")]:
    for io in [False, True]:
        v = verdict(runA, fileA, i, io)
        rob.append(dict(check="許容誤差・並び順", setting=f"{lab}{'・並び順は無視' if io else ''}",
                        n=len(v), match=int(v.match.sum()), flagship_mismatch=int((~v.match & v.folder.str.startswith("F")).sum()),
                        regular_mismatch=int((~v.match & ~v.folder.str.startswith("F")).sum())))
# 頑健性2：環境（記事ごとの新しい環境 vs 書いたときの環境）、両方で動かした15本
vB = verdict(runB, fileB)
both = vA.merge(vB, on="folder", suffixes=("_A", "_B"))
rob.append(dict(check="環境", setting="新しい環境（requirements.txt だけ）", n=len(both), match=int(both.match_A.sum()),
                flagship_mismatch=int((~both.match_A).sum()), regular_mismatch=0))
rob.append(dict(check="環境", setting="書いたときの環境", n=len(both), match=int(both.match_B.sum()),
                flagship_mismatch=int((~both.match_B).sum()), regular_mismatch=0))
both[["folder", "steps_A", "match_A", "steps_B", "match_B"]].to_csv(R / "env_comparison.csv", index=False)
# 頑健性3：結果ファイル単位（記事の数え方を変える）
fa = fileA.copy(); fa["ok"] = fa.level.map(lambda l: ORDER.index(l) <= 2 if l in ORDER else True)
rob.append(dict(check="数える単位", setting="結果ファイル単位", n=len(fa), match=int(fa.ok.sum()),
                flagship_mismatch=int((~fa.ok & fa.folder.str.startswith("F")).sum()),
                regular_mismatch=int((~fa.ok & ~fa.folder.str.startswith("F")).sum())))
# 頑健性4：手順の数え方（取得の通信失敗を失敗に数える）
strict = (runA.steps_ok == runA.n_steps).sum()
rob.append(dict(check="手順", setting="通信の失敗も失敗に数える（全部動いた本数）", n=len(runA), match=int(strict),
                flagship_mismatch=int(((runA.steps_ok < runA.n_steps) & runA.folder.str.startswith("F")).sum()), regular_mismatch=0))
pd.DataFrame(rob).to_csv(R / "robustness.csv", index=False)
print(pd.DataFrame(rob).to_string())

# 静的な棚卸し（379本、実行なし）
inv["unseeded_random"] = (inv.uses_random == 1) & (inv.seed_fixed == 0)
inv["unpinned"] = inv.req_pinned < inv.req_total
flags = {"README に再現手順": inv.readme_repro, "requirements.txt あり": inv.req == 1,
         "requirements.txt の版を全部固定": ~inv.unpinned, "コードに書いたのに requirements にない部品": inv.n_req_missing > 0,
         "コードがネットにつなぐ": inv.net_in_code == 1, "ほかの記事のフォルダを読む": inv.cross_ref == 1,
         "乱数を使うのに種がない": inv.unseeded_random, "まとめて動かすスクリプト": inv.run_all == 1,
         "絶対パス": inv.abs_path == 1, "10MB 超のファイル": inv.big_files > 0}
st = pd.DataFrame([dict(item=k, n=int(v.sum()), share=round(v.mean(), 3),
                        flagship=int(v[inv.kind == "看板"].sum()), regular=int(v[inv.kind == "通常"].sum())) for k, v in flags.items()])
st.to_csv(R / "static_inventory_summary.csv", index=False); print(st.to_string())
# 頑健性5：静的な危険信号で、実行の失敗を見分けられたか
m = vA.merge(inv, on="folder")
m["risk"] = (m.net_in_code == 1) | (m.cross_ref == 1) | m.unseeded_random | (m.n_req_missing > 0)
ct = pd.crosstab(m.risk, m.verdict.ne("そのまま再現")); ct.to_csv(R / "static_flag_vs_run.csv"); print(ct)
summary = dict(population=len(inv), flagship=int((inv.kind == "看板").sum()), regular=int((inv.kind == "通常").sum()),
               sample=len(vA), estimates=est, data_mb_total=round(inv.data_mb.sum(), 1),
               run_sec_total_clean=round(runA.run_sec.sum(), 1), run_sec_median_clean=float(runA.run_sec.median()),
               mismatch_files=fileA[~fileA.level.isin(ORDER[:3])].to_dict("records"))
json.dump(summary, open(R / "summary.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(est, ensure_ascii=False, indent=1))
