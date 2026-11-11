"""245：重複の入った架空の顧客表を、SQL の5つの照合ルールで片づけ、正解（人ID）と比べる"""
import json
import duckdb, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, save, tsql_to_duckdb, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

con = duckdb.connect(); con.execute("CREATE SCHEMA dbo")
con.execute(f"CREATE TABLE dbo.customers AS SELECT customer_id, person_id, name, CAST(birth AS DATE) birth, CAST(tel AS VARCHAR) tel, email, dup_type, "
            f"CAST(updated_at AS TIMESTAMP) updated_at FROM read_csv_auto('{DATA / 'customers.csv'}', all_varchar=false)")
q2 = tsql_to_duckdb((SQL / "02_normalize.sql").read_text())
con.execute("CREATE TABLE dbo.c_norm AS " + q2[q2.index("\nSELECT") + 1:].replace("INTO dbo.c_norm\n", ""))  # T-SQL の SELECT … INTO を DuckDB の書き方に
q3 = tsql_to_duckdb((SQL / "03_rules.sql").read_text()).replace("'NULL#' + CAST(customer_id AS VARCHAR(10))", "'NULL#' || CAST(customer_id AS VARCHAR(10))")
con.execute("CREATE TABLE dbo.groups AS " + q3)
g = con.execute("SELECT * FROM dbo.groups ORDER BY customer_id").df()
n_rows, n_people = len(g), g.person_id.nunique()
true_dups = n_rows - n_people
RULES = {"g1": "R1 完全一致", "g2": "R2 名前＋生年月日", "g3": "R3 ＋電話", "g4": "R4 ＋（電話 または メール）", "g5": "R5 R4＋（生年月日＋メール）"}

# 「または」のつながりが2回の MIN で閉じたか（Python の連結成分と比べる）
import networkx as nx  # noqa: E402  （確かめだけに使う）
def components(keys_list):
    G = nx.Graph(); G.add_nodes_from(g.customer_id)
    for keys in keys_list:
        for _, grp in n.groupby(keys).customer_id:
            ids = list(grp)
            G.add_edges_from(zip(ids[:-1], ids[1:]))
    lab = {}
    for comp in nx.connected_components(G):
        m = min(comp)
        for i in comp: lab[i] = m
    return g.customer_id.map(lab)
n = con.execute("SELECT * FROM dbo.c_norm").df()
n["tel_k"] = n.tel_n.fillna("NULL#" + n.customer_id.astype(str))
n = n.set_index("customer_id").loc[g.customer_id].reset_index()
chk_closure = {"g4": bool((components([["name_n", "birth", "tel_k"], ["name_n", "birth", "email_n"]]).values == g.g4.values).all()),
               "g5": bool((components([["name_n", "birth", "tel_k"], ["name_n", "birth", "email_n"], ["birth", "email_n"]]).values == g.g5.values).all())}

res = []
for col, lab in RULES.items():
    k = g.sort_values(["updated_at", "customer_id"], ascending=False).groupby(col).head(1).set_index(col)  # 残す行（新しい行）
    removed = g[~g.customer_id.isin(k.customer_id)]
    same = removed.person_id.values == k.loc[removed[col], "person_id"].values
    correct, wrong = int(same.sum()), int((~same).sum())
    # 種類ごとに、見つけられた重複の割合
    found_by_type = {}
    for t in ["そのまま二重", "名前の空白", "電話の書き方", "メールの大文字", "電話が変わった", "姓が変わった"]:  # 並びを固定
        tt = g[g.dup_type == t]
        # その行が、同じ人の別の行と同じグループにいるか
        grp_people = g.groupby(col).person_id.agg(lambda s: s.value_counts().to_dict())
        found_by_type[t] = round(float(np.mean([grp_people[r[col]].get(r.person_id, 0) >= 2 for _, r in tt.iterrows()])) * 100, 1)
    res.append({"rule": lab, "groups": int(g[col].nunique()), "removed": len(removed), "correct": correct, "wrong_merge": wrong,
                "missed": true_dups - correct, "found_pct_by_type": found_by_type})
R = pd.DataFrame(res)

# 残す行：新しい行の電話が空のとき
kept = con.execute(tsql_to_duckdb((SQL / "04_keep_latest.sql").read_text())).df()
lost_naive = int((kept.tel_latest.isna() & kept.tel_filled.notna()).sum())
chk = {"rows": n_rows, "people": n_people, "true_dups": true_dups, "closure_matches_networkx": chk_closure,
       "same_name_birth_diff_person_pairs": 40, "rules": res, "kept_rows_R5": len(kept), "tel_lost_if_keep_latest_only": lost_naive,
       "tel_null_after_fill": int(kept.tel_filled.isna().sum())}
json.dump(chk, open(RES / "checks.json", "w"), ensure_ascii=False, indent=1, default=str)
R.drop(columns="found_pct_by_type").to_csv(RES / "rules_summary.csv", index=False)
pd.DataFrame({r["rule"]: r["found_pct_by_type"] for r in res}).to_csv(RES / "found_pct_by_type.csv")
print(json.dumps(chk, ensure_ascii=False, indent=1, default=str))

# 図1：ルールごとの「正しく消せた」「間違えてまとめた」「見落とした」
fig, ax = plt.subplots(figsize=(8.6, 4.2))
y = np.arange(len(R))[::-1]
ax.barh(y, R.correct, color=BLUE, label="正しく消せた重複")
ax.barh(y, R.missed, left=R.correct, color=LIGHT, label="見落とした重複")
ax.barh(y, -R.wrong_merge, color=ORANGE, label="別人をまとめて消した（左へ）")
for yi, r in zip(y, R.itertuples()):
    ax.text(true_dups + 15, yi, f"{r.correct}／{true_dups}　誤り{r.wrong_merge}", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(R.rule); ax.axvline(0, color=INK, lw=0.8)
ax.set_xlim(-120, true_dups + 260); ax.set_xlabel("行数", labelpad=2)
ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=3)
ax.set_title(f"架空の顧客表（{n_rows:,}行、本当の重複{true_dups}行）を5つのルールで片づける", fontsize=11.5)
save(fig, "a245_rules.png", y=-0.12)

# 図2：重複の種類ごとに、見つけられた割合
T = pd.DataFrame({r["rule"].split(" ")[0]: r["found_pct_by_type"] for r in res})
order = ["そのまま二重", "名前の空白", "電話の書き方", "メールの大文字", "電話が変わった", "姓が変わった"]
T = T.loc[order]
fig, ax = plt.subplots(figsize=(8.6, 3.9))
im = ax.imshow(T.values, cmap="Blues", vmin=0, vmax=100, aspect="auto")
for i in range(T.shape[0]):
    for j in range(T.shape[1]):
        v = T.values[i, j]; ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=9.5, color="white" if v > 60 else INK)
ax.set_xticks(range(T.shape[1])); ax.set_xticklabels(T.columns); ax.set_yticks(range(T.shape[0])); ax.set_yticklabels(T.index)
ax.set_title("重複の種類ごとに、同じ人の行と同じグループに入った割合", fontsize=11.5)
for s in ax.spines.values(): s.set_visible(False)
save(fig, "a245_by_type.png")

# 図3：手順の表
fig, ax = plt.subplots(figsize=(11.5, 3.3)); ax.axis("off")
rows = [["1", "照合用の列を作る", "空白・ハイフンを取る、メールを小文字に", "REPLACE・LOWER"],
        ["2", "グループ番号をつける", "キーごとの最小の顧客ID（「または」は2回）", "MIN() OVER (PARTITION BY …)"],
        ["3", "グループの中身を見る", "名前＋生年月日だけでまとまった組を目で確かめる", "COUNT(*) OVER・HAVING"],
        ["4", "1行だけ残す", "新しい行を残し、空の電話は古い行から埋める", "ROW_NUMBER・FIRST_VALUE"],
        ["5", "消す前に件数を照合", "元の行数＝残す行数＋消す行数", "COUNT"]]
t = ax.table(cellText=rows, colLabels=["", "手順", "中身", "使う SQL"], loc="center", cellLoc="left", colLoc="center", colWidths=[0.03, 0.2, 0.43, 0.3])
t.auto_set_font_size(False); t.set_fontsize(9.5); t.scale(1, 1.55)
for (i, j), c in t.get_celld().items():
    c.set_edgecolor("#dddddd")
    if i == 0: c.set_facecolor("#eef3fb"); c.set_text_props(weight="bold")
ax.set_title("SQL で重複を片づける5つの手順", fontsize=12)
save(fig, "a245_steps.png", y=0.06)
