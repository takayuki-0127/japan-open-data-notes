"""02 整形：線形計画のパラメータを作る（すべて2024年度・2024年産）。
- 作物ごとに「1ha で1人1日あたり何 kcal になるか」を、収量×食べられる割合×100g当たり熱量 から計算する
- 今の国産の熱量（公表の品目別自給率×1人1日当たり供給熱量）と合うよう、作物ごとに補正係数 κ を置く
- モデルに入れない品目（魚介・砂糖・油脂・果実など）の国産分は、公表の国産供給熱量 860kcal との差としてまとめて固定する
"""
import json, csv
import pandas as pd
from common import DATA, RES, num

TOTAL_KCAL = None  # 供給熱量（1人1日）
DOMESTIC_KCAL_OFFICIAL = 860.0  # 令和6年度 1人1日当たり国内供給熱量（農林水産省 公表、2025-10-10）

CROPS = [  # 名前, 需給表の品目, 作物統計の行, 公表の自給率の行
    ("米", "穀類_米", "水稲（主食用）", "米"),
    ("小麦", "穀類_小麦", "小麦", "小麦"),
    ("大豆", "豆類_大豆", "大豆", "豆類_大豆_うち食用"),
    ("ばれいしょ", "いも類_ばれいしょ", "ばれいしょ", "いも類_ばれいしょ"),
    ("かんしょ", "いも類_かんしょ", "かんしょ", "いも類_かんしょ"),
    ("野菜", "野菜", "野菜（ばれいしょを除く）", "野菜"),
]

def load():
    fbs = pd.read_csv(DATA / "fbs_2024.csv", dtype=str).set_index("需給品目")
    fbs = fbs.apply(lambda c: c.map(num))
    crops = pd.read_csv(DATA / "crops_2024.csv").set_index("作物")
    misc = json.load(open(DATA / "misc_2024.json", encoding="utf-8"))
    v = crops.loc["主要野菜計"]; p = crops.loc["ばれいしょ"]
    crops.loc["野菜（ばれいしょを除く）"] = [v["作付面積_ha"] - p["作付面積_ha"], None, v["収穫量_t"] - p["収穫量_t"]]
    crops.loc["野菜（ばれいしょを除く）", "10a当たり収量_kg"] = crops.loc["野菜（ばれいしょを除く）", "収穫量_t"] / crops.loc["野菜（ばれいしょを除く）", "作付面積_ha"] * 100
    return fbs, crops, misc

def col(fbs, item, key):
    c = [x for x in fbs.columns if key in x]
    return fbs.loc[item, c[0]]

if __name__ == "__main__":
    fbs, crops, misc = load()
    pop = misc["population_2024"] * 1000
    total = fbs.loc["合計", [c for c in fbs.columns if "１日当たり_熱量" in c][0]]
    ss = misc["ss"]
    rows = []
    for name, item, crow, ssrow in CROPS:
        kcal_day = col(fbs, item, "１日当たり_熱量")
        rough = col(fbs, item, "粗食料_総数"); loss = col(fbs, item, "減耗量"); yld = col(fbs, item, "歩留り")
        k100 = col(fbs, item, "100g中の栄養成分量_熱量")
        e_t = rough / (rough + loss) * yld / 100 * k100 * 1e4  # 食用に回る生産1トンあたりの kcal
        y_t_ha = crops.loc[crow, "10a当たり収量_kg"] / 100  # t/ha
        kcal_per_ha_day = y_t_ha * e_t / (pop * 365)  # 1ha で 1人1日あたり kcal
        area = crops.loc[crow, "作付面積_ha"]
        dom = kcal_day * ss[ssrow] / 100
        raw_dom = kcal_per_ha_day * area
        rows.append(dict(作物=name, 需給表の品目=item, 面積_ha=area, 収量_t_ha=y_t_ha, 食用1tのkcal=e_t,
                         kcal_10a_年=y_t_ha / 10 * e_t, kcal_人日_per_万ha=kcal_per_ha_day * 1e4,
                         供給熱量_kcal人日=kcal_day, 公表自給率=ss[ssrow], 国産熱量_kcal人日=dom,
                         面積から計算した国産熱量=raw_dom, kappa=dom / raw_dom))
    P = pd.DataFrame(rows)
    # 畜産（飼料自給率を反映した国産熱量）
    live = {"肉類": ("肉類", "肉類（飼料自給率）"), "鶏卵": ("鶏卵", "鶏卵（飼料自給率）"), "牛乳及び乳製品": ("牛乳及び乳製品", "牛乳及び乳製品（飼料自給率）")}
    L = []
    for k, (item, s) in live.items():
        kd = col(fbs, item, "１日当たり_熱量"); L.append(dict(品目=k, 供給熱量=kd, 飼料自給率込みの自給率=ss[s], 国産熱量=kd * ss[s] / 100))
    L = pd.DataFrame(L)
    fd = misc["feed"]
    B = fd["供給量（消費）_国内産_粗飼料B【TDN千トン】"]; C = fd["供給量（消費）_国内産_濃厚飼料_国産原料C【TDN千トン】"]; A = fd["需要量A【TDN千トン】"]
    cr = crops
    feed_land = cr.loc["牧草", "作付面積_ha"] + cr.loc["青刈りとうもろこし", "作付面積_ha"] + cr.loc["ソルゴー", "作付面積_ha"]
    wcs = cr.loc["WCS用稲", "作付面積_ha"]; frice = cr.loc["飼料用米", "作付面積_ha"]
    # 前提：飼料用米は主食用と同じ収量（玄米）、TDN は玄米重量の 80%（推測にもとづく前提）。粗飼料 B は飼料作物と WCS の面積に比例。
    TDN_frice = frice * cr.loc["水稲（主食用）", "10a当たり収量_kg"] / 100 * 0.80 / 1000  # 千トン
    live_dom = L["国産熱量"].sum()
    params = dict(population=pop, total_kcal=total, domestic_official=DOMESTIC_KCAL_OFFICIAL,
                  official_ss=ss["供給熱量ベースの総合食料自給率"],
                  livestock_dom=live_dom, feed_B=B, feed_C=C, feed_A=A, feed_ss=(B + C) / A * 100,
                  feed_land_upland_ha=feed_land, wcs_ha=wcs, feed_rice_ha=frice, TDN_feed_rice=TDN_frice,
                  loss_per_ha_feedland=live_dom * B / (B + C) / (feed_land + wcs),
                  loss_per_ha_feedrice=live_dom * TDN_frice / (B + C) / frice,
                  crops_dom=P["国産熱量_kcal人日"].sum())
    params["other_fixed"] = DOMESTIC_KCAL_OFFICIAL - params["crops_dom"] - live_dom
    params["land"] = misc["land"]
    params["barley_ha"] = sum(cr.loc[x, "作付面積_ha"] for x in ["二条大麦", "六条大麦", "はだか麦"])
    RES.mkdir(exist_ok=True)
    P.to_csv(RES / "crop_params.csv", index=False, encoding="utf-8-sig")
    L.to_csv(RES / "livestock.csv", index=False, encoding="utf-8-sig")
    json.dump(params, open(RES / "params.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    pd.set_option("display.width", 220); pd.set_option("display.max_columns", 20)
    print(P.round(3)); print(L.round(2)); print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in params.items() if k != "land"})
