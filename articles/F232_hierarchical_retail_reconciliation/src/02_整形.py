# F232 02 整形：業態×商品の階層（全体→業態→中分類→葉）を作る
import pandas as pd, numpy as np, json, pathlib
B = pathlib.Path(__file__).resolve().parents[1]
d = pd.read_csv(B / "data/raw/retail_national_2014_2026.csv")
w = d.pivot_table(index="ym", columns=["業態", "品目"], values="値")

# 葉（いちばん細かい単位）。足すと各業態の合計に一致する組だけを使う
LEAF = {
    "百貨店": ["紳士服・洋品", "婦人・子供服・洋品", "その他の衣料品", "身の回り品", "飲食料品",
            "家具", "家庭用電気機械器具", "家庭用品", "その他の商品", "食堂・喫茶"],
    "スーパー": ["紳士服・洋品", "婦人・子供服・洋品", "その他の衣料品", "身の回り品", "飲食料品",
             "家具", "家庭用電気機械器具", "家庭用品", "その他の商品", "食堂・喫茶"],
    "コンビニ": ["FF・日配食品", "加工食品", "非食品", "サービス売上高"],
    "ドラッグストア": ["調剤医薬品", "ＯＴＣ医薬品", "ヘルスケア用品（衛生用品）・介護・ベビー", "健康食品",
                "ビューティケア（化粧品・小物）", "トイレタリー", "家庭用品・日用消耗品・ペット用品", "食品", "その他"],
    "ホームセンター": ["ＤＩＹ用具・素材", "電気", "インテリア", "家庭用品・日用品", "園芸・エクステリア",
                "ペット・ペット用品", "カー用品・アウトドア", "オフィス・カルチャー", "その他"],
    "家電大型専門店": ["ＡＶ家電", "情報家電", "通信家電", "カメラ類", "生活家電", "その他"],
}
# 中分類（統計で公表されている集計）。百貨店・スーパーの「衣料品」は身の回り品を含む
MID = {
    ("百貨店", "衣料品"): ["紳士服・洋品", "婦人・子供服・洋品", "その他の衣料品", "身の回り品"],
    ("百貨店", "その他"): ["家具", "家庭用電気機械器具", "家庭用品", "その他の商品", "食堂・喫茶"],
    ("スーパー", "衣料品"): ["紳士服・洋品", "婦人・子供服・洋品", "その他の衣料品", "身の回り品"],
    ("スーパー", "その他"): ["家具", "家庭用電気機械器具", "家庭用品", "その他の商品", "食堂・喫茶"],
    ("コンビニ", "商品販売額"): ["FF・日配食品", "加工食品", "非食品"],
}
TOT = {"百貨店": "合計", "スーパー": "合計", "コンビニ": "合計", "ドラッグストア": "商品販売額",
       "ホームセンター": "商品販売額", "家電大型専門店": "商品販売額"}

leaves = [(g, i) for g in LEAF for i in LEAF[g]]
nodes = [("全体", "全体", 0)] + [(g, g, 1) for g in LEAF] + [(g, f"{g}/{m}", 2) for (g, m) in MID] + \
        [(g, f"{g}/{i}", 3) for g, i in leaves]
S = np.zeros((len(nodes), len(leaves)))
for r, (g, name, lv) in enumerate(nodes):
    for c, (lg, li) in enumerate(leaves):
        if lv == 0: S[r, c] = 1
        elif lv == 1: S[r, c] = (lg == g)
        elif lv == 2: S[r, c] = (lg == g and li in MID[(g, name.split("/", 1)[1])])
        else: S[r, c] = (name == f"{lg}/{li}")
Y = pd.DataFrame({f"{g}/{i}": w[(g, i)] for g, i in leaves})
YB = Y.values @ S.T
Yall = pd.DataFrame(YB, index=Y.index, columns=[n[1] for n in nodes])
# 検算：公表の業態合計・中分類と、葉の足し上げが一致するか
chk = []
for g in LEAF:
    chk.append([g, "業態合計", float((Yall[g] / w[(g, TOT[g])] - 1).abs().max() * 100)])
for (g, m) in MID:
    chk.append([g, m, float((Yall[f"{g}/{m}"] / w[(g, m)] - 1).abs().max() * 100)])
pd.DataFrame(chk, columns=["業態", "集計", "最大のずれ_%"]).to_csv(B / "results/00_hierarchy_check.csv", index=False)
Yall.to_csv(B / "data/hier_wide.csv")
pd.DataFrame(nodes, columns=["業態", "ノード", "階層"]).to_csv(B / "data/nodes.csv", index=False)
np.savetxt(B / "data/S_matrix.csv", S, fmt="%d", delimiter=",")
print(Yall.shape, len(leaves), "max check gap %", max(c[2] for c in chk))
