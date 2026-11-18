"""読み取り済みの CSV（data/extract_*.csv）と学校基本調査の Excel から、分析用の表を作る。合計の照合もここで行う。"""
import json, re
import openpyxl
import pandas as pd
from common import ROOT, REGIONS

D = ROOT / "data"
chk = {}
st = pd.read_csv(D / "extract_stage.csv").set_index("year")
parts = st[["grad", "ug_jc_tech", "senshu", "prep"]].sum(axis=1) + st.jls.fillna(0)
chk["stage_parts_eq_total"] = bool((parts == st.total).all())

# 国別（全体・高等教育機関）：計と内訳の和、前年の値の照合
out = {}
for kind in ["all", "he"]:
    d = pd.read_csv(D / f"extract_country_{kind}.csv")
    tot = d[d.country == "計"].set_index("survey_year")
    rest = d[d.country != "計"]
    chk[f"{kind}_sum_eq_total"] = bool((rest.groupby("survey_year").n.sum() == tot.n).all())
    chk[f"{kind}_prevsum_eq_prevtotal"] = bool((rest.groupby("survey_year").n_prev.sum() == tot.n_prev).all())
    # 今年の表にある「前年の値」と、前年の表の値（同じ国）を比べる
    cur = rest.set_index(["survey_year", "country"]).n
    prev = rest.set_index(["survey_year", "country"]).n_prev
    diffs = []
    for (y, c), v in prev.items():
        if (y - 1, c) in cur.index and c != "その他":
            diffs.append({"kind": kind, "year": y - 1, "country": c, "own_table": int(cur[(y - 1, c)]), "next_table": int(v),
                          "diff": int(v - cur[(y - 1, c)])})
    out[kind] = pd.DataFrame(diffs)
    # 年×国の表：その年の表の値。2013年だけは2014年の表の前年の値
    panel = rest[["survey_year", "country", "n"]].rename(columns={"survey_year": "year"})
    p13 = rest[rest.survey_year == 2014][["country", "n_prev"]].rename(columns={"n_prev": "n"}).assign(year=2013)
    panel = pd.concat([p13[["year", "country", "n"]], panel]).sort_values(["year", "country"])
    panel.to_csv(D / f"country_{kind}.csv", index=False)
    tt = pd.concat([pd.Series({2013: int(tot.n_prev[2014])}), tot.n]).rename("total")
    tt.index.name = "year"
    tt.to_csv(D / f"country_{kind}_total.csv")
pd.concat(out.values()).to_csv(D / "prev_value_check.csv", index=False)
chk["all_total_eq_stage_total"] = bool(all(pd.read_csv(D / "country_all_total.csv").set_index("year").total == st.total.loc[2013:2025]))
he_stage = st.total - st.jls.fillna(0)
chk["he_total_eq_stage_he"] = bool(all(pd.read_csv(D / "country_he_total.csv").set_index("year").total == he_stage.loc[2013:2025]))

# 日本語教育機関の国別（上位10か国＋その他）
j = pd.read_csv(D / "extract_country_jls.csv")
jt = j[j.country == "計"].set_index("survey_year").n
chk["jls_sum_eq_total"] = bool((j[j.country != "計"].groupby("survey_year").n.sum() == jt).all())
chk["jls_total_eq_stage_jls"] = bool(all(jt == st.jls.loc[2014:2025].astype(int)))
j[j.country != "計"].rename(columns={"survey_year": "year"}).to_csv(D / "country_jls.csv", index=False)

# 都道府県 → 地方（北から南）
p = pd.read_csv(D / "extract_pref.csv")
pt = p.groupby(["survey_year", "basis"]).n.sum()
chk["pref_sum_eq_total"] = bool(all(pt[(y, "本部")] == st.total[y] for y in range(2014, 2026)))
rmap = {pf: r for r, ps in REGIONS for pf in ps}
p["region"] = p.pref.map(rmap)
reg = p.groupby(["survey_year", "basis", "region"], sort=False).n.sum().reset_index().rename(columns={"survey_year": "year"})
reg.to_csv(D / "region.csv", index=False)
p.rename(columns={"survey_year": "year"}).to_csv(D / "pref.csv", index=False)

# 学校基本調査 2025年度：国籍別 外国人学生数（大学・大学院、計の列）。見出しの文字で列と国を選ぶ
def gakko(fname):
    ws = openpyxl.load_workbook(D / "raw" / fname, data_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    head = [r for r in rows if r[0] == "区分"]
    j = next(k for k in range(2, len(head[0])) if all(h[k] == "計" for h in head))
    res = {}
    for r in rows:
        if r[0] == "令和7年度" and r[1] is not None:
            k = re.sub(r"\s+", "", str(r[1]))
            res[k] = res.get(k, 0) + int(r[j])  # 同じ名前が2行ある国（パラオ）は足す
    return res
gu, gg = gakko("gakko_2025_t22_univ_nationality.xlsx"), gakko("gakko_2025_t24_grad_nationality.xlsx")
gname = {"韓国・朝鮮": "韓国", "バングラデシユ": "バングラデシュ"}
g = pd.DataFrame([{"country": gname.get(k, k), "univ": gu.get(k, 0), "grad": gg.get(k, 0)} for k in gu if k != "計"])
chk["gakko_univ_sum_eq_total"] = bool(g.univ.sum() == gu["計"])
chk["gakko_grad_sum_eq_total"] = bool(g.grad.sum() == gg["計"])
g["n"] = g.univ + g.grad
g.to_csv(D / "gakko_2025_univ_grad.csv", index=False)
chk["gakko_totals"] = {"univ": gu["計"], "grad": gg["計"]}
# 照合のために、国の値を何か所か記録（PDF の表を目で見た値と比べる）
ca = pd.read_csv(D / "country_all.csv").set_index(["year", "country"]).n
chk["spot"] = {f"{y}_{c}": int(ca[(y, c)]) for y, c in [(2013, "中国"), (2019, "中国"), (2019, "ベトナム"), (2025, "中国"), (2025, "ネパール")]}
for k, v in chk.items():
    if isinstance(v, bool):
        assert v, k
json.dump(chk, open(D / "build_checks.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, sort_keys=True)
st.to_csv(D / "stage.csv")
print(json.dumps(chk, ensure_ascii=False))
