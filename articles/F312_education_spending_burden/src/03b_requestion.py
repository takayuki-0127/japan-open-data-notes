"""問い直し（結果を見てから足した）：
40代では教育費の割合が下がり、50代では上がった。子育ての時期が遅くなった分、40代だけを見ると軽く見えるのではないか。
世帯主が40代と50代の世帯をまとめ（世帯数分布で重みづけ）、教育費の割合と、18歳未満の人1人当たりの実質の教育費を見る。
あわせて、年齢ごとの教育費の割合（始点と終点）と、18歳未満人員の年齢ごとの変化を出す。"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES = ROOT / "results"
r3 = lambda x: round(float(x), 3)
W = pd.read_csv(RES / "panel_by_age_year.csv")
S, E = [2002, 2003, 2004], [2023, 2024, 2025]
AG = ["29歳以下", "30～39歳", "40～49歳", "50～59歳", "60～69歳", "70歳以上"]
g = W[W.age.isin(["40～49歳", "50～59歳"])].copy()
for c in ["education", "consumption", "children", "real_edu"]:
    g[c + "_w"] = g[c] * g.hh_weight
a = g.groupby("year")[["education_w", "consumption_w", "children_w", "real_edu_w", "hh_weight"]].sum()
a["share_edu"] = 100 * a.education_w / a.consumption_w
a["real_per_child"] = a.real_edu_w / a.children_w
a.round(4).to_csv(RES / "requestion_40_59_by_year.csv")
prof = W[W.age.isin(AG)].copy()
prof["period"] = np.where(prof.year.isin(S), "2002〜04年", np.where(prof.year.isin(E), "2023〜25年", None))
pm = prof.dropna(subset=["period"]).groupby(["period", "age"])[["share_edu", "children", "real_edu_per_child"]].mean().round(4)
pm.to_csv(RES / "requestion_age_profile.csv")
out = {"age40_59": {"share_edu": [r3(a.loc[S, "share_edu"].mean()), r3(a.loc[E, "share_edu"].mean())],
                    "share_edu_change_pt": r3(a.loc[E, "share_edu"].mean() - a.loc[S, "share_edu"].mean()),
                    "real_per_child_dlog": r3(100 * np.log(a.loc[E, "real_per_child"].mean() / a.loc[S, "real_per_child"].mean()))},
       "profile": {p: {ag: dict(share=r3(pm.loc[(p, ag), "share_edu"]), children=r3(pm.loc[(p, ag), "children"])) for ag in AG} for p in ["2002〜04年", "2023〜25年"]}}
(RES / "requestion.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=0))
